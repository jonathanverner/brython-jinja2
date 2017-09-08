"""
    This module provides the :class:`InterpolatedStr` class which
    can be used to interpolate complex strings with multiple
    instances of ``{{ }}``-type circular expressions.
"""
from .utils.events import EventMixin
from .expression import parse_interpolated_str, ConstNode



class InterpolatedStr(EventMixin):
    """
        The :class:`InterpolatedStr` manages string interpolations.
        Use it as follows:

        ```
            from brython_jinja2.context import Context
            from brython_jinja2.interpolatedstr import InterpolatedStr

            c = context()
            istr = InterpolatedStr("Hello {{name}}, {{surname}}!")
            assert istr.value == "Hello , !"
            c.name = "John"
            assert istr.value == "Hello John, !"
            c.name = "Smith"
            assert istr.value == "Hello John, Smith!"
        ```

        The class tries to do some clever tricks to only evaluate the
        subexpressions which have changed due to a given context change.
        (e.g. c.name='Anne' would not affect the second expresssion in
        the above example).

    """

    def __init__(self, string, start='{{', end='}}', stop_strs=[]):
        super().__init__()
        if isinstance(string, InterpolatedStr):
            # pylint: disable=protected-access; we are cloning ourselves, we have access to protected variables
            self._src = string._src
            self.asts = []
            for ast in string.asts:
                self.asts.append(ast.clone())
        else:
            self._src, self.asts = parse_interpolated_str(string, start=start, end=end, stop_strs=stop_strs)

        for ast_index in range(len(self.asts)):
            self.asts[ast_index].bind('change', lambda event, ast_index=ast_index: self._change_chandler(event, ast_index))

        self._dirty = True
        self._dirty_vals = True
        self._cached_vals = []
        self._cached_val = ""
        self.evaluate()

    def is_const(self):
        for a in self.asts:
            if not a.is_const():
                return False
        return True
    
    def bind_ctx(self, context):
        for ast in self.asts:
            ast.bind_ctx(context)
        self._dirty = True
        self._cached_val = ""

    def clone(self):
        return InterpolatedStr(self)
    
    def get_ast(self, n, strip_str=True):
        if not strip_str:
            return self.asts[n]
        else:
            return self.asts[n]._rarg._children[0]
        

    def _change_chandler(self, event, ast_index):
        if not self._dirty_vals:
            if 'value' in event.data:
                self._cached_vals[ast_index] = event.data['value']
            else:
                self._dirty_vals = True
        if self._dirty:
            return
        self._dirty = True
        self.emit('change', {})

    @property
    def value(self):
        if self._dirty:
            if self._dirty_vals:
                self.evaluate()
            else:
                self._cached_val = "".join(self._cached_vals)
        return self._cached_val

    def evaluate(self):
        self._cached_val = ""
        self._cached_vals = []
        for ast in self.asts:
            try:
                self._cached_vals.append(ast.eval())
                # pylint: disable=bare-except; interpolated str must handle any exceptions when evaluating circular expressions
            except:
                self._cached_vals.append("")
        self._cached_val = "".join(self._cached_vals)
        self._dirty = False
        
    def rstrip(self):
        ret = self.clone()
        if ret.asts:
            node = self.get_ast(-1, strip_str=True)
            if isinstance(node, ConstNode):
                node._cached_val = node._cached_val.rstrip()
        return ret
    
    def __str__(self):
        if self._dirty:
            return "InterpolatedStr("+self._src+")[=dirty:"+self.value+"]"
        else:
            return "InterpolatedStr("+self._src+")[="+self.value+"]"
