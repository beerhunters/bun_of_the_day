# handlers/start.py
from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, ChatMemberAdministrator, ChatMemberOwner
from database.queries import add_user
from logger import logger

start_r = Router()


async def check_bot_admin(bot: Bot, chat_id: int) -> bool:
    """Проверка, является ли бот администратором в чате."""
    try:
        bot_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
        return isinstance(bot_member, (ChatMemberAdministrator, ChatMemberOwner))
    except Exception as e:
        logger.error(f"Ошибка проверки прав администратора в чате {chat_id}: {e}")
        return False


@start_r.message(CommandStart())
async def start(message: Message):
    """Обработчик команды /start для активации бота в чате или описания в ЛС."""
    from_user = message.from_user
    chat_id = message.chat.id

    if not from_user:
        await message.reply("Не удалось получить информацию о пользователе.")
        return

    if message.chat.type == "private":
        await message.answer(
            "Привет! Я Бот Булочка Дня! 🥐🤖\n\n"
            "Моя задача — приносить радость в групповые чаты! Я приветствую новых участников стикерами, "
            "каждый день выбираю самую аппетитную булочку среди игроков и раздаю виртуальные вкусности. 🍩✨\n\n"
            "Добавь меня в свой чат, сделай администратором и активируй командой /start. "
            "После этого используй /play, чтобы начать игру! 🎮\n\n"
            "<i>Создан для веселья и булочек.</i>\n"
            "<i>Проект будет развиваться по мере того, как его создатель прокачивает свой интеллект (а пока он ест булочки и пишет код). 🧐🍩</i>",
            parse_mode="HTML",
        )
        return

    if not await check_bot_admin(message.bot, chat_id):
        await message.reply(
            "Я не могу начать работу, пока не стану администратором! 😔\n"
            "Пожалуйста, сделай меня админом в этом чате, и я начну раздавать булочки! 🥐",
            parse_mode="HTML",
        )
        logger.warning(
            f"Бот не активирован в чате {chat_id}: не является администратором"
        )
        return

    user = await add_user(
        telegram_id=from_user.id,
        username=from_user.username,
        full_name=from_user.full_name,
        chat_id=chat_id,
    )

    display_name = (
        f"@{from_user.username}" if from_user.username else from_user.full_name
    )
    if user:
        await message.reply(
            f"Привет, {display_name}! Я Бот Булочка Дня, и я активирован! 🥐✨\n"
            "Теперь я буду встречать новичков стикерами и каждый день выбирать самую вкусную булочку. "
            "Используй /play, чтобы присоединиться к игре и начать получать булочки! 🎮",
            parse_mode="HTML",
        )
        logger.info(f"Бот активирован в чате {chat_id} пользователем {from_user.id}")
    else:
        await message.reply(
            f"Привет, {display_name}! Я уже активирован в этом чате! 🥐\n"
            "Используй /play, чтобы начать игру и получить свою булочку! 🎮",
            parse_mode="HTML",
        )
        logger.debug(
            f"Повторная активация в чате {chat_id} пользователем {from_user.id}"
        )
