from asyncio import coroutine

from . import exceptions
from . import nodes
from . import environment
from . import interpolatedstr
from . import expression
from .platform import bs4
from .utils import delayedupdater

class RenderFactory:
    AVAILABLE = {}
    
    @classmethod
    def register(cls, NodeType, RenderType):
        cls.AVAILABLE[NodeType] = RenderType
        
    def __init__(self, env):
        self.env = env
        self.active = { k:v for k,v in self.AVAILABLE.items() }

    def from_node(self, node):
        if not type(node) in self.active:
            raise exceptions.RenderError("No renderer available for node "+str(node), location=node._location)
        return self.active[type(node)](tpl_node=node, factory=self)
    
default_factory = RenderFactory(environment.default_env)
        
def register_render_node(Node):
    def decorator(cls):
        RenderFactory.register(Node, cls)
        return cls
    return decorator

class RenderNode(delayedupdater.DelayedUpdater):
    def __init__(self, tpl_node=None, factory=default_factory):
        super().__init__()
        self._tpl_node = tpl_node
        self._factory = factory
        self._children = [self._factory.from_node(ch) for ch in tpl_node.children()]
        self._parent = None
        for ch in self._children:
            ch.bind('change', self._child_change_handler)
        
    def clone(self, clone_into=None):
        if clone_into is None:
            clone_into = type(self)()
        clone_into._tpl_node = self._tpl_node
        clone_into._children = [ch.clone() for ch in self._children]
        return clone_into
        
    @coroutine
    def render_into(self, ctx, parent=None):
        self._parent = parent
        for ch in self._children:
            yield ch.render_into(ctx, parent=self._parent)

    def destroy(self):
        for ch in self._children:
            ch.unbind('change')
            ch.destroy()


@register_render_node(nodes.HTMLElement)
class HTMLElement(RenderNode):
    UPDATE_ON = 'blur'
    
    def __init__(self, tpl_node=None, factory=default_factory):
        super().__init__(tpl_node, factory)
        self._attrs = {}
        self._dynamic_attrs = [ exp.clone() for exp in tpl_node._dynamic_attrs ]
        for attr, val in tpl_node._args.items():
            if isinstance(val, interpolatedstr.InterpolatedStr):
                self._attrs[attr] = val.clone()
            else:
                self._attrs[attr] = val
        
        self._value_expr = None
        self._source_expr = None
        self._update_on = self.UPDATE_ON
                
    def clone(self, clone_into=None):
        clone_into = super().clone(clone_into)
        for attr, val in self._attrs.items():
            if isinstance(val, interpolatedstr.InterpolatedStr):
                clone_into._attrs[attr] = val.clone()
            else:
                clone_into._attrs[attr] = val
        return clone_into
    
    
    def _setup_value_binding(self, val):
        self._value_expr = val.get_ast(0, strip_str=True)
        src = self._attrs.get('data-value-source', None)
        if isinstance(src, interpolatedstr.InterpolatedStr):
            raise exceptions.TemplateSyntaxError('Value source must be a bare expression, not an interpolated string: '+str(src), src=None, location=self._tpl_node._location)
        if src is None:
            raise NotImplementedError("Guessing value source not supported yet, please provide a data-value-source attribute at "+str(self._tpl_node._location))
        self._source_expr, _ = expression.parse(src)
        self._update_on = self._attrs.get('data-update-source-on', self.UPDATE_ON)
        self._elt._elt.bind(self._update_on, self._update_source)
        
            
    @coroutine
    def render_into(self, ctx, parent):
        tn = self._tpl_node
        self._elt = bs4.Tag("<"+tn._name+"><"+tn._end_name+">")
        for attr, val in self._attrs.items():
            if isinstance(val, interpolatedstr.InterpolatedStr):
                val.bind_ctx(ctx)
                val.bind('change', self._change_handler)
                self._elt[attr] = val.value
                if attr.lower() == 'value':
                    self._setup_value_binding(val)
            else:
                self._elt[attr]=val
        for da in self._dynamic_attrs:
            da.bind_ctx(ctx)
            da.bind('change', self._change_handler)
            try:
                for attr, val in da.value.items():
                    self._elt[attr]=val
            except:
                pass
        for ch in self._children:
            yield ch.render_into(ctx, self._elt)
        parent.append(self._elt)
        
    def destroy(self):
        super().destroy()
        for val in self._attrs.values():
            if isinstance(val, interpolatedstr.InterpolatedStr):
                val.unbind('change')
        for da in self._dynamic_attrs:
            da.unbind('change')
        self._elt.decompose()
    
    def _update_source(self, evt):
        if self._elt['value'] == self._value_expr.value:
            print("VALUE UNCHANGED", self._value_expr.value)
            return
        else:
            try:
                self._value_expr.solve(self._elt['value'], self._source_expr)
            except Exception as ex:
                print("Context:", self._value_expr._ctx)
                print("Source equiv to Value:", self._value_expr.equiv(self._source_expr))
                print("Value Expr:", self._value_expr)
                print("Source Expr:", self._source_expr)
                print("Orig value:", self._elt['value'])
                print("Exception setting value:", str(ex))
                print("Final value", self._value_expr.value)
                self._elt['value'] = self._value_expr.value
            
    def _update(self):
        for attr, val in self._attrs.items():
            if isinstance(val, interpolatedstr.InterpolatedStr):
                self._elt[attr] = val.value
        for da in self._dynamic_attrs:
            try:
                for attr, val in da.value.items():
                    self._elt[attr]=val
            except:
                pass 
        
@register_render_node(nodes.Text)
class Text(RenderNode):
    def __init__(self, tpl_node=None, factory=default_factory):
        super().__init__(tpl_node, factory)
        self._interpolated = tpl_node._interpolated.clone()
    
    def clone(self, clone_into=None):
        clone_into = super().clone(clone_into)
        clone_into._interpolated = self._interpolated.clone()
        return clone_into
        
    @coroutine
    def render_into(self, ctx, parent):
        self._interpolated.bind_ctx(ctx)
        self._elt = bs4.NavigableString(self._interpolated.value)
        parent.append(self._elt)
        self._interpolated.bind('change', self._change_handler)
        
    def _update(self):
        self._elt.replace_with(self._interpolated.value)
        
    def destroy(self):
        super().destroy()
        self._interpolated.unbind('change')
        self._elt.decompose()


