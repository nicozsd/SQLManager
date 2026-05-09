import tkinter as tk
from tkinter import messagebox
import os
import sys
from pathlib import Path
import customtkinter as ctk

try:
    from PIL import Image
except ImportError:
    Image = None

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
from .UI.theme import APP_DESCRIPTION, APP_SUBTITLE, APP_TAGS, APP_TITLE, COLORS, FONTS

class dialog:
    """
    Orquestrador Principal da Janela de Configuração.
    Uso: 
        d = dialog("Atualização de modelos")
        d.start()
    """
    def __init__(self, title: str):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        
        window_width = 980
        window_height = 840
        center_x = int((self.root.winfo_screenwidth() - window_width) / 2)
        center_y = int((self.root.winfo_screenheight() - window_height) / 2)
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.resizable(True, True)
        
        self._apply_theme()
        
        self.current_db_type = None
        self.require_recid_var = tk.BooleanVar(value=self._env_bool("SQLMANAGER_REQUIRE_RECID", True))
        self.btn_test = None
        self.btn_modelupdate = None
        self.brand_image = None
        self.window_icon = None
        
        # Inicializa a renderização da interface via herança/mixins
        self._build_ui()

    def _apply_theme(self):
        self.root.configure(fg_color=COLORS["bg"])
        self._apply_window_icon()

    def _asset_path(self, file_name: str) -> Path:
        local_asset = Path(__file__).resolve().parent / "assets" / file_name
        if local_asset.exists():
            return local_asset
        return Path(root_dir) / "assets" / file_name

    def _apply_window_icon(self):
        icon_path = self._asset_path("app_icon.png")
        if icon_path.exists():
            try:
                self.window_icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(False, self.window_icon)
            except Exception:
                self.window_icon = None

    def _load_brand_image(self):
        if Image is None:
            return None
        icon_path = self._asset_path("app_icon.png")
        if not icon_path.exists():
            return None
        try:
            return ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(88, 88))
        except Exception:
            return None

    def _build_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=24, border_width=1, border_color=COLORS["border"])
        header.pack(fill="x", pady=(0, 18))
        header.grid_columnconfigure(1, weight=1)

        self.brand_image = self._load_brand_image()
        icon_holder = ctk.CTkFrame(header, width=110, height=110, fg_color=COLORS["panel_alt"], corner_radius=22, border_width=1, border_color=COLORS["border"])
        icon_holder.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=18, pady=18)
        icon_holder.grid_propagate(False)

        if self.brand_image is not None:
            ctk.CTkLabel(icon_holder, text="", image=self.brand_image).pack(expand=True)
        else:
            ctk.CTkLabel(icon_holder, text="SQL", font=("Segoe UI Black", 28), text_color=COLORS["cyan"]).pack(expand=True)

        text_col = ctk.CTkFrame(header, fg_color="transparent")
        text_col.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=(18, 8))

        ctk.CTkLabel(text_col, text=APP_TITLE, font=FONTS["title"], text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(text_col, text=APP_SUBTITLE, font=FONTS["subtitle"], text_color=COLORS["cyan"] ).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(text_col, text=APP_DESCRIPTION, font=FONTS["body"], text_color=COLORS["muted"], justify="left", wraplength=620).pack(anchor="w", pady=(10, 0))

        tag_row = ctk.CTkFrame(header, fg_color="transparent")
        tag_row.grid(row=1, column=1, sticky="w", padx=(0, 18), pady=(0, 18))

        tag_colors = [COLORS["violet"], COLORS["cyan"], COLORS["success"], COLORS["pink"]]
        for tag, color in zip(APP_TAGS, tag_colors):
            ctk.CTkLabel(tag_row, text=tag, font=FONTS["tag"], text_color=COLORS["text"], fg_color=color, corner_radius=999, padx=12, pady=4).pack(side="left", padx=(0, 8))

    def _build_ui(self):
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=24, pady=24)

        self._build_header(main_container)

        self.db_selector = DBSelector(["SQL Server (SSMS)", "MySQL"], self._on_db_changed)
        self.db_selector.render(main_container, fill="x", pady=(0, 14))

        db_env = os.getenv("DB_TYPE", "SQLSERVER").upper()
        if db_env == "MYSQL":
            self.db_selector.selected_value.set("MySQL")
            self.current_db_type = "MySQL"
        else:
            self.db_selector.selected_value.set("SQL Server (SSMS)")
            self.current_db_type = "SQL Server (SSMS)"

        self.info_panel = InfoPanel()
        self.info_panel.render(main_container, fill="x", pady=(0, 14))

        options_frame = ctk.CTkFrame(main_container, fg_color=COLORS["surface"], corner_radius=18, border_width=1, border_color=COLORS["border"])
        options_frame.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(options_frame, text="Opcoes de Runtime", font=FONTS["section"], text_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(options_frame, text="Controle aplicado apenas durante a geracao dos models.", font=FONTS["body_small"], text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(0, 10))
        ctk.CTkCheckBox(options_frame, text="Exigir RECID BIGINT no Model Update", variable=self.require_recid_var, onvalue=True, offvalue=False, font=FONTS["body"], text_color=COLORS["text"], fg_color=COLORS["violet"], hover_color=COLORS["violet_hover"], border_color=COLORS["checkbox_border"], checkmark_color=COLORS["text"]).pack(anchor="w", padx=18, pady=(0, 16))

        self.dashboard = MetadataDashboard()
        self.dashboard.render(main_container, fill="both", expand=True, pady=(0, 14))

        buttons_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(8, 0))

        self.btn_test = ActionButton("Testar Conexão", self._run_test_connection)
        self.btn_test.render(buttons_frame, side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_modelupdate = Button_modelupdate("Atualizar Modelos", self._run_model_update)
        self.btn_modelupdate.render(buttons_frame, side="right", fill="x", expand=True, padx=(6, 0))
        self.btn_modelupdate.set_state("disabled")

        self._refresh_metadata()

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

    def _on_db_changed(self, selected_db: str):
        self.current_db_type = selected_db
        self._refresh_metadata()

    def _set_model_update_state(self, state: str):
        if self.btn_modelupdate is not None:
            self.btn_modelupdate.set_state(state)

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
            self._set_model_update_state("normal")
            messagebox.showinfo("Sucesso", "Conexão estabelecida com sucesso e dados obtidos!")

        except Exception as e:
            error_msg = str(e)
            if "cryptography" in error_msg and "auth" in error_msg:
                error_msg += "\n\n[DICA DO SQLMANAGER]: O MySQL 8+ exige um pacote extra de segurança para a senha.\nAbra o seu terminal e instale rodando:\npip install cryptography"
                
            messagebox.showerror("Erro de Conexão", f"Falha ao conectar no banco de dados:\n\n{error_msg}")
            self._set_model_update_state("disabled")
            
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
                    self._set_model_update_state("normal")
                except Exception:
                    tables = tables if tables is not None else []
                    views = views if views is not None else []
                    self._set_model_update_state("disabled")
            else:
                tables = tables if tables is not None else []
                views = views if views is not None else []
                self._set_model_update_state("disabled")

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

    teste = dialog(APP_TITLE)
    teste.start()
