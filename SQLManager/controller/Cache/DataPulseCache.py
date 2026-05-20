from __future__ import annotations

import copy
import hashlib
import importlib
import json
import os
import pickle
import base64
import threading
import time
import zlib

from dataclasses import dataclass, field
from contextlib import nullcontext
from typing import Any, Callable, Dict, Iterable, Optional, Set


def _normalize_tag(tag: Any) -> str:
    return str(tag or "").strip().upper()


def _sanitize_key_part(value: Any) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ":") else "_" for ch in str(value or "").strip())


@dataclass
class _CacheEntry:
    payload: Any
    expires_at: float
    created_at: float
    tags: Set[str] = field(default_factory=set)
    compressed: bool = False
    size_bytes: int = 0


class CacheBackend:
    name = "base"

    def bind_connection(self, connection: Any):
        return None

    def get(self, key: str):
        raise NotImplementedError()

    def set(self, key: str, value: Any, ttl: int, tags: Iterable[str] = ()):  # pragma: no cover - interface
        raise NotImplementedError()

    def delete(self, key: str):
        raise NotImplementedError()

    def invalidate_tags(self, tags: Iterable[str]):
        raise NotImplementedError()

    def clear(self):
        raise NotImplementedError()

    def stats(self) -> Dict[str, Any]:
        return {"backend": self.name}

    def get_version(self, scope: str) -> Optional[int]:
        return None

    def bump_version(self, scope: str) -> Optional[int]:
        return None


class MemoryCacheBackend(CacheBackend):
    name = "memory"

    def __init__(self, max_entries: int = 2000, compression_min_bytes: int = 8192):
        self.max_entries = max(int(max_entries), 1)
        self.compression_min_bytes = max(int(compression_min_bytes), 0)
        self._lock = threading.RLock()
        self._entries: Dict[str, _CacheEntry] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._bytes = 0

    def configure(self, max_entries: Optional[int] = None, namespace: Optional[str] = None, compression_min_bytes: Optional[int] = None):
        with self._lock:
            if max_entries is not None:
                self.max_entries = max(int(max_entries), 1)
            if compression_min_bytes is not None:
                self.compression_min_bytes = max(int(compression_min_bytes), 0)
            self._prune_locked()

    def get(self, key: str):
        now = time.time()
        with self._lock:
            entry = self._entries.get(key)
            if not entry:
                return None
            if entry.expires_at < now:
                self._remove_locked(key, entry)
                return None
            return self._decode(entry)

    def set(self, key: str, value: Any, ttl: int, tags: Iterable[str] = ()):  # noqa: D401
        now = time.time()
        normalized_tags = {_normalize_tag(tag) for tag in tags if _normalize_tag(tag)}
        payload, compressed, size_bytes = self._encode(value)
        entry = _CacheEntry(
            payload=payload,
            expires_at=now + max(int(ttl), 1),
            created_at=now,
            tags=normalized_tags,
            compressed=compressed,
            size_bytes=size_bytes,
        )
        with self._lock:
            old_entry = self._entries.get(key)
            if old_entry:
                self._remove_locked(key, old_entry)
            self._entries[key] = entry
            self._bytes += size_bytes
            for tag in normalized_tags:
                self._tag_index.setdefault(tag, set()).add(key)
            self._prune_locked()

    def delete(self, key: str):
        with self._lock:
            entry = self._entries.get(key)
            if entry:
                self._remove_locked(key, entry)

    def invalidate_tags(self, tags: Iterable[str]):
        normalized_tags = {_normalize_tag(tag) for tag in tags if _normalize_tag(tag)}
        with self._lock:
            keys_to_remove = set()
            for tag in normalized_tags:
                keys_to_remove.update(self._tag_index.get(tag, set()))
            for key in keys_to_remove:
                entry = self._entries.get(key)
                if entry:
                    self._remove_locked(key, entry)

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._tag_index.clear()
            self._bytes = 0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "backend": self.name,
                "entries": len(self._entries),
                "bytes": self._bytes,
                "tags": len(self._tag_index),
            }

    def _encode(self, value: Any):
        payload = copy.deepcopy(value)
        raw = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
        if self.compression_min_bytes and len(raw) >= self.compression_min_bytes:
            compressed_payload = zlib.compress(raw)
            return compressed_payload, True, len(compressed_payload)
        return payload, False, len(raw)

    def _decode(self, entry: _CacheEntry):
        if entry.compressed:
            return pickle.loads(zlib.decompress(entry.payload))
        return copy.deepcopy(entry.payload)

    def _remove_locked(self, key: str, entry: _CacheEntry):
        self._entries.pop(key, None)
        self._bytes = max(self._bytes - entry.size_bytes, 0)
        for tag in entry.tags:
            tag_keys = self._tag_index.get(tag)
            if not tag_keys:
                continue
            tag_keys.discard(key)
            if not tag_keys:
                self._tag_index.pop(tag, None)

    def _prune_locked(self):
        if len(self._entries) <= self.max_entries:
            return
        ordered_entries = sorted(self._entries.items(), key=lambda item: item[1].created_at)
        remove_count = len(self._entries) - self.max_entries
        for key, entry in ordered_entries[:remove_count]:
            self._remove_locked(key, entry)


