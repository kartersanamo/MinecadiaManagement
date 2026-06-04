from discord.ext import commands
from discord import app_commands
import pandas as pd
import discord
import os
import json
from core.database import execute

with open("assets/config.json", "r") as file:
    data = json.load(file)

class MediaDump(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
    
    with open("assets/config.json", "r") as file:
      self.data = json.load(file)

  @app_commands.command(name="media-dump", description="Dumps the Media Information")
  @app_commands.checks.has_any_role(*data["STAFF_ROLES"])
  async def mediadump(self, interaction: discord.Interaction):
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message("Beginning to dump media info...")

    rows = await execute("SELECT * FROM media")

    if not rows:
      return await interaction.edit_original_response(content="No media records found.")

    data_frame = pd.DataFrame(rows)
    temp_file = "media_dump_temp.csv"
    data_frame.to_csv(temp_file, index=False)

    await interaction.edit_original_response(content=None, attachments=[discord.File(temp_file)])
    os.remove(temp_file)

  @mediadump.error
  async def mediadump_error(self, interaction: discord.Interaction, error):
    await interaction.response.send_message(content=error, ephemeral=True)
    
async def setup(client:commands.Bot) -> None:
  await client.add_cog(MediaDump(client))