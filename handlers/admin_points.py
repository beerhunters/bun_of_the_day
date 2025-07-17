from aiogram import Bot, Router
from aiogram.types import Message
from aiogram.filters import Command
from database.queries import (
    get_user_by_id,
    get_user_by_username,
    update_user_points,
    get_all_users,
    get_user_buns_stats,
    add_or_update_user_bun,
)
from logger import logger
from config import ADMIN
import random

admin_points_r = Router()

# Эмодзи для добавления и отнимания
ADD_EMOJI = "🎉"
SUB_EMOJI = "🍞"

# Сообщения для админских команд с вариациями
SUCCESS_ALL_POINTS_MESSAGES_ADD = [
    "Хлебобулочная система замесила {points} очков для всех в чате! Подкреплено: {updated} булочников.",
    "С пылу с жару! {points} очков роздано всем пекарям чата, обновлено: {updated} подмастерьев.",
    "Тесто поднялось! Всем булочникам чата добавлено {points} очков, замешано: {updated} рук.",
    "Пекарня щедро насыпала {points} очков всем участникам! Итог: {updated} сдобных мастеров.",
]

SUCCESS_ALL_POINTS_MESSAGES_SUB = [
    "Хлебный бунт! У всех булочников чата отнято {points} очков, пострадало: {updated} пекарей.",
    "Тесто опало! {points} очков урезано у всех в чате, замешено: {updated} горе-булочников.",
    "Пекарня объявила диету: минус {points} очков для всех, похудело: {updated} мастеров.",
    "Крошки с барского стола! У всех отняли {points} очков, итог: {updated} голодных пекарей.",
]

SUCCESS_USER_POINTS_MESSAGES_ADD = [
    "Секретный рецепт всыпал {points} очков булочнику @{target}! Свежая выпечка в деле.",
    "Тесто для @{target} поднялось на {points} очков! Теперь он настоящий булочный магнат.",
    "Прямо из печи! @{target} получил {points} очков от хлебной магии.",
    "@{target} подкинули {points} очков — теперь он король булок!",
]

SUCCESS_USER_POINTS_MESSAGES_SUB = [
    "У @{target} конфисковали {points} очков — тесто не подошло!",
    "Крах хлебного плана! @{target} лишился {points} очков.",
    "@{target} уронил булку — минус {points} очков в копилке!",
    "Пекарский штраф! @{target} потерял {points} очков за сырое тесто.",
]

NEWBIE_MESSAGE = "@{target} получил стартовый Круассан с {points} очками!"

NO_ADMIN_RIGHTS_MESSAGES = [
    "Только главный пекарь может месить очки, @{username}!",
    "Эй, @{username}, руки прочь от теста — это дело мастера пекарни!",
    "Без хлебного жезла не командуй, @{username}!",
    "Ты не король булок, @{username}, очки раздаёт только главный пекарь!",
]

INVALID_POINTS_MESSAGE = "Укажи нормальное количество теста! Пример: /add_points_all <chat_id> 5-10 или /add_points <chat_id> @username -5"
USER_NOT_FOUND_MESSAGE = (
    "Булочник @{target} не найден среди мастеров теста в этом чате!"
)
NO_ACTIVE_USERS_MESSAGE = "В пекарне пусто — нет активных булочников для замеса очков!"
NOT_PRIVATE_MESSAGE = "Эти команды работают только в личке главного пекаря!"


