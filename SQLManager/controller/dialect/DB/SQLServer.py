from unittest import result

from .. import DialectMixin
from ....CoreConfig import CoreConfig

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
        if not CoreConfig.require_recid():
            return f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({markers})"
        return f"INSERT INTO {table_name} ({', '.join(fields)}) OUTPUT INSERTED.RECID VALUES ({markers})"

    def execute_insert_and_get_id(self, trs, query: str, values: tuple) -> int:
        if not CoreConfig.require_recid():
            trs.executeCommand(query, values)
            return None
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

    def get_model_tables_query(self) -> str:
        return """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """

    def get_model_views_query(self) -> str:
        return "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS ORDER BY TABLE_NAME"

    def get_model_columns_query(self) -> str:
        return f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = {self.get_parameter_marker()}
            ORDER BY ORDINAL_POSITION
        """

    def get_database_analysis_tables_query(self) -> str:
        return """
            /*sqlmanager:analysis_tables*/
            SELECT
                t.name AS table_name,
                ISNULL((
                    SELECT SUM(p.rows)
                    FROM sys.partitions p
                    WHERE p.object_id = t.object_id AND p.index_id IN (0, 1)
                ), 0) AS row_count,
                CASE WHEN EXISTS (
                    SELECT 1 FROM sys.key_constraints kc
                    WHERE kc.parent_object_id = t.object_id AND kc.type = 'PK'
                ) THEN 1 ELSE 0 END AS has_primary_key,
                CASE WHEN EXISTS (
                    SELECT 1 FROM sys.indexes i
                    WHERE i.object_id = t.object_id AND i.type_desc IN ('CLUSTERED', 'CLUSTERED COLUMNSTORE')
                ) THEN 1 ELSE 0 END AS has_clustered_index
            FROM sys.tables t
            WHERE t.is_ms_shipped = 0
            ORDER BY t.name
        """

    def get_database_analysis_columns_query(self) -> str:
        return """
            /*sqlmanager:analysis_columns*/
            SELECT
                t.name AS table_name,
                c.name AS column_name,
                ty.name AS data_type,
                c.is_nullable AS is_nullable,
                c.max_length AS max_length
            FROM sys.tables t
            INNER JOIN sys.columns c ON t.object_id = c.object_id
            INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
            WHERE t.is_ms_shipped = 0
            ORDER BY t.name, c.column_id
        """

    def get_database_analysis_indexes_query(self) -> str:
        return """
            /*sqlmanager:analysis_indexes*/
            SELECT
                t.name AS table_name,
                i.name AS index_name,
                i.is_unique AS is_unique,
                i.is_primary_key AS is_primary_key,
                i.type_desc AS index_type,
                CASE WHEN i.type_desc IN ('CLUSTERED', 'CLUSTERED COLUMNSTORE') THEN 1 ELSE 0 END AS is_clustered,
                STRING_AGG(CASE WHEN ic.is_included_column = 0 THEN c.name END, ',') AS key_columns,
                STRING_AGG(CASE WHEN ic.is_included_column = 1 THEN c.name END, ',') AS included_columns
            FROM sys.tables t
            INNER JOIN sys.indexes i ON t.object_id = i.object_id
            LEFT JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            LEFT JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE t.is_ms_shipped = 0 AND i.name IS NOT NULL AND i.is_hypothetical = 0
            GROUP BY t.name, i.name, i.is_unique, i.is_primary_key, i.type_desc
            ORDER BY t.name, i.name
        """

    def get_database_analysis_foreign_keys_query(self) -> str:
        return """
            /*sqlmanager:analysis_foreign_keys*/
            SELECT
                tp.name AS table_name,
                cp.name AS column_name,
                fk.name AS foreign_key_name,
                tr.name AS referenced_table,
                cr.name AS referenced_column
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
            INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
            INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            ORDER BY tp.name, fk.name, fkc.constraint_column_id
        """

    def get_database_analysis_constraints_query(self) -> str:
        return """
            /*sqlmanager:analysis_constraints*/
            SELECT t.name AS table_name, kc.name AS constraint_name, kc.type_desc AS constraint_type
            FROM sys.key_constraints kc
            INNER JOIN sys.tables t ON kc.parent_object_id = t.object_id
            WHERE t.is_ms_shipped = 0
            UNION ALL
            SELECT t.name AS table_name, cc.name AS constraint_name, 'CHECK_CONSTRAINT' AS constraint_type
            FROM sys.check_constraints cc
            INNER JOIN sys.tables t ON cc.parent_object_id = t.object_id
            WHERE t.is_ms_shipped = 0
            UNION ALL
            SELECT t.name AS table_name, dc.name AS constraint_name, 'DEFAULT_CONSTRAINT' AS constraint_type
            FROM sys.default_constraints dc
            INNER JOIN sys.tables t ON dc.parent_object_id = t.object_id
            WHERE t.is_ms_shipped = 0
        """

    def format_table_ddl(self, content: str) -> str:
        # Remove espaços vazios, quebras de linha e a vírgula do final da string
        return content.strip().rstrip(',')
