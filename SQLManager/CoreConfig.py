r"""
CoreConfig - Sistema de Configuração para o SQLManager

Este módulo permite que projetos externos configurem o SQLManager
sem modificar seus arquivos internos.

Uso no projeto host:
    from SQLManager import CoreConfig
    
    CoreConfig.configure(
        db_server='localhost',
        db_database='MyDB',
        db_user='admin',
        db_password='pass123'
    )
    
    CoreConfig.register_regex('CustomEmail', r'^[\w\.-]+@mycompany\.com$')
"""

from typing import Optional, Dict, Any
import os

class CoreConfig:
    """
    Classe estática para configuração global do Core
    """
    
    _db_server: Optional[str] = None
    _db_database: Optional[str] = None
    _db_user: Optional[str] = None
    _db_password: Optional[str] = None
    _db_driver: str = "ODBC Driver 18 for SQL Server"
    _db_type: str = "sqlserver"

    _require_recid: bool = True
    _select_use_transaction: bool = True
    _data_pulse_cache_enabled: bool = True
    _data_pulse_cache_ttl: int = 45
    _data_pulse_cache_max_entries: int = 2000
    
    _custom_regex: Dict[str, str] = {}

    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
    _router_config: Dict[str, Any] = {}
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
    
    _is_configured: bool = False

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    
    @classmethod
    def configure(cls, 
                  db_server: Optional[str] = None,
                  db_database: Optional[str] = None,
                  db_user: Optional[str] = None,
                  db_password: Optional[str] = None,
                  db_driver: Optional[str] = None,
                  db_type: Optional[str] = None,
                  require_recid: Optional[bool] = None,
                  select_use_transaction: Optional[bool] = None,
                  data_pulse_cache_enabled: Optional[bool] = None,
                  data_pulse_cache_ttl: Optional[int] = None,
                  data_pulse_cache_max_entries: Optional[int] = None,
                  load_from_env: bool = True):
        """
        Configura o SQLManager com as credenciais do projeto host
        
        Args:
            db_server: Servidor do banco de dados
            db_database: Nome do banco de dados
            db_user: Usuário do banco
            db_password: Senha do banco
            db_driver: Driver ODBC (opcional)
            db_type: Tipo do banco de dados ('sqlserver', 'mysql', etc.)
            require_recid: Se True, model update exige RECID BIGINT nas tabelas
            select_use_transaction: Se True, SELECT abre contexto transacional
            data_pulse_cache_enabled: Liga ou desliga o cache interno de SELECT
            data_pulse_cache_ttl: TTL em segundos do cache interno de SELECT
            data_pulse_cache_max_entries: Limite de entradas do cache interno
            load_from_env: Se True, tenta carregar do .env do projeto host primeiro
        
        Exemplo:
            CoreConfig.configure(
                db_server='localhost',
                db_database='MyDB',
                db_user='admin',
                db_password='pass123'
            )
        """
        if load_from_env:
            cls._db_server = db_server or os.getenv('DB_SERVER')
            cls._db_database = db_database or os.getenv('DB_DATABASE')
            cls._db_user = db_user or os.getenv('DB_USER')
            cls._db_password = db_password or os.getenv('DB_PASSWORD')
            
            # Carrega do env e sobrescreve apenas se o usuário não passou nos argumentos
            env_db_type = os.getenv('DB_TYPE')
            if env_db_type and not db_type:
                db_type = env_db_type

            if require_recid is None:
                require_recid = cls._env_bool('SQLMANAGER_REQUIRE_RECID', cls._require_recid)
            if select_use_transaction is None:
                select_use_transaction = cls._env_bool('SQLMANAGER_SELECT_USE_TRANSACTION', cls._select_use_transaction)
            if data_pulse_cache_enabled is None:
                data_pulse_cache_enabled = cls._env_bool('SQLMANAGER_CACHE_ENABLED', cls._data_pulse_cache_enabled)
            if data_pulse_cache_ttl is None:
                data_pulse_cache_ttl = cls._env_int('SQLMANAGER_CACHE_TTL', cls._data_pulse_cache_ttl)
            if data_pulse_cache_max_entries is None:
                data_pulse_cache_max_entries = cls._env_int('SQLMANAGER_CACHE_MAX_ENTRIES', cls._data_pulse_cache_max_entries)
        else:
            cls._db_server = db_server
            cls._db_database = db_database
            cls._db_user = db_user
            cls._db_password = db_password
        
        if db_driver:
            cls._db_driver = db_driver
        
        cls._db_type = (db_type or "sqlserver").lower()
        cls._require_recid = bool(cls._require_recid if require_recid is None else require_recid)
        cls._select_use_transaction = bool(cls._select_use_transaction if select_use_transaction is None else select_use_transaction)
        cls._data_pulse_cache_enabled = bool(cls._data_pulse_cache_enabled if data_pulse_cache_enabled is None else data_pulse_cache_enabled)
        cls._data_pulse_cache_ttl = max(int(cls._data_pulse_cache_ttl if data_pulse_cache_ttl is None else data_pulse_cache_ttl), 1)
        cls._data_pulse_cache_max_entries = max(int(cls._data_pulse_cache_max_entries if data_pulse_cache_max_entries is None else data_pulse_cache_max_entries), 1)
        
        cls._is_configured = True
    
    @classmethod
    def is_configured(cls) -> bool:
        """Verifica se o Core foi configurado"""
        return cls._is_configured
    
    @classmethod
    def get_db_config(cls) -> Dict[str, Optional[str]]:
        """
        Retorna as configurações de banco de dados
        
        Returns:
            Dict com server, database, user, password, driver, type
        """
        return {
            'server': cls._db_server,
            'database': cls._db_database,
            'user': cls._db_user,
            'password': cls._db_password,
            'driver': cls._db_driver,
            'type': cls._db_type
        }

    @classmethod
    def require_recid(cls) -> bool:
        return cls._require_recid

    @classmethod
    def select_use_transaction(cls) -> bool:
        return cls._select_use_transaction

    @classmethod
    def get_runtime_config(cls) -> Dict[str, Any]:
        return {
            'require_recid': cls._require_recid,
            'select_use_transaction': cls._select_use_transaction,
            'data_pulse_cache_enabled': cls._data_pulse_cache_enabled,
            'data_pulse_cache_ttl': cls._data_pulse_cache_ttl,
            'data_pulse_cache_max_entries': cls._data_pulse_cache_max_entries,
        }

    @classmethod
    def get_cache_config(cls) -> Dict[str, Any]:
        return {
            'enabled': cls._data_pulse_cache_enabled,
            'ttl': cls._data_pulse_cache_ttl,
            'max_entries': cls._data_pulse_cache_max_entries,
        }
    
    @classmethod
    def register_regex(cls, regex_id: str, pattern: str):
        r"""
        Registra um novo padrão regex customizado
        
        Args:
            regex_id: Identificador único do regex
            pattern: Padrão regex (string)
        
        Exemplo:
            CoreConfig.register_regex('CompanyEmail', r'^[\w\.-]+@mycompany\.com$')
            
            my_edt = EDTController('CompanyEmail', DataType.String)
        """
        cls._custom_regex[regex_id] = pattern
    
    @classmethod
    def register_multiple_regex(cls, regex_dict: Dict[str, str]):
        r"""
        Registra múltiplos padrões regex de uma vez
        
        Args:
            regex_dict: Dicionário com {regex_id: pattern}
        
        Exemplo:
            CoreConfig.register_multiple_regex({
                'CompanyEmail': r'^[\w\.-]+@mycompany\.com$',
                'ProductCode': r'^PRD-\d{6}$',
                'OrderNumber': r'^ORD-\d{8}$'
            })
        """
        cls._custom_regex.update(regex_dict)
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
    @classmethod
    def configure_router(cls, config: Dict[str, Any]):
        """
        Configura o módulo AutoRouter (Rotas Dinâmicas)
        
        Args:
            config: Dicionário de configuração do AutoRouter
            
        Exemplo:
            CoreConfig.configure_router({
                'enable_dynamic_routes': True,
                'url_suffix': 'api/v1',
                'exclude_tables': ['SysLog'],
                'app': my_flask_app
            })
        """
        cls._router_config = config
    
    @classmethod
    def get_router_config(cls) -> Dict[str, Any]:
        """Retorna a configuração atual do AutoRouter"""
        return cls._router_config
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''

    @classmethod
    def get_regex(cls, regex_id: str) -> Optional[str]:
        """
        Obtém um padrão regex customizado
        
        Args:
            regex_id: Identificador do regex
        
        Returns:
            String do padrão regex ou None se não existir
        """
        return cls._custom_regex.get(regex_id)
    
    @classmethod
    def has_regex(cls, regex_id: str) -> bool:
        """Verifica se um regex customizado existe"""
        return regex_id in cls._custom_regex
    
    @classmethod
    def get_all_custom_regex(cls) -> Dict[str, str]:
        """Retorna todos os regex customizados registrados"""
        return cls._custom_regex.copy()
    
    @classmethod
    def reset(cls):
        """Reseta todas as configurações (testes)"""
        cls._db_server = None
        cls._db_database = None
        cls._db_user = None
        cls._db_password = None
        cls._db_driver = "ODBC Driver 18 for SQL Server"
        cls._db_type = "sqlserver"
        cls._require_recid = True
        cls._select_use_transaction = True
        cls._data_pulse_cache_enabled = True
        cls._data_pulse_cache_ttl = 45
        cls._data_pulse_cache_max_entries = 2000
        cls._custom_regex = {}
        cls._router_config = {}
        cls._is_configured = False
    
    ''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
    @classmethod
    def configure_from_dict(cls, config: Dict[str, Any]):
        r"""
        Configura a partir de um dicionário
        
        Args:
            config: Dicionário com as configurações
        
        Exemplo:
            config = {
                'db_server': 'localhost',
                'db_database': 'MyDB',
                'db_user': 'admin',
                'db_password': 'pass123',
                'db_type': 'mysql',
                'router_config': {
                    'enable_dynamic_routes': True,
                    'url_suffix': 'api/v1',
                    'exclude_tables': ['SysLog'],
                    'app': my_flask_app
                },
                'custom_regex': {
                    'CompanyEmail': r'^[\w\.-]+@mycompany\.com$'
                }
            }
            CoreConfig.configure_from_dict(config)
        """
        cls.configure(
            db_server=config.get('db_server'),
            db_database=config.get('db_database'),
            db_user=config.get('db_user'),
            db_password=config.get('db_password'),
            db_driver=config.get('db_driver'),
            db_type=config.get('db_type'),
            require_recid=config.get('require_recid'),
            select_use_transaction=config.get('select_use_transaction'),
            data_pulse_cache_enabled=config.get('data_pulse_cache_enabled'),
            data_pulse_cache_ttl=config.get('data_pulse_cache_ttl'),
            data_pulse_cache_max_entries=config.get('data_pulse_cache_max_entries'),
            load_from_env=config.get('load_from_env', True)
        )
        
        if 'custom_regex' in config:
            cls.register_multiple_regex(config['custom_regex'])
            
        if 'router_config' in config:
            cls.configure_router(config['router_config'])        
    ''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
