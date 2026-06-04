import discord

from core.config import get_settings


class PermissionService:
    @staticmethod
    async def is_staff(user: discord.Member) -> bool:
        settings = get_settings()
        return any(role.name in settings["STAFF_ROLES"] for role in user.roles)

    @staticmethod
    async def is_admin(user: discord.Member) -> bool:
        settings = get_settings()
        return any(role.name in settings["ADMIN_ROLES"] for role in user.roles)


is_staff = PermissionService.is_staff
is_admin = PermissionService.is_admin
