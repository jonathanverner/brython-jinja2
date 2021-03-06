"""
    The context Module provides the Context class used for variable lookup
    in expressions, templates etc.
"""

import asyncio

from .utils.observer import ListProxy, DictProxy, Immutable

class Context(object):
    """
        Class used for looking up identifiers when evaluating an expression.
        Access to the variables is via attributes, e.g.:

        .. code-block:: python

            ctx = Context()
            ctx.a = 20
            ctx.l = [1,2,3]


        The class also supports inheritance (nested scopes) via the base
        attribute passed to init:

        .. code-block:: python

            ctx = Context()
            ctx.a = 20

            ch = Context(base=ctx)
            assert ch.a == 20, "Child has access to base scope"

            ch.a = 30
            assert ctx.a == 20, "Child cannot modify base scope"
            assert ch.a == 30, "Child cannot modify base scope"


        WARNING: Only use it to store variables not starting with ``_``.
    """

    def __init__(self, dct=None, base=None):
        """
            The optional parameter ``dct`` is used to initialize the context.
            The optional parameter ``base`` makes this context inherit all
            properties of the base context.
        """
        self._base = base or {}
        if dct is None:
            self._dct = {}
        else:
            self._dct = dct.copy()
        self._saved = {}

    def reset(self, dct):
        """
            Clears the current context and for initializes it with
            the content of :param:`dct`.
        """
        keys = list(self._dct.keys())
        for k in keys:
            delattr(self, k)
        if isinstance(dct, dict):
            for k in dct.keys():
                setattr(self, k, dct[k])
        elif isinstance(dct, Context):
            for k in dct._dct.keys():
                setattr(self, k, getattr(dct, k))

    @property
    def immutable_attrs(self):
        ret = []
        for attr, val in self._dct.items():
            if isinstance(val, Immutable):
                ret.append(attr)
        return ret

    def __iter__(self):
        return iter(self._dct)

    def __contains__(self, attr):
        if attr in self._dct:
            return True
        return attr in self._base

    def __getattr__(self, attr):
        if attr.startswith('_'):
            super().__getattribute__(attr)
        if attr in self._dct:
            ret = self._dct[attr]
            if isinstance(ret, Immutable):
                return ret.value
            else:
                return ret
        elif attr in self._base:
            return getattr(self._base, attr)
        else:
            super().__getattribute__(attr)

    def __setattr__(self, attr, val):
        if attr.startswith('_'):
            super().__setattr__(attr, val)
        else:
            if attr in self._dct and isinstance(self._dct[attr], Immutable):
                raise Exception("Cannot assign to an immutable attribute: "+str(attr))
            elif isinstance(val, list):
                self._dct[attr] = ListProxy(val)
            elif isinstance(val, dict):
                self._dct[attr] = DictProxy(val)
            elif asyncio.iscoroutine(val) or isinstance(val, asyncio.Future):
                val = asyncio.ensure_future(val)

                def set_later(future_val, attr=attr):
                    setattr(self, attr, future_val.result())

                val.add_done_callback(set_later)
            else:
                self._dct[attr] = val

    def __delattr__(self, attr):
        if attr.startswith('_'):
            super().__delattr__(attr)
        else:
            del self._dct[attr]

    def __repr__(self):
        return repr(self._dct)

    def __str__(self):
        return str(self._dct)

    def _get(self, name):
        if name in self._dct:
            ret = self._dct[name]
            if isinstance(ret, Immutable):
                return ret.value
            return ret
        if isinstance(self._base, Context):
            return self._base._get(name)
        return self._base[name]

    def _set(self, name, val):
        if name in self._dct and isinstance(self._dct[name], Immutable):
            raise Exception("Cannot assign to an immutable attribute: "+str(name))
        if isinstance(val, list):
            self._dct[name] = ListProxy(val)
        elif isinstance(val, dict):
            self._dct[name] = DictProxy(val)
        else:
            self._dct[name] = val

    def _clear(self):
        self._dct.clear()

    def _save(self, name):
        """ If the identifier @name is present, saves its value on
            the saved stack """
        if name not in self._dct:
            return
        if name not in self._saved:
            self._saved[name] = []
        self._saved[name].append(self._dct[name])

    def _restore(self, name):
        """ If the identifier @name is present in the saved stack
            restores its value to the last value on the saved stack."""
        if name in self._saved:
            self._dct[name] = self._saved[name].pop()
            if len(self._saved[name]) == 0:
                del self._saved[name]
