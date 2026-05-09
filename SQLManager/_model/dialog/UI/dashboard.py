import tkinter as tk
import customtkinter as ctk
from .mixins import ComponentMixin
from .theme import COLORS, FONTS


class _MetadataListSection:
    def __init__(self, title: str, selectable: bool = False):
        self.title = title
        self.selectable = selectable
        self.frame = None
        self.count_label = None
        self.body = None
        self.variables = {}
        self.items = []

    def build(self, parent, row: int, col: int):
        self.frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"], corner_radius=18, border_width=1, border_color=COLORS["border"])
        self.frame.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        header.columnconfigure(0, weight=1)

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(title_col, text=self.title, font=FONTS["section"], text_color=COLORS["text"]).pack(anchor="w")
        self.count_label = ctk.CTkLabel(title_col, text="0 itens", font=FONTS["body_small"], text_color=COLORS["cyan"])
        self.count_label.pack(anchor="w")

        if self.selectable:
            actions = ctk.CTkFrame(header, fg_color="transparent")
            actions.grid(row=0, column=1, sticky="e")
            ctk.CTkButton(actions, text="Marcar tudo", command=self.select_all, width=96, height=30, font=FONTS["body_small"], fg_color=COLORS["panel_alt"], hover_color=COLORS["surface_hover"], border_width=1, border_color=COLORS["border"]).pack(side="left", padx=(0, 6))
            ctk.CTkButton(actions, text="Desmarcar", command=self.clear_selection, width=96, height=30, font=FONTS["body_small"], fg_color=COLORS["panel_alt"], hover_color=COLORS["surface_hover"], border_width=1, border_color=COLORS["border"]).pack(side="left")

        self.body = ctk.CTkScrollableFrame(
            self.frame,
            fg_color=COLORS["input"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["input_border"],
            height=215,
            label_text="",
        )
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))

    def set_items(self, items, selected_items=None):
        if self.body is None:
            return

        previous_selected = set(self.get_selected_items()) if self.selectable else set()

        for child in self.body.winfo_children():
            child.destroy()

        normalized_items = [str(item) for item in (items or [])]
        self.items = normalized_items
        self.variables = {}
        suffix = "item" if len(normalized_items) == 1 else "itens"
        self.count_label.configure(text=f"{len(normalized_items)} {suffix}")

        if not normalized_items:
            ctk.CTkLabel(self.body, text="Sem dados", font=FONTS["body_small"], text_color=COLORS["muted"]).pack(anchor="w", padx=8, pady=8)
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
                ctk.CTkCheckBox(
                    self.body,
                    text=item,
                    variable=variable,
                    onvalue=True,
                    offvalue=False,
                    font=FONTS["body"],
                    text_color=COLORS["text"],
                    fg_color=COLORS["violet"],
                    hover_color=COLORS["violet_hover"],
                    border_color=COLORS["checkbox_border"],
                    checkmark_color=COLORS["text"],
                ).pack(anchor="w", fill="x", padx=8, pady=3)
                self.variables[item] = variable
        else:
            for item in normalized_items:
                ctk.CTkLabel(self.body, text=item, font=FONTS["body"], text_color=COLORS["text"], anchor="w").pack(anchor="w", fill="x", padx=8, pady=3)

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

    def _build(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")

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
