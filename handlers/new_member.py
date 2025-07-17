# handlers/new_member.py
import random

from aiogram import Bot, Router
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, MEMBER
from database.queries import add_user, get_user_by_id, add_user_to_game
from logger import logger

# Список стикеров
STICKER_IDS = [
    "CAACAgIAAxkBAAENqQdnmgj2PreJnV9zPnYLeQr9oE_6ywACBmYAAl3N0Uj-7tbvioUa5TYE",
    "CAACAgIAAxkBAAENp0FnmOucMj3bxD-d8KBzb7sqM1RTlQACu1wAAkI8yEgIHgv8-kFWxzYE",
]

# Список юмористических сообщений для возвращающихся пользователей
RETURN_MESSAGES = [
    "@{username} пытался нас покинуть, но булочки оказались сильнее!",
    "Смотрите-ка, @{username} вернулся! Не смог жить без наших булочек!",
    "@{username} думал, что сможет сбежать, но круассаны сказали: 'Не так быстро!'",
    "Добро пожаловать обратно, @{username}! Мы знали, что ты не устоишь перед ароматом булок.",
]

new_member_r = Router()


@new_member_r.chat_member(
    ChatMemberUpdatedFilter(IS_NOT_MEMBER >> MEMBER)  # Фильтр на вступление в чат
)
async def new_member_handler(event: ChatMemberUpdated, bot: Bot):
    """Обработчик вступления участника в чат: отправляет стикер или сообщение при добавлении/возвращении."""
    new_member = event.new_chat_member.user
    chat_id = event.chat.id

    # Пропускаем ботов
    if new_member.is_bot:
        logger.debug(f"Пропущен бот: {new_member.full_name} (ID: {new_member.id})")
        return

    telegram_id = new_member.id
    username = (
        new_member.username or new_member.full_name
    )  # Используем username или full_name
    # Проверяем, существует ли пользователь в базе
    user = await get_user_by_id(telegram_id, chat_id)

    send_sticker = False
    if user:
        # Пользователь существует, проверяем статус in_game
        if not user.in_game:
            # Если пользователь не в игре, включаем его обратно
            await add_user_to_game(telegram_id, chat_id)
            # Отправляем юмористическое сообщение
            message = random.choice(RETURN_MESSAGES).format(username=username)
            try:
                await bot.send_message(chat_id, message)
                logger.info(
                    f"Сообщение отправлено возвращённому пользователю: {new_member.full_name} (ID: {telegram_id}) в чат {chat_id}"
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
            logger.info(
                f"Пользователь {new_member.full_name} (ID: {telegram_id}) возвращён в игру в чате {chat_id}"
            )
        else:
            logger.debug(f"Пользователь {new_member.id} уже в игре в чате {chat_id}")
    else:
        # Новый пользователь, добавляем с in_game=True
        await add_user(
            telegram_id=telegram_id,
            username=new_member.username,
            full_name=new_member.full_name,
            chat_id=chat_id,
            # in_game=True,
        )
        send_sticker = True
        logger.info(
            f"Добавлен новый участник: {new_member.full_name} (ID: {telegram_id}) в чат {chat_id}"
        )

    # Отправляем стикер только для новых пользователей
    if send_sticker:
        try:
            sticker_id = random.choice(STICKER_IDS)
            await bot.send_sticker(chat_id, sticker=sticker_id)
            logger.info(
                f"Стикер отправлен новому участнику: {new_member.full_name} (ID: {telegram_id}) в чат {chat_id}"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке стикера в чат {chat_id}: {e}")
