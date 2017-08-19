def decorator(dec):
    def new_dec(fn):
        ret = dec(fn)
        ret.__decorated = fn
        return ret
    return new_dec


@decorator
def pure(func):
    """
        This decorator indicates that the function `func` is side-effect free.
    """
    func.__pure = True
    return func

def inverts(func):
    """
        This decorator indicates that the decorated function is the inverse to `func`
    """
    @decorator
    def dec(f):
        f.__inverse = func
        func.__inverse = f
        return f
    return dec


def invertible(func):
    """
        Returns true if the function `func` is invertible.
    """
    return hasattr(func,'__inverse')


def invert(func):
    """
        Returns the inverse to function `func`
    """
    return func.__inverse
        

# The following is taken from https://stackoverflow.com/questions/21808113/is-there-anything-similar-to-self-inside-a-python-generator

class ProxyGenerator(object):
    """This class implements the generator interface"""
    def __init__(self, generator, args, kw):
        self.generator = generator(self, *args, **kw)
    def __iter__(self):
        return self
    def __next__(self):
        return next(self.generator)
    next = __next__
    def send(self, value):
        return self.generator.send(value)


@decorator
def self_generator(func):
    def wrap(*args, **kw):
        return ProxyGenerator(func, args, kw)
    return wrap
