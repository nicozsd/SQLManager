from __future__ import annotations

import threading
import time

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from ...controller.Cache import data_pulse_cache
from ..query.executor import DatasetExecutor
from ..registry import AnalyticsRegistry, analytics_registry


@dataclass
class MaterializationJob:
    name: str
    dataset_name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    interval_seconds: int = 300
    enabled: bool = True
    invalidate_first: bool = False
    last_run_started_at: Optional[float] = None
    last_run_finished_at: Optional[float] = None
    last_duration_ms: Optional[int] = None
    last_status: str = 'idle'
    last_error: Optional[str] = None
    last_meta: Dict[str, Any] = field(default_factory=dict)
    run_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'dataset_name': self.dataset_name,
            'payload': dict(self.payload),
            'interval_seconds': self.interval_seconds,
            'enabled': self.enabled,
            'invalidate_first': self.invalidate_first,
            'last_run_started_at': self.last_run_started_at,
            'last_run_finished_at': self.last_run_finished_at,
            'last_duration_ms': self.last_duration_ms,
            'last_status': self.last_status,
            'last_error': self.last_error,
            'last_meta': dict(self.last_meta),
            'run_count': self.run_count,
        }


class MaterializationScheduler:
    def __init__(self, executor: DatasetExecutor, registry: Optional[AnalyticsRegistry] = None):
        self.executor = executor
        self.registry = registry or analytics_registry
        self.cache = data_pulse_cache
        self._jobs: Dict[str, MaterializationJob] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._running_jobs: set[str] = set()

    def register_job(self, job: MaterializationJob, overwrite: bool = True) -> MaterializationJob:
        job_key = str(job.name or '').strip().lower()
        if not job_key:
            raise ValueError('MaterializationJob precisa de um nome valido')
        with self._lock:
            if not overwrite and job_key in self._jobs:
                return self._jobs[job_key]
            self._jobs[job_key] = job
            return job

    def load_from_config(self, jobs: Iterable[Dict[str, Any]]):
        for job_config in jobs or []:
            if not isinstance(job_config, dict):
                continue
            name = job_config.get('name') or job_config.get('dataset_name')
            dataset_name = job_config.get('dataset_name') or name
            if not name or not dataset_name:
                continue
            self.register_job(
                MaterializationJob(
                    name=str(name),
                    dataset_name=str(dataset_name),
                    payload=dict(job_config.get('payload') or {}),
                    interval_seconds=max(int(job_config.get('interval_seconds', 300) or 300), 5),
                    enabled=bool(job_config.get('enabled', True)),
                    invalidate_first=bool(job_config.get('invalidate_first', False)),
                )
            )

    def list_jobs(self) -> List[MaterializationJob]:
        with self._lock:
            return [self._jobs[key] for key in sorted(self._jobs.keys())]

    def get_job(self, job_name: str) -> Optional[MaterializationJob]:
        with self._lock:
            return self._jobs.get(str(job_name or '').strip().lower())

    def run_job(self, job_name: str) -> Dict[str, Any]:
        job = self.get_job(job_name)
        if job is None:
            raise KeyError(f"Materialization job '{job_name}' nao encontrado")
        return self._run_job(job)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name='SQLManagerMaterializationScheduler', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _loop(self):
        while not self._stop_event.is_set():
            now = time.time()
            for job in self.list_jobs():
                if not job.enabled:
                    continue
                if job.last_run_finished_at and (now - job.last_run_finished_at) < job.interval_seconds:
                    continue
                self._run_job(job)
            self._stop_event.wait(1)

    def _run_job(self, job: MaterializationJob) -> Dict[str, Any]:
        job_key = str(job.name or '').strip().lower()
        with self._lock:
            if job_key in self._running_jobs:
                return {
                    'status': 409,
                    'error': f"Materialization job '{job.name}' ja esta em execucao",
                    'data': job.to_dict(),
                }
            self._running_jobs.add(job_key)

        started_at = time.time()
        job.last_run_started_at = started_at
        job.last_status = 'running'
        job.last_error = None
        status_code = 200
        error_message = None
        try:
            if job.invalidate_first:
                self.cache.invalidate_dataset(job.dataset_name)
            response = self.executor.execute(job.dataset_name, job.payload)
            job.last_status = 'success'
            job.last_meta = dict(response.get('meta') or {})
        except Exception as exc:
            status_code = 500
            error_message = str(exc)
            job.last_status = 'error'
            job.last_error = error_message
        finally:
            finished_at = time.time()
            job.last_run_finished_at = finished_at
            job.last_duration_ms = int((finished_at - started_at) * 1000)
            job.run_count += 1
            with self._lock:
                self._running_jobs.discard(job_key)

        payload = {
            'status': status_code,
            'data': job.to_dict(),
        }
        if error_message:
            payload['error'] = error_message
        return payload