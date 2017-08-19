DELIMITERS=r'\'"'
WHITESPACE = " \t\n"
NAME_CHARS = 'abcdefghijklmnopqrstuvwxyz_-0123456789'

class InvalidSyntax(Exception):
    def __init__(self, message, src, pos):
        self.src=src
        self.pos=pos
        self.message = message
        message = str(self)
        super().__init__(message)
    
    def __str__(self):
        return "InvalidSyntax at "+str(self.pos)+": "+self.message+"\nsrc: "+self.src+"\n     "+" "*self.pos+"^"
    
    def __repr__(self):
        return str(self)
    
class AttribStateMachine:
    def __init__(self, env):
        self._env = env
        self.clear()
        
    def clear(self):
        self._input = ''
        self._head = 0
        self._mem = {'ret':{}, 'name':'','val':None, 'delimiter':None}
        self._state = self.read_name
        
        
    def skip_chars(self, skip):
        for c in self._input[self._head:]:
            if c not in skip:
                break
            self._head += 1
            
    def check_string(self, string):
        old_head = self._head
        for c in string:
            if self.current_char != c:
                self._head = old_head
                return False
            else:
                self.move_right()
        return True
            
    def move_right(self, delta=1):
        self._head += delta
        
    @property
    def current_char(self):
        if self._head < len(self._input):
            return self._input[self._head]
        else:
            return None

    def store_attr(self):
        if len(self._mem['name']) > 0:
            self._mem['ret'][self._mem['name']]=self._mem['val']
        self._mem['val'] = None
        self._mem['name'] = ''
        self._mem['delimiter'] = None
        
    def read_name(self):
        if self._mem['name'].startswith(self._env.variable_start_string):
            if self.check_string(self._env.variable_end_string):
                self._mem['name'] += self._env.variable_end_string
                self.store_attr()
                self.skip_chars(WHITESPACE)
                return self.read_name
            else:
                self._mem['name'] += self.current_char
                self.move_right()
                return self.read_name
        else:
            if self.current_char in WHITESPACE:
                self.skip_chars(WHITESPACE)
                return self.test_eq
            elif self.current_char == '=':
                return self.test_eq
            elif self.current_char.lower() in NAME_CHARS:
                self._mem['name'] += self.current_char
                self.move_right()
                return self.read_name
            elif self._mem['name'] == '' and self.check_string(self._env.variable_start_string):
                self._mem['name'] = self._env.variable_start_string
                return self.read_name
            else:
                raise InvalidSyntax("Unexpected char '"+self.current_char+"', expecting valid name char.",src=self._input, pos=self._head)
        
    def read_val(self):
        if self.current_char in self._mem['delimiter']:
            self.store_attr()
            self.move_right()
            self.skip_chars(WHITESPACE)
            return self.read_name
        elif self._mem['delimiter']==WHITESPACE and self.current_char not in NAME_CHARS:
            raise InvalidSyntax("Unexpected char '"+self.current_char+"', expecting valid name char (did you forget to put quotes around value?).",src=self._input, pos=self._head)
        else:
            self._mem['val'] += self.current_char
            self.move_right()
            return self.read_val

    def test_eq(self):
        if self.current_char == '=':
            self.move_right()
            if self.current_char == ' ':
                self.skip_chars(WHITESPACE)
                return self.get_delim
            elif self.current_char.lower() in NAME_CHARS:
                self._mem['delimiter']=WHITESPACE
                self._mem['val'] = ''
                return self.read_val
            elif self.current_char in DELIMITERS:
                self._mem['delimiter']=self.current_char
                self._mem['val'] = ''
                self.move_right()
                return self.read_val
            else:
                raise InvalidSyntax("Unexpected char '"+self.current_char+"', expecting valid name char.",src=self._input, pos=self._head)
        else:
            self.store_attr()
            return self.read_name
            
    def get_delim(self):
        if self.current_char in DELIMITERS:
            self._mem['delimiter']=self.current_char
            self._mem['val'] = ''
            self.move_right()
            return self.read_val
        else:
            raise InvalidSyntax("Unexpected char '"+self.current_char+"', expecting a valid delimiter ("+DELIMITERS+")",src=self._input, pos=self._head)
        
    def step(self):
        self._state = self._state()
        
    def finished(self):
        return self._head >= len(self._input)
        
    def parse(self, string):
        self.clear()
        self._input = string
        self.skip_chars(WHITESPACE)
        while not self.finished():
            self.step()
        if self._state in [self.read_name, self.test_eq]:
            self.store_attr()
        elif self._state == self.get_delim:
            raise InvalidSyntax("Unexpected end of string, expecting a delimiter", src=self._input, pos=self._head)
        elif self._state == self.read_val:
            if self._mem['delimiter'] == WHITESPACE:
                self.store_attr()
            else:
                raise InvalidSyntax("Unexpected end of string while reading value of attribute '"+self._mem['name']+"'", src=self._input, pos=self._head)
        return self._mem['ret']

        

