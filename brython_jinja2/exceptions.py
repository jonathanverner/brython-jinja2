class TemplateError(Exception):
    def __init__(self, message, location=None):
        super().__init__(message)
        self.loc = location
        self.source = None
        #self.message = message

    def __str__(self):
        lines = [self.message, '  ' + str(self.loc)]

        # if the source is set, add the line to the output
        if self.source is not None:
            try:
                line = self.source.splitlines()[self.loc._ln]
            except IndexError:
                line = None
            if line:
                lines.append('    ' + line.strip())

        return '\n'.join(lines)
    

class TemplateSyntaxError(TemplateError):
    """Raised to tell the user that there is a problem with the template."""

