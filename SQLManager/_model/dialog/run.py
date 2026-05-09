import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from pathlib import Path

# --- CORREÇÃO DE PATH ---
# Garante que o Python encontre o módulo 'SQLManager' e a raiz do projeto
current_dir = os.path.dirname(os.path.abspath(__file__))
model_dir = os.path.dirname(current_dir)
package_dir = os.path.dirname(model_dir)
root_dir = os.path.dirname(package_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), ".env"))
    load_dotenv(os.path.join(root_dir, ".env"))
except ImportError:
    pass

from .UI.db_selector import DBSelector
from .UI.info_panel import InfoPanel
from .UI.action_button import ActionButton
from .UI.dashboard import MetadataDashboard
from .UI.button_modelupdate import Button_modelupdate

class dialog:
    """
    Orquestrador Principal da Janela de Configuração.
    Uso: 
        d = dialog("Atualização de modelos")
        d.start()
    """
    def __init__(self, title: str):
        self.root = tk.Tk()
        self.root.title(title)
        
        window_width = 860
        window_height = 840
        center_x = int((self.root.winfo_screenwidth() - window_width) / 2)
        center_y = int((self.root.winfo_screenheight() - window_height) / 2)
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.resizable(True, True)
        
        self._apply_theme()
        
        self.current_db_type = None
        self.require_recid_var = tk.BooleanVar(value=self._env_bool("SQLMANAGER_REQUIRE_RECID", True))
        
        # Inicializa a renderização da interface via herança/mixins
        self._build_ui()

    def _apply_theme(self):
        """Configura um estilo minimalista e moderno"""
        style = ttk.Style(self.root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        self.root.configure(bg="#F3F3F3")
        style.configure("TFrame", background="#F3F3F3")
        style.configure("TLabelframe", background="#F3F3F3", font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", background="#F3F3F3")
        style.configure("TLabel", background="#F3F3F3")
        style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#0078D7", foreground="white", padding=6)
        style.map("TButton", background=[("active", "#005A9E")])

    def _build_ui(self):
        main_container = ttk.Frame(self.root, padding=20)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Cabeçalho
        ttk.Label(main_container, text="Model Update", font=("Segoe UI", 16, "bold"), background="#F3F3F3").pack(pady=(0, 20))

        # 1. Seletor de Banco (Delegando renderização ao componente)
        self.db_selector = DBSelector(["SQL Server (SSMS)", "MySQL"], self._on_db_changed)
        self.db_selector.render(main_container, fill=tk.X, pady=(0, 15))

        # Preenche com o valor atual salvo no .env (se houver)
        db_env = os.getenv("DB_TYPE", "SQLSERVER").upper()
        if db_env == "MYSQL":
            self.db_selector.selected_value.set("MySQL")
            self.current_db_type = "MySQL"
        else:
            self.db_selector.selected_value.set("SQL Server (SSMS)")
            self.current_db_type = "SQL Server (SSMS)"

        # 2. Painel de Informações Seguras
        self.info_panel = InfoPanel()
        self.info_panel.render(main_container, fill=tk.X, pady=(0, 15))

        # 3. Dashboard de Metadados
        self.dashboard = MetadataDashboard()
        self.dashboard.render(main_container, fill=tk.BOTH, expand=True, pady=(0, 12))
        self._refresh_metadata()

        options_frame = ttk.LabelFrame(main_container, text=" Opcoes de Runtime ", padding=12)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Checkbutton(options_frame, text="Exigir RECID BIGINT no Model Update", variable=self.require_recid_var).pack(anchor=tk.W)

        # 4. Botões de Ação
        buttons_frame = ttk.Frame(main_container)
        buttons_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        self.btn_test = ActionButton("Testar Conexão", self._run_test_connection)
        self.btn_test.render(buttons_frame, side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.btn_modelupdate = Button_modelupdate("Atualizar Modelos", self._run_model_update)
        self.btn_modelupdate.render(buttons_frame, side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        self.btn_modelupdate.set_state(tk.DISABLED) # Começa desabilitado

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

    def _on_db_changed(self, selected_db: str):
        self.current_db_type = selected_db
        self._refresh_metadata()

    def _can_query_remote_metadata(self) -> bool:
        return all([
            self.info_panel.server_var.get().strip(),
            self.info_panel.database_var.get().strip(),
            self.info_panel.user_var.get().strip(),
            self.info_panel.password_var.get().strip(),
        ])

    def _get_remote_metadata(self):
        from SQLManager.connection import database_connection
        from SQLManager._model._model_update import ModelUpdaterBase

        self._apply_ui_credentials()

        dialect = ModelUpdaterBase()
        db = database_connection()
        db.connect()

        try:
            tables = db.doQuery(dialect.get_model_tables_query())
            views = db.doQuery(dialect.get_model_views_query())
            return [row[0] for row in tables], [row[0] for row in views]
        finally:
            db.disconnect()

    def _run_test_connection(self):
        self.btn_test.set_loading(True)
        self.root.update_idletasks() # Força update visual
        
        try:
            tables, views = self._get_remote_metadata()
            self._refresh_metadata(tables=tables, views=views)
            self.btn_modelupdate.set_state(tk.NORMAL)
            messagebox.showinfo("Sucesso", "Conexão estabelecida com sucesso e dados obtidos!")

        except Exception as e:
            error_msg = str(e)
            if "cryptography" in error_msg and "auth" in error_msg:
                error_msg += "\n\n[DICA DO SQLMANAGER]: O MySQL 8+ exige um pacote extra de segurança para a senha.\nAbra o seu terminal e instale rodando:\npip install cryptography"
                
            messagebox.showerror("Erro de Conexão", f"Falha ao conectar no banco de dados:\n\n{error_msg}")
            self.btn_modelupdate.set_state(tk.DISABLED)
            
        finally:
            self.btn_test.set_loading(False)

    def _apply_ui_credentials(self):
        """Captura os dados da tela e aplica ao CoreConfig apenas para a sessão atual (sem alterar o .env)."""
        from SQLManager import CoreConfig
        
        db_enum_val = "MYSQL" if self.current_db_type == "MySQL" else "SQLSERVER"
        os.environ["DB_TYPE"] = db_enum_val
        os.environ["DB_SERVER"] = self.info_panel.server_var.get()
        os.environ["DB_DATABASE"] = self.info_panel.database_var.get()
        os.environ["DB_USER"] = self.info_panel.user_var.get()
        os.environ["DB_PASSWORD"] = self.info_panel.password_var.get()
        os.environ["SQLMANAGER_REQUIRE_RECID"] = "true" if self.require_recid_var.get() else "false"

        CoreConfig.configure(load_from_env=True)

    def _model_folder(self, child: str) -> str:
        cwd_model = Path.cwd() / "src" / "model" / child
        if cwd_model.exists():
            return str(cwd_model)
        return os.path.join(root_dir, "src", "model", child)

    def _list_local_files(self, folder_path: str):
        if not os.path.exists(folder_path):
            return []

        files = []
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".py") and not file_name.startswith("__"):
                files.append(Path(file_name).stem)
        return sorted(files, key=str.lower)

    def _refresh_metadata(self, tables=None, views=None):
        if tables is None or views is None:
            if self._can_query_remote_metadata():
                try:
                    tables, views = self._get_remote_metadata()
                    self.btn_modelupdate.set_state(tk.NORMAL)
                except Exception:
                    tables = tables if tables is not None else []
                    views = views if views is not None else []
                    self.btn_modelupdate.set_state(tk.DISABLED)
            else:
                tables = tables if tables is not None else []
                views = views if views is not None else []
                self.btn_modelupdate.set_state(tk.DISABLED)

        self.dashboard.update_data(
            tables=tables,
            views=views,
            edts=self._list_local_files(self._model_folder("EDTs")),
            enums=self._list_local_files(self._model_folder("enum"))
        )

    def _run_model_update(self):
        """Inicia o processo real de atualização de modelos."""
        self.btn_modelupdate.set_loading(True, "Atualizando...")
        self.root.update_idletasks()

        try:
            # Garante que os dados em tela sejam aplicados antes da Model Update rodar
            self._apply_ui_credentials()

            # Importa e executa o ModelUpdater real (Issue #6)
            from SQLManager._model._model_update import ModelUpdater
            updater = ModelUpdater()
            updater.run(
                selected_tables=self.dashboard.get_selected_tables(),
                selected_views=self.dashboard.get_selected_views(),
            )
            self._refresh_metadata()
            
            messagebox.showinfo("Sucesso", "Modelos atualizados e gerados com sucesso!")
        except ImportError as ie:
            messagebox.showwarning("Erro de Importação", f"A classe ModelUpdater não pôde ser importada localmente:\n{ie}")
        except Exception as e:
            messagebox.showerror("Erro de Atualização", f"Ocorreu um erro ao gerar os modelos:\n{str(e)}")
        finally:
            self.btn_modelupdate.set_loading(False)
            self.root.destroy() # Fecha a janela e conclui o processo

    def start(self):
        self.root.mainloop()

if __name__ == "__main__":
    # Tenta carregar o .env para popular o InfoPanel no teste local
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(root_dir, ".env"))
    except ImportError:
        pass

    teste = dialog("Model Update")
    teste.start()
