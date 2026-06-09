import discord

from core.config import ConfigManager
from core.database import DatabasePool
from repositories.statistics_repository import StatisticsRepository
from services.embed_service import EmbedService
from services.log_service import get_log_service
from services.permission_service import PermissionService
from services.statistics_service import StatisticsService


class BotApp:
    def __init__(self, bot):
        self.bot = bot
        self.settings = ConfigManager.all()
        self.db = DatabasePool.get()
        self.statistics_repo = StatisticsRepository(self.db)
        self.statistics = StatisticsService(self.statistics_repo)
        self.permissions = PermissionService()
        self.embeds = EmbedService()

    @property
    def logs(self):
        return get_log_service(self.bot)

    @classmethod
    def from_bot(cls, bot) -> "BotApp":
        return cls(bot)
