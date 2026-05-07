import os
import pyodbc
import pymysql
import threading

from queue import Queue, Empty
from typing import Union, TypeAlias
from ..CoreConfig import CoreConfig

class _TTS_Manager:
    '''
    Gerenciador de níveis de transação (TTS)
    '''
    
    def _set_autocommit(self, value: bool):
        '''A ser implementado nas classes filhas (Define comportamento do autocommit)'''
        pass
    
    def ttsbegin(self):
        '''Adiciona um nível de transação'''
        if self.tts_level == 0:
            self._set_autocommit(False)
        self.tts_level += 1

    def ttscommit(self):
        '''Remove um nível de transação, e faz commit se for o último'''
        if self.tts_level > 0:
            self.tts_level -= 1
            if self.tts_level == 0:
                self.connection.commit()
                self._set_autocommit(True)

    def ttsabort(self):
        '''Aborta a transação, desfazendo todas as operações'''
        if self.tts_level > 0:
            self.connection.rollback()
            self._set_autocommit(True)
            self.tts_level = 0

class _Consult_Manager:
    '''
    Gerenciador de consultas (queries) e comandos (execute)
    '''
    
    def doQuery(self, query: str, params: tuple = (), ret_cols: bool = False): 
        '''Realiza uma query na conexão'''
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()
        return (results, columns) if ret_cols else results
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
    def executeCommand(self, command: str, params: tuple = ()): 
        '''Executa um comando na conexão'''
        cursor = self.connection.cursor()
        cursor.execute(command, params)
        affected = getattr(cursor, 'rowcount', 0)

        if isinstance(self, database_connection):
            self.connection.commit()

        cursor.close()
        return affected
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''

class Transaction (_TTS_Manager, _Consult_Manager):
    """
    Transação isolada com conexão própria.

    Uma transação totalmente isolada, semelhante a um "copia e cola" da database_connection,
    mas com conexão própria.

        with database.transaction() as trs:
            -Use a transação isolada
            ProductsTable = source.TablePack.ProductsTable(trs)
            -No final, commit ou abort é automático

        - Instancie tabelas usando a transaction, não a database_connection.
        - Você pode usar begin, commit, abort normalmente dentro da transação,
          ou deixar o 'with' cuidar disso automaticamente.
        - Se usar ttsbegin da TableController integrada à tabela, será um nível de tts
          para a consulta da tabela, não para a transação inteira.

        O commit ou abort é feito automaticamente ao final do bloco 'with'.
    """
    
    def __init__(self, _dbself: 'database_connection'):
        self._db         = _dbself
        self._connection = None
        self._tts_level  = 0
    
    @property
    def connection(self):
        '''so valida conexão, se não tiver da erro'''
        if not self._connection:
            raise Exception("Use 'with transaction'")
        return self._connection
    
    @property
    def tts_level(self):
        return self._tts_level
    
    @tts_level.setter
    def tts_level(self, value):
        self._tts_level = value
        
    def _set_autocommit(self, value: bool):
        self._db._set_autocommit_on_conn(self.connection, value)
    
    def __enter__(self):
        '''monta um transação (isolada)'''
        self._connection = self._db._get_connection()
        self._set_autocommit(True)
        self.ttsbegin()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        '''finaliza a transação commit ou abort'''
        try:
            if exc_type:
                self.ttsabort()
            else:
                while self._tts_level > 0:
                    self.ttscommit()
        finally:
            self._db._return_connection(self._connection)
            self._connection = None
        return False

    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''
    def transaction(self):
        """
        Retorna um context manager que cria uma "transação filha" (nested).
        Uso: `with trs.transaction() as trs:` ou `with trs.transaction() as trs:` —
        ele aumenta o nível TTS e faz commit/abort local (usa a mesma conexão do pai).
        """
        parent = self

        class _NestedTransaction:
            def __enter__(self):
                parent.ttsbegin()
                return parent

            def __exit__(self, exc_type, exc_value, tb):
                if exc_type:
                    parent.ttsabort()
                else:
                    parent.ttscommit()
                return False

        return _NestedTransaction()
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #1 / made by: Nicolas Santos / created: 23/02/2026 '''    

