from .connection import database_connection
from .controller import EDTController, BaseEnumController, TableController, SystemController, ViewController
from .CoreConfig import CoreConfig

''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
from .controller.RouterController import AutoRouter

# NOTA: AutoRouter deve ser instanciado manualmente na aplicação host
# Exemplo:
#   db = database_connection()
#   router = AutoRouter(db)
#   response = router.handle_request('GET', 'Products', path_parts=['1'])
#
# Veja RouterController_Example.py para exemplos completos de uso
''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''

__all__ = [
    "database_connection",
    "EDTController",
    "BaseEnumController",
    "TableController",
    "ViewController",
    "SystemController",
    "CoreConfig",
    "AutoRouter"
]