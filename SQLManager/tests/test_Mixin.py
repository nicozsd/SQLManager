from abc import ABC, abstractmethod

# Simulador do CoreConfig
config = {
    "dialect": "sqlserver"
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

    # --- Interface Padrão (Contrato) ---
    def db_name(self) -> str:
        return "Generic"

    def format_pagination(self, limit: int, offset: int) -> str:
        raise NotImplementedError
        
    def format_index_hint(self, index_hint: str) -> str:
        raise NotImplementedError

    def get_parameter_marker(self) -> str:
        raise NotImplementedError

# --- 2. As Implementações (Mixins) ---
class SQLServerMixin(DialectMixin, dialect="sqlserver"):
    def db_name(self):
        return "SQLServer"
        
    def format_pagination(self, limit: int, offset: int) -> str:
        return f" OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"

    def format_index_hint(self, index_hint: str) -> str:
        return f" WITH (INDEX({index_hint}))" if index_hint else ""

    def get_parameter_marker(self) -> str:
        return "?"

class MySQLMixin(DialectMixin, dialect="mysql"):
    def db_name(self):
        return "MySQL"

    def format_pagination(self, limit: int, offset: int) -> str:
        return f" LIMIT {limit} OFFSET {offset}"

    def format_index_hint(self, index_hint: str) -> str:
        return f" USE INDEX ({index_hint})" if index_hint else ""

    def get_parameter_marker(self) -> str:
        return "%s"

# --- 3. Simulador do SelectManager ---
class SelectManagerMock(DialectMixin):
    """
    Simula a classe que vai herdar os comportamentos dinamicamente
    """
    def __new__(cls, *args, **kwargs):
        dialect_name = config.get("dialect")
        mixin_cls = DialectMixin.resolve(dialect_name)
        
        if not mixin_cls:
            raise ValueError(f"Dialeto {dialect_name} não suportado.")

        dynamic_cls = type(f"{cls.__name__}_{dialect_name}", (mixin_cls, cls), {})
        return object.__new__(dynamic_cls)

    def build_query(self) -> str:
        # Simulando a montagem de uma query (SelectManager.execute)
        query = f"SELECT * FROM Users{self.format_index_hint('idx_users')}"
        query += f" WHERE status = {self.get_parameter_marker()}"
        query += self.format_pagination(limit=10, offset=20)
        return query

# --- 4. Executando o Teste ---
print("="*50)
print("TESTE: SQL SERVER")
print("="*50)
config["dialect"] = "sqlserver"
manager_sql = SelectManagerMock()
print(f"Dialeto ativo: {manager_sql.db_name()}")
print(f"Query Gerada : {manager_sql.build_query()}")

print("\n" + "="*50)
print("TESTE: MYSQL")
print("="*50)
config["dialect"] = "mysql"
manager_mysql = SelectManagerMock()
print(f"Dialeto ativo: {manager_mysql.db_name()}")
print(f"Query Gerada : {manager_mysql.build_query()}")