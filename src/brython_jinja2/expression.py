"""
    Parse (most) python expressions into an AST

    Notable differences:

      - chaining bool operators, e.g. ``1 <= 2 < 3`` is not supported

      - Tuples are not supported

      - dict constants are not supported
"""
# pylint: disable=line-too-long; contains long conditionals which look bad when split on multiple lines
# pylint: disable=protected-access; pylint doesn't allow descendants to use parent's protected variables.
#                                   here they are used extensively by descendants of the ExpNode class.

from .context import Context
from .exceptions import ExpressionError, ExpressionSyntaxError, NoSolution, SkipSubtree
from .platform import typing
from .platform.typing import List, Dict, Optional, Tuple, Iterator, Union, NewType, cast, Any, Iterable, Callable, TypeVar
from .utils.events import EventMixin
from .utils.observer import observe
from .utils.functools import invertible, invert, self_generator
from .utils import parser_utils as utils


ET_EXPRESSION = 0
ET_INTERPOLATED_STRING = 1

TokenT = NewType('TokenT', int)

T_SPACE = TokenT(0)
T_NUMBER = TokenT(1)            # A number immediately preceded by '-' is a negative number, the '-' is not taken as an operator, so 10-11 is not a valid expression
T_LBRACKET = TokenT(2)
T_RBRACKET = TokenT(3)
T_LPAREN = TokenT(4)
T_RPAREN = TokenT(5)
T_LBRACE = TokenT(6)
T_RBRACE = TokenT(7)
T_DOT = TokenT(8)
T_COMMA = TokenT(9)
T_COLON = TokenT(10)
T_OPERATOR = TokenT(11)
T_STRING = TokenT(12)           # Started by " or '; there is NO distinction between backslash escaping between the two; """,''' and modifiers (e.g. r,b) not implemented"
T_IDENTIFIER = TokenT(13)       # Including True, False, None, an identifier starts by alphabetical character and is followed by alphanumeric characters and/or _$
T_LBRACKET_INDEX = TokenT(14)   # Bracket starting a list slice
T_LBRACKET_LIST = TokenT(15)    # Bracket starting a list
T_LPAREN_FUNCTION = TokenT(16)  # Parenthesis starting a function call
T_LPAREN_EXPR = TokenT(17)      # Parenthesis starting a subexpression
T_EQUAL = TokenT(18)
T_KEYWORD = TokenT(19)          # Warning: This does not include True,False,None; these fall in the T_IDENTIFIER category, also this includes 'in' which can, in certain context, be an operator
T_UNKNOWN = TokenT(20)

OP_PRIORITY = {
    '(': -2,    # Parenthesis have lowest priority so that we always stop partial evaluation when
                #  reaching a parenthesis
    '==': 0,
    'and': 0,
    'or': 0,
    'is': 0,
    'is not': 0,
    'in': 0,
    'not': 1,   # not has higher priority then other boolean operations so that 'a and not b' is interpreted as 'a and (not b)'
    '+': 2,
    '-': 2,
    '*': 3,
    '/': 3,
    '//': 3,
    '%': 3,
    '-unary': 4,
    '**': 4,
    '[]':  5,    # Array slicing/indexing
    '()': 5,    # Function calling
    '.': 5      # Attribute access has highest priority (e.g. a.c**2 is not a.(c**2), and a.func(b) is not a.(func(b)))
}


def token_type(start_chars: str) -> TokenT:
    """ Identifies the next token type based on the next four characters """
    # pylint: disable=too-many-boolean-expressions
    # pylint: disable=too-many-return-statements
    # pylint: disable=too-many-branches
    first_char = start_chars[0]
    if first_char == ' ' or first_char == "\t" or first_char == "\n":
        return T_SPACE
    elif first_char == '[':
        return T_LBRACKET
    elif first_char == ']':
        return T_RBRACKET
    elif first_char == '(':
        return T_LPAREN
    elif first_char == ')':
        return T_RPAREN
    elif first_char == '{':
        return T_LBRACE
    elif first_char == '}':
        return T_RBRACE
    elif first_char == '.':
        return T_DOT
    elif first_char == ',':
        return T_COMMA
    elif first_char == ':':
        return T_COLON
    elif first_char == '=' and start_chars[1] != '=':
        return T_EQUAL
    elif first_char == "'" or first_char == '"':
        return T_STRING
    first_ord = ord(first_char)
    if first_ord >= 48 and first_ord <= 57:
        return T_NUMBER
    len_start = len(start_chars)
    if len_start >= 2:
        twochars = start_chars[:2]
        if first_char in "-+*/<>%" or twochars in ['==', '!=', '<=', '>=']:
            return T_OPERATOR
        if len_start >= 3:
            char_ord = ord(start_chars[2])
            if (twochars == 'or' or twochars == 'is') and (
                    char_ord > 122 or char_ord < 65 or char_ord == 91):
                return T_OPERATOR
            elif (twochars == 'in' or twochars == 'if') and (char_ord > 122 or char_ord < 65 or char_ord == 91):
                return T_KEYWORD
            if len_start >= 4:
                char_ord = ord(start_chars[3])
                threechars = start_chars[:3]
                if (threechars == 'and' or threechars == 'not') and (char_ord > 122 or char_ord < 65 or char_ord == 91):
                    return T_OPERATOR
                elif (threechars == 'for') and (char_ord > 122 or char_ord < 65 or char_ord == 91):
                    return T_KEYWORD
    if (first_ord >= 65 and first_ord <= 90) or (first_ord >= 97 and first_ord <= 122) or first_char == '_' or first_char == '$':
        return T_IDENTIFIER
    else:
        return T_UNKNOWN


def parse_number(expr: str, pos: int) -> Tuple[float, int]:
    """ Parses a number """
    # pylint: disable=too-many-nested-blocks
    if expr[pos] == '-':
        negative = True
        pos = pos + 1
    else:
        negative = False
    ret = int(expr[pos]) # type: float
    pos = pos + 1
    decimal_part = True
    div = 10
    while pos < len(expr) and ((expr[pos] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) or (decimal_part and expr[pos] == '.')):
        if expr[pos] == '.':
            decimal_part = False
        else:
            if decimal_part:
                ret *= 10
                ret += int(expr[pos])
            else:
                ret += int(expr[pos]) / div
                div = div * 10
        pos = pos + 1
    if negative:
        return -ret, pos
    else:
        return ret, pos


def parse_string(expr: str, pos: int) -> Tuple[str, int]:
    """ Parses a string, properly interpretting backslashes. """
    end_quote = expr[pos]
    backslash = False
    ret = ""
    pos = pos + 1
    while pos < len(expr) and (backslash or expr[pos] != end_quote):
        if not backslash:
            if expr[pos] == '\\':
                backslash = True
            else:
                ret += expr[pos]
        else:
            if expr[pos] == '\\':
                ret += '\\'
            elif expr[pos] == '"':
                ret += '"'
            elif expr[pos] == "'":
                ret += "'"
            elif expr[pos] == "n":
                ret += "\n"
            elif expr[pos] == "r":
                ret += "\r"
            elif expr[pos] == "t":
                ret += "\t"
            backslash = False
        pos = pos + 1
    if pos >= len(expr):
        raise ExpressionSyntaxError("String is missing end quote: " + end_quote, src=expr, location=pos)
    return ret, pos + 1


def parse_identifier(expr: str, pos: int):
    """
        Parses an identifier. Which should match /[a-z_$0-9]/i
    """
    ret = expr[pos]
    pos = pos + 1
    while pos < len(expr):
        char_ord = ord(expr[pos])
        if not ((char_ord >= 48 and char_ord <= 57) or (char_ord >= 65 and char_ord <= 90) or (char_ord >= 97 and char_ord <= 122) or char_ord == 36 or char_ord == 95):
            break
        ret += expr[pos]
        pos = pos + 1
    return ret, pos


