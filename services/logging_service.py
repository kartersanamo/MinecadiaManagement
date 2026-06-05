import discord

from core.config import ConfigManager


class AdminLogService:
    @staticmethod
    async def send(client, embed: discord.Embed) -> None:
        settings = ConfigManager.all()
        guild = client.get_guild(ConfigManager.get("GUILD_ID"))
        channel = guild.get_channel(ConfigManager.get("ADMIN_LOGS"))
        await channel.send(embed=embed)


admin_log = AdminLogService.send