async def apply_points_to_user(
    telegram_id: int, chat_id: int, points: int
) -> tuple[int, bool]:
    """Применяет очки к пользователю, возвращает новые очки и флаг нового Круассана."""
    # Получаем user_id из таблицы users
    user = await get_user_by_id(telegram_id, chat_id)
    if not user:
        logger.warning(
            f"Пользователь telegram_id={telegram_id} не найден в чате {chat_id}"
        )
        return 0, False

    user_id = user.id  # Получаем user_id из объекта пользователя
    buns = await get_user_buns_stats(telegram_id, chat_id)

    if not buns:  # Если булочек нет, добавляем Круассан с базовыми очками
        user_bun = await add_or_update_user_bun(user_id, "Круассан", chat_id)
        if not user_bun:
            logger.error(
                f"Не удалось добавить Круассан для user_id={user_id} в чате {chat_id}"
            )
            return 0, False

        base_points = user_bun.points  # Базовые очки Круассана (2 из таблицы buns)
        new_total = max(0, points)  # Итоговые очки равны запрошенным
        if new_total != base_points:
            # Корректируем до запрошенных очков
            additional_points = new_total - base_points
            total_points = base_points + additional_points
            await update_user_points(
                telegram_id, chat_id, total_points - base_points
            )  # Добавляем только разницу
        logger.info(
            f"Добавлен Круассан с базовыми {base_points} очками, итого: {new_total}"
        )
        return new_total, True  # True — это новый Круассан
    else:  # Если булочки есть, добавляем только новые очки
        total_points = sum(bun["points"] for bun in buns)
        await update_user_points(
            telegram_id, chat_id, points
        )  # Передаём только новые очки
        new_total = max(0, total_points + points)
        return new_total, False  # False — Круассан не добавлен


@admin_points_r.message(Command("add_points_all"))
async def add_points_all_handler(message: Message, bot: Bot):
    """Обработчик команды /add_points_all <chat_id> <points> или <min-max>: изменяет очки всем участникам в указанном чате."""
    user = message.from_user

    # Проверяем, что команда отправлена в личку и пользователь — ADMIN
    if message.chat.type != "private" or user.id != ADMIN:
        await message.reply(
            NOT_PRIVATE_MESSAGE
            if message.chat.type != "private"
            else random.choice(NO_ADMIN_RIGHTS_MESSAGES).format(username=user.username)
        )
        logger.debug(
            f"@{user.username} (ID: {user.id}) попытался использовать /add_points_all не в личке или без прав"
        )
        return

    # Проверяем и парсим аргументы (chat_id и очки или диапазон)
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            raise IndexError
        chat_id = int(args[1])  # chat_id как первый аргумент
        points_arg = args[2]
        if "-" in points_arg:
            min_points, max_points = map(int, points_arg.split("-"))
            if min_points > max_points:
                raise ValueError(
                    "Минимальное значение должно быть меньше максимального"
                )
        else:
            min_points = max_points = int(points_arg)
    except (IndexError, ValueError):
        await message.reply(INVALID_POINTS_MESSAGE)
        logger.debug(
            f"@{user.username} указал некорректные данные в /add_points_all: {message.text}"
        )
        return

    # Получаем всех активных участников чата
    all_users = await get_all_users()
    chat_users = [
        user for user in all_users if user["chat_id"] == chat_id and user["in_game"]
    ]

    if not chat_users:
        await message.reply(NO_ACTIVE_USERS_MESSAGE)
        logger.debug(f"В чате {chat_id} нет активных участников для начисления очков")
        return

    # Начисляем или отнимаем очки каждому пользователю
    updated_count = 0
    total_points = 0
    for user_data in chat_users:
        points = (
            random.randint(min_points, max_points)
            if min_points != max_points
            else min_points
        )
        new_points, is_new_croissant = await apply_points_to_user(
            user_data["telegram_id"], chat_id, points
        )
        if is_new_croissant:
            # Уведомляем только если это действительно новый Круассан
            await bot.send_message(
                chat_id,
                NEWBIE_MESSAGE.format(target=user_data["username"], points=new_points),
            )
        updated_count += 1
        total_points = (
            points if min_points == max_points else f"{min_points}-{max_points}"
        )
        logger.info(
            f"@{user_data['username']} (ID: {user_data['telegram_id']}) изменил очки на {points}, теперь: {new_points}"
        )

    # Выбираем сообщение и эмодзи
    if min_points > 0:
        message_text = random.choice(SUCCESS_ALL_POINTS_MESSAGES_ADD).format(
            points=total_points, updated=updated_count
        )
        emoji = ADD_EMOJI
    else:
        message_text = random.choice(SUCCESS_ALL_POINTS_MESSAGES_SUB).format(
            points=(
                abs(total_points)
                if isinstance(total_points, int)
                else f"{abs(min_points)}-{abs(max_points)}"
            ),
            updated=updated_count,
        )
        emoji = SUB_EMOJI

    await bot.send_message(chat_id, message_text)
    await bot.send_message(chat_id, emoji)
    await message.reply(f"Команда выполнена для чата {chat_id}")
    logger.info(
        f"@{user.username} изменил очки на {total_points} для {updated_count} пользователей в чате {chat_id}"
    )


