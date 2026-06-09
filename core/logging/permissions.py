from __future__ import annotations

import discord

from core.config import ConfigManager


def _member_roles(author, guild: discord.Guild | None):
    if guild is None or author is None:
        return ()
    if isinstance(author, discord.Member):
        return author.roles
    member = guild.get_member(author.id)
    if member is not None:
        return member.roles
    return ()


def _has_named_role(author, guild: discord.Guild | None, role_names: list[str]) -> bool:
    if guild is None:
        return False
    member_roles = _member_roles(author, guild)
    return any(
        discord.utils.get(guild.roles, name=role_name) in member_roles
        for role_name in role_names
    )


def staff_role_names() -> list[str]:
    roles = ConfigManager.get("STAFF_ROLES") or []
    return list(roles) if isinstance(roles, list) else []


def admin_role_names() -> list[str]:
    roles = ConfigManager.get("ADMIN_ROLES") or []
    return list(roles) if isinstance(roles, list) else []


def is_staff_member(author, guild: discord.Guild | None) -> bool:
    return _has_named_role(author, guild, staff_role_names())


def is_admin_member(author, guild: discord.Guild | None) -> bool:
    return _has_named_role(author, guild, admin_role_names())


def is_staff_message(message) -> bool:
    guild = getattr(message, "guild", None)
    author = getattr(message, "author", None)
    return is_staff_member(author, guild)


def is_admin_message(message) -> bool:
    guild = getattr(message, "guild", None)
    author = getattr(message, "author", None)
    return is_admin_member(author, guild)
