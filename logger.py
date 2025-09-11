import logging
import os
from logging.handlers import RotatingFileHandler

# Импортируем LOG_LEVEL из config, но с защитой от циклического импорта
try:
    from config import LOG_LEVEL
except ImportError:
    LOG_LEVEL = "INFO"  # Fallback если config еще не загружен

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


# Определяем уровни логирования
LOG_LEVEL_MAPPING = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

app_log_level = LOG_LEVEL_MAPPING.get(LOG_LEVEL, logging.INFO)

# Настройка файлового обработчика (все логи уровня ERROR и выше)
file_handler = RotatingFileHandler(
    "logs/bot.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=10,  # Храним больше файлов для истории
    encoding="utf-8",
)
file_handler.setLevel(logging.ERROR)  # В файл только ошибки
file_handler.setFormatter(CustomFormatter())

# Настройка консольного обработчика (уровень из переменной окружения)
console_handler = logging.StreamHandler()
console_handler.setLevel(app_log_level)  # Из переменной LOG_LEVEL
console_handler.setFormatter(CustomFormatter())

# Базовая настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Самый низкий уровень для root logger
    handlers=[file_handler, console_handler],
    force=True  # Перезаписываем предыдущие настройки
)

# Создаем основной логгер приложения
logger = logging.getLogger("bun_bot")
logger.setLevel(logging.DEBUG)  # Позволяем всем уровням проходить через логгер

# Дополнительные специализированные логгеры
db_logger = logging.getLogger("bun_bot.database")
handlers_logger = logging.getLogger("bun_bot.handlers")
api_logger = logging.getLogger("bun_bot.api")


def log_with_context(chat_id=None, user_id=None, logger_name="bun_bot"):
    """Создает логгер с контекстной информацией о чате и пользователе."""
    context_logger = logging.getLogger(logger_name)
    extra = {"chat_id": chat_id, "user_id": user_id}
    return logging.LoggerAdapter(context_logger, extra)


def get_logger(name: str = "bun_bot"):
    """Получить именованный логгер."""
    return logging.getLogger(name)


# Настройка уровня логирования для внешних библиотек
# Отключаем INFO логи от aiogram если уровень ERROR или выше
if app_log_level >= logging.ERROR:
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
elif app_log_level >= logging.WARNING:
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

# Логгируем информацию о текущих настройках при инициализации
logger.info(f"Logging initialized with level: {LOG_LEVEL} (numeric: {app_log_level})")
logger.info(f"Console output level: {logging.getLevelName(console_handler.level)}")
logger.info(f"File output level: {logging.getLevelName(file_handler.level)}")
logger.info("External libraries logging levels adjusted")
