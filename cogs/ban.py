import datetime
from discord.ext import commands
from discord import app_commands
from typing import Literal
import discord
import json

with open("assets/config.json", "r") as file:
    data = json.load(file)

class Ban(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
  
  @app_commands.command(name="ban", description="Bans a user from this discord")
  @app_commands.checks.has_any_role(*ConfigManager.get("ADMIN_ROLES"))
  @app_commands.describe(user="The user to ban from the discord", can_appeal="How long until they can appeal their ban")
  async def ban(self, interaction: discord.Interaction, user: discord.Member, can_appeal: Literal['1 Week', '2 Weeks', '3 Weeks', '4 Weeks', '8 Weeks', '12 Weeks', '24 Weeks', '36 Weeks', '48 Weeks']):
    return await interaction.response.send_message(content = "Please manually ban or use the other `/ban` command!")
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message(content="Attempting to ban user...")
    role = interaction.guild.get_role(1184716835879403541)
    await user.add_roles(role)
    can_appeal = int(float(datetime.datetime.utcnow().timestamp())) + (int(can_appeal.split(' ')[0])*604800)
    async with await get_pool() as pool:
            async with pool.acquire() as mydb:
                async with mydb.cursor() as cursor:
                    await cursor.execute(f"INSERT INTO `bans` (`user_id`, `can_appeal`) VALUES ('{user.id}', '{can_appeal}')")
            pool.close()
            await pool.wait_closed()
    await interaction.edit_original_response(content=f"Successfully banned {user} for until <t:{can_appeal}:R>")

async def setup(client:commands.Bot) -> None:
  await client.add_cog(Ban(client))