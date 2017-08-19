from . import exceptions

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

html_tokens = (
    (T_HTML_COMMENT_START, '<!--'),
    (T_HTML_COMMENT_END, '-->'),
    (T_HTML_ELEMENT_START, '<'),
    (T_HTML_ELEMENT_END, '>'),
    (T_SPACE, ' '),
)


class EOSException(exceptions.TemplateSyntaxError):
    pass

class Location:
    def __init__(self, name=None, filename=None, ln=0, col=0, pos=0):
        self._name = name
        self._fname = filename
        self._ln = ln
        self._col = col
        self._pos = pos
        
    @property
    def pos(self):
        return self._pos
    
    def _inc_pos(self, delta=1):
        self._pos += delta
        self._col += delta
        
    def _newline(self):
        self._ln += 1
        self._col = 0
        
    def clone(self):
        return Location(name=self._name, filename=self._fname, ln=self._ln, col=self._col, pos=self._pos)
        
    def __str__(self):
        return "{name}({fname}):{ln}, {col}".format(name=self._name, fname=self._fname, ln=self._ln, col=self._col)
    
    def __repr__(self):
        return str(self)

class TokenStream:
    def __init__(self, src, name=None, fname=None, tmap=[]):
        self.loc = Location(name=name, filename=fname, pos=0, ln=0, col=0)
        self.token_map = list(tmap) + list(html_tokens)
        self.src = src
        self.left = []
        
    def push_left(self, token, val, pos):
        self.left.append((token,val,pos))
        
    def skip(self, tokens):
        self.cat_while(tokens)
        
    def cat_until(self, tokens):
        ret = ''
        toks=[]
        for t, val, loc in self:
            toks.append((t,val,str(loc)))
            if t in tokens:
                return ret
            else:
                ret += val
        #raise Exception("End of stream while looking for TOKENS '"+str(tokens)+"' in '"+str(self.token_map)+"' at "+str(self.loc) +"('"+self.src+"') got "+str(toks))
        raise EOSException("End of stream while looking for TOKENS "+str(tokens), location=self.loc)
        
    def cat_while(self, tokens):
        ret = ''
        t, val, pos = next(self)
        while t in tokens:
            ret += val
            t, val, pos = next(self)
        self.push_left(t, val, pos)
        return ret
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if len(self.left) > 0:
            return self.left.pop(0)
        if self.loc.pos >= len(self.src):
            raise StopIteration
        for (token, string) in self.token_map:
            if self.src[self.loc.pos:self.loc.pos+len(string)] == string:
                self.loc._inc_pos(len(string))
                if token == T_NEWLINE:
                    self.loc._newline()
                return (token, string, self.loc)
        old_loc = self.loc.clone()
        self.loc._inc_pos()
        return (T_OTHER, self.src[old_loc.pos], old_loc)
