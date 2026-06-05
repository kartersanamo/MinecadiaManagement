import discord

from core.config import ConfigManager


class ApprovalView(discord.ui.View):
    def __init__(self, youtuber_name: str) -> None:
        self.youtuber_name: str = youtuber_name
        super().__init__(timeout = None)
    @discord.ui.button(emoji = "✅", custom_id = "approvalview_approve", style = discord.ButtonStyle.grey, row = 0)
    async def approve(self, interaction: discord.Interaction, Button: discord.ui.Button) -> None:
        await interaction.response.defer()
        video_embed: discord.Embed = interaction.message.embeds[1]
        community_videos: discord.TextChannel = interaction.guild.get_channel(ConfigManager.get("COMMUNITY_VIDEOS_CHANNEL_ID"))
        await community_videos.send(
            content = f"## A new video has been uploaded by {self.youtuber_name}!",
            embed = video_embed
        )
        after_embed: discord.Embed = discord.Embed(
            description = f"`✅` {interaction.user.mention} has approved a video by {self.youtuber_name}.",
            color = discord.Color.from_str(ConfigManager.get("EMBED_COLOR"))
        )
        await interaction.message.edit(
            embeds = [
                after_embed
            ],
            view = None
        )
    
    @discord.ui.button(emoji = "❌", custom_id = "approvalview_deny", style = discord.ButtonStyle.grey, row = 0)
    async def deny(self, interaction: discord.Interaction, Button: discord.ui.Button) -> None:
        await interaction.response.defer()
        after_embed: discord.Embed = discord.Embed(
            description = f"`❌` {interaction.user.mention} has denied a video by {self.youtuber_name}.",
            color = discord.Color.from_str(ConfigManager.get("EMBED_COLOR"))
        )
        await interaction.message.edit(
            embeds = [
                after_embed
            ],
            view = None
        )
