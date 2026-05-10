import os
import sys
import threading
from pathlib import Path

import pygame

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

APP_TITLE = "Model - SQLManager"
APP_SUBTITLE = "Model update com interface em pygame"
APP_DESCRIPTION = "Selecione o banco, teste a conexao, revise tabelas e views e execute o build inicial."
APP_TAGS = ["AutoRouter", "WebSocket", "Relations", "ORM-like"]

COLORS = {
    "bg": (8, 12, 20),
    "panel": (13, 20, 36),
    "panel_alt": (16, 26, 45),
    "surface": (21, 31, 51),
    "surface_hover": (28, 42, 66),
    "input": (11, 19, 34),
    "border": (36, 50, 77),
    "text": (244, 248, 255),
    "muted": (124, 143, 171),
    "cyan": (0, 229, 255),
    "violet": (124, 58, 237),
    "green": (16, 185, 129),
    "pink": (236, 72, 153),
    "warning": (245, 158, 11),
    "danger": (244, 63, 94),
}

current_dir = os.path.dirname(os.path.abspath(__file__))
model_dir = os.path.dirname(current_dir)
package_dir = os.path.dirname(model_dir)
root_dir = os.path.dirname(package_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if load_dotenv is not None:
    load_dotenv(os.path.join(os.getcwd(), ".env"))
    load_dotenv(os.path.join(root_dir, ".env"))


class Button:
    def __init__(self, label, action, color):
        self.label = label
        self.action = action
        self.color = color
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.enabled = True

    def draw(self, surface, font, mouse_pos):
        bg = self.color if self.enabled else COLORS["border"]
        if self.enabled and self.rect.collidepoint(mouse_pos):
            bg = tuple(min(255, channel + 18) for channel in bg)
        pygame.draw.rect(surface, bg, self.rect, border_radius=12)
        pygame.draw.rect(surface, COLORS["border"], self.rect, width=1, border_radius=12)
        text = font.render(self.label, True, COLORS["text"])
        surface.blit(text, text.get_rect(center=self.rect.center))

    def handle_click(self, event):
        return self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


class Toggle:
    def __init__(self, label, value=False):
        self.label = label
        self.value = value
        self.rect = pygame.Rect(0, 0, 0, 0)

    def draw(self, surface, font):
        box = pygame.Rect(self.rect.x, self.rect.y + 3, 18, 18)
        pygame.draw.rect(surface, COLORS["input"], box, border_radius=5)
        pygame.draw.rect(surface, COLORS["violet" if self.value else "border"], box, width=2, border_radius=5)
        if self.value:
            pygame.draw.line(surface, COLORS["text"], (box.x + 4, box.y + 9), (box.x + 8, box.y + 13), 2)
            pygame.draw.line(surface, COLORS["text"], (box.x + 8, box.y + 13), (box.x + 14, box.y + 5), 2)
        text = font.render(self.label, True, COLORS["text"])
        surface.blit(text, (self.rect.x + 30, self.rect.y))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.value = not self.value
            return True
        return False


class TextInput:
    def __init__(self, label, value="", password=False):
        self.label = label
        self.value = value
        self.password = password
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.active = False

    def draw(self, surface, label_font, input_font):
        label = label_font.render(self.label, True, COLORS["muted"])
        surface.blit(label, (self.rect.x, self.rect.y - 18))
        pygame.draw.rect(surface, COLORS["input"], self.rect, border_radius=10)
        border = COLORS["cyan"] if self.active else COLORS["border"]
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=10)
        display_text = self.value if not self.password else "*" * len(self.value)
        text_surface = input_font.render(display_text, True, COLORS["text"])
        surface.blit(text_surface, (self.rect.x + 12, self.rect.y + 10))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key == pygame.K_TAB:
                return False
            elif event.key == pygame.K_RETURN:
                return True
            elif event.unicode and event.unicode.isprintable():
                self.value += event.unicode
        return False


