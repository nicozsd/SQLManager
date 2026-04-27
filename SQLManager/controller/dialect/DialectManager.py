from abc import ABC, abstractmethod

from ...CoreConfig import CoreConfig

class DialectMixin(ABC):
    _registry = {}

    def __init_subclass__(cls, dialect=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if dialect:
            DialectMixin._registry[dialect] = cls

    @classmethod
    def resolve(cls, name):
        return cls._registry.get(name)

class ControllerBase(DialectMixin):
    """
    Esta classe garante que os métodos existam e resolve o dialeto.
    """
    def __new__(cls, *args, **kwargs):
        dialect_name = CoreConfig.get("dialect")
        mixin_cls = DialectMixin.resolve(dialect_name)
        
        if not mixin_cls:
            raise ValueError(f"Dialeto {dialect_name} não suportado.")

        dynamic_name = f"{cls.__name__}_{dialect_name}"
        dynamic_cls = type(dynamic_name, (mixin_cls, cls), {})
        
        instance = object.__new__(dynamic_cls)
        return instance

__all__ = ["DialectMixin", "ControllerBase"]