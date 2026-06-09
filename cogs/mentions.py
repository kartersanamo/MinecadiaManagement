from __future__ import annotations

from datetime import datetime, timedelta

import discord
from discord.ext import commands

from core.logging.events import LogCategory, LogPayload, LogSeverity
from core.logging.embed_builder import format_user
from services.log_service import get_log_service
from services.permission_service import is_admin, is_staff


class Mentions(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.mention_timestamps: dict[int, list[datetime]] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild:
                return
            if await is_admin(message.author) and message.author.id != 837793755838939157:
                return

            content = message.content
            if "<" not in content or ">" not in content or "@" not in content:
                return

            sub = content[content.index("<") + 2 : content.index(">")]
            try:
                mentioned_member = discord.utils.get(message.guild.members, id=int(sub))
            except Exception:
                mentioned_member = None

            if not mentioned_member or not await is_staff(mentioned_member):
                return

            now = datetime.utcnow()
            user_id = message.author.id
            if user_id not in self.mention_timestamps:
                self.mention_timestamps[user_id] = []

            one_hour_ago = now - timedelta(hours=1)
            self.mention_timestamps[user_id] = [
                ts for ts in self.mention_timestamps[user_id] if ts > one_hour_ago
            ]
            self.mention_timestamps[user_id].append(now)

            if len(self.mention_timestamps[user_id]) < 3:
                return

            delta = timedelta(hours=1)
            error_text = None
            try:
                await message.author.timeout(delta, reason="Auto Timeout for Excessive Staff Mentions")
            except Exception as error:
                error_text = str(error)

            await get_log_service(self.client).record(
                LogPayload(
                    event_type="moderation.staff_mention_timeout",
                    category=LogCategory.MODERATION,
                    title="Moderation",
                    action="Staff Mentions Timeout",
                    guild_id=message.guild.id,
                    actor_id=message.author.id,
                    channel_id=message.channel.id,
                    severity=LogSeverity.WARN if not error_text else LogSeverity.CRITICAL,
                    fields={
                        "Target": format_user(message.author),
                        "Channel": f"{message.channel.mention} (`{message.channel.id}`)",
                        "Details": error_text or "Auto-timeout applied (3 staff mentions within 1 hour)",
                    },
                )
            )
            del self.mention_timestamps[user_id]
        except Exception:
            pass


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Mentions(client))
