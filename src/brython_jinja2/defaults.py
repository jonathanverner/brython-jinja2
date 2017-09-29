"""
    brython_jinja2.defaults
    ~~~~~~~~~~~~~~~

    Brython Jinja default filters and tags.

    :copyright: (c) 2017 by the Jinja Team, (c) 2017 Jonathan L. Verner.
    :license: BSD, see LICENSE for more details.
"""

# defaults for the parser / lexer
BLOCK_START_STRING = '{%'
BLOCK_END_STRING = '%}'
VARIABLE_START_STRING = '{{'
VARIABLE_END_STRING = '}}'
COMMENT_START_STRING = '{#'
COMMENT_END_STRING = '#}'
LINE_STATEMENT_PREFIX = None
LINE_COMMENT_PREFIX = None
TRIM_BLOCKS = False
LSTRIP_BLOCKS = False
NEWLINE_SEQUENCE = '\n'
KEEP_TRAILING_NEWLINE = False
