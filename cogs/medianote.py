from discord.ext import commands
from discord import app_commands
import discord
import json
from core.database import execute

with open("assets/config.json", "r") as file:
    data = json.load(file)

class MediaNote(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
  
    with open("assets/config.json", "r") as file:
      self.data = json.load(file)

  @app_commands.command(name="media-note", description="Adds a note to a Media Rank")
  @app_commands.checks.has_any_role(*data["STAFF_ROLES"])
  @app_commands.describe(user="The user to add the note on", note="The note to add onto the user's profile")
  async def medianote(self, interaction: discord.Interaction, user: discord.Member, note:str):
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message("Attempting to add media note...")

    rows = await execute("SELECT * FROM media WHERE userID = %s", (user.id,))
    row = rows[0]
    if not row:
      return await interaction.response.send_message("This user has never had media rank before!")
    notes = row.get('notes', '')
    new_notes = f'{notes} {note}--------'
    await execute("UPDATE media SET notes = %s WHERE userID = %s", (new_notes, user.id))

    embed = discord.Embed(title=f"Successfully added the following note to {user}",
                          description=note,
                          color=data["EMBED_COLOR"]
    )
    logo_url = self.client.app.embeds.get_logo_url(data["LOGO"])
    embed.set_footer(text=self.data["FOOTER"], icon_url=logo_url)

    await interaction.edit_original_response(content=None, embed=embed)


async def setup(client:commands.Bot) -> None:
  await client.add_cog(MediaNote(client))