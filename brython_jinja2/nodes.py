from . import environment
from . import exceptions
from . import expression
from . import interpolatedstr
from . import lexer
from .platform import bs4
from .utils import htmlparser

class Node:
    def __init__(self, name='', location=None, env=environment.default_env):
        if location is None:
            self._location = lexer.Location()
        else:
            self._location = location
        self._env = env
        self._args = []
        self._children = []
        self._name = name
        self._end_name = name
        
    def __str__(self):
        return str(type(self))+" (at "+ str(self._location)+" )"
    
    def rstrip(self):
        if len(self._children) > 0:
            self._children[-1].rstrip()

    def parse(self, args, token_stream, parser):
        self._args = args
        self._children, _ = parser._parse(token_stream, start_node=self)
    
    def ends(self, start_node):
        return self._name == start_node._end_name
    
    def children(self):
        return self._children

class HTMLElement(Node):
    def _parse_args(self, args):
        self._name = ''
        args = args.strip()
        for c in args:
            if c == ' ':
                break
            else:
                self._name += c
        self._name = self._name.upper()
        self._end_name = '/'+self._name
        args = args[len(self._name):].strip()
        attr_parser = htmlparser.AttribStateMachine(self._env)
        arg_dict = attr_parser.parse(args)
        ret = {}
        for k,v in arg_dict.items():
            if k.startswith(self._env.variable_start_string) and k.endswith(self._env.variable_end_string):
                exp_src = k[len(self._env.variable_start_string):-len(self._env.variable_end_string)]
                self._dynamic_attrs.append(expression.parse(exp_src))
            else:
                if self._env.variable_start_string in v:
                    ret[k] = interpolatedstr.InterpolatedStr(v, start=self._env.variable_start_string, end=self._env.variable_end_string)
                else:
                    ret[k] = v
        return ret
    
    def parse(self, args, token_stream, parser):
        args = args.strip()
        if args.endswith('/') or args.startswith('/'):
            closed=True
            args = args.rstrip('/')
        else:
            closed=False
        self._dynamic_attrs = []
        args = self._parse_args(args)
        if not closed:
            super().parse(args, token_stream, parser)
            
    def __str__(self):
        return "<"+self._name+" "+" ".join([k+"="+str(v) for k,v in self._args.items()])+"> (at "+str(self._location)+")"
        
class Content(Node):
    def __init__(self, content=None, *args, **kwargs):
        super().__init__(name='', *args, **kwargs)
        self._content = content
        if content is not None:
            self._interpolated = interpolatedstr.InterpolatedStr(content)
        else:
            self._interpolated = None

class HTMLComment(Content):
    pass

class Text(Content):
    def rstrip(self):
        self._content=self._content.rstrip()
        self._interpolated = interpolatedstr.InterpolatedStr(self._content)
        
class NodeFactory:
    AVAILABLE = {}
    
    @classmethod
    def register(cls, NodeName, NodeType):
        cls.AVAILABLE[NodeName] = NodeType
    
    def __init__(self, env):
        self.env = env
        self.active = { k:v for k,v in self.AVAILABLE.items() if k not in env.disabled_tags}
        
    def from_name(self, name, location):
        if name not in self.active:
            raise exceptions.TemplateSyntaxError("Unknown (or disabled) tag: "+name, location=location)
        return self.active[name](name=name, location=location, env=self.env)
        
def register_node(NodeName):
    def decorator(cls):
        NodeFactory.register(NodeName, cls)
        return cls
    return decorator

