from .connection import database_connection
from .controller import EDTController, BaseEnumController, DatabaseAnalysisController, TableController, SystemController, ViewController, NumberSequenceController
from .CoreConfig import CoreConfig
from .analytics import (
    AnalyticsRegistry,
    AnalyticsRouter,
    DataSource,
    Dataset,
    Hierarchy,
    MaterializationJob,
    MaterializationScheduler,
    Measure,
    SecurityPolicy,
    analytics_registry,
)

''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
from .controller.API.RouterController        import AutoRouter
from .controller.API.WebSocketManager        import WebSocketManager
from .controller.Database.databaseWatchController import DatabaseWatcher
from .controller.Cache.DataPulseCache          import data_pulse_cache, DataPulseCache, DatabaseCacheBackend, MemoryCacheBackend, RedisCacheBackend

__version__ = "5.0.0"

__all__ = [
    "__version__",
    "database_connection",
    "EDTController",
    "BaseEnumController",
    "DatabaseAnalysisController",
    "TableController",
    "ViewController",
    "SystemController",
    "NumberSequenceController",
    "CoreConfig",    
    "AutoRouter",
    "AnalyticsRegistry",
    "AnalyticsRouter",
    "DataSource",
    "Dataset",
    "Hierarchy",
    "MaterializationJob",
    "MaterializationScheduler",
    "Measure",
    "SecurityPolicy",
    "analytics_registry",
    "WebSocketManager",
    "DatabaseWatcher",
    "DataPulseCache",
    "DatabaseCacheBackend",
    "MemoryCacheBackend",
    "RedisCacheBackend",
    "data_pulse_cache"
]
''' [END CODE] Project: SQLManager Version 4.0 / issue: #3 / made by: Nicolas Santos / created: 27/02/2026 '''
