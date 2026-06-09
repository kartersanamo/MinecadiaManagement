from __future__ import annotations

from core.logging.events import LogPayload
from core.logging.permissions import is_admin_message


class LogRouter:
    @staticmethod
    def destination(payload: LogPayload, message_context=None) -> str:
        if payload.route_admin:
            return "admin"
        if message_context is not None and is_admin_message(message_context):
            return "admin"
        return "main"
