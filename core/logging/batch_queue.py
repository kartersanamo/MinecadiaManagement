from __future__ import annotations

import discord
from discord.ext import tasks

from core.config import ConfigManager
from core.loggers import log_tasks
from core.logging.config_helpers import admin_logs_channel_id, flush_interval_seconds, logs_channel_id


class BatchQueue:
    def __init__(self, client: discord.Client):
        self.client = client
        self._main: list[discord.Embed] = []
        self._admin: list[discord.Embed] = []
        self._interval = max(15, flush_interval_seconds())
        self._flush_main.change_interval(seconds=self._interval)
        self._flush_admin.change_interval(seconds=self._interval)
        self._flush_main.start()
        self._flush_admin.start()

    def stop(self):
        self._flush_main.cancel()
        self._flush_admin.cancel()

    @tasks.loop(seconds=60)
    async def _flush_main(self):
        await self._flush("main")

    @tasks.loop(seconds=60)
    async def _flush_admin(self):
        await self._flush("admin")

    @_flush_main.before_loop
    @_flush_admin.before_loop
    async def _wait_ready(self):
        await self.client.wait_until_ready()

    def enqueue(self, embed: discord.Embed, *, admin: bool) -> None:
        if admin:
            self._admin.append(embed)
        else:
            self._main.append(embed)

    async def send_immediate(self, embed: discord.Embed, *, admin: bool) -> None:
        channel_id = admin_logs_channel_id() if admin else logs_channel_id()
        channel = self.client.get_channel(channel_id)
        if channel is None:
            guild = self.client.get_guild(int(ConfigManager.get("GUILD_ID") or 0))
            if guild:
                channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            log_tasks.warning("Log channel %s not found (admin=%s)", channel_id, admin)
            return
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as exc:
            log_tasks.error("Failed to send immediate log: %s", exc)

    async def _flush(self, kind: str) -> None:
        queue = self._admin if kind == "admin" else self._main
        if not queue:
            return

        channel_id = admin_logs_channel_id() if kind == "admin" else logs_channel_id()
        channel = self.client.get_channel(channel_id)
        if channel is None:
            guild = self.client.get_guild(int(ConfigManager.get("GUILD_ID") or 0))
            if guild:
                channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            log_tasks.warning("Log channel %s not found for flush (%s)", channel_id, kind)
            queue.clear()
            return

        batch = queue[:]
        queue.clear()
        for i in range(0, len(batch), 10):
            slice_ = batch[i : i + 10]
            try:
                await channel.send(embeds=slice_)
            except discord.HTTPException as exc:
                log_tasks.error("Failed to flush %s logs (%s embeds): %s", kind, len(slice_), exc)
