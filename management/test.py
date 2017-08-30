from http import server
import os
from plumbum import local
import sys
from webbrowser import open_new_tab

from .utils import M

runner = local['pytest']['--cov=./brython_jinja2']

@M.command()
def devserver(port=8080):
    os.chdir(os.path.dirname(os.path.dirname(__file__))+'/web')
    open_new_tab("http://localhost:{}/".format(port))
    server.test(HandlerClass=server.SimpleHTTPRequestHandler, ServerClass=server.HTTPServer, port=port)
    
@M.command()
def run(tests=None):
    if tests is None:
        tests='tests'
    else:
        tests = 'tests/brython_jinja2/test_'+tests+'.py'
    try:
        runner.run(tests, stdout=sys.stdout, stderr=sys.stderr)
    except:
        pass

