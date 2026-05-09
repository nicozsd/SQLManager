from typing import Callable
import customtkinter as ctk
from .mixins import ComponentMixin
from .theme import COLORS, FONTS

class ActionButton(ComponentMixin):
    def __init__(self, text: str, command: Callable):
        super().__init__()
        self.text = text
        self.command = command

    def _build(self, parent):
        btn = ctk.CTkButton(
            parent,
            text=self.text,
            command=self.command,
            font=FONTS["button"],
            fg_color=COLORS["panel_alt"],
            hover_color=COLORS["surface_hover"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=14,
            height=42,
        )
        return btn
        
    def set_loading(self, is_loading: bool, text: str = "Processando..."):
        if not self.widget: return
        if is_loading:
            self.widget.configure(text=text, state="disabled")
        else:
            self.widget.configure(text=self.text, state="normal")