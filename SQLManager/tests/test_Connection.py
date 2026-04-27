import os
import sys

# Adiciona o diretório raiz ao path para importação
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, os.path.dirname(parent_dir))

from SQLManager.CoreConfig import CoreConfig
from SQLManager.connection import database_connection

def load_env_natively():
    """Lê o arquivo .env nativamente e joga para o os.environ"""
    # Tenta achar o .env na raiz do projeto ou na pasta SQLManager
    env_path = os.path.join(os.path.dirname(parent_dir), '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(parent_dir, '.env')
        
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Ignora linhas em branco e comentários
                if line and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    os.environ[key.strip()] = value.strip().strip("'\"")

def test_database_connection():
    print("="*50)
    print("TESTE PRÁTICO: CONEXÃO COM BANCO DE DADOS")
    print("="*50)
    
    # Carrega as variáveis do arquivo .env de forma nativa
    load_env_natively()

    # === ATENÇÃO: PREENCHA COM SUAS CREDENCIAIS REAIS NO ARQUIVO .env ===
    CoreConfig.configure(
        load_from_env=True
    )
    
    # Instancia a classe que acabamos de refatorar
    db = database_connection()
    
    print(f"Tipo do Banco (Dialeto): {db.db_type.upper()}")
    print(f"Servidor Alvo          : {db.db_params['server']}")
    print(f"Banco de Dados         : {db.db_params['database']}")
    print(f"Driver                 : {db.db_params['driver']}")
    print("-" * 50)
    print("Tentando estabelecer conexão...")
    
    if db.can_connect():
        print("\n[OK] can_connect() retornou True! (Servidor encontrado e credenciais aceitas)")
        
        try:
            db.connect()
            # Executa uma query simples que funciona no MySQL
            resultado = db.doQuery("SELECT 1 AS ConnectionTest")
            print(f"[OK] Query de teste executada com sucesso! Resultado: {resultado}")
        except Exception as e:
            print(f"\n[ERRO] Falha ao executar query: {e}")
        finally:
            db.disconnect()
            print("[OK] Desconectado do pool com segurança.")
    else:
        print("\n[ERRO] can_connect() retornou False.")
        print("DICA: Verifique se o servidor MySQL está ligado e se as credenciais no código estão corretas.")

if __name__ == '__main__':
    test_database_connection()