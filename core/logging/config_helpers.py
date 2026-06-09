from __future__ import annotations

from core.config import ConfigManager


def logging_settings() -> dict:
    raw = ConfigManager.get("LOGGING") or {}
    return raw if isinstance(raw, dict) else {}


def logs_channel_id() -> int:
    channel = logging_settings().get("LOGS_CHANNEL") or ConfigManager.get("LOGS_CHANNEL")
    return int(channel or 0)


def admin_logs_channel_id() -> int:
    return int(ConfigManager.get("ADMIN_LOGS") or 0)


def flush_interval_seconds() -> int:
    return int(logging_settings().get("FLUSH_INTERVAL_SECONDS") or 60)


def guild_id() -> int:
    return int(ConfigManager.get("GUILD_ID") or 0)


def ignored_channel_ids() -> set[int]:
    ids = logging_settings().get("IGNORED_CHANNEL_IDS") or []
    return {int(x) for x in ids}


def recruitment_channel_ids() -> set[int]:
    ids = logging_settings().get("RECRUITMENT_CHANNELS") or ConfigManager.get("RECRUITMENT_CHANNELS") or []
    return {int(x) for x in ids}


def log_flag(name: str, default: bool = False) -> bool:
    return bool(logging_settings().get(name, default))
