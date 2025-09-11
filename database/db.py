import os
import functools
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from database.models import Base
from logger import logger

DOCKER_ENV = os.getenv("DOCKER_ENV", "True") == "True"
DB_PATH = "/app/db.sqlite3" if DOCKER_ENV else "db.sqlite3"
ENGINE_ECHO = os.getenv("DB_ECHO", "False") == "True"
engine = create_async_engine(url=f"sqlite+aiosqlite:///{DB_PATH}", echo=ENGINE_ECHO)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Инициализация базы данных - создание всех таблиц из моделей."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_missing_tables():
    """Создание недостающих таблиц без пересоздания существующих."""
    from database.models import DailySelection
    from sqlalchemy import inspect

    async with engine.begin() as conn:
        # Используем инспектор для проверки существования таблицы
        def check_table_exists(sync_conn):
            inspector = inspect(sync_conn)
            return "daily_selections" in inspector.get_table_names()

        table_exists = await conn.run_sync(check_table_exists)

        if not table_exists:
            # Создаем только недостающую таблицу
            def create_table(sync_conn):
                DailySelection.__table__.create(sync_conn)

            await conn.run_sync(create_table)
            logger.info("✅ Таблица 'daily_selections' создана успешно")
        else:
            # logger.info("ℹ️ Таблица 'daily_selections' уже существует")
            pass


def with_session(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            try:
                result = await func(session, *args, **kwargs)
                await session.commit()
                return result
            except SQLAlchemyError:
                await session.rollback()
                raise

    return wrapper
