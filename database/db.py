import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import functools

DOCKER_ENV = os.getenv("DOCKER_ENV", "True") == "True"
DB_PATH = "/app/db.sqlite3" if DOCKER_ENV else "db.sqlite3"
ENGINE_ECHO = os.getenv("DB_ECHO", "False") == "True"

engine = create_async_engine(url=f"sqlite+aiosqlite:///{DB_PATH}", echo=ENGINE_ECHO)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    from models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def with_session(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            async with session.begin():
                return await func(session=session, *args, **kwargs)

    return wrapper
