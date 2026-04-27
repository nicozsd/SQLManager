from abc import ABC, abstractmethod

config = {
    "dialect": "mysql"
}

class DialectMixin(ABC):
    _registry = {}

    def __init_subclass__(cls, dialect=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if dialect:
            DialectMixin._registry[dialect] = cls

    @classmethod
    def resolve(cls, name):
        return cls._registry.get(name)

    # Métodos padrão (Interface)
    def db_name(self):
        return "Generic"

    def process(self):
        return "END"

# --- 2. As Implementações (Mixins) ---
class MySQLMixin(DialectMixin, dialect="mysql"):
    def db_name(self):
        return "MySQL"

    def process(self):
        # Chama o próximo na cadeia (BaseProcess)
        result = super().process() 
        return f"[MYSQL] {result}"

class PostgresMixin(DialectMixin, dialect="postgres"):
    def db_name(self):
        return "Postgres"

    def process(self):
        result = super().process()
        return f"[POSTGRES] {result}"

class ControllerBase(DialectMixin):
    """
    Esta classe garante que os métodos existam e resolve o dialeto.
    """
    def __new__(cls, *args, **kwargs):
        dialect_name = config.get("dialect")
        mixin_cls = DialectMixin.resolve(dialect_name)
        
        if not mixin_cls:
            raise ValueError(f"Dialeto {dialect_name} não suportado.")

        dynamic_name = f"{cls.__name__}_{dialect_name}"
        dynamic_cls = type(dynamic_name, (mixin_cls, cls), {})
        
        instance = object.__new__(dynamic_cls)
        return instance

#TableController
class Controller(ControllerBase):
    def __init__(self):
        super().__init__()
        pass

    def select(self) -> str:
        return f"SELECT * FROM {self.db_name()}"

cont = Controller()
print(cont.select())