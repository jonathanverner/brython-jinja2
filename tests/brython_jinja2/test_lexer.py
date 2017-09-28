import brython_jinja2.lexer as l
from brython_jinja2.lexer import TokenStream
from brython_jinja2.environment import default_env

def test_slices():
    SRC='<abc >'
    ts = TokenStream(SRC)
    assert len(ts) == len(SRC)
    assert ts[:2] == '<a'
    assert ts[1:3] == 'ab'
    assert ts[1:] == 'abc >'
    assert ts[:-1] == '<abc '
    assert ts[2] == 'b'
    assert ts[-2] == ' '
    assert ts.pop_left()[1] == '<'
    
    assert ts.cat_until(['b']) == 'a'
    assert ts[0] == 'b'
    assert ts[1] == 'c'
    assert ts[:2] == 'bc'
    
def test_skip():
    SRC='   12345'
    ts = TokenStream(SRC)
    ts.skip([' '])
    assert ts[0] == '1'
    ts.skip(2)
    assert ts[0] == '3'
    
def test_comment():
    SRC='{##}'
    ts = default_env._tokenize(SRC,'test_comment')
    toks = list(ts)
    assert toks[0][:2] == (l.T_COMMENT_START, '{#')
    assert toks[1][:2] == (l.T_COMMENT_END, '#}')
    assert toks[2][0] == l.T_EOS
    
