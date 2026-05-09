import tkinter as tk
from typing import List, Callable
import customtkinter as ctk
from .mixins import ComponentMixin
from .theme import COLORS, FONTS

class DBSelector(ComponentMixin):
    def __init__(self, options: List[str], on_select_callback: Callable[[str], None]):
        super().__init__()
        self.options = options
        self.on_select = on_select_callback
        self.selected_value = tk.StringVar()

    def _build(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"], corner_radius=18, border_width=1, border_color=COLORS["border"])
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=1)

        label = ctk.CTkLabel(
            frame,
            text="Banco",
            font=FONTS["section"],
            text_color=COLORS["text"],
        )
        label.grid(row=0, column=0, sticky="w", padx=(18, 14), pady=16)

        combo = ctk.CTkOptionMenu(
            frame,
            values=self.options,
            variable=self.selected_value,
            command=self.on_select,
            font=FONTS["body"],
            dropdown_font=FONTS["body"],
            fg_color=COLORS["input"],
            button_color=COLORS["violet"],
            button_hover_color=COLORS["violet_hover"],
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["panel_alt"],
            dropdown_text_color=COLORS["text"],
            dropdown_hover_color=COLORS["surface_hover"],
            corner_radius=12,
            height=40,
        )
        combo.grid(row=0, column=1, sticky="ew", padx=(0, 18), pady=12)

        if self.options:
            self.selected_value.set(self.options[0])
        return frame