''' [BEGIN CODE] Teste de injeção de Dialetos no ModelUpdater '''
import sys
import os

# Ajuste de path para importar o SQLManager corretamente a partir da pasta tests
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

from SQLManager._model._model_update import ModelUpdaterBase
from SQLManager import CoreConfig

def run_tests():
    print("="*70)
    print(" TESTANDO RESOLUÇÃO DINÂMICA DE DIALETOS NO MODEL UPDATER ")
    print("="*70)

    # DDL Genérico de teste (Baseado em T-SQL nativo)
    dummy_ddl = """[RECID] [bigint] IDENTITY(1,1) NOT NULL,
[NAME] [nvarchar](100) NOT NULL,
[ISDISABLE] [bit] NOT NULL DEFAULT 0"""

    # 1. Testando MySQL
    print("\n[TESTE 1] Simulando ambiente com DB_TYPE = 'mysql'")
    os.environ['DB_TYPE'] = 'mysql'
    CoreConfig.configure(db_type='mysql')
    updater_mysql = ModelUpdaterBase()
    
    print(f"  -> Classe resolvida: {updater_mysql.__class__.__name__}")
    print(f"  -> Dialeto ativo: {updater_mysql.db_name()}")
    print(f"  -> Query de Tabelas:\n{updater_mysql.get_model_tables_query().strip()}")
    
    assert "DATABASE()" in updater_mysql.get_model_tables_query(), "Falha: Query não possui a sintaxe do MySQL!"
    assert "%s" in updater_mysql.get_model_columns_query(), "Falha: Query de colunas não usa marcador %s nativo do MySQL"
    
    formatted_mysql_ddl = updater_mysql.format_table_ddl(dummy_ddl)
    assert "AUTO_INCREMENT PRIMARY KEY" in formatted_mysql_ddl and "[" not in formatted_mysql_ddl, "Falha: DDL não formatado corretamente para MySQL!"

    # 2. Testando SQL Server
    print("\n[TESTE 2] Simulando ambiente com DB_TYPE = 'sqlserver'")
    os.environ['DB_TYPE'] = 'sqlserver'
    CoreConfig.configure(db_type='sqlserver')
    updater_sql = ModelUpdaterBase()
    
    print(f"  -> Classe resolvida: {updater_sql.__class__.__name__}")
    print(f"  -> Dialeto ativo: {updater_sql.db_name()}")
    print(f"  -> Query de Tabelas:\n{updater_sql.get_model_tables_query().strip()}")
    
    assert "DATABASE()" not in updater_sql.get_model_tables_query(), "Falha: Query possui sintaxe indevida do MySQL no SQL Server!"
    assert "?" in updater_sql.get_model_columns_query(), "Falha: Query de colunas não usa marcador ? nativo do SQL Server"
    
    formatted_sql_ddl = updater_sql.format_table_ddl(dummy_ddl)
    assert formatted_sql_ddl == dummy_ddl, "Falha: DDL foi alterado indevidamente no SQL Server!"

    # 3. Testando Fallback (Padrão)
    print("\n[TESTE 3] Simulando ambiente Vazio / Fallback para SQLSERVER")
    if 'DB_TYPE' in os.environ:
        del os.environ['DB_TYPE']
    CoreConfig.reset()
    updater_default = ModelUpdaterBase()
    assert updater_default.db_name() == "SQLServer", "Falha: Fallback nativo falhou!"
    print("  -> Fallback validado e funcionando com segurança para SQLServer.")

    print("\n" + "="*70)
    print(" ✅ TODOS OS TESTES PASSARAM COM SUCESSO! ")
    print("="*70)

if __name__ == '__main__':
    run_tests()