def skip_chars(string, pos, skip):
    for c in string[pos:]:
        if c in skip:
            pos += 1
        else:
            return pos
    return pos

def store_attr(mem):
    if len(mem['name']) > 0:
        mem['ret'][mem['name']]=mem['val']
    mem['val'] = None
    mem['name'] = ''
    mem['delimiter'] = None

def read_name(pos, string, mem):
    if string[pos] in WHITESPACE:
        return skip_chars(string,pos,WHITESPACE), test_eq
    elif string[pos] == '=':
        return pos, test_eq
    elif string[pos].lower() in NAME_CHARS:
        mem['name'] += string[pos]
        return pos+1, read_name
    else:
        raise InvalidSyntax("Unexpected char '"+string[pos]+"', expecting valid name char.",src=string, pos=pos)
    
def read_val(pos, string, mem):
    if string[pos] in mem['delimiter']:
        store_attr(mem)
        return skip_chars(string,pos+1,WHITESPACE), read_name
    elif mem['delimiter']==WHITESPACE and string[pos] not in NAME_CHARS:
        raise InvalidSyntax("Unexpected char '"+string[pos]+"', expecting valid name char (did you forget to put quotes around value?).",src=string, pos=pos)
    else:
        mem['val'] += string[pos]
        return pos+1, read_val

def test_eq(pos, string, mem):
    if string[pos] == '=':
        if string[pos+1] == ' ':
            return skip_chars(string, pos+1, WHITESPACE), get_delim
        elif string[pos+1].lower() in NAME_CHARS:
            mem['delimiter']=WHITESPACE
            mem['val'] = ''
            return pos+1, read_val
        elif string[pos+1] in DELIMITERS:
            mem['delimiter']=string[pos+1]
            mem['val'] = ''
            return pos+2, read_val
        else:
            raise InvalidSyntax("Unexpected char '"+string[pos+1]+"', expecting valid name char.",src=string, pos=pos+1)
    else:
        store_attr(mem)
        return pos, read_name
        
def get_delim(pos, string, mem):
    if string[pos] in DELIMITERS:
        mem['delimiter']=string[pos]
        mem['val'] = ''
        return pos+1, read_val
    else:
        raise InvalidSyntax("Unexpected char '"+string[pos]+"', expecting a valid delimiter ("+DELIMITERS+")",src=string, pos=pos)
    

def parse_attrs(string):
    mem = {'ret':{}, 'name':'','val':None, 'delimiter':None}
    pos = skip_chars(string, 0, WHITESPACE)
    state = read_name
    while pos < len(string):
        pos, state = state(pos, string, mem)
    if state in [read_name, test_eq]:
        store_attr(mem)
    elif state == get_delim:
        raise InvalidSyntax("Unexpected end of string, expecting a delimiter", src=string, pos=pos)
    elif state == read_val:
        if mem['delimiter'] == WHITESPACE:
            store_attr(mem)
        else:
            raise InvalidSyntax("Unexpected end of string while reading value of attribute '"+mem['name']+"'", src=string, pos=pos)
    return mem['ret']