class _TokenStream(Iterable[Tuple[TokenT, Any, int]]):
    def __init__(self, expr):
        self._src = expr
        self._src_pos = 0
        self._generator = _tokenize(self, expr)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._generator)

    next = __next__

    def send(self, value):
        return self._generator.send(value)


def tokenize(expr: str) -> _TokenStream:
    return _TokenStream(expr)

def _tokenize(self, expr: str) -> Iterator[Tuple[TokenT, Any, int]]:
    """
        A generator which takes a string and converts it to a
        stream of tokens, yielding the triples (token, its value, next position in the string)
        one by one.
    """
    # pylint: disable=too-many-branches; python doesn't have a switch statement
    # pylint: disable=too-many-statements; the length is just due to the many token types

    self._src = expr
    pos = 0
    while pos < len(expr):
        self._src_pos = pos
        tokentype = token_type(expr[pos:pos + 4])
        if tokentype == T_SPACE:
            pos = pos + 1
        elif tokentype == T_NUMBER:
            number, pos = parse_number(expr, pos)
            yield (T_NUMBER, number, pos)
        elif tokentype == T_STRING:
            string, pos = parse_string(expr, pos)
            yield (T_STRING, string, pos)
        elif tokentype == T_IDENTIFIER:
            identifier, pos = parse_identifier(expr, pos)
            yield (T_IDENTIFIER, identifier, pos)
        elif tokentype == T_OPERATOR:
            if expr[pos] == '*' and pos+1 < len(expr) and expr[pos+1] == '*':
                yield (T_OPERATOR, '**', pos+2)
                pos = pos + 2
            elif expr[pos] == '/' and pos + 1 < len(expr) and expr[pos + 1] == '/':
                yield (T_OPERATOR, '//', pos + 2)
                pos = pos + 2
            elif expr[pos] == '=' and pos + 1 < len(expr) and expr[pos + 1] == '=':
                yield (T_OPERATOR, '==', pos + 2)
                pos = pos + 2
            elif expr[pos] == '<' and pos + 1 < len(expr) and expr[pos + 1] == '=':
                yield (T_OPERATOR, '<=', pos + 2)
                pos = pos + 2
            elif expr[pos] == '>' and pos + 1 < len(expr) and expr[pos + 1] == '=':
                yield (T_OPERATOR, '>=', pos + 2)
                pos = pos + 2
            elif expr[pos] == '!':
                yield (T_OPERATOR, '!=', pos + 2)
                pos = pos + 2
            elif expr[pos] == 'o':
                yield (T_OPERATOR, 'or', pos + 2)
                pos = pos + 2
            elif expr[pos] == 'i' and expr[pos + 1] == 's':
                npos = pos + 2
                len_expr = len(expr)
                while npos < len_expr and expr[npos] == ' ' or expr[npos] == '\t' or expr[npos] == '\n':
                    npos += 1
                if expr[npos:npos + 3] == 'not':
                    if npos + 3 > len_expr:
                        yield (T_OPERATOR, 'is not', npos + 3)
                        pos = npos + 3
                    else:
                        char_ord = ord(expr[npos + 3])
                        if (char_ord < 48 or char_ord > 57) and (char_ord < 65 or char_ord > 90) and (char_ord < 97 or char_ord > 122):
                            yield (T_OPERATOR, 'is not', npos + 3)
                            pos = npos + 3
                        else:
                            yield (T_OPERATOR, 'is', pos + 2)
                            pos = pos + 2
                else:
                    yield (T_OPERATOR, 'is', pos + 2)
                    pos = pos + 2
            elif expr[pos] == 'a':
                yield (T_OPERATOR, 'and', pos + 3)
                pos = pos + 3
            elif expr[pos] == 'n':
                yield (T_OPERATOR, 'not', pos + 3)
                pos = pos + 3
            else:
                yield (T_OPERATOR, expr[pos], pos + 1)
                pos = pos + 1
        elif tokentype == T_KEYWORD:
            if expr[pos] == 'f':
                yield (tokentype, 'for', pos + 3)
                pos += 3
            elif expr[pos + 1] == 'f':
                yield (tokentype, 'if', pos + 2)
                pos += 2
            else:
                yield (tokentype, 'in', pos + 2)
                pos += 2
        else:
            yield (tokentype, expr[pos], pos + 1)
            pos = pos + 1


T = TypeVar('T', bound='ExpNode')
class ExpNode(EventMixin):
    """ Base class for nodes in the AST tree """

    def __init__(self):
        super().__init__()

        # True if the value is known to be defined
        self.defined = False

        # The cached value of the expression.
        self._cached_val = None

        # The context to which the node is bound
        self._ctx = None

        # If true, the cached_calue value of is possibly stale.
        # Note that the node should never set its dirty bit to
        # False if it isn't sure that no subexpression is marked
        # as dirty. In particular, if a change event arrives
        # from a subexpression without a value, the dirty bit
        # should be set to True and only reset to False on a
        # subsequent call to evaluate.
        self._dirty = True

    def _visit(self, visitor, results):
        """
            Calls the function visitor with the `results` list as the first argument and
            the current node as the second argument. The return value, if not None, is paired
            with the current node and appended to the `results` list. Then it iteratively
            does the same for each of its children.

            If the visitor raises StopIteration, the whole process is stopped. If the visitor
            raises the SkipSubTree exception, the children of this node are not visited.

            The base implementation in ExpNode returns True, if children should be visited
            and False otherwise (e.g. if the visitor raised the `SkipSubTree` exception)
        """
        try:
            ret = visitor(results, self)
        except SkipSubtree:
            return False
        if ret is not None:
            results.append((self, ret))
        return True

    def is_const(self, assume_const=[]):
        """
            Returns true if the subexpression rooted at this node has constant value (i.e. independent of the context).
            If assume_const is nonempty, it is a list of ExpressionNodes which are assumed to be const.
        """
        return True

    def solve(self, val, x: 'ExpNode') -> None:
        """
            Tries to assign a value to x so that the subexpression rooted at this node evaluates to val.
        """
        if self._ctx is None:
            raise ExpressionError("Cannot solve without a context", src=str(self))
        raise NoSolution(self, val, x)

    @property
    def mutable(self):
        """
            Returns true if the value of the expression (as evaluated in the context to which it is bound) is mutable.
        """
        if not self._ctx:
            raise ExpressionError("Mutable_val makes sense only for bound expressions.", src=str(self))
        return False

    def simplify(self, assume_const=[]):
        """
            Simplifies the subexpression rooted at this node by evaluating nodes which are const (i.e. `is_const` is true)
            modulo the list assume_const and replacing them with the resulting values.
        """
        return self.clone()

    def eval(self, force_cache_refresh=False):
        """
            Evaluates the node looking up identifiers the context to which it was bound
            by the :func:`bind` method and returns the value.

            Note:
                If the function is passed `force_cache_refresh=False` the method does nothing if a known good
                cached value exists. Otherwise the value is recomputed even if a known good value is cached.

            Note:
                The method will update the cached value and the cache status to good.

            Note:
                The method can throw; in this case, the value will be undefined
        """
        raise NotImplementedError

    def evalctx(self, context: Context):
        """
            Evaluates the node looking up identifiers the context `context`. This method
            ignores any context previously set by the :func:`bind` method and also does
            not update the cache or cache status.

            Note: The method may throw (e.g. KeyError, AttrAcessError, ...)
        """
        raise NotImplementedError

    @property
    def cache_status(self):
        """
            Returns True, if the cache is good, otherwise returns False
        """
        return not self._dirty

    @property
    def value(self):
        """
            The value of the expression.

            Note: Until a context is bound to the expression, the value returns None.
            Note: Always returns the cached value. If you want to refresh the cache,
            call evaluate with `force_cache_refresh=True`.

            Note: The function wraps the eval code in a try-catch block so it does
            not raise an exception.
        """
        if self._dirty:
            try:
                self._cached_val = self.eval()
                # pylint: disable=bare-except; function must not raise an exception!
            except:
                pass
        return self._cached_val

    @value.setter
    def value(self, val):
        """
            Computes the expression and assigns value to the result.
            E.g. if the expression is `ob[1]` and `ctx` is
            `{ob:[1,2,3,4]}` then `_assign(ctx,20)`
            executes `ctx.ob[1]=20`.

            Note: The methods in general assume that the assignment
            succeeds, i.e. that a next call to evaluate should return
            `val`. In particular, the _assign caches the
            value `val` without actually computing the value of the
            expression.
        """
        self._assign(val)
        self._cached_val = val
        if self._dirty:
            self._dirty = False
        else:
            self.emit('change', {'value': self._cached_val})

    def _assign(self, _val):
        raise ExpressionError("Assigning to " + str(self) + " not supported")

    def bind_ctx(self, ctx: Context):
        """
            Binds the node to the context `ctx` and starts watching the context for changes.
            When a change happens, it emits a `change` event. If the new value is known,
            it is passed as the `value` field of `event.data`.

            Note: Any changes to an expression which is defined and does not have a
            good cached value (cache_status is False) will not fire a change event.
        """
        self._ctx = ctx

    def clone(self: T) -> T:
        """
            Returns a clone of this node which can bind a diffrent context.
        """
        raise NotImplementedError

    def is_function_call(self):
        """
            Returns true if the expression is a function call.
        """
        # pylint: disable=no-member; since we explicitely check that we are an OpNode, we can access ``_opstr``
        return isinstance(self, OpNode) and self._opstr == '()'

    def is_assignable(self):
        """
            Returns true if the expression value can be assigned to.

            (alias of the mutable property)
        """
        return self.mutable

    def _change_handler(self, _event):
        if self._dirty and self.defined:
            return
        self._dirty = True
        self.emit('change', {})

    def __repr__(self):
        return "<AST Node>"


    def equiv(self, other: 'ExpNode', assume_equal=[]):
        """
            Returns True if the subexpression rooted at the current node is always equal (regardless of the context)
            to the expression other if we assume that the identifiers in assume_equal are equal
        """
        return self == other

    def contains(self, exp: 'ExpNode'):
        """
            Returns true if the exp is a subexpression of the expression rooted at the current node.
        """
        return self.equiv(exp)

    def __eq__(self, other):
        return False


