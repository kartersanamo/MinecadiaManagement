import json
import os

from dotenv import load_dotenv

load_dotenv()

_settings: dict | None = None


def get_settings() -> dict:
    global _settings
    if _settings is not None:
        return _settings
    with open("Assets/config.json", "r") as file:
        data = json.load(file)
    if os.getenv("DISCORD_TOKEN"):
        data["TOKEN"] = os.getenv("DISCORD_TOKEN")
    if os.getenv("DB_HOST"):
        data["DATABASE_CONFIG"] = {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", ""),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "") or os.getenv("DB_DATABASE", ""),
            "autocommit": os.getenv("DB_AUTOCOMMIT", "true").lower() in ("1", "true", "yes"),
        }
    _settings = data
    return _settings


def get_data() -> dict:
    return get_settings()
