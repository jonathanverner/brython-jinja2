from brython_jinja2 import nodes
from brython_jinja2.parser import Parser
from brython_jinja2.environment import default_env
from brython_jinja2.lexer import TokenStream

    
def test_parser_basic():
    TPL_SRC="""<div><div a=10 b= "b10" c ='20' d =  30 test e="{{ 10 + 20 + int('10') }}" f="><" g='{{ '><' }}' />Ahoj</div>"""
    parser = Parser(default_env, TPL_SRC, 'basic_tpl', '<stdin>')
    node_lst = parser.parse()
    assert len(node_lst) == 1
    assert len(node_lst[0].children) == 2
    div = node_lst[0].children[0]
    txt = node_lst[0].children[1]
    assert div._name == 'DIV'
    assert div._attrs == {'A':'10', 'B':'b10', 'C':'20', 'D':'30', 'TEST':None, 'E':'40', 'F':'><', 'G':'><'}
    assert type(txt) == nodes.Content