class Selector:
    def __init__(self, label, options, current):
        self.label = label
        self.options = options
        self.index = options.index(current) if current in options else 0
        self.rect = pygame.Rect(0, 0, 0, 0)

    @property
    def value(self):
        return self.options[self.index]

    def draw(self, surface, label_font, value_font):
        label = label_font.render(self.label, True, COLORS["muted"])
        surface.blit(label, (self.rect.x, self.rect.y - 18))
        pygame.draw.rect(surface, COLORS["input"], self.rect, border_radius=10)
        pygame.draw.rect(surface, COLORS["border"], self.rect, width=2, border_radius=10)
        text = value_font.render(self.value, True, COLORS["text"])
        surface.blit(text, (self.rect.x + 12, self.rect.y + 10))
        pygame.draw.polygon(surface, COLORS["cyan"], [(self.rect.right - 24, self.rect.y + 16), (self.rect.right - 12, self.rect.y + 16), (self.rect.right - 18, self.rect.y + 24)])

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.index = (self.index + 1) % len(self.options)
            return True
        return False


class MultiSelectList:
    def __init__(self, title, selectable=True):
        self.title = title
        self.selectable = selectable
        self.items = []
        self.selected = set()
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.scroll = 0
        self.row_height = 26

    def set_items(self, items):
        previous = set(self.get_selected_items())
        self.items = list(items or [])
        if self.selectable:
            self.selected = {item for item in previous if item in self.items} or set(self.items)
        else:
            self.selected = set()
        self.scroll = 0

    def get_selected_items(self):
        if not self.selectable:
            return list(self.items)
        return [item for item in self.items if item in self.selected]

    def select_all(self):
        if self.selectable:
            self.selected = set(self.items)

    def clear(self):
        if self.selectable:
            self.selected.clear()

    def handle_event(self, event, offset_y):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            if event.button == 4:
                self.scroll = max(0, self.scroll - 1)
                return True
            if event.button == 5:
                max_scroll = max(0, len(self.items) - self.visible_rows())
                self.scroll = min(max_scroll, self.scroll + 1)
                return True
            if event.button == 1 and self.selectable:
                list_top = self.rect.y + 44
                if event.pos[1] >= list_top:
                    index = (event.pos[1] - list_top) // self.row_height + self.scroll
                    if 0 <= index < len(self.items):
                        item = self.items[index]
                        if item in self.selected:
                            self.selected.remove(item)
                        else:
                            self.selected.add(item)
                        return True
        return False

    def visible_rows(self):
        return max(1, (self.rect.height - 56) // self.row_height)

    def draw(self, surface, header_font, body_font, mouse_pos):
        pygame.draw.rect(surface, COLORS["surface"], self.rect, border_radius=16)
        pygame.draw.rect(surface, COLORS["border"], self.rect, width=1, border_radius=16)
        title = header_font.render(self.title, True, COLORS["text"])
        count = body_font.render(f"{len(self.items)} itens", True, COLORS["cyan"])
        surface.blit(title, (self.rect.x + 14, self.rect.y + 12))
        surface.blit(count, (self.rect.x + 14, self.rect.y + 32))

        if self.selectable:
            mark_rect = pygame.Rect(self.rect.right - 154, self.rect.y + 12, 66, 24)
            clear_rect = pygame.Rect(self.rect.right - 80, self.rect.y + 12, 66, 24)
            for rect, label in ((mark_rect, "Marcar"), (clear_rect, "Limpar")):
                color = COLORS["panel_alt"]
                if rect.collidepoint(mouse_pos):
                    color = COLORS["surface_hover"]
                pygame.draw.rect(surface, color, rect, border_radius=10)
                pygame.draw.rect(surface, COLORS["border"], rect, width=1, border_radius=10)
                txt = body_font.render(label, True, COLORS["text"])
                surface.blit(txt, txt.get_rect(center=rect.center))
            self.mark_rect = mark_rect
            self.clear_rect = clear_rect
        else:
            self.mark_rect = None
            self.clear_rect = None

        list_rect = pygame.Rect(self.rect.x + 12, self.rect.y + 52, self.rect.width - 24, self.rect.height - 64)
        pygame.draw.rect(surface, COLORS["input"], list_rect, border_radius=12)
        if not self.items:
            empty = body_font.render("Sem dados", True, COLORS["muted"])
            surface.blit(empty, (list_rect.x + 12, list_rect.y + 12))
            return

        visible_rows = self.visible_rows()
        visible_items = self.items[self.scroll:self.scroll + visible_rows]
        for row, item in enumerate(visible_items):
            item_rect = pygame.Rect(list_rect.x + 8, list_rect.y + 6 + row * self.row_height, list_rect.width - 16, self.row_height - 2)
            is_selected = item in self.selected
            if is_selected:
                pygame.draw.rect(surface, COLORS["violet"], item_rect, border_radius=8)
            elif item_rect.collidepoint(mouse_pos):
                pygame.draw.rect(surface, COLORS["surface_hover"], item_rect, border_radius=8)
            text_color = COLORS["text"] if is_selected else COLORS["text"]
            item_surface = body_font.render(item, True, text_color)
            surface.blit(item_surface, (item_rect.x + 10, item_rect.y + 5))


class dialog:
    def __init__(self, title: str):
        pygame.init()
        pygame.font.init()
        self.running = True
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((1280, 860), pygame.RESIZABLE)
        pygame.display.set_caption(APP_TITLE)

        self.assets_dir = Path(__file__).resolve().parent / "assets"
        self.banner = self._load_image("banner.png")
        self.icon = self._load_image("app_icon.png")
        if self.icon is not None:
            pygame.display.set_icon(self.icon)

        self.font_title = pygame.font.SysFont("Segoe UI", 28, bold=True)
        self.font_subtitle = pygame.font.SysFont("Segoe UI", 16)
        self.font_section = pygame.font.SysFont("Segoe UI", 18, bold=True)
        self.font_body = pygame.font.SysFont("Segoe UI", 15)
        self.font_small = pygame.font.SysFont("Segoe UI", 13)
        self.font_button = pygame.font.SysFont("Segoe UI", 16, bold=True)

        db_value = "MySQL" if os.getenv("DB_TYPE", "SQLSERVER").upper() == "MYSQL" else "SQL Server (SSMS)"
        self.selector = Selector("Banco", ["SQL Server (SSMS)", "MySQL"], db_value)
        self.inputs = {
            "server": TextInput("Servidor (Host)", os.getenv("DB_SERVER", "")),
            "database": TextInput("Banco (Database)", os.getenv("DB_DATABASE", "")),
            "user": TextInput("Usuario (User)", os.getenv("DB_USER", "")),
            "password": TextInput("Senha (Password)", os.getenv("DB_PASSWORD", ""), password=True),
        }
        self.require_recid = Toggle("Exigir RECID BIGINT no Model Update", self._env_bool("SQLMANAGER_REQUIRE_RECID", True))

        self.tables_list = MultiSelectList("Tabelas", selectable=True)
        self.views_list = MultiSelectList("Views", selectable=True)
        self.edts_list = MultiSelectList("EDTs", selectable=False)
        self.enums_list = MultiSelectList("Enums", selectable=False)

        self.remote_tables = []
        self.remote_views = []
        self.remote_metadata_loaded = False
        self.status_message = "Pronto para iniciar"
        self.error_message = ""
        self.scroll_offset = 0
        self.pending_action = None
        self.confirm_message = None

        self.buttons = {
            "build": Button("Inicial Build", self._request_build, COLORS["violet"]),
            "test": Button("Testar Conexao", self._request_test_connection, COLORS["green"]),
            "cancel": Button("Cancelar", self._cancel, COLORS["danger"]),
        }
        self.buttons["build"].enabled = False

        self._refresh_local_lists()
        self._update_remote_lists([] , [])

    def _load_image(self, file_name):
        asset = self.assets_dir / file_name
        if asset.exists():
            try:
                return pygame.image.load(str(asset)).convert_alpha()
            except Exception:
                return None
        return None

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

    def _model_folder(self, child: str) -> Path:
        cwd_model = Path.cwd() / "src" / "model" / child
        if cwd_model.exists():
            return cwd_model
        return Path(root_dir) / "src" / "model" / child

    def _list_local_files(self, folder_path: Path):
        if not folder_path.exists():
            return []
        return sorted([item.stem for item in folder_path.iterdir() if item.suffix == ".py" and not item.name.startswith("__")], key=str.lower)

    def _refresh_local_lists(self):
        self.edts_list.set_items(self._list_local_files(self._model_folder("EDTs")))
        self.enums_list.set_items(self._list_local_files(self._model_folder("enum")))

    def _update_remote_lists(self, tables, views):
        self.tables_list.set_items(tables)
        self.views_list.set_items(views)

    def _can_query_remote_metadata(self):
        return all(input_box.value.strip() for input_box in self.inputs.values())

    def _apply_ui_credentials(self):
        from SQLManager import CoreConfig

        db_enum_val = "MYSQL" if self.selector.value == "MySQL" else "SQLSERVER"
        os.environ["DB_TYPE"] = db_enum_val
        os.environ["DB_SERVER"] = self.inputs["server"].value
        os.environ["DB_DATABASE"] = self.inputs["database"].value
        os.environ["DB_USER"] = self.inputs["user"].value
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
            views = db.doQuery(dialect.get_model_views_query())
            return [row[0] for row in tables], [row[0] for row in views]
        finally:
            db.disconnect()

    def _request_test_connection(self):
        if not self._can_query_remote_metadata():
            self.status_message = "Preencha servidor, banco, usuario e senha antes de testar a conexao"
            self.error_message = self.status_message
            return
        self.status_message = "Testando conexao..."
        self.error_message = ""
        self.buttons["test"].enabled = False
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
            self.status_message = "Teste a conexao antes de iniciar o build"
            self.error_message = self.status_message
            return
        self._start_build()

    def _start_build(self):
        self.status_message = "Executando build inicial..."
        self.error_message = ""
        self.buttons["build"].enabled = False
        self.buttons["test"].enabled = False

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
                    selected_tables=self.tables_list.get_selected_items(),
                    selected_views=self.views_list.get_selected_items(),
                    confirm_callback=confirm_callback,
                )
                self.pending_action = ("build_success",)
            except Exception as exc:
                self.pending_action = ("build_error", str(exc))

        self.confirm_result = False
        threading.Thread(target=worker, daemon=True).start()

    def _cancel(self):
        self.running = False

    def _handle_pending_action(self):
        if self.pending_action is None:
            return
        action = self.pending_action
        self.pending_action = None
        kind = action[0]
        if kind == "connection_success":
            _, tables, views = action
            self.remote_tables = tables
            self.remote_views = views
            self.remote_metadata_loaded = True
            self._update_remote_lists(tables, views)
            self.status_message = "Conexao estabelecida com sucesso"
            self.error_message = ""
            self.buttons["test"].enabled = True
            self.buttons["build"].enabled = True
        elif kind == "connection_error":
            _, error = action
            self.remote_tables = []
            self.remote_views = []
            self.remote_metadata_loaded = False
            self._update_remote_lists([], [])
            self.status_message = "Falha ao conectar"
            self.error_message = error
            self.buttons["test"].enabled = True
            self.buttons["build"].enabled = False
        elif kind == "confirm_from_worker":
            _, message = action
            self.confirm_message = message
        elif kind == "build_success":
            self.status_message = "Build concluido com sucesso"
            self.error_message = ""
            self.buttons["test"].enabled = True
            self.buttons["build"].enabled = True
            self._refresh_local_lists()
        elif kind == "build_error":
            _, error = action
            self.status_message = "Falha no build"
            self.error_message = error
            self.buttons["test"].enabled = True
            self.buttons["build"].enabled = self.remote_metadata_loaded

    def _handle_button_shortcuts(self, event):
        if self.confirm_message is None:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.confirm_result = True
                self.confirm_message = None
                return True
            if event.key == pygame.K_ESCAPE:
                self.confirm_result = False
                self.confirm_message = None
                return True
        return False

    def _draw_text(self, text, font, color, x, y):
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))

    def _draw_wrapped(self, text, font, color, rect):
        words = text.split()
        line = []
        y = rect.y
        for word in words:
            trial = " ".join(line + [word])
            if font.size(trial)[0] > rect.width and line:
                self._draw_text(" ".join(line), font, color, rect.x, y)
                y += font.get_height() + 4
                line = [word]
            else:
                line.append(word)
        if line:
            self._draw_text(" ".join(line), font, color, rect.x, y)

    def _draw_header(self, rect):
        pygame.draw.rect(self.screen, COLORS["panel"], rect, border_radius=20)
        pygame.draw.rect(self.screen, COLORS["border"], rect, width=1, border_radius=20)
        icon_rect = pygame.Rect(rect.x + 18, rect.y + 18, 86, 86)
        pygame.draw.rect(self.screen, COLORS["panel_alt"], icon_rect, border_radius=18)
        pygame.draw.rect(self.screen, COLORS["border"], icon_rect, width=1, border_radius=18)
        if self.icon is not None:
            scaled = pygame.transform.smoothscale(self.icon, (60, 60))
            self.screen.blit(scaled, scaled.get_rect(center=icon_rect.center))
        if self.banner is not None:
            banner = pygame.transform.smoothscale(self.banner, (420, 104))
            self.screen.blit(banner, (rect.x + 124, rect.y + 10))
        else:
            self._draw_text(APP_TITLE, self.font_title, COLORS["text"], rect.x + 126, rect.y + 24)
        self._draw_text(APP_SUBTITLE, self.font_body, COLORS["cyan"], rect.x + 126, rect.y + 104)
        self._draw_wrapped(APP_DESCRIPTION, self.font_small, COLORS["muted"], pygame.Rect(rect.x + 126, rect.y + 128, rect.width - 144, 40))

        pill_x = rect.x + rect.width - 430
        for tag, color in zip(APP_TAGS, [COLORS["violet"], COLORS["cyan"], COLORS["green"], COLORS["pink"]]):
            label = self.font_small.render(tag, True, COLORS["text"])
            pill = pygame.Rect(pill_x, rect.y + 24, label.get_width() + 20, 24)
            pygame.draw.rect(self.screen, color, pill, border_radius=12)
            self.screen.blit(label, label.get_rect(center=pill.center))
            pill_x += pill.width + 8

    def _draw_panel(self, rect, title, subtitle=None):
        pygame.draw.rect(self.screen, COLORS["surface"], rect, border_radius=18)
        pygame.draw.rect(self.screen, COLORS["border"], rect, width=1, border_radius=18)
        self._draw_text(title, self.font_section, COLORS["text"], rect.x + 16, rect.y + 14)
        if subtitle:
            self._draw_text(subtitle, self.font_small, COLORS["muted"], rect.x + 16, rect.y + 38)

    def _layout(self):
        width, height = self.screen.get_size()
        outer = pygame.Rect(20, 20 - self.scroll_offset, width - 40, 980)
        header = pygame.Rect(outer.x, outer.y, outer.width, 176)
        controls_left = pygame.Rect(outer.x, header.bottom + 14, (outer.width - 12) // 2, 84)
        controls_right = pygame.Rect(controls_left.right + 12, header.bottom + 14, outer.width - controls_left.width - 12, 84)
        left_col = pygame.Rect(outer.x, controls_left.bottom + 12, 360, 266)
        right_col = pygame.Rect(left_col.right + 12, controls_left.bottom + 12, outer.width - left_col.width - 12, 556)
        buttons = pygame.Rect(outer.x, right_col.bottom + 14, outer.width, 56)
        return outer, header, controls_left, controls_right, left_col, right_col, buttons

    def _update_widget_rects(self, controls_left, controls_right, left_col, right_col, buttons_rect):
        self.selector.rect = pygame.Rect(controls_left.x + 16, controls_left.y + 36, controls_left.width - 32, 42)
        self.require_recid.rect = pygame.Rect(controls_right.x + 16, controls_right.y + 38, controls_right.width - 32, 22)

        input_width = left_col.width - 32
        top = left_col.y + 50
        for index, key in enumerate(("server", "database", "user", "password")):
            self.inputs[key].rect = pygame.Rect(left_col.x + 16, top + index * 52, input_width, 40)

        panel_width = (right_col.width - 12) // 2
        panel_height = (right_col.height - 12) // 2
        self.tables_list.rect = pygame.Rect(right_col.x, right_col.y, panel_width, panel_height)
        self.views_list.rect = pygame.Rect(right_col.x + panel_width + 12, right_col.y, panel_width, panel_height)
        self.edts_list.rect = pygame.Rect(right_col.x, right_col.y + panel_height + 12, panel_width, panel_height)
        self.enums_list.rect = pygame.Rect(right_col.x + panel_width + 12, right_col.y + panel_height + 12, panel_width, panel_height)

        button_width = (buttons_rect.width - 24) // 3
        self.buttons["build"].rect = pygame.Rect(buttons_rect.x, buttons_rect.y, button_width, 48)
        self.buttons["test"].rect = pygame.Rect(buttons_rect.x + button_width + 12, buttons_rect.y, button_width, 48)
        self.buttons["cancel"].rect = pygame.Rect(buttons_rect.right - button_width, buttons_rect.y, button_width, 48)

    def _draw(self):
        self.screen.fill(COLORS["bg"])
        outer, header, controls_left, controls_right, left_col, right_col, buttons_rect = self._layout()
        self._update_widget_rects(controls_left, controls_right, left_col, right_col, buttons_rect)

        self._draw_header(header)
        self._draw_panel(controls_left, "Banco", "Clique para alternar o dialeto")
        self.selector.draw(self.screen, self.font_small, self.font_body)
        self._draw_panel(controls_right, "Runtime", "Aplicado apenas durante o build")
        self.require_recid.draw(self.screen, self.font_body)
        self._draw_panel(left_col, "Credenciais", "Usadas apenas em runtime")
        for field in self.inputs.values():
            field.draw(self.screen, self.font_small, self.font_body)

        for widget in (self.tables_list, self.views_list, self.edts_list, self.enums_list):
            widget.draw(self.screen, self.font_section, self.font_small, pygame.mouse.get_pos())

        for button in self.buttons.values():
            button.draw(self.screen, self.font_button, pygame.mouse.get_pos())

        status_color = COLORS["danger"] if self.error_message else COLORS["cyan"]
        status_rect = pygame.Rect(buttons_rect.x, buttons_rect.y + 58, buttons_rect.width, 24)
        self._draw_wrapped(self.error_message or self.status_message, self.font_small, status_color, status_rect)

        if self.confirm_message is not None:
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
            modal = pygame.Rect(self.screen.get_width() // 2 - 220, self.screen.get_height() // 2 - 120, 440, 220)
            pygame.draw.rect(self.screen, COLORS["panel"], modal, border_radius=18)
            pygame.draw.rect(self.screen, COLORS["border"], modal, width=1, border_radius=18)
            self._draw_text("Confirmacao", self.font_section, COLORS["text"], modal.x + 18, modal.y + 16)
            self._draw_wrapped(self.confirm_message, self.font_body, COLORS["muted"], pygame.Rect(modal.x + 18, modal.y + 52, modal.width - 36, 90))
            yes_rect = pygame.Rect(modal.x + 18, modal.bottom - 62, 190, 40)
            no_rect = pygame.Rect(modal.right - 208, modal.bottom - 62, 190, 40)
            pygame.draw.rect(self.screen, COLORS["violet"], yes_rect, border_radius=12)
            pygame.draw.rect(self.screen, COLORS["danger"], no_rect, border_radius=12)
            self._draw_text("Continuar", self.font_button, COLORS["text"], yes_rect.x + 48, yes_rect.y + 11)
            self._draw_text("Cancelar", self.font_button, COLORS["text"], no_rect.x + 52, no_rect.y + 11)
            self.confirm_yes_rect = yes_rect
            self.confirm_no_rect = no_rect
        else:
            self.confirm_yes_rect = None
            self.confirm_no_rect = None

        pygame.display.flip()

    def _handle_mouse_actions(self, event):
        if self.confirm_message is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.confirm_yes_rect and self.confirm_yes_rect.collidepoint(event.pos):
                    self.confirm_result = True
                    self.confirm_message = None
                    if self.status_message == "Executando build inicial...":
                        return True
                if self.confirm_no_rect and self.confirm_no_rect.collidepoint(event.pos):
                    self.confirm_result = False
                    self.confirm_message = None
                    return True
            return False

        if self.selector.handle_event(event):
            self.remote_tables = []
            self.remote_views = []
            self.remote_metadata_loaded = False
            self._update_remote_lists([], [])
            self.buttons["build"].enabled = False
            return True

        if self.require_recid.handle_event(event):
            return True

        for panel in (self.tables_list, self.views_list, self.edts_list, self.enums_list):
            if panel.handle_event(event, self.scroll_offset):
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and panel.mark_rect and panel.mark_rect.collidepoint(event.pos):
                panel.select_all()
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and panel.clear_rect and panel.clear_rect.collidepoint(event.pos):
                panel.clear()
                return True

        for button in self.buttons.values():
            if button.handle_click(event):
                button.action()
                return True

        return False

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
                if self._handle_button_shortcuts(event):
                    continue
                if self.confirm_message is None:
                    for field in self.inputs.values():
                        field.handle_event(event)
                self._handle_mouse_actions(event)

            self._draw()
            self.clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    teste = dialog(APP_TITLE)
    teste.start()
