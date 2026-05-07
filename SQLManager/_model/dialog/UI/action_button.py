import tkinter as tk
from tkinter import ttk
from typing import Callable
from .mixins import ComponentMixin

class ActionButton(ComponentMixin):
    def __init__(self, text: str, command: Callable):
        super().__init__()
        self.text = text
        self.command = command

    def _build(self, parent: tk.Widget) -> tk.Widget:
        btn = ttk.Button(parent, text=self.text, command=self.command, cursor="hand2")
        return btn
        
    def set_loading(self, is_loading: bool, text: str = "Processando..."):
        if not self.widget: return
        if is_loading:
            self.widget.config(text=text, state=tk.DISABLED)
        else:
            self.widget.config(text=self.text, state=tk.NORMAL)