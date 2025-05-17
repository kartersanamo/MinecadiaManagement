from Assets.functions import execute
from discord.ext import commands
from discord import app_commands
from typing import Literal
from datetime import date
import discord
import json

with open("MinecadiaManagement/Assets/config.json", "r") as file:
    data = json.load(file)

class MediaAccept(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client

    with open("MinecadiaManagement/Assets/config.json", "r") as file:
      self.data = json.load(file)

  @app_commands.command(name="media-accept", description="Accepts a new member as Media Rank")
  @app_commands.checks.has_any_role(*data["STAFF_ROLES"])
  @app_commands.describe(user="The user to accept as Media", sendmsg="Whether or not you would like to send the acceptance message")
  async def mediaaccept(self, interaction: discord.Interaction, user: discord.Member, rank:Literal["YouTuber", "Streamer", "TikToker"], sendmsg:Literal["No"]=None):
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message("Accepting this user as media...")

    result = await execute(f"SELECT * FROM media WHERE userID = '{user.id}'")
    if result:
      result = result[0]
      if result['active']=="True":
        return await interaction.edit_original_response(content="Failed! This member is already media!")
        
      old_notes = result["notes"]
      new_notes = f"{old_notes} {rank} - Accepted on {date.today()}--------"
      await execute(f"UPDATE media SET `active`='True', `notes`='{new_notes}', `rank`='{rank}' WHERE `userID`='{user.id}'")
    else:
      query = "INSERT INTO media (userID, active, rank, notes) VALUES (%s, %s, %s, %s)"
      await execute(query, (user.id, "True", rank, f"{rank} - Accepted on {date.today()}--------",))

    media_role = discord.utils.get(interaction.guild.roles, name="Media")
    await user.add_roles(media_role)

    if sendmsg != "No":
      channel = discord.utils.get(interaction.guild.channels, name="media-announcements")
      embed = discord.Embed(
          title="Congratulations!",
          description=  f"After reviewing your application. I am happy to inform you that you have been accepted for **{rank} Rank** (Media).\n \n"
                        f"Any media rank players who are caught cheating/hacking, being excessively toxic/discriminatory, or breaking server rules (discord & in-game) are subject to their rank being removed immediately.\n \n"
                        f"You must maintain appropriate behavior, remain active unless given notice (may do so by making a ticket explaining your absence if it is a bit long), and maintain views. Any type of disrespect or demands will result in the removal of the rank.\n \n"
                        f"Please review the channel called {channel.mention} for important additional information pertaining to the rules and requirements to maintain the rank. Additionally, we occasionally host giveaways in there as well, so always good to keep an eye on that channel! :slight_smile:\n \n"
                        f"Again, congratulations!",
          color=discord.Color.from_str(self.data["EMBED_COLOR"]),
      )
      embed.set_footer(text=self.data["FOOTER"], icon_url=self.data["LOGO"])

      await interaction.edit_original_response(content="Successfully accepted this user as media!")
      await interaction.channel.send(content=user.mention, embed=embed)

  @mediaaccept.error
  async def mediaaccept_error(self, interaction: discord.Interaction, error):
    await interaction.response.send_message(content=error, ephemeral=True)

async def setup(client:commands.Bot) -> None:
  await client.add_cog(MediaAccept(client))