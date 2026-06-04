from discord.ext import commands

from core.config import ConfigLoader
from core.database import DatabasePool
from repositories.statistics_repository import StatisticsRepository
from services.statistics_service import StatisticsService


class BotApp:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = ConfigLoader.get()
        self.db = DatabasePool.get()
        self.statistics_repo = StatisticsRepository(self.db)
        self.statistics = StatisticsService(self.statistics_repo)

    @classmethod
    def from_bot(cls, bot: commands.Bot) -> "BotApp":
        return cls(bot)
