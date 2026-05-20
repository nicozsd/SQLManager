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

    def get_model_tables_query(self) -> str:
        return """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME
        """

    def get_model_views_query(self) -> str:
        return "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME"

    def get_model_columns_query(self) -> str:
        return f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = {self.get_parameter_marker()}
            ORDER BY ORDINAL_POSITION
        """

    def get_database_analysis_tables_query(self) -> str:
        return """
            /*sqlmanager:analysis_tables*/
            SELECT
                t.TABLE_NAME AS table_name,
                COALESCE(t.TABLE_ROWS, 0) AS row_count,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    WHERE tc.TABLE_SCHEMA = DATABASE() AND tc.TABLE_NAME = t.TABLE_NAME AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                ) THEN 1 ELSE 0 END AS has_primary_key,
                CASE WHEN EXISTS (
                    SELECT 1
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    WHERE tc.TABLE_SCHEMA = DATABASE() AND tc.TABLE_NAME = t.TABLE_NAME AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                ) THEN 1 ELSE 0 END AS has_clustered_index
            FROM INFORMATION_SCHEMA.TABLES t
            WHERE t.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE = 'BASE TABLE'
            ORDER BY t.TABLE_NAME
        """

    def get_database_analysis_columns_query(self) -> str:
        return """
            /*sqlmanager:analysis_columns*/
            SELECT
                TABLE_NAME AS table_name,
                COLUMN_NAME AS column_name,
                DATA_TYPE AS data_type,
                CASE WHEN IS_NULLABLE = 'YES' THEN 1 ELSE 0 END AS is_nullable,
                COALESCE(CHARACTER_MAXIMUM_LENGTH, 0) AS max_length
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """

    def get_database_analysis_indexes_query(self) -> str:
        return """
            /*sqlmanager:analysis_indexes*/
            SELECT
                TABLE_NAME AS table_name,
                INDEX_NAME AS index_name,
                CASE WHEN NON_UNIQUE = 0 THEN 1 ELSE 0 END AS is_unique,
                CASE WHEN INDEX_NAME = 'PRIMARY' THEN 1 ELSE 0 END AS is_primary_key,
                INDEX_TYPE AS index_type,
                CASE WHEN INDEX_NAME = 'PRIMARY' THEN 1 ELSE 0 END AS is_clustered,
                GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ',') AS key_columns,
                '' AS included_columns
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE, INDEX_TYPE
            ORDER BY TABLE_NAME, INDEX_NAME
        """

    def get_database_analysis_foreign_keys_query(self) -> str:
        return """
            /*sqlmanager:analysis_foreign_keys*/
            SELECT
                TABLE_NAME AS table_name,
                COLUMN_NAME AS column_name,
                CONSTRAINT_NAME AS foreign_key_name,
                REFERENCED_TABLE_NAME AS referenced_table,
                REFERENCED_COLUMN_NAME AS referenced_column
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION
        """

    def get_database_analysis_constraints_query(self) -> str:
        return """
            /*sqlmanager:analysis_constraints*/
            SELECT
                TABLE_NAME AS table_name,
                CONSTRAINT_NAME AS constraint_name,
                CONSTRAINT_TYPE AS constraint_type
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME, CONSTRAINT_NAME
        """

    def format_table_ddl(self, content: str) -> str:
        content = content.replace('[', '').replace(']', '')
        content = content.replace('IDENTITY(1,1)', 'AUTO_INCREMENT PRIMARY KEY')
        content = content.replace('nvarchar', 'VARCHAR')
        content = content.replace('varchar', 'VARCHAR')
        content = content.replace('bit', 'BOOLEAN')
        content = content.replace('SYSDATETIME()', 'CURRENT_TIMESTAMP')
        content = content.replace('GETDATE()', 'CURRENT_TIMESTAMP')
        
        # Remove espaços vazios, quebras de linha e a vírgula do final da string
        return content.strip().rstrip(',')