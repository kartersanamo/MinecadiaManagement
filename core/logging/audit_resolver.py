from __future__ import annotations

import time
from typing import TypeVar

import discord

T = TypeVar("T")


class AuditResolver:
    def __init__(self, ttl_seconds: float = 3.0):
        self._ttl = ttl_seconds
        self._cache: dict[tuple[int, str, int | None], tuple[float, discord.AuditLogEntry | None]] = {}

    async def latest(
        self,
        guild: discord.Guild,
        action: discord.AuditLogAction,
        *,
        target_id: int | None = None,
        limit: int = 6,
    ) -> discord.AuditLogEntry | None:
        key = (guild.id, action.name, target_id)
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and now - cached[0] < self._ttl:
            return cached[1]

        entry: discord.AuditLogEntry | None = None
        try:
            async for log_entry in guild.audit_logs(limit=limit, action=action):
                if target_id is None:
                    entry = log_entry
                    break
                tid = getattr(log_entry.target, "id", None)
                if tid == target_id:
                    entry = log_entry
                    break
        except (discord.Forbidden, discord.HTTPException):
            entry = None

        self._cache[key] = (now, entry)
        return entry

    async def member_update(self, member: discord.Member) -> discord.AuditLogEntry | None:
        return await self.latest(
            member.guild,
            discord.AuditLogAction.member_update,
            target_id=member.id,
        )

    async def message_delete(self, guild: discord.Guild, author_id: int) -> discord.AuditLogEntry | None:
        return await self.latest(
            guild,
            discord.AuditLogAction.message_delete,
            target_id=author_id,
        )

    async def bulk_message_delete(self, guild: discord.Guild) -> discord.AuditLogEntry | None:
        return await self.latest(guild, discord.AuditLogAction.message_bulk_delete)

    async def ban(self, guild: discord.Guild, user_id: int) -> discord.AuditLogEntry | None:
        return await self.latest(guild, discord.AuditLogAction.ban, target_id=user_id)

    async def kick(self, guild: discord.Guild, user_id: int) -> discord.AuditLogEntry | None:
        return await self.latest(guild, discord.AuditLogAction.kick, target_id=user_id)
