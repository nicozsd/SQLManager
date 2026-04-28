import tkinter as tk
from tkinter import ttk
from typing import List, Callable
from .mixins import ComponentMixin

class DBSelector(ComponentMixin):
    def __init__(self, options: List[str], on_select_callback: Callable[[str], None]):
        super().__init__()
        self.options = options
        self.on_select = on_select_callback
        self.selected_value = tk.StringVar()

    def _build(self, parent: tk.Widget) -> tk.Widget:
        frame = ttk.Frame(parent)
        ttk.Label(frame, text="Selecione o Banco:", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 10))
        
        cb = ttk.Combobox(frame, textvariable=self.selected_value, values=self.options, state="readonly", font=("Segoe UI", 10))
        cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        cb.bind("<<ComboboxSelected>>", lambda e: self.on_select(self.selected_value.get()))
        
        if self.options:
            cb.current(0)
        return frame