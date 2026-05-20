from __future__ import annotations

import math
import time

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    rank = (len(ordered) - 1) * max(0.0, min(float(percentile), 1.0))
    lower_index = int(math.floor(rank))
    upper_index = int(math.ceil(rank))
    if lower_index == upper_index:
        return float(ordered[lower_index])
    weight = rank - lower_index
    return float((ordered[lower_index] * (1 - weight)) + (ordered[upper_index] * weight))


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    warmup: int
    total_ms: float
    avg_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    samples_ms: List[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'iterations': self.iterations,
            'warmup': self.warmup,
            'total_ms': round(self.total_ms, 3),
            'avg_ms': round(self.avg_ms, 3),
            'median_ms': round(self.median_ms, 3),
            'p95_ms': round(self.p95_ms, 3),
            'p99_ms': round(self.p99_ms, 3),
            'min_ms': round(self.min_ms, 3),
            'max_ms': round(self.max_ms, 3),
            'samples_ms': [round(sample, 3) for sample in self.samples_ms],
        }


def benchmark_callable(name: str, func: Callable[[], Any], iterations: int = 30, warmup: int = 5) -> BenchmarkResult:
    iterations = max(int(iterations or 1), 1)
    warmup = max(int(warmup or 0), 0)

    for _ in range(warmup):
        func()

    samples_ms: List[float] = []
    for _ in range(iterations):
        started_at = time.perf_counter_ns()
        func()
        elapsed_ms = (time.perf_counter_ns() - started_at) / 1_000_000
        samples_ms.append(elapsed_ms)

    total_ms = sum(samples_ms)
    return BenchmarkResult(
        name=name,
        iterations=iterations,
        warmup=warmup,
        total_ms=total_ms,
        avg_ms=(total_ms / iterations),
        median_ms=_percentile(samples_ms, 0.5),
        p95_ms=_percentile(samples_ms, 0.95),
        p99_ms=_percentile(samples_ms, 0.99),
        min_ms=min(samples_ms),
        max_ms=max(samples_ms),
        samples_ms=samples_ms,
    )


def benchmark_dataset_query(executor, dataset_name: str, payload: Optional[Dict[str, Any]] = None, iterations: int = 30, warmup: int = 5) -> BenchmarkResult:
    query_payload = dict(payload or {})
    return benchmark_callable(
        name=f'dataset:{dataset_name}',
        func=lambda: executor.execute(dataset_name, query_payload),
        iterations=iterations,
        warmup=warmup,
    )


def benchmark_select(name: str, select_callable: Callable[[], Any], iterations: int = 30, warmup: int = 5) -> BenchmarkResult:
    return benchmark_callable(name=name, func=select_callable, iterations=iterations, warmup=warmup)