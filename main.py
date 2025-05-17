from discord.ext import commands
from typing import Literal
import discord
import json

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='.', intents=discord.Intents().all())

        with open("MinecadiaManagement/Assets/config.json", "r") as file:
            self.data = json.load(file)

        self.cogslist = self.data["COGS_LIST"]

    async def setup_hook(self):
        for ext in self.cogslist:
            print("Loaded cog: " + ext)
            await self.load_extension("Cogs." + ext)

    async def on_ready(self):
        await client.change_presence(activity=discord.Game(name=self.data["PRESENCE"]))
        client.remove_command("help")
        print(" Logged in as " + self.user.name)
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands: {synced}")

client = Client()

@client.tree.command(name="management-reload", description="Reloads a Cog Class")
async def reload(interaction: discord.Interaction, cog:Literal["Unban", "Timeout", "Mentions", "Logs", "Ban", "MediaRemove", "MediaNote", "MediaList", "MediaDump", "MediaAccept"]):
    if interaction.user.id==837793755838939157:
        await client.reload_extension(f"Cogs.{cog.lower()}")
        await interaction.response.send_message(f"Successfully reloaded **{cog}.py**", ephemeral=True) 
    else:
        return await interaction.response.send_message(f"You cannot do this!", ephemeral=True)

@client.tree.context_menu(name = "Create Giveaway for 1d")
async def create_giveaway_1d(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_message(content = "Created a giveaway for 1d " + message.content)

with open('MinecadiaManagement/Assets/config.json', 'r') as f: 
    TOKEN = json.load(f)['TOKEN']

client.run(TOKEN)