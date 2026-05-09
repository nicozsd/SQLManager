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
        self.items = []
        self.empty_label = None

    def build(self, parent, row: int, col: int):
        self.frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"], corner_radius=14, border_width=1, border_color=COLORS["border"])
        self.frame.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.columnconfigure(0, weight=1)

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(title_col, text=self.title, font=FONTS["section"], text_color=COLORS["text"]).pack(anchor="w")
        self.count_label = ctk.CTkLabel(title_col, text="0 itens", font=FONTS["body_small"], text_color=COLORS["cyan"])
        self.count_label.pack(anchor="w")

        if self.selectable:
            actions = ctk.CTkFrame(header, fg_color="transparent")
            actions.grid(row=0, column=1, sticky="e")
            ctk.CTkButton(actions, text="Marcar", command=self.select_all, width=72, height=26, font=FONTS["body_small"], fg_color=COLORS["panel_alt"], hover_color=COLORS["surface_hover"], border_width=1, border_color=COLORS["border"]).pack(side="left", padx=(0, 6))
            ctk.CTkButton(actions, text="Limpar", command=self.clear_selection, width=72, height=26, font=FONTS["body_small"], fg_color=COLORS["panel_alt"], hover_color=COLORS["surface_hover"], border_width=1, border_color=COLORS["border"]).pack(side="left")

        list_wrapper = ctk.CTkFrame(self.frame, fg_color=COLORS["input"], corner_radius=12, border_width=1, border_color=COLORS["input_border"])
        list_wrapper.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        list_wrapper.grid_columnconfigure(0, weight=1)
        list_wrapper.grid_rowconfigure(0, weight=1)

        select_mode = tk.EXTENDED if self.selectable else tk.BROWSE
        self.body = tk.Listbox(
            list_wrapper,
            selectmode=select_mode,
            exportselection=False,
            activestyle="none",
            relief=tk.FLAT,
            bg=COLORS["input"],
            fg=COLORS["text"],
            selectbackground=COLORS["list_select_bg"],
            selectforeground=COLORS["list_select_fg"],
            highlightthickness=0,
            borderwidth=0,
            font=FONTS["body"],
        )
        scrollbar = tk.Scrollbar(list_wrapper, orient=tk.VERTICAL, command=self.body.yview, borderwidth=0, highlightthickness=0)
        self.body.configure(yscrollcommand=scrollbar.set)

        self.body.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8)

        self.empty_label = ctk.CTkLabel(list_wrapper, text="Sem dados", font=FONTS["body_small"], text_color=COLORS["muted"])

    def set_items(self, items, selected_items=None):
        if self.body is None:
            return

        previous_selected = set(self.get_selected_items()) if self.selectable else set()

        normalized_items = [str(item) for item in (items or [])]
        self.items = normalized_items
        suffix = "item" if len(normalized_items) == 1 else "itens"
        self.count_label.configure(text=f"{len(normalized_items)} {suffix}")

        self.body.delete(0, tk.END)

        if not normalized_items:
            if self.empty_label is not None:
                self.empty_label.grid(row=0, column=0)
            return

        if self.empty_label is not None:
            self.empty_label.grid_forget()

        for item in normalized_items:
            self.body.insert(tk.END, item)

        if self.selectable:
            if selected_items is not None:
                selected_set = set(selected_items)
            elif previous_selected:
                selected_set = previous_selected.intersection(normalized_items)
            else:
                selected_set = set(normalized_items)

            for index, item in enumerate(normalized_items):
                if item in selected_set:
                    self.body.selection_set(index)
        else:
            self.body.configure(state=tk.NORMAL)
            if normalized_items:
                self.body.selection_clear(0, tk.END)
            self.body.configure(state=tk.DISABLED)

    def get_selected_items(self):
        if not self.selectable:
            return list(self.items)
        return [self.items[index] for index in self.body.curselection()]

    def select_all(self):
        self.body.selection_set(0, tk.END)

    def clear_selection(self):
        self.body.selection_clear(0, tk.END)


class MetadataDashboard(ComponentMixin):
    def __init__(self):
        super().__init__()
        self.sections = {}

    def _build(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")

        for col in range(2):
            frame.columnconfigure(col, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

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
