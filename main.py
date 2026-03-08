import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google")

from discord.ext import commands
from typing import Literal
import discord
import json
import os
from dotenv import load_dotenv
from Assets.functions import get_data

load_dotenv()

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='.', intents=discord.Intents().all())

        self.data = get_data()
        self.cogslist = self.data["COGS_LIST"]

    async def setup_hook(self):
        for ext in self.cogslist:
            print("Loaded cog: " + ext)
            await self.load_extension("Cogs." + ext)

        guild = discord.Object(id=self.data["GUILD_ID"])

        # Do not clear global commands here
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands to guild: {synced}")

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name=self.data["PRESENCE"]))
        self.remove_command("help")
        print(" Logged in as " + self.user.name)

client = Client()

@client.tree.command(name="management-reload", description="Reloads a Cog Class")
async def reload(interaction: discord.Interaction, cog:Literal["Unban", "Timeout", "Mentions", "Logs", "Ban", "MediaRemove", "MediaNote", "MediaList", "MediaDump", "MediaAccept", "Analyze"]):
    if interaction.user.id==837793755838939157:
        await client.reload_extension(f"Cogs.{cog.lower()}")
        await interaction.response.send_message(f"Successfully reloaded **{cog}.py**", ephemeral=True) 
    else:
        return await interaction.response.send_message(f"You cannot do this!", ephemeral=True)

@client.tree.context_menu(name = "Create Giveaway for 1d")
async def create_giveaway_1d(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message(content = "Created a giveaway for 1d " + message.content)

TOKEN = os.getenv('DISCORD_TOKEN') or client.data.get('TOKEN')
if not TOKEN:
    raise ValueError('Set DISCORD_TOKEN in .env')

client.run(TOKEN)