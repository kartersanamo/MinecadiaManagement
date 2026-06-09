from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timezone
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from core.config import ConfigManager
from core.logging.config_helpers import admin_logs_channel_id, guild_id, logs_channel_id
from core.logging.embed_builder import format_channel, format_user, truncate
from core.logging.events import LogCategory, LogPayload, LogSeverity
from core.logging.permissions import is_admin_member
from repositories.audit_log_repository import AuditLogRepository
from services.log_service import get_log_service


def _admin_check(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    member = interaction.user
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    return is_admin_member(member, interaction.guild)


async def _require_admin(interaction: discord.Interaction) -> bool:
    if _admin_check(interaction):
        return True
    raise app_commands.CheckFailure("Administrator access required.")


_admin_check_decorator = app_commands.check(_require_admin)


class LogCommands(commands.GroupCog, group_name="log", group_description="Audit log search and management"):
    def __init__(self, client: commands.Bot):
        self.client = client

    def _rows_embed(self, title: str, rows: list[dict], *, page: int = 0) -> discord.Embed:
        embed = discord.Embed(title=title, color=discord.Color.from_str(str(ConfigManager.get("EMBED_COLOR"))))
        if not rows:
            embed.description = "No events found."
            return embed
        lines = []
        for row in rows:
            ts = f"<t:{row['created_at']}:R>"
            actor = f"<@{row['actor_id']}>" if row.get("actor_id") else "—"
            lines.append(
                f"`{row['event_id'][:8]}` **{row['title']}** · {row['source_bot']} · {actor} · {ts}"
            )
        embed.description = "\n".join(lines[:25])
        embed.set_footer(text=f"Page {page + 1} · {len(rows)} result(s)")
        return embed

    @_admin_check_decorator
    @app_commands.command(name="search", description="Search audit logs")
    @app_commands.describe(
        user="Filter by actor or target",
        event_type="Event type prefix (e.g. member.join)",
        channel="Filter by channel",
        source_bot="Source bot name",
        days="Look back N days (default 7)",
    )
    async def search(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
        event_type: str | None = None,
        channel: discord.abc.GuildChannel | None = None,
        source_bot: str | None = None,
        days: app_commands.Range[int, 1, 90] = 7,
    ):
        await interaction.response.defer(ephemeral=True)
        since = int(time.time()) - days * 86400
        gid = interaction.guild.id if interaction.guild else guild_id()
        if user:
            actor_rows = await AuditLogRepository.search(
                guild_id=gid, actor_id=user.id, event_type=event_type,
                channel_id=channel.id if channel else None, source_bot=source_bot,
                since=since, limit=25,
            )
            target_rows = await AuditLogRepository.search(
                guild_id=gid, target_id=user.id, event_type=event_type,
                channel_id=channel.id if channel else None, source_bot=source_bot,
                since=since, limit=25,
            )
            seen: set[str] = set()
            rows = []
            for row in actor_rows + target_rows:
                if row["event_id"] not in seen:
                    seen.add(row["event_id"])
                    rows.append(row)
            rows.sort(key=lambda r: r["created_at"], reverse=True)
            rows = rows[:25]
        else:
            rows = await AuditLogRepository.search(
                guild_id=gid,
                channel_id=channel.id if channel else None,
                event_type=event_type,
                source_bot=source_bot,
                since=since,
                limit=25,
            )
        embed = self._rows_embed("Audit Log Search", rows)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @_admin_check_decorator
    @app_commands.command(name="user", description="Last 25 events for a member")
    async def user(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id if interaction.guild else guild_id()
        actor_rows = await AuditLogRepository.search(guild_id=gid, actor_id=user.id, limit=25)
        target_rows = await AuditLogRepository.search(guild_id=gid, target_id=user.id, limit=25)
        seen = set()
        merged = []
        for row in actor_rows + target_rows:
            eid = row["event_id"]
            if eid not in seen:
                seen.add(eid)
                merged.append(row)
        merged.sort(key=lambda r: r["created_at"], reverse=True)
        embed = self._rows_embed(f"Events for {user.display_name}", merged[:25])
        await interaction.followup.send(embed=embed, ephemeral=True)

    @_admin_check_decorator
    @app_commands.command(name="channel", description="Last 25 events in a channel")
    async def channel(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id if interaction.guild else guild_id()
        rows = await AuditLogRepository.search(guild_id=gid, channel_id=channel.id, limit=25)
        embed = self._rows_embed(f"Events in {channel.name}", rows)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @_admin_check_decorator
    @app_commands.command(name="export", description="Export audit logs as CSV")
    @app_commands.describe(days="Export last N days (max 30)", max_rows="Maximum rows (max 5000)")
    async def export(
        self,
        interaction: discord.Interaction,
        days: app_commands.Range[int, 1, 30] = 7,
        max_rows: app_commands.Range[int, 100, 5000] = 5000,
    ):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id if interaction.guild else guild_id()
        now = int(time.time())
        since = now - days * 86400
        rows = await AuditLogRepository.export_rows(gid, since, now, limit=max_rows)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["event_id", "event_type", "category", "severity", "actor_id", "target_id",
             "channel_id", "source_bot", "title", "summary", "created_at"]
        )
        for row in rows:
            writer.writerow([
                row.get("event_id"), row.get("event_type"), row.get("category"), row.get("severity"),
                row.get("actor_id"), row.get("target_id"), row.get("channel_id"),
                row.get("source_bot"), row.get("title"), row.get("summary"), row.get("created_at"),
            ])
        buf.seek(0)
        filename = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
        await interaction.followup.send(
            content=f"Exported {len(rows)} row(s).",
            file=discord.File(io.BytesIO(buf.getvalue().encode()), filename=filename),
            ephemeral=True,
        )

    @_admin_check_decorator
    @app_commands.command(name="stats", description="Event counts by category/type")
    @app_commands.describe(days="7 or 30 day window")
    async def stats(self, interaction: discord.Interaction, days: Literal[7, 30] = 7):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild.id if interaction.guild else guild_id()
        since = int(time.time()) - days * 86400
        rows = await AuditLogRepository.stats(gid, since)
        embed = discord.Embed(
            title=f"Audit Stats ({days}d)",
            color=discord.Color.from_str(str(ConfigManager.get("EMBED_COLOR"))),
        )
        if not rows:
            embed.description = "No events in this period."
        else:
            lines = [f"**{r['category']}** · `{r['event_type']}` — {r['cnt']}" for r in rows[:30]]
            embed.description = "\n".join(lines)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @_admin_check_decorator
    @app_commands.command(name="test", description="Post sample embeds to log channels")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        logs = get_log_service(self.client)
        main_id = await logs.record(
            LogPayload(
                event_type="test.main",
                category=LogCategory.CUSTOM,
                title="Custom",
                action="Test Main",
                guild_id=interaction.guild.id if interaction.guild else guild_id(),
                actor_id=interaction.user.id,
                summary="Sample main-channel log embed.",
                fields={"Actor": format_user(interaction.user)},
            )
        )
        admin_id = await logs.record(
            LogPayload(
                event_type="test.admin",
                category=LogCategory.CUSTOM,
                title="Custom",
                action="Test Admin",
                guild_id=interaction.guild.id if interaction.guild else guild_id(),
                actor_id=interaction.user.id,
                summary="Sample admin-channel log embed.",
                route_admin=True,
                immediate=True,
            )
        )
        await interaction.followup.send(
            f"Posted test embeds.\nMain event: `{main_id[:8]}`\nAdmin event: `{admin_id[:8]}`\n"
            f"Channels: <#{logs_channel_id()}> · <#{admin_logs_channel_id()}>",
            ephemeral=True,
        )

    @_admin_check_decorator
    @app_commands.command(name="custom", description="Post a manual custom audit log")
    @app_commands.describe(
        title="Log title",
        description="Log description",
        severity="Severity level",
        user="Optional related user",
        channel="Optional related channel",
    )
    async def custom(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        severity: Literal["info", "warn", "critical"] = "info",
        user: discord.Member | None = None,
        channel: discord.abc.GuildChannel | None = None,
    ):
        await interaction.response.defer(ephemeral=True)
        sev = LogSeverity(severity)
        fields = {"Details": truncate(description)}
        if user:
            fields["Target"] = format_user(user)
        if channel:
            fields["Channel"] = format_channel(channel)
        event_id = await get_log_service(self.client).record(
            LogPayload(
                event_type="custom.manual",
                category=LogCategory.CUSTOM,
                title="Custom",
                action=title[:64],
                guild_id=interaction.guild.id if interaction.guild else guild_id(),
                actor_id=interaction.user.id,
                target_id=user.id if user else None,
                channel_id=channel.id if channel else None,
                severity=sev,
                summary=description,
                fields=fields,
            )
        )
        await interaction.followup.send(f"Logged event `{event_id[:8]}`.", ephemeral=True)

    @_admin_check_decorator
    @app_commands.command(name="lookup", description="Fetch a single event by ID")
    async def lookup(self, interaction: discord.Interaction, event_id: str):
        await interaction.response.defer(ephemeral=True)
        row = await AuditLogRepository.get_by_event_id(event_id.strip())
        if not row:
            await interaction.followup.send("Event not found.", ephemeral=True)
            return
        embed = discord.Embed(
            title=row["title"],
            description=truncate(row.get("summary")),
            color=discord.Color.from_str(str(ConfigManager.get("EMBED_COLOR"))),
            timestamp=datetime.fromtimestamp(row["created_at"], tz=timezone.utc),
        )
        embed.add_field(name="Event ID", value=f"`{row['event_id']}`", inline=False)
        embed.add_field(name="Type", value=f"`{row['event_type']}`", inline=True)
        embed.add_field(name="Category", value=row["category"], inline=True)
        embed.add_field(name="Source", value=row["source_bot"], inline=True)
        if row.get("actor_id"):
            embed.add_field(name="Actor", value=f"<@{row['actor_id']}>", inline=True)
        if row.get("target_id"):
            embed.add_field(name="Target", value=f"<@{row['target_id']}>", inline=True)
        if row.get("channel_id"):
            embed.add_field(name="Channel", value=f"<#{row['channel_id']}>", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(LogCommands(client))
