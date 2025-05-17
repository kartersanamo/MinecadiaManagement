from Assets.functions import is_admin, is_staff 
from discord.ext import commands
from datetime import timedelta, datetime
import discord
import json

class Mentions(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.attempts = {}

        with open("MinecadiaManagement/Assets/config.json", "r") as file:
            self.data = json.load(file)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if await is_admin(message.author) and message.author.id != 837793755838939157:
                return

            content = message.content
            if "<" in content and ">" in content and "@" in content:
                sub = content[content.index("<") + 2:content.index(">")]
                mentioned_member = discord.utils.get(message.guild.members, id=int(sub))

                if await is_staff(mentioned_member):
                    self.attempts[message.author.id] = self.attempts.get(message.author.id, 0) + 1

                    if self.attempts[message.author.id] == 3:
                        delta = timedelta(seconds=3600)
                        logs = discord.utils.get(message.guild.channels, name="logs")

                        try:
                            await message.author.timeout(delta, reason="Auto Timeout for Staff Mentions")
                            embed = discord.Embed(title="Staff Mentions Timeout", description=f"`Member` {message.author}#{message.author.discriminator} ({message.author.id})", color=discord.Color.from_str(self.data["EMBED_COLOR"]), timestamp=datetime.utcnow())

                        except Exception as Error:
                            embed=discord.Embed(title="Staff Mentions Timeout   ", description=f"`Member` {message.author}#{message.author.discriminator} ({message.author.id})\n`Error` {Error}", color=discord.Color.from_str(self.data["EMBED_COLOR"]), timestamp=datetime.datetime.utcnow())
    
                        await logs.send(embed=embed)

                        del self.attempts[message.author.id]

                else:
                    if message.author.id in self.attempts:
                        del self.attempts[message.author.id]

            else:
                if message.author.id in self.attempts:
                    del self.attempts[message.author.id]

        except:
            pass

async def setup(client:commands.Bot) -> None:
  await client.add_cog(Mentions(client))