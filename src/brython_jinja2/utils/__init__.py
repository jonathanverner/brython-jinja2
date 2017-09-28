"""
    Miscellaneous utility classes and functions.
"""


class Location:
    
    @classmethod
    def location_from_pos(cls, src, pos, name=None, filename=None):
        loc = Location(src, name=name, filename=filename, ln=0, col=0, pos=0)
        for c in src:
            loc._inc_pos()
            if c == '\n':
                loc._newline()
            if loc.pos >= pos:
                break
        return loc
        
    def __init__(self, src='', name=None, filename=None, ln=0, col=0, pos=0):
        self._src = src
        self._name = name
        self._fname = filename
        self._ln = ln
        self._col = col
        self._pos = pos
        
    @property
    def line(self):
        return self._ln
    
    @property
    def column(self):
        return self._col
    
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
        return Location(self._src, name=self._name, filename=self._fname, ln=self._ln, col=self._col, pos=self._pos)
        
    def context(self, num_ctx_lines=4):
        ln = self.line
        col = self.column
        
        # Get the Context
        src_lines = self._src.split('\n')
        
        # If there is just a single line, don't bother with line numbers and context lines
        if len(src_lines) < 2:
            return ["src: "+self._src,"     "+" "*col+"^"]
        
        start_ctx = max(ln-num_ctx_lines,0)
        end_ctx = min(ln+num_ctx_lines+1,len(src_lines))
        prev_lines = src_lines[start_ctx:ln]
        post_lines = src_lines[ln+1:end_ctx]
        
        # Get the current line with a caret indicating the column
        cur_lines = ['', src_lines[ln], " "*col+"^"]

        
        # Prepend line numbers & current line marker
        line_num_len = len(str(end_ctx))
        for i in range(len(prev_lines)):
            prev_lines[i] = '  '+str(start_ctx+i).ljust(line_num_len+2) + prev_lines[i]
            
        cur_lines[1] = '> '+str(ln).ljust(line_num_len)+ cur_lines[1]
        cur_lines[2] = '  '+''.ljust(line_num_len) + cur_lines[2]

        for i in range(len(post_lines)):
            post_lines[i] = '  '+str(ln+i).ljust(line_num_len+2) + post_lines[i]
            
        return prev_lines+post_lines+cur_lines
    
    def __str__(self):
        ret = '{ln}, {col}'.format(ln=self.line, col=self.column)
        if self._fname is not None:
            ret+="("+self._fname+")"
        if self._name is not None:
            ret+=self._name
        return ret
    
    def __repr__(self):
        return str(self)
