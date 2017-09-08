from . import environment
from . import exceptions
from . import expression
from . import interpolatedstr
from . import lexer
from .platform import bs4
from .utils import htmlparser, parser_utils as pu

class Node:
    def __init__(self, parser, token_stream, location=None):
        if location is None:
            self._location = lexer.Location()
        else:
            self._location = location
        self._children = []
        
    def __str__(self):
        return str(type(self))+" (at "+ str(self._location)+" )"
    
    def rstrip(self):
        """
            Strips whitespace on the right side of the Node's content
            
            Note: For internal use by `Parser`
        """
        if self._children:
            self._children[-1].rstrip()

    def parse_children(self, token_stream, parser):
        """
        Parses children of this node starting at token_stream 
        (which is at the position just after the end of the starting tag of the current node)
        
        Note: For internal use by `Parser`.
        
        Args:
            token_stream (lexer.TokenStream): the source code
            parser (parser.Parser): the parser which is currently parsing the source code
        
        Returns:
            Node: If the method parsed a node which is not supposed to be a child, it returns it.
                  Otherwise returns None.
        """
        return None

    def ended_by(self, parser, end_node):
        """
        Tests whether this node is closed by `end_node`. 
        
        Note: For internal use by `Parser`.
        
        Args:
            parser   (parser.Parser):   the parser in its current state
            end_node (Node):            the node to test 
        
        Returns:
            bool: `True` if the node is closed by `end_node`, `False` otherwise. 
                           
        """
        return end_node is None
    
    @property
    def children(self):
        return self._children

_END_OF_PARENT = 0

class HTMLElement(Node):
    SELF_CLOSING_TAGS = ['AREA', 'BASE', 'BR', 'COL', 'COMMAND', 'EMBED', 'HR', 'IMG', 'INPUT', 'KEYGEN', 'LINK', 'META', 'PARAM', 'SOURCE', 'TRACK', 'WBR']
    PARENT_CLOSING_TAGS = set(['HTML', 'HEAD', 'BODY', 'DD', 'LI', 'P', 'OPTGROUP', 'OPTION', 'RB', 'RT', 'RTC', 'RP', 'TBODY', 'TR', 'TD', 'TFOOT'])
    EOF_CLOSING_TAGS = set(['HTML', 'BODY'])
    AUTO_CLOSING_TAGS = {
        'HEAD': ['BODY'], 
        'DT':   ['DT', 'DD'], 
        'DD':   ['DT', 'DD'],
        'LI':   ['LI'],
        'P':    ['ADDRESS', 'ARTICLE', 'ASIDE', 'BLOCKQUOTE', 
                 'DIV', 'DL', 'FIELDSET', 'FOOTER', 'FORM', 
                 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'HEADER', 
                 'HGROUP', 'HR', 'MAIN', 'NAV', 'OL', 'P', 
                 'PRE', 'SECTION', 'TABLE', 'UL'],
        'OPTGROUP': ['OPTGROUP'],
        'OPTION': ['OPTION', 'OPTGROUP'], 
        'RB': ['RB', 'RT', 'RTC', 'RP'],
        'RT': ['RB', 'RT', 'RTC', 'RP'],
        'RTC': ['RB', 'RTC', 'RP'],
        'RP': ['RB', 'RT', 'RTC', 'RP'],
        'TBODY':['TBODY', 'TFOOT'], 
        'TH':['TD', 'TH'],
        'THEAD':['TBODY', 'TFOOT'],
        'TR':['TR'], 
        'TD':['TD', 'TH'], 
        'TFOOT':['TBODY', 'TFOOT'],  
    }
    # FIXME: colgroup
    
    def __init__(self, parser, token_stream, location=None):
        super().__init__(parser, token_stream, location)
        self._name = token_stream.cat_until([lexer.T_SPACE, lexer.T_HTML_ELEMENT_END]).upper()
        self._attrs = {}
        self._closed = False
        token_stream.skip([lexer.T_SPACE])
        tok, tok_val, pos = next(token_stream)
        while tok != lexer.T_HTML_ELEMENT_END and tok_val != '/':
            attr_name = tok_val+token_stream.cat_until([lexer.T_SPACE, lexer.T_HTML_ELEMENT_END, '/', '='])
            attr_name = attr_name.upper()
            token_stream.skip([lexer.T_SPACE])
            _, tok_val, _ = token_stream.peek()
            if tok_val != '=':
                self._attrs[attr_name] = None
            else:
                token_stream.pop_left()
                token_stream.skip([lexer.T_SPACE])
                _, tok_val, _ = token_stream.peek()
                if tok_val in ['"', "'"]:
                    delims = [tok_val]
                    token_stream.pop_left()
                else:
                    delims = [' ', '\n', '\t']
                interpolation = interpolatedstr.InterpolatedStr(token_stream.remain_src, 
                                                                start=parser.env.variable_start_string, 
                                                                end=parser.env.variable_end_string,
                                                                stop_strs=delims)
                if interpolation.is_const():
                    self._attrs[attr_name] = interpolation.value
                else:
                    self._attrs[attr_name] = interpolation
                token_stream.skip(len(interpolation._src))
                token_stream.skip(delims)
            token_stream.skip([lexer.T_SPACE])
            tok, tok_val, pos = next(token_stream)
            
        if tok_val == '/' or self._name in HTMLElement.SELF_CLOSING_TAGS:
            token_stream.pop_left()
            self._closed = True
    
    def parse_children(self, token_stream, parser):
        closing_node = None
        if not self._closed:
            self._children, closing_node = parser._parse(token_stream, start_node=self)
            if isinstance(closing_node, HTMLElement) and closing_node._name == '/'+self._name:
                closing_node = None
            self._closed = True
        return closing_node
            
    
    def ended_by(self, parser, end_node):        
        if self._name in HTMLElement.PARENT_CLOSING_TAGS:
            parent = parser._parent(self)
            if parent and parent.ended_by(parser, end_node):
                return True
            
        if end_node is None:
            return self._name in HTMLElement.EOF_CLOSING_TAGS
        
        if not isinstance(end_node, HTMLElement):
            return False
        
        if end_node._name == '/'+self._name:
            return True
            
        if end_node._name in HTMLElement.AUTO_CLOSING_TAGS.get(self._name, []):
            return True
        
        return False
            
    def __str__(self):
        return "<"+self._name+" "+" ".join([k+"="+str(v) for k,v in self._attrs.items()])+"> (at "+str(self._location)+")"
        
