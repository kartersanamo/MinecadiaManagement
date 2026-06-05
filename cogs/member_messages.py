"""Roll up guild message activity by day (all members)."""
from __future__ import annotations

import logging

from discord.ext import commands
import discord

from core.analytics import logger as analytics

_log = logging.getLogger("analytics.member_messages")


class MemberMessages(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not analytics:
            return
        if message.author.bot or not message.guild:
            return
        try:
            analytics.record_member_message(
                str(message.author.id),
                len(message.content or ""),
            )
        except Exception as exc:
            _log.debug("record_member_message failed: %s", exc)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(MemberMessages(client))
