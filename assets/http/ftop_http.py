"""
HTTP ingestion for Minecadia Factions F-Top live leaderboard updates.

POST /api/ftop-live
Headers: Authorization: Bearer {FTOP_LIVE_SECRET}
Body JSON:
  {
    "server": "ServerName",
    "updatedAt": 1710000000000,
    "ftop": [...],
    "expeditions": [...],
    "pvp": [...]
  }

Each array entry:
  {
    "position": 1,
    "name": "FactionTag",
    "value": 1234.0,
    "delta": 50.0,
    "previousPosition": 2,
    "positionDelta": 1
  }

Response: {"ok": true}
"""
from __future__ import annotations

import logging
import os
import json
from typing import TYPE_CHECKING, Any

from aiohttp import web

if TYPE_CHECKING:
    from discord.ext import commands

log = logging.getLogger("ftop_http")
_runner: web.AppRunner | None = None


def _api_secret() -> str | None:
    return os.environ.get("FTOP_LIVE_SECRET")


def _api_port() -> int:
    return int(os.environ.get("FTOP_HTTP_PORT", "8767"))


def _auth(request: web.Request) -> bool:
    secret = _api_secret()
    auth_header = request.headers.get("Authorization", "")
    return bool(secret and auth_header == f"Bearer {secret}")


async def start_ftop_http(bot: "commands.Bot") -> None:
    global _runner
    secret = _api_secret()
    if not secret:
        log.warning("FTOP_LIVE_SECRET not set — F-Top HTTP API disabled")
        return

    async def ftop_update(request: web.Request) -> web.Response:
        if not _auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        
        if not isinstance(body, dict):
            return web.json_response({"error": "Invalid payload"}, status=400)
        
        # Validate required fields
        server = body.get("server")
        updated_at = body.get("updatedAt")
        ftop = body.get("ftop")
        expeditions = body.get("expeditions")
        pvp = body.get("pvp")
        
        if not server or not isinstance(server, str):
            return web.json_response({"error": "Missing or invalid 'server'"}, status=400)
        
        if not updated_at or not isinstance(updated_at, (int, float)):
            return web.json_response({"error": "Missing or invalid 'updatedAt'"}, status=400)
        
        if not isinstance(ftop, list) or not isinstance(expeditions, list) or not isinstance(pvp, list):
            return web.json_response({"error": "Missing or invalid category arrays"}, status=400)
        
        try:
            from services.ftop_service import FTopService
            
            service = FTopService(bot)
            await service.update_ftop_message(
                server=server,
                updated_at=updated_at,
                ftop_data=ftop,
                expeditions_data=expeditions,
                pvp_data=pvp,
            )
            return web.json_response({"ok": True})
        except Exception as exc:
            log.exception("F-Top update failed: %s", exc)
            return web.json_response({"error": "Failed to update F-Top message"}, status=500)

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    app = web.Application()
    app.router.add_post("/api/ftop-live", ftop_update)
    app.router.add_get("/health", health)

    _runner = web.AppRunner(app)
    await _runner.setup()
    site = web.TCPSite(_runner, "0.0.0.0", _api_port())
    await site.start()
    log.info("F-Top HTTP API listening on 0.0.0.0:%s", _api_port())


async def stop_ftop_http() -> None:
    global _runner
    if _runner:
        await _runner.cleanup()
        _runner = None