class RedisCacheBackend(CacheBackend):
    name = "redis"

    def __init__(self, url: str = "redis://localhost:6379/0", namespace: str = "sqlmanager", compression_min_bytes: int = 8192):
        try:
            redis_module = importlib.import_module("redis")
        except ImportError as exc:  # pragma: no cover - backend opcional
            raise RuntimeError("Redis backend requer o pacote 'redis'. Instale SQLManager[redis].") from exc

        self._client = redis_module.Redis.from_url(url)
        self.url = url
        self.namespace = _sanitize_key_part(namespace or "sqlmanager")
        self.compression_min_bytes = max(int(compression_min_bytes), 0)

    def configure(self, max_entries: Optional[int] = None, namespace: Optional[str] = None, compression_min_bytes: Optional[int] = None):
        if namespace is not None:
            self.namespace = _sanitize_key_part(namespace or self.namespace)
        if compression_min_bytes is not None:
            self.compression_min_bytes = max(int(compression_min_bytes), 0)

    def get(self, key: str):
        raw = self._client.get(self._key(key))
        if raw is None:
            return None
        compressed = raw[:1] == b"1"
        payload = raw[1:]
        if compressed:
            payload = zlib.decompress(payload)
        return pickle.loads(payload)

    def set(self, key: str, value: Any, ttl: int, tags: Iterable[str] = ()):  # noqa: D401
        payload = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = False
        if self.compression_min_bytes and len(payload) >= self.compression_min_bytes:
            payload = zlib.compress(payload)
            compressed = True
        full_key = self._key(key)
        self._client.setex(full_key, max(int(ttl), 1), (b"1" if compressed else b"0") + payload)
        for tag in {_normalize_tag(tag) for tag in tags if _normalize_tag(tag)}:
            self._client.sadd(self._tag_key(tag), full_key)

    def delete(self, key: str):
        self._client.delete(self._key(key))

    def invalidate_tags(self, tags: Iterable[str]):
        for tag in {_normalize_tag(tag) for tag in tags if _normalize_tag(tag)}:
            tag_key = self._tag_key(tag)
            members = self._client.smembers(tag_key)
            if members:
                self._client.delete(*members)
            self._client.delete(tag_key)

    def clear(self):
        cache_keys = list(self._client.scan_iter(f"{self.namespace}:cache:*"))
        tag_keys = list(self._client.scan_iter(f"{self.namespace}:tag:*"))
        if cache_keys:
            self._client.delete(*cache_keys)
        if tag_keys:
            self._client.delete(*tag_keys)

    def stats(self) -> Dict[str, Any]:
        return {
            "backend": self.name,
            "namespace": self.namespace,
            "dbsize": self._client.dbsize(),
        }

    def get_version(self, scope: str) -> Optional[int]:
        raw = self._client.get(self._version_key(scope))
        if raw is None:
            return 0
        return int(raw)

    def bump_version(self, scope: str) -> Optional[int]:
        return int(self._client.incr(self._version_key(scope)))

    def _key(self, key: str) -> str:
        return f"{self.namespace}:cache:{key}"

    def _tag_key(self, tag: str) -> str:
        return f"{self.namespace}:tag:{_sanitize_key_part(tag)}"

    def _version_key(self, scope: str) -> str:
        return f"{self.namespace}:version:{_sanitize_key_part(scope)}"


