from brython_jinja2 import templatenodes as nodes
from brython_jinja2.parser import Parser
from brython_jinja2.environment import default_env
from brython_jinja2.lexer import TokenStream

    
def test_parser_basic():
    TPL_SRC="""<div><div a=10 b= "b10" c ='20' d =  30 test e="{{ 10 + 20 + int('10') }}" f="><" g='{{ '><' }}' />Ahoj</div>"""
    parser = Parser(default_env)
    node_lst = parser.parse(TPL_SRC, 'basic_tpl', '<stdin>')
