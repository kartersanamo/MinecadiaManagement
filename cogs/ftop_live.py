"""
Cog for F-Top live leaderboard commands.
Provides /ftop-live setup command to configure the live message channel.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from core.app import BotApp
from core.config import ConfigManager

if TYPE_CHECKING:
    pass

log = logging.getLogger("ftop_live_cog")


class FTopLive(commands.Cog):
    """Commands for managing the F-Top live leaderboard."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.app = BotApp.from_bot(bot)

    @app_commands.command(name="ftop-live", description="Manage F-Top live leaderboard")
    @app_commands.describe(action="Action to perform (setup, status, info)")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="setup", value="setup"),
            app_commands.Choice(name="status", value="status"),
            app_commands.Choice(name="info", value="info"),
        ]
    )
    async def ftop_live_cmd(
        self, interaction: discord.Interaction, action: str = "info"
    ) -> None:
        """Manage F-Top live leaderboard setup and status."""

        # Check admin permission
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ This command must be used in a server.",
                ephemeral=True,
            )
            return
        
        is_admin = await self.app.permissions.is_admin(interaction.user)
        if not is_admin:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True,
            )
            return

        if action == "setup":
            await self._setup(interaction)
        elif action == "status":
            await self._status(interaction)
        else:
            await self._info(interaction)

    async def _setup(self, interaction: discord.Interaction) -> None:
        """Setup F-Top live message in the current channel."""
        await interaction.response.defer()

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.followup.send(
                "❌ This command must be used in a text channel.",
                ephemeral=True,
            )
            return

        # Create initial message with placeholder data
        embed = discord.Embed(
            title="F-Top Live Leaderboard",
            description="`🔁` Awaiting response from server... ",
            color=discord.Color.gold(),
        )

        try:
            message = await interaction.channel.send(embed=embed)

            # Store in config (this is a simple approach; in production you'd want persistent storage)
            from services.ftop_service import FTopService

            service = FTopService(self.bot)
            # For now, we use a generic "default" server name for single-server setup
            await service.save_message_ids("default", interaction.channel.id, message.id)

            log.info(
                "F-Top live message setup in channel %s (message %s)",
                interaction.channel.id,
                message.id,
            )

            await interaction.followup.send(
                f"✅ F-Top live leaderboard message created in {interaction.channel.mention}\n"
                f"Message ID: `{message.id}`\n"
                f"The message will auto-update when the Minecraft server posts updates.",
                ephemeral=True,
            )
        except Exception as exc:
            log.exception("Failed to setup F-Top message: %s", exc)
            await interaction.followup.send(
                f"❌ Failed to create message: {str(exc)}",
                ephemeral=True,
            )

    async def _status(self, interaction: discord.Interaction) -> None:
        """Show current F-Top setup status."""
        await interaction.response.defer(ephemeral=True)

        from services.ftop_service import FTopService

        service = FTopService(self.bot)
        msg_ids = await service.get_message_ids("default")

        if not msg_ids:
            embed = discord.Embed(
                title="F-Top Live Status",
                description="❌ No F-Top live message configured",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="Setup",
                value="Run `/ftop-live setup` in the channel where you want the leaderboard.",
                inline=False,
            )
        else:
            channel_id, message_id = msg_ids
            channel = self.bot.get_channel(channel_id)
            channel_mention = (
                f"<#{channel_id}>" if channel else f"Unknown (ID: {channel_id})"
            )

            embed = discord.Embed(
                title="F-Top Live Status",
                description="✅ F-Top live message is configured",
                color=discord.Color.green(),
            )
            embed.add_field(name="Channel", value=channel_mention, inline=False)
            embed.add_field(name="Message ID", value=f"`{message_id}`", inline=False)
            embed.add_field(
                name="Status", value="Ready to receive updates", inline=False
            )

        await interaction.followup.send(embed=embed)

    async def _info(self, interaction: discord.Interaction) -> None:
        """Show F-Top live leaderboard info."""
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="F-Top Live Leaderboard",
            description="Displays real-time Top 5 factions across three categories",
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="📋 Categories",
            value="• 🏆 **F Top** — Base points\n"
            "• 🗺️ **Expeditions Top** — Expedition points\n"
            "• ⚔️ **PvP Top** — PvP points",
            inline=False,
        )

        embed.add_field(
            name="📊 Information",
            value="• Updates every ~10 minutes\n"
            "• Shows position changes (⬆️ rose, ⬇️ dropped, 🆕 new)\n"
            "• Displays value deltas in parentheses\n"
            "• Edits existing message (no spam)",
            inline=False,
        )

        embed.add_field(
            name="🔧 Setup",
            value="Run `/ftop-live setup` in the channel where you want the leaderboard to appear.",
            inline=False,
        )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Setup the FTopLive cog."""
    await bot.add_cog(FTopLive(bot))
