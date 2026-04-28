from unittest import result

from .. import DialectMixin

class SQLServerMixin(DialectMixin, dialect="sqlserver"):
    def db_name(self):
        return "SQLServer"

    def protected_attr(self):
        protected_attrs = {
            'db', 'source_name', 'source_name', 'records', 'Columns', 'Indexes', 'ForeignKeys',
            '_where_conditions', '_columns', '_joins', '_order_by', '_limit',
            '_offset', '_group_by', '_having_conditions', '_distinct', '_do_update',
            'controller', '__class__', '__dict__', 'isUpdate', '_pending_wrapper',
            '__select_manager', 'field', 'select', 'insert', 'update', 'delete',
            'insert_recordset', 'update_recordset', 'delete_from', 'set_current',
            'clear', 'validate_fields', 'validate_write', 'get_table_columns',
            'get_columns_with_defaults', 'get_table_index', 'get_table_foreign_keys',
            'get_table_total', 'count', 'paginate', 'exists', '_get_field_instance', '_is_aggregate_function',
            '_extract_field_from_aggregate', 'SelectForUpdate', '_register_class_fields',
            'table_name', 'new_Relation', 'relations'
        }

        return protected_attrs
    
    def aggr_functions(self) -> list:
        return ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP_CONCAT', 'STRING_AGG']
    
    def table_Columns(self) -> str:
        return "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?"
    
    def format_pagination(self, limit: int, offset: int) -> str:
        return f" OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"

    def format_index_hint(self, index_hint: str) -> str:
        return f" WITH (INDEX({index_hint}))" if index_hint else ""

    def get_parameter_marker(self) -> str:
        # pyodbc padrão usa '?'
        return "?"

    def format_insert_query(self, table_name: str, fields: list) -> str:
        markers = ", ".join(["?"] * len(fields))
        return f"INSERT INTO {table_name} ({', '.join(fields)}) OUTPUT INSERTED.RECID VALUES ({markers})"

    def execute_insert_and_get_id(self, trs, query: str, values: tuple) -> int:
        result = trs.doQuery(query, values)
        return int(result[0][0]) if result and result[0][0] else None

    def get_columns_with_defaults_query(self) -> str:
        return f"""
        SELECT c.name FROM sys.columns c
        INNER JOIN sys.tables t ON c.object_id = t.object_id
        WHERE t.name = {self.get_parameter_marker()} AND c.default_object_id > 0
        """

    def get_table_index_query(self) -> str:
        return f"SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID({self.get_parameter_marker()})"

    def get_table_foreign_keys_query(self) -> str:
        return f"""
            SELECT fk.name AS f_key, tp.name AS t_origin, cp.name AS c_origin, tr.name AS t_reference, cr.name AS c_reference
            FROM sys.foreign_keys fk INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            WHERE tp.name = {self.get_parameter_marker()} OR tr.name = {self.get_parameter_marker()}
        """