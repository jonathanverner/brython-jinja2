from . import exceptions
from .utils import Location

T_BLOCK_START = 0
T_BLOCK_END = 1
T_VARIABLE_START = 2
T_VARIABLE_END = 3
T_COMMENT_START = 4
T_COMMENT_END = 5
T_HTML_ELEMENT_START = 6
T_HTML_ELEMENT_END = 7
T_HTML_COMMENT_START = 8
T_HTML_COMMENT_END = 9
T_NEWLINE = 10
T_SPACE = 12
T_OTHER = 13
T_EOS = 14

html_tokens = (
    (T_HTML_COMMENT_START, '<!--'),
    (T_HTML_COMMENT_END, '-->'),
    (T_HTML_ELEMENT_START, '<'),
    (T_HTML_ELEMENT_END, '>'),
    (T_SPACE, ' '),
)

TOKEN_NAMES = {
    T_BLOCK_START: 'BLOCK START',
    T_BLOCK_END: 'BLOCK END',
    T_VARIABLE_START: 'VARIABLE START',
    T_VARIABLE_END: 'VARIABLE END',
    T_COMMENT_START: 'COMMENT START',
    T_COMMENT_END: 'COMMENT END',
    T_HTML_ELEMENT_START: 'HTML ELEMENT START',
    T_HTML_ELEMENT_END: 'HTML ELEMENT END',
    T_HTML_COMMENT_START: 'HTML COMMENT START',
    T_HTML_COMMENT_END: 'HTML COMMENT END',
    T_NEWLINE: 'NEW LINE',
    T_SPACE: 'WHITESPACE',
    T_OTHER: 'OTHER',
    T_EOS: 'END OF STREAM'
}

def token_repr(tok):
    if type(tok) == int:
        return TOKEN_NAMES.get(tok, 'UNKNOWN TOKEN')
    else:
        return str(tok)

def tokens_to_strs(tmap, tokens):
    return [ s for t, s in tmap if t in tokens]

class TokenStream:
    def __init__(self, src, name=None, fname=None, tmap=[]):
        self.loc = Location(src, name=name, filename=fname, pos=0, ln=0, col=0)
        self.token_map = list(tmap)+[(T_SPACE,' ')]
        self.src = src
        self.left = []
        
    def push_left(self, token, val, pos):
        self.left.append((token,val, pos))
        
    def pop_left(self):
        return next(self)
    
    def peek(self):
        return self._next_tok(advance=False)
        
    def skip(self, tokens):
        if type(tokens) == int:
            rest = tokens-len(self.left)
            self.left = self.left[tokens:]
            while rest > 0:
                self.pop_left()
                rest -= 1
        else:
            self.cat_while(tokens)
        
    def cat_until(self, tokens):
        ret = ''
        toks=[]
        for t, val, loc in self:
            if t in tokens or val in tokens:
                self.push_left(t, val, loc)
                return ret
            else:
                toks.append((t,val,loc))
                ret += val
        raise exceptions.EOSException("End of stream while looking for TOKENS "+str([token_repr(t) for t in tokens]), src=self.src, location=self.loc)
        
    def cat_while(self, tokens):
        ret = ''
        t, val, pos = next(self)
        while t in tokens or val in tokens:
            ret += val
            t, val, pos = next(self)
        self.push_left(t, val, pos)
        return ret
    
    def _next_tok(self, advance=True):
        old_loc = self.loc.clone()
        if len(self.left) > 0:
            if advance:
                return self.left.pop(0)
            else:
                return self.left[0]
        if self.loc.pos == len(self.src):
            if advance:
                self.loc._inc_pos()
            return (T_EOS, '', old_loc)
        elif self.loc.pos > len(self.src):
            raise IndexError
        for (token, string) in self.token_map:
            if self.src[self.loc.pos:self.loc.pos+len(string)] == string:
                if advance:
                    self.loc._inc_pos(len(string))
                    if token == T_NEWLINE:
                        self.loc._newline()
                return (token, string, old_loc)
        if advance:
            self.loc._inc_pos()
        return (T_OTHER, self.src[old_loc.pos], old_loc)
    
    def find(self, needle):
        return self[:].find(needle)
    
    def __len__(self):
        return len(self.left)+len(self.src)
    
    def __getitem__(self, key):
        return self.remain_src[key]
        
    @property
    def remain_src(self):
        return ''.join([ t[1] for t in self.left ])+self.src[self.loc.pos:]
        

    def __iter__(self):
        return self
    
    def __next__(self):
        try:
            return self._next_tok(advance=True)
        except IndexError:
            raise StopIteration
