from discord.ext import commands
from discord import app_commands
from datetime import timedelta
from typing import Literal
import discord
import json

with open("MinecadiaManagement/Assets/config.json", "r") as file:
    data = json.load(file)

class Timeout(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
  
    with open("MinecadiaManagement/Assets/config.json", "r") as file:
      self.data = json.load(file)

  @app_commands.command(name="timeout", description="Times out a user in the discord")
  @app_commands.describe(user="The user to timeout in the discord", duration="How long to timeout the user for", reason="The reason for timing out the user")
  async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: Literal['60 secs', '5 mins', '10 mins', '1 hour', '1 day', '1 week'], reason: str = ""):
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message("Attempting to time out user...")
    split = duration.split(" ")

    seconds = (
        60 if split[0] == '60' else
        5 * 60 if split[0] == '5' else
        10 * 60 if split[0] == '10' else
        60 * 60 if split[0] == '1' and split[1] == 'hour' else
        60 * 60 * 24 if split[0] == '1' and split[1] == 'day' else
        60 * 60 * 24 * 7
    )

    delta = timedelta(seconds=seconds)
    reason = "None provided" if reason == "" else reason
    if user.is_timed_out():
      return await interaction.edit_original_response(content=f"Failed! **{user}** is already timed out; which ends <t:{int(user.timed_out_until.timestamp())}:R>")
        
    await user.timeout(delta, reason=reason)
    await interaction.edit_original_response(content=f"Successfully timed out **{user.mention}** for **{duration.title()}** for reason **{reason}**.")
  
  @timeout.error
  async def timeout_error(self, interaction: discord.Interaction, error):
    await interaction.edit_original_response(content=error)
    
async def setup(client:commands.Bot) -> None:
  await client.add_cog(Timeout(client))