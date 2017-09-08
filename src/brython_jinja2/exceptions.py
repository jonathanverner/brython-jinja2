from .utils import Location

class LocatedError(BaseException):
    def __init__(self, message, src=None, location=None):
        self.src=src
        if type(location) != int or src is None:
            self.loc=location
        else:
            self.loc = Location.location_from_pos(self.src, location)
        self.message = message
        self.context_lines = 4
        try:
            self.print()
        except Exception as ex:
            print("EX:", str(ex))
        message = self.__str__()
        super().__init__(message)
    
    def context(self):
        if self.loc is None:
            ln="src: "+self.src[:70]
            if len(self.src) > 70:
                ln +=" ..."
            return [ln]
            
        ln = self.loc.line
        col = self.loc.column
        
        # Get the Context
        src_lines = self.src.split('\n')
        
        # If there is just a single line, don't bother with line numbers and context lines
        if len(src_lines) < 2:
            if isinstance(self.loc, Location):
                col = self.loc.column
            else:
                col = int(self.loc)
            return ["src: "+self.src,"     "+" "*col+"^"]
        
        start_ctx = max(ln-self.context_lines,0)
        end_ctx = min(ln+self.context_lines+1,len(src_lines))
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
            
        
            
    def print(self):
        print(str(self))
        
    def __str__(self):
        lines = []
        if self.loc is None:
            lines.append(type(self).__name__+": "+self.message)
        else:
            lines.append(type(self).__name__+" at "+str(self.loc)+": "+self.message)
        if self.src is not None:
            try:
                #print("CONTEXT:", self.context())
                lines.extend(self.context())
                #print("LINES:", lines)
            except Exception as ex:
                print(lines)
                print(self.context())
                print("EXCEPTION", ex)
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
