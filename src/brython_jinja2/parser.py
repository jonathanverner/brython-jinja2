from . import lexer
from . import nodes
from . import environment
from . import exceptions

class Parser:
    def __init__(self, environment, source, name=None, filename=None):
        self.env = environment
        self.src = source
        self.name = name
        self.filename = filename
        self.factory = nodes.NodeFactory(self.env)
        self._parse_stack = [] # Holds elements which are currently being parsed
        self._next_node = None  # Holds nodes which were parsed by a
    
    def parse(self):
        tokenstream = self.env._tokenize(self.src, self.name, self.filename)
        tree, __ = self._parse(tokenstream)
        return tree
       
    def _pop(self):
        del self._parse_stack[-1]
        
    def _parse(self, tokenstream, start_node=None):
        if start_node is not None:
            self._parse_stack.append(start_node)
        parsed_nodes = []
        for (token, val, pos) in tokenstream:
            if token == lexer.T_HTML_ELEMENT_START:
                node = nodes.HTMLElement(self, tokenstream, location=pos)
                if self._parse_stack and self._parse_stack[-1].ended_by(self, node):
                    self._pop()
                    return parsed_nodes, node
                self._next_node = node.parse_children(tokenstream, self)
                parsed_nodes.append(node)
            elif token == lexer.T_BLOCK_START:
                if self.env.lstrip_blocks and parsed_nodes:
                    parsed_nodes[-1].rstrip()
                tokenstream.skip([lexer.T_SPACE])
                node_name = tokenstream.cat_until([lexer.T_SPACE, lexer.T_BLOCK_END])
                node = self.factory.from_name(node_name, self, tokenstream, location=pos)
                if self._parse_stack and self._parse_stack[-1].ended_by(self, node):
                    self._pop()
                    return parsed_nodes, node
                self._next_node = node.parse_children(tokenstream, self)
                parsed_nodes.append(node)
            elif token == lexer.T_HTML_COMMENT_START:
                node = nodes.HTMLComment(self, tokenstream, location=pos)
                parsed_nodes.append(node)
            elif token == lexer.T_COMMENT_START:
                node = nodes.Comment(self, tokenstream, location=pos)
                parsed_nodes.append(node)
            elif token in [lexer.T_OTHER, lexer.T_NEWLINE, lexer.T_SPACE]:
                tokenstream.push_left(token, val, pos )
                node = nodes.Content(self, tokenstream, self)
                parsed_nodes.append(node)
            elif token == lexer.T_EOS:
                if self._parse_stack and not self._parse_stack[-1].ended_by(self, None):
                    raise exceptions.EOSException("End of stream reached while parsing "+str(start_node), src=self.src, location=tokenstream.loc)
                else:
                    if self._parse_stack:
                        tokenstream.push_left(token, val, pos)
                        self._pop()
                    return parsed_nodes, None
            else:
                raise exceptions.TemplateSyntaxError("Unexpected token: "+str(token)+" ("+val+")", src=self.src, location=pos)
            
            while self._next_node:
                node = self._next_node
                if self._parse_stack and self._parse_stack[-1].ended_by(self, node):
                    self._pop()
                    return parsed_nodes, node
                self._next_node = node.parse_children(tokenstream, self)
                parsed_nodes.append(node)

        return parsed_nodes, None
                
                
    
