import discord

from core.config import ConfigManager


class PermissionService:
    @staticmethod
    async def is_staff(user: discord.Member) -> bool:
        return any(role.name in ConfigManager.get("STAFF_ROLES") for role in user.roles)

    @staticmethod
    async def is_admin(user: discord.Member) -> bool:
        return any(role.name in ConfigManager.get("ADMIN_ROLES") for role in user.roles)


is_staff = PermissionService.is_staff
is_admin = PermissionService.is_admin
