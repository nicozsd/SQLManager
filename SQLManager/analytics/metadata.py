from __future__ import annotations

import importlib

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence


def _safe_alias(value: str) -> str:
    return ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in str(value or '').strip()) or 'metric'


@dataclass
class DataSource:
    name: str
    model: Optional[Any] = None
    model_path: Optional[str] = None
    connection: str = 'default'
    kind: str = 'model'
    read_only: bool = True
    description: str = ''

    def resolve_model(self):
        if self.model is not None:
            return self.model
        if not self.model_path:
            return None
        module_name, _, attr_name = self.model_path.partition(':')
        if not module_name or not attr_name:
            raise ValueError(f"model_path invalido: {self.model_path}")
        module = importlib.import_module(module_name)
        self.model = getattr(module, attr_name)
        return self.model


@dataclass
class Measure:
    name: str
    aggregation: str = 'count'
    field: Optional[str] = None
    label: Optional[str] = None
    description: str = ''
    formatter: Optional[str] = None

    def sql_expression(self) -> str:
        aggregation = str(self.aggregation or 'count').strip().upper()
        field_name = '*'
        if aggregation != 'COUNT' or self.field:
            if not self.field:
                raise ValueError(f"Measure '{self.name}' requer um field para aggregation {aggregation}")
            field_name = self.field
        return f"{aggregation}({field_name}) AS {_safe_alias(self.name)}"


@dataclass
class Hierarchy:
    name: str
    levels: Sequence[str]
    description: str = ''


@dataclass
class SecurityPolicy:
    name: str = 'default'
    required_filters: Dict[str, Any] = field(default_factory=dict)
    allowed_values: Dict[str, Sequence[Any]] = field(default_factory=dict)

    def validate(self, filters: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None):
        normalized_filters = filters or {}
        for field_name, expected_value in self.required_filters.items():
            if field_name not in normalized_filters:
                raise PermissionError(f"Filtro obrigatorio ausente para policy '{self.name}': {field_name}")
            if expected_value is not None and normalized_filters[field_name] != expected_value:
                raise PermissionError(f"Filtro '{field_name}' viola a policy '{self.name}'")

        for field_name, allowed in self.allowed_values.items():
            if field_name not in normalized_filters:
                continue
            value = normalized_filters[field_name]
            values = value if isinstance(value, list) else [value]
            if any(item not in allowed for item in values):
                raise PermissionError(f"Valor nao permitido em '{field_name}' para policy '{self.name}'")


@dataclass
class Dataset:
    name: str
    source: DataSource
    dimensions: List[str] = field(default_factory=list)
    measures: Dict[str, Measure] = field(default_factory=dict)
    hierarchies: Dict[str, Hierarchy] = field(default_factory=dict)
    security_policy: Optional[SecurityPolicy] = None
    default_filters: Dict[str, Any] = field(default_factory=dict)
    default_order_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: str = ''
    auto_discover_dimensions: bool = True
    cache_ttl: Optional[int] = None

    def add_measure(self, measure: Measure) -> 'Dataset':
        self.measures[measure.name] = measure
        return self

    def add_hierarchy(self, hierarchy: Hierarchy) -> 'Dataset':
        self.hierarchies[hierarchy.name] = hierarchy
        return self

    def ensure_default_measure(self):
        if not self.measures:
            self.add_measure(Measure(name='records', aggregation='count'))

    def merged_filters(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged = dict(self.default_filters)
        merged.update(filters or {})
        return merged

    def to_dict(self) -> Dict[str, Any]:
        self.ensure_default_measure()
        return {
            'name': self.name,
            'source': {
                'name': self.source.name,
                'kind': self.source.kind,
                'connection': self.source.connection,
                'read_only': self.source.read_only,
            },
            'dimensions': list(self.dimensions),
            'measures': [
                {
                    'name': measure.name,
                    'aggregation': measure.aggregation,
                    'field': measure.field,
                    'label': measure.label,
                    'description': measure.description,
                }
                for measure in self.measures.values()
            ],
            'hierarchies': [
                {
                    'name': hierarchy.name,
                    'levels': list(hierarchy.levels),
                    'description': hierarchy.description,
                }
                for hierarchy in self.hierarchies.values()
            ],
            'default_filters': dict(self.default_filters),
            'default_order_by': self.default_order_by,
            'tags': list(self.tags),
            'description': self.description,
            'auto_discover_dimensions': self.auto_discover_dimensions,
            'cache_ttl': self.cache_ttl,
        }


def build_default_dataset(name: str, model: Any, module_name: str = '') -> Dataset:
    dataset = Dataset(
        name=name,
        source=DataSource(
            name=name,
            model=model,
            model_path=f"{module_name}:{name}" if module_name else None,
            kind='model',
            read_only=True,
        ),
        description=f"Dataset autodetectado para {name}",
        tags=['AUTO'],
        auto_discover_dimensions=True,
    )
    dataset.add_measure(Measure(name='records', aggregation='count'))
    return dataset


def filter_public_names(names: Iterable[str]) -> List[str]:
    return [name for name in names if not str(name).startswith('_')]