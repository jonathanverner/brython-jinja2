from brython_jinja2.nodes import HTMLElement
from brython_jinja2.lexer import TokenStream
from brython_jinja2.environment import default_env

class MockParser:
    def __init__(self):
        self.env = default_env
        
    def _parse(self, node):
        pass
    
def test_html_node():
    parser = MockParser()
    HTML = TokenStream("""div a=10 b= "b10" c ='20' d =  30 test e="{{ 10 + 20 + int('10') }}" f="><" g='{{ '><' }}' />""")
    node = HTMLElement(parser, HTML)
    assert node._name == 'DIV'
    assert node._attrs == {'A':'10', 'B':'b10', 'C':'20', 'D':'30', 'TEST':None, 'E':'40', 'F':'><', 'G':'><'}
    assert node._closed
