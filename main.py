import asyncio

import aiocron
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand


from config import API_TOKEN
from handlers.admin_cntr import admin_cntr
from handlers.admin_points import admin_points_r

from handlers.exceptions import error_router
from handlers.in_game import in_game_r
from handlers.new_member import new_member_r
from handlers.random_user import send_random_message
from handlers.evening_humor import send_evening_humor, get_random_evening_cron
from handlers.start import start_r

from database.queries import get_active_chat_ids
from database.db import create_missing_tables
from logger import logger


async def send_daily_messages(bot: Bot):
    """Отправка утренних сообщений во все активные чаты."""
    try:
        chat_ids = await get_active_chat_ids()
        if not chat_ids:
            logger.warning("Нет активных чатов для отправки сообщений.")
            return

        for chat_id in chat_ids:
            try:
                await send_random_message(bot, chat_id=chat_id)
                logger.info(f"Сообщение отправлено в чат {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при получении активных чатов: {e}")


# Глобальная переменная для хранения текущей задачи вечерних сообщений
evening_cron_task = None


async def schedule_random_evening_message(bot: Bot):
    """Планирование отправки вечернего сообщения на случайное время."""
    global evening_cron_task
    
    try:
        # Получаем случайное время для следующего вечернего сообщения
        cron_time = get_random_evening_cron()
        
        # Останавливаем предыдущую задачу, если она была
        if evening_cron_task:
            evening_cron_task.stop()
        
        # Создаем новую задачу на случайное время
        evening_cron_task = aiocron.crontab(
            cron_time,
            func=lambda: asyncio.create_task(send_evening_and_reschedule(bot)),
            start=True
        )
        
        logger.info(f"Вечернее сообщение запланировано на {cron_time} (UTC)")
        
    except Exception as e:
        logger.error(f"Ошибка при планировании вечернего сообщения: {e}")


async def send_evening_and_reschedule(bot: Bot):
    """Отправка вечернего сообщения и планирование следующего."""
    try:
        # Отправляем вечернее сообщение
        await send_evening_humor(bot)
        
        # Планируем следующее сообщение на завтра
        await schedule_random_evening_message(bot)
        
    except Exception as e:
        logger.error(f"Ошибка при отправке и перепланировании вечернего сообщения: {e}")


async def main():
    """Главная функция для запуска бота."""
    
    # Создаем недостающие таблицы перед запуском бота
    logger.info("Проверка и создание недостающих таблиц...")
    try:
        await create_missing_tables()
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        return
    
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
    dp.include_routers(
        start_r,
        new_member_r,
        in_game_r,
        admin_cntr,
        admin_points_r,
        error_router,
    )
    bot_commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/play", description="Играть"),
        BotCommand(command="/stats", description="Статистика"),
        BotCommand(command="/stats_me", description="Моя статистика"),
    ]
    await bot.set_my_commands(bot_commands)
    try:
        try:
            # Запускаем задачу отправки сообщений каждое утро в 9:00
            morning_cron_task = aiocron.crontab(
                "0 9 * * *",
                func=lambda: asyncio.create_task(send_daily_messages(bot)),
                start=True,  # Запускаем сразу
            )
            morning_cron_task.start()
            logger.info("Задача отправки утренних сообщений запущена...")
            
            # Запускаем планировщик вечерних юморных сообщений
            await schedule_random_evening_message(bot)
            logger.info("Планировщик вечерних юморных сообщений запущен...")
            
        except Exception as e:
            logger.error(f"Ошибка при запуске задач: {e}")
        logger.info("Бот запущен...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
