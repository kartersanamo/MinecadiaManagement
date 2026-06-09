from __future__ import annotations

import uuid
from datetime import datetime, timezone

import discord

from core.config import ConfigManager
from core.logging.events import LogCategory, LogPayload


_CATEGORY_COLORS: dict[LogCategory, int] = {
    LogCategory.MEMBER: 0x57F287,
    LogCategory.MESSAGE: 0x5865F2,
    LogCategory.CHANNEL: 0x9B59B6,
    LogCategory.ROLE: 0x9B59B6,
    LogCategory.SERVER: 0x9B59B6,
    LogCategory.VOICE: 0x1ABC9C,
    LogCategory.MODERATION: 0xE67E22,
    LogCategory.INTERACTION: 0x95A5A6,
    LogCategory.SCHEDULED: 0x3498DB,
    LogCategory.SECURITY: 0xED4245,
    LogCategory.BOT: 0xF1C40F,
    LogCategory.CUSTOM: 0xF1C40F,
}


def _default_color() -> discord.Color:
    return discord.Color.from_str(str(ConfigManager.get("EMBED_COLOR") or "0xF1C40F"))


def _category_color(category: LogCategory) -> discord.Color:
    hex_color = _CATEGORY_COLORS.get(category)
    if hex_color is None:
        return _default_color()
    return discord.Color(hex_color)


def new_event_id() -> str:
    return str(uuid.uuid4())


def truncate(text: str | None, limit: int = 1000) -> str:
    if not text:
        return "—"
    text = str(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def format_user(user: discord.abc.User | None) -> str:
    if user is None:
        return "—"
    return f"{user.mention} (`{user.id}`)"


def format_channel(channel: discord.abc.GuildChannel | discord.Thread | None) -> str:
    if channel is None:
        return "—"
    mention = getattr(channel, "mention", None) or f"#{getattr(channel, 'name', channel.id)}"
    return f"{mention} (`{channel.id}`)"


def build_embed(payload: LogPayload, event_id: str, bot: discord.Client | None = None) -> discord.Embed:
    embed = discord.Embed(
        title=payload.display_title,
        description=truncate(payload.summary) if payload.summary else None,
        color=_category_color(payload.category),
        timestamp=datetime.now(timezone.utc),
    )

    if payload.fields.get("Actor"):
        embed.add_field(name="Actor", value=truncate(payload.fields["Actor"], 1024), inline=True)
    if payload.fields.get("Target"):
        embed.add_field(name="Target", value=truncate(payload.fields["Target"], 1024), inline=True)
    if payload.fields.get("Channel"):
        embed.add_field(name="Channel", value=truncate(payload.fields["Channel"], 1024), inline=True)

    reserved = {"Actor", "Target", "Channel"}
    for key, value in payload.fields.items():
        if key in reserved:
            continue
        embed.add_field(name=key, value=truncate(value, 1024), inline=False)

    if payload.source_bot and payload.source_bot != "Management":
        embed.add_field(name="Source", value=payload.source_bot, inline=True)

    if payload.jump_url:
        embed.add_field(name="Link", value=f"[Jump]({payload.jump_url})", inline=False)

    footer_text = f"Event ID: {event_id[:8]}"
    logo = ConfigManager.get("LOGO")
    footer = ConfigManager.get("FOOTER") or "Minecadia Management"
    embed.set_footer(text=f"{footer_text} · {footer}")

    if payload.thumbnail_url:
        embed.set_thumbnail(url=payload.thumbnail_url)
    elif bot and bot.user:
        embed.set_author(name=bot.user.display_name, icon_url=bot.user.display_avatar.url)

    return embed
