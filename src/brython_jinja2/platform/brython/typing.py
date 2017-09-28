class Any:
    pass

class DummyParametrizedType:
    @classmethod
    def __getitem__(cls, tp):
        return tp

class List(DummyParametrizedType):
    pass

class Tuple(DummyParametrizedType):
    pass

class Optional(DummyParametrizedType):
    pass

class Union(DummyParametrizedType):
    pass

class Iterable(DummyParametrizedType):
    pass

def NewType(self, name, tp):
    return tp

def cast(tp, x):
    return x

def TypeVar(self, name, bound=None):
    return object