class ConstNode(ExpNode):
    """ Node representing a string or number constant """

    def __init__(self, val: Union[float, str]) -> None:
        super().__init__()
        self._dirty = False
        self._cached_val = val

    def is_const(self, assume_const=[]):
        return True

    def name(self):
        return self._cached_val

    def eval(self, force_cache_refresh=False):
        return self._cached_val

    def evalctx(self, context: Context):
        return self._cached_val

    def clone(self) -> 'ConstNode':
        # Const Nodes can't change, so clones can be identical
        return self

    def __repr__(self):
        return repr(self._cached_val)

    def __eq__(self, other):
        return type(self) == type(other) and self._cached_val == other._cached_val


class IdentNode(ExpNode):
    """ Node representing an identifier or one of the predefined constants True, False, None, str, int, len.
        (we don't allow overriding str, int and len)
    """
    CONSTANTS = {
        'True': True,
        'False': False,
        'None': None,
        'str': str,
        'int': int,
        'len': len
    }
    BUILTINS = {
        'str': str,
        'int': int,
        'len': len
    }

    def __init__(self, identifier: str) -> None:
        super().__init__()
        self._ident = identifier
        if self._ident in self.CONSTANTS:
            self._const = True
            self._cached_val = self.CONSTANTS[self._ident]
            self._defined = True
            self._dirty = False
            self._value_observer = None
            self._ctx_observer = None
        else:
            self._const = False

    @property
    def mutable(self):
        if self._const:
            return False
        if self._ctx is None:
            return True
        return self._ident not in self._ctx.immutable_attrs

    def is_const(self, assume_const=[]):
        if self._const:
            return True
        else:
            return self._ident in [e._ident for e in assume_const if isinstance(e, IdentNode)]

    def solve(self, value, x):
        if self._const:
            raise NoSolution(self, value, x)
        if self.equiv(x):
            self._assign(value)


    def simplify(self, assume_const=[]):
        if self.is_const(assume_const):
            return ConstNode(self.eval())
        else:
            return self.clone()

    def name(self):
        return self._ident

    def clone(self) -> 'IdentNode':
        if self._const:
            return self
        else:
            return IdentNode(self._ident)

    def bind_ctx(self, context):
        super().bind_ctx(context)
        if not self._const:
            self._ctx_observer = observe(self._ctx)
            self._ctx_observer.bind('change', self._context_change)
            self._value_observer = observe(self.value, ignore_errors=True)
            if self._value_observer:
                self._value_observer.bind('change', self._value_change)

    def eval(self, force_cache_refresh=False):
        if not self._const:
            self.defined = False
            if self._dirty or force_cache_refresh:
                try:
                    self._cached_val = self._ctx._get(self._ident)
                except KeyError:
                    self._cached_val = self.BUILTINS[self._ident]
                self._dirty = False
            self.defined = True
        return self._cached_val

    def evalctx(self, context):
        if not self._const:
            try:
                return context._get(self._ident)
            except KeyError:
                return self.BUILTINS[self._ident]
        else:
            return self._cached_val

    def _assign(self, value):
        if self._const:
            raise ExpressionError("Cannot assign '"+str(value)+"' to the constant" + str(self._cached_val))
        else:
            setattr(self._ctx, self._ident, value)

    def _context_change(self, event):
        if self._dirty and self.defined:
            return
        if event.data['key'] == self._ident:
            if self._value_observer:
                self._value_observer.unbind()
            if 'value' in event.data['key']:
                self._cached_val = event.data['value']
                self._value_observer = observe(self._cached_val, ignore_errors=True)
                if self._value_observer:
                    self._value_observer.bind('change', self._value_change)
                self.defined = True
                self._dirty = False
                self.emit('change', {'value': self._cached_val})
            else:
                self.defined = False
                self._dirty = True
                self.emit('change', {})

    def _value_change(self, event):
        if self._dirty and self.defined:
            return
        self._dirty = True
        if 'value' in event.data:
            self.emit('change', {'value': self._cached_val})
        elif event.data['type'] in ['sort', 'reverse']:
            self.emit('change', {})
        else:
            self.defined = False
            self._dirty = True
            self.emit('change', {})

    def __repr__(self):
        return self.name()

    def __eq__(self, other):
        return type(self) == type(other) and self._ident == other._ident


