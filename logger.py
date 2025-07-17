# # logger.py
# import logging
# import os
# from logging.handlers import RotatingFileHandler
#
# # Убедимся, что папка logs существует
# if not os.path.exists("logs"):
#     os.makedirs("logs")
#
#
# # Создаём форматтер для логов
# class CustomFormatter(logging.Formatter):
#     grey = "\x1b[38;21m"
#     green = "\x1b[32;1m"
#     yellow = "\x1b[33;1m"
#     red = "\x1b[31;1m"
#     bold_red = "\x1b[41m"
#     reset = "\x1b[0m"
#     format = "%(asctime)s | %(levelname)s | - %(message)s"  # Убрали filename и lineno
#
#     FORMATS = {
#         logging.DEBUG: grey + format + reset,
#         logging.INFO: green + format + reset,
#         logging.WARNING: yellow + format + reset,
#         logging.ERROR: red + format + reset,
#         logging.CRITICAL: bold_red + format + reset,
#     }
#
#     def format(self, record):
#         log_fmt = self.FORMATS.get(record.levelno, self.format)
#         formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
#         record.levelname = record.levelname.ljust(8)
#         return formatter.format(record)
#
#
# # Настройка обработчика для файла (ошибки и выше)
# file_handler = RotatingFileHandler(
#     "logs/bot.log",
#     maxBytes=5 * 1024 * 1024,  # 5 MB
#     backupCount=5,  # Храним до 5 файлов логов
#     encoding="utf-8",
# )
# file_handler.setLevel(logging.ERROR)  # Логируем INFO и выше в файл
# file_handler.setFormatter(CustomFormatter())
#
# # Настройка обработчика для консоли (DEBUG и выше)
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.INFO)  # Выводим всё в консоль для отладки
# console_handler.setFormatter(CustomFormatter())
#
# # Настройка корневого логгера
# logging.basicConfig(
#     level=logging.INFO,  # Устанавливаем минимальный уровень для приложения
#     handlers=[file_handler, console_handler],  # Оба обработчика
# )
#
# # Создаём логгер для использования в приложении
# logger = logging.getLogger("bot")
# logger.py
import logging
import os
from logging.handlers import RotatingFileHandler

if not os.path.exists("logs"):
    os.makedirs("logs")


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    green = "\x1b[32;1m"
    yellow = "\x1b[33;1m"
    red = "\x1b[31;1m"
    bold_red = "\x1b[41m"
    reset = "\x1b[0m"
    format = "%(asctime)s | %(levelname)s | %(message)s (chat_id: %(chat_id)s, user_id: %(user_id)s)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        if not hasattr(record, "chat_id"):
            record.chat_id = "N/A"
        if not hasattr(record, "user_id"):
            record.user_id = "N/A"
        log_fmt = self.FORMATS.get(record.levelno, self.format)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        record.levelname = record.levelname.ljust(8)
        return formatter.format(record)


file_handler = RotatingFileHandler(
    "logs/bot.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(CustomFormatter())

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(CustomFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler],
)

logger = logging.getLogger("bot")


# Пример использования с контекстом
def log_with_context(chat_id=None, user_id=None):
    extra = {"chat_id": chat_id, "user_id": user_id}
    return logging.LoggerAdapter(logger, extra)
