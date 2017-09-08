from bs4 import BeautifulSoup, Tag


def dom_from_html(html):
    """
        Creates a DOM structure from :param:`html`
    """

    soup = BeautifulSoup(html, "html.parser")
    return soup.contents[0]

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
