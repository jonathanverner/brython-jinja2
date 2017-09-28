from .utils import Location

class LocatedError(Exception):
    def __init__(self, message, src=None, location=None):
        if isinstance(location, Location):
            self.loc = location
        elif type(location) == int:
            if src is None:
                self.loc = Location(pos = location)
            else:
                self.loc = Location.location_from_pos(src, location)
        else:
            self.loc = Location(src)
        self.message = message
        self.context_lines = 4
       
    def __str__(self):
        lines = []
        lines.append(type(self).__name__+" at "+str(self.loc)+": "+self.message)
        lines.extend(self.loc.context(num_ctx_lines=self.context_lines))
        return "\n".join(lines)
        
    
class AbstractSyntaxError(LocatedError):
    """An error indicating invalid syntax"""


class TemplateError(LocatedError):
    """A general template error."""
        

class TemplateSyntaxError(AbstractSyntaxError, TemplateError):
    """Raised to tell the user that there is a problem with the template."""
    

class EOSException(TemplateSyntaxError):
    """Unexpected end of stream"""


class RenderError(TemplateError):
    """A general error rendering a template"""
    

class ExpressionError(LocatedError):
    """A general expression error """


class ExpressionSyntaxError(AbstractSyntaxError, ExpressionError):
    """A general expression error """


class NoSolution(ExpressionError):
    def __init__(self, expr, val, var):
        super().__init__("No solution for "+str(expr)+" = "+str(val)+" (over "+str(var)+")")
        

class DoesNotExistError(LocatedError):
    pass


class SkipSubtree(Exception):
    """Raised by visitors to indicate that the current subtree should be skipped. """
