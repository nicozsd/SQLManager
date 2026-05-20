from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from ...connection import Transaction, database_connection as data
from ..dialect import ControllerBase


class DatabaseAnalysisController(ControllerBase):
    def __init__(self, db: Union[data, Transaction]):
        self.db = db
        self.source_name = '__DATABASE_ANALYSIS__'

    def analyze_database(
        self,
        query_patterns: Optional[Iterable[Dict[str, Any]]] = None,
        large_table_threshold: int = 100000,
        bi_table_threshold: int = 250000,
    ) -> Dict[str, Any]:
        return self.analyze(
            query_patterns=query_patterns,
            large_table_threshold=large_table_threshold,
            bi_table_threshold=bi_table_threshold,
        )

    def analyze(
        self,
        query_patterns: Optional[Iterable[Dict[str, Any]]] = None,
        large_table_threshold: int = 100000,
        bi_table_threshold: int = 250000,
    ) -> Dict[str, Any]:
        tables = self._fetch_rows(self.get_database_analysis_tables_query())
        indexes = self._fetch_rows(self.get_database_analysis_indexes_query())
        columns = self._fetch_rows(self.get_database_analysis_columns_query())
        foreign_keys = self._fetch_rows(self.get_database_analysis_foreign_keys_query())
        constraints = self._fetch_rows(self.get_database_analysis_constraints_query())

        tables_by_name = {self._normalize_name(row.get('table_name')): self._normalize_table_row(row) for row in tables}
        indexes_by_table = defaultdict(list)
        for row in indexes:
            normalized = self._normalize_index_row(row)
            indexes_by_table[normalized['table_name']].append(normalized)

        columns_by_table = defaultdict(list)
        for row in columns:
            normalized = self._normalize_column_row(row)
            columns_by_table[normalized['table_name']].append(normalized)

        foreign_keys_by_table = defaultdict(list)
        for row in foreign_keys:
            normalized = self._normalize_fk_row(row)
            foreign_keys_by_table[normalized['table_name']].append(normalized)

        issues: List[Dict[str, Any]] = []
        recommendations: List[Dict[str, Any]] = []

        for table_name, table in tables_by_name.items():
            row_count = table['row_count']
            if not table['has_primary_key']:
                issues.append(self._issue(
                    table_name,
                    'missing-primary-key',
                    'high' if row_count >= large_table_threshold else 'medium',
                    'transaction',
                    f"Tabela {table_name} sem chave primaria.",
                    18,
                    8,
                ))

            if self._db_type() == 'sqlserver' and row_count >= large_table_threshold and not table['has_clustered_index']:
                issues.append(self._issue(
                    table_name,
                    'missing-clustered-index',
                    'medium',
                    'transaction',
                    f"Tabela {table_name} grande sem indice clustered.",
                    12,
                    6,
                ))

            table_indexes = indexes_by_table.get(table_name, [])
            if row_count >= large_table_threshold and not table_indexes:
                issues.append(self._issue(
                    table_name,
                    'large-table-without-indexes',
                    'high',
                    'hybrid',
                    f"Tabela {table_name} grande sem indices secundarios detectados.",
                    14,
                    18,
                ))

            if row_count >= bi_table_threshold and not self._has_columnstore_index(table_indexes):
                issues.append(self._issue(
                    table_name,
                    'bi-table-without-analytics-acceleration',
                    'medium',
                    'bi',
                    f"Tabela {table_name} com perfil analitico sem aceleracao dedicada para BI.",
                    0,
                    10,
                ))

        duplicate_indexes = self._detect_duplicate_indexes(indexes_by_table)
        for kept_index, duplicate_index in duplicate_indexes:
            issues.append(self._issue(
                duplicate_index['table_name'],
                'duplicate-index',
                'medium',
                'hybrid',
                f"Indice {duplicate_index['index_name']} duplica a cobertura de {kept_index['index_name']}.",
                5,
                5,
            ))
            recommendations.append({
                'table': duplicate_index['table_name'],
                'index': duplicate_index['index_name'],
                'fields': ', '.join(duplicate_index['key_columns']),
                'included_fields': ', '.join(duplicate_index['included_columns']),
                'kind': 'recommendation',
                'category': 'drop-duplicate-index',
                'workload': 'hybrid',
                'estimated_gain_pct': self._estimate_gain_pct(tables_by_name.get(duplicate_index['table_name'], {}).get('row_count', 0), base_gain=8),
                'severity': 'medium',
                'reason': f"Indice duplicado detectado: {duplicate_index['index_name']}",
                'ddl': self._build_drop_index_ddl(duplicate_index['table_name'], duplicate_index['index_name']),
                'action': 'drop',
            })

        for table_name, fk_rows in foreign_keys_by_table.items():
            row_count = tables_by_name.get(table_name, {}).get('row_count', 0)
            for fk in fk_rows:
                candidate_key = [fk['column_name']]
                if self._has_covering_index(indexes_by_table.get(table_name, []), candidate_key):
                    continue
                index_name = self._recommend_index_name(table_name, candidate_key)
                recommendations.append(self._build_index_recommendation(
                    table_name=table_name,
                    index_name=index_name,
                    key_columns=candidate_key,
                    included_columns=[],
                    workload='transaction',
                    category='foreign-key-index',
                    severity='high' if row_count >= large_table_threshold else 'medium',
                    reason=f"FK {fk['foreign_key_name']} em {fk['column_name']} sem indice de apoio.",
                    estimated_gain_pct=self._estimate_gain_pct(row_count, base_gain=22),
                ))

        for pattern in self._normalize_query_patterns(query_patterns):
            table_name = pattern['table']
            if table_name not in tables_by_name:
                continue
            key_columns = self._dedupe_preserving_order(
                pattern['filters_eq'] + pattern['range_filters'] + pattern['order_by']
            )
            included_columns = self._dedupe_preserving_order(pattern['include'] + pattern['group_by'])
            included_columns = [column for column in included_columns if column not in key_columns]
            if not key_columns or self._has_covering_index(indexes_by_table.get(table_name, []), key_columns):
                continue
            row_count = tables_by_name[table_name]['row_count']
            recommendations.append(self._build_index_recommendation(
                table_name=table_name,
                index_name=self._recommend_index_name(table_name, key_columns),
                key_columns=key_columns,
                included_columns=included_columns,
                workload=pattern['workload'],
                category='workload-index',
                severity='high' if row_count >= large_table_threshold else 'medium',
                reason=f"Padrao de consulta sem cobertura suficiente para {table_name}.",
                estimated_gain_pct=self._estimate_gain_pct(row_count, base_gain=18, frequency=pattern['frequency'], workload=pattern['workload']),
            ))

        grid = self._build_grid(indexes_by_table, recommendations)
        scores = self._build_scores(issues)

        return {
            'status': 200,
            'summary': {
                'database_type': self._db_type(),
                'tables': len(tables_by_name),
                'indexes': sum(len(items) for items in indexes_by_table.values()),
                'foreign_keys': sum(len(items) for items in foreign_keys_by_table.values()),
                'constraints': len(constraints),
                'issues': len(issues),
                'recommendations': len(recommendations),
                'duplicate_indexes': len(duplicate_indexes),
                'transaction_score': scores['transaction'],
                'bi_score': scores['bi'],
            },
            'tables': list(tables_by_name.values()),
            'columns': [row for rows in columns_by_table.values() for row in rows],
            'indexes': [row for rows in indexes_by_table.values() for row in rows],
            'foreign_keys': [row for rows in foreign_keys_by_table.values() for row in rows],
            'constraints': constraints,
            'issues': issues,
            'recommendations': recommendations,
            'grid': grid,
            'grid_columns': ['table', 'index', 'fields', 'included_fields', 'kind', 'category', 'workload', 'estimated_gain_pct', 'severity', 'reason', 'ddl', 'action'],
        }

    def apply_recommendations(self, recommendations: Iterable[Dict[str, Any]], dry_run: bool = True) -> List[Dict[str, Any]]:
        results = []
        for row in recommendations or []:
            ddl = str(row.get('ddl') or '').strip()
            if not ddl:
                continue
            result = {
                'table': row.get('table'),
                'index': row.get('index'),
                'action': row.get('action', 'create'),
                'ddl': ddl,
                'applied': False,
            }
            if not dry_run:
                self._execute_command(ddl)
                result['applied'] = True
            results.append(result)
        return results

    def _fetch_rows(self, query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        if hasattr(self.db, 'doQuery'):
            result = self.db.doQuery(query, params, ret_cols=True)
            if isinstance(result, tuple) and len(result) == 2:
                rows, columns = result
                return [self._row_to_dict(row, columns) for row in rows]
            if isinstance(result, list) and result and isinstance(result[0], dict):
                return [dict(row) for row in result]
            return []
        raise TypeError('Objeto de conexao nao suporta analise de banco')

    def _row_to_dict(self, row: Any, columns: List[str]) -> Dict[str, Any]:
        if isinstance(row, dict):
            return dict(row)
        return {columns[index]: row[index] for index in range(len(columns))}

    def _execute_command(self, command: str):
        if hasattr(self.db, 'executeCommand'):
            return self.db.executeCommand(command)
        if hasattr(self.db, 'execute'):
            return self.db.execute(command)
        raise TypeError('Objeto de conexao nao suporta execucao de comandos')

    def _normalize_name(self, value: Any) -> str:
        return str(value or '').strip().upper()

    def _normalize_table_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'table_name': self._normalize_name(row.get('table_name')),
            'row_count': int(row.get('row_count') or 0),
            'has_primary_key': bool(row.get('has_primary_key')),
            'has_clustered_index': bool(row.get('has_clustered_index')),
        }

    def _normalize_index_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'table_name': self._normalize_name(row.get('table_name')),
            'index_name': str(row.get('index_name') or '').strip(),
            'is_unique': bool(row.get('is_unique')),
            'is_primary_key': bool(row.get('is_primary_key')),
            'index_type': str(row.get('index_type') or '').strip().upper(),
            'is_clustered': bool(row.get('is_clustered')),
            'key_columns': self._split_columns(row.get('key_columns')),
            'included_columns': self._split_columns(row.get('included_columns')),
        }

    def _normalize_column_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'table_name': self._normalize_name(row.get('table_name')),
            'column_name': self._normalize_name(row.get('column_name')),
            'data_type': str(row.get('data_type') or '').strip().lower(),
            'is_nullable': bool(row.get('is_nullable')),
            'max_length': int(row.get('max_length') or 0),
        }

    def _normalize_fk_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'table_name': self._normalize_name(row.get('table_name')),
            'column_name': self._normalize_name(row.get('column_name')),
            'foreign_key_name': str(row.get('foreign_key_name') or '').strip(),
            'referenced_table': self._normalize_name(row.get('referenced_table')),
            'referenced_column': self._normalize_name(row.get('referenced_column')),
        }

    def _split_columns(self, value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            parts = value
        else:
            parts = str(value).split(',')
        return [self._normalize_name(part) for part in parts if str(part).strip()]

    def _db_type(self) -> str:
        db_type = getattr(self.db, 'db_type', None)
        if not db_type and hasattr(self.db, '_db'):
            db_type = getattr(self.db._db, 'db_type', None)
        return str(db_type or 'sqlserver').lower()

    def _issue(self, table: str, category: str, severity: str, workload: str, message: str, transaction_penalty: int, bi_penalty: int) -> Dict[str, Any]:
        return {
            'table': table,
            'category': category,
            'severity': severity,
            'workload': workload,
            'message': message,
            'transaction_penalty': transaction_penalty,
            'bi_penalty': bi_penalty,
        }

    def _detect_duplicate_indexes(self, indexes_by_table: Dict[str, List[Dict[str, Any]]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        duplicates: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for table_indexes in indexes_by_table.values():
            seen: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
            for index in table_indexes:
                signature = (
                    tuple(index['key_columns']),
                    tuple(index['included_columns']),
                    index['is_unique'],
                )
                if not signature[0]:
                    continue
                previous = seen.get(signature)
                if previous is None:
                    seen[signature] = index
                    continue
                kept = previous if previous['is_primary_key'] else previous
                duplicate = index if not index['is_primary_key'] else previous
                duplicates.append((kept, duplicate))
        return duplicates

    def _has_covering_index(self, indexes: Iterable[Dict[str, Any]], candidate_key_columns: Iterable[str]) -> bool:
        candidate = [self._normalize_name(column) for column in candidate_key_columns if self._normalize_name(column)]
        if not candidate:
            return True
        for index in indexes or []:
            existing = [self._normalize_name(column) for column in index.get('key_columns', [])]
            if len(existing) >= len(candidate) and existing[:len(candidate)] == candidate:
                return True
        return False

    def _has_columnstore_index(self, indexes: Iterable[Dict[str, Any]]) -> bool:
        for index in indexes or []:
            if 'COLUMNSTORE' in str(index.get('index_type') or '').upper():
                return True
        return False

    def _normalize_query_patterns(self, query_patterns: Optional[Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        normalized_patterns = []
        for pattern in query_patterns or []:
            if not isinstance(pattern, dict):
                continue
            table = self._normalize_name(pattern.get('table'))
            if not table:
                continue
            normalized_patterns.append({
                'table': table,
                'filters_eq': self._normalize_column_list(pattern.get('filters_eq')),
                'range_filters': self._normalize_column_list(pattern.get('range_filters')),
                'order_by': self._normalize_column_list(pattern.get('order_by')),
                'group_by': self._normalize_column_list(pattern.get('group_by')),
                'include': self._normalize_column_list(pattern.get('include')),
                'frequency': max(int(pattern.get('frequency', 1) or 1), 1),
                'workload': str(pattern.get('workload') or 'hybrid').strip().lower(),
            })
        return normalized_patterns

    def _normalize_column_list(self, value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [self._normalize_name(part) for part in value.split(',') if str(part).strip()]
        if isinstance(value, (list, tuple, set)):
            return [self._normalize_name(part) for part in value if self._normalize_name(part)]
        return []

    def _dedupe_preserving_order(self, values: Iterable[str]) -> List[str]:
        seen = set()
        ordered = []
        for value in values:
            normalized = self._normalize_name(value)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered

    def _estimate_gain_pct(self, row_count: int, base_gain: int, frequency: int = 1, workload: str = 'hybrid') -> int:
        if row_count >= 1000000:
            size_bonus = 26
        elif row_count >= 250000:
            size_bonus = 18
        elif row_count >= 50000:
            size_bonus = 10
        else:
            size_bonus = 4
        frequency_bonus = min(max(frequency - 1, 0) * 2, 16)
        workload_bonus = 6 if workload == 'bi' else 4 if workload == 'transaction' else 5
        return max(5, min(base_gain + size_bonus + frequency_bonus + workload_bonus, 85))

    def _recommend_index_name(self, table_name: str, key_columns: Iterable[str]) -> str:
        suffix = '_'.join(self._normalize_name(column) for column in key_columns if self._normalize_name(column))
        name = f"IX_{table_name}_{suffix}" if suffix else f"IX_{table_name}_AUTO"
        return name[:120]

    def _build_index_recommendation(
        self,
        table_name: str,
        index_name: str,
        key_columns: List[str],
        included_columns: List[str],
        workload: str,
        category: str,
        severity: str,
        reason: str,
        estimated_gain_pct: int,
    ) -> Dict[str, Any]:
        return {
            'table': table_name,
            'index': index_name,
            'fields': ', '.join(key_columns),
            'included_fields': ', '.join(included_columns),
            'kind': 'recommendation',
            'category': category,
            'workload': workload,
            'estimated_gain_pct': estimated_gain_pct,
            'severity': severity,
            'reason': reason,
            'ddl': self._build_create_index_ddl(table_name, index_name, key_columns, included_columns),
            'action': 'create',
        }

    def _build_grid(self, indexes_by_table: Dict[str, List[Dict[str, Any]]], recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grid = []
        for table_name in sorted(indexes_by_table.keys()):
            for index in indexes_by_table[table_name]:
                grid.append({
                    'table': table_name,
                    'index': index['index_name'],
                    'fields': ', '.join(index['key_columns']),
                    'included_fields': ', '.join(index['included_columns']),
                    'kind': 'existing',
                    'category': 'existing-index',
                    'workload': 'hybrid',
                    'estimated_gain_pct': 0,
                    'severity': 'info',
                    'reason': index['index_type'],
                    'ddl': None,
                    'action': 'keep',
                })
        grid.extend(recommendations)
        return grid

    def _build_scores(self, issues: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        transaction_score = 100
        bi_score = 100
        for issue in issues or []:
            transaction_score -= int(issue.get('transaction_penalty') or 0)
            bi_score -= int(issue.get('bi_penalty') or 0)
        return {
            'transaction': max(0, transaction_score),
            'bi': max(0, bi_score),
        }

    def _build_create_index_ddl(self, table_name: str, index_name: str, key_columns: List[str], included_columns: List[str]) -> str:
        quoted_index = self._quote_identifier(index_name)
        quoted_table = self._quote_identifier(table_name)
        quoted_keys = ', '.join(self._quote_identifier(column) for column in key_columns)
        if self._db_type() == 'mysql':
            return f"CREATE INDEX {quoted_index} ON {quoted_table} ({quoted_keys})"
        include_clause = ''
        if included_columns:
            include_clause = ' INCLUDE (' + ', '.join(self._quote_identifier(column) for column in included_columns) + ')'
        return f"CREATE NONCLUSTERED INDEX {quoted_index} ON {quoted_table} ({quoted_keys}){include_clause}"

    def _build_drop_index_ddl(self, table_name: str, index_name: str) -> str:
        quoted_index = self._quote_identifier(index_name)
        quoted_table = self._quote_identifier(table_name)
        if self._db_type() == 'mysql':
            return f"DROP INDEX {quoted_index} ON {quoted_table}"
        return f"DROP INDEX {quoted_index} ON {quoted_table}"

    def _quote_identifier(self, value: str) -> str:
        raw = str(value or '').strip()
        if self._db_type() == 'mysql':
            return f"`{raw}`"
        return f"[{raw}]"