import os
import sys
import threading
from pathlib import Path

import pygame

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ---------------------------------------------------------------------------
# Identidade da aplicacao
# ---------------------------------------------------------------------------
APP_TITLE = "Gerenciador de Modelos — SQLManager"
APP_DESCRIPTION = (
    "Configure a conexao com o banco de dados, selecione os objetos desejados "
    "e gere os arquivos de modelo com controle total sobre o processo."
)

# ---------------------------------------------------------------------------
# Paleta de cores
# ---------------------------------------------------------------------------
COLORS = {
    "bg":           (8,   12,  20),
    "panel":        (13,  20,  36),
    "panel_alt":    (16,  26,  45),
    "surface":      (21,  31,  51),
    "surface_hover":(28,  42,  66),
    "input":        (11,  19,  34),
    "border":       (36,  50,  77),
    "text":         (244, 248, 255),
    "muted":        (124, 143, 171),
    "cyan":         (0,   229, 255),
    "violet":       (124, 58,  237),
    "green":        (16,  185, 129),
    "pink":         (236, 72,  153),
    "warning":      (245, 158, 11),
    "danger":       (244, 63,  94),
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
# Componentes de UI
# ===========================================================================

class Button:
    def __init__(self, label, action, color, accent=None):
        self.label  = label
        self.action = action
        self.color  = color
        self.accent = accent or color
        self.rect   = pygame.Rect(0, 0, 0, 0)
        self.enabled = True

    def draw(self, surface, font, mouse_pos):
        bg = self.color if self.enabled else COLORS["border"]
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        if hovered:
            bg = tuple(min(255, c + 22) for c in bg)

        shadow = self.rect.move(0, 3).inflate(-6, -4)
        shadow_surf = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 60))
        surface.blit(shadow_surf, shadow.topleft)

        pygame.draw.rect(surface, bg, self.rect, border_radius=14)
        pygame.draw.rect(surface,
                         self.accent if hovered else COLORS["border"],
                         self.rect, width=1, border_radius=14)
        text = font.render(self.label, True,
                           COLORS["text"] if self.enabled else COLORS["muted"])
        surface.blit(text, text.get_rect(center=self.rect.center))

    def handle_click(self, event):
        return (
            self.enabled
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


class Toggle:
    def __init__(self, label, value=False):
        self.label = label
        self.value = value
        self.rect  = pygame.Rect(0, 0, 0, 0)

    def draw(self, surface, font):
        box = pygame.Rect(self.rect.x, self.rect.y + 2, 20, 20)
        bg  = COLORS["violet"] if self.value else COLORS["input"]
        pygame.draw.rect(surface, bg, box, border_radius=6)
        pygame.draw.rect(surface,
                         COLORS["violet"] if self.value else COLORS["border"],
                         box, width=2, border_radius=6)
        if self.value:
            pygame.draw.line(surface, COLORS["text"], (box.x + 4, box.y + 10), (box.x + 8,  box.y + 14), 2)
            pygame.draw.line(surface, COLORS["text"], (box.x + 8, box.y + 14), (box.x + 16, box.y + 5),  2)
        text = font.render(self.label, True, COLORS["text"])
        surface.blit(text, (self.rect.x + 30, self.rect.y + 2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.value = not self.value
            return True
        return False


class TextInput:
    def __init__(self, label, value="", password=False):
        self.label    = label
        self.value    = value
        self.password = password
        self.rect     = pygame.Rect(0, 0, 0, 0)
        self.active   = False

    def draw(self, surface, label_font, input_font):
        lbl = label_font.render(self.label, True, COLORS["muted"])
        surface.blit(lbl, (self.rect.x, self.rect.y - 16))
        pygame.draw.rect(surface, COLORS["input"], self.rect, border_radius=10)
        border = COLORS["cyan"] if self.active else COLORS["border"]
        pygame.draw.rect(surface, border, self.rect,
                         width=2 if self.active else 1, border_radius=10)
        display = self.value if not self.password else chr(8226) * len(self.value)
        ts = input_font.render(display, True, COLORS["text"])
        surface.blit(ts, (self.rect.x + 12, self.rect.y + (self.rect.height - ts.get_height()) // 2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key == pygame.K_RETURN:
                return True
            elif event.unicode and event.unicode.isprintable():
                self.value += event.unicode
        return False


class Selector:
    def __init__(self, label, options, current):
        self.label   = label
        self.options = options
        self.index   = options.index(current) if current in options else 0
        self.rect    = pygame.Rect(0, 0, 0, 0)

    @property
    def value(self):
        return self.options[self.index]

    def draw(self, surface, label_font, value_font):
        lbl = label_font.render(self.label, True, COLORS["muted"])
        surface.blit(lbl, (self.rect.x, self.rect.y - 16))
        pygame.draw.rect(surface, COLORS["input"], self.rect, border_radius=10)
        pygame.draw.rect(surface, COLORS["border"], self.rect, width=1, border_radius=10)
        ts = value_font.render(self.value, True, COLORS["text"])
        surface.blit(ts, (self.rect.x + 12, self.rect.y + (self.rect.height - ts.get_height()) // 2))
        cx = self.rect.right - 18
        cy = self.rect.centery
        pygame.draw.polygon(surface, COLORS["cyan"],
                            [(cx - 6, cy - 3), (cx + 6, cy - 3), (cx, cy + 5)])

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.index = (self.index + 1) % len(self.options)
            return True
        return False


class CollapsibleSection:
    """Secao retratil com cabecalho clicavel mostrando total de itens."""

    HEADER_H  = 52
    CONTENT_H = 152

    def __init__(self, title, selectable=True):
        self.title      = title
        self.selectable = selectable
        self.expanded   = False
        self.items      = []
        self.selected   = set()
        self.scroll     = 0
        self.row_height = 28
        self.rect       = pygame.Rect(0, 0, 0, 0)
        self.mark_rect  = None
        self.clear_rect = None

    # ------------------------------------------------------------------
    def effective_height(self):
        return self.HEADER_H + (self.CONTENT_H if self.expanded else 0)

    # ------------------------------------------------------------------
    def set_items(self, items):
        previous = set(self.get_selected_items())
        self.items = list(items or [])
        if self.selectable:
            self.selected = {i for i in previous if i in self.items} or set(self.items)
        else:
            self.selected = set()
        self.scroll = 0

    def get_selected_items(self):
        if not self.selectable:
            return list(self.items)
        return [i for i in self.items if i in self.selected]

    def select_all(self):
        if self.selectable:
            self.selected = set(self.items)

    def clear_selection(self):
        if self.selectable:
            self.selected.clear()

    # ------------------------------------------------------------------
    def _header_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.HEADER_H)

    def _content_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y + self.HEADER_H, self.rect.width, self.CONTENT_H)

    def _visible_rows(self, list_top):
        bottom = self.rect.y + self.HEADER_H + self.CONTENT_H - 8
        return max(1, (bottom - list_top) // self.row_height)

    # ------------------------------------------------------------------
    def handle_event(self, event):
        hr = self._header_rect()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hr.collidepoint(event.pos):
                self.expanded = not self.expanded
                self.scroll   = 0
                return True

        if not self.expanded:
            return False

        cr = self._content_rect()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if cr.collidepoint(event.pos):
                if event.button == 4:
                    self.scroll = max(0, self.scroll - 1)
                    return True
                if event.button == 5:
                    list_top = cr.y + (40 if self.selectable else 8)
                    max_s = max(0, len(self.items) - self._visible_rows(list_top))
                    self.scroll = min(max_s, self.scroll + 1)
                    return True
                if event.button == 1 and self.selectable:
                    list_top = cr.y + 40
                    if event.pos[1] >= list_top:
                        idx = (event.pos[1] - list_top) // self.row_height + self.scroll
                        if 0 <= idx < len(self.items):
                            item = self.items[idx]
                            if item in self.selected:
                                self.selected.discard(item)
                            else:
                                self.selected.add(item)
                            return True
        return False

    # ------------------------------------------------------------------
    def draw(self, surface, header_font, body_font, mouse_pos):
        hr    = self._header_rect()
        top_r = 16
        bot_r = 0 if self.expanded else 16

        hovered = hr.collidepoint(mouse_pos) and not self.expanded
        hbg = COLORS["surface_hover"] if hovered else COLORS["surface"]
        pygame.draw.rect(surface, hbg, hr,
                         border_top_left_radius=top_r, border_top_right_radius=top_r,
                         border_bottom_left_radius=bot_r, border_bottom_right_radius=bot_r)

        stripe = pygame.Rect(hr.x + 2, hr.y + 12, 3, hr.height - 24)
        stripe_color = COLORS["cyan"] if self.selectable else COLORS["violet"]
        pygame.draw.rect(surface, stripe_color, stripe, border_radius=2)

        ts = header_font.render(self.title, True, COLORS["text"])
        surface.blit(ts, (hr.x + 18, hr.centery - ts.get_height() // 2))

        count = len(self.items)
        if self.selectable:
            sel         = sum(1 for i in self.items if i in self.selected)
            badge_text  = f"{sel} / {count}"
            badge_color = COLORS["violet"]
        else:
            badge_text  = str(count) if count else u"\u2014"
            badge_color = COLORS["cyan"]

        bs   = body_font.render(badge_text, True, COLORS["text"])
        bw   = bs.get_width() + 24
        brect = pygame.Rect(hr.right - bw - 44, hr.centery - 13, bw, 26)
        pygame.draw.rect(surface, badge_color, brect, border_radius=13)
        surface.blit(bs, bs.get_rect(center=brect.center))

        ax, ay = hr.right - 24, hr.centery
        if self.expanded:
            pts = [(ax - 7, ay + 4), (ax + 7, ay + 4), (ax, ay - 4)]
        else:
            pts = [(ax - 7, ay - 4), (ax + 7, ay - 4), (ax, ay + 4)]
        pygame.draw.polygon(surface, COLORS["muted"], pts)

        pygame.draw.rect(surface, COLORS["border"], hr, width=1,
                         border_top_left_radius=top_r, border_top_right_radius=top_r,
                         border_bottom_left_radius=bot_r, border_bottom_right_radius=bot_r)

        if not self.expanded:
            return

        cr = self._content_rect()
        pygame.draw.rect(surface, COLORS["input"], cr,
                         border_bottom_left_radius=16, border_bottom_right_radius=16)
        pygame.draw.rect(surface, COLORS["border"], cr, width=1,
                         border_bottom_left_radius=16, border_bottom_right_radius=16)

        if self.selectable:
            mark_rect  = pygame.Rect(cr.right - 158, cr.y + 10, 68, 22)
            clear_rect = pygame.Rect(cr.right - 82,  cr.y + 10, 68, 22)
            for r, lbl in ((mark_rect, "Marcar"), (clear_rect, "Limpar")):
                rbg = COLORS["surface_hover"] if r.collidepoint(mouse_pos) else COLORS["panel_alt"]
                pygame.draw.rect(surface, rbg, r, border_radius=8)
                pygame.draw.rect(surface, COLORS["border"], r, width=1, border_radius=8)
                lt = body_font.render(lbl, True, COLORS["text"])
                surface.blit(lt, lt.get_rect(center=r.center))
            self.mark_rect  = mark_rect
            self.clear_rect = clear_rect
        else:
            self.mark_rect  = None
            self.clear_rect = None

        list_top = cr.y + (40 if self.selectable else 8)

        if not self.items:
            empty = body_font.render("Sem dados disponiveis", True, COLORS["muted"])
            surface.blit(empty, (cr.x + 16, list_top + 10))
            return

        visible = self._visible_rows(list_top)
        for row, item in enumerate(self.items[self.scroll:self.scroll + visible]):
            ir = pygame.Rect(cr.x + 10, list_top + row * self.row_height,
                             cr.width - 20, self.row_height - 2)
            is_sel = item in self.selected
            if is_sel:
                pygame.draw.rect(surface, COLORS["violet"], ir, border_radius=8)
            elif ir.collidepoint(mouse_pos) and self.selectable:
                pygame.draw.rect(surface, COLORS["surface_hover"], ir, border_radius=8)
            item_s = body_font.render(item, True, COLORS["text"])
            surface.blit(item_s, (ir.x + 10, ir.y + (ir.height - item_s.get_height()) // 2))


# ===========================================================================
# Janela principal
# ===========================================================================

class dialog:
    def __init__(self, title):
        pygame.init()
        pygame.font.init()

        self.running = True
        self.clock   = pygame.time.Clock()
        self.screen  = pygame.display.set_mode((1280, 860), pygame.RESIZABLE)
        pygame.display.set_caption(APP_TITLE)

        self.assets_dir = Path(__file__).resolve().parent / "assets"
        self.banner     = self._load_image("banner.png")
        icon = self._load_image("app_icon.png")
        if icon is not None:
            pygame.display.set_icon(icon)

        self.font_title   = pygame.font.SysFont("Segoe UI", 26, bold=True)
        self.font_section = pygame.font.SysFont("Segoe UI", 17, bold=True)
        self.font_body    = pygame.font.SysFont("Segoe UI", 15)
        self.font_small   = pygame.font.SysFont("Segoe UI", 13)
        self.font_button  = pygame.font.SysFont("Segoe UI", 15, bold=True)
        self.font_label   = pygame.font.SysFont("Segoe UI", 12)

        db_value = "MySQL" if os.getenv("DB_TYPE", "SQLSERVER").upper() == "MYSQL" else "SQL Server (SSMS)"
        self.selector = Selector("Dialeto", ["SQL Server (SSMS)", "MySQL"], db_value)
        self.inputs = {
            "server":   TextInput("Servidor / Host",  os.getenv("DB_SERVER",   "")),
            "database": TextInput("Banco de Dados",   os.getenv("DB_DATABASE", "")),
            "user":     TextInput("Usuario",          os.getenv("DB_USER",     "")),
            "password": TextInput("Senha",            os.getenv("DB_PASSWORD", ""), password=True),
        }
        self.require_recid = Toggle(
            "Exigir RECID BIGINT nos modelos",
            self._env_bool("SQLMANAGER_REQUIRE_RECID", True),
        )

        self.tables_section = CollapsibleSection("Tabelas",      selectable=True)
        self.views_section  = CollapsibleSection("Views",        selectable=True)
        self.edts_section   = CollapsibleSection("EDTs",         selectable=False)
        self.enums_section  = CollapsibleSection("Enumeracoes",  selectable=False)

        self.remote_metadata_loaded = False
        self.status_message  = "Pronto  configure a conexao e teste antes de iniciar."
        self.error_message   = ""
        self.scroll_offset   = 0
        self.pending_action  = None
        self.confirm_message = None
        self.confirm_result  = False

        self.buttons = {
            "cancel": Button("Cancelar",       self._cancel,                  COLORS["danger"],  COLORS["pink"]),
            "test":   Button("Testar Conexao", self._request_test_connection, COLORS["green"],   COLORS["cyan"]),
            "build":  Button("Executar Build", self._request_build,           COLORS["violet"],  COLORS["pink"]),
        }
        self.buttons["build"].enabled = False

        self._refresh_local_lists()
        self._update_remote_lists([], [])

    # ------------------------------------------------------------------

    def _load_image(self, file_name):
        asset = self.assets_dir / file_name
        if asset.exists():
            try:
                return pygame.image.load(str(asset)).convert_alpha()
            except Exception:
                return None
        return None

    @staticmethod
    def _env_bool(name, default):
        value = os.getenv(name)
        if value is None:
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

    def _model_folder(self, child):
        cwd_model = Path.cwd() / "src" / "model" / child
        if cwd_model.exists():
            return cwd_model
        return Path(root_dir) / "src" / "model" / child

    def _list_local_files(self, folder_path):
        if not folder_path.exists():
            return []
        return sorted(
            [f.stem for f in folder_path.iterdir() if f.suffix == ".py" and not f.name.startswith("__")],
            key=str.lower,
        )

    def _refresh_local_lists(self):
        self.edts_section.set_items(self._list_local_files(self._model_folder("EDTs")))
        self.enums_section.set_items(self._list_local_files(self._model_folder("enum")))

    def _update_remote_lists(self, tables, views):
        self.tables_section.set_items(tables)
        self.views_section.set_items(views)

    def _can_query_remote_metadata(self):
        return all(inp.value.strip() for inp in self.inputs.values())

    def _apply_ui_credentials(self):
        from SQLManager import CoreConfig

        db_enum_val = "MYSQL" if self.selector.value == "MySQL" else "SQLSERVER"
        os.environ["DB_TYPE"]     = db_enum_val
        os.environ["DB_SERVER"]   = self.inputs["server"].value
        os.environ["DB_DATABASE"] = self.inputs["database"].value
        os.environ["DB_USER"]     = self.inputs["user"].value
        os.environ["DB_PASSWORD"] = self.inputs["password"].value
        os.environ["SQLMANAGER_REQUIRE_RECID"] = "true" if self.require_recid.value else "false"
        CoreConfig.configure(load_from_env=True)

    def _get_remote_metadata(self):
        from SQLManager.connection import database_connection
        from SQLManager._model._model_update import ModelUpdaterBase

        self._apply_ui_credentials()
        dialect = ModelUpdaterBase()
        db = database_connection()
        db.connect()
        try:
            tables = db.doQuery(dialect.get_model_tables_query())
            views  = db.doQuery(dialect.get_model_views_query())
            return [r[0] for r in tables], [r[0] for r in views]
        finally:
            db.disconnect()

    # ------------------------------------------------------------------

    def _request_test_connection(self):
        if not self._can_query_remote_metadata():
            self.status_message = "Preencha servidor, banco, usuario e senha antes de testar."
            self.error_message  = self.status_message
            return
        self.status_message = "Estabelecendo conexao com o banco de dados..."
        self.error_message  = ""
        self.buttons["test"].enabled  = False
        self.buttons["build"].enabled = False

        def worker():
            try:
                tables, views = self._get_remote_metadata()
                self.pending_action = ("connection_success", tables, views)
            except Exception as exc:
                self.pending_action = ("connection_error", str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _request_build(self):
        if not self.remote_metadata_loaded:
            self.status_message = "Teste a conexao com o banco antes de executar o build."
            self.error_message  = self.status_message
            return
        self._start_build()

    def _start_build(self):
        self.status_message = "Gerando modelos aguarde..."
        self.error_message  = ""
        self.buttons["build"].enabled = False
        self.buttons["test"].enabled  = False

        def confirm_callback(message):
            self.pending_action = ("confirm_from_worker", message)
            while self.confirm_message is not None and self.running:
                self.clock.tick(30)
            return self.confirm_result

        def worker():
            try:
                from SQLManager._model._model_update import ModelUpdater

                self._apply_ui_credentials()
                updater = ModelUpdater()
                updater.run(
                    selected_tables=self.tables_section.get_selected_items(),
                    selected_views=self.views_section.get_selected_items(),
                    confirm_callback=confirm_callback,
                )
                self.pending_action = ("build_success",)
            except Exception as exc:
                self.pending_action = ("build_error", str(exc))

        self.confirm_result = False
        threading.Thread(target=worker, daemon=True).start()

    def _cancel(self):
        self.running = False

    # ------------------------------------------------------------------

    def _handle_pending_action(self):
        if self.pending_action is None:
            return
        action = self.pending_action
        self.pending_action = None
        kind = action[0]

        if kind == "connection_success":
            _, tables, views = action
            self.remote_metadata_loaded = True
            self._update_remote_lists(tables, views)
            self.status_message = f"Conexao estabelecida  {len(tables)} tabelas e {len(views)} views encontradas."
            self.error_message  = ""
            self.buttons["test"].enabled  = True
            self.buttons["build"].enabled = True

        elif kind == "connection_error":
            _, error = action
            self.remote_metadata_loaded = False
            self._update_remote_lists([], [])
            self.status_message = "Falha ao conectar com o banco de dados."
            self.error_message  = error
            self.buttons["test"].enabled  = True
            self.buttons["build"].enabled = False

        elif kind == "confirm_from_worker":
            _, message = action
            self.confirm_message = message

        elif kind == "build_success":
            self.status_message = "Build concluido com sucesso."
            self.error_message  = ""
            self.buttons["test"].enabled  = True
            self.buttons["build"].enabled = True
            self._refresh_local_lists()

        elif kind == "build_error":
            _, error = action
            self.status_message = "Falha durante a geracao dos modelos."
            self.error_message  = error
            self.buttons["test"].enabled  = True
            self.buttons["build"].enabled = self.remote_metadata_loaded

    # ------------------------------------------------------------------

    def _handle_button_shortcuts(self, event):
        if self.confirm_message is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.confirm_result  = True
                self.confirm_message = None
                return True
            if event.key == pygame.K_ESCAPE:
                self.confirm_result  = False
                self.confirm_message = None
                return True
        return False

    # ------------------------------------------------------------------

    def _draw_text(self, text, font, color, x, y):
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))

    def _draw_wrapped(self, text, font, color, rect):
        words = text.split()
        line, y = [], rect.y
        for word in words:
            trial = " ".join(line + [word])
            if font.size(trial)[0] > rect.width and line:
                self._draw_text(" ".join(line), font, color, rect.x, y)
                y += font.get_height() + 3
                line = [word]
            else:
                line.append(word)
        if line:
            self._draw_text(" ".join(line), font, color, rect.x, y)

    def _section_label(self, text, x, y):
        s = self.font_label.render(text.upper(), True, COLORS["muted"])
        self.screen.blit(s, (x, y))
        line_x = x + s.get_width() + 8
        line_y = y + s.get_height() // 2
        pygame.draw.line(self.screen, COLORS["border"], (line_x, line_y), (x + 300, line_y), 1)

    # ------------------------------------------------------------------

    def _draw_header(self, rect):
        pygame.draw.rect(self.screen, COLORS["panel"], rect, border_radius=20)
        pygame.draw.rect(self.screen, COLORS["border"], rect, width=1, border_radius=20)

        if self.banner is not None:
            bw, bh = self.banner.get_size()
            max_w  = rect.width  - 40
            max_h  = rect.height - 20
            scale  = min(max_w / bw, max_h / bh)
            sw, sh = int(bw * scale), int(bh * scale)
            scaled = pygame.transform.smoothscale(self.banner, (sw, sh))
            self.screen.blit(scaled, scaled.get_rect(center=rect.center))
        else:
            self._draw_text(APP_TITLE, self.font_title, COLORS["text"],
                            rect.x + 24, rect.centery - 13)

        accent = pygame.Rect(rect.x + 32, rect.bottom - 3, rect.width - 64, 3)
        pygame.draw.rect(self.screen, COLORS["cyan"], accent, border_radius=2)

    def _draw_left_panel(self, rect):
        pygame.draw.rect(self.screen, COLORS["panel"], rect, border_radius=18)
        pygame.draw.rect(self.screen, COLORS["border"], rect, width=1, border_radius=18)

        x = rect.x + 18
        y = rect.y + 14

        self._section_label("Dialeto do banco", x, y)
        self.selector.draw(self.screen, self.font_small, self.font_body)

        y += 20 + 40 + 14
        self._section_label("Credenciais de acesso", x, y)
        for field in self.inputs.values():
            field.draw(self.screen, self.font_small, self.font_body)

        y += 20 + 4 * 52
        self._section_label("Opcoes de runtime", x, y)
        self.require_recid.draw(self.screen, self.font_body)

    # ------------------------------------------------------------------

    def _layout(self):
        width, _height = self.screen.get_size()
        pad = 18
        ox  = pad
        oy  = pad - self.scroll_offset
        ow  = width - 2 * pad

        header = pygame.Rect(ox, oy, ow, 106)

        content_y = header.bottom + 14
        left_w    = 342
        right_w   = ow - left_w - 12

        # Altura do painel esquerdo calculada estaticamente
        left_h = 14 + 20 + 40 + 14 + 20 + 4 * 52 + 14 + 22 + 28 + 16
        left_col = pygame.Rect(ox, content_y, left_w, left_h)

        sections   = [self.tables_section, self.views_section,
                      self.edts_section,   self.enums_section]
        sections_h = sum(s.effective_height() for s in sections) + (len(sections) - 1) * 8
        right_col  = pygame.Rect(ox + left_w + 12, content_y, right_w, sections_h)

        bottom_y     = max(left_col.bottom, right_col.bottom) + 16
        buttons_rect = pygame.Rect(ox, bottom_y, ow, 52)
        status_rect  = pygame.Rect(ox, buttons_rect.bottom + 10, ow, 24)

        return header, left_col, right_col, buttons_rect, status_rect

    def _update_widget_rects(self, left_col, right_col, buttons_rect):
        x = left_col.x + 18

        # Selector: logo abaixo do label (top pad 14 + label 20 = y+34)
        sel_y = left_col.y + 14 + 20
        self.selector.rect = pygame.Rect(x, sel_y, left_col.width - 36, 40)

        # Inputs: apos selector + gap + label (40 + 14 + 20 = 74)
        inp_y = sel_y + 40 + 14 + 20
        for key in ("server", "database", "user", "password"):
            self.inputs[key].rect = pygame.Rect(x, inp_y + 16, left_col.width - 36, 38)
            inp_y += 52

        # Toggle: apos inputs + gap + label (14 + 22 = 36)
        toggle_y = inp_y + 14 + 22
        self.require_recid.rect = pygame.Rect(x, toggle_y, left_col.width - 36, 24)

        # Secoes na coluna direita
        sy = right_col.y
        for section in (self.tables_section, self.views_section,
                        self.edts_section,   self.enums_section):
            section.rect = pygame.Rect(right_col.x, sy, right_col.width, section.effective_height())
            sy += section.effective_height() + 8

        # Botoes: Cancelar | Testar Conexao | Executar Build
        bw = (buttons_rect.width - 2 * 12) // 3
        self.buttons["cancel"].rect = pygame.Rect(buttons_rect.x,                  buttons_rect.y, bw, 52)
        self.buttons["test"].rect   = pygame.Rect(buttons_rect.x + bw + 12,        buttons_rect.y, bw, 52)
        self.buttons["build"].rect  = pygame.Rect(buttons_rect.x + 2 * (bw + 12),  buttons_rect.y, bw, 52)

    # ------------------------------------------------------------------

    def _draw(self):
        self.screen.fill(COLORS["bg"])
        header, left_col, right_col, buttons_rect, status_rect = self._layout()
        self._update_widget_rects(left_col, right_col, buttons_rect)
        mouse = pygame.mouse.get_pos()

        self._draw_header(header)
        self._draw_left_panel(left_col)

        for section in (self.tables_section, self.views_section,
                        self.edts_section,   self.enums_section):
            section.draw(self.screen, self.font_section, self.font_small, mouse)

        for button in self.buttons.values():
            button.draw(self.screen, self.font_button, mouse)

        status_color = COLORS["danger"] if self.error_message else COLORS["muted"]
        self._draw_wrapped(self.error_message or self.status_message,
                           self.font_small, status_color, status_rect)

        self._draw_confirm_modal(mouse)
        pygame.display.flip()

    def _draw_confirm_modal(self, mouse):
        if self.confirm_message is None:
            self.confirm_yes_rect = None
            self.confirm_no_rect  = None
            return

        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        modal = pygame.Rect(
            self.screen.get_width()  // 2 - 240,
            self.screen.get_height() // 2 - 130,
            480, 240,
        )
        pygame.draw.rect(self.screen, COLORS["panel"], modal, border_radius=20)
        pygame.draw.rect(self.screen, COLORS["border"], modal, width=1, border_radius=20)

        top_stripe = pygame.Rect(modal.x + 1, modal.y + 1, modal.width - 2, 4)
        pygame.draw.rect(self.screen, COLORS["violet"], top_stripe,
                         border_top_left_radius=20, border_top_right_radius=20)

        self._draw_text("Confirmacao necessaria", self.font_section,
                        COLORS["text"], modal.x + 22, modal.y + 20)
        self._draw_wrapped(self.confirm_message, self.font_body, COLORS["muted"],
                           pygame.Rect(modal.x + 22, modal.y + 56, modal.width - 44, 110))

        yes_rect = pygame.Rect(modal.x + 22,      modal.bottom - 66, 204, 42)
        no_rect  = pygame.Rect(modal.right - 226,  modal.bottom - 66, 204, 42)

        for r, label, color in (
            (yes_rect, "Confirmar", COLORS["violet"]),
            (no_rect,  "Cancelar",  COLORS["danger"]),
        ):
            bg = tuple(min(255, c + 22) for c in color) if r.collidepoint(mouse) else color
            pygame.draw.rect(self.screen, bg, r, border_radius=14)
            t = self.font_button.render(label, True, COLORS["text"])
            self.screen.blit(t, t.get_rect(center=r.center))

        self.confirm_yes_rect = yes_rect
        self.confirm_no_rect  = no_rect

    # ------------------------------------------------------------------

    def _handle_mouse_actions(self, event):
        if self.confirm_message is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.confirm_yes_rect and self.confirm_yes_rect.collidepoint(event.pos):
                    self.confirm_result  = True
                    self.confirm_message = None
                    return True
                if self.confirm_no_rect and self.confirm_no_rect.collidepoint(event.pos):
                    self.confirm_result  = False
                    self.confirm_message = None
                    return True
            return False

        if self.selector.handle_event(event):
            self.remote_metadata_loaded = False
            self._update_remote_lists([], [])
            self.buttons["build"].enabled = False
            return True

        if self.require_recid.handle_event(event):
            return True

        for section in (self.tables_section, self.views_section,
                        self.edts_section,   self.enums_section):
            if section.handle_event(event):
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if section.mark_rect and section.mark_rect.collidepoint(event.pos):
                    section.select_all()
                    return True
                if section.clear_rect and section.clear_rect.collidepoint(event.pos):
                    section.clear_selection()
                    return True

        if self.confirm_message is None:
            for field in self.inputs.values():
                field.handle_event(event)

        for button in self.buttons.values():
            if button.handle_click(event):
                button.action()
                return True

        return False

    # ------------------------------------------------------------------

    def start(self):
        while self.running:
            self._handle_pending_action()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.confirm_message is None:
                    self.running = False
                    break
                if event.type == pygame.MOUSEWHEEL:
                    self.scroll_offset = max(0, self.scroll_offset - event.y * 18)
                if self._handle_button_shortcuts(event):
                    continue
                self._handle_mouse_actions(event)

            self._draw()
            self.clock.tick(60)

        pygame.quit()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    d = dialog(APP_TITLE)
    d.start()
