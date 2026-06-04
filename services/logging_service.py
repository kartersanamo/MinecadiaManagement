# migrated from domain/logging.py
import discord

from core.config import get_settings


async def admin_log(client, embed: discord.Embed):
    settings = get_settings()
    guild = client.get_guild(settings["GUILD_ID"])
    channel = guild.get_channel(settings["ADMIN_LOGS"])
    await channel.send(embed=embed)
