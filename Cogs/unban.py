from discord.ext import commands
from discord import app_commands
import discord
import json

with open("Assets/config.json", "r") as file:
    data = json.load(file)

class Unban(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
  
    with open("Assets/config.json", "r") as file:
        self.data = json.load(file)

  @app_commands.command(name="unban", description="Unbans a user from the discord")
  @app_commands.checks.has_any_role(*data["ADMIN_ROLES"])
  @app_commands.describe(user="The ID of the user to unban from the discord", reason="The reason for unbanning the user from the discord")
  async def unban(self, interaction: discord.Interaction, user: str, reason:str=""):
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message("Attempting to unban user...")

    try:
      user = await self.client.fetch_user(int(user))

    except Exception as e:
      return await interaction.edit_original_response(content="Failed! Invalid user inputted.")
      
    reason = "None provided" if reason=="" else reason
      
    async for ban_entry in interaction.guild.bans():
      ban_user = ban_entry.user
      
      if(ban_user.name, ban_user.discriminator) == (user.name, user.discriminator):
        await interaction.guild.unban(user=user, reason=reason)
        return await interaction.edit_original_response(content=f"Sucessfully unbanned **{user}** for reason **{reason}**.")

    await interaction.edit_original_response(content=f"Failed! **{user}** is not banned.")

  @unban.error
  async def unban_error(self, interaction: discord.Interaction, error):
    await interaction.edit_original_response(content=error)
    
async def setup(client:commands.Bot) -> None:
  await client.add_cog(Unban(client))