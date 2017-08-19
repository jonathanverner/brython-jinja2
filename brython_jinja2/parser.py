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
    
    def parse(self):
        tokenstream = self.env._tokenize(self.src, self.name, self.filename)
        return self._parse(tokenstream)
    
    def _parse(self, tokenstream, start_node=None):
        parsed_nodes = []
        for (token, val, pos) in tokenstream:
            if token == lexer.T_HTML_ELEMENT_START:
                args = tokenstream.cat_until([lexer.T_HTML_ELEMENT_END])
                node = nodes.HTMLElement(location=pos, env=self.env)
                node.parse(args, tokenstream, self)
            elif token == lexer.T_HTML_COMMENT_START:
                comment = tokenstream.cat_until(tokenstream, [lexer.T_HTML_ELEMENT_END])
                node = nodes.HTMLComment(comment, location=pos, env=self.env)
            elif token == lexer.T_BLOCK_START:
                if self.env.lstrip_blocks and len(parsed_nodes > 0):
                    parsed_nodes[-1].rstrip()
                tokenstream.skip([lexer.T_SPACE])
                node_name = tokenstream.cat_until([lexer.T_SPACE, lexer.T_BLOCK_END])
                args = tokenstream.cat_until([lexer.T_BLOCK_END])
                node = self.factory.from_name(node_name, location=pos)
                parsed_nodes.append(node)
                if self.env.trim_blocks:
                    tokenstream.skip([lexer.T_SPACE, lexer.T_NEWLINE])
                node.parse(args, tokenstream, self)
            elif token == lexer.T_COMMENT_START:
                node = nodes.Comment(location=pos, env=self.env)
                node.parse(args, tokenstream, self)
            elif token == lexer.T_OTHER:
                content = val+tokenstream.cat_while([lexer.T_OTHER, lexer.T_NEWLINE, lexer.T_SPACE])
                node = nodes.Text(content, location=pos, env=self.env)
            else:
                raise exceptions.TemplateSyntaxError("Unexpected token"+str(token)+" ("+val+")", location=pos)
            if start_node is not None and node.ends(start_node):
                return parsed_nodes, node
            else:
                parsed_nodes.append(node)
        if start_node is not None:
            raise lexer.EOSException("End of stream reached while parsing "+str(start_node), location=tokenstream.loc)
        return parsed_nodes
                
                
    
