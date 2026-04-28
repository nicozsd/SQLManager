import sys
import os

# Ajuste de path para importar o SQLManager corretamente
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

from SQLManager.controller import TableController, EDTController

class MockTransaction:
    """
    Simula uma transação de banco de dados para capturarmos
    as queries geradas pelo SelectManager, InsertManager, etc.
    """
    def __init__(self):
        self.query = ""
        self.values = ()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass
        
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
        self.last_trs = MockTransaction()
        
    def transaction(self):
        self.last_trs = MockTransaction()
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
            
        # 4. Teste de DELETE
        print("\n  >>> Teste 4: DELETE filtrando por RECID")
        table.delete_from().where(table.RECID == 5).execute()
        print(f"      [QUERY]  {db.last_trs.query}")
        print(f"      [VALUES] {db.last_trs.values}")
        
        print(f"\n  ✅ Testes do dialeto {db_type.upper()} concluídos com sucesso!\n")
        print("-" * 70)

if __name__ == '__main__':
    run_dialect_tests()