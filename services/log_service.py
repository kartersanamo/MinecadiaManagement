from __future__ import annotations

import discord

from core.logging.audit_resolver import AuditResolver
from core.logging.batch_queue import BatchQueue
from core.logging.embed_builder import build_embed, new_event_id
from core.logging.events import LogPayload
from core.logging.router import LogRouter
from repositories.audit_log_repository import AuditLogRepository


class LogService:
    def __init__(self, client: discord.Client):
        self.client = client
        self.queue = BatchQueue(client)
        self.audit = AuditResolver()

    async def record(self, payload: LogPayload, *, message_context=None) -> str:
        event_id = new_event_id()
        embed = build_embed(payload, event_id, self.client)

        await AuditLogRepository.insert(
            event_id=event_id,
            event_type=payload.event_type,
            category=payload.category.value,
            severity=payload.severity.value,
            guild_id=payload.guild_id,
            actor_id=payload.actor_id,
            target_id=payload.target_id,
            channel_id=payload.channel_id,
            source_bot=payload.source_bot,
            title=payload.display_title,
            summary=payload.summary,
            payload_json={
                "fields": payload.fields,
                "metadata": payload.metadata,
                "action": payload.action,
            },
        )

        if payload.skip_discord:
            return event_id

        admin = LogRouter.destination(payload, message_context) == "admin"
        if payload.immediate or admin:
            await self.queue.send_immediate(embed, admin=admin)
        else:
            self.queue.enqueue(embed, admin=admin)
        return event_id


_log_service: LogService | None = None


def get_log_service(client: discord.Client | None = None) -> LogService:
    global _log_service
    if _log_service is None:
        if client is None:
            raise RuntimeError("LogService not initialized")
        _log_service = LogService(client)
    return _log_service


def init_log_service(client: discord.Client) -> LogService:
    global _log_service
    _log_service = LogService(client)
    return _log_service