class MultiChildNode(ExpNode):
    """
        Common base class for nodes which have multiple child nodes.
    """

    def __init__(self, children):
        super().__init__()
        self._children = children
        self._cached_vals = []
        self._dirty_children = True
        for ch_index in range(len(self._children)):
            child = self._children[ch_index]
            if child is not None:
                child.bind('change', lambda event, chi=ch_index: self._child_changed(event, chi))

    def _visit(self, visitor, results):
        if super()._visit(visitor, results):
            for ch in self._children:
                ch._visit(visitor, results)
            return True
        else:
            return False

    def is_const(self, assume_const=[]):
        for ch in self._children:
            if ch is not None and not ch.is_const(assume_const):
                return False
        return True

    def simplify(self, assume_const=[]):
        """
            Since MultiChildNode is an abstract node which is never instantiated,
            the simplify method doesn't return a simplified node but a list of simplified
            children so that it can be used by subclasses. The only exception is if
            all of the children simplify to a const expression, in which case a ConstNode
            holding the list of evaluated children is returned.
        """
        simplified_children = []
        all_const = True
        for ch in self._children:
            if ch is not None:
                sch = ch.simplify(assume_const)
                if not sch.is_const(assume_const):
                    all_const = False
                simplified_children.append(sch)
            else:
                simplified_children.append(None)
        if all_const:
            return ConstNode([sch.eval() for ch in simplified_children])
        else:
            return simplified_children

    def clone(self) -> List[ExpNode]: # type: ignore
        """
            Since MultiChildNode is an abstract node which is never instantiated,
            the clone method doesn't return the MultiChildNode but a list of cloned
            children so that it can be used by subclasses.
        """
        clones = []
        for child in self._children:
            if child is not None:
                clones.append(child.clone())
            else:
                clones.append(None)
        return clones

    def eval(self, force_cache_refresh=False):
        #    As an exception, this method does not set the _cached_val
        #    variable, since it would otherwise clobber the values set in
        #    the classes deriving from MultiChildNode.
        if self._dirty_children or force_cache_refresh:
            self.defined = False
            self._cached_vals = []
            for child in self._children:
                if child is not None:
                    self._cached_vals.append(child.eval(force_cache_refresh=force_cache_refresh))
                else:
                    self._cached_vals.append(None)
            self._dirty = False
            self._dirty_children = False
            self.defined = True
            return self._cached_vals
        else:
            return self._cached_vals

    def evalctx(self, context):
        ret = []
        for child in self._children:
            if child is not None:
                ret.append(child.evalctx(context))
            else:
                ret.append(None)
        return ret

    def bind_ctx(self, context):
        super().bind_ctx(context)
        for child in self._children:
            if child is not None:
                child.bind_ctx(context)

    def _child_changed(self, event, child_index):
        if self._dirty_children and self.defined:
            return
        if 'value' in event.data:
            self._cached_vals[child_index] = event.data['value']
        else:
            self._dirty_children = True
        if not self._dirty or not self.defined:
            self._dirty = True
            self.emit('change')

    def contains(self, exp):
        for ch in self._children:
            if ch.contains(exp):
                return True
        return self.equiv(exp)

    def __eq__(self, other):
        if not type(other) == type(self):
            return False
        if len(self._children) != len(other._children):
            return False
        for s_ch, o_ch in zip(self._children, other._children):
            if s_ch != o_ch:
                return False
        return True


class ListNode(MultiChildNode):
    """ Node representing a list constant, e.g. [1,2,"ahoj",3,None] """

    def __init__(self, lst):
        super().__init__(lst)

    # This class does not have an eval method of its own.
    # This means that, temporarily, the `_cached_val` need not
    # reflect the real cached value, which is stored in
    # `_cached_vals`. The `_cached_val` attribute is updated
    # by the parent value getter when it is called.
    def clone(self):
        return ListNode(super().clone())

    def simplify(self, assume_const=[]):
        simplified_children = super().simplify(assume_const)
        if isinstance(simplified_children, ConstNode):
            return simplified_children
        else:
            return ListNode(simplified_children)

    def solve(self, val, x):
        if not isinstance(val, list) or len(self._children) != len(val):
            raise NoSolution(self, val, x)

        solve_val = None
        solve_exp = None
        for index, ch in enumerate(self._children):
            if ch.contains(x):
                if solve_exp is not None:
                    raise NoSolution(self, val, x)
                else:
                    solve_exp = ch
                    solve_val = val[index]
        if solve_exp is None:
            raise NoSolution(self, val, x)
        solve_exp.solve(solve_val, x)

    def __repr__(self):
        return repr(self._children)


class FuncArgsNode(MultiChildNode):
    """ Node representing the arguments to a function """

    def __init__(self, args, kwargs):
        super().__init__(args)
        self._kwargs = kwargs
        self._cached_kwargs = {}
        self._dirty_kwargs = False
        for (kwarg, val) in self._kwargs.items():
            val.bind('change', lambda event, arg=kwarg: self._kwarg_change(event, arg))

    def _visit(self, visitor, results):
        if super()._visit(visitor, results):
            for ch in self._kwargs:
                ch._visit(visitor, results)

    def clone(self):
        cloned_args = super().clone()
        cloned_kwargs = {}
        for (arg, val) in self._kwargs.items():
            cloned_kwargs[arg] = val.clone()
        return FuncArgsNode(cloned_args, cloned_kwargs)

    def is_const(self, assume_const=[]):
        if not super().is_const(assume_const):
            return False
        for kwarg in self._kwargs.values():
            if not kwarg.is_const(assume_const):
                return False
        return True

    def simplify(self, assume_const=[]):
        s_args = super().simplify(assume_const)
        s_kwargs = {}
        all_kwargs_const = True
        for (k,v) in self._kwargs.items():
            sv = v.simplify(assume_const)
            s_kwargs[k] = sv
            if not sv.is_const():
                all_kwargs_const = False
        if isinstance(s_args, ConstNode):
            if all_kwargs_const:
                return ConstFuncArgsNode(s_args.eval(), { k:v.eval() for k,v in s_kwargs.items() })
            else:
                return FuncArgsNode([ConstNode(arg) for arg in s_args.eval()], s_kwargs)
        else:
            return FuncArgsNode(s_args, s_kwargs)

    def eval(self, force_cache_refresh=False):
        args = super().eval(force_cache_refresh=force_cache_refresh)
        if self._dirty_kwargs or force_cache_refresh:
            self._cached_kwargs = {}
            for (arg, val) in self._kwargs.items():
                self._cached_kwargs[arg] = val.eval(
                    force_cache_refresh=force_cache_refresh)
        self._cached_val = args, self._cached_kwargs
        self.defined = True
        self._dirty_kwargs = False
        self._dirty = False
        return self._cached_val

    def evalctx(self, context):
        args = super().evalctx(context)
        kwargs = {}
        for (arg, val) in self._kwargs.items():
            kwargs[arg] = val.evalctx(context)
        return args, kwargs

    def bind_ctx(self, context):
        super().bind_ctx(context)
        for kwarg in self._kwargs.values():
            kwarg.bind_ctx(context)

    def _kwarg_change(self, event, arg):
        if self._dirty_kwargs and self.defined:
            return
        if 'value' in event.data:
            self._cached_kwargs[arg] = event.data['value']
        else:
            self._dirty_kwargs = True
        if not self._dirty or not self.defined:
            self._dirty = True
            self.emit('change')

    def contains(self, exp):
        if super().contains(exp):
            return True
        for (kwarg, val) in self._kwargs.items():
            if val.contains(exp):
                return True
        return self.equiv(exp)

    def __repr__(self):
        return ','.join([repr(child) for child in self._children] +
                        [arg + '=' + repr(val) for (arg, val) in self._kwargs.items()])

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        D = set(other._kwargs.keys()).difference(self._kwargs.keys())
        if not D.empty():
            return False
        for kwarg, val in self._kwargs.items():
            if kwarg not in other._kwargs or val != other._kwargs[kwarg]:
                return False
        return True


class ConstFuncArgsNode(ExpNode):
    def __init__(self, args, kwargs):
        self._args =  args
        self._kwargs = kwargs

    def clone(self):
        return ConstFuncArgsNode(self._args, self._kwargs)

    def is_const(self, assume_const=[]):
        return True

    def eval(self, force_cache_refresh=False):
        return self._args, self._kwargs

    def evalctx(self, context):
        return self.eval()

    def bind_ctx(self, ctx):
        self._ctx = ctx

    def __repr__(self):
        return ','.join([repr(arg) for arg in self._args] +
                        [arg + '=' + repr(val) for (arg, val) in self._kwargs.items()])

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        for sa, oa in zip(self._args, other._args):
            if sa != oa:
                return False
        D = set(other._kwargs.keys()).difference(self._kwargs.keys())
        if not D.empty():
            return False
        for k, v in self._kwargs.keys():
            if k not in other._kwargs or other._kwargs[k] != v:
                return False
        return False


