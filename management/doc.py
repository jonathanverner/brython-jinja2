from http import server
import os
from plumbum import local, ProcessExecutionError
import sys
from webbrowser import open_new_tab


from .utils import M

sphinx = local['sphinx-build']
sphinx_args = ["-d", "_build/doctrees"]
apidoc = local['sphinx-apidoc']

@M.command()
def build(format="html"):
    if format == "latex":
        sphinx_args.extend(["-D", "latex_paper_size=a4"])

    apidoc("-o", './doc/en/api/', './src/')

    with local.cwd('./doc/en'):
        sphinx(".", "_build", "-b", format, *sphinx_args, stdout=sys.stdout, stderr=sys.stderr)

@M.command()
def view(port=7364):
    with local.cwd('./doc/en/_build/'):
        open_new_tab("http://localhost:{}/".format(port))
        server.test(HandlerClass=server.SimpleHTTPRequestHandler, ServerClass=server.HTTPServer, port=port)

