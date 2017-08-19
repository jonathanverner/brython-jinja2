"""
    The template submodule provides data-binding utilities.
"""

class Location:
    
    @classmethod
    def location_from_pos(cls, src, pos, name=None, filename=None):
        loc = Location(name=name, filename=filename, ln=0, col=0, pos=0)
        for c in src:
            loc._inc_pos()
            if c == '\n':
                loc._newline()
            if loc.pos >= pos:
                break
        return loc
        
    def __init__(self, name=None, filename=None, ln=0, col=0, pos=0):
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
        return Location(name=self._name, filename=self._fname, ln=self._ln, col=self._col, pos=self._pos)
        
    def __str__(self):
        ret = '{ln}, {col}'.format(ln=self.line, col=self.column)
        if self._fname is not None:
            ret+="("+self._fname+")"
        if self._name is not None:
            ret+=self._name
        return ret
    
    def __repr__(self):
        return str(self)
