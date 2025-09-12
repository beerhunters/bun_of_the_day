import logging
import os
import asyncio
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

# Импортируем настройки из config с защитой от циклического импорта
try:
    from config import (
        LOG_LEVEL, LOG_TO_FILE, LOG_TO_TELEGRAM, LOG_FILE_LEVEL, 
        LOG_TELEGRAM_LEVEL, API_TOKEN, FOR_LOGS
    )
except ImportError:
    # Fallback значения если config еще не загружен
    LOG_LEVEL = "INFO"
    LOG_TO_FILE = True
    LOG_TO_TELEGRAM = True
    LOG_FILE_LEVEL = "ERROR"
    LOG_TELEGRAM_LEVEL = "ERROR"
    API_TOKEN = None
    FOR_LOGS = None

# Создаем директорию для логов
if not os.path.exists("logs"):
    os.makedirs("logs")


class CustomFormatter(logging.Formatter):
    """Кастомный форматер с цветами для консоли и контекстной информацией."""
    
    grey = "\x1b[38;21m"
    green = "\x1b[32;1m"
    yellow = "\x1b[33;1m"
    red = "\x1b[31;1m"
    bold_red = "\x1b[41m"
    reset = "\x1b[0m"
    
    # Стандартизированный формат с дополнительной информацией
    format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s | [chat_id:%(chat_id)s, user_id:%(user_id)s]"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        # Добавляем контекстную информацию если её нет
        if not hasattr(record, "chat_id"):
            record.chat_id = "N/A"
        if not hasattr(record, "user_id"):
            record.user_id = "N/A"
        
        # Выбираем формат с цветом для данного уровня
        log_fmt = self.FORMATS.get(record.levelno, self.format)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        
        # Выравниваем levelname для красивого вывода
        record.levelname = record.levelname.ljust(8)
        
        return formatter.format(record)


class TelegramHandler(logging.Handler):
    """Handler для отправки критических ошибок в Telegram."""
    
    def __init__(self, token: str, chat_id: int):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.last_error_time = {}  # Защита от спама
        
    def emit(self, record):
        """Отправка лога в Telegram."""
        if not self.token or not self.chat_id:
            return
            
        try:
            # Защита от спама - не более одной ошибки такого типа в минуту
            error_key = f"{record.levelname}:{record.module}:{record.lineno}"
            now = datetime.now()
            
            if error_key in self.last_error_time:
                time_diff = (now - self.last_error_time[error_key]).total_seconds()
                if time_diff < 60:  # Меньше минуты
                    return
            
            self.last_error_time[error_key] = now
            
            # Форматируем сообщение
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            message = f"🚨 <b>Bot Error Report</b>\n\n"
            message += f"🕐 <b>Time:</b> {timestamp}\n"
            message += f"⚠️ <b>Level:</b> {record.levelname}\n"
            message += f"📁 <b>Module:</b> {record.module}:{record.lineno}\n"
            message += f"💬 <b>Message:</b>\n<code>{record.getMessage()}</code>\n"
            
            # Добавляем контекстную информацию если есть
            if hasattr(record, 'chat_id') and record.chat_id != 'N/A':
                message += f"💭 <b>Chat ID:</b> {record.chat_id}\n"
            if hasattr(record, 'user_id') and record.user_id != 'N/A':
                message += f"👤 <b>User ID:</b> {record.user_id}\n"
                
            # Добавляем stack trace для ERROR и CRITICAL
            if record.exc_info and record.levelno >= logging.ERROR:
                import traceback
                tb = ''.join(traceback.format_exception(*record.exc_info))
                # Ограничиваем длину traceback
                if len(tb) > 1000:
                    tb = tb[:1000] + "...[truncated]"
                message += f"\n📋 <b>Traceback:</b>\n<code>{tb}</code>"
            
            # Отправляем асинхронно
            asyncio.create_task(self._send_to_telegram(message))
            
        except Exception as e:
            # Не логируем ошибки отправки в Telegram, чтобы избежать циклов
            pass
    
    async def _send_to_telegram(self, message: str):
        """Асинхронная отправка сообщения в Telegram."""
        try:
            import aiohttp
            
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        # Если не удалось отправить, просто игнорируем
                        pass
                        
        except Exception:
            # Игнорируем ошибки отправки
            pass


# Определяем уровни логирования
LOG_LEVEL_MAPPING = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

app_log_level = LOG_LEVEL_MAPPING.get(LOG_LEVEL, logging.INFO)
file_log_level = LOG_LEVEL_MAPPING.get(LOG_FILE_LEVEL, logging.ERROR)
telegram_log_level = LOG_LEVEL_MAPPING.get(LOG_TELEGRAM_LEVEL, logging.ERROR)

# Создаем обработчики
handlers = []

# Консольный обработчик (основной уровень из LOG_LEVEL)
console_handler = logging.StreamHandler()
console_handler.setLevel(app_log_level)
console_handler.setFormatter(CustomFormatter())
handlers.append(console_handler)

# Файловый обработчик (если включен)
if LOG_TO_FILE:
    file_handler = RotatingFileHandler(
        "logs/bot.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setLevel(file_log_level)
    file_handler.setFormatter(CustomFormatter())
    handlers.append(file_handler)

# Telegram обработчик (если включен и есть токен)
telegram_handler = None
if LOG_TO_TELEGRAM and API_TOKEN and FOR_LOGS:
    try:
        telegram_handler = TelegramHandler(API_TOKEN, FOR_LOGS)
        telegram_handler.setLevel(telegram_log_level)
        handlers.append(telegram_handler)
    except Exception:
        pass

# Базовая настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Самый низкий уровень для root logger
    handlers=handlers,
    force=True  # Перезаписываем предыдущие настройки
)

# Создаем основной логгер приложения
logger = logging.getLogger("bun_bot")
logger.setLevel(logging.DEBUG)


def log_with_context(chat_id: Optional[int] = None, user_id: Optional[int] = None, logger_name: str = "bun_bot"):
    """Создает логгер с контекстной информацией о чате и пользователе."""
    context_logger = logging.getLogger(logger_name)
    extra = {"chat_id": chat_id, "user_id": user_id}
    return logging.LoggerAdapter(context_logger, extra)


def get_logger(name: str = "bun_bot"):
    """Получить именованный логгер."""
    return logging.getLogger(name)


def setup_external_loggers(log_level: int):
    """Настройка уровня логирования для внешних библиотек."""
    external_libs = [
        "aiogram", "aiogram.event", "aiogram.dispatcher", 
        "aiohttp", "aiosqlite", "aiocron"
    ]
    
    # Для внешних библиотек устанавливаем WARNING или выше, если основной уровень ERROR
    external_level = logging.WARNING if log_level >= logging.ERROR else log_level
    
    for lib in external_libs:
        logging.getLogger(lib).setLevel(external_level)


# Настраиваем внешние библиотеки
setup_external_loggers(app_log_level)

# Логгируем информацию о настройках при инициализации
logger.info(f"🚀 Logging system initialized")
logger.info(f"📊 Console level: {LOG_LEVEL}")
if LOG_TO_FILE:
    logger.info(f"📁 File logging: enabled ({LOG_FILE_LEVEL})")
else:
    logger.info(f"📁 File logging: disabled")
    
if LOG_TO_TELEGRAM and telegram_handler:
    logger.info(f"📱 Telegram notifications: enabled ({LOG_TELEGRAM_LEVEL})")
else:
    logger.info(f"📱 Telegram notifications: disabled")

logger.info(f"🔧 External libraries: {logging.getLevelName(logging.getLogger('aiogram').level)}")