''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''

''' [BEGIN CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''

'''
Atualização automática de modelos (EDTs, Enums, Tables e Views) baseada na estrutura do banco de dados SQL Server.
Lê banco de dados e sincroniza com aplicação, gerando __init__.py automaticamente
'''

from . import *
from SQLManager.controller.dialect import DialectMixin
import os

class ModelUpdaterBase(DialectMixin):
    def __new__(cls, *args, **kwargs):
        from SQLManager import CoreConfig
        dialect_name = CoreConfig.get_db_config().get('type', 'sqlserver').lower()
        mixin_cls = DialectMixin.resolve(dialect_name)
        
        if not mixin_cls:
            mixin_cls = DialectMixin.resolve('sqlserver')
            
        if mixin_cls in cls.__mro__:
            return object.__new__(cls)
            
        dynamic_name = f"{cls.__name__}_{dialect_name}"
        dynamic_cls = type(dynamic_name, (mixin_cls, cls), {})
        
        return object.__new__(dynamic_cls)

class ModelUpdater(ModelUpdaterBase):
    '''Atualização automática de modelos'''

    @staticmethod
    def _get_values(obj):
        '''Retorna valores de dict ou lista de forma compatível'''
        if isinstance(obj, dict):
            return obj.values()
        elif isinstance(obj, list):
            return obj
        else:
            return obj

    def ensurer_database(self, name:str, content:str):
        """Garante a criação de uma nova tabela no banco de dados caso não exista"""
        if not name:
            return
        query = self.get_model_tables_query()
        
        tables = self.db.doQuery(query)
        db_tables_lower = [row[0].lower() for row in tables]
        if name.lower() not in db_tables_lower:
            
            # Adaptação on-the-fly de DDL utilizando a arquitetura de Dialetos
            content = self.format_table_ddl(content)

            query = f"""
            CREATE TABLE {name} ({content})
            """
            
            self.db.executeCommand(query)

    def ensurer(self, ref_Path: Path, content: str):
        '''Garante que arquivo exista com conteúdo específico'''
        if not ref_Path.exists():
            with open(ref_Path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Criado: {SystemController().custom_text(ref_Path.name, 'green')}")
        else:
            print(f"Existente: {SystemController().custom_text(ref_Path.name, 'yellow')}")

    def _clear_init_files(self):
        '''Limpa arquivos __init__.py de EDTs, Enums, Tables e Views'''
        init_files = [
            self.edts_path   / "__init__.py",
            self.enums_path  / "__init__.py",
            self.tables_path / "__init__.py",
            self.views_path  / "__init__.py"
        ]
        
        for init_file in init_files:
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write("# Auto-generated file - será atualizado automaticamente\n\n__all__ = []\n")
        
        print(SystemController().custom_text("Arquivos __init__.py limpos", "red", is_bold=True))

    def _generate_model_init(self):
        '''Gera __init__.py da pasta src/model/'''
        model_init_file = self.model_path / "__init__.py"
        content = (
            "from . import EDTs   as EDTPack\n"
            "from . import enum   as EnumPack\n"
            "from . import views  as ViewPack\n"
            "from . import tables as TablePack\n\n"
            "__all__ = [\n"
            "    \"EDTPack\",\n"
            "    \"EnumPack\",\n"
            "    \"ViewPack\",\n"
            "    \"TablePack\",\n"
            "]\n"
        )

        with open(model_init_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def __init__(self):
        self.db = database_connection()
        self.db.connect()
        
        project_root = Path.cwd()
        self.model_path  = project_root / "src" / "model"
        self.edts_path   = self.model_path  / "EDTs"
        self.enums_path  = self.model_path  / "enum"
        self.tables_path = self.model_path  / "tables"
        self.views_path  = self.model_path  / "views"

        self.edts_path.mkdir(parents=True, exist_ok=True)
        self.enums_path.mkdir(parents=True, exist_ok=True)
        self.tables_path.mkdir(parents=True, exist_ok=True)
        self.views_path.mkdir(parents=True, exist_ok=True)
                
        self.available_edts   = {}
        self.available_enums  = {}
        self.available_tables = {}
        self.available_views  = {}
                
        self.edt_file_to_class   = {}
        self.enum_file_to_class  = {}
        self.table_file_to_class = {}
        self.view_file_to_class  = {}
                
        self.sql_type_mapping = {
            'int':          ('int', 'DataType.Number'),
            'bigint':       ('int', 'DataType.Number'),
            'smallint':     ('int', 'DataType.Number'),
            'tinyint':      ('int', 'DataType.Number'),
            'bit':          ('bool', 'DataType.Boolean'),
            'decimal':      ('float', 'DataType.Float'),
            'numeric':      ('float', 'DataType.Float'),
            'money':        ('float', 'DataType.Float'),
            'float':        ('float', 'DataType.Float'),
            'real':         ('float', 'DataType.Float'),
            'varchar':      ('str', 'DataType.String'),
            'nvarchar':     ('str', 'DataType.String'),
            'char':         ('str', 'DataType.String'),
            'nchar':        ('str', 'DataType.String'),
            'text':         ('str', 'DataType.String'),
            'ntext':        ('str', 'DataType.String'),
            'datetime':     ('str', 'DataType.String'),
            'datetime2':    ('str', 'DataType.String'),
            'date':         ('str', 'DataType.String'),
            'time':         ('str', 'DataType.String'),
        }
    
    def __del__(self):
        '''Fecha conexão ao destruir objeto'''
        if hasattr(self, 'db'):
            self.db.disconnect()    
    
    def run(self):
        '''Executa atualização completa'''
        print("="*40)
        print("MODEL UPDATE")
        print("="*40)

        existing_tables = list(self.tables_path.glob("*.py"))
        existing_tables = [f for f in existing_tables if not f.name.startswith("_")]
        
        if existing_tables:
            print(f"\n{SystemController().custom_text('ATENÇÃO', 'red', is_bold=True)}")
            print(f"Tabelas não existentes no banco serão {SystemController().custom_text('REMOVIDAS', 'red', is_bold=True)}.")
            print(f"Faça {SystemController().custom_text('BACKUP', 'yellow', is_bold=True)} de src/model/tables antes de continuar.")
            
            ui_resposta = None
            try:
                import tkinter as tk
                from tkinter import messagebox
                
                root = tk._default_root
                is_temp_root = False
                if root is None:
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    is_temp_root = True
                    
                ui_resposta = messagebox.askyesno(
                    "Aviso de Segurança - SQLManager",
                    "ATENÇÃO!\n\n"
                    "Tabelas não existentes no banco de dados serão REMOVIDAS.\n"
                    "Faça BACKUP da pasta 'src/model/tables' antes de continuar.\n\n"
                    "Deseja continuar com a atualização?",
                    icon='warning'
                )
                
                if is_temp_root:
                    root.destroy()
            except Exception:
                pass # Falha ao abrir UI, segue para o fallback de terminal
                
            if ui_resposta is None:
                print(f"\nContinuar? ({SystemController().custom_text('y', 'green')}/{SystemController().custom_text('n', 'red')})")
                resposta = input().strip().lower()
                if resposta != "y":
                    print("Cancelado pelo usuário.")
                    raise Exception("Atualização cancelada pelo usuário.")
            elif ui_resposta is False:
                print("Cancelado pelo usuário.")
                raise Exception("Atualização cancelada pelo usuário.")

        try:            
            utils.stepInfo("00", "Limpando arquivos __init__.py")
            self._clear_init_files()

            utils.stepInfo("00.0", "Gerando __init__.py da pasta src/model/")
            self._generate_model_init()

            utils.stepInfo("00.1", "Garantindo Enums obrigatórios")
            for enum in self._get_values(enums):
                self.ensurer(self.enums_path, enum)

            utils.stepInfo("00.2", "Garantindo EDTs obrigatórios")
            for edt in self._get_values(EDTs):
                self.ensurer(self.edts_path, edt)

            utils.stepInfo("00.3", "Garantindo Tables obrigatórios")
            for table in tables:
                self.ensurer_database(table, tables[table])

            utils.stepInfo("01.1", "Escaneando EDTs existentes")
            EDT_Manager._scan_existing_edts(self, _ShowEDTs=True)

            utils.stepInfo("01.2", "Atualizando Model de EDTs")
            EDT_Manager._update_edts_init(self)

            utils.stepInfo("02.1", "Escaneando Enums existentes")
            Enum_Manager._scan_existing_enums(self, _ShowEnums=True)

            utils.stepInfo("02.2", "Atualizando Model de Enums")
            Enum_Manager._update_enums_init(self)

            utils.stepInfo("03.1", "Escaneando Tables existentes")
            Table_Manager._scan_existing_tables(self, _ShowTables=True)

            utils.stepInfo("03.2", "Atualizando Tables")
            Table_Manager._update_tables(self)

            utils.stepInfo("03.3", "Atualizando model de Tables")
            Table_Manager._scan_existing_tables(self, _ShowTables=True)
            Table_Manager._update_tables_init(self)

            utils.stepInfo("04.1", "Escaneando Views existentes")
            View_Manager._scan_existing_views(self, _ShowViews=True)

            utils.stepInfo("04.2", "Atualizando Views")
            View_Manager._update_views(self)

            utils.stepInfo("04.3", "Atualizando model de Views")
            View_Manager._update_views_init(self)

            print("\n" + "="*40)
            print("ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
            print("="*40)

        except Exception as e:
            print(f"\n[ERRO] Falha na atualização: {str(e)}")
            raise
   
if __name__ == "__main__":
    import sys
    
    # Se o usuário passou parâmetros na linha de comando (CLI), roda direto no terminal
    if len(sys.argv) > 1:
        updater = ModelUpdater().run()
    else:
        try:
            # Tenta carregar a Janela de Interface Gráfica
            from SQLManager._model.dialog.run import dialog
            app_dialog = dialog("Model Update")
            app_dialog.start()
        except Exception as e:
            # Fallback seguro para servidores sem interface (Headless / SSH)
            print(f"\n[SQLManager] Interface gráfica indisponível ({e}). Iniciando via terminal...\n")
            updater = ModelUpdater().run()

''' [END CODE] Project: SQLManager Version 4.0 / issue: #4 / made by: Nicolas Santos / created: 23/02/2026 '''

''' [END CODE] Project: SQLManager Version 4.0 / issue: #6 / made by: Nicolas Santos / created: 26/02/2026 '''