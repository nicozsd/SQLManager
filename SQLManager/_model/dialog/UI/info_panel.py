import os
import tkinter as tk
from tkinter import ttk
from .mixins import ComponentMixin

class InfoPanel(ComponentMixin):
    def __init__(self):
        super().__init__()
        self.server_var = tk.StringVar()
        self.database_var = tk.StringVar()
        self.user_var = tk.StringVar()
        self.password_var = tk.StringVar()

    def _build(self, parent: tk.Widget) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text=" Credenciais de Conexão (.env) ", padding=15)
        
        # Extração em tempo de execução (Runtime apenas)
        self.server_var.set(os.getenv('DB_SERVER', ''))
        self.database_var.set(os.getenv('DB_DATABASE', ''))
        self.user_var.set(os.getenv('DB_USER', ''))
        self.password_var.set(os.getenv('DB_PASSWORD', ''))
        
        # Componentes
        self._add_entry_row(frame, "Servidor (Host):", self.server_var, 0)
        self._add_entry_row(frame, "Banco (Database):", self.database_var, 1)
        self._add_entry_row(frame, "Usuário (User):", self.user_var, 2)
        self._add_entry_row(frame, "Senha (Password):", self.password_var, 3, is_password=True)
        
        return frame

    def _add_entry_row(self, parent: tk.Widget, label_text: str, text_var: tk.StringVar, row: int, is_password: bool = False):
        font_base = ("Segoe UI", 10)
        ttk.Label(parent, text=label_text, font=font_base, foreground="#555").grid(row=row, column=0, sticky=tk.W, pady=4, padx=(0, 10))
        entry = ttk.Entry(parent, textvariable=text_var, font=font_base, width=25)
        if is_password:
            entry.config(show="*")
        entry.grid(row=row, column=1, sticky=tk.W, pady=4)