class ListSliceNode(MultiChildNode):
    """ Node representing a slice or an index """

    def __init__(self, is_slice, start, end, step):
        super().__init__([start, end, step])
        self._slice = is_slice

    def simplify(self, assume_const=[]):
        if self._slice:
            args = super().simplify(assume_const)
            if isinstance(args, ConstNode):
                return ConstNode(slice(*args.eval()))
            else:
                return ListSliceNode(self._slice, *args)
        else:
            return self._children[0].simplify(assume_const)

    def clone(self):
        # pylint: disable=unbalanced-tuple-unpacking; we know we are a ListSlice so super().clone will return three children
        start_c, end_c, step_c = super().clone()
        return ListSliceNode(self._slice, start_c, end_c, step_c)

    def eval(self, force_cache_refresh=False):
        if self._dirty or force_cache_refresh:
            self.defined = False
            super().eval(force_cache_refresh=True)
            start, end, step = self._cached_vals
            if self._slice:
                self._cached_val = slice(start, end, step)
            else:
                self._cached_val = start
            self._dirty = False
            self.defined = True
        return self._cached_val

    def evalctx(self, context):
        # pylint: disable=unbalanced-tuple-unpacking; we know we are a ListSlice so super().evalctx will return three children
        start, end, step = super().evalctx(context)
        if self._slice:
            return slice(start, end, step)
        else:
            return start

    def __repr__(self):
        start, end, step = self._children
        if self._slice:
            ret = ''
            if start is None:
                ret = ':'
            else:
                ret = repr(start) + ':'
            if end is not None:
                ret += repr(end)
            if step is not None:
                ret += ':' + repr(step)
            return ret
        else:
            return repr(start)


class AttrAccessNode(ExpNode):
    """ Node representing attribute access, e.g. obj.prop """

    def __init__(self, obj, attribute):
        super().__init__()
        self._obj = obj
        self._attr = attribute
        self._observer = None
        self._obj.bind('change', self._change_handler)

    def _visit(self, visitor, results):
        if super()._visit(visitor, results):
            self._obj._visit(visitor, results)

    def clone(self) -> 'AttrAccessNode':
        return AttrAccessNode(self._obj.clone(), self._attr.clone())

    @property
    def mutable(self):
        if self._ctx is None:
            return True
        else:
            return self._obj.mutable


    def is_const(self, assume_const=[]):
        return self._obj.is_const(assume_const)

    def simplify(self, assume_const=[]):
        s_obj = self._obj.simplify(assume_const)
        if s_obj.is_const():
            return ConstNode(self.eval())
        else:
            return AttrAccessNode(s_obj, self._attr)

    def eval(self, force_cache_refresh=False):
        """
           Note that this function expects the AST of the attr access to
           be rooted at the rightmost element of the attr access chain !!
        """
        if self._dirty or force_cache_refresh:
            self.defined = False
            if self._observer:
                self._observer.unbind()
            obj_val = self._obj.eval(force_cache_refresh=force_cache_refresh)
            self._cached_val = getattr(obj_val, self._attr.name())
            self._observer = observe(self._cached_val, self._change_attr_handler, ignore_errors=True)
            self._dirty = False
            self.defined = True
        return self._cached_val

    def evalctx(self, context: Context):
        """
           Note that this function expects the AST of the attr access to
           be rooted at the rightmost element of the attr access chain !!
        """

        obj_val = self._obj.evalctx(context)
        return getattr(obj_val, self._attr.name())

    def solve(self, val, x: ExpNode):
        if self.equiv(x):
            try:
                self._assign(val)
            except:
                pass
        raise NoSolution(self, val, x)

    def _assign(self, value):
        obj_val = self._obj.eval()
        setattr(obj_val, self._attr.name(), value)
        if self._observer:
            self._observer.unbind()
        self._cached_val = value
        self._observer = observe(self._cached_val, self._change_attr_handler, ignore_errors=True)
        self.defined = True

    def bind_ctx(self, context: Context):
        super().bind_ctx(context)
        if self._observer is not None:
            self._observer.unbind()
        self._obj.bind_ctx(context)

    def _change_attr_handler(self, event):
        """
            Handles changes to the value of the attribute.
        """
        if self._dirty and self.defined:
            return
        if 'value' in event.data:
            self._dirty = True
            self.emit('change', {'value': self._cached_val})
        else:
            self._dirty = True
            self.emit('change', {})

    def contains(self, exp: ExpNode):
        return self._obj.contains(exp) or self.equiv(exp)

    def __repr__(self):
        return repr(self._obj) + '.' + repr(self._attr)

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return self._obj == other._obj and self._attr == other._attr


class ListComprNode(ExpNode):
    """ Node representing comprehension, e.g. [ x+10 for x in lst if x//2 == 0 ] """

    def __init__(self, expr: ExpNode, var: IdentNode, lst: ExpNode, cond: ExpNode) -> None:
        super().__init__()
        self._expr = expr
        self._var = var
        self._lst = lst
        self._cond = cond
        self._expr.bind('change', self._change_handler)
        self._lst.bind('change', self._change_handler)
        if self._cond is not None:
            self._cond.bind('change', self._change_handler)

    def _visit(self, visitor, results):
        if super()._visit(visitor, results):
            self._expr._visit(visitor, results)
            self._lst._visit(visitor, results)
            self._cond._visit(visitor, results)

    def is_const(self, assume_const=[]):
        return self._lst.is_const(assume_const) and self._expr.is_const(assume_const=assume_const+[self._var])

    def simplify(self, assume_const=[]):
        mod_const = [e for e in assume_const if not e.isinstance(IdentNode) or e._ident != self._var.name()]
        s_lst = self._lst.simplify(assume_const)
        if self._cond is not None:
            s_cond = self._cond.simplify(mod_const)
        else:
            s_cond = None
        s_expr = self._expr.simplify(mod_const)

        if s_cond is not None and s_cond.is_const(mod_const):
            if not s_cond.eval():
                return ConstNode([])
            else:
                s_cond = None
        if s_cond is None:
            if s_lst.is_const(assume_const):
                if s_expr.is_const(assume_const=mod_const+[self._var]):
                    return ConstNode(self.eval())
                else:
                    return ListComprNode(s_expr, self._var, s_lst.eval(), None)
            else:
                return ListComprNode(s_expr, self._var, s_lst, None)
        else:
            if s_lst.is_const(assume_const):
                return ListComprNode(s_expr, self._var, s_lst.eval(), s_cond)
            else:
                return ListComprNode(s_expr, self._var, s_lst, s_cond)

    def solve(self, value, x: ExpNode):
        if not isinstance(value, list):
            raise NoSolution(self, value, x)
        pos = 0
        self._ctx._save(self._var.name())
        new_val = []
        for c in self._lst.eval():
            self._ctx._set(self._var.name(), c)
            if self._cond is None or self._cond.eval(force_cache_refresh=True):
                self._expr.solve(value[pos], self._var)
                new_val.append(self._ctx._get(self._var.name()))
            else:
                new_val.append(c)
        self._lst._assign(new_val)

    def clone(self) -> 'ListComprNode':
        expr_c = self._expr.clone()
        var_c = self._var.clone()
        lst_c = self._lst.clone()
        if self._cond is None:
            cond_c = None
        else:
            cond_c = self._cond.clone()
        return ListComprNode(expr_c, var_c, lst_c, cond_c)

    def eval(self, force_cache_refresh=False):
        if self._dirty or force_cache_refresh:
            self.defined = False
            lst = self._lst.eval(force_cache_refresh=force_cache_refresh)
            self._cached_val = []
            var_name = self._var.name()
            self._ctx._save(var_name)
            for elem in lst:
                self._ctx._set(var_name, elem)
                if self._cond is None or self._cond.eval(force_cache_refresh=True):
                    self._cached_val.append(self._expr.eval(force_cache_refresh=True))
            self._ctx._restore(var_name)
            self.defined = True
            self._dirty = False
        return self._cached_val

    def evalctx(self, context: Context):
        lst = self._lst.evalctx(context)
        ret = []
        var_name = self._var.name()
        context._save(var_name)
        for elem in lst:
            context._set(var_name, elem)
            if self._cond is None or self._cond.evalctx(context):
                ret.append(self._expr.evalctx(context))
        context._restore(var_name)
        return ret

    def bind_ctx(self, context: Context):
        super().bind_ctx(context)
        self._lst.bind_ctx(context)
        self._expr.bind_ctx(context)
        if self._cond is not None:
            self._cond.bind_ctx(context)


    def contains(self, exp: ExpNode):
        if self._lst.contains(exp):
            return True
        if self._var.equiv(exp):
            return False
        return self._expr.contains(exp) or self._cond.contains(exp) or self.equiv(exp)

    def __repr__(self):
        if self._cond is None:
            return '[' + repr(self._expr) + ' for ' + \
                repr(self._var) + ' in ' + repr(self._lst) + ']'
        else:
            return '[' + repr(self._expr) + ' for ' + repr(self._var) + \
                ' in ' + repr(self._lst) + ' if ' + repr(self._cond) + ']'

    def __eq__(self, other):
        return type(self) == type(other) and self._var == other._var and self._cond == other._cond and self._expr == other._expr and self._lst == other._lst


