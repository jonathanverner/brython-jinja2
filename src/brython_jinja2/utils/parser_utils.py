
def skip_chars(string, pos, skip):
    while string[pos] in skip:
        pos += 1
    return pos

def cat_until(string, pos, until):
    ret = ''
    while string[pos] not in until:
        ret += string[pos]
        pos += 1
    return pos, ret

def cat_while(string, pos, cond):
    ret = ''
    while string[pos] in cond:
        ret += string[pos]
        pos += 1
    return pos, ret



class MultiMatcher:
    """
       Python implementation of Aho-Corasick string matching
       
       Alfred V. Aho and Margaret J. Corasick, "Efficient string matching: an aid to
       bibliographic search", CACM, 18(6):333-340, June 1975.
       
       <http://xlinux.nist.gov/dads//HTML/ahoCorasick.html>
       
       Copyright (C) 2015 Ori Livneh <ori@wikimedia.org>
       
       Licensed under the Apache License, Version 2.0 (the "License");
       you may not use this file except in compliance with the License.
       You may obtain a copy of the License at
       
           http://www.apache.org/licenses/LICENSE-2.0
       
       Unless required by applicable law or agreed to in writing, software
       distributed under the License is distributed on an "AS IS" BASIS,
       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
       See the License for the specific language governing permissions and
       limitations under the License.
       
       Example:
       
            matcher = MultiMatcher(['token','end'])
            
            pos, match = matcher.find('this is a token and this is the end')
            assert pos == 10 and match == 'token'
            
            pos, match = matcher.find('this is a token and this is the end', pos+1)
            assert pos == 32 and match == 'end'   
    """
    _FAIL = -1
    
    def __init__(self, needles):
        """
            Constructs a state machine which searches a string for needles.
            
            Args:
              needles (list[str]): the list of strings to search for
        """
        self.transitions = {}
        self.outputs = {}
        self.fails = {}

        new_state = 0

        for needle in needles:
            state = 0

            for j, char in enumerate(needle):
                res = self.transitions.get((state, char), self._FAIL)
                if res == self._FAIL:
                    break
                state = res

            for char in needle[j:]:
                new_state += 1
                self.transitions[(state, char)] = new_state
                state = new_state

            self.outputs[state] = [needle]

        queue = []
        for (from_state, char), to_state in self.transitions.items():
            if from_state == 0 and to_state != 0:
                queue.append(to_state)
                self.fails[to_state] = 0

        while queue:
            r = queue.pop(0)
            for (from_state, char), to_state in self.transitions.items():
                if from_state == r:
                    queue.append(to_state)
                    state = self.fails[from_state]

                    while True:
                        res = self.transitions.get((state, char), state and self._FAIL)
                        if res != self._FAIL:
                            break
                        state = self.fails[state]

                    failure = self.transitions.get((state, char), state and self._FAIL)
                    self.fails[to_state] = failure
                    self.outputs.setdefault(to_state, []).extend(
                        self.outputs.get(failure, []))
        
    def find(self, haystack, start_pos=0):
        """
            Uses the statemachine to find the first occurence of some needle in the `haystack`.
            
            Args:
                haystack (str):  The string to search
                start_pos (int): Start searching from the given position
                
            Returns:
                int, str: the position of the first occurence in haystack (or -1 if not found), the needle found (or None if not found)
        """
        state = 0
        for i, char in enumerate(haystack[start_pos:]):
            while True:
                res = self.transitions.get((state, char), state and self._FAIL)
                if res != self._FAIL:
                    state = res
                    break
                state = self.fails[state]

            for match in self.outputs.get(state, ()):
                pos = i - len(match) + 1
                return (pos+start_pos, match)
        return (-1, None)
