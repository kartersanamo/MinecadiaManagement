from discord.ext import commands
from discord import app_commands
from datetime import date
import discord
import json
from core.database import execute
from utils.embeds import get_embed_logo_url

with open("Assets/config.json", "r") as file:
    data = json.load(file)

class MediaRemove(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
  
    with open("Assets/config.json", "r") as file:
      self.data = json.load(file)

  @app_commands.command(name="media-remove", description="Removes a user's Media Rank")
  @app_commands.checks.has_any_role(*data["STAFF_ROLES"])
  @app_commands.describe(user="The user to remove the rank from", reason="The reason for removing this Media Rank")
  async def mediaremove(self, interaction: discord.Interaction, user: discord.Member, reason: str):
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message("Attempting to remove this user as media...")

    rows = await execute("SELECT * FROM media")
    isMedia = False
    notes = ""
    rank = ""
    for row in rows:
      if int(row["userID"]) == user.id and row["active"] == "True":
        isMedia = True
        notes = row['notes']
        rank = row['rank']
        break
    if not isMedia:
      return await interaction.edit_original_response(content="This user is not currently Media!")
    newnotes = f"{notes} {rank} - Removed on {date.today()} - {reason}--------"
    await execute(f"UPDATE media SET active='False', notes='{newnotes}' WHERE `userID`='{user.id}'")

    role = discord.utils.get(interaction.guild.roles, name="Media")
    await user.remove_roles(role)

    embed = discord.Embed(title="Media Removed",
                          description=f"**{interaction.user.display_name}** has removed **{user.display_name}**'s Media Rank for the following reason:\n{reason}",
                          color=discord.Color.from_str(data["EMBED_COLOR"])
    )
    logo_url = get_embed_logo_url(data["LOGO"])
    embed.set_footer(text=self.data["FOOTER"], icon_url=logo_url)

    await interaction.edit_original_response(embed=embed, content="Removed their roles! **Reminder** to remove their in-game permissions as well!")

  @mediaremove.error
  async def mediaremove_error(self, interaction: discord.Interaction, error):
    await interaction.response.send_message(content=error, ephemeral=True)

async def setup(client:commands.Bot) -> None:
  await client.add_cog(MediaRemove(client))