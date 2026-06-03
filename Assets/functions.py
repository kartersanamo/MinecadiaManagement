import functools
import logger
import discord
import json
import aiomysql
from typing import Optional
import os
import time
from dotenv import load_dotenv

load_dotenv()

log_tasks = logger.logging.getLogger("Tasks")
log_commands = logger.logging.getLogger("Commands")


def get_data():
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
   return data

data = get_data()


def task(action_name: str, log: bool = None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                time_elapsed = round((time.perf_counter() - start_time), 2)
                if time_elapsed > 3:
                    log_tasks.warning(
                        f"{action_name} took a long time to complete and finished in {time_elapsed}s"
                    )
                elif log:
                    log_tasks.info(f"{action_name} completed in {time_elapsed}s")
                return result
            except Exception as error:
                log_tasks.error(
                    f"{action_name} failed after {round((time.perf_counter() - start_time), 2)}s : {error}"
                )
                raise error
        return wrapper
    return decorator


async def connect():
    return await aiomysql.connect(
        host=data["DATABASE_CONFIG"]["host"],
        port=data["DATABASE_CONFIG"]["port"],
        user=data["DATABASE_CONFIG"]["user"],
        password=data["DATABASE_CONFIG"]["password"],
        db=data["DATABASE_CONFIG"]["database"],
        autocommit=bool(data["DATABASE_CONFIG"]["autocommit"]),
        cursorclass=aiomysql.DictCursor
    )

async def execute(query):
    rows = []
    connection = None 
    try:
        connection = await connect()
        async with connection.cursor() as cursor:
            await cursor.execute(query)
            rows = await cursor.fetchall()
    except Exception as error:
        log_tasks.error(f"Error executing query: {query} {error}")
    finally:
        if connection:
            connection.close()
        return rows

async def admin_log(client, embed: discord.Embed):
    guild = client.get_guild(data['GUILD_ID'])
    channel = guild.get_channel(data['ADMIN_LOGS'])
    await channel.send(embed=embed)

async def is_staff(user: discord.Member):
    return any(role.name in data["STAFF_ROLES"] for role in user.roles)

async def is_admin(user: discord.Member):
    return any(role.name in data["ADMIN_ROLES"] for role in user.roles)

def get_embed_logo_url(logo_path: Optional[str]) -> Optional[str]:
    if not logo_path:
        return None

    if logo_path.startswith(("http://", "https://")):
        return logo_path

    if os.path.isfile(logo_path):
        filename = os.path.basename(logo_path)
        return f"attachment://{filename}"

    return None
