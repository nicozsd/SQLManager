''' [BEGIN CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 08/05/2026 '''

from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass
class _DataPulseEntry:
    value: Any
    expires_at: float
    created_at: float


class DataPulseCache:
    """
    Cache interno por tabela para reduzir leituras repetidas no banco.
    """

    def __init__(self, enabled: bool = True, default_ttl: int = 45, max_entries: int = 2000):
        env_enabled = os.getenv("SQLMANAGER_CACHE_ENABLED")
        env_ttl = os.getenv("SQLMANAGER_CACHE_TTL")
        env_max_entries = os.getenv("SQLMANAGER_CACHE_MAX_ENTRIES")

        self.enabled = self._parse_bool(env_enabled, enabled)
        self.default_ttl = self._parse_int(env_ttl, default_ttl)
        self.max_entries = self._parse_int(env_max_entries, max_entries)
        self._lock = threading.RLock()
        self._tables: Dict[str, Dict[str, _DataPulseEntry]] = {}
        self._versions: Dict[str, int] = {}
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "invalidations": 0}

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
            return max(int(value), 1)
        except (TypeError, ValueError):
            return default

    def configure(self, enabled: Optional[bool] = None, default_ttl: Optional[int] = None, max_entries: Optional[int] = None):
        with self._lock:
            if enabled is not None:
                self.enabled = bool(enabled)
            if default_ttl is not None:
                self.default_ttl = max(int(default_ttl), 1)
            if max_entries is not None:
                self.max_entries = max(int(max_entries), 1)

    def table_key(self, table_name: str) -> str:
        return str(table_name or "").upper()

    def version_for(self, table_name: str) -> int:
        return self._versions.get(self.table_key(table_name), 0)

    def make_query_key(self, tables: Iterable[str], operation: str, payload: Any) -> str:
        table_list = [self.table_key(table) for table in tables if table]
        version_map = {table: self.version_for(table) for table in table_list}
        raw_key = {
            "tables": table_list,
            "versions": version_map,
            "operation": operation,
            "payload": payload,
        }
        raw_text = json.dumps(raw_key, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    def get(self, table_name: str, key: str):
        if not self.enabled:
            return None

        table_key = self.table_key(table_name)
        now = time.time()

        with self._lock:
            table_cache = self._tables.get(table_key)
            if not table_cache:
                self._stats["misses"] += 1
                return None

            entry = table_cache.get(key)
            if not entry:
                self._stats["misses"] += 1
                return None

            if entry.expires_at < now:
                table_cache.pop(key, None)
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            return copy.deepcopy(entry.value)

    def set(self, table_name: str, key: str, value: Any, ttl: Optional[int] = None):
        if not self.enabled:
            return

        table_key = self.table_key(table_name)
        ttl_value = max(int(ttl or self.default_ttl), 1)
        now = time.time()

        with self._lock:
            table_cache = self._tables.setdefault(table_key, {})
            table_cache[key] = _DataPulseEntry(
                value=copy.deepcopy(value),
                expires_at=now + ttl_value,
                created_at=now,
            )
            self._stats["sets"] += 1
            self._prune_locked()

    def invalidate_table(self, table_name: str):
        table_key = self.table_key(table_name)
        if not table_key:
            return

        with self._lock:
            self._versions[table_key] = self._versions.get(table_key, 0) + 1
            self._tables.pop(table_key, None)
            self._stats["invalidations"] += 1

    def invalidate_tables(self, table_names: Iterable[str]):
        for table_name in table_names:
            self.invalidate_table(table_name)

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
        with self._lock:
            self._tables.clear()
            self._versions.clear()

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._stats)

    def _prune_locked(self):
        total_entries = sum(len(table_cache) for table_cache in self._tables.values())
        if total_entries <= self.max_entries:
            return

        entries = []
        for table_key, table_cache in self._tables.items():
            for key, entry in table_cache.items():
                entries.append((entry.created_at, table_key, key))

        entries.sort()
        remove_count = total_entries - self.max_entries
        for _, table_key, key in entries[:remove_count]:
            table_cache = self._tables.get(table_key)
            if table_cache:
                table_cache.pop(key, None)


data_pulse_cache = DataPulseCache()

''' [END CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 08/05/2026 '''
