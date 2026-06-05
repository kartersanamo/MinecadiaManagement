# Minecadia Management Bot

Discord bot for server moderation and management tools on Minecadia.

## What it does

- Timeouts, mention alerts, and moderation logs
- YouTube channel checker for media submissions
- Server analytics and member message tracking
- Staff analysis commands

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add DISCORD_TOKEN, DB_*, YOUTUBE_API_KEY
python main.py
```

## Config

- `.env` — token, database, YouTube API key
- `assets/config.json` — channels, roles, embed settings
