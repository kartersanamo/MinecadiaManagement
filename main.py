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
from core.config import get_data
from core.decorators import task
from core.loggers import log_tasks

load_dotenv()


COG_FILES = [file.split(".")[0].title() for file in os.listdir("cogs/") if file.endswith(".py")]


class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = ".", intents = discord.Intents().all())
        self.data: dict = get_data()

    @task("Setup Cogs")
    async def setup_cogs(self):
        for ext in COG_FILES:
            await self.load_extension("cogs." + ext.lower())
            log_tasks.info(f"Loaded cog {ext}.py")

    @task("Register Analytics")
    async def register_analytics(self):
        import sys

        _minecadia = Path(__file__).resolve().parent.parent
        if str(_minecadia) not in sys.path:
            sys.path.insert(0, str(_minecadia))
        from _analytics.register import register_command_tracking

        await register_command_tracking(self)
    
    @task("Update Presence")
    async def update_presence(self):
        presence = self.data["PRESENCE"]
        await client.change_presence(activity = discord.Game(name = presence))
        log_tasks.info(f"Updated the bot's presence to {presence}")

    @task("Remove Help")
    async def remove_help(self):
        client.remove_command("help")

    @task("Sync Command Tree")
    async def sync_command_tree(self):
        commands: list[discord.app_commands.AppCommand] = await self.tree.sync()
        command_list: str = ', '.join([command.name for command in commands])
        log_tasks.info(f"Synced {len(commands)} commands {command_list}")

    @task("Setup Hook")
    async def setup_hook(self):
        self.app = BotApp.from_bot(self)
        await self.setup_cogs()
        await self.register_analytics()

    @task("Logging in")
    async def on_ready(self):
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

@managementreload.error
async def managementreload_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    await interaction.followup.send(content = error, ephemeral = True) if interaction.response.is_done() else await interaction.response.send_message(content = error, ephemeral = True)

TOKEN = os.getenv("DISCORD_TOKEN") or client.data.get("TOKEN")
if not TOKEN:
    raise ValueError("Set DISCORD_TOKEN in .env")

if __name__ == "__main__":
    client.run(TOKEN)
