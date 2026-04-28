import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

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

from UI.db_selector import DBSelector
from UI.info_panel import InfoPanel
from UI.action_button import ActionButton
from UI.dashboard import MetadataDashboard
from UI.button_modelupdate import Button_modelupdate

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
        
        window_width = 450
        window_height = 640
        center_x = int((self.root.winfo_screenwidth() - window_width) / 2)
        center_y = int((self.root.winfo_screenheight() - window_height) / 2)
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.resizable(False, False)
        
        self._apply_theme()
        
        self.current_db_type = None
        
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
        self.dashboard.render(main_container, fill=tk.BOTH, expand=True, pady=(0, 20))

        # 4. Botões de Ação
        buttons_frame = ttk.Frame(main_container)
        buttons_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        self.btn_test = ActionButton("Testar Conexão", self._run_test_connection)
        self.btn_test.render(buttons_frame, side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.btn_modelupdate = Button_modelupdate("Atualizar Modelos", self._run_model_update)
        self.btn_modelupdate.render(buttons_frame, side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        self.btn_modelupdate.set_state(tk.DISABLED) # Começa desabilitado

    def _on_db_changed(self, selected_db: str):
        self.current_db_type = selected_db

    def _run_test_connection(self):
        self.btn_test.set_loading(True)
        self.root.update_idletasks() # Força update visual
        
        try:
            from SQLManager import CoreConfig
            from SQLManager.connection import database_connection

            # 1. Aplica as credenciais da UI apenas para a sessão atual
            self._apply_ui_credentials()

            # 2. Conexão Real
            db = database_connection()
            db.connect()

            # 3. Conta Tabelas e Views reais no banco (Padrão ANSI suportado por SQLServer e MySQL)
            q_tables = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
            q_views = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS"
            
            tables_count = db.doQuery(q_tables)[0][0]
            views_count = db.doQuery(q_views)[0][0]

            db.disconnect()

            # 4. Conta EDTs e Enums já existentes localmente
            edts_count = self._count_local_files(os.path.join(root_dir, "src", "model", "EDTs"))
            enums_count = self._count_local_files(os.path.join(root_dir, "src", "model", "enum"))

            # 5. Atualiza a Dashboard e libera a próxima etapa
            self.dashboard.update_data(tables=tables_count, views=views_count, edts=edts_count, enums=enums_count)
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

        CoreConfig.configure(load_from_env=True)

    def _count_local_files(self, folder_path: str) -> int:
        """Conta quantos arquivos python existem em uma pasta (ignorando __init__)."""
        count = 0
        if os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith(".py") and not file.startswith("__"):
                    count += 1
        return count

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
            updater.run()
            
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