"""
SQLManager -- Gerenciador de Modelos
Interface grafica para configurar e executar o build inicial do modelo de dados.
"""
import os
import sys
import threading
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from PIL import Image as PILImage

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ---------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "Gerenciador de Modelos -- SQLManager"

THEME = {
    "bg":          "#080C14",
    "panel":       "#0D1424",
    "surface":     "#151F33",
    "input":       "#0B1322",
    "border":      "#24324D",
    "text":        "#F4F8FF",
    "muted":       "#7C8FAB",
    "dim":         "#4A5E7A",
    "cyan":        "#00E5FF",
    "violet":      "#7C3AED",
    "violet_h":    "#6D28D9",
    "green":       "#10B981",
    "green_h":     "#059669",
    "danger":      "#F43F5E",
    "danger_h":    "#E11D48",
}

# ---------------------------------------------------------------------------
# Resolucao de paths
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
# Secao retratil (acordeao)
# ===========================================================================

class CollapsibleSection(ctk.CTkFrame):
    """
    Painel retratil com cabecalho clicavel e lista scrollavel de itens.
    Para secoes selecionaveis, cada item possui uma caixa de selecao.
    Para secoes somente-leitura, os itens sao exibidos como rotulos.
    """

    def __init__(self, master, title: str, selectable: bool = True, **kw):
        super().__init__(master, fg_color=THEME["panel"], corner_radius=16, **kw)
        self.title      = title
        self.selectable = selectable
        self._items:   list  = []
        self._vars:    dict  = {}   # item -> tk.BooleanVar  (apenas selecionaveis)
        self._widgets: dict  = {}   # item -> widget de linha
        self._expanded = False
        self._scroll   = None
        self._body     = None

        # Cabecalho (botao que abre/fecha a secao)
        self._header = ctk.CTkButton(
            self,
            text=self._header_text(),
            fg_color=THEME["surface"],
            hover_color=THEME["border"],
            text_color=THEME["text"],
            anchor="w",
            corner_radius=14,
            font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
            command=self._toggle,
        )
        self._header.pack(fill="x", padx=4, pady=4)

    # ------------------------------------------------------------------

    def _header_text(self) -> str:
        n     = len(self._items)
        arrow = "[-]" if self._expanded else "[+]"
        if self.selectable:
            sel = sum(1 for v in self._vars.values() if v.get())
            return f"   {self.title}      {sel} de {n} selecionados   {arrow}"
        return f"   {self.title}      {n} registros   {arrow}"

    def _refresh_header(self, *_):
        self._header.configure(text=self._header_text())

    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------

    def _show_body(self):
        if self._body is None:
            self._build_body()
        self._body.pack(fill="both", expand=True, padx=4, pady=(0, 6))

    def _hide_body(self):
        if self._body is not None:
            self._body.pack_forget()

    def _build_body(self):
        self._body = ctk.CTkFrame(self, fg_color=THEME["input"], corner_radius=12)

        if self.selectable:
            toolbar = ctk.CTkFrame(self._body, fg_color="transparent")
            toolbar.pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkButton(
                toolbar, text="Selecionar Tudo", width=130, height=26,
                fg_color=THEME["violet"], hover_color=THEME["violet_h"],
                font=ctk.CTkFont("Segoe UI", 12), corner_radius=8,
                command=self.select_all,
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                toolbar, text="Limpar", width=80, height=26,
                fg_color=THEME["border"], hover_color=THEME["surface"],
                text_color=THEME["text"],
                font=ctk.CTkFont("Segoe UI", 12), corner_radius=8,
                command=self.clear_selection,
            ).pack(side="left")

        self._scroll = ctk.CTkScrollableFrame(
            self._body, height=170, fg_color="transparent",
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["surface"],
        )
        self._scroll.pack(fill="both", expand=True, padx=6, pady=(4, 6))
        self._populate_scroll()

    def _populate_scroll(self):
        for w in self._widgets.values():
            w.destroy()
        self._widgets.clear()

        for item in self._items:
            row = ctk.CTkFrame(self._scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)

            if self.selectable:
                var = self._vars.setdefault(item, tk.BooleanVar(value=True))
                cb = ctk.CTkCheckBox(
                    row, text=item, variable=var,
                    text_color=THEME["text"],
                    checkmark_color=THEME["text"],
                    fg_color=THEME["violet"],
                    border_color=THEME["border"],
                    hover_color=THEME["surface"],
                    font=ctk.CTkFont("Segoe UI", 13),
                    command=self._refresh_header,
                )
                cb.pack(anchor="w", padx=8)
            else:
                lbl = ctk.CTkLabel(
                    row, text=f"  {item}", anchor="w",
                    text_color=THEME["muted"],
                    font=ctk.CTkFont("Segoe UI", 13),
                )
                lbl.pack(fill="x", padx=8)
            self._widgets[item] = row

    # ------------------------------------------------------------------

    def set_items(self, items):
        previous = {k for k, v in self._vars.items() if v.get()}
        self._items = list(items or [])

        # Remove vars de itens que saíram
        for k in list(self._vars.keys()):
            if k not in self._items:
                del self._vars[k]

        # Cria vars para novos itens
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
        self._refresh_header()

    def clear_selection(self):
        for v in self._vars.values():
            v.set(False)
        self._refresh_header()


