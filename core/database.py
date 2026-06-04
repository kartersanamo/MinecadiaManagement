import aiomysql

from core.config import get_settings


async def connect():
    data = get_settings()
    return await aiomysql.connect(
        host=data["DATABASE_CONFIG"]["host"],
        port=data["DATABASE_CONFIG"]["port"],
        user=data["DATABASE_CONFIG"]["user"],
        password=data["DATABASE_CONFIG"]["password"],
        db=data["DATABASE_CONFIG"]["database"],
        autocommit=bool(data["DATABASE_CONFIG"]["autocommit"]),
        cursorclass=aiomysql.DictCursor,
    )


from core.loggers import log_tasks


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
