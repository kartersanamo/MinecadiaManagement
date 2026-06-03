import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google")

import logger  # noqa: F401 — configures logging before other imports

from Assets.functions import get_data, task, log_tasks, log_commands
from discord.ext import commands
from typing import Literal
import discord
from dotenv import load_dotenv

load_dotenv()


class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=discord.Intents().all())
        self.data: dict = get_data()
        self.cogslist: list[str] = self.data["COGS_LIST"]

    @task("Setup Cogs")
    async def setup_cogs(self):
        for ext in self.cogslist:
            log_tasks.info(f"Loaded cog {ext}.py")
            await self.load_extension("Cogs." + ext)
        import sys

        _minecadia = Path(__file__).resolve().parent.parent
        if str(_minecadia) not in sys.path:
            sys.path.insert(0, str(_minecadia))
        from _analytics.register import register_command_tracking

        await register_command_tracking(self)

    @task("Sync Command Tree")
    async def sync_command_tree(self):
        guild = discord.Object(id=self.data["GUILD_ID"])
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        log_tasks.info(
            f"Synced {len(synced)} commands to guild {self.data['GUILD_ID']}: "
            f"{[command.name for command in synced]}"
        )

    @task("Setup Hook")
    async def setup_hook(self):
        await self.setup_cogs()
        await self.sync_command_tree()

    @task("Logging in")
    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name=self.data["PRESENCE"]))
        self.remove_command("help")
        log_tasks.info(f"Logged in as {client.user} ({client.user.id})")

    async def on_command_error(self, ctx, error):
        log_commands.error(f"Command error: {error}")


client = Client()


@client.tree.command(name="management-reload", description="Reloads a Cog Class")
async def reload(
    interaction: discord.Interaction,
    cog: Literal[
        "Unban",
        "Timeout",
        "Mentions",
        "Logs",
        "Ban",
        "MediaRemove",
        "MediaNote",
        "MediaList",
        "MediaDump",
        "MediaAccept",
        "Analyze",
    ],
):
    if interaction.user.id == 837793755838939157:
        await client.reload_extension(f"Cogs.{cog.lower()}")
        log_commands.info(
            f"Reloaded cog {cog}.py by {interaction.user} ({interaction.user.id})"
        )
        await interaction.response.send_message(
            f"Successfully reloaded **{cog}.py**", ephemeral=True
        )
    else:
        await interaction.response.send_message("You cannot do this!", ephemeral=True)


@reload.error
async def reload_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    log_commands.error(f"/{interaction.command.name} error {error}")
    if interaction.response.is_done():
        await interaction.followup.send(content=str(error), ephemeral=True)
    else:
        await interaction.response.send_message(content=str(error), ephemeral=True)


@client.tree.context_menu(name="Create Giveaway for 1d")
async def create_giveaway_1d(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message(
        content="Created a giveaway for 1d " + message.content
    )


TOKEN = os.getenv("DISCORD_TOKEN") or client.data.get("TOKEN")
if not TOKEN:
    raise ValueError("Set DISCORD_TOKEN in .env")

if __name__ == "__main__":
    client.run(TOKEN)