# ===========================================================================
# Janela principal
# ===========================================================================

class dialog(ctk.CTk):
    """
    Janela principal do Gerenciador de Modelos.
    Interface: dialog(title).start()
    """

    _POLL_MS = 80

    def __init__(self, title: str):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1240x780")
        self.minsize(960, 620)
        self.configure(fg_color=THEME["bg"])

        self.assets_dir = Path(__file__).resolve().parent / "assets"

        # Estado assincrono
        self.remote_metadata_loaded = False
        self.pending_action         = None
        self.confirm_message        = None
        self.confirm_result         = False
        self._confirm_win           = None

        self._build_ui()
        self._refresh_local_lists()
        self._update_remote_lists([], [])
        self._set_build_enabled(False)

    # ------------------------------------------------------------------
    # Construcao da interface
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._build_header()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 0))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)
        self._build_footer()

    # -- Header --

    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color=THEME["panel"], corner_radius=0, height=108)
        frame.pack(fill="x")
        frame.pack_propagate(False)

        banner = self.assets_dir / "banner.png"
        if banner.exists():
            try:
                pil = PILImage.open(str(banner))
                pil.thumbnail((960, 92), PILImage.LANCZOS)
                self._banner = ctk.CTkImage(pil, size=(pil.width, pil.height))
                ctk.CTkLabel(frame, image=self._banner, text="").place(
                    relx=0.5, rely=0.5, anchor="center"
                )
            except Exception:
                self._banner = None
                self._fallback_title(frame)
        else:
            self._banner = None
            self._fallback_title(frame)

        # Linha de acento inferior
        ctk.CTkFrame(frame, fg_color=THEME["cyan"], height=3, corner_radius=0).pack(
            side="bottom", fill="x", padx=48
        )

    def _fallback_title(self, parent):
        ctk.CTkLabel(
            parent,
            text=APP_TITLE,
            font=ctk.CTkFont("Segoe UI", 22, weight="bold"),
            text_color=THEME["text"],
        ).place(relx=0.5, rely=0.5, anchor="center")

    # -- Painel esquerdo --

    def _build_left_panel(self, body):
        outer = ctk.CTkScrollableFrame(
            body,
            width=340,
            fg_color=THEME["panel"],
            corner_radius=18,
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["surface"],
        )
        outer.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=12)

        # Banco de dados
        self._cat(outer, "BANCO DE DADOS")
        db_init = "MySQL" if os.getenv("DB_TYPE", "SQLSERVER").upper() == "MYSQL" else "SQL Server (SSMS)"
        self.var_db = tk.StringVar(value=db_init)
        seg = ctk.CTkSegmentedButton(
            outer,
            values=["SQL Server (SSMS)", "MySQL"],
            variable=self.var_db,
            fg_color=THEME["surface"],
            selected_color=THEME["violet"],
            selected_hover_color=THEME["violet_h"],
            unselected_color=THEME["surface"],
            unselected_hover_color=THEME["border"],
            text_color=THEME["text"],
            font=ctk.CTkFont("Segoe UI", 13),
            corner_radius=10,
            command=self._on_db_changed,
        )
        seg.pack(fill="x", padx=12, pady=(0, 14))

        # Credenciais
        self._cat(outer, "CREDENCIAIS DE ACESSO")
        self.e_server   = self._entry(outer, "Servidor / Host",  os.getenv("DB_SERVER",   ""))
        self.e_database = self._entry(outer, "Banco de Dados",   os.getenv("DB_DATABASE", ""))
        self.e_user     = self._entry(outer, "Usuario",          os.getenv("DB_USER",     ""))
        self.e_password = self._entry(outer, "Senha",            os.getenv("DB_PASSWORD", ""), show="*")

        # Runtime
        self._cat(outer, "OPCOES DE RUNTIME")
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
        """Rotulo de categoria em maiusculas com linha separadora."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(14, 4))
        ctk.CTkLabel(
            row,
            text=text,
            anchor="w",
            font=ctk.CTkFont("Segoe UI", 11, weight="bold"),
            text_color=THEME["dim"],
        ).pack(side="left")
        ctk.CTkFrame(row, fg_color=THEME["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=6
        )

    def _entry(self, parent, label: str, value: str = "", show: str = "") -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent, text=label, anchor="w",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=THEME["muted"],
        ).pack(fill="x", padx=12, pady=(0, 2))
        e = ctk.CTkEntry(
            parent,
            fg_color=THEME["input"],
            border_color=THEME["border"],
            text_color=THEME["text"],
            font=ctk.CTkFont("Segoe UI", 13),
            show=show,
            corner_radius=9,
            height=38,
        )
        e.pack(fill="x", padx=12, pady=(0, 8))
        if value:
            e.insert(0, value)
        return e

    # -- Painel direito --

    def _build_right_panel(self, body):
        scroll = ctk.CTkScrollableFrame(
            body,
            fg_color="transparent",
            scrollbar_button_color=THEME["border"],
            scrollbar_button_hover_color=THEME["surface"],
        )
        scroll.grid(row=0, column=1, sticky="nsew", pady=12)

        self.sec_tables = CollapsibleSection(scroll, "Tabelas",      selectable=True)
        self.sec_tables.pack(fill="x", padx=4, pady=(0, 8))

        self.sec_views  = CollapsibleSection(scroll, "Views",        selectable=True)
        self.sec_views.pack(fill="x", padx=4, pady=(0, 8))

        self.sec_edts   = CollapsibleSection(scroll, "EDTs",         selectable=False)
        self.sec_edts.pack(fill="x", padx=4, pady=(0, 8))

        self.sec_enums  = CollapsibleSection(scroll, "Enumeracoes",  selectable=False)
        self.sec_enums.pack(fill="x", padx=4)

    # -- Footer --

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=THEME["panel"], corner_radius=0, height=80)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        # Linha de topo
        ctk.CTkFrame(footer, fg_color=THEME["border"], height=1, corner_radius=0).pack(
            fill="x", side="top"
        )

        self.lbl_status = ctk.CTkLabel(
            footer,
            text="Pronto -- configure a conexao e teste antes de iniciar.",
            anchor="w",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=THEME["dim"],
        )
        self.lbl_status.pack(side="left", padx=20, fill="x", expand=True)

        self.btn_build = ctk.CTkButton(
            footer, text="Executar Build",
            fg_color=THEME["violet"], hover_color=THEME["violet_h"],
            text_color=THEME["text"], font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
            corner_radius=12, width=180, height=48,
            command=self._request_build,
        )
        self.btn_build.pack(side="right", padx=(6, 20), pady=16)

        self.btn_test = ctk.CTkButton(
            footer, text="Testar Conexao",
            fg_color=THEME["green"], hover_color=THEME["green_h"],
            text_color=THEME["text"], font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
            corner_radius=12, width=180, height=48,
            command=self._request_test_connection,
        )
        self.btn_test.pack(side="right", padx=6, pady=16)

        self.btn_cancel = ctk.CTkButton(
            footer, text="Cancelar",
            fg_color=THEME["danger"], hover_color=THEME["danger_h"],
            text_color=THEME["text"], font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
            corner_radius=12, width=140, height=48,
            command=self.destroy,
        )
        self.btn_cancel.pack(side="right", padx=6, pady=16)

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

    def _set_status(self, msg: str, error: bool = False):
        color = THEME["danger"] if error else THEME["muted"]
        self.lbl_status.configure(text=msg, text_color=color)

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
        os.environ["DB_TYPE"]               = db
        os.environ["DB_SERVER"]             = self._entry_val(self.e_server)
        os.environ["DB_DATABASE"]           = self._entry_val(self.e_database)
        os.environ["DB_USER"]               = self._entry_val(self.e_user)
        os.environ["DB_PASSWORD"]           = self._entry_val(self.e_password)
        os.environ["SQLMANAGER_REQUIRE_RECID"] = "true" if self.var_recid.get() else "false"
        CoreConfig.configure(load_from_env=True)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _on_db_changed(self, _value):
        self.remote_metadata_loaded = False
        self._update_remote_lists([], [])
        self._set_build_enabled(False)

    # ------------------------------------------------------------------
    # Acoes principais
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
            self._set_status("Teste a conexao com o banco antes de executar o build.", error=True)
            return
        self._start_build()

    def _start_build(self):
        self._set_status("Gerando modelos -- aguarde...")
        self._set_build_enabled(False)
        self.btn_test.configure(state="disabled")

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

    # ------------------------------------------------------------------
    # Polling de acoes assincronas (thread-safe via after)
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
            # Expandir automaticamente apos carregar dados remotos
            self.sec_tables.expand()
            self.sec_views.expand()
            self._set_status(
                f"Conexao estabelecida -- {len(tables)} tabelas e {len(views)} views encontradas."
            )
            self.btn_test.configure(state="normal")
            self._set_build_enabled(True)

        elif kind == "connection_error":
            _, error = action
            self.remote_metadata_loaded = False
            self._update_remote_lists([], [])
            self._set_status(f"Falha na conexao: {error}", error=True)
            self.btn_test.configure(state="normal")
            self._set_build_enabled(False)

        elif kind == "confirm_from_worker":
            _, message = action
            self.confirm_message = message
            self._show_confirm(message)

        elif kind == "build_success":
            self._set_status("Build concluido com sucesso.")
            self.btn_test.configure(state="normal")
            self._set_build_enabled(True)
            self._refresh_local_lists()
            self.sec_edts.expand()
            self.sec_enums.expand()

        elif kind == "build_error":
            _, error = action
            self._set_status(f"Falha no build: {error}", error=True)
            self.btn_test.configure(state="normal")
            self._set_build_enabled(self.remote_metadata_loaded)

    # ------------------------------------------------------------------
    # Dialog de confirmacao
    # ------------------------------------------------------------------

    def _show_confirm(self, message: str):
        if self._confirm_win and self._confirm_win.winfo_exists():
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("Confirmacao")
        dlg.geometry("500x260")
        dlg.resizable(False, False)
        dlg.configure(fg_color=THEME["panel"])
        dlg.grab_set()
        dlg.focus_set()
        self._confirm_win = dlg

        # Faixa de acento no topo
        ctk.CTkFrame(dlg, fg_color=THEME["violet"], height=4, corner_radius=0).pack(
            fill="x"
        )

        ctk.CTkLabel(
            dlg,
            text="Confirmacao necessaria",
            font=ctk.CTkFont("Segoe UI", 17, weight="bold"),
            text_color=THEME["text"],
        ).pack(pady=(18, 6), padx=24, anchor="w")

        ctk.CTkLabel(
            dlg,
            text=message,
            wraplength=460,
            justify="left",
            font=ctk.CTkFont("Segoe UI", 13),
            text_color=THEME["muted"],
        ).pack(padx=24, pady=(0, 20), anchor="w")

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 24))

        def _confirm():
            self.confirm_result  = True
            self.confirm_message = None
            dlg.destroy()

        def _deny():
            self.confirm_result  = False
            self.confirm_message = None
            dlg.destroy()

        ctk.CTkButton(
            btn_row, text="Confirmar",
            fg_color=THEME["violet"], hover_color=THEME["violet_h"],
            width=170, height=44, corner_radius=10,
            font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
            command=_confirm,
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Cancelar",
            fg_color=THEME["danger"], hover_color=THEME["danger_h"],
            width=170, height=44, corner_radius=10,
            font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
            command=_deny,
        ).pack(side="right", expand=True, fill="x", padx=(6, 0))

    # ------------------------------------------------------------------
    # Interface publica
    # ------------------------------------------------------------------

    def start(self):
        self._poll()
        self.mainloop()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    d = dialog(APP_TITLE)
    d.start()
