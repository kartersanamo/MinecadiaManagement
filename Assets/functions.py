import discord
import json
import aiomysql

def get_data():
   with open("MinecadiaManagement/Assets/config.json", "r") as file:
      return json.load(file)
   
data = get_data()

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
        print(f"Execute error: '{error}'")
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