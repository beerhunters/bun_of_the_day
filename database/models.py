from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(
        Integer, unique=True, nullable=False
    )  # Telegram ID пользователя
    username = Column(String, nullable=True)  # Username (может быть null)
    full_name = Column(String, nullable=False)  # Полное имя
    chat_id = Column(Integer, nullable=False)  # Чат, в котором пользователь играет
    in_game = Column(Boolean, default=False)  # Статус в игре
    buns = relationship("UserBun", back_populates="user")  # Связь с булочками


class UserBun(Base):
    __tablename__ = "user_buns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # Связь с пользователем
    bun = Column(String, nullable=False)  # Название булочки
    count = Column(Integer, default=0)  # Сколько раз выпадала эта булочка
    chat_id = Column(Integer, nullable=False)  # Чат, в котором это произошло
    points = Column(Integer, nullable=False, default=0)  # Новая колонка
    user = relationship("User", back_populates="buns")  # Обратная связь
    __table_args__ = (
        UniqueConstraint(
            "user_id", "bun", "chat_id", name="unique_user_bun_chat"
        ),  # Уникальность связки
    )


class Bun(Base):
    """Модель булочек с их баллами."""

    __tablename__ = "buns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # Название булочки, уникальное
    points = Column(Integer, nullable=False)  # Баллы за булочку


class GameSetting(Base):
    __tablename__ = "game_settings"

    id = Column(Integer, primary_key=True)  # AUTOINCREMENT автоматически в SQLite
    key = Column(String(50), unique=True, nullable=False)  # Ограничение длины работает
    value = Column(Integer, nullable=False)
    description = Column(Text)
