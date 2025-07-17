import random
from aiogram import types, Router, Bot
from aiogram.filters import Command, ChatMemberUpdatedFilter, LEFT

from database.queries import (
    get_user_by_id,
    add_user_to_game,
    add_user,
    get_user_buns_stats,
    get_top_users_by_points,
    set_user_out_of_game,
)
from handlers.start import check_bot_admin
from logger import logger

IN_GAME_TEXT = [
    "Ты присоединился, @{user}! 🥳 Может, именно ты станешь булочкой дня! 🍩",
    "Отлично, @{user}, ты в игре! 🎉 Кто знает, может, ты — будущая булочка дня? 🥐",
    "Все готово, @{user}! 🔥 Время быть булочкой дня! 🍞 Ждем с нетерпением!",
    "Ты присоединился, @{user}, и кто знает... Может, ты — булочка дня? 🥯✨",
    "Ого, @{user}, ты в игре! 🏆 Кто станет булочкой дня — сюрприз! 🍪",
    "Ты с нами, @{user}! 🎮 Кто знает, может, ты станешь булочкой дня? 🍰",
    "Зарегистрирован, @{user}! 🥳 Может, именно твоя булочка окажется в центре внимания! 🥞",
    "Ты в игре, @{user}! 🥳 Кто знает, когда твоя булочка дня окажется на пьедестале? 🥖",
    "Добро пожаловать в игру, @{user}! 🎉 Возможно, ты — булочка дня, и мы это еще узнаем! 🥨",
    "Ты в игре, @{user}! 🚀 Время быть булочкой дня, независимо от того, когда это случится! 🥯",
]

NO_BUNS_MESSAGE = [
    "Ты либо не выигрывал булочек, либо все раскидал сосисками! 🌭📊",
    "Булочек нет — то ли не везет, то ли сосиски всему виной! 🍔😢",
    "Твои булочки? Съедены или раздарены сосисками! 🥐💥",
    "Ни булочки, ни крошки — сосиски постарались? 🌭😅",
    "Булочная пустота — сосиски победили! 🍞🚫",
]

in_game_r = Router()


def pluralize_times(count: int) -> str:
    """Возвращает правильную форму слова 'раз' в зависимости от числа."""
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} раз"
    elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
        return f"{count} раза"
    else:
        return f"{count} раз"


def pluralize_points(points: int) -> str:
    """Возвращает правильную форму слова 'очко' в зависимости от числа."""
    if points % 10 == 1 and points % 100 != 11:
        return f"{points} очко"
    elif points % 10 in [2, 3, 4] and points % 100 not in [12, 13, 14]:
        return f"{points} очка"
    else:
        return f"{points} очков"


@in_game_r.message(Command(commands="play"))
async def in_game_handler(message: types.Message):
    from_user = message.from_user
    chat_id = message.chat.id
    if message.chat.type == "private":
        await message.reply("Эту команду можно использовать только в групповом чате!")
        return
    if not from_user:
        await message.reply("Не удалось получить информацию о пользователе.")
        return
    user_id = from_user.id
    user = await get_user_by_id(user_id, chat_id)
    if user:
        if user.in_game:
            await message.reply("Ты уже в игре! 🎮")
        else:
            await add_user_to_game(user_id, chat_id)
            text = random.choice(IN_GAME_TEXT).format(
                user=(
                    f"@{from_user.username}"
                    if from_user.username
                    else from_user.full_name
                )
            )
            await message.reply(text)
    else:
        await add_user(
            telegram_id=user_id,
            username=from_user.username,
            full_name=from_user.full_name,
            chat_id=chat_id,
        )
        text = random.choice(IN_GAME_TEXT).format(
            user=f"{from_user.username}" if from_user.username else from_user.full_name
        )
        await message.reply(text)


@in_game_r.message(Command(commands="stats_me"))
async def stats_me_handler(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.chat.type == "private":
        await message.reply("Эту команду можно использовать только в групповом чате!")
        return
    user_buns = await get_user_buns_stats(telegram_id=user_id, chat_id=chat_id)
    if not user_buns:
        await message.reply(random.choice(NO_BUNS_MESSAGE))
        return
    username = message.from_user.username or message.from_user.full_name
    stats_text = f"<b>🧁 Статистика @{username}:</b>\n\n"
    total_points = 0
    for i, item in enumerate(user_buns, start=1):
        bun = item["bun"]
        count = item["count"]
        points = item["points"]
        times_text = pluralize_times(count)
        points_text = pluralize_points(points)
        stats_text += f"{i}. {bun} - {times_text} ({points_text}) 🔥\n"
        total_points += points
    total_points_text = pluralize_points(total_points)
    stats_text += f"\n<b>Всего:</b> {total_points_text}"
    await message.reply(stats_text, parse_mode="HTML")


@in_game_r.message(Command(commands="stats"))
async def statistic_handler(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type == "private":
        await message.reply("Эту команду можно использовать только в групповом чате!")
        return

    top_users = await get_top_users_by_points(chat_id=chat_id)
    if not top_users:
        await message.reply("В этом чате пока нет активных игроков с булочками!")
        return

    stats_text = "<b>🏆 Топ-10 игроков по очкам:</b>\n\n"
    for i, user in enumerate(top_users, start=1):
        display_name = f"@{user['username']}" if user["username"] else user["full_name"]
        times_text = pluralize_times(user["count"])
        stats_text += f"{i}. {display_name} - {user['bun']} ({times_text})\n"
    await message.reply(stats_text, parse_mode="HTML")


@in_game_r.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEFT))
async def on_user_left_chat(update: types.ChatMemberUpdated, bot: Bot):
    """Обработка события выхода пользователя из чата."""
    user_id = update.from_user.id
    chat_id = update.chat.id
    if update.chat.type == "private":
        return

    if not await check_bot_admin(bot, chat_id):
        logger.warning(
            f"Бот не имеет прав администратора в чате {chat_id}, игнорируем событие"
        )
        return

    changed = await set_user_out_of_game(telegram_id=user_id, chat_id=chat_id)
    if changed:
        display_name = (
            f"@{update.from_user.username}"
            if update.from_user.username
            else update.from_user.full_name
        )
        await bot.send_message(
            chat_id,
            f"{display_name} покинул чат и больше не участвует в розыгрыше булочек!",
            parse_mode="HTML",
        )