@admin_points_r.message(Command("add_points"))
async def add_points_handler(message: Message, bot: Bot):
    """Обработчик команды /add_points <chat_id> @username <points> или <min-max>: изменяет очки конкретному участнику."""
    user = message.from_user

    # Проверяем, что команда отправлена в личку и пользователь — ADMIN
    if message.chat.type != "private" or user.id != ADMIN:
        await message.reply(
            NOT_PRIVATE_MESSAGE
            if message.chat.type != "private"
            else random.choice(NO_ADMIN_RIGHTS_MESSAGES).format(username=user.username)
        )
        logger.debug(
            f"@{user.username} (ID: {user.id}) попытался использовать /add_points не в личке или без прав"
        )
        return

    # Проверяем и парсим аргументы
    try:
        args = message.text.split(maxsplit=3)
        if len(args) < 4:
            raise IndexError
        chat_id = int(args[1])  # chat_id как первый аргумент
        target_username = args[2].strip()
        if not target_username.startswith("@"):
            raise ValueError("Юзернейм должен начинаться с @")
        target_username = target_username[1:]
        points_arg = args[3]
        if "-" in points_arg:
            min_points, max_points = map(int, points_arg.split("-"))
            if min_points > max_points:
                raise ValueError(
                    "Минимальное значение должно быть меньше максимального"
                )
            points = random.randint(min_points, max_points)
        else:
            points = int(points_arg)
    except (IndexError, ValueError):
        await message.reply(INVALID_POINTS_MESSAGE)
        logger.debug(
            f"@{user.username} указал некорректные данные в /add_points: {message.text}"
        )
        return

    # Ищем пользователя
    target_data = await get_user_by_username(chat_id, target_username)
    if not target_data or not target_data.in_game:
        await message.reply(USER_NOT_FOUND_MESSAGE.format(target=target_username))
        logger.debug(f"@{target_username} не найден или не в игре в чате {chat_id}")
        return

    # Применяем очки
    new_points, is_new_croissant = await apply_points_to_user(
        target_data.telegram_id, chat_id, points
    )
    if is_new_croissant:
        # Уведомляем только если это действительно новый Круассан
        await bot.send_message(
            chat_id, NEWBIE_MESSAGE.format(target=target_username, points=new_points)
        )

    # Выбираем сообщение и эмодзи
    if points > 0:
        message_text = random.choice(SUCCESS_USER_POINTS_MESSAGES_ADD).format(
            points=points, target=target_username
        )
        emoji = ADD_EMOJI
    else:
        message_text = random.choice(SUCCESS_USER_POINTS_MESSAGES_SUB).format(
            points=abs(points), target=target_username
        )
        emoji = SUB_EMOJI

    await bot.send_message(chat_id, message_text)
    await bot.send_message(chat_id, emoji)
    await message.reply(f"Команда выполнена для @{target_username} в чате {chat_id}")
    logger.info(
        f"@{user.username} изменил очки на {points} для @{target_username} (ID: {target_data.telegram_id}), теперь: {new_points}"
    )
