"""
Service for managing F-Top live leaderboard Discord messages.
Handles message creation, editing, and formatting with position changes.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass

import discord
from core.database import DatabasePool

if TYPE_CHECKING:
    from discord.ext import commands

log = logging.getLogger("ftop_service")


@dataclass
class LeaderboardEntry:
    """Represents a single leaderboard entry."""
    position: int
    name: str
    value: float
    delta: float
    previous_position: Optional[int]
    position_delta: int


class FTopService:
    """Service for updating F-Top live leaderboard messages."""

    def __init__(self, bot: "commands.Bot"):
        self.bot = bot
        self.db = DatabasePool.get()

    async def get_message_ids(self, server: str) -> Optional[tuple[int, int]]:
        """Get stored channel_id and message_id for a server."""
        rows = await self.db.execute(
            "SELECT channel_id, message_id FROM ftop_live_messages WHERE server = %s",
            (server,),
        )
        if rows:
            return (rows[0]["channel_id"], rows[0]["message_id"])
        return None

    async def save_message_ids(
        self, server: str, channel_id: int, message_id: int
    ) -> None:
        """Save or update channel_id and message_id for a server."""
        await self.db.execute(
            """
            INSERT INTO ftop_live_messages (server, channel_id, message_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE channel_id = %s, message_id = %s
            """,
            (server, channel_id, message_id, channel_id, message_id),
        )

    async def update_ftop_message(
        self,
        server: str,
        updated_at: int | float,
        ftop_data: list[dict],
        expeditions_data: list[dict],
        pvp_data: list[dict],
    ) -> None:
        """Update or create the F-Top live leaderboard message."""
        
        # Parse leaderboard entries
        ftop = [self._parse_entry(e) for e in ftop_data[:5]]
        expeditions = [self._parse_entry(e) for e in expeditions_data[:5]]
        pvp = [self._parse_entry(e) for e in pvp_data[:5]]

        # Build the embed
        embed = self._build_embed(server, updated_at, ftop, expeditions, pvp)

        # Get stored message IDs
        msg_ids = await self.get_message_ids(server)

        if msg_ids:
            await self._edit_message(msg_ids[0], msg_ids[1], embed, server)
        else:
            await self._create_message(server, embed)

    def _parse_entry(self, data: dict) -> LeaderboardEntry:
        """Parse a leaderboard entry from JSON."""
        return LeaderboardEntry(
            position=int(data.get("position", 0)),
            name=str(data.get("name", "Unknown")),
            value=float(data.get("value", 0.0)),
            delta=float(data.get("delta", 0.0)),
            previous_position=int(data["previousPosition"])
            if data.get("previousPosition") is not None
            else None,
            position_delta=int(data.get("positionDelta", 0)),
        )

    def _build_embed(
        self,
        server: str,
        updated_at: int | float,
        ftop: list[LeaderboardEntry],
        expeditions: list[LeaderboardEntry],
        pvp: list[LeaderboardEntry],
    ) -> discord.Embed:
        """Build the F-Top leaderboard embed."""
        
        # Convert timestamp to datetime
        dt = datetime.fromtimestamp(updated_at / 1000.0)
        timestamp_str = f"<t:{int(updated_at / 1000)}:R>"
        
        embed = discord.Embed(
            title=f"{server} Live Tops",
            description="Updated every 10 minutes",
            color=discord.Color.gold(),
            timestamp=dt,
        )

        # Add F Top section
        ftop_text = self._format_category(ftop)
        embed.add_field(name="🏆 F Top", value=ftop_text or "No data", inline=False)

        # Add Expeditions Top section
        expeditions_text = self._format_category(expeditions)
        embed.add_field(
            name="🗺️ Expeditions Top",
            value=expeditions_text or "No data",
            inline=False,
        )

        # Add PvP Top section
        pvp_text = self._format_category(pvp)
        embed.add_field(name="⚔️ PvP Top", value=pvp_text or "No data", inline=False)

        # Add last updated timestamp as final line with small text
        embed.add_field(
            name="\u200b",  # Zero-width space for field name
            value=f"-# Last updated: {timestamp_str}",
            inline=False,
        )
        return embed

    def _format_category(self, entries: list[LeaderboardEntry]) -> str:
        """Format a category's entries into readable text."""
        if not entries:
            return "No data"

        lines = []
        for entry in entries:
            line = self._format_entry(entry)
            lines.append(line)

        return "\n".join(lines)

    def _format_entry(self, entry: LeaderboardEntry) -> str:
        """Format a single leaderboard entry with position changes."""
        # Format value with delta
        value_str = f"{entry.value:,.0f}"
        delta_sign = "+" if entry.delta >= 0 else ""
        value_with_delta = f"{value_str} ({delta_sign}{entry.delta:,.0f})"

        # Format position indicator
        position_indicator = ""
        if entry.previous_position is None:
            # New entry
            position_indicator = " 🆕"
        elif entry.position_delta > 0:
            # Rose in rankings
            position_indicator = f" ⬆️ (↑{entry.position_delta})"
        elif entry.position_delta < 0:
            # Dropped in rankings
            position_indicator = f" ⬇️ (↓{abs(entry.position_delta)})"
        # else: unchanged position, no indicator

        return f"{entry.position}. **{entry.name}** {value_with_delta}{position_indicator}"

    async def _create_message(self, server: str, embed: discord.Embed) -> None:
        """Create a new F-Top message in the configured channel."""
        from core.config import ConfigManager

        channel_id = ConfigManager.get("FTOP_LIVE_CHANNEL_ID")
        if not channel_id:
            log.warning("FTOP_LIVE_CHANNEL_ID not configured")
            return

        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                log.error("F-Top channel not found: %s", channel_id)
                return

            if not isinstance(channel, discord.TextChannel):
                log.error("F-Top channel is not a text channel: %s", channel_id)
                return

            message = await channel.send(embed=embed)
            await self.save_message_ids(server, channel.id, message.id)
            log.info("Created new F-Top message for server: %s", server)
        except Exception as exc:
            log.exception("Failed to create F-Top message: %s", exc)

    async def _edit_message(
        self, channel_id: int, message_id: int, embed: discord.Embed, server: str
    ) -> None:
        """Edit an existing F-Top message."""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                log.warning("F-Top channel not found, will recreate: %s", channel_id)
                await self._create_message(server, embed)
                return

            if not isinstance(channel, discord.TextChannel):
                log.error("F-Top channel is not a text channel: %s", channel_id)
                return

            message = await channel.fetch_message(message_id)
            await message.edit(embed=embed)
            log.debug("Updated F-Top message for server: %s", server)
        except discord.NotFound:
            log.warning(
                "F-Top message not found (deleted?), will recreate: %s/%s",
                channel_id,
                message_id,
            )
            await self._create_message(server, embed)
        except Exception as exc:
            log.exception("Failed to edit F-Top message: %s", exc)
