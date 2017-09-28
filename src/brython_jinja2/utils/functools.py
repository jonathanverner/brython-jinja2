import asyncio

def decorator(dec):
    def new_dec(func):
        ret = dec(func)
        ret.__decorated = func # pylint: disable=W0212
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
    def decorated(f):
        f.__inverse = func # pylint: disable=W0212
        func.__inverse = f # pylint: disable=W0212
        return f
    return decorated


def invertible(func):
    """
        Returns true if the function `func` is invertible.
    """
    return hasattr(func, '__inverse')


def invert(func):
    """
        Returns the inverse to function `func`
    """
    return func.__inverse # pylint: disable=W0212


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
    def wrap(*args, **kw) -> ProxyGenerator:
        return ProxyGenerator(func, args, kw)
    return wrap

@decorator
def factory(cls):

    def register(cls, name):
        @decorator
        def dec(product):
            cls.AVAILABLE[name] = product
            return product
        return dec

    def _filter(self, cond):
        self.ACTIVE = {k:v for k, v in self.AVAILABLE.items() if cond(k)}

    def create(self, name, *args, **kwargs):
        constr = self.ACTIVE[name]
        return constr(*args, **kwargs)

    cls.AVAILABLE = {}
    cls.register = register
    cls.create = create
    cls._filter = _filter # pylint: disable=W0212

    return cls

def throttle(sec: float):
    """
        A decorator which turns the decorated function/method into a coroutine.
        The coroutine waits for `sec` seconds and then calls the decorated function.
        If the coroutine is called while another call is waiting, it does nothing
        (effectively allowing at most 1 call in the given number of seconds).
    """
    @decorator
    def throttle_decorator(func):
        _throttle = False

        @asyncio.coroutine
        def decorated(*args, **kwargs):
            if _throttle:
                return
            _throttle = True
            yield asyncio.sleep(sec)
            func(*args, **kwargs)
            _throttle = False

        return decorated

    return throttle_decorator
