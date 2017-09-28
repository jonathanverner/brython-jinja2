import pytest

from brython_jinja2 import templatenodes as nodes
from brython_jinja2.lexer import TokenStream
from brython_jinja2.environment import default_env
from brython_jinja2.exceptions import ExpressionSyntaxError, EOSException, TemplateSyntaxError
from brython_jinja2.parser import Parser

class MockParser:
    def __init__(self):
        self.env = default_env
        
    def _parse(self, node):
        pass
    
def test_variable_node():
    parser = MockParser()
    tokenstream = TokenStream("10+25*x }}")
    node = nodes.Variable(parser, tokenstream, tokenstream.loc)
    assert str(node._content) == "10 + 25 * x"
    
    tokenstream = TokenStream("'}}'+str(10) }}")
    node = nodes.Variable(parser, tokenstream, tokenstream.loc)
    assert str(node._content) == "'}}' + str(10)"
    
    parser.env.variable_end_string=">>"
    tokenstream = TokenStream("'>>'+str(10) >>")
    node = nodes.Variable(parser, tokenstream, tokenstream.loc)
    assert str(node._content) == "'>>' + str(10)"
    parser.env.variable_end_string="}}"
    
    with pytest.raises(ExpressionSyntaxError):
        tokenstream = TokenStream("10+25*x }*")
        node = nodes.Variable(parser, tokenstream, tokenstream.loc)
        
def test_comment_node():
    parser = MockParser()
    
    tokenstream = parser.env._tokenize("this is a comment {{ }}, {% %}, and nothing should <matter> #}",'test_comment_node')
    node = nodes.Comment(parser, tokenstream, tokenstream.loc)
    assert node._content == "this is a comment {{ }}, {% %}, and nothing should <matter> "
    
def test_if_node():
    TPL = "{% if x == 10 %} 10 {% elif x == 20 %}20{% else %}OTHER{% endif %}"
    parser = Parser()
    tpl = parser.parse(TPL, 'test_if_node.1', 'test_templatenodes.py')
    
    assert len(tpl) == 1
    assert isinstance(tpl[0], nodes.IfNode)
    
    cases = tpl[0]._cases
    
    assert len(cases) == 3
    assert str(cases[0][0]) == 'x == 10'
    assert cases[0][1][0]._content == " 10 "
    assert str(cases[1][0]) == 'x == 20'
    assert cases[1][1][0]._content == "20"
    assert str(cases[2][0]) == 'True'
    assert cases[2][1][0]._content == "OTHER"
    
    TPL = "{% if x == 10 %} 10 {% else %}20{% else %}OTHER{% endif %}"
    parser = Parser()
    with pytest.raises(TemplateSyntaxError):
        tpl = parser.parse(TPL, 'test_if_node.2', 'test_templatenodes.py')
     
    
    TPL = "{% if x == 10 %} 10 {% else %}20{% elif 10 %}OTHER{% endif %}"
    parser = Parser()
    with pytest.raises(TemplateSyntaxError):
        tpl = parser.parse(TPL, 'test_if_node.3', 'test_templatenodes.py')
        
    
    TPL = "{% else %}20{% elif 10 %}OTHER{% endif %}"
    parser = Parser()
    with pytest.raises(TemplateSyntaxError):
        tpl = parser.parse(TPL, 'test_if_node.4', 'test_templatenodes.py')
        
