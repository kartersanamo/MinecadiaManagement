# migrated from domain/permissions.py
import discord

from core.config import ConfigManager


async def is_staff(user: discord.Member):
    return any(role.name in ConfigManager.get("STAFF_ROLES") for role in user.roles)


async def is_admin(user: discord.Member):
    return any(role.name in ConfigManager.get("ADMIN_ROLES") for role in user.roles)