class database_connection (_TTS_Manager, _Consult_Manager):
    '''
    classe de controle de banco com pool de conexões e transações
    Foi realizado o processo de modificação para que seja possivel usar transações isoladas (KNEX como foi demonstrado)

    porem todo seu codigo legado continua funcionando normalmente.
    então para necessidades mais "unicas" como UMA tabela que não vai usar niveis de tts pode usar database
    SENÃO usar a transaction.
    modelo de uso:
        database = database_connection()
        database.connect()
        table = source.TablePack.ProductsTable(database)        
        table.insert()
        database.disconnect()
    
    OBS: se for isolado consulte a classe transaction
    '''
    
    def __init__(self, 
                _Server:    str = None,
                _Database:  str = None,
                _User:      str = None,
                _Password:  str = None,
                _Driver:    str = "ODBC Driver 17 for SQL Server",
                _pool_size: int = 5, 
                _timeout:   int = 30):
        """
        Inicializa a conexão com o banco de dados
        
        Args:
            _Server: Servidor do banco (se None, usa CoreConfig ou .env)
            _Database: Database (se None, usa CoreConfig ou .env)
            _User: Usuário (se None, usa CoreConfig ou .env)
            _Password: Senha (se None, usa CoreConfig ou .env)
            _pool_size: Tamanho do pool de conexões
            _timeout: Timeout para conexões
        
        Ordem de prioridade:
            1. Parâmetros passados diretamente
            2. CoreConfig (configurado pelo projeto host)
            3. Variáveis de ambiente (.env)
        """
        if CoreConfig.is_configured():
            config   = CoreConfig.get_db_config()
            server   = _Server   or config.get('server')
            database = _Database or config.get('database')
            user     = _User     or config.get('user')
            password = _Password or config.get('password')
            driver   = config.get('driver')
            self.db_type = config.get('DB_TYPE') or config.get('db_type') or os.getenv('DB_TYPE', 'sqlserver')
        else:
            server   = _Server   or os.getenv('DB_SERVER')
            database = _Database or os.getenv('DB_DATABASE')
            user     = _User     or os.getenv('DB_USER')
            password = _Password or os.getenv('DB_PASSWORD')
            driver   = _Driver   or os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
            self.db_type = os.getenv('DB_TYPE', 'sqlserver')

        # Normaliza para minúsculo (ex: MySQL -> mysql) para bater com as verificações
        self.db_type = self.db_type.lower()

        self.db_params = {
            'server': server,
            'database': database,
            'user': user,
            'password': password,
            'driver': driver
        }
        
        # Padrão da string de conexão para SQL Server (ODBC)
        self.connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"Encrypt=no;TrustServerCertificate=yes;"
        )
        self._pool    = Queue(maxsize=_pool_size)
        self._timeout = _timeout
        self._local   = threading.local() 
        
        print(self.db_params)
        print(self.db_type)
    
    @property
    def connection(self):
        if not hasattr(self._local, 'connection') or not self._local.connection:
            self._local.connection = self._get_connection()
        return self._local.connection
    
    @property
    def tts_level(self):
        return getattr(self._local, 'tts_level', 0)
    
    @tts_level.setter
    def tts_level(self, value):
        self._local.tts_level = value
        
    def _set_autocommit_on_conn(self, conn, value: bool):
        '''Seta o autocommit de forma segura dependendo do driver'''
        if self.db_type == 'mysql':
            conn.autocommit(value)
        else:
            conn.autocommit = value
            
    def _set_autocommit(self, value: bool):
        self._set_autocommit_on_conn(self.connection, value)
    
    def _get_connection(self):
        '''Pega conexão do pool ou cria nova imediatamente se vazio'''
        try:
            return self._pool.get_nowait()
        except Empty:
            if self.db_type == 'mysql':
                port = int(os.getenv('DB_PORT', '3306'))
                return pymysql.connect(
                    host=self.db_params['server'],
                    user=self.db_params['user'],
                    password=self.db_params['password'],
                    database=self.db_params['database'],
                    port=port,
                    autocommit=True
                )
            else:
                return pyodbc.connect(self.connection_string)
    
    def _return_connection(self, conn):
        '''Devolve conexão ao pool ou fecha se cheio'''
        if not conn:
            return
        try:
            self._set_autocommit_on_conn(conn, True)
            self._pool.put_nowait(conn)
        except:
            try:
                conn.close()
            except:
                pass

    def connect(self):
        '''Realiza a conexão atual da thread, ou cria uma nova'''
        return self.connection

    def disconnect(self):
        '''Realiza a desconexão atual da thread, ou fecha a conexão'''
        if hasattr(self._local, 'connection') and self._local.connection:
            if self.tts_level > 0:
                try:
                    self._local.connection.rollback()
                except:
                    pass
                self.tts_level = 0
            self._return_connection(self._local.connection)
            self._local.connection = None
    
    def close_all_connections(self):
        while not self._pool.empty():
            try:
                self._pool.get_nowait().close()
            except:
                break

    def can_connect(self) -> bool:
        '''Testa se a conexão pode ser estabelecida'''
        try:
            if self.db_type == 'mysql':
                print('mysql')
                port = int(os.getenv('DB_PORT', '3306'))
                conn = pymysql.connect(
                    host=self.db_params['server'],
                    user=self.db_params['user'],
                    password=self.db_params['password'],
                    database=self.db_params['database'],
                    port=port,
                    connect_timeout=self._timeout
                )
            else:
                conn = pyodbc.connect(self.connection_string, timeout=self._timeout)
            conn.close()
            return True
        except:
            return False


    def transaction(self) -> Transaction:
        return Transaction(self)