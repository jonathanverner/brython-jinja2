from . import lexer
from . import templatenodes as nodes
from . import environment
from . import exceptions
from .platform.typing import List, Optional, Tuple



class Parser:
    def __init__(self, environment: environment.Environment = environment.default_env) -> None:
        self.env = environment
        self.factory = nodes.NodeFactory(self.env)

    def parse(self, source: str, name: str = None, filename: str = None):
        tokenstream = self.env._tokenize(source, name, filename)
        tree, __ = self._parse(tokenstream)
        return tree

    def _parse(self, tokenstream: lexer.TokenStream, end_node_names: List[str] = []) -> Tuple[List[nodes.Node], Optional[str]]:
        parsed_nodes = [] # type: List[nodes.Node]
        for (token, val, pos) in tokenstream:
            if token == lexer.T_BLOCK_START:
                if self.env.lstrip_blocks and parsed_nodes:
                    parsed_nodes[-1].rstrip()
                tokenstream.skip([lexer.T_SPACE])
                node_name = tokenstream.cat_until([lexer.T_SPACE, lexer.T_BLOCK_END])
                if node_name in end_node_names:
                    return parsed_nodes, node_name
                node = self.factory.from_name(self, node_name, tokenstream, location=pos)
                parsed_nodes.append(node)
            elif token == lexer.T_VARIABLE_START:
                node = nodes.Variable(self, tokenstream, location=pos)
                parsed_nodes.append(node)
            elif token == lexer.T_COMMENT_START:
                if self.env.lstrip_blocks and parsed_nodes:
                    parsed_nodes[-1].rstrip()
                node = nodes.Comment(self, tokenstream, location=pos)
                parsed_nodes.append(node)
            elif token == lexer.T_EOS:
                if end_node_names:
                    raise exceptions.EOSException("End of stream reached while looking for"+str(end_node_names), location=tokenstream.loc)
                return parsed_nodes, None
            else:
                tokenstream.push_left(token, val, pos )
                node = nodes.Content(self, tokenstream, location=pos)
                parsed_nodes.append(node)
        return parsed_nodes, None



