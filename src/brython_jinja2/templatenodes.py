from . import environment
from . import exceptions
from . import expression
from . import interpolatedstr
from . import lexer
from .context import Context
from .platform import bs4
from .platform import typing
from .platform.typing import List, Dict, Optional, Tuple, Iterable, Callable
from .utils.delayedupdater import DelayedUpdater


_NODE_BEGIN_MARKER='data-jinja-tpl-node-'
_NODE_END_MARKER='_'


class Node(DelayedUpdater):
    def __init__(self, parser, token_stream: lexer.TokenStream, location: Optional[lexer.Location]=None):
        if location is None:
            self._location = lexer.Location()
        else:
            self._location = location
        self._children = []
        self._rendered = []
        self._ctx = Context()

    @classmethod
    def _html_ref(cls, id: int) -> str:
        return _NODE_BEGIN_MARKER+str(id)+_NODE_END_MARKER

    @classmethod
    def _extract_id(cls, text: str) -> int:
        return int(text.rstrip(_NODE_END_MARKER).lstrip(_NODE_BEGIN_MARKER))


    def _get_html_content(self):
        html = ""
        for num, ch in enumerate(self._children):
            html+=ch._html_ref(num)
        return html

    def render_dom(self) -> List[bs4.Tag]:
        root = bs4.dom_from_html(self._get_html_content())
        t_el = _TemplatedTag(root, self._children)
        self._rendered = [ch.extract() for ch in t_el.children]
        return self._rendered

    def render_text(self) -> str:
        ret = ""
        for ch in self._children:
            ret += ch.render_text(self._ctx)
        return ret

    def bind_ctx(self, ctx: Context):
        self._ctx = ctx
        for ch in self._children:
            ch.bind_ctx(ctx)

    def __str__(self):
        return str(type(self))+" (at "+ str(self._location)+" )"

    def rstrip(self):
        """
            Strips whitespace on the right side of the Node's content

            Note: For internal use by `Parser`
        """
        if self._children:
            self._children[-1].rstrip()

    @classmethod
    def parse_args(cls, token_stream: lexer.TokenStream, end_str: str) -> expression.ExpNode:
        """
            Parses an expression at the current position of token_stream. The expression
            should be ended by the string `end_str`. The stream is advanced to the
            first character after `end_str`.

            Args:
              token_stream (lexer.TokenStream): the stream of tokens to parse
              end_str (str): the string which should end the expression

            Returns:
              expression.Node: The root node of the AST representing the parsed expression
        """
        exp_tokens = expression.tokenize(token_stream.remain_src)
        ast, _etok, pos = expression._parse(exp_tokens, end_tokens = [end_str[0]])
        if not token_stream.remain_src[pos:pos+len(end_str)-1] == end_str[1:]:
            raise exceptions.ExpressionSyntaxError("Invalid argument string, expecting '"+str(end_str)+"', found '"+end_str[0]+token_stream.remain_src[pos:pos+len(end_str)-1]+"' instead.", src=token_stream.remain_src, location=pos)
        token_stream.skip(pos+len(end_str)-2)
        return ast

    @property
    def children(self):
        return self._children

class NodeFactory:
    AVAILABLE = {}

    @classmethod
    def register(cls, NodeName: str, NodeType: type):
        cls.AVAILABLE[NodeName] = NodeType

    def __init__(self, env: environment.Environment):
        self.env = env
        self.active = { k:v for k,v in self.AVAILABLE.items() if k not in env.disabled_tags}

    def from_name(self, parser, name: str, tokenstream: lexer.TokenStream, location: lexer.Location) -> Node:
        if name not in self.active:
            raise exceptions.TemplateSyntaxError("Unknown (or disabled) tag: "+name, src=tokenstream.src, location=location)
        return self.active[name](parser, tokenstream, location)

def register_node(NodeName: str) -> Callable[[type], type]:
    def decorator(cls: type) -> type:
        NodeFactory.register(NodeName, cls)
        return cls
    return decorator

class _TemplatedTag(bs4.PageElement):
    def __init__(self, elt: bs4.Tag, node_map: Dict[int, Node]):
        self._elt = bs4.Tag(elt.name)
        self._dynamic_attrs = []
        for ch in elt.children:
            if isinstance(ch, bs4.NavigableString):
                pieces = ch.text.split(_NODE_BEGIN_MARKER)
                self.append(bs4.NavigableString(pieces[0]))
                for p in pieces[1:]:
                    id, rest = p.split(_NODE_END_MARKER)
                    for el in node_map[int(id)].render_dom():
                        self.append(el)
                    self.append(bs4.NavigableString(rest))
            elif isinstance(ch, bs4.Tag):
                self.append(_TemplatedTag(ch, node_map))

        for name, val in self.attrs.items():
            if _NODE_BEGIN_MARKER in name:
                if not val == '':
                    raise exceptions.TemplateError("templated attribute cannot have a value")
                id = Node._extract_id(name)
                self._dynamic_attrs.append(_TemplatedAttr(self, node_map[id]))
            elif _NODE_BEGIN_MARKER in val:
                id = Node._extract_id(val)
                self._dynamic_attrs.append(_TemplatedValAttr(self, name, val, node_map))

