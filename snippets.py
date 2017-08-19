from brython_jinja2.utils import htmlparser as p
p.parse_attrs('ahoj')
p.parse_attrs('ahoj="10"')

class InvalidSyntax(Exception):
    def __init__(self, message, src, pos):
        super().__init__(message)
        self.message = message
        self.src=src
        self.pos=pos
    
    def __str__(self):
        return "InvalidSyntax at "+str(self.pos)+": "+self.message+"\nsrc: "+self.src+"\n     "+" "*self.pos+"^"

from brython_jinja2.template import Template
from brython_jinja2.context import Context
from brython_jinja2.platform import bs4
from browser import document as doc
ctx = Context()
d = bs4.Tag('<div></div>')
t = Template("""<div class='{{ " ".join(css_classes) }}' id='{{ id }}' style='border:solid,1px,black'>Ahoj {{ name }}</div>""")
ctx.css_classes=['red','green','blue']
ctx.id='test'
ctx.name='Jonathane'
doc <= d._elt
f = t.render(ctx, d)


from asyncio import coroutine, sleep
@coroutine
def dp(self):
  yield sleep(1)
  print("Ahoj")

c = dp(1)

from brython_jinja2 import context as ctx
c = ctx.Context()
c.a = 6
c.b = ctx.Immutable(7)
c.d = ctx.Immutable([1,2,3,4])
c.d.append(5)
print(c.d)
print(c)
print(c.immutable_attrs)

from brython_jinja2 import expression as exp

e, _ = exp.parse('(1+4)*4+x')
e.simplify()

c.x = ctx.Immutable(6)
e.bind_ctx(c)
exp.simplify(e)
