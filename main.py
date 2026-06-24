import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

import warnings
warnings.filterwarnings("ignore", category = FutureWarning, module = "google")

from discord import app_commands
from discord.ext import commands
import discord
from dotenv import load_dotenv
from core.app import BotApp
from core.config import ConfigManager
from core.decorators import task
from core.loggers import log_commands, log_tasks
from core.errors.setup import wire_bot

load_dotenv()


COG_FILES = [file.split(".")[0].title() for file in os.listdir("cogs/") if file.endswith(".py")]


class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = ".", intents = discord.Intents().all())
        wire_bot(self, bot_name="Management", log_commands=log_commands, log_tasks=log_tasks)

    @task("Setup Cogs")
    async def setup_cogs(self):
        for ext in COG_FILES:
            await self.load_extension("cogs." + ext.lower())
            log_tasks.info(f"Loaded cog {ext}.py")

    @task("Register Analytics")
    async def register_analytics(self):
        from core.analytics.register import register_command_tracking

        await register_command_tracking(self)
    
    @task("Update Presence")
    async def update_presence(self):
        presence = ConfigManager.get("PRESENCE")
        activity = discord.Game(name=presence)
        self._presence_activity = activity
        await client.change_presence(activity=activity)
        log_tasks.info(f"Updated the bot's presence to {presence}")

    @task("Remove Help")
    async def remove_help(self):
        client.remove_command("help")

    @task("Sync Command Tree")
    async def sync_command_tree(self):
        from core.guild_command_sync import sync_guild_commands

        stale_commands = [
            ("Create Giveaway for 1d", discord.AppCommandType.message),
        ]
        for name, cmd_type in stale_commands:
            self.tree.remove_command(name, type=cmd_type)

        await sync_guild_commands(
            self,
            config_guild_id=ConfigManager.get("GUILD_ID"),
            log=log_tasks,
            also_sync_global = False,
            clear_global_after_guild = True
        )

    @task("Setup Hook")
    async def setup_hook(self):
        from core.errors.setup import wire_bot_async_setup
        from services.log_service import init_log_service

        await wire_bot_async_setup(self, bot_name="Management", log_tasks=log_tasks)
        self.app = BotApp.from_bot(self)
        init_log_service(self)
        await self.setup_cogs()
        await self.register_analytics()

    async def on_connect(self):
        from core.liveness import mark_connected

        mark_connected()
        log_tasks.info("Discord gateway connected")

    async def on_disconnect(self):
        from core.liveness import mark_disconnected

        mark_disconnected()
        log_tasks.warning("Discord gateway disconnected — awaiting reconnect")

    async def on_resume(self):
        from core.liveness import mark_connected

        mark_connected()
        await self.update_presence()
        log_tasks.info("Bot connection resumed")

    @task("Logging in")
    async def on_ready(self):
        from assets.http.log_http import start_log_http

        await start_log_http(self)
        await self.update_presence()
        await self.remove_help()
        await self.sync_command_tree()
        log_tasks.info(f"Logged in as {client.user} ({client.user.id})")


client = Client()


@task("Management Reload Command", True)
async def management_reload_command(interaction: discord.Interaction, cog: str):
    if interaction.guild is None:
        return await interaction.response.send_message(content = "Commands cannot be ran in DMs!", ephemeral = True)
    if cog not in COG_FILES:
        await interaction.response.send_message(f"Invalid cog name **{cog}.py**", ephemeral = True)
        return
    await client.reload_extension(f"cogs.{cog.lower()}")
    await interaction.response.send_message(f"Successfully reloaded **{cog}.py**", ephemeral = True)

async def cog_autocomplete(_: discord.Interaction, current: str):
    return [
        app_commands.Choice(name = cog, value = cog)
        for cog in COG_FILES if current.lower() in cog.lower()
    ]

@client.tree.command(name = "management-reload", description = "Reloads a Cog Class")
@app_commands.autocomplete(cog = cog_autocomplete)
async def managementreload(interaction: discord.Interaction, cog: str):
    await management_reload_command(interaction, cog)

TOKEN = os.getenv("DISCORD_TOKEN") or client.data.get("TOKEN")
if not TOKEN:
    raise ValueError("Set DISCORD_TOKEN in .env")

if __name__ == "__main__":
    client.run(TOKEN)
