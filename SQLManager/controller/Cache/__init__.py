from .DataPulseCache import (
	CacheBackend,
	DataPulseCache as DataPulseCacheClass,
	DatabaseCacheBackend,
	MemoryCacheBackend,
	RedisCacheBackend,
	data_pulse_cache,
)

DataPulseCache = data_pulse_cache
DataPulseCacheSingleton = data_pulse_cache

__all__ = [
	'CacheBackend',
	'DatabaseCacheBackend',
	'MemoryCacheBackend',
	'RedisCacheBackend',
	'DataPulseCache',
	'DataPulseCacheClass',
	'DataPulseCacheSingleton',
	'data_pulse_cache',
]