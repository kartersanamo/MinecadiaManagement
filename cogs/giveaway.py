from discord.ext import commands
import discord
from discord import app_commands

class Giveaway(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.giveaway_1d_menu = app_commands.ContextMenu(
            name = "Create Giveaway for 1d", 
            callback = self.create_giveaway_1d
        )
        self.client.tree.add_command(self.giveaway_1d_menu)

    async def create_giveaway_1d(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.send_message(content="Created a giveaway for 1d: " + message.content)

    async def cog_unload(self):
        self.client.tree.remove_command(self.giveaway_1d_menu.name, type=self.giveaway_1d_menu.type)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(Giveaway(client))
    await client.tree.sync()