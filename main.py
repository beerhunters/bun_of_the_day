import asyncio
import signal
import sys

# Импортируем логгер в самом начале - он сам настроит все нужное
from logger import logger

import aiocron
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, ErrorEvent
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramServerError, TelegramNetworkError

from config import API_TOKEN, REQUEST_DELAY
from handlers.admin_cntr import admin_cntr
from handlers.admin_points import admin_points_r

from handlers.exceptions import error_router
from handlers.in_game import in_game_r
from handlers.new_member import new_member_r
from handlers.random_user import send_random_message
from handlers.evening_humor import (
    send_evening_humor,
    get_random_evening_cron,
)
from handlers.start import start_r

from database.queries import get_active_chat_ids
from database.db import create_missing_tables


async def error_handler(event: ErrorEvent):
    """Глобальный обработчик ошибок для подавления спама от временных сетевых проблем."""
    exception = event.exception
    
    # Подавляем логирование частых сетевых ошибок Telegram
    if isinstance(exception, (TelegramServerError, TelegramNetworkError)):
        error_msg = str(exception).lower()
        if any(keyword in error_msg for keyword in [
            "bad gateway", 
            "server disconnected", 
            "connection timeout",
            "request timeout",
            "internal server error"
        ]):
            # Логируем только раз в 5 минут для таких ошибок
            if not hasattr(error_handler, '_last_network_error_log'):
                error_handler._last_network_error_log = 0
            
            import time
            current_time = time.time()
            if current_time - error_handler._last_network_error_log > 300:  # 5 минут
                logger.warning(f"Временные проблемы с Telegram API: {exception}")
                error_handler._last_network_error_log = current_time
            return True  # Ошибка обработана, не логировать
    
    # Для остальных ошибок используем стандартное логирование
    logger.error(f"Необработанная ошибка: {exception}", exc_info=True)
    return True


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
                # Добавляем задержку между запросами для избежания flood control
                await asyncio.sleep(REQUEST_DELAY)
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при получении активных чатов: {e}")


# Глобальная переменная для хранения задачи вечерних сообщений
evening_cron_task = None


async def schedule_evening_message(bot: Bot):
    """Планирование отправки вечернего сообщения на фиксированное время 20:00."""
    global evening_cron_task

    try:
        # Получаем фиксированное время для вечернего сообщения
        cron_time = get_random_evening_cron()

        # Останавливаем предыдущую задачу, если она была
        if evening_cron_task:
            evening_cron_task.stop()
            logger.info("Предыдущая задача вечерних сообщений остановлена")

        # Создаем задачу на фиксированное время (20:00 каждый день)
        evening_cron_task = aiocron.crontab(
            cron_time,
            func=lambda: asyncio.create_task(send_evening_humor(bot)),
            start=True,
        )

        # Сразу стартуем задачу
        evening_cron_task.start()
        logger.info(f"✅ Задача вечерних сообщений запущена: {cron_time}")

    except Exception as e:
        logger.error(f"Ошибка при планировании вечернего сообщения: {e}")





async def main():
    """Главная функция для запуска бота."""
    bot = None
    
    def signal_handler():
        logger.info("Получен сигнал прерывания")
        sys.exit(0)
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

    # Создаем недостающие таблицы перед запуском бота
    logger.info("Проверка и создание недостающих таблиц...")
    try:
        await create_missing_tables()
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        return

    bot = Bot(
        token=API_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )
    dp = Dispatcher()
    
    # Регистрируем глобальный обработчик ошибок
    dp.errors.register(error_handler)
    
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
            # Запускаем задачу отправки сообщений каждое утро в 9:00 МСК
            morning_cron_task = aiocron.crontab(
                "0 9 * * *",
                func=lambda: asyncio.create_task(send_daily_messages(bot)),
                start=True,  # Запускаем сразу
            )
            morning_cron_task.start()
            logger.info("Задача отправки утренних сообщений запущена...")

            # Запускаем планировщик вечерних юморных сообщений
            await schedule_evening_message(bot)
            logger.info("Планировщик вечерних юморных сообщений запущен...")

        except Exception as e:
            logger.error(f"Ошибка при запуске задач: {e}")
        logger.info("🚀 Бот запущен и готов к работе!")

        # Тестируем систему уведомлений (можно убрать после проверки)
        try:
            logger.info("📝 Тестирование новой системы логирования...")
            # Раскомментируйте следующую строку для тестирования Telegram уведомлений
            # logger.error(
            #     "🧪 Тест критической ошибки для проверки Telegram уведомлений",
            #     exc_info=True,
            # )
        except Exception as e:
            logger.error(f"Ошибка в тестовом блоке: {e}", exc_info=True)

        await dp.start_polling(
            bot,
            skip_updates=True,  # Пропускать старые обновления при запуске
            allowed_updates=["message", "callback_query", "chat_member"],  # Только нужные типы
            handle_as_tasks=False  # Обрабатывать обновления последовательно для стабильности
        )
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        logger.info("Завершение работы бота...")
        try:
            if bot and bot.session:
                await bot.session.close()
        except Exception as cleanup_error:
            logger.error(f"Ошибка при очистке ресурсов: {cleanup_error}")
        logger.info("Ресурсы очищены, бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