class DatabaseCacheBackend(CacheBackend):
    name = "database"

    def __init__(self, connection: Any = None, namespace: str = "sqlmanager", compression_min_bytes: int = 8192):
        self.db = connection
        self.namespace = _sanitize_key_part(namespace or "sqlmanager") or "sqlmanager"
        self.compression_min_bytes = max(int(compression_min_bytes), 0)
        self.cache_table = f"{self.namespace.upper()}_CACHE"
        self.version_table = f"{self.namespace.upper()}_CACHE_VERSIONS"
        self._schema_ready = False
        self._lock = threading.RLock()
        self._last_cleanup_at = 0.0

    def bind_connection(self, connection: Any):
        self.db = connection
        self._schema_ready = False

    def configure(self, max_entries: Optional[int] = None, namespace: Optional[str] = None, compression_min_bytes: Optional[int] = None):
        if namespace is not None:
            self.namespace = _sanitize_key_part(namespace or self.namespace) or self.namespace
            self.cache_table = f"{self.namespace.upper()}_CACHE"
            self.version_table = f"{self.namespace.upper()}_CACHE_VERSIONS"
            self._schema_ready = False
        if compression_min_bytes is not None:
            self.compression_min_bytes = max(int(compression_min_bytes), 0)

    def get(self, key: str):
        if not self._ensure_ready():
            return None
        self._cleanup_if_needed()
        rows = self.db.doQuery(
            f"SELECT PAYLOAD, EXPIRES_AT, COMPRESSED FROM {self.cache_table} WHERE CACHE_KEY = ?",
            (key,),
        )
        if not rows:
            return None
        payload, expires_at, compressed = rows[0]
        if int(expires_at) < int(time.time()):
            self.delete(key)
            return None
        return self._decode_payload(payload, bool(compressed))

    def set(self, key: str, value: Any, ttl: int, tags: Iterable[str] = ()):  # noqa: D401
        if not self._ensure_ready():
            return
        now = int(time.time())
        expires_at = now + max(int(ttl), 1)
        payload, compressed = self._encode_payload(value)
        with self._transaction_scope() as conn:
            conn.executeCommand(f"DELETE FROM {self.cache_table} WHERE CACHE_KEY = ?", (key,))
            conn.executeCommand(
                f"INSERT INTO {self.cache_table} (CACHE_KEY, PAYLOAD, EXPIRES_AT, CREATED_AT, COMPRESSED) VALUES (?, ?, ?, ?, ?)",
                (key, payload, expires_at, now, int(compressed)),
            )

    def delete(self, key: str):
        if not self._ensure_ready():
            return
        self.db.executeCommand(f"DELETE FROM {self.cache_table} WHERE CACHE_KEY = ?", (key,))

    def invalidate_tags(self, tags: Iterable[str]):
        return None

    def clear(self):
        if not self._ensure_ready():
            return
        with self._transaction_scope() as conn:
            conn.executeCommand(f"DELETE FROM {self.cache_table}")
            conn.executeCommand(f"DELETE FROM {self.version_table}")

    def stats(self) -> Dict[str, Any]:
        if not self._ensure_ready():
            return {
                "backend": self.name,
                "namespace": self.namespace,
                "bound": False,
            }

        cache_rows = self.db.doQuery(f"SELECT COUNT(*) FROM {self.cache_table}")
        version_rows = self.db.doQuery(f"SELECT COUNT(*) FROM {self.version_table}")
        return {
            "backend": self.name,
            "namespace": self.namespace,
            "bound": True,
            "entries": int(cache_rows[0][0]) if cache_rows else 0,
            "versions": int(version_rows[0][0]) if version_rows else 0,
        }

    def get_version(self, scope: str) -> Optional[int]:
        if not self._ensure_ready():
            return 0
        rows = self.db.doQuery(
            f"SELECT VERSION_NO FROM {self.version_table} WHERE SCOPE_NAME = ?",
            (scope,),
        )
        if not rows:
            return 0
        return int(rows[0][0])

    def bump_version(self, scope: str) -> Optional[int]:
        if not self._ensure_ready():
            return 0
        current = self.get_version(scope) or 0
        next_version = current + 1
        now = int(time.time())
        with self._transaction_scope() as conn:
            conn.executeCommand(f"DELETE FROM {self.version_table} WHERE SCOPE_NAME = ?", (scope,))
            conn.executeCommand(
                f"INSERT INTO {self.version_table} (SCOPE_NAME, VERSION_NO, UPDATED_AT) VALUES (?, ?, ?)",
                (scope, next_version, now),
            )
        return next_version

    def _ensure_ready(self) -> bool:
        if self.db is None:
            return False
        if self._schema_ready:
            return True
        with self._lock:
            if self._schema_ready:
                return True
            db_type = str(getattr(self.db, 'db_type', 'sqlserver') or 'sqlserver').lower()
            with self._transaction_scope() as conn:
                for statement in self._schema_statements(db_type):
                    conn.executeCommand(statement)
            self._schema_ready = True
            return True

    def _schema_statements(self, db_type: str):
        if db_type == 'mysql':
            return [
                f"CREATE TABLE IF NOT EXISTS {self.cache_table} (CACHE_KEY VARCHAR(255) PRIMARY KEY, PAYLOAD LONGTEXT NOT NULL, EXPIRES_AT BIGINT NOT NULL, CREATED_AT BIGINT NOT NULL, COMPRESSED TINYINT(1) NOT NULL DEFAULT 0)",
                f"CREATE TABLE IF NOT EXISTS {self.version_table} (SCOPE_NAME VARCHAR(255) PRIMARY KEY, VERSION_NO BIGINT NOT NULL, UPDATED_AT BIGINT NOT NULL)",
            ]
        return [
            f"IF OBJECT_ID(N'{self.cache_table}', N'U') IS NULL BEGIN CREATE TABLE {self.cache_table} (CACHE_KEY NVARCHAR(255) NOT NULL PRIMARY KEY, PAYLOAD NVARCHAR(MAX) NOT NULL, EXPIRES_AT BIGINT NOT NULL, CREATED_AT BIGINT NOT NULL, COMPRESSED BIT NOT NULL DEFAULT 0) END",
            f"IF OBJECT_ID(N'{self.version_table}', N'U') IS NULL BEGIN CREATE TABLE {self.version_table} (SCOPE_NAME NVARCHAR(255) NOT NULL PRIMARY KEY, VERSION_NO BIGINT NOT NULL, UPDATED_AT BIGINT NOT NULL) END",
        ]

    def _transaction_scope(self):
        if hasattr(self.db, 'transaction'):
            return self.db.transaction()
        return nullcontext(self.db)

    def _cleanup_if_needed(self):
        now = time.time()
        if now - self._last_cleanup_at < 30:
            return
        self._last_cleanup_at = now
        self.db.executeCommand(f"DELETE FROM {self.cache_table} WHERE EXPIRES_AT < ?", (int(now),))

    def _encode_payload(self, value: Any):
        payload = pickle.dumps(copy.deepcopy(value), protocol=pickle.HIGHEST_PROTOCOL)
        compressed = False
        if self.compression_min_bytes and len(payload) >= self.compression_min_bytes:
            payload = zlib.compress(payload)
            compressed = True
        return base64.b64encode(payload).decode('ascii'), compressed

    def _decode_payload(self, payload: Any, compressed: bool):
        raw = base64.b64decode(str(payload).encode('ascii'))
        if compressed:
            raw = zlib.decompress(raw)
        return pickle.loads(raw)


