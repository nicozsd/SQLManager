import tkinter as tk
from tkinter import ttk
from .mixins import ComponentMixin


class _MetadataListSection:
    def __init__(self, title: str, selectable: bool = False):
        self.title = title
        self.selectable = selectable
        self.frame = None
        self.count_label = None
        self.canvas = None
        self.canvas_window = None
        self.body = None
        self.variables = {}
        self.items = []

    def build(self, parent: tk.Widget, row: int, col: int):
        self.frame = ttk.LabelFrame(parent, text=f" {self.title} ", padding=10)
        self.frame.grid(row=row, column=col, sticky=tk.NSEW, padx=6, pady=6)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        header = ttk.Frame(self.frame)
        header.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        header.columnconfigure(0, weight=1)

        self.count_label = ttk.Label(header, text="0", font=("Segoe UI", 12, "bold"), foreground="#0078D7")
        self.count_label.grid(row=0, column=0, sticky=tk.W)

        if self.selectable:
            actions = ttk.Frame(header)
            actions.grid(row=0, column=1, sticky=tk.E)
            ttk.Button(actions, text="Marcar tudo", command=self.select_all, width=12).pack(side=tk.LEFT, padx=(0, 4))
            ttk.Button(actions, text="Desmarcar", command=self.clear_selection, width=12).pack(side=tk.LEFT)

        list_container = ttk.Frame(self.frame)
        list_container.grid(row=1, column=0, sticky=tk.NSEW)
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(list_container, height=180, highlightthickness=0, bg="#FFFFFF")
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.body = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.body, anchor=tk.NW)
        self.body.bind("<Configure>", self._sync_scroll_region)
        self.canvas.bind("<Configure>", self._resize_body)

    def _sync_scroll_region(self, _event=None):
        if self.canvas is not None:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_body(self, event):
        if self.canvas is None or self.canvas_window is None:
            return
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def set_items(self, items, selected_items=None):
        if self.body is None:
            return

        previous_selected = set(self.get_selected_items()) if self.selectable else set()

        for child in self.body.winfo_children():
            child.destroy()

        normalized_items = [str(item) for item in (items or [])]
        self.items = normalized_items
        self.variables = {}
        self.count_label.config(text=str(len(normalized_items)))

        if not normalized_items:
            ttk.Label(self.body, text="Sem dados", foreground="#777777").pack(anchor=tk.W, padx=4, pady=4)
            self._sync_scroll_region()
            return

        if self.selectable:
            if selected_items is not None:
                selected_set = set(selected_items)
            elif previous_selected:
                selected_set = previous_selected.intersection(normalized_items)
            else:
                selected_set = set(normalized_items)

            for item in normalized_items:
                variable = tk.BooleanVar(value=item in selected_set)
                ttk.Checkbutton(self.body, text=item, variable=variable).pack(anchor=tk.W, fill=tk.X, padx=4, pady=1)
                self.variables[item] = variable
        else:
            for item in normalized_items:
                ttk.Label(self.body, text=item).pack(anchor=tk.W, fill=tk.X, padx=4, pady=1)

        self._sync_scroll_region()

    def get_selected_items(self):
        if not self.selectable:
            return list(self.items)
        return [item for item, variable in self.variables.items() if variable.get()]

    def select_all(self):
        for variable in self.variables.values():
            variable.set(True)

    def clear_selection(self):
        for variable in self.variables.values():
            variable.set(False)


class MetadataDashboard(ComponentMixin):
    def __init__(self):
        super().__init__()
        self.sections = {}

    def _build(self, parent: tk.Widget) -> tk.Widget:
        frame = ttk.LabelFrame(parent, text=" Metadados do Banco ", padding=12)

        for col in range(2):
            frame.columnconfigure(col, weight=1)
        for row in range(2):
            frame.rowconfigure(row, weight=1)

        self.sections = {
            "tables": _MetadataListSection("Tabelas", selectable=True),
            "views": _MetadataListSection("Views", selectable=True),
            "edts": _MetadataListSection("EDTs"),
            "enums": _MetadataListSection("Enums"),
        }

        self.sections["tables"].build(frame, 0, 0)
        self.sections["views"].build(frame, 0, 1)
        self.sections["edts"].build(frame, 1, 0)
        self.sections["enums"].build(frame, 1, 1)

        return frame

    def update_data(self, tables=None, views=None, edts=None, enums=None):
        if not self.widget:
            return
        if tables is not None:
            self.sections["tables"].set_items(tables)
        if views is not None:
            self.sections["views"].set_items(views)
        if edts is not None:
            self.sections["edts"].set_items(edts)
        if enums is not None:
            self.sections["enums"].set_items(enums)

    def get_selected_tables(self):
        return self.sections["tables"].get_selected_items()

    def get_selected_views(self):
        return self.sections["views"].get_selected_items()
