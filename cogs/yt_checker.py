import os

from discord.ext import commands, tasks
from discord import app_commands
from typing import Literal
import discord
import json

from googleapiclient.discovery import build

from core.config import get_data
from core.loggers import log_tasks
from ui.views.approval_view import ApprovalView


class YTChecker(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.data = get_data()
        api_key = os.getenv("YOUTUBE_API_KEY") or self.data.get("YOUTUBE_API_KEY")
        if not api_key:
            log_tasks.warning(
                "YOUTUBE_API_KEY is not set; videochecker task will not run API calls"
            )
            self.youtube = None
        else:
            self.youtube = build("youtube", "v3", developerKey=api_key)
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.videochecker.start()

    @tasks.loop(minutes=10)
    async def videochecker(self):
        if self.youtube is None:
            return
        try:
            with open("assets/yt_info.json", 'r+') as f:
                data = json.load(f)
                for video in data.keys():
                    if 'latest_video' not in data[str(video)] or data[str(video)]['latest_video'] == "N/A":
                        continue
                    part_string='contentDetails,statistics,snippet'
                    response = self.youtube.channels().list(
                        part=part_string,
                        id=data[str(video)]['channel_ID']
                    ).execute()
                    response2 = self.youtube.playlistItems().list(
                        part='contentDetails',
                        playlistId = response['items'][0]['contentDetails']['relatedPlaylists']['uploads'],
                        maxResults = 50
                    ).execute() 
                    recentVideoID = response2['items'][0]['contentDetails']['videoId']
                    if data[str(video)]['latest_video']==recentVideoID:
                        continue
                    response3 = self.youtube.videos().list(
                        part="snippet,contentDetails,statistics",
                        id=recentVideoID
                    ).execute()
                    guild = self.client.get_guild(self.data['GUILD_ID'])
                    approval_channel: discord.TextChannel = guild.get_channel(self.data['APPROVAL_CHANNEL_ID'])
                    community_videos_channel: discord.TextChannel = guild.get_channel(self.data['COMMUNITY_VIDEOS_CHANNEL_ID'])
                    approval_embed: discord.Embed = discord.Embed(
                        title = "New Video Request",
                        description = f"Would you like to post the following video to {community_videos_channel.mention}?\nPlease select an option below.",
                        color = discord.Color.from_str(self.data["EMBED_COLOR"])
                    )
                    video_embed = discord.Embed(title = f"New Video By {video}!",
                                        color = discord.Color.from_str(self.data['EMBED_COLOR']),
                                        description = f"[{response3['items'][0]['snippet']['title']}](https://youtube.com/watch?v={recentVideoID})")
                    try:
                        video_embed.set_image(url = response3['items'][0]['snippet']['thumbnails']['maxres']['url'])
                    except:
                        try:
                            video_embed.set_image(url = response3['items'][0]['snippet']['thumbnails']['sddefault']['url'])
                        except:
                            pass
                    
                    await approval_channel.send(
                        embeds = [
                                approval_embed, 
                                video_embed
                            ],
                        view = ApprovalView(video)
                        )
                    data[video]['latest_video'] = recentVideoID
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
        except Exception as e:
            log_tasks.error(f"videochecker failed: {e}")
        
    @app_commands.command(name = "task", description = "Edit the YT Checker Task")
    async def task(self, interaction: discord.Interaction, option: Literal['Restart', 'Start', 'Stop'] = 'Restart'):
        if option == 'Restart':
            self.videochecker.restart()
            await interaction.response.send_message("`✅` Success! The YT Checker Task has been restarted.")
        elif option == 'Start':
            self.videochecker.start()
            await interaction.response.send_message("`✅` Success! The YT Checker Task has been started.")
        elif option == 'Stop':
            self.videochecker.cancel()
            await interaction.response.send_message("`✅` Success! The YT Checker Task has been stopped.")


async def setup(client:commands.Bot) -> None:
  await client.add_cog(YTChecker(client))