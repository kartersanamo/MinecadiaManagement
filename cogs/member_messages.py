"""Roll up guild message activity by day (all members)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from discord.ext import commands
import discord

_log = logging.getLogger("analytics.member_messages")

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from _analytics import logger as analytics
except ImportError:
    analytics = None


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