class Content(Node):
    def __init__(self, parser, token_stream, location=None):
        super().__init__(parser, token_stream, location)
        self._interpolated = interpolatedstr.InterpolatedStr(token_stream, 
                                                             start=parser.env.variable_start_string, 
                                                             end=parser.env.variable_end_string,
                                                             stop_strs=lexer.tokens_to_strs(parser.env.token_map, [lexer.T_BLOCK_START, lexer.T_COMMENT_START, lexer.T_HTML_ELEMENT_START]))
        token_stream.skip(len(self._interpolated._src))
        
    def rstrip(self):
        self._interpolated = self._interpolated.rstrip()

class HTMLComment(Node):
    def __init__(self, parser, token_stream, location=None):
        super().__init__(parser, token_stream, location)
        self._content = token_stream.cat_until([lexer.T_HTML_COMMENT_END])
        token_stream.pop_left()
        
class NodeFactory:
    AVAILABLE = {}
    
    @classmethod
    def register(cls, NodeName, NodeType):
        cls.AVAILABLE[NodeName] = NodeType
    
    def __init__(self, env):
        self.env = env
        self.active = { k:v for k,v in self.AVAILABLE.items() if k not in env.disabled_tags}
        
    def from_name(self, parser, name, tokenstream, location):
        if name not in self.active:
            raise exceptions.TemplateSyntaxError("Unknown (or disabled) tag: "+name, src=parser.src, location=location)
        return self.active[name](parser, tokenstream, location)
        
def register_node(NodeName):
    def decorator(cls):
        NodeFactory.register(NodeName, cls)
        return cls
    return decorator

