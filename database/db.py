import functools

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DOCKER_ENV = True

DB_URL = "/app/data/db.sqlite3"

engine = create_async_engine(url=DB_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def with_session(func):
    """Декоратор для автоматического создания и закрытия сессии"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            return await func(session, *args, **kwargs)

    return wrapper
