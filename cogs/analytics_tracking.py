"""Guild analytics: member events, voice time, server snapshots, command usage."""
from __future__ import annotations

import time

import discord
from discord.ext import commands, tasks

from core.analytics import logger as analytics
from core.config import ConfigManager


class AnalyticsTracking(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.guild_id = int(ConfigManager.get("GUILD_ID", 0))
        self._voice_started: dict[tuple[int, int], float] = {}
        self._ready_initialized = False

    async def cog_load(self) -> None:
        if not self.snapshot_loop.is_running():
            self.snapshot_loop.start()
        if not self.voice_flush_loop.is_running():
            self.voice_flush_loop.start()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._ready_initialized:
            return
        self._ready_initialized = True
        await self._seed_voice_sessions()
        await self._record_guild_snapshot()

    async def cog_unload(self) -> None:
        self.snapshot_loop.cancel()
        self.voice_flush_loop.cancel()

    def _record_voice_duration(
        self, user_id: int, channel_id: int, started: float
    ) -> None:
        elapsed = time.time() - started
        if elapsed < 0.5:
            return
        seconds = max(1, int(round(elapsed)))
        analytics.record_voice_seconds(user_id, channel_id, seconds)

    async def _seed_voice_sessions(self) -> None:
        """Track members already in voice when the bot starts."""
        guild = self.client.get_guild(self.guild_id)
        if not guild:
            return
        now = time.time()
        for channel in guild.voice_channels:
            for member in channel.members:
                if member.bot:
                    continue
                self._voice_started[(member.id, channel.id)] = now

    @tasks.loop(seconds=30)
    async def voice_flush_loop(self) -> None:
        """Persist voice time while members are still connected."""
        for (user_id, channel_id), started in list(self._voice_started.items()):
            elapsed = time.time() - started
            if elapsed >= 1:
                self._record_voice_duration(user_id, channel_id, started)
                self._voice_started[(user_id, channel_id)] = time.time()

    @voice_flush_loop.before_loop
    async def before_voice_flush(self) -> None:
        await self.client.wait_until_ready()

    async def _record_guild_snapshot(self) -> None:
        guild = self.client.get_guild(self.guild_id)
        if not guild:
            return
        online = sum(
            1
            for m in guild.members
            if m.status != discord.Status.offline and not m.bot
        )
        member_count = len(guild.members)
        analytics.record_online_sample(member_count, online)
        analytics.record_server_snapshot(
            member_count,
            online,
            guild.premium_tier,
            guild.premium_subscription_count or 0,
        )

    @tasks.loop(hours=1)
    async def snapshot_loop(self) -> None:
        await self._record_guild_snapshot()

    @snapshot_loop.before_loop
    async def before_snapshot(self) -> None:
        await self.client.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id != self.guild_id:
            return
        invite_code = None
        try:
            invites = await member.guild.invites()
            # Best-effort; exact invite requires audit log / invite tracking
            if invites:
                invite_code = invites[0].code
        except Exception:
            pass
        age_days = max(
            0,
            int((discord.utils.utcnow() - member.created_at).total_seconds() // 86400),
        )
        analytics.record_member_event(
            "join",
            member.id,
            invite_code=invite_code,
            account_age_days=age_days,
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != self.guild_id:
            return
        try:
            await member.guild.fetch_ban(member)
            return
        except discord.NotFound:
            pass
        analytics.record_member_event("leave", member.id)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.guild.id != self.guild_id or member.bot:
            return
        key = (member.id, before.channel.id if before.channel else 0)
        if before.channel and not after.channel:
            started = self._voice_started.pop((member.id, before.channel.id), None)
            if started:
                self._record_voice_duration(
                    member.id, before.channel.id, started
                )
        elif after.channel and not before.channel:
            self._voice_started[(member.id, after.channel.id)] = time.time()
        elif (
            before.channel
            and after.channel
            and before.channel.id != after.channel.id
        ):
            started = self._voice_started.pop((member.id, before.channel.id), None)
            if started:
                self._record_voice_duration(
                    member.id, before.channel.id, started
                )
            self._voice_started[(member.id, after.channel.id)] = time.time()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.application_command:
            return
        if not interaction.command:
            return
        name = interaction.command.qualified_name
        analytics.record_command(str(self.client.user.id), name)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(AnalyticsTracking(client))
