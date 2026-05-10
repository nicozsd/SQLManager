"""
SQLManager -- Gerenciador de Modelos
Interface para configurar, analisar e executar o build do modelo de dados.
"""
import os
import sys
import threading
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from PIL import Image as PILImage, ImageDraw as PILDraw

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "Gerenciador de Modelos -- SQLManager"

THEME = {
    "bg":        "#080C14",
    "panel":     "#0D1424",
    "surface":   "#151F33",
    "surface2":  "#1C2A44",
    "input":     "#0B1322",
    "border":    "#24324D",
    "text":      "#F4F8FF",
    "muted":     "#7C8FAB",
    "dim":       "#3A4E66",
    "cyan":      "#00E5FF",
    "violet":    "#7C3AED",
    "violet_h":  "#6D28D9",
    "green":     "#10B981",
    "green_h":   "#059669",
    "orange":    "#F59E0B",
    "danger":    "#F43F5E",
    "danger_h":  "#E11D48",
}

# ---------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
model_dir   = os.path.dirname(current_dir)
package_dir = os.path.dirname(model_dir)
root_dir    = os.path.dirname(package_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if load_dotenv is not None:
    load_dotenv(os.path.join(os.getcwd(), ".env"))
    load_dotenv(os.path.join(root_dir, ".env"))


# ===========================================================================
# Linha clicavel sem checkbox
# ===========================================================================

class ClickableRow(ctk.CTkFrame):
    """Linha de item selecionavel sem icones de checkbox."""

    def __init__(self, master, text: str, var: tk.BooleanVar, on_change, **kw):
        super().__init__(master, fg_color="transparent", cursor="hand2", **kw)
        self._var = var
        self._on_change = on_change

        self._bar = ctk.CTkFrame(self, width=3, corner_radius=2)
        self._bar.pack(side="left", fill="y", padx=(4, 8), pady=2)

        self._lbl = ctk.CTkLabel(
            self, text=text, anchor="w",
            font=ctk.CTkFont("Segoe UI", 12),
        )
        self._lbl.pack(side="left", fill="x", expand=True, pady=2)

        self._update()
        for w in (self, self._lbl, self._bar):
            w.bind("<Button-1>", self._click)

    def _click(self, _e=None):
        self._var.set(not self._var.get())
        self._update()
        self._on_change()

    def _update(self):
        if self._var.get():
            self.configure(fg_color=THEME["surface2"])
            self._bar.configure(fg_color=THEME["violet"])
            self._lbl.configure(text_color=THEME["text"])
        else:
            self.configure(fg_color="transparent")
            self._bar.configure(fg_color=THEME["dim"])
            self._lbl.configure(text_color=THEME["muted"])


# ===========================================================================
# Secao retratil
# ===========================================================================

class CollapsibleSection(ctk.CTkFrame):

    def __init__(self, master, title: str, selectable: bool = True, **kw):
        super().__init__(master, fg_color=THEME["panel"], corner_radius=14, **kw)
        self.title      = title
        self.selectable = selectable
        self._items:    list = []
        self._vars:     dict = {}
        self._widgets:  dict = {}
        self._expanded  = False
        self._body      = None
        self._scroll    = None
        self._search_var: tk.StringVar | None = None
        self._filter:   str = ""

        self._header = ctk.CTkButton(
            self,
            text=self._header_text(),
            fg_color=THEME["surface"],
            hover_color=THEME["surface2"],
            text_color=THEME["text"],
            anchor="w",
            corner_radius=12,
            font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
            command=self._toggle,
        )
        self._header.pack(fill="x", padx=4, pady=4)

    def _header_text(self) -> str:
        n = len(self._items)
        arrow = "  [-]" if self._expanded else "  [+]"
        if self.selectable:
            sel = sum(1 for v in self._vars.values() if v.get())
            return f"   {self.title}      {sel} / {n} selecionados{arrow}"
        return f"   {self.title}      {n} registros{arrow}"

    def _refresh_header(self, *_):
        self._header.configure(text=self._header_text())

    def _toggle(self):
        self._expanded = not self._expanded
        self._refresh_header()
        if self._expanded:
            self._show_body()
        else:
            self._hide_body()

    def expand(self):
        if not self._expanded:
            self._toggle()

    def collapse(self):
        if self._expanded:
            self._toggle()

    def _show_body(self):
        if self._body is None:
            self._build_body()
        self._body.pack(fill="both", expand=True, padx=4, pady=(0, 6))

    def _hide_body(self):
        if self._body is not None:
            self._body.pack_forget()

    def _build_body(self):
        self._body = ctk.CTkFrame(self, fg_color=THEME["input"], corner_radius=10)

        if self.selectable:
            tb = ctk.CTkFrame(self._body, fg_color="transparent")
            tb.pack(fill="x", padx=10, pady=(8, 4))
            ctk.CTkButton(
                tb, text="Selecionar Tudo", width=120, height=24,
                fg_color=THEME["violet"], hover_color=THEME["violet_h"],
                font=ctk.CTkFont("Segoe UI", 12), corner_radius=7,
                command=self.select_all,
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                tb, text="Limpar", width=70, height=24,
                fg_color=THEME["border"], hover_color=THEME["surface"],
                text_color=THEME["text"],
                font=ctk.CTkFont("Segoe UI", 12), corner_radius=7,
                command=self.clear_selection,
            ).pack(side="left")

            self._search_var = tk.StringVar()
            self._search_var.trace_add("write", self._on_search)
            ctk.CTkEntry(
                self._body,
                textvariable=self._search_var,
                placeholder_text="Pesquisar...",
                fg_color=THEME["input"], border_color=THEME["border"],
                text_color=THEME["text"],
                placeholder_text_color=THEME["dim"],
                font=ctk.CTkFont("Segoe UI", 12),
                corner_radius=8, height=30,
            ).pack(fill="x", padx=10, pady=(0, 4))

        self._scroll = ctk.CTkScrollableFrame(
            self._body, height=160, fg_color="transparent",
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["surface"],
        )
        self._scroll.pack(fill="both", expand=True, padx=6, pady=(4, 6))
        self._populate_scroll()

    def _on_search(self, *_):
        self._filter = (self._search_var.get() if self._search_var else "").lower()
        self._populate_scroll()

    def _populate_scroll(self):
        for w in self._widgets.values():
            w.destroy()
        self._widgets.clear()

        visible = [
            item for item in self._items
            if not self._filter or self._filter in item.lower()
        ]

        for item in visible:
            if self.selectable:
                var = self._vars.setdefault(item, tk.BooleanVar(value=True))
                row = ClickableRow(
                    self._scroll, item, var,
                    on_change=self._refresh_header,
                )
                row.pack(fill="x", pady=1)
            else:
                row = ctk.CTkFrame(self._scroll, fg_color="transparent")
                row.pack(fill="x", pady=0)
                ctk.CTkLabel(
                    row, text=f"   {item}", anchor="w",
                    text_color=THEME["muted"],
                    font=ctk.CTkFont("Segoe UI", 12),
                ).pack(fill="x")
            self._widgets[item] = row

    def set_items(self, items):
        previous = {k for k, v in self._vars.items() if v.get()}
        self._items = list(items or [])
        for k in list(self._vars.keys()):
            if k not in self._items:
                del self._vars[k]
        for item in self._items:
            if item not in self._vars and self.selectable:
                default = (item in previous) if previous else True
                self._vars[item] = tk.BooleanVar(value=default)
        if self._body is not None and self._expanded:
            self._populate_scroll()
        self._refresh_header()

    def get_selected_items(self) -> list:
        if not self.selectable:
            return list(self._items)
        return [i for i in self._items if self._vars.get(i) and self._vars[i].get()]

    def select_all(self):
        for v in self._vars.values():
            v.set(True)
        for w in self._widgets.values():
            if isinstance(w, ClickableRow):
                w._update()
        self._refresh_header()

    def clear_selection(self):
        for v in self._vars.values():
            v.set(False)
        for w in self._widgets.values():
            if isinstance(w, ClickableRow):
                w._update()
        self._refresh_header()


# ===========================================================================
# Janela principal
# ===========================================================================

class dialog(ctk.CTk):
    _POLL_MS = 80

    def __init__(self, title: str):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1260x800")
        self.minsize(980, 640)
        self.configure(fg_color=THEME["bg"])

        self.assets_dir = Path(__file__).resolve().parent / "assets"

        self.remote_metadata_loaded = False
        self.pending_action  = None
        self.confirm_message = None
        self.confirm_result  = False
        self._confirm_win    = None

        self._build_ui()
        self._refresh_local_lists()
        self._update_remote_lists([], [])
        self._set_build_enabled(False)
        self._set_analyze_enabled(False)

    # ------------------------------------------------------------------
    # Construcao
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._build_header()
        self._build_action_pane()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(8, 0))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)
        self._build_status_bar()

    # -- Banner --

    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color=THEME["panel"], corner_radius=0, height=104)
        frame.pack(fill="x")
        frame.pack_propagate(False)

        self._fallback_title(frame)

        ctk.CTkFrame(frame, fg_color=THEME["cyan"], height=2, corner_radius=0).pack(
            side="bottom", fill="x", padx=40
        )

    def _fallback_title(self, parent):
        ctk.CTkLabel(
            parent, text=APP_TITLE,
            font=ctk.CTkFont("Segoe UI", 22, weight="bold"),
            text_color=THEME["text"],
        ).place(relx=0.5, rely=0.5, anchor="center")

    # -- ActionPane (estilo AX2012: icone esquerda + texto direita) --

    def _build_action_pane(self):
        pane = ctk.CTkFrame(self, fg_color=THEME["panel"], corner_radius=0, height=54)
        pane.pack(fill="x")
        pane.pack_propagate(False)

        ctk.CTkFrame(pane, fg_color=THEME["border"], height=1, corner_radius=0).pack(
            fill="x", side="bottom"
        )

        inner = ctk.CTkFrame(pane, fg_color="transparent")
        inner.pack(side="left", fill="y", padx=6)

        ico_cancel  = self._make_icon("x",      THEME["danger"], 16)
        ico_test    = self._make_icon("plug",    THEME["green"],  16)
        ico_analyze = self._make_icon("lens",    THEME["cyan"],   16)
        ico_build   = self._make_icon("arrow",   THEME["violet"], 16)

        btn_cfg = dict(
            fg_color="transparent",
            hover_color=THEME["surface2"],
            text_color=THEME["text"],
            font=ctk.CTkFont("Segoe UI", 13),
            corner_radius=8,
            height=46,
            anchor="w",
            compound="left",
        )

        self.btn_cancel = ctk.CTkButton(
            inner, text="  Cancelar", image=ico_cancel, width=124,
            command=self.destroy, **btn_cfg,
        )
        self.btn_cancel.pack(side="left", padx=2)

        self._pane_sep(inner)

        self.btn_test = ctk.CTkButton(
            inner, text="  Testar Conexao", image=ico_test, width=150,
            command=self._request_test_connection, **btn_cfg,
        )
        self.btn_test.pack(side="left", padx=2)

        self.btn_analyze = ctk.CTkButton(
            inner, text="  Analisar", image=ico_analyze, width=116,
            command=self._request_analyze,
            state="disabled", **btn_cfg,
        )
        self.btn_analyze.pack(side="left", padx=2)

        self._pane_sep(inner)

        self.btn_build = ctk.CTkButton(
            inner, text="  Executar Build", image=ico_build, width=150,
            command=self._request_build,
            state="disabled",
            font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
            fg_color="transparent",
            hover_color=THEME["surface2"],
            text_color=THEME["text"],
            corner_radius=8, height=46, anchor="w", compound="left",
        )
        self.btn_build.pack(side="left", padx=2)

    @staticmethod
    def _pane_sep(parent):
        ctk.CTkFrame(parent, fg_color=THEME["border"], width=1,
                     corner_radius=0).pack(
            side="left", fill="y", padx=8, pady=10
        )

    @staticmethod
    def _make_icon(shape: str, color: str, size: int = 16) -> ctk.CTkImage:
        img  = PILImage.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = PILDraw.Draw(img)
        h    = color.lstrip("#")
        c    = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
        p    = 2

        if shape == "x":
            draw.line([(p, p), (size - p, size - p)], fill=c, width=2)
            draw.line([(size - p, p), (p, size - p)], fill=c, width=2)

        elif shape == "plug":
            mid = size // 2
            r   = size // 4
            draw.ellipse([p, mid - r, p + r * 2, mid + r], outline=c, width=2)
            draw.ellipse([size - p - r * 2, mid - r, size - p, mid + r],
                         outline=c, width=2)
            draw.line([(p + r * 2, mid), (size - p - r * 2, mid)], fill=c, width=2)

        elif shape == "lens":
            r  = size // 2 - p - 2
            cx = r + p + 1
            cy = r + p + 1
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=2)
            lx = int(cx + r * 0.68)
            ly = int(cy + r * 0.68)
            draw.line([(lx, ly), (size - p, size - p)], fill=c, width=2)

        elif shape == "arrow":
            pts = [(p + 1, p), (p + 1, size - p), (size - p, size // 2)]
            draw.polygon(pts, fill=c)

        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    # -- Painel esquerdo --

    def _build_left_panel(self, body):
        outer = ctk.CTkScrollableFrame(
            body, width=336,
            fg_color=THEME["panel"], corner_radius=16,
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["surface"],
        )
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=4)

        self._cat(outer, "BANCO DE DADOS")
        db_init = "MySQL" if os.getenv("DB_TYPE", "SQLSERVER").upper() == "MYSQL" else "SQL Server (SSMS)"
        self.var_db = tk.StringVar(value=db_init)
        ctk.CTkSegmentedButton(
            outer,
            values=["SQL Server (SSMS)", "MySQL"],
            variable=self.var_db,
            fg_color=THEME["surface"],
            selected_color=THEME["violet"],
            selected_hover_color=THEME["violet_h"],
            unselected_color=THEME["surface"],
            unselected_hover_color=THEME["surface2"],
            text_color=THEME["text"],
            font=ctk.CTkFont("Segoe UI", 12),
            corner_radius=9,
            command=self._on_db_changed,
        ).pack(fill="x", padx=12, pady=(0, 14))

        self._cat(outer, "CREDENCIAIS DE ACESSO")
        self.e_server   = self._entry(outer, "Servidor / Host",  os.getenv("DB_SERVER",   ""))
        self.e_database = self._entry(outer, "Banco de Dados",   os.getenv("DB_DATABASE", ""))
        self.e_user     = self._entry(outer, "Usuario",          os.getenv("DB_USER",     ""))
        self.e_password = self._entry(outer, "Senha",            os.getenv("DB_PASSWORD", ""), show="*")

        self._cat(outer, "RUNTIME")
        self.var_recid = tk.BooleanVar(value=self._env_bool("SQLMANAGER_REQUIRE_RECID", True))
        ctk.CTkSwitch(
            outer,
            text="Exigir RECID BIGINT nos modelos",
            variable=self.var_recid,
            font=ctk.CTkFont("Segoe UI", 13),
            text_color=THEME["text"],
            progress_color=THEME["violet"],
            button_color=THEME["text"],
            button_hover_color="#CBD5E1",
        ).pack(fill="x", padx=12, pady=(0, 16))

    def _cat(self, parent, text: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(14, 4))
        ctk.CTkLabel(
            row, text=text, anchor="w",
            font=ctk.CTkFont("Segoe UI", 11, weight="bold"),
            text_color=THEME["dim"],
        ).pack(side="left")
        ctk.CTkFrame(row, fg_color=THEME["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=6
        )

    def _entry(self, parent, label: str, value: str = "", show: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent, text=label, anchor="w",
            font=ctk.CTkFont("Segoe UI", 12), text_color=THEME["muted"],
        ).pack(fill="x", padx=12, pady=(0, 2))
        e = ctk.CTkEntry(
            parent,
            fg_color=THEME["input"], border_color=THEME["border"],
            text_color=THEME["text"],
            font=ctk.CTkFont("Segoe UI", 13),
            show=show, corner_radius=9, height=36,
        )
        e.pack(fill="x", padx=12, pady=(0, 8))
        if value:
            e.insert(0, value)
        return e

    # -- Painel direito --

    def _build_right_panel(self, body):
        scroll = ctk.CTkScrollableFrame(
            body, fg_color="transparent",
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["surface"],
        )
        scroll.grid(row=0, column=1, sticky="nsew", pady=4)

        self.sec_tables = CollapsibleSection(scroll, "Tabelas",     selectable=True)
        self.sec_tables.pack(fill="x", padx=4, pady=(0, 8))

        self.sec_views  = CollapsibleSection(scroll, "Views",       selectable=True)
        self.sec_views.pack(fill="x", padx=4, pady=(0, 8))

        self.sec_edts   = CollapsibleSection(scroll, "EDTs",        selectable=False)
        self.sec_edts.pack(fill="x", padx=4, pady=(0, 8))

        self.sec_enums  = CollapsibleSection(scroll, "Enumeracoes", selectable=False)
        self.sec_enums.pack(fill="x", padx=4)

    # -- Barra de status --

    def _build_status_bar(self):
        bar = ctk.CTkFrame(self, fg_color=THEME["panel"], corner_radius=0, height=34)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        ctk.CTkFrame(bar, fg_color=THEME["border"], height=1, corner_radius=0).pack(
            fill="x", side="top"
        )
        self.lbl_status = ctk.CTkLabel(
            bar,
            text="Pronto -- configure a conexao e teste antes de iniciar.",
            anchor="w",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=THEME["dim"],
        )
        self.lbl_status.pack(side="left", padx=16, fill="x", expand=True)

    # ------------------------------------------------------------------
    # Utilitarios
    # ------------------------------------------------------------------

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        v = os.getenv(name)
        if v is None:
            return default
        return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

    def _model_folder(self, child: str) -> Path:
        p = Path.cwd() / "src" / "model" / child
        return p if p.exists() else Path(root_dir) / "src" / "model" / child

    def _local_files(self, folder: Path) -> list:
        if not folder.exists():
            return []
        return sorted(
            [f.stem for f in folder.iterdir()
             if f.suffix == ".py" and not f.name.startswith("__")],
            key=str.lower,
        )

    def _refresh_local_lists(self):
        self.sec_edts.set_items(self._local_files(self._model_folder("EDTs")))
        self.sec_enums.set_items(self._local_files(self._model_folder("enum")))

    def _update_remote_lists(self, tables, views):
        self.sec_tables.set_items(tables)
        self.sec_views.set_items(views)

    def _set_build_enabled(self, enabled: bool):
        self.btn_build.configure(state="normal" if enabled else "disabled")

    def _set_analyze_enabled(self, enabled: bool):
        self.btn_analyze.configure(state="normal" if enabled else "disabled")

    def _set_status(self, msg: str, error: bool = False):
        self.lbl_status.configure(
            text=msg,
            text_color=THEME["danger"] if error else THEME["muted"],
        )

    def _entry_val(self, e: ctk.CTkEntry) -> str:
        return e.get().strip()

    def _can_query(self) -> bool:
        return all(
            self._entry_val(e)
            for e in (self.e_server, self.e_database, self.e_user, self.e_password)
        )

    def _apply_credentials(self):
        from SQLManager import CoreConfig

        db = "MYSQL" if self.var_db.get() == "MySQL" else "SQLSERVER"
        os.environ["DB_TYPE"]                  = db
        os.environ["DB_SERVER"]                = self._entry_val(self.e_server)
        os.environ["DB_DATABASE"]              = self._entry_val(self.e_database)
        os.environ["DB_USER"]                  = self._entry_val(self.e_user)
        os.environ["DB_PASSWORD"]              = self._entry_val(self.e_password)
        os.environ["SQLMANAGER_REQUIRE_RECID"] = "true" if self.var_recid.get() else "false"
        CoreConfig.configure(load_from_env=True)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _on_db_changed(self, _value):
        self.remote_metadata_loaded = False
        self._update_remote_lists([], [])
        self._set_build_enabled(False)
        self._set_analyze_enabled(False)

    # ------------------------------------------------------------------
    # Acoes
    # ------------------------------------------------------------------

    def _request_test_connection(self):
        if not self._can_query():
            self._set_status(
                "Preencha servidor, banco, usuario e senha antes de testar.", error=True
            )
            return
        self._set_status("Estabelecendo conexao com o banco de dados...")
        self.btn_test.configure(state="disabled")
        self._set_build_enabled(False)
        self._set_analyze_enabled(False)

        def worker():
            try:
                from SQLManager.connection import database_connection
                from SQLManager._model._model_update import ModelUpdaterBase

                self._apply_credentials()
                base = ModelUpdaterBase()
                db   = database_connection()
                db.connect()
                try:
                    tables = [r[0] for r in db.doQuery(base.get_model_tables_query())]
                    views  = [r[0] for r in db.doQuery(base.get_model_views_query())]
                finally:
                    db.disconnect()
                self.pending_action = ("connection_success", tables, views)
            except Exception as exc:
                self.pending_action = ("connection_error", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _request_build(self):
        if not self.remote_metadata_loaded:
            self._set_status("Teste a conexao antes de executar o build.", error=True)
            return
        self._start_build()

    def _start_build(self):
        self._set_status("Gerando modelos -- aguarde...")
        self._set_build_enabled(False)
        self.btn_test.configure(state="disabled")
        self._set_analyze_enabled(False)

        def confirm_callback(message):
            self.pending_action = ("confirm_from_worker", message)
            while self.confirm_message is not None:
                import time
                time.sleep(0.05)
            return self.confirm_result

        def worker():
            try:
                from SQLManager._model._model_update import ModelUpdater

                self._apply_credentials()
                ModelUpdater().run(
                    selected_tables=self.sec_tables.get_selected_items(),
                    selected_views=self.sec_views.get_selected_items(),
                    confirm_callback=confirm_callback,
                )
                self.pending_action = ("build_success",)
            except Exception as exc:
                self.pending_action = ("build_error", str(exc))

        self.confirm_result = False
        threading.Thread(target=worker, daemon=True).start()

    def _request_analyze(self):
        if not self.remote_metadata_loaded:
            self._set_status("Teste a conexao antes de analisar.", error=True)
            return

        db_tables    = set(self.sec_tables._items)
        db_views     = set(self.sec_views._items)
        local_tables = set(self._local_files(self._model_folder("tables")))
        local_views  = set(self._local_files(self._model_folder("views")))

        result = {
            "tables": {
                "novos":  sorted(db_tables - local_tables),
                "modelo": sorted(db_tables & local_tables),
                "orfaos": sorted(local_tables - db_tables),
            },
            "views": {
                "novos":  sorted(db_views - local_views),
                "modelo": sorted(db_views & local_views),
                "orfaos": sorted(local_views - db_views),
            },
        }
        self._show_analysis(result)

    def _show_analysis(self, result: dict):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Analise de Impacto")
        dlg.geometry("1020x640")
        dlg.minsize(820, 500)
        dlg.configure(fg_color=THEME["bg"])
        dlg.grab_set()
        dlg.focus_set()

        # Faixa de acento
        ctk.CTkFrame(dlg, fg_color=THEME["cyan"], height=3, corner_radius=0).pack(fill="x")

        # Titulo
        hdr = ctk.CTkFrame(dlg, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(14, 6))
        ctk.CTkLabel(
            hdr, text="Analise de Impacto",
            font=ctk.CTkFont("Segoe UI", 18, weight="bold"),
            text_color=THEME["text"],
        ).pack(side="left")
        ctk.CTkLabel(
            hdr,
            text="  Compare o banco de dados com os arquivos de modelo ja gerados",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=THEME["muted"],
        ).pack(side="left", pady=4)

        ctk.CTkFrame(dlg, fg_color=THEME["border"], height=1, corner_radius=0).pack(
            fill="x", padx=24
        )

        scroll = ctk.CTkScrollableFrame(
            dlg, fg_color="transparent",
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["surface"],
        )
        scroll.pack(fill="both", expand=True, padx=16, pady=8)

        self._analysis_section(
            scroll, "TABELAS",
            result["tables"],
            len(self.sec_tables._items),
        )
        ctk.CTkFrame(scroll, fg_color=THEME["border"], height=1).pack(
            fill="x", pady=14
        )
        self._analysis_section(
            scroll, "VIEWS",
            result["views"],
            len(self.sec_views._items),
        )

        ctk.CTkButton(
            dlg, text="Fechar", width=120, height=36,
            fg_color=THEME["surface"], hover_color=THEME["border"],
            text_color=THEME["text"], font=ctk.CTkFont("Segoe UI", 13),
            corner_radius=9, command=dlg.destroy,
        ).pack(pady=(4, 14))

    def _analysis_section(self, parent, title: str, data: dict, db_count: int):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=(6, 8))
        ctk.CTkLabel(
            top, text=title,
            font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
            text_color=THEME["dim"],
        ).pack(side="left")
        ctk.CTkLabel(
            top,
            text=f"   {db_count} no banco de dados",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=THEME["muted"],
        ).pack(side="left")

        cols = ctk.CTkFrame(parent, fg_color="transparent")
        cols.pack(fill="x")
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.columnconfigure(2, weight=1)

        specs = [
            ("Novos no Banco",   data["novos"],  THEME["green"],
             "Serao criados no modelo"),
            ("Ja no Modelo",     data["modelo"], THEME["cyan"],
             "Serao regenerados"),
            ("Apenas Local",     data["orfaos"], THEME["orange"],
             "Nao estao mais no banco"),
        ]
        for col, (label, items, color, hint) in enumerate(specs):
            px = (0, 0) if col == 0 else (6, 0)
            panel = ctk.CTkFrame(cols, fg_color=THEME["panel"], corner_radius=12)
            panel.grid(row=0, column=col, sticky="nsew", padx=px)

            ctk.CTkFrame(panel, fg_color=color, height=3, corner_radius=0).pack(fill="x")

            ctk.CTkLabel(
                panel,
                text=f"{label}   ({len(items)})",
                font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
                text_color=color, anchor="w",
            ).pack(anchor="w", padx=12, pady=(8, 1))
            ctk.CTkLabel(
                panel, text=hint,
                font=ctk.CTkFont("Segoe UI", 11),
                text_color=THEME["dim"], anchor="w",
            ).pack(anchor="w", padx=12, pady=(0, 6))

            sf = ctk.CTkScrollableFrame(
                panel, height=130, fg_color="transparent",
                scrollbar_button_color=THEME["border"],
                scrollbar_button_hover_color=THEME["surface"],
            )
            sf.pack(fill="both", expand=True, padx=6, pady=(0, 8))

            if not items:
                ctk.CTkLabel(
                    sf, text="Nenhum", anchor="w",
                    text_color=THEME["dim"],
                    font=ctk.CTkFont("Segoe UI", 12),
                ).pack(anchor="w", padx=8, pady=6)
            else:
                for item in items:
                    ctk.CTkLabel(
                        sf, text=item, anchor="w",
                        text_color=THEME["muted"],
                        font=ctk.CTkFont("Segoe UI", 12),
                    ).pack(fill="x", padx=8, pady=1)

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def _poll(self):
        if self.pending_action is not None:
            action = self.pending_action
            self.pending_action = None
            self._dispatch(action)
        try:
            self.after(self._POLL_MS, self._poll)
        except Exception:
            pass

    def _dispatch(self, action):
        kind = action[0]

        if kind == "connection_success":
            _, tables, views = action
            self.remote_metadata_loaded = True
            self._update_remote_lists(tables, views)
            self.sec_tables.expand()
            self.sec_views.expand()
            self._set_status(
                f"Conexao estabelecida -- {len(tables)} tabelas e {len(views)} views encontradas."
            )
            self.btn_test.configure(state="normal")
            self._set_build_enabled(True)
            self._set_analyze_enabled(True)

        elif kind == "connection_error":
            _, error = action
            self.remote_metadata_loaded = False
            self._update_remote_lists([], [])
            self._set_status(f"Falha na conexao: {error}", error=True)
            self.btn_test.configure(state="normal")
            self._set_build_enabled(False)
            self._set_analyze_enabled(False)

        elif kind == "confirm_from_worker":
            _, message = action
            self.confirm_message = message
            self._show_confirm(message)

        elif kind == "build_success":
            self._set_status("Build concluido com sucesso.")
            self.btn_test.configure(state="normal")
            self._set_build_enabled(True)
            self._set_analyze_enabled(True)
            self._refresh_local_lists()
            self.sec_edts.expand()
            self.sec_enums.expand()

        elif kind == "build_error":
            _, error = action
            self._set_status(f"Falha no build: {error}", error=True)
            self.btn_test.configure(state="normal")
            self._set_build_enabled(self.remote_metadata_loaded)
            self._set_analyze_enabled(self.remote_metadata_loaded)

    # ------------------------------------------------------------------
    # Modal de confirmacao
    # ------------------------------------------------------------------

    def _show_confirm(self, message: str):
        if self._confirm_win and self._confirm_win.winfo_exists():
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Confirmacao")
        dlg.geometry("500x250")
        dlg.resizable(False, False)
        dlg.configure(fg_color=THEME["panel"])
        dlg.grab_set()
        dlg.focus_set()
        self._confirm_win = dlg

        ctk.CTkFrame(dlg, fg_color=THEME["violet"], height=4, corner_radius=0).pack(fill="x")

        ctk.CTkLabel(
            dlg, text="Confirmacao necessaria",
            font=ctk.CTkFont("Segoe UI", 16, weight="bold"),
            text_color=THEME["text"],
        ).pack(pady=(16, 6), padx=24, anchor="w")

        ctk.CTkLabel(
            dlg, text=message, wraplength=460, justify="left",
            font=ctk.CTkFont("Segoe UI", 13), text_color=THEME["muted"],
        ).pack(padx=24, pady=(0, 18), anchor="w")

        row = ctk.CTkFrame(dlg, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(0, 20))

        def _yes():
            self.confirm_result  = True
            self.confirm_message = None
            dlg.destroy()

        def _no():
            self.confirm_result  = False
            self.confirm_message = None
            dlg.destroy()

        ctk.CTkButton(
            row, text="Confirmar",
            fg_color=THEME["violet"], hover_color=THEME["violet_h"],
            width=170, height=40, corner_radius=9,
            font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
            command=_yes,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            row, text="Cancelar",
            fg_color=THEME["danger"], hover_color=THEME["danger_h"],
            width=170, height=40, corner_radius=9,
            font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
            command=_no,
        ).pack(side="right", expand=True, fill="x", padx=(6, 0))

    # ------------------------------------------------------------------
    # Entrada publica
    # ------------------------------------------------------------------

    def start(self):
        self._poll()
        self.mainloop()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    d = dialog(APP_TITLE)
    d.start()
