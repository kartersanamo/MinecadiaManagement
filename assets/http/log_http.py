"""
HTTP ingestion for external Minecadia bots.

POST /api/logs
Headers: X-Log-Token: {MANAGEMENT_LOG_API_SECRET}
Body JSON:
  {
    "event_type": "account.sync",
    "title": "Account Synced",
    "summary": "optional description",
    "actor_id": 123,
    "target_id": 456,
    "channel_id": 789,
    "severity": "info|warn|critical",
    "metadata": {},
    "source_bot": "Utilities"
  }
Response: {"event_id": "uuid"}
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from aiohttp import web

from core.logging.config_helpers import guild_id
from core.logging.events import LogCategory, LogPayload, LogSeverity
from services.log_service import get_log_service

if TYPE_CHECKING:
    from discord.ext import commands

log = logging.getLogger("log_http")
_runner: web.AppRunner | None = None


def _api_secret() -> str | None:
    return os.environ.get("MANAGEMENT_LOG_API_SECRET")


def _api_port() -> int:
    return int(os.environ.get("LOG_HTTP_PORT", "8766"))


def _auth(request: web.Request) -> bool:
    secret = _api_secret()
    return bool(secret and request.headers.get("X-Log-Token") == secret)


def _severity(value: str | None) -> LogSeverity:
    try:
        return LogSeverity(value or "info")
    except ValueError:
        return LogSeverity.INFO


async def start_log_http(bot: "commands.Bot") -> None:
    global _runner
    secret = _api_secret()
    if not secret:
        log.warning("MANAGEMENT_LOG_API_SECRET not set — log HTTP API disabled")
        return

    async def ingest(request: web.Request) -> web.Response:
        if not _auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        if not isinstance(body, dict):
            return web.json_response({"error": "Invalid payload"}, status=400)

        event_type = str(body.get("event_type") or "custom.external")[:64]
        action = str(body.get("title") or body.get("action") or "External Event")[:64]
        summary = str(body.get("summary") or "")[:2000] or None
        source = str(body.get("source_bot") or "External")[:32]
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

        payload = LogPayload(
            event_type=event_type,
            category=LogCategory.CUSTOM,
            title="Custom",
            action=action,
            guild_id=int(body.get("guild_id") or guild_id()),
            severity=_severity(body.get("severity")),
            actor_id=int(body["actor_id"]) if body.get("actor_id") else None,
            target_id=int(body["target_id"]) if body.get("target_id") else None,
            channel_id=int(body["channel_id"]) if body.get("channel_id") else None,
            source_bot=source,
            summary=summary,
            metadata=metadata,
            fields={"Details": summary} if summary else {},
            route_admin=bool(body.get("route_admin")),
            immediate=bool(body.get("immediate")),
        )

        try:
            event_id = await get_log_service(bot).record(payload)
        except Exception as exc:
            log.exception("Log ingest failed: %s", exc)
            return web.json_response({"error": "Failed to record log"}, status=500)

        return web.json_response({"event_id": event_id})

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    app = web.Application()
    app.router.add_post("/api/logs", ingest)
    app.router.add_get("/health", health)

    _runner = web.AppRunner(app)
    await _runner.setup()
    site = web.TCPSite(_runner, "127.0.0.1", _api_port())
    await site.start()
    log.info("Log HTTP API listening on 127.0.0.1:%s", _api_port())


async def stop_log_http() -> None:
    global _runner
    if _runner:
        await _runner.cleanup()
        _runner = None
