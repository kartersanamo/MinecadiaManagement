from discord.ext import commands
from datetime import timedelta, datetime
import discord
import json
from domain.permissions import is_admin, is_staff

class Mentions(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.mention_timestamps = {}

        with open("assets/config.json", "r") as file:
            self.data = json.load(file)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if await is_admin(message.author) and message.author.id != 837793755838939157:
                return

            content = message.content
            if "<" in content and ">" in content and "@" in content:
                sub = content[content.index("<") + 2:content.index(">")]
                try:
                    mentioned_member = discord.utils.get(message.guild.members, id=int(sub))
                except:
                    mentioned_member = None

                if mentioned_member and await is_staff(mentioned_member):
                    now = datetime.utcnow()
                    user_id = message.author.id
                    if user_id not in self.mention_timestamps:
                        self.mention_timestamps[user_id] = []

                    one_hour_ago = now - timedelta(hours = 1)
                    self.mention_timestamps[user_id] = [
                        timestamp for timestamp in self.mention_timestamps[user_id] if timestamp > one_hour_ago
                    ]

                    self.mention_timestamps[user_id].append(now)

                    if len(self.mention_timestamps[user_id]) >= 3:
                        delta = timedelta(hours=1)
                        logs = message.guild.get_channel(918928087582916699)

                        try:
                            await message.author.timeout(delta, reason = "Auto Timeout for Excessive Staff Mentions")
                            embed = discord.Embed(
                                title="Staff Mentions Timeout",
                                description=f"`Member` {message.author}#{message.author.discriminator} ({message.author.id})",
                                color=discord.Color.from_str(self.data["EMBED_COLOR"]),
                                timestamp=now
                            )
                        except Exception as error:
                            embed = discord.Embed(
                                title="Staff Mentions Timeout (Error)",
                                description=f"`Member` {message.author}#{message.author.discriminator} ({message.author.id})\n`Error` {error}",
                                color=discord.Color.from_str(self.data["EMBED_COLOR"]),
                                timestamp=now
                            )

                        await logs.send(embed=embed)
                        del self.mention_timestamps[user_id]
                else:
                    pass
        except Exception:
            pass

async def setup(client:commands.Bot) -> None:
    await client.add_cog(Mentions(client))
