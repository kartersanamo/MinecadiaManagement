import discord

from core.config import get_settings


class AdminLogService:
    @staticmethod
    async def send(client, embed: discord.Embed) -> None:
        settings = get_settings()
        guild = client.get_guild(settings["GUILD_ID"])
        channel = guild.get_channel(settings["ADMIN_LOGS"])
        await channel.send(embed=embed)


admin_log = AdminLogService.send