class OpNode(ExpNode):
    """ Node representing an operation, e.g. a is None, a**5, a[10], a.b or func(x,y)"""
    UNARY = ['-unary', 'not']
    OPS = {
        '+': lambda x, y: x + y,
        '-': lambda x, y: x - y,
        '-unary': lambda y: -y,
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / y,
        '//': lambda x, y: x // y,
        '%': lambda x, y: x % y,
        '**': lambda x, y: x**y,
        '==': lambda x, y: x == y,
        '!=': lambda x, y: x != y,
        '<': lambda x, y: x < y,
        '>': lambda x, y: x > y,
        '<=': lambda x, y: x <= y,
        '>=': lambda x, y: x >= y,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'not': lambda y: not y,
        'is': lambda x, y: x is y,
        'in': lambda x, y: x in y,
        'is not': lambda x, y: x is not y,
        '[]': lambda x, y: x[y],
        '()': lambda func, args: func(*args[0], **args[1])
    } # type: Dict[str, Callable]

    def __init__(self, operator:str, l_exp: ExpNode, r_exp: ExpNode) -> None:
        super().__init__()
        self._opstr = operator
        self._op = OpNode.OPS[operator]
        self._larg = l_exp
        self._rarg = r_exp
        self._observer = None
        if l_exp is not None:  # The unary operator 'not' does not have a left argument
            l_exp.bind('change', self._change_handler)
        r_exp.bind('change', self._change_handler)

    def _visit(self, visitor, results):
        if super()._visit(visitor, results):
            if self._larg is not None:
                self._larg._visit(visitor, results)
            self._rarg._visit(visitor, results)
    @property
    def mutable(self):
        if self._opstr == '[]':
            return self._larg.mutable and isinstance(self._rarg, ListSliceNode) and not self._rarg._slice
        return False

    def is_const(self, assume_const=[]):
        if self._larg is not None:
            return self._larg.is_const(assume_const) and self._rarg.is_const(assume_const)
        else:
            return self._rarg.is_const(assume_const)

    def simplify(self, assume_const=[]):
        if self._larg is not None:
            s_l = self._larg.simplify(assume_const)
        else:
            s_l = None
        s_r = self._rarg.simplify(assume_const)
        if s_l is None or s_l.is_const(assume_const):
            if s_r.is_const(assume_const):
                return ConstNode(self.eval())
            else:
                return OpNode(self._opstr, s_l, s_r)
        else:
            return OpNode(self._opstr, s_l, s_r)


    def clone(self) -> 'OpNode':
        if self._larg is None:
            l_exp = None
        else:
            l_exp = self._larg.clone()
        r_exp = self._rarg.clone()
        return OpNode(self._opstr, l_exp, r_exp)

    def eval(self, force_cache_refresh=False):
        if self._dirty or force_cache_refresh:
            self.defined = False
            if self._opstr in self.UNARY:
                self._cached_val = self._op(self._rarg.eval(
                    force_cache_refresh=force_cache_refresh))
            else:
                left = self._larg.eval(force_cache_refresh=force_cache_refresh)
                right = self._rarg.eval(force_cache_refresh=force_cache_refresh)
                self._cached_val = self._op(left, right)
            if self._opstr in ['[]', '()']:
                if self._observer is not None:
                    self._observer.unbind()
                self._observer = observe(self._cached_val, ignore_errors=True)
                if self._observer is not None:
                    self._observer.bind('change', self._change_handler)
            self.defined = True
            self._dirty = False
        return self._cached_val

    def evalctx(self, context: Context):
        if self._opstr in self.UNARY:
            return self._op(self._rarg.evalctx(context))
        else:
            return self._op(
                self._larg.evalctx(context),
                self._rarg.evalctx(context))

    def call(self, *inject_args, **inject_kwargs):
        """
            Assuming the node is a function call, call the function
            appending

            :param inject_args: to its arguments and updating
            :type inject_args: tuple

            its kwargs with :param:`inject_kwargs`. Retuns the result
            of the call.
        """
        if self._opstr != '()':
            raise ExpressionError("Calling " + repr(self) + " does not make sense.")
        func = self._larg.eval()
        args, kwargs = self._rarg.eval()
        args_copy = args.copy()
        kwargs_copy = kwargs.copy()
        args_copy.extend(inject_args)
        kwargs_copy.update(inject_kwargs)
        return func(*args_copy, **kwargs_copy)

    def _solve_func(self, val, x):
        func = self._larg.eval()
        if not invertible(func):
            raise NoSolution(self, val, x)
        inverse = invert(func)
        found = 0
        for k, v in self._rarg._kwargs.items():
            if v.contains(x):
                found += 1
                if found > 1:
                    raise NoSolution(self, val, x)
        args, kwargs = self._rarg.eval()
        exp = None
        for k, v in self._rarg._kwargs.items():
            if v.contains(x):
                kwargs[k] = val
                exp = v
        for i, v in enumerate(self._rarg._children):
            if v.contains(x):
                args[i] = val
                exp = v
        exp.solve(inverse(*args, **kwargs), x)

    def _to_number(self, x, val):
        if type(val) in [int, float]:
            return val
        try:
            return int(val)
        except:
            pass
        try:
            return float(val)
        except:
            raise NoSolution(self, val, x)

    def solve(self, val, x: ExpNode):
        if self._opstr == '-unary':
            if not self._rarg.equiv(x):
                raise NoSolution(self, val, x)
            val = self._to_number(x, val)
            return self._rarg.solve(-val, x)
        elif self._opstr == 'not':
            if not self._rarg.equiv(x):
                raise NoSolution(self, val, x)
            return self._rarg.solve(not val, x)
        elif self._opstr == '[]' and self.equiv(x):
            return self._assign(val)
        elif self._opstr == '()':
            return self._solve_func(val, x)
        elif self._opstr == '*':
            val = self._to_number(x, val)
            if not self._larg.contains(x):
                return self._rarg.solve(val/self._larg.value, x)
            elif not self._rarg.contains(x):
                return self._larg.solve(val/self._larg.value, x)
            raise NoSolution(self, val, x)
        elif self._opstr == '-':
            val = self._to_number(x, val)
            if not self._larg.contains(x):
                return self._rarg.solve(val+self._larg.value, x)
            elif not self._rarg.contains(x):
                return self._larg.solve(val+self._larg.value, x)
            raise NoSolution(self, val, x)
        elif self._opstr == '+':
            val = self._to_number(x, val)
            if not self._larg.contains(x):
                return self._rarg.solve(val-self._larg.value, x)
            elif not self._rarg.contains(x):
                return self._larg.solve(val-self._rarg.value, x)
            raise NoSolution(self, val, x)
        else:
            raise NoSolution(self, val, x)

    def _assign(self, value):
        if self._opstr != '[]':
            raise ExpressionError("Assigning to "+repr(self)+" does not make sense.")
        self._larg.value[self._rarg.value] = value
        self.defined = True

    def bind_ctx(self, context: Context):
        super().bind_ctx(context)
        if self._opstr not in self.UNARY:
            self._larg.bind_ctx(context)
        self._rarg.bind_ctx(context)

    def contains(self, exp: ExpNode):
        if self._larg is not None and self._larg.contains(exp):
            return True
        return self._rarg.contains(exp) or self.equiv(exp)

    def __repr__(self):
        if self._opstr == '-unary':
            return '-' + repr(self._rarg)
        elif self._opstr == 'not':
            return '(not ' + repr(self._rarg) + ')'
        elif self._opstr == '[]':
            return repr(self._larg) + '[' + repr(self._rarg) + ']'
        elif self._opstr == '()':
            return repr(self._larg) + '(' + repr(self._rarg) + ')'
        elif self._opstr == '**':
            return repr(self._larg) + '**' + repr(self._rarg)
        else:
            if isinstance(self._larg, OpNode) and OP_PRIORITY[self._larg._opstr] < OP_PRIORITY[self._opstr]:
                l_repr = '('+repr(self._larg)+')'
            else:
                l_repr = repr(self._larg)

            if isinstance(self._rarg, OpNode) and OP_PRIORITY[self._rarg._opstr] <= OP_PRIORITY[self._opstr]:
                r_repr = '('+repr(self._rarg)+')'
            else:
                r_repr = repr(self._rarg)

            return l_repr + ' ' + self._opstr + ' ' + r_repr

    def __eq__(self, other):
        return type(self) == type(other) and self._op == other._op and self._larg == other._larg and self._rarg == other._rarg


