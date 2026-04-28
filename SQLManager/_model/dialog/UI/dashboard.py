import tkinter as tk
from tkinter import ttk
from .mixins import ComponentMixin

class MetadataDashboard(ComponentMixin):
    def __init__(self):
        super().__init__()
        self.metrics = {}

    def _build(self, parent: tk.Widget) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text=" Metadados do Banco ", padding=15)
        
        # Grid config para expandir igualmente
        for i in range(2):
            frame.columnconfigure(i, weight=1)

        self._create_metric(frame, "Tabelas", 0, 0)
        self._create_metric(frame, "Views", 0, 1)
        self._create_metric(frame, "EDTs", 1, 0)
        self._create_metric(frame, "Enums", 1, 1)
        
        return frame

    def _create_metric(self, parent: tk.Widget, name: str, row: int, col: int):
        container = ttk.Frame(parent)
        container.grid(row=row, column=col, sticky=tk.NSEW, pady=10)
        
        ttk.Label(container, text=name.upper(), font=("Segoe UI", 9, "bold"), foreground="#888").pack()
        
        val_label = ttk.Label(container, text="-", font=("Segoe UI", 18, "bold"), foreground="#0078D7")
        val_label.pack()
        
        self.metrics[name.lower()] = val_label

    def update_data(self, tables: int, views: int, edts: int, enums: int):
        if not self.widget: return
        self.metrics["tabelas"].config(text=str(tables))
        self.metrics["views"].config(text=str(views))
        self.metrics["edts"].config(text=str(edts))
        self.metrics["enums"].config(text=str(enums))