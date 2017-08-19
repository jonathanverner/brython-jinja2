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
        