def simplify(exp: ExpNode) -> ExpNode:
    if exp._ctx is None:
        return exp.simplify()
    else:
        assume_const = [IdentNode(a) for a in exp._ctx.immutable_attrs]
        return exp.simplify(assume_const)

def partial_eval(arg_stack: List[ExpNode], op_stack, pri=-1, src=None, location=None) -> None:
    """ Partially evaluates the stack, i.e. while the operators in @op_stack have strictly
        higher priority then @pri, they are converted to OpNodes/AttrAccessNodes with
        arguments taken from the @arg_stack. The result is always placed back on the @arg_stack"""
    while len(op_stack) > 0 and pri <= OP_PRIORITY[op_stack[-1][1]]:
        _token, operator = op_stack.pop()
        try:
            arg_r = arg_stack.pop()
            if operator in OpNode.UNARY:
                arg_l = None
            else:
                arg_l = arg_stack.pop()
            if operator == '.':
                arg_stack.append(AttrAccessNode(arg_l, arg_r))
            else:
                arg_stack.append(OpNode(operator, arg_l, arg_r))
        except IndexError:
            raise ExpressionSyntaxError("Not enough arguments for operator '" + operator + "'", src=src, location=location)


def parse_args(token_stream: _TokenStream) -> Tuple[List[ExpNode], Dict[str, ExpNode]]:
    """ Parses function arguments from the stream and returns them as a pair (args, kwargs)
        where the first is a list and the second a dict """
    args = []       # type: List[ExpNode]
    kwargs = {}     # type: Dict[str, ExpNode]
    state = 'args'
    while state == 'args':
        arg, endt, _pos = _parse(token_stream, [T_COMMA, T_EQUAL, T_RPAREN])
        if endt == T_EQUAL:
            state = 'kwargs'
        elif endt == T_RPAREN:
            args.append(arg)
            return args, kwargs
        else:
            args.append(arg)
    if not isinstance(arg, IdentNode):
        raise ExpressionSyntaxError("Invalid keyword argument name: '"+str(arg)+"'", src=token_stream._src, location=token_stream._pos) # type: ignore
    val, endt, _pos = _parse(token_stream, [T_COMMA, T_RPAREN])
    kwargs[arg._ident] = val                                        # type: ignore
    while endt != T_RPAREN:
        arg, endt, _pos = _parse(token_stream, [T_EQUAL])
        val, endt, _pos = _parse(token_stream, [T_COMMA, T_RPAREN])
        if not isinstance(arg, IdentNode):
            raise ExpressionSyntaxError("Invalid keyword argument name: '"+str(arg)+"'", src=token_stream._src, location=token_stream._pos) # type: ignore
        kwargs[arg._ident] = val                                    # type: ignore
    return args, kwargs


def parse_lst(token_stream: _TokenStream) -> Union[ListComprNode, ListNode]:
    """ Parses a list constant or list comprehension from the token_stream
        and returns the appropriate node """
    elem, endt, _pos = _parse(token_stream, [T_RBRACKET, T_COMMA, T_KEYWORD])
    if endt == T_KEYWORD:
        expr = elem
        var, endt, _pos = _parse(token_stream, [T_KEYWORD])
        if not isinstance(var, IdentNode):
            raise ExpressionSyntaxError("Invalid list comprehension variable: '"+str(var)+"'", src=token_stream._src, location=token_stream._pos) # type: ignore
        lst, endt, _pos = _parse(token_stream, [T_KEYWORD, T_RBRACKET])
        if endt == T_KEYWORD:
            cond, endt, _pos = _parse(token_stream, [T_RBRACKET])
        else:
            cond = None
        return ListComprNode(expr, var, lst, cond)
    else:
        elst = [elem]
        while endt != T_RBRACKET:
            elem, endt, _pos = _parse(token_stream, [T_RBRACKET, T_COMMA, T_KEYWORD])
            elst.append(elem)
        return ListNode(elst)


def parse_slice(token_stream: _TokenStream) -> Tuple[bool, ExpNode, ExpNode, ExpNode]:
    """ Parses a slice (e.g. a:b:c) or index from the token_stream and returns the slice as a quadruple,
        the first element of which indicates whether it is a slice (True) or an index (False)
    """
    index_s, endt, _pos = _parse(token_stream, [T_COLON, T_RBRACKET])
    if endt == T_COLON:
        is_slice = True
        index_e, endt, _pos = _parse(token_stream, [T_RBRACKET, T_COLON])
        if endt == T_COLON:
            step, endt, _pos = _parse(token_stream, [T_RBRACKET])
        else:
            step = None
    else:
        is_slice = False
        index_e = None
        step = None
    return is_slice, index_s, index_e, step


def my_find(haystack, needle, stop_strs):
    pass


def parse_interpolated_str(tpl_expr, start='{{', end='}}', stop_strs=[]):
    """ Parses a string of the form

        .. code-block:: jinja

            Test text {{ exp }} other text {{ exp2 }} final text.


        where ``exp`` and ``exp2`` are expressions and returns a list of asts
        representing the expressions:

        .. code-block:: python

            ["Test text ",str(exp)," other text ",str(exp2)," final text."]


        Args:
            start (str):           the string opening an expression (defaults to '{{')
            end (str):             the string closing an expression (defaults to '}}')
            stop_strs (list(str)): Optionally stop parsing when reaching stop_str
                                   outside of an expression

        Returns:
            tuple(str, list(:class:`ExpNode`)): The parsed part of the string,
            a list of asts representing the text (:class:`ConstNode` s) and asts
            of the expressions

        Raises:
            :exc:`exceptions.ExpressionSyntaxError`: In case either one of the expressions is not
              a valid expression or if one of the expressions is not closed
    """
    last_pos = 0
    matcher = utils.MultiMatcher([start]+stop_strs)
    abs_pos, match = matcher.find(tpl_expr)
    if abs_pos > -1:
        token_stream = tokenize(tpl_expr[abs_pos + len(match):])
    ret = []
    while abs_pos > -1 and match not in stop_strs:
        if last_pos < abs_pos:
            ret.append(ConstNode(tpl_expr[last_pos:abs_pos]))                # Get string from the end of the previous expression to the start of the next expression
        abs_pos += len(start)                                                # Skip the opening string (start)
        token_stream = tokenize(tpl_expr[abs_pos:])                          # Tokenize the expression
        ast, _etok, rel_pos = _parse(token_stream, end_tokens=[str(end[0])])
        abs_pos += rel_pos                                                   # Skip the first character of the closing string (end)
        if not tpl_expr[abs_pos:abs_pos+len(end)-1] == end[1:]:
            raise ExpressionSyntaxError("Invalid interpolated string, expecting '"+str(end[1:])+"'", src=tpl_expr, location=abs_pos)
        else:
            abs_pos += len(end)-1                                            # Skip the rest of the closing string (end)
        ret.append(OpNode("()", IdentNode("str"), FuncArgsNode([ast], {})))  # Wrap the expression in a str call and add it to the list
        last_pos = abs_pos
        abs_pos, match = matcher.find(tpl_expr, last_pos)
    if len(tpl_expr) > last_pos and not match in stop_strs:
        abs_pos = len(tpl_expr)
    ret.append(ConstNode(tpl_expr[last_pos:abs_pos]))
    return tpl_expr[:abs_pos], ret


