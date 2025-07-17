import asyncio

from aiogram import Router, types
from aiogram.filters import Command

from config import ADMIN
from database.queries import (
    get_all_users,
    remove_user_from_game,
    get_all_buns,
    remove_bun,
    edit_bun,
    add_bun,
)
from handlers.in_game import pluralize_points
from collections import defaultdict

from handlers.random_user import send_random_message

admin_cntr = Router()


@admin_cntr.message(Command(commands="user_list"))
async def user_list_handler(message: types.Message, bot):
    """Вывод списка всех пользователей по чатам с названиями чатов (только для admin в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return

    users = await get_all_users()
    if not users:
        await message.reply("Пользователей в базе нет.")
        return

    # Группируем пользователей по chat_id
    users_by_chat = defaultdict(list)
    for user in users:
        users_by_chat[user["chat_id"]].append(user)

    MAX_MESSAGE_LENGTH = 4096
    messages = []

    # Обрабатываем каждый чат
    for chat_id in sorted(users_by_chat.keys()):
        try:
            chat = await bot.get_chat(chat_id)
            chat_title = chat.title if chat.title else f"Чат {chat_id}"
        except Exception as e:
            chat_title = f"Чат {chat_id} (ошибка получения названия: {str(e)})"

        chat_users = sorted(users_by_chat[chat_id], key=lambda x: x["telegram_id"])
        header = f"<b>{chat_title} (ID: <code>{chat_id}</code>):</b>\n"
        current_message = header
        user_count = 0

        for user in chat_users:
            user_count += 1
            display_name = (
                f"@{user['username']}" if user["username"] else user["full_name"]
            )
            status = "✅ в игре" if user["in_game"] else "❌ не в игре"
            user_line = (
                f"{user_count}. {display_name} (ID: {user['telegram_id']}) — {status}\n"
            )

            if len(current_message) + len(user_line) > MAX_MESSAGE_LENGTH:
                messages.append(current_message)
                current_message = (
                    f"<b>{chat_title} (ID: {chat_id}, продолжение):</b>\n" + user_line
                )
            else:
                current_message += user_line

        if current_message != header:
            messages.append(current_message)

    if not messages:
        await message.reply("Не удалось сформировать список пользователей.")
        return

    for msg in messages:
        await message.reply(msg, parse_mode="HTML")
        await asyncio.sleep(0.5)


@admin_cntr.message(Command(commands="remove_from_game"))
async def remove_from_game_handler(message: types.Message):
    """Удаление пользователя из розыгрыша по chat_id и порядковому номеру в чате (только для admin в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return

    # Ожидаем два аргумента: chat_id и порядковый номер в чате
    args = message.text.split()[1:]  # Пропускаем саму команду
    if len(args) != 2:
        await message.reply(
            "Использование: /remove_from_game <chat_id> <порядковый_номер>"
        )
        return

    try:
        chat_id = int(args[0])  # chat_id как целое число
        user_number = int(args[1]) - 1  # Номер в чате (нумерация с 1, индексы с 0)
    except ValueError:
        await message.reply("chat_id и порядковый номер должны быть целыми числами!")
        return

    # Получаем список всех пользователей
    users = await get_all_users()
    if not users:
        await message.reply("Список пользователей пуст.")
        return

    # Фильтруем пользователей по chat_id
    chat_users = [user for user in users if user["chat_id"] == chat_id]
    if not chat_users:
        await message.reply(f"В чате {chat_id} нет пользователей.")
        return

    # Проверяем, что номер в допустимом диапазоне для данного чата
    if user_number < 0 or user_number >= len(chat_users):
        await message.reply(
            f"Пользователь с номером {user_number + 1} не найден в чате {chat_id}!"
        )
        return

    # Извлекаем данные пользователя по индексу в списке чата
    user = chat_users[user_number]
    telegram_id = user["telegram_id"]
    display_name = f"@{user['username']}" if user["username"] else user["full_name"]

    # Удаляем пользователя из розыгрыша
    removed = await remove_user_from_game(telegram_id=telegram_id, chat_id=chat_id)
    if removed:
        await message.reply(
            f"Пользователь {display_name} (ID: {telegram_id}) удален из розыгрыша в чате {chat_id}."
        )
    else:
        await message.reply(
            f"Пользователь {display_name} (ID: {telegram_id}) уже не в игре в чате {chat_id}."
        )


@admin_cntr.message(Command(commands="list_buns"))
async def list_buns_handler(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply("Эта команда доступна только администратору в ЛС!")
        return
    buns = await get_all_buns()
    if not buns:
        await message.reply("Булочек пока нет!")
        return
    text = "<b>Список булочек:</b>\n\n"
    for name, points in buns.items():
        text += f"- {name}: {pluralize_points(points)}\n"
    await message.reply(text, parse_mode="HTML")


@admin_cntr.message(Command(commands="add_bun"))
async def add_bun_handler(message: types.Message):
    """Добавление новой булочки (только для админа в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return

    args = message.text.split(maxsplit=2)[1:]  # Пропускаем команду
    if len(args) != 2:
        await message.reply("Использование: /add_bun <название> <баллы>")
        return

    name, points_str = args
    try:
        points = int(points_str)
        if points < 0:
            raise ValueError("Баллы не могут быть отрицательными!")

        bun = await add_bun(name=name, points=points)
        if bun:
            await message.reply(f"Булочка '{name}' с {points} баллами добавлена!")
        else:
            await message.reply(f"Булочка '{name}' уже существует!")
    except ValueError as e:
        await message.reply(f"Ошибка: {e if str(e) else 'баллы должны быть числом!'}")


@admin_cntr.message(Command(commands="edit_bun"))
async def edit_bun_handler(message: types.Message):
    """Редактирование баллов булочки (только для админа в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return

    args = message.text.split(maxsplit=2)[1:]  # Пропускаем команду
    if len(args) != 2:
        await message.reply("Использование: /edit_bun <название> <новые_баллы>")
        return

    name, points_str = args
    try:
        points = int(points_str)
        if points < 0:
            raise ValueError("Баллы не могут быть отрицательными!")

        bun = await edit_bun(name=name, points=points)
        if bun:
            await message.reply(f"Булочка '{name}' обновлена: теперь {points} баллов.")
        else:
            await message.reply(f"Булочка '{name}' не найдена!")
    except ValueError as e:
        await message.reply(f"Ошибка: {e if str(e) else 'баллы должны быть числом!'}")


@admin_cntr.message(Command(commands="remove_bun"))
async def remove_bun_handler(message: types.Message):
    """Удаление булочки (только для админа в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return

    args = message.text.split(maxsplit=1)[1:]  # Пропускаем команду
    if len(args) != 1:
        await message.reply("Использование: /remove_bun <название>")
        return

    name = args[0]
    success = await remove_bun(name=name)
    if success:
        await message.reply(f"Булочка '{name}' удалена!")
    else:
        await message.reply(f"Булочка '{name}' не найдена!")


@admin_cntr.message(Command(commands="help"))
async def admin_help_handler(message: types.Message):
    """Вывод списка всех админских команд (только для админа в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return

    help_text = (
        "<b>📋 Админские команды:</b>\n\n"
        "📋 /user_list - Список всех пользователей.\n"
        "🗑 /remove_from_game - Удалить пользователя из розыгрыша по порядковому номеру.\n\n"
        "📋 /list_buns - Список всех булочек.\n"
        "➕ /add_bun 'название' 'баллы' - Добавить булочку.\n"
        "✏️ /edit_bun 'название' 'новые_баллы' - Изменить баллы.\n"
        "🗑 /remove_bun 'название' - Удалить булочку.\n\n"
        "➕ /add_points_all 'чат' 'баллы' - Добавить баллы всем пользователям в чате.\n"
        "➕ /add_points 'юзернейм' 'баллы' - Добавить баллы пользователю по юзернейму.\n\n"
        "📬 /send_to_chat - Ручной запуск отправки ежедневных сообщений.\n\n"
        "ℹ️ /help - Список команд."
    )
    await message.reply(help_text, parse_mode="HTML")


@admin_cntr.message(Command(commands="send_to_chat"))
async def send_to_chat_handler(message: types.Message, bot):
    """Ручная отправка сообщения в указанный чат (только для админа в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return

    args = message.text.split(maxsplit=1)[1:]  # Пропускаем команду
    if not args:
        await message.reply("Использование: /send_to_chat <chat_id>")
        return

    try:
        chat_id = int(args[0])  # Преобразуем chat_id в целое число
    except ValueError:
        await message.reply("chat_id должен быть числом!")
        return

    await message.reply(f"Отправляю сообщение в чат {chat_id}...")
    try:
        await send_random_message(bot, chat_id)
        await message.reply(f"Сообщение успешно отправлено в чат {chat_id}!")
    except Exception as e:
        await message.reply(f"Ошибка при отправке в чат {chat_id}: {str(e)}")
