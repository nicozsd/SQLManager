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