_PARSE_CACHE = {} # type: Dict[Tuple[str, bool], Tuple[ExpNode, int]]


def parse(expr: str, trailing_garbage_ok: bool=False, use_cache: bool=True) -> Tuple[ExpNode, int]:
    """
        Parses the expression ``expr`` into an AST tree of
        :class:`ExpNode` instances. If trailing_garbage_ok is set
        to ``False``, the string must be a valid expression (otherwise
        an exception is thrown). If it is set to false, only an initial
        part of the string needs to be a valid expression. The
        function returns a tuple consisting of the root node
        of the AST tree and the position in the string ``expr`` where
        parsing stopped.

        Additionnaly, the method maintains a cache of parsed expressions
        and, unless the ``use_cache`` is set to ``False``, the parsed trees
        are first looked up in this cache  and, if present, a clone is returned.

        Args:
            expr (str):                    the expression to parse
            trailing_garbage_ok (bool):    whether to ignore trailing garbage
            use_cache (bool):              whether to use the cache

        Returns:
            tuple(:class:`ExpNode`, int):  The parsed tree and the position where parsing
            stopped.
    """
    if (expr, trailing_garbage_ok) in _PARSE_CACHE and use_cache:
        ast, pos = _PARSE_CACHE[(expr, trailing_garbage_ok)]
        return ast.clone(), pos
    token_stream = tokenize(expr)
    ast, _etok, pos = _parse(token_stream, trailing_garbage_ok=trailing_garbage_ok)
    if use_cache:
        _PARSE_CACHE[(expr, True)] = ast, pos
    return ast, pos


def _parse(token_stream: _TokenStream, end_tokens=[], trailing_garbage_ok=False, end_token_vals=[]) -> Tuple[ExpNode, Optional[TokenT], int]:
    """
        Parses the `token_stream`, optionally stopping when an
        unconsumed token which is either a token in `end_tokens` or its string value is
        in `end_tokens`.

        Args:
            token_stream (iterator): The token stream
            end_tokens (list): A list of stop token classes and stop token values

        Returns:
            triple: the parsed tree, last token seen, next position

            The parsed tree may be None if the `token_stream` is empty.
            `next_position` corresponds to the next position in the source string.

        The parser is a simple stack based parser, using a variant
        of the [Shunting Yard Algorithm](https://en.wikipedia.org/wiki/Shunting-yard_algorithm)
    """
    arg_stack = [] # type: List[ExpNode]
    op_stack = []  # type: List[Tuple[TokenT, Any]]
    prev_token = None
    prev_token_set = False
    save_pos = 0
    for (token, val, pos) in token_stream:
        if token in end_tokens or (type(val) == str and val in end_tokens):  # The token is unconsumed and in the stoplist, so we evaluate what we can and stop parsing
            partial_eval(arg_stack, op_stack, src=token_stream._src, location=token_stream._src_pos)
            if len(arg_stack) == 0:
                return None, token, pos
            else:
                return arg_stack[0], token, pos
        elif token == T_IDENTIFIER:
            arg_stack.append(IdentNode(str(val)))
        elif token in [T_NUMBER, T_STRING]:
            arg_stack.append(ConstNode(val))
        elif token == T_OPERATOR or token == T_DOT or (token == T_KEYWORD and val == 'in'):
            # NOTE: '.' and 'in' are, in this context, operators.
            # If the operator has lower priority than operators on the @op_stack
            # we need to evaluate all pending operations with higher priority
            if val == '-' and (prev_token == T_OPERATOR or prev_token is None or prev_token == T_LBRACKET_LIST or prev_token == T_LPAREN_EXPR):
                val = '-unary'
            pri = OP_PRIORITY[str(val)]
            partial_eval(arg_stack, op_stack, pri, src=token_stream._src, location=token_stream._src_pos)
            op_stack.append((token, val))
        elif token == T_LBRACKET:
            # '[' can either start a list constant/comprehension, e.g. [1,2,3] or list slice, e.g. ahoj[1:10];
            # We destinguish between the two cases by noticing that first case must either
            # be at the start of the expression or be directly preceded by an
            # operator
            if prev_token == T_OPERATOR or prev_token is None or (
                    token == T_KEYWORD and val == 'in') or prev_token == T_LBRACKET_LIST or prev_token == T_LPAREN_EXPR or prev_token == T_LPAREN_FUNCTION:
                arg_stack.append(parse_lst(token_stream))
                prev_token = T_LBRACKET_LIST
            else:
                is_slice, index_s, index_e, step = parse_slice(token_stream)
                pri = OP_PRIORITY['[]']
                partial_eval(arg_stack, op_stack, pri, src=token_stream._src, location=token_stream._src_pos)
                arg_stack.append(ListSliceNode(is_slice, index_s, index_e, step))
                op_stack.append((T_OPERATOR, '[]'))
                prev_token = T_LBRACKET_INDEX
            prev_token_set = True
        elif token == T_LPAREN:
            # A '(' can either start a parenthesized expression or a function call.
            # We destinguish between the two cases by noticing that first case must either
            # be at the start of the expression or be directly preceded by an operator
            # TODO: Implement Tuples
            if prev_token == T_OPERATOR or prev_token is None or (
                    token == T_KEYWORD and val == 'in') or prev_token == T_LBRACKET_LIST or prev_token == T_LBRACKET_INDEX or prev_token == T_LPAREN_EXPR or prev_token == T_LPAREN_FUNCTION:
                op_stack.append((T_LPAREN_EXPR, val))
                prev_token = T_LPAREN_EXPR
            else:
                prev_token = T_LPAREN_FUNCTION
                args, kwargs = parse_args(token_stream)
                pri = OP_PRIORITY['()']
                partial_eval(arg_stack, op_stack, pri, src=token_stream._src, location=token_stream._src_pos)
                arg_stack.append(FuncArgsNode(args, kwargs))
                op_stack.append((T_OPERATOR, '()'))
            prev_token_set = True
        elif token == T_RPAREN:
            partial_eval(arg_stack, op_stack, src=token_stream._src, location=token_stream._src_pos)
            if op_stack[-1][0] != T_LPAREN_EXPR:
                raise Exception("Expecting '(' at " + str(pos))
            op_stack.pop()
        else:
            if trailing_garbage_ok:
                partial_eval(arg_stack, op_stack, src=token_stream._src, location=token_stream._src_pos)
                if len(arg_stack) > 2 or len(op_stack) > 0:
                    raise ExpressionSyntaxError("Invalid expression, leftovers: args:"+str(arg_stack)+"ops:"+str(op_stack), src=token_stream._src, location=token_stream._src_pos)
                return arg_stack[0], None, pos
            else:
                raise ExpressionSyntaxError("Unexpected token "+str((token, val)), src=token_stream._src, location=token_stream._src_pos)
        if not prev_token_set:
            prev_token = token
        else:
            prev_token_set = False
        save_pos = pos
    partial_eval(arg_stack, op_stack, src=token_stream._src, location=token_stream._src_pos)
    if len(arg_stack) > 2 or len(op_stack) > 0:
        raise ExpressionSyntaxError("Invalid expression, leftovers: args:"+str(arg_stack)+"ops:"+str(op_stack), src=token_stream._src, location=token_stream._src_pos)
    return arg_stack[0], None, save_pos
