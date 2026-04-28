from unittest import result

from .. import DialectMixin

class MySQLMixin(DialectMixin, dialect="mysql"):
    def db_name(self):
        return "MySQL"

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
        return ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP_CONCAT']
    
    def table_Columns(self) -> str:
        return "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = %s AND TABLE_SCHEMA = DATABASE()"

    def format_pagination(self, limit: int, offset: int) -> str:
        return f" LIMIT {limit} OFFSET {offset}"

    def format_index_hint(self, index_hint: str) -> str:
        return f" USE INDEX ({index_hint})" if index_hint else ""

    def get_parameter_marker(self) -> str:
        # Drivers PyMySQL/mysql-connector usa "%s"
        return "%s"

    def format_insert_query(self, table_name: str, fields: list) -> str:
        markers = ", ".join(["%s"] * len(fields))
        return f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({markers})"

    def execute_insert_and_get_id(self, trs, query: str, values: tuple) -> int:
        cursor = trs.connection.cursor()
        cursor.execute(query, values)
        last_id = cursor.lastrowid
        cursor.close()
        return last_id

    def get_columns_with_defaults_query(self) -> str:
        return f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = {self.get_parameter_marker()} AND COLUMN_DEFAULT IS NOT NULL"

    def get_table_index_query(self) -> str:
        return f"SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_NAME = {self.get_parameter_marker()}"

    def get_table_foreign_keys_query(self) -> str:
        return f"""
            SELECT CONSTRAINT_NAME AS f_key, TABLE_NAME AS t_origin, COLUMN_NAME AS c_origin, REFERENCED_TABLE_NAME AS t_reference, REFERENCED_COLUMN_NAME AS c_reference
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_NAME IS NOT NULL AND (TABLE_NAME = {self.get_parameter_marker()} OR REFERENCED_TABLE_NAME = {self.get_parameter_marker()})
        """