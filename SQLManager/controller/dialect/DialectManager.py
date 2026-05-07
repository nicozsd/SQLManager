from abc import ABC, abstractmethod
from typing import List

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
        # Extrai a instância do banco (posicional ou nomeada)
        db = kwargs.get('db') if 'db' in kwargs else (args[0] if args else None)
        dialect_name = getattr(db, 'db_type', 'sqlserver') if db else 'sqlserver'
        
        mixin_cls = DialectMixin.resolve(dialect_name)
        
        if not mixin_cls:
            raise ValueError(f"Dialeto {dialect_name} não suportado.")

        # Se a classe atual já possui o mixin, não recriamos (evita recursão)
        if mixin_cls in cls.__mro__:
            return object.__new__(cls)

        dynamic_name = f"{cls.__name__}_{dialect_name}"
        dynamic_cls = type(dynamic_name, (mixin_cls, cls), {})
        
        return object.__new__(dynamic_cls)

    # --- Interface Padrão (Contrato) ---
    @abstractmethod
    def format_insert_query(self, table_name: str, fields: List[str]) -> str: pass
    @abstractmethod
    def execute_insert_and_get_id(self, trs, query: str, values: tuple) -> int: pass
    @abstractmethod
    def get_columns_with_defaults_query(self) -> str: pass
    @abstractmethod
    def get_table_index_query(self) -> str: pass
    @abstractmethod
    def get_table_foreign_keys_query(self) -> str: pass
    @abstractmethod
    def format_table_ddl(self, content: str) -> str: pass

__all__ = ["DialectMixin", "ControllerBase"]