class _TemplatedValAttr:
    def __init__(self, elt: bs4.Tag, name: str, value: str, nodes: List[Node]):
        self._elt = elt
        self._name = name
        self._components = []
        pieces = value.split(_NODE_BEGIN_MARKER)
        if pieces[0]:
            self._components.append(pieces[0])
        for p in pieces[1:]:
            id, rest = p.split(_NODE_END_MARKER)
            node = nodes[int(id)]
            self._components.append(node)
            if rest:
                self._components.append(rest)


class _TemplatedAttr:
    def __init__(self, elt: bs4.Tag, node: Node):
        self._node = node



class _TemplatedText(bs4.NavigableString):
    def __init__(self, node: Node):
        self._tpl_node = node
        self.replace_with(self._tpl_node.render_text())


class Comment(Node):
    def __init__(self, parser, token_stream: lexer.TokenStream, location=None):
        super().__init__(parser, token_stream, location)
        self._content = token_stream.cat_until([lexer.T_COMMENT_END])

    def _get_html_content(self):
        return ""

class Variable(Node):
    def __init__(self, parser, token_stream: lexer.TokenStream, location=None):
        super().__init__(parser, token_stream, location)
        e_str = parser.env.variable_end_string
        self._content = self.parse_args(token_stream, e_str)

    def _get_html_content(self):
        return ""

    @property
    def safe(self):
        return False

    def bind_ctx(self, ctx):
        super().bind_ctx(ctx)
        self._content.bind_ctx(ctx)

    def render_dom(self):
        if self.safe:
            self._rendered = bs4.dom_from_html(self._content.value)
        else:
            self._rendered = _TemplatedText(self)
        return self._rendered

    def render_text(self):
        return self._content.value

class Content(Node):
    def __init__(self, parser, token_stream: lexer.TokenStream, location):
        super().__init__(parser, token_stream, location)
        self._content = token_stream.cat_until([lexer.T_BLOCK_START, lexer.T_VARIABLE_START, lexer.T_COMMENT_START, lexer.T_EOS])

    def _get_html_content(self):
        return self._content

    def render_dom(self):
        return bs4.NavigableString(self._content)

    def render_text(self):
        return self._content



@register_node('if')
class IfNode(Node):
    """
    The if tag is comparable with the Python if statement. In the simplest form, you can use it to test if a variable is defined, not empty and not false:

    .. code-block:: jinja

        {% if users %}
        <ul>
        {% for user in users %}
            <li>{{ user.username|e }}</li>
        {% endfor %}
        </ul>
        {% endif %}


    For multiple branches, elif and else can be used like in Python. You can use more complex Expressions there, too:

    .. code-block:: jinja

        {% if kenny.sick %}
            Kenny is sick.
        {% elif kenny.dead %}
            You killed Kenny!  You bastard!!!
        {% else %}
            Kenny looks okay --- so far
        {% endif %}

    """
    def __init__(self, parser, token_stream, location=None):
        super().__init__(parser, token_stream, location)
        self._cases = []
        cond = self.parse_args(token_stream, end_str=parser.env.block_end_string)
        body, end_node = parser._parse(token_stream, end_node_names=['else', 'elif', 'endif'])
        self._cases.append((cond, body))
        while end_node == 'elif':
            cond = self.parse_args(token_stream, end_str=parser.env.block_end_string)
            body, end_node = parser._parse(token_stream, end_node_names=['else', 'elif', 'endif'])
            self._cases.append((cond, body))
        if end_node == 'else':
            token_stream.cat_until([parser.env.block_end_string])
            token_stream.skip(1)
            cond = expression.ConstNode(True)
            body, end_node = parser._parse(token_stream, end_node_names=['endif'])
            self._cases.append((cond, body))
        token_stream.cat_until([parser.env.block_end_string])
        token_stream.skip(len(parser.env.block_end_string))

@register_node('else')
class ElseNode(Node):
    def __init__(self, parser, token_stream, location):
        raise exceptions.TemplateSyntaxError("Unexpected else tag (did you put more than one else tag inside an if?)", src=token_stream.src, location=location)

@register_node('elif')
class ElifNode(Node):
    def __init__(self, parser, token_stream, location):
        raise exceptions.TemplateSyntaxError("Unexpected elif tag (did you put the elif after the else?)", src=token_stream.src, location=location)

@register_node('endif')
class EndifNode(Node):
    def __init__(self, parser, token_stream, location):
        raise exceptions.TemplateSyntaxError("Unexpected endif tag (not in the scope of an if tag)", src=token_stream.src, location=location)
