from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LogCategory(str, Enum):
    MEMBER = "Member"
    MESSAGE = "Message"
    CHANNEL = "Channel"
    ROLE = "Role"
    SERVER = "Server"
    VOICE = "Voice"
    MODERATION = "Moderation"
    INTERACTION = "Interaction"
    SCHEDULED = "Scheduled"
    SECURITY = "Security"
    BOT = "Bot"
    CUSTOM = "Custom"


class LogSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


@dataclass
class LogPayload:
    event_type: str
    category: LogCategory
    title: str
    action: str
    guild_id: int
    severity: LogSeverity = LogSeverity.INFO
    actor_id: int | None = None
    target_id: int | None = None
    channel_id: int | None = None
    source_bot: str = "Management"
    summary: str | None = None
    fields: dict[str, str] = field(default_factory=dict)
    thumbnail_url: str | None = None
    jump_url: str | None = None
    route_admin: bool = False
    immediate: bool = False
    skip_discord: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def display_title(self) -> str:
        return f"{self.category.value} · {self.action}"
