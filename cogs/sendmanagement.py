from discord.ext import commands
from discord import app_commands
from typing import Literal
import discord
from core.config import ConfigManager


class SendManagement(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
    @app_commands.command(name="send-management", description="Sends a message prompt.")
    @app_commands.describe(option="The message that you'd wish to send")
    @app_commands.guild_only()
    async def send_management(self, interaction: discord.Interaction, option: Literal["Strikes"]):
        await interaction.response.send_message(content="Sending your message...", ephemeral=True)
        embeds = {
              "Strikes": [
                {"embed": discord.Embed(color=discord.Color.from_str(ConfigManager.get("EMBED_COLOR")), 
                                        description=("**Factions Strikes & DQs**\n"
                                                     "\n"
                                                      "Below you can find all of the strikes and DQs for this season of factions!\n")),
                  "view": None,
                  "image": "https://i.imgur.com/Mcp6YbL.png"
                }
              ]
        }
        chosen_embed = embeds.get(option, [])

        for embed in chosen_embed:
            embed_obj = embed['embed']
            if embed['image']:
               embed_obj.set_image(url=embed['image'])
            await interaction.channel.send(embed=embed_obj, view=embed['view'])
        await interaction.edit_original_response(content="Successfully sent your message!")



async def setup(client:commands.Bot) -> None:
    await client.add_cog(SendManagement(client))