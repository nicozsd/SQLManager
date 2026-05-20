import sys
import os
import types

# Ajuste de path para importar o SQLManager corretamente
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

sys.modules.setdefault("pyodbc", types.ModuleType("pyodbc"))
sys.modules.setdefault("pymysql", types.ModuleType("pymysql"))

from SQLManager.controller import TableController, EDTController
from SQLManager.connection.database_connection import Transaction, _Consult_Manager


class RawCursorCapture:
    def __init__(self):
        self.executed_query = None
        self.executed_params = None
        self.description = [("EMAIL",)]

    def execute(self, query, params=()):
        self.executed_query = query
        self.executed_params = params

    def fetchall(self):
        return [["teste@local"]]

    def close(self):
        pass


class RawConnectionCapture:
    def __init__(self):
        self.cursor_instance = RawCursorCapture()
        self.autocommit_value = True
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def autocommit(self, value):
        self.autocommit_value = value


class RawQueryDB(_Consult_Manager):
    def __init__(self, db_type):
        self.db_type = db_type
        self._connection = RawConnectionCapture()

    @property
    def connection(self):
        return self._connection


class RawQueryParentDB:
    def __init__(self, db_type):
        self.db_type = db_type
        self._connection = RawConnectionCapture()

    def _get_connection(self):
        return self._connection

    def _return_connection(self, conn):
        pass

    def _set_autocommit_on_conn(self, conn, value):
        conn.autocommit(value)

class MockTransaction:
    """
    Simula uma transação de banco de dados para capturarmos
    as queries geradas pelo SelectManager, InsertManager, etc.
    """
    def __init__(self, db_type=None):
        self.query = ""
        self.values = ()
        self.db_type = db_type
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass

    def transaction(self):
        return self
        
    def doQuery(self, query, values=()):
        self.query = query
        self.values = values
        
        # Simula o retorno de metadados se for uma consulta de colunas
        if "INFORMATION_SCHEMA.COLUMNS" in query.upper() or "SYS.COLUMNS" in query.upper():
            return [["RECID", "bigint", "NO"], ["NAME", "nvarchar", "YES"], ["AGE", "int", "YES"]]
            
        # Caso contrário, retorna um mock de dados da tabela
        return [[1, "Teste", 25]]
        
    def executeCommand(self, query, values=()):
        self.query = query
        self.values = values
        class Cursor:
            rowcount = 1
            def fetchall(self): return [[1, "Nicolas", 25]]
        return Cursor()
        
    # Mock da propriedade 'connection' e 'cursor' para simular a inserção no MySQL
    @property
    def connection(self):
        parent = self
        class MockConnection:
            def cursor(self):
                class MockCursor:
                    lastrowid = 1
                    def execute(self, q, v):
                        parent.query = q
                        parent.values = v
                    def close(self): pass
                return MockCursor()
        return MockConnection()

class MockDB:
    """
    Simula a classe database_connection
    """
    def __init__(self, db_type):
        self.db_type = db_type
        self.last_trs = MockTransaction(db_type)
        
    def transaction(self):
        self.last_trs = MockTransaction(self.db_type)
        return self.last_trs
        
    def doQuery(self, query, values=()):
        return self.last_trs.doQuery(query, values)

# Tabela Dummy para os testes
class UsersTable(TableController):
    def __init__(self, db):
        super().__init__(db, "Users")
        self.RECID = EDTController("onlyNumbers", int)
        self.NAME = EDTController("any", str)
        self.AGE = EDTController("onlyNumbers", int)

def run_dialect_tests():
    print("="*70)
    print(" TESTES DE GERAÇÃO DE QUERY DINÂMICA (SQL SERVER vs MYSQL) ")
    print("="*70)
    
    for db_type in ["sqlserver", "mysql"]:
        print(f"\n[{db_type.upper()}] Inicializando Instância...")
        db = MockDB(db_type)
        table = UsersTable(db)
        
        # 1. Teste de SELECT com Filtros, Paginação e Operadores Especiais
        print("\n  >>> Teste 1: SELECT com Filtros (==, IN) e Paginação (Limit/Offset)")
        table.select().where((table.NAME == "Teste") & (table.AGE.in_([20, 25, 30]))).limit(10).offset(20).execute()
        print(f"      [QUERY]  {db.last_trs.query}")
        print(f"      [VALUES] {db.last_trs.values}")
        expected_marker = "%s" if db_type == "mysql" else "?"
        unexpected_marker = "?" if db_type == "mysql" else "%s"
        assert expected_marker in db.last_trs.query
        assert unexpected_marker not in db.last_trs.query
        
        # 2. Teste de INSERT
        print("\n  >>> Teste 2: INSERT de um novo registro")
        table.NAME = "Maria"
        table.AGE = 30
        table.insert()
        print(f"      [QUERY]  {db.last_trs.query}")
        print(f"      [VALUES] {db.last_trs.values}")
            
        # 3. Teste de UPDATE (em massa)
        print("\n  >>> Teste 3: UPDATE em massa filtrando por Idade")
        table.update_recordset(where=table.AGE > 25, NAME="Senhora Maria")
        print(f"      [QUERY]  {db.last_trs.query}")
        print(f"      [VALUES] {db.last_trs.values}")
        assert expected_marker in db.last_trs.query
        assert unexpected_marker not in db.last_trs.query
            
        # 4. Teste de DELETE
        print("\n  >>> Teste 4: DELETE filtrando por RECID")
        table.delete_from().where(table.RECID == 5).execute()
        print(f"      [QUERY]  {db.last_trs.query}")
        print(f"      [VALUES] {db.last_trs.values}")
        assert expected_marker in db.last_trs.query
        assert unexpected_marker not in db.last_trs.query

        print("\n  >>> Teste 5: Controller instanciado diretamente com Transaction")
        with db.transaction() as trs:
            transaction_table = UsersTable(trs)
            transaction_table.select().where(transaction_table.NAME == "Teste").limit(1).execute()
        print(f"      [QUERY]  {db.last_trs.query}")
        print(f"      [VALUES] {db.last_trs.values}")
        assert expected_marker in db.last_trs.query
        assert unexpected_marker not in db.last_trs.query
        
        print(f"\n  [OK] Testes do dialeto {db_type.upper()} concluídos com sucesso!\n")
        print("-" * 70)


def run_raw_query_placeholder_tests():
    print("="*70)
    print(" TESTES DE PLACEHOLDER EM SQL BRUTO (MYSQL) ")
    print("="*70)

    raw_db = RawQueryDB("mysql")
    raw_db.doQuery("SELECT EMAIL FROM USERSTABLE WHERE EMAIL = ? OR USERID = ?", ("mail", "user"))
    assert raw_db.connection.cursor_instance.executed_query == "SELECT EMAIL FROM USERSTABLE WHERE EMAIL = %s OR USERID = %s"
    assert raw_db.connection.cursor_instance.executed_params == ("mail", "user")

    parent_db = RawQueryParentDB("mysql")
    with Transaction(parent_db) as trs:
        trs.doQuery("SELECT EMAIL FROM USERSTABLE WHERE EMAIL = ? OR USERID = ?", ("mail", "user"))

    assert parent_db._connection.cursor_instance.executed_query == "SELECT EMAIL FROM USERSTABLE WHERE EMAIL = %s OR USERID = %s"
    assert parent_db._connection.cursor_instance.executed_params == ("mail", "user")

    print("\n  [OK] SQL bruto respeita DBTYPE em conexao direta e transaction.\n")

if __name__ == '__main__':
    run_dialect_tests()
    run_raw_query_placeholder_tests()
