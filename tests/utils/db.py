from database import Base
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine


async def create_test_engine(pg_url: str):
    """Creates a test PostgreSQL engine.

    This function takes a PostgreSQL URL string and creates a test engine
    based on it.
    It first creates the database using a synchronous engine, then creates
    an async engine for the test DB.
    Finally, it creates tables using the async engine.

    :param pg_url: A PostgreSQL URL string.
    :return: A test PostgreSQL engine.
    :rtype: sqlalchemy.ext.asyncio.AsyncEngine
    """
    # Extract DB name
    server_url, db_name = pg_url.rsplit("/", 1)

    # 1. Create the database using a synchronous engine
    sync_server_url = server_url.replace("+asyncpg", "") + "/postgres"
    sync_engine = create_engine(sync_server_url, isolation_level="AUTOCOMMIT")

    with sync_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        conn.execute(text(f"CREATE DATABASE {db_name}"))

    sync_engine.dispose()

    # 2. Create async engine for the actual test DB
    engine = create_async_engine(pg_url, future=True)

    # 3. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


async def drop_test_engine(engine):
    await engine.dispose()
