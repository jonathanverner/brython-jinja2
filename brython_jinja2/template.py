from asyncio import coroutine, sleep

from . import environment
from . import parser
from . import rendernodes
from .utils import events

@events.emits('change')
class Template(events.EventMixin):
    def __init__(self, src, env=environment.default_env, update_interval=0.1):
        self.env = env
        self.src = src
        self.parser = parser.Parser(self.env, self.src)
        self.ast = self.parser.parse()
        self.render_factory = rendernodes.RenderFactory(self.env)
        self._rendered_nodes = []
        self._update_scheduled = False
        self._update_interval = update_interval
        
    @coroutine
    def render(self, ctx, into):
        for node in self.ast:
            rn = self.render_factory.from_node(node)
            yield rn.render_into(ctx, into)
            self._rendered_nodes.append(rn)
            rn.bind('change', self._schedule_update)
    
    @coroutine
    def _schedule_update(self, evt):
        if self._update_scheduled:
            return
        self._update_scheduled = True
        yield sleep(self._update_interval)
        self._update()
        self._update_scheduled = False
        
    def _update(self):
        for rn in self._rendered_nodes:
            rn.update_if_needed()
    
    def destroy(self):
        for rn in self._rendered_nodes:
            rn.unbind('change')
            rn.destroy()
        self._rendered_nodes = []
