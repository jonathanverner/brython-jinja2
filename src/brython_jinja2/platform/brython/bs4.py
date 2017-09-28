from browser import document, window, html

html.ROOT = html.maketag('ROOT')

def dom_from_html(html):
    """
        Creates a DOM structure from :param:`html`. The dom structure is
        wrapped in a <ROOT> element.
    """
    return Tag(html.ROOT(html))

def from_html(html):
    div = html.DIV(html)
    return from_native_element(div.firstChild)

def from_native_element(elt):
    if elt.nodeType == elt.TEXT_NODE:
        return NavigableString(elt.text)
    elif elt.nodeType == elt.ELEMENT_NODE:
        return Tag(elt)
    else:
        return None
 

class Element:
    def __init__(self, elt):
        self._elt = elt
    
    @property
    def parent(self):
        if self._elt.parentElement is None:
            return Document()
        else:
            return from_native_element(self._elt.parentElement)

    @property
    def parents(self):
        parent = self.parent
        while isinstance(parent, Tag):
            yield parent
            parent = parent.parent

    @property
    def next_sibling(self):
        return from_native_element(self._elt.nextSibling)

    @property
    def next_siblings(self):
        sib = self.next_sibling
        while sib is not None:
            yield sib
            sib = sib.next_sibling
    
    @property
    def previous_sibling(self):
        return from_native_element(self._elt.previousSibling)

    @property
    def previous_siblings(self):
        sib = self.previous_sibling
        while sib is not None:
            yield sib
            sib = sib.previous_sibling
    
    
    @property
    def next_element(self):
        if self._elt.firstChild is not None:
            return from_native_element(self._elt.firstChild)
        else:
            return self.next_sibling

    @property
    def next_elements(self):
        sib = self.next_element
        while sib is not None:
            yield sib
            sib = sib.next_element

    @property
    def previous_element(self):
        return self.previous_sibling or self.parent

    @property
    def previous_elements(self):
        sib = self.previous_element
        while sib is not None:
            yield sib
            sib = sib.previous_element


class NavigableString(Element):
    def __init__(self, string):
        super().__init__(document.createTextNode(string))
      
    def replace_with(self, string):
        self._elt.set_text(string)

class Attrs:
    def __init__(self, elt):
        self.elt = elt
        
    def keys(self):
        return [a.name for a in self.elt.attributes]
    
    def items(self):
        return [(a.name,a.value) for a in self.elt.attributes]
    
    def __setitem__(self, key, value):
        self.elt[key] = value
        
    def __getitem__(self, key):
        return self.elt[key]

class Tag(Element):
    def __init__(self, element_or_html):
        if isinstance(element_or_html, str):
            element_or_html = html.DIV(element_or_html).firstChild
        self._elt = element_or_html
        if self._elt.nodeType == self._elt.ELEMENT_NODE:
            self.name = self._elt.tagName
        else:
            self.name  = None

    def get(self, key):
        return self._elt.getAttribute(key)
    
    @property
    def attrs(self):
        return Attrs(self)

    @property
    def contents(self):
        return [ch for ch in self.children]

    @property
    def children(self):
        ch = self._elt.firstChild
        while ch:
            yield from_native_element(ch)
            ch = ch.nextSibling

    @property
    def descendants(self):
        for ch in self.children:
            yield ch
            for d in ch.descendants:
                yield d

    def extract(self) -> Element:
        if self.parent:
            self.parent._elt.removeChild(self._elt)
        return self

    def append(self, tag_or_html):
        if isinstance(tag_or_html, str):
            tag_or_html = from_html(tag_or_html)
        self._elt.appendChild(tag_or_html._elt)

    def insert(self, pos, tag_or_html):
        if isinstance(tag_or_html, str):
            tag_or_html = from_html(tag_or_html)
        self._elt.insertBefore(tag_or_html._elt, self._elt.children[pos])
        
    def insert_before(self, tag):
        self._elt.parentNode.insertBefore(tag._elt, self._elt)
        
    def insert_after(self, tag):
        self._elt.parentNode.insertBefore(tag._elt, self._elt.nextSibling)
            
    def decompose(self):
        self._elt.remove()

    def __getitem__(self, key):
        if key == 'value' and self.name.upper()=='INPUT':
            return self._elt.value
        ret = self._elt.getAttribute(key)
        if ret is None:
            raise KeyError(key)
        else:
            if key in ['class', 'rev', 'accept-charset', 'headers', 'accesskey']:
                ret = ret.split(' ')
                if len(ret) == 1:
                    ret = ret[0]
            return ret

    def __setitem__(self, key, value):
        if key == 'value' and self.name.upper()=='INPUT':
            return self._elt.set_value(value)
        
        if isinstance(value, list):
            value = ' '.join(list)
        self._elt.setAttribute(key, value)


def _test_attrs(tag, attrs):
    for (attr, val) in attrs.items():
        if not tag.get(attr) == val:
            return False
    return True


class Document:
    def __init__(self):
        pass

    def find_all(self, filter, attrs=None, limit=0, recursive=True, class_=None, **kwargs):
        ret = []
        count = 0
        attr_selector = ''
        if attrs is not None:
            kwargs.update(attrs)
        if class_ is not None:
            kwargs['class'] = class_
        if kwargs:
            for (attr, val) in kwargs.items():
                attr_selector += '['+attr+'='+str(val)+']'
        if isinstance(filter, list):
            filter = ','.join(filter)
        if isinstance(filter, str):
            ret = self[str+attr_selector]
            if limit > 0:
                ret = ret[:limit]
        elif callable(filter):
            for tag in self[attr_selector]:
                if filter(tag):
                    ret.append(tag)
                    count += 1
                if limit > 0 and count > limit:
                    break
        return ret

    def find(self, name, attrs=None, **kwargs):
        if attrs is not None:
            kwargs.update(attrs)
        attr_selector = ''
        if kwargs:
            for (attr, val) in kwargs.items():
                attr_selector += '['+attr+'='+str(val)+']'
        if isinstance(filter, list):
            filter = ','.join(filter)
        if isinstance(filter, str):
            ret = window.document.querySelector(str)
            if ret is None:
                return None
            else:
                return Tag(ret)
        elif callable(filter):
            for tag in self[attr_selector]:
                if filter(tag):
                    return tag
        return None

    @property
    def contents(self):
        return [Tag(ch.elt) for ch in window.document.children]

    @property
    def children(self):
        for ch in window.document.children:
            yield Tag(ch.elt)

    @property
    def descendants(self):
        for ch in self._elt.children:
            t = Tag(ch)
            yield t
            for d in t.descendants:
                yield d

    def select(self, selector):
        return self[selector]

    def __getitem__(self, selector):
        return [Tag(l) for l in window.document.querySelectorAll(selector)]

    def __getattr__(self, name):
        return self.find(name)



