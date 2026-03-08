from Assets.functions import execute
from Assets.functions import get_embed_logo_url
from discord.ext import commands
from discord import app_commands
from typing import Literal
import discord
import json

with open("Assets/config.json", "r") as file:
    data = json.load(file)

class MediaList(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
    
    with open("Assets/config.json", "r") as file:
      self.data = json.load(file)

  @app_commands.command(name="media-list", description="Lists all of the users with Media Rank")
  @app_commands.checks.has_any_role(*data["STAFF_ROLES"])
  @app_commands.describe(past="Specify if you want to see all of the past Media")
  async def medialist(self, interaction: discord.Interaction, past: Literal["Yes"] = None):
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message("Gathering a list of media...")

    query = "SELECT * FROM media" if past else "SELECT * FROM media WHERE `active`='True'"
    rows = await execute(query)

    rank_to_emoji = {
        "YouTuber": "Minecadia_Arkham_Supergirl",
        "Streamer": "Minecadia_Arkham_Superman",
        "TikToker": "Minecadia_Arkham_Batman",
    }

    desc = ""
    for row in rows:
      user = discord.utils.get(interaction.guild.members, id=int(row["userID"]))

      emoji_name = rank_to_emoji.get(row['rank'], '')
      emoji = discord.utils.get(interaction.guild.emojis, name=emoji_name)
        
      if user:
        desc += str(emoji) 
        desc += f"**{user.display_name}**" if row['active'] == "True" else user.display_name
        desc += f" ({row['rank']})\n"

    embed = discord.Embed(title="List of All Media",
                          description=desc,
                          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
    )
    logo_url = get_embed_logo_url(self.data["LOGO"])
    embed.set_footer(text=self.data["FOOTER"], icon_url=logo_url)

    await interaction.edit_original_response(content=None, embed=embed)
  
  @medialist.error
  async def medialist_error(self, interaction: discord.Interaction, error):
    await interaction.response.send_message(content=error, ephemeral=True)

async def setup(client:commands.Bot) -> None:
  await client.add_cog(MediaList(client))