from bs4 import BeautifulSoup, Tag

def dom_from_html(html):
    """
        Creates a DOM structure from :param:`html`. The dom structure is
        wrapped in a <ROOT> element.
    """
    soup = BeautifulSoup('<root>'+html+'</root>', "html.parser")
    return soup

def from_html(html):
    soup = BeautifulSoup('<root>'+html+'</root>', "html.parser")
    return soup.firstChild

def from_native_element(elt):
    return elt

def __le__(self, other):
    self.append(other)
Tag.__le__ = __le__



class doc(BeautifulSoup):

    def __init__(self):
        super().__init__("<html><body></body></html>", "parser.html")

    def __getitem__(self, selector):
        return self.select(selector)

    def __le__(self, other):
        self.append(other)
        
    def insert_after(self, elt):
        raise NotImplementedError()
    
    def insert_before(self, elt):
        raise NotImplementedError()
