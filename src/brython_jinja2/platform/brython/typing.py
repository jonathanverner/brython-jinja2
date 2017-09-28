class Any:
    pass

class DummyParametrizedType:
    @classmethod
    def __getitem__(cls, tp):
        return tp
    
class List(DummyParametrizedType):
    pass

class Optional(DummyParametrizedType):
    pass
    
class Union(DummyParametrizedType):
    pass

