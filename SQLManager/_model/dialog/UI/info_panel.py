import os
import tkinter as tk
import customtkinter as ctk
from .mixins import ComponentMixin
from .theme import COLORS, FONTS

class InfoPanel(ComponentMixin):
    def __init__(self):
        super().__init__()
        self.server_var = tk.StringVar()
        self.database_var = tk.StringVar()
        self.user_var = tk.StringVar()
        self.password_var = tk.StringVar()

    def _build(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"], corner_radius=18, border_width=1, border_color=COLORS["border"])
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=1)
        
        self.server_var.set(os.getenv('DB_SERVER', ''))
        self.database_var.set(os.getenv('DB_DATABASE', ''))
        self.user_var.set(os.getenv('DB_USER', ''))
        self.password_var.set(os.getenv('DB_PASSWORD', ''))

        header = ctk.CTkLabel(
            frame,
            text="Credenciais de Conexao",
            font=FONTS["section"],
            text_color=COLORS["text"],
        )
        header.grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 4))

        subtitle = ctk.CTkLabel(
            frame,
            text="Valores usados apenas em runtime para o Model Update.",
            font=FONTS["body_small"],
            text_color=COLORS["muted"],
        )
        subtitle.grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 10))

        self._add_entry_row(frame, "Servidor (Host):", self.server_var, 0)
        self._add_entry_row(frame, "Banco (Database):", self.database_var, 1)
        self._add_entry_row(frame, "Usuário (User):", self.user_var, 2)
        self._add_entry_row(frame, "Senha (Password):", self.password_var, 3, is_password=True)

        return frame

    def _add_entry_row(self, parent, label_text: str, text_var: tk.StringVar, row: int, is_password: bool = False):
        grid_row = row + 2
        label = ctk.CTkLabel(parent, text=label_text, font=FONTS["body"], text_color=COLORS["muted"])
        label.grid(row=grid_row, column=0, sticky="w", padx=(18, 12), pady=8)

        entry = ctk.CTkEntry(
            parent,
            textvariable=text_var,
            font=FONTS["body"],
            fg_color=COLORS["input"],
            border_color=COLORS["input_border"],
            text_color=COLORS["text"],
            corner_radius=12,
            height=38,
        )
        if is_password:
            entry.configure(show="*")
        entry.grid(row=grid_row, column=1, sticky="ew", padx=(0, 18), pady=8)