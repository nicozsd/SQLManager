''' [BEGIN CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 12/03/2026 '''

from __future__ import annotations

import asyncio
import inspect

from typing import Any, Dict, Optional

try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    SOCKETIO_AVAILABLE = True
except ImportError:
    SocketIO = None
    emit = None
    join_room = None
    leave_room = None
    SOCKETIO_AVAILABLE = False


class WebSocketManager:
    """Gerencia broadcasts em tempo real usando adaptadores WebSocket comuns."""

    def __init__(self, app=None, socketio: Optional[Any] = None, enabled: bool = False, config: Optional[Dict[str, Any]] = None):
        self.app = app
        self.config = config or {}
        self.socketio = socketio
        self.enabled = bool(enabled)
        self.adapter = "disabled"

        if not self.enabled:
            self.socketio = None
            return

        if self.socketio is None and app is not None and SOCKETIO_AVAILABLE and SocketIO is not None:
            self.socketio = SocketIO(
                app,
                cors_allowed_origins=self.config.get("cors_allowed_origins", "*"),
                async_mode=self.config.get("async_mode", "threading")
            )

        if self.socketio is None:
            self.enabled = False
            return

        self.adapter = self._detect_adapter(self.socketio)
        self._register_events()

    def _detect_adapter(self, socketio: Any) -> str:
        module_name = socketio.__class__.__module__.lower()
        class_name = socketio.__class__.__name__.lower()

        if "flask_socketio" in module_name:
            return "flask_socketio"
        if "socketio" in module_name or "socketio" in class_name:
            return "python_socketio"
        if hasattr(socketio, "publish"):
            return "publisher"
        if hasattr(socketio, "broadcast"):
            return "broadcaster"
        if hasattr(socketio, "emit"):
            return "emitter"
        if hasattr(socketio, "send_json") or hasattr(socketio, "send"):
            return "sender"
        return "generic"

    def _run_maybe_async(self, result):
        if not inspect.isawaitable(result):
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(result)
        except RuntimeError:
            asyncio.run(result)

    def _safe_call(self, func, *args, **kwargs):
        try:
            self._run_maybe_async(func(*args, **kwargs))
            return True
        except TypeError:
            return False

    def _register_events(self):
        if not hasattr(self.socketio, "on"):
            return

        try:
            @self.socketio.on("connect")
            def handle_connect(*args, **kwargs):
                payload = {
                    "status": "connected",
                    "message": "Connected to SQLManager WebSocket",
                    "features": ["table_rooms", "simple_notifications", "full_data_sync"]
                }
                if self.adapter == "flask_socketio" and emit is not None:
                    emit("connection_response", payload)
                else:
                    self._emit("connection_response", payload)

            @self.socketio.on("disconnect")
            def handle_disconnect(*args, **kwargs):
                return None

            @self.socketio.on("subscribe")
            def handle_subscribe(*args, **kwargs):
                data = args[-1] if args and isinstance(args[-1], dict) else kwargs
                table_name = str(data.get("table", "")).upper()
                if not table_name:
                    self._emit("error", {"message": "Missing table name"})
                    return
                if self.adapter == "flask_socketio" and join_room is not None:
                    join_room(table_name)
                elif hasattr(self.socketio, "enter_room") and args:
                    self._safe_call(self.socketio.enter_room, args[0], table_name)
                self._emit("subscribed", {"table": table_name, "message": f"Subscribed to {table_name} updates"})

            @self.socketio.on("unsubscribe")
            def handle_unsubscribe(*args, **kwargs):
                data = args[-1] if args and isinstance(args[-1], dict) else kwargs
                table_name = str(data.get("table", "")).upper()
                if not table_name:
                    self._emit("error", {"message": "Missing table name"})
                    return
                if self.adapter == "flask_socketio" and leave_room is not None:
                    leave_room(table_name)
                elif hasattr(self.socketio, "leave_room") and args:
                    self._safe_call(self.socketio.leave_room, args[0], table_name)
                self._emit("unsubscribed", {"table": table_name, "message": f"Unsubscribed from {table_name}"})
        except Exception:
            return

    def _emit(self, event: str, payload: Dict[str, Any], room: Optional[str] = None):
        if not self.enabled or not self.socketio:
            return

        target = room or payload.get("table")

        if hasattr(self.socketio, "emit"):
            for kwargs in ({"room": target}, {"to": target}, {}):
                if not target and kwargs:
                    continue
                if self._safe_call(self.socketio.emit, event, payload, **kwargs):
                    return

        if hasattr(self.socketio, "publish"):
            channel = target or event
            result = self.socketio.publish(channel, {"event": event, "data": payload})
            self._run_maybe_async(result)
            return

        if hasattr(self.socketio, "broadcast"):
            for args in ((event, payload, target), (event, payload), (payload,)):
                try:
                    result = self.socketio.broadcast(*args)
                    self._run_maybe_async(result)
                    return
                except TypeError:
                    continue

        if hasattr(self.socketio, "send_json"):
            result = self.socketio.send_json({"event": event, "data": payload})
            self._run_maybe_async(result)
            return

        if hasattr(self.socketio, "send"):
            result = self.socketio.send({"event": event, "data": payload})
            self._run_maybe_async(result)

    def broadcast_insert(self, table_name: str, recid: int, data: Optional[Dict[str, Any]] = None):
        if not self.enabled:
            return

        table_upper = table_name.upper()
        simple_notification = {
            "action": "insert",
            "table": table_name,
            "recid": recid
        }
        self._emit("db_notification", simple_notification, room=table_upper)

        if data:
            full_notification = {
                "action": "insert",
                "table": table_name,
                "recid": recid,
                "data": data
            }
            self._emit("db_data_sync", full_notification, room=table_upper)

    def broadcast_update(self, table_name: str, recid: int, data: Optional[Dict[str, Any]] = None):
        if not self.enabled:
            return

        table_upper = table_name.upper()
        simple_notification = {
            "action": "update",
            "table": table_name,
            "recid": recid
        }
        self._emit("db_notification", simple_notification, room=table_upper)

        if data:
            full_notification = {
                "action": "update",
                "table": table_name,
                "recid": recid,
                "data": data
            }
            self._emit("db_data_sync", full_notification, room=table_upper)

    def broadcast_delete(self, table_name: str, recid: int):
        if not self.enabled:
            return

        table_upper = table_name.upper()
        notification = {
            "action": "delete",
            "table": table_name,
            "recid": recid
        }
        self._emit("db_notification", notification, room=table_upper)

    def broadcast_batch(self, table_name: str, action: str, count: int):
        if not self.enabled:
            return

        table_upper = table_name.upper()
        notification = {
            "action": f"batch_{action}",
            "table": table_name,
            "affected_count": count
        }
        self._emit("db_notification", notification, room=table_upper)

''' [END CODE] Project: SQLManager Version 4.0 / made by: Nicolas Santos / created: 12/03/2026 '''
