"""
    brython_jinja2.environment
    ~~~~~~~~~~~~~~~
    
    Provides a class that holds runtime and parsing time options.
    
    :copyright: (c) 2017 by the Jinja Team, (c) Jonathan L. Verner.
    :license: BSD, see LICENSE for more details.
"""


from . import defaults
from . import lexer

class Environment:
    def __init__(self,
                 block_start_string=defaults.BLOCK_START_STRING,
                 block_end_string=defaults.BLOCK_END_STRING,
                 variable_start_string=defaults.VARIABLE_START_STRING,
                 variable_end_string=defaults.VARIABLE_END_STRING,
                 comment_start_string=defaults.COMMENT_START_STRING,
                 comment_end_string=defaults.COMMENT_END_STRING,
                 line_statement_prefix=defaults.LINE_STATEMENT_PREFIX,
                 line_comment_prefix=defaults.LINE_COMMENT_PREFIX,
                 trim_blocks=defaults.TRIM_BLOCKS,
                 lstrip_blocks=defaults.LSTRIP_BLOCKS,
                 newline_sequence=defaults.NEWLINE_SEQUENCE,
                 keep_trailing_newline=defaults.KEEP_TRAILING_NEWLINE,
                 extensions=(),
                 undefined=None,
                 autoescape=False,
                 loader=None):
        self.token_map = sorted((
            (lexer.T_BLOCK_START,block_start_string),
            (lexer.T_BLOCK_END, block_end_string),
            #(lexer.T_VARIABLE_START, variable_start_string),
            #(lexer.T_VARIABLE_END, variable_end_string),
            (lexer.T_COMMENT_START, comment_start_string),
            (lexer.T_COMMENT_END, comment_end_string),
            (lexer.T_NEWLINE, newline_sequence)
        ), key=lambda x:len(x[1]))
        self.variable_start_string = variable_start_string
        self.variable_end_string = variable_end_string
        self.extensions = extensions
        self.undefined = undefined
        self.autoescape = autoescape
        self.loader = loader
        self.trim_blocks = trim_blocks
        self.lstrip_blocks = lstrip_blocks
        self.disabled_tags = {}
        
    def preprocess(self, source, name=None, filename=None):
        """Preprocesses the source with all extensions.  This is automatically
        called for all parsing and compiling methods.
        """
        ret = source
        for ext in self.extensions:
            ret = ext.preprocess(ret, name, filename)
        return ret
        
    def _tokenize(self, source, name, filename=None):
        """
        Called by the parser to do the preprocessing and filtering for all the extensions.  
        
        Returns:
            iterable((token, val, pos)): returns an iterable of tokens
        """
        source = self.preprocess(source, name, filename)
        stream = lexer.TokenStream(source, name=name, fname=filename, tmap=self.token_map)
        for ext in self.extensions:
            stream = ext.filter_stream(stream)
        return stream        

default_env = Environment()
