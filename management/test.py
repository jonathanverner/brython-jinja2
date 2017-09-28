from http import server
import os
from plumbum import local, ProcessExecutionError
import sys
from webbrowser import open_new_tab

from .utils import M

test_runner = local['pytest']
linter = local['pylint']

@M.command()
def devserver(port=8080):
    os.chdir(os.path.dirname(os.path.dirname(__file__))+'/web')
    open_new_tab("http://localhost:{}/".format(port))
    server.test(HandlerClass=server.SimpleHTTPRequestHandler, ServerClass=server.HTTPServer, port=port)

@M.command()
def run(tests=None):
    with local.env(PYTHONPATH='./src:./'):
        if tests is None:
            tests='tests'
            args = (tests,)
        else:
            tests = 'tests/brython_jinja2/test_'+tests+'.py'
            args = (tests,'--fulltrace', '--pdb')
        try:
            test_runner.run(args, stdout=sys.stdout, stderr=sys.stderr)
        except:
            pass

@M.command()
def lint(report=False):
    with local.env(PYTHONPATH='./src:./tests/brython/'):
        try:
            if not report:
                linter("--reports=n", "brython_jinja2", stdout=sys.stdout, stderr=sys.stderr)
            else:
                linter("brython_jinja2", stdout=sys.stdout, stderr=sys.stderr)
        except ProcessExecutionError:
            exit(1)
