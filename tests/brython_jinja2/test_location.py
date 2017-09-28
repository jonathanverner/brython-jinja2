from brython_jinja2.utils import Location

src = """
from brython_jinja2.utils import Location

def a(test):
    print("AHOJ")
    
def test_ctx():
    loc = Location("abc")
    assert

""".strip()

def test_location_context_single_line():
    loc = Location(src="ahoj")
    assert len(loc.context(num_ctx_lines=20)) == 2
    
def test_location_from_pos():
    loc = Location.location_from_pos(src=src, pos=src.find("AHOJ"))
    assert loc.line == 3
    assert loc.column == 11
    assert loc.pos == src.find("AHOJ")
    
def test_location_context():
    loc = Location.location_from_pos(src=src, pos=src.find("AHOJ"))
    ctx = loc.context(num_ctx_lines = 1)
    assert len(ctx) == 5

    loc = Location.location_from_pos(src=src, pos=src.find("from"))
    ctx = loc.context(num_ctx_lines = 1)
    assert len(ctx) == 4    
    
    loc = Location.location_from_pos(src=src, pos=src.find("assert"))
    ctx = loc.context(num_ctx_lines = 1)
    assert len(ctx) == 4    
    
    loc = Location.location_from_pos(src=src, pos=src.find("def"))
    ctx = loc.context(num_ctx_lines = 20)
    assert len(ctx) == 2+len(src.split('\n'))
    ctx = loc.context(num_ctx_lines = 2)
    assert len(ctx) == 7