class DataPulseCache:
    """
    Cache interno com backend plugavel para leituras repetidas.

    Mantem o contrato legado (`get`, `set`, `invalidate_table`) e adiciona tags,
    backends distribuidos e single-flight local para evitar avalanche de cache.
    """

    def __init__(
        self,
        enabled: bool = True,
        default_ttl: int = 45,
        max_entries: int = 2000,
        backend: str = "memory",
        namespace: str = "sqlmanager",
        compression_min_bytes: int = 8192,
        redis_url: Optional[str] = None,
    ):
        env_enabled = os.getenv("SQLMANAGER_CACHE_ENABLED")
        env_ttl = os.getenv("SQLMANAGER_CACHE_TTL")
        env_max_entries = os.getenv("SQLMANAGER_CACHE_MAX_ENTRIES")
        env_backend = os.getenv("SQLMANAGER_CACHE_BACKEND")
        env_namespace = os.getenv("SQLMANAGER_CACHE_NAMESPACE")
        env_compression_min_bytes = os.getenv("SQLMANAGER_CACHE_COMPRESSION_MIN_BYTES")
        env_redis_url = os.getenv("SQLMANAGER_CACHE_REDIS_URL")

        self.enabled = self._parse_bool(env_enabled, enabled)
        self.default_ttl = self._parse_int(env_ttl, default_ttl)
        self.max_entries = max(self._parse_int(env_max_entries, max_entries), 1)
        self.namespace = _sanitize_key_part(env_namespace or namespace or "sqlmanager")
        self.compression_min_bytes = self._parse_int(env_compression_min_bytes, compression_min_bytes)
        self._lock = threading.RLock()
        self._versions: Dict[str, int] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "single_flight_waits": 0,
        }
        self._flight_locks: Dict[str, threading.Lock] = {}
        self._backend_name = (env_backend or backend or "memory").strip().lower()
        self._redis_url = env_redis_url or redis_url
        self._bound_connection = None
        self.backend = self._build_backend(self._backend_name, self.max_entries, self.namespace, self.compression_min_bytes, self._redis_url)

    @staticmethod
    def _parse_bool(value: Optional[str], default: bool) -> bool:
        if value is None:
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

    @staticmethod
    def _parse_int(value: Optional[str], default: int) -> int:
        if value is None:
            return default
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return default

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def bind_connection(self, connection: Any):
        self._bound_connection = connection
        if hasattr(self.backend, 'bind_connection'):
            self.backend.bind_connection(connection)
        elif self._backend_name == 'database':
            self.backend = self._build_backend(self._backend_name, self.max_entries, self.namespace, self.compression_min_bytes, self._redis_url)

    def _build_backend(self, backend_name: str, max_entries: int, namespace: str, compression_min_bytes: int, redis_url: Optional[str]):
        backend_key = (backend_name or "memory").strip().lower()
        if backend_key == "redis":
            return RedisCacheBackend(url=redis_url or "redis://localhost:6379/0", namespace=namespace, compression_min_bytes=compression_min_bytes)
        if backend_key == 'database':
            return DatabaseCacheBackend(connection=self._bound_connection, namespace=namespace, compression_min_bytes=compression_min_bytes)
        return MemoryCacheBackend(max_entries=max_entries, compression_min_bytes=compression_min_bytes)

    def configure(
        self,
        enabled: Optional[bool] = None,
        default_ttl: Optional[int] = None,
        max_entries: Optional[int] = None,
        backend: Optional[str] = None,
        namespace: Optional[str] = None,
        compression_min_bytes: Optional[int] = None,
        redis_url: Optional[str] = None,
    ):
        with self._lock:
            if enabled is not None:
                self.enabled = bool(enabled)
            if default_ttl is not None:
                self.default_ttl = max(int(default_ttl), 1)
            if max_entries is not None:
                self.max_entries = max(int(max_entries), 1)
            if namespace is not None:
                self.namespace = _sanitize_key_part(namespace or self.namespace)
            if compression_min_bytes is not None:
                self.compression_min_bytes = max(int(compression_min_bytes), 0)
            if redis_url is not None:
                self._redis_url = redis_url

            requested_backend = (backend or self._backend_name).strip().lower()
            backend_changed = requested_backend != self._backend_name

            if backend_changed:
                self._backend_name = requested_backend
                self.backend = self._build_backend(requested_backend, self.max_entries, self.namespace, self.compression_min_bytes, self._redis_url)
            elif hasattr(self.backend, "configure"):
                self.backend.configure(max_entries=self.max_entries, namespace=self.namespace, compression_min_bytes=self.compression_min_bytes)

    def table_key(self, table_name: str) -> str:
        return _normalize_tag(table_name)

    def dataset_key(self, dataset_name: str) -> str:
        return _normalize_tag(f"DATASET:{dataset_name}")

    def version_for(self, scope: str) -> int:
        scope_key = self.table_key(scope)
        backend_version = self.backend.get_version(scope_key) if hasattr(self.backend, 'get_version') else None
        if backend_version is not None:
            return int(backend_version)
        return self._versions.get(scope_key, 0)

    def bump_version(self, scope: str):
        scope_key = self.table_key(scope)
        if not scope_key:
            return 0
        backend_version = self.backend.bump_version(scope_key) if hasattr(self.backend, 'bump_version') else None
        if backend_version is not None:
            return int(backend_version)
        with self._lock:
            self._versions[scope_key] = self._versions.get(scope_key, 0) + 1
            return self._versions[scope_key]

    def make_query_key(
        self,
        tables: Iterable[str],
        operation: str,
        payload: Any,
        dataset: Optional[str] = None,
        security_scope: Optional[str] = None,
    ) -> str:
        table_list = [self.table_key(table) for table in tables if self.table_key(table)]
        scopes = list(table_list)
        if dataset:
            scopes.append(self.dataset_key(dataset))
        version_map = {scope: self.version_for(scope) for scope in scopes}
        raw_key = {
            "namespace": self.namespace,
            "tables": table_list,
            "dataset": dataset,
            "versions": version_map,
            "operation": operation,
            "security_scope": security_scope,
            "payload": payload,
        }
        raw_text = json.dumps(raw_key, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    def _backend_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def get(self, table_name: str, key: str):
        if not self.enabled:
            return None

        cached_value = self.backend.get(self._backend_key(key))
        with self._lock:
            if cached_value is None:
                self._stats["misses"] += 1
                return None
            self._stats["hits"] += 1
        return cached_value

    def set(self, table_name: str, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[Iterable[str]] = None):
        if not self.enabled:
            return

        ttl_value = max(int(ttl or self.default_ttl), 1)
        normalized_tags = {self.table_key(table_name)} if self.table_key(table_name) else set()
        normalized_tags.update({_normalize_tag(tag) for tag in tags or [] if _normalize_tag(tag)})
        self.backend.set(self._backend_key(key), value, ttl_value, normalized_tags)
        with self._lock:
            self._stats["sets"] += 1

    def remember(self, table_name: str, key: str, resolver: Callable[[], Any], ttl: Optional[int] = None, tags: Optional[Iterable[str]] = None):
        cached_value = self.get(table_name, key)
        if cached_value is not None:
            return cached_value

        backend_key = self._backend_key(key)
        with self._lock:
            lock = self._flight_locks.setdefault(backend_key, threading.Lock())

        if not lock.acquire(blocking=False):
            with self._lock:
                self._stats["single_flight_waits"] += 1
            with lock:
                return self.get(table_name, key)

        try:
            cached_value = self.get(table_name, key)
            if cached_value is not None:
                return cached_value
            resolved = resolver()
            self.set(table_name, key, resolved, ttl=ttl, tags=tags)
            return resolved
        finally:
            lock.release()
            with self._lock:
                self._flight_locks.pop(backend_key, None)

    def invalidate_table(self, table_name: str):
        table_key = self.table_key(table_name)
        if not table_key:
            return
        self.bump_version(table_key)
        self.backend.invalidate_tags([table_key])
        with self._lock:
            self._stats["invalidations"] += 1

    def invalidate_dataset(self, dataset_name: str):
        dataset_key = self.dataset_key(dataset_name)
        self.bump_version(dataset_key)
        self.backend.invalidate_tags([dataset_key])
        with self._lock:
            self._stats["invalidations"] += 1

    def invalidate_tags(self, tags: Iterable[str]):
        normalized_tags = {_normalize_tag(tag) for tag in tags if _normalize_tag(tag)}
        if not normalized_tags:
            return
        for tag in normalized_tags:
            self.bump_version(tag)
        self.backend.invalidate_tags(normalized_tags)
        with self._lock:
            self._stats["invalidations"] += len(normalized_tags)

    def invalidate_tables(self, table_names: Iterable[str]):
        self.invalidate_tags(table_names)

    def invalidate_controller(self, controller: Any):
        table_name = getattr(controller, "source_name", None) or getattr(controller, "table_name", None)
        self.invalidate_table(table_name)

        for cls in getattr(controller.__class__, "mro", lambda: [])():
            count_cache = getattr(cls, "_count_cache", None)
            if isinstance(count_cache, dict):
                prefix = f"{str(table_name).upper()}_"
                for key in list(count_cache.keys()):
                    if str(key).upper().startswith(prefix):
                        count_cache.pop(key, None)

    def clear(self):
        self.backend.clear()
        with self._lock:
            self._versions.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = dict(self._stats)
        stats.update(self.backend.stats())
        stats["namespace"] = self.namespace
        stats["bound_connection"] = self._bound_connection is not None
        return stats


data_pulse_cache = DataPulseCache()
