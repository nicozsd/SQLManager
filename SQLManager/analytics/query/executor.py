from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...CoreConfig import CoreConfig
from ...controller.Cache import data_pulse_cache
from ..metadata import Dataset, Measure
from ..registry import AnalyticsRegistry, analytics_registry


@dataclass
class AnalyticsQuery:
    dataset_name: str
    dimensions: List[str] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    order_by: Optional[str] = None
    descending: bool = False
    page: int = 1
    limit: int = 100
    include_total: bool = False
    user_context: Dict[str, Any] = field(default_factory=dict)


class DatasetExecutor:
    def __init__(self, db, registry: Optional[AnalyticsRegistry] = None):
        self.db = db
        self.registry = registry or analytics_registry
        self.cache = data_pulse_cache
        self.cache.bind_connection(db)
        self._metadata_cache: Dict[str, Tuple[Dict[str, str], Dict[str, str]]] = {}

    def execute(self, dataset_name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = self._coerce_query(dataset_name, payload or {})
        analytics_config = CoreConfig.get_analytics_config()
        self.cache.bind_connection(self.db)
        dataset = self.registry.ensure(query.dataset_name, modules=analytics_config.get('datasets_modules'))
        if dataset is None:
            raise KeyError(f"Dataset '{query.dataset_name}' nao encontrado")

        query.filters = dataset.merged_filters(query.filters)
        if dataset.security_policy is not None:
            dataset.security_policy.validate(query.filters, query.user_context)

        controller = self._instantiate_controller(dataset)
        fields_map, field_types = self._get_fields_map(dataset, controller)
        dimensions = self._resolve_dimensions(dataset, query.dimensions, fields_map)
        measures = self._resolve_measures(dataset, query.measures)
        where_sql, where_params = self._compile_filters(controller, query.filters, fields_map, field_types)

        cache_key = self.cache.make_query_key(
            [controller.source_name],
            'analytics',
            {
                'dimensions': dimensions,
                'measures': [measure.name for measure in measures],
                'filters': query.filters,
                'order_by': query.order_by,
                'descending': query.descending,
                'page': query.page,
                'limit': query.limit,
                'include_total': query.include_total,
            },
            dataset=dataset.name,
            security_scope=query.user_context.get('scope'),
        )

        ttl = dataset.cache_ttl or analytics_config.get('cache_ttl', 120)

        def resolver():
            return self._run_query(controller, dataset, query, dimensions, measures, where_sql, where_params)

        return self.cache.remember(
            controller.source_name,
            cache_key,
            resolver,
            ttl=ttl,
            tags=[controller.source_name, self.cache.dataset_key(dataset.name)],
        )

    def _coerce_query(self, dataset_name: str, payload: Dict[str, Any]) -> AnalyticsQuery:
        return AnalyticsQuery(
            dataset_name=dataset_name,
            dimensions=list(payload.get('dimensions') or []),
            measures=list(payload.get('measures') or []),
            filters=dict(payload.get('filters') or {}),
            order_by=payload.get('order_by'),
            descending=bool(payload.get('descending', False)),
            page=max(int(payload.get('page', 1) or 1), 1),
            limit=max(int(payload.get('limit', 100) or 100), 1),
            include_total=bool(payload.get('include_total', False)),
            user_context=dict(payload.get('user_context') or {}),
        )

    def _instantiate_controller(self, dataset: Dataset):
        model = dataset.source.resolve_model()
        if model is None:
            raise ValueError(f"Dataset '{dataset.name}' nao possui model associado")
        return model(self.db)

    def _metadata_cache_key(self, dataset: Dataset, controller) -> str:
        model = dataset.source.model or dataset.source.resolve_model()
        model_module = getattr(model, '__module__', '')
        model_name = getattr(model, '__qualname__', getattr(model, '__name__', 'model'))
        return f"{dataset.name.strip().lower()}::{controller.source_name}::{model_module}.{model_name}"

    def _get_fields_map(self, dataset: Dataset, controller) -> Tuple[Dict[str, str], Dict[str, str]]:
        cache_key = self._metadata_cache_key(dataset, controller)
        cached = self._metadata_cache.get(cache_key)
        if cached is not None:
            return cached

        fields_map: Dict[str, str] = {}
        field_types: Dict[str, str] = {}
        for field_name, field_type, _nullable in controller.get_table_columns():
            fields_map[str(field_name).upper()] = str(field_name)
            field_types[str(field_name).upper()] = str(field_type or '')
        cached = (fields_map, field_types)
        self._metadata_cache[cache_key] = cached
        return cached

    def _resolve_dimensions(self, dataset: Dataset, requested_dimensions: Iterable[str], fields_map: Dict[str, str]) -> List[str]:
        dimensions = list(requested_dimensions or dataset.dimensions)
        resolved = []
        for dimension in dimensions:
            real_name = fields_map.get(str(dimension).upper())
            if not real_name:
                raise ValueError(f"Dimensao invalida para dataset '{dataset.name}': {dimension}")
            resolved.append(real_name)
        return resolved

    def _resolve_measures(self, dataset: Dataset, requested_measures: Iterable[str]) -> List[Measure]:
        dataset.ensure_default_measure()
        if not requested_measures:
            return list(dataset.measures.values())
        measures = []
        for measure_name in requested_measures:
            if measure_name not in dataset.measures:
                raise ValueError(f"Measure invalida para dataset '{dataset.name}': {measure_name}")
            measures.append(dataset.measures[measure_name])
        return measures

    def _compile_filters(self, controller, filters: Dict[str, Any], fields_map: Dict[str, str], field_types: Dict[str, str]):
        where_condition = None
        for key, raw_value in filters.items():
            field_name_raw = key
            operator = 'eq'
            if '_' in key:
                parts = key.rsplit('_', 1)
                if parts[1] in ['eq', 'gt', 'gte', 'lt', 'lte', 'neq', 'like', 'in']:
                    field_name_raw = parts[0]
                    operator = parts[1]

            real_field_name = fields_map.get(str(field_name_raw).upper())
            if real_field_name is None:
                raise ValueError(f"Filtro invalido: {field_name_raw}")

            normalized_value = self._cast_value(raw_value, field_types.get(real_field_name.upper(), ''))
            field_attr = controller.field(real_field_name)
            match operator:
                case 'eq':
                    condition = field_attr == normalized_value
                case 'gt':
                    condition = field_attr > normalized_value
                case 'gte':
                    condition = field_attr >= normalized_value
                case 'lt':
                    condition = field_attr < normalized_value
                case 'lte':
                    condition = field_attr <= normalized_value
                case 'neq':
                    condition = field_attr != normalized_value
                case 'like':
                    condition = field_attr.like(str(normalized_value))
                case 'in':
                    condition = field_attr.in_(normalized_value if isinstance(normalized_value, list) else [normalized_value])
                case _:
                    raise ValueError(f"Operador nao suportado: {operator}")

            where_condition = condition if where_condition is None else (where_condition & condition)

        if where_condition is None:
            return '', []

        where_sql, where_values = where_condition.to_sql(controller.get_parameter_marker())
        params = where_values if isinstance(where_values, list) else [where_values]
        return where_sql, params

    def _cast_value(self, value: Any, field_type: str):
        if isinstance(value, list):
            return [self._cast_value(item, field_type) for item in value]
        if isinstance(value, str) and ',' in value and field_type and 'char' not in field_type.lower() and 'text' not in field_type.lower():
            return [self._cast_value(item.strip(), field_type) for item in value.split(',') if item.strip()]

        field_type_lower = str(field_type or '').lower()
        if isinstance(value, str):
            normalized = value.strip()
            if field_type_lower and any(token in field_type_lower for token in ('int', 'bigint', 'smallint', 'tinyint')):
                return int(normalized)
            if field_type_lower and any(token in field_type_lower for token in ('decimal', 'numeric', 'float', 'double', 'real', 'money')):
                return float(normalized)
            if field_type_lower and any(token in field_type_lower for token in ('bit', 'bool')):
                return normalized.lower() in ('1', 'true', 'yes', 'on')
        return value

    def _run_query(self, controller, dataset: Dataset, query: AnalyticsQuery, dimensions: List[str], measures: List[Measure], where_sql: str, where_params: List[Any]) -> Dict[str, Any]:
        measure_alias_map = {measure.name: ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in measure.name) or 'metric' for measure in measures}
        select_fields = list(dimensions)
        select_fields.extend(measure.sql_expression() for measure in measures)
        base_query = f"SELECT {', '.join(select_fields)} FROM {controller.source_name}"
        if where_sql:
            base_query += f" WHERE {where_sql}"
        if dimensions:
            base_query += " GROUP BY " + ', '.join(dimensions)

        order_by = query.order_by or dataset.default_order_by or (dimensions[0] if dimensions else None)
        if order_by:
            order_field = measure_alias_map.get(order_by, order_by)
            direction = 'DESC' if query.descending else 'ASC'
            base_query += f" ORDER BY {order_field} {direction}"

        paged_query = base_query
        offset = (query.page - 1) * query.limit
        if query.limit > 0 and hasattr(controller, 'format_pagination'):
            paged_query += controller.format_pagination(query.limit, offset)

        rows, columns = self._execute_query(controller, paged_query, tuple(where_params))
        data = [self._serialize_row(row, columns) for row in rows]

        total = None
        if query.include_total:
            total_query = f"SELECT COUNT(*) AS TOTAL FROM {controller.source_name}"
            if dimensions:
                total_query = f"SELECT COUNT(*) AS TOTAL FROM ({base_query}) AS analytics_total"
            elif where_sql:
                total_query += f" WHERE {where_sql}"
            total_rows, _ = self._execute_query(controller, total_query, tuple(where_params))
            total = int(total_rows[0][0]) if total_rows else 0

        return {
            'status': 200,
            'data': data,
            'meta': {
                'dataset': dataset.name,
                'page': query.page,
                'limit': query.limit,
                'count': len(data),
                'dimensions': dimensions,
                'measures': [measure.name for measure in measures],
                'total': total,
                'backend': self.cache.backend_name,
            },
        }

    def _execute_query(self, controller, query: str, params: Tuple[Any, ...]):
        if hasattr(controller.db, 'doQuery'):
            result = controller.db.doQuery(query, params, ret_cols=True)
            if isinstance(result, tuple) and len(result) == 2:
                return result
        if hasattr(controller.db, 'execute'):
            cursor = controller.db.execute(query, params)
            rows = cursor.fetchall() if hasattr(cursor, 'fetchall') else list(cursor)
            columns = [desc[0] for desc in getattr(cursor, 'description', [])]
            return rows, columns
        raise TypeError('Objeto de conexao nao suporta consultas analiticas')

    def _serialize_row(self, row: Any, columns: List[str]) -> Dict[str, Any]:
        if isinstance(row, dict):
            return dict(row)
        return {column: row[index] for index, column in enumerate(columns)}