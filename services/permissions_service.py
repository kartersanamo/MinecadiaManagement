# migrated from domain/permissions.py
import discord

from core.config import get_settings


async def is_staff(user: discord.Member):
    settings = get_settings()
    return any(role.name in settings["STAFF_ROLES"] for role in user.roles)


async def is_admin(user: discord.Member):
    settings = get_settings()
    return any(role.name in settings["ADMIN_ROLES"] for role in user.roles)
