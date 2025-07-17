# handlers/exceptions.py
import os
import traceback
from datetime import datetime
from typing import Optional

from aiogram import Router, Bot
from aiogram.handlers import ErrorHandler
from aiogram.types import Update

from config import FOR_LOGS
from logger import logger  # Импортируем единый логгер

error_router = Router()


class ErrorInfo:
    """Класс для хранения информации об ошибке"""

    def __init__(self, exception: Exception, update: Optional[Update] = None):
        self.exception = exception
        self.exception_name = type(exception).__name__
        self.exception_message = str(exception)
        self.error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update = update
        self.traceback_info = traceback.format_exc()
        self.traceback_snippet = self._format_traceback()
        self.error_location = self._get_error_location()

    def _get_error_location(self) -> str:
        """Получение точного местоположения ошибки"""
        if not hasattr(self.exception, "__traceback__"):
            return "❓ Неизвестное местоположение"
        tb = traceback.extract_tb(self.exception.__traceback__)
        if not tb:
            return "❓ Неизвестное местоположение"
        last_call = tb[-1]
        filename = last_call.filename
        line = last_call.lineno
        func = last_call.name
        code_line = last_call.line.strip() if last_call.line else "???"
        return (
            f"📂 <b>Файл:</b> {filename}\n"
            f"📌 <b>Строка:</b> {line}\n"
            f"🔹 <b>Функция:</b> {func}\n"
            f"🖥 <b>Код:</b> <pre>{code_line}</pre>"
        )

    def _format_traceback(self, max_length: int = 2000) -> str:
        """Форматирование трейсбека с ограничением длины"""
        tb_lines = self.traceback_info.splitlines()
        snippet = (
            "\n".join(tb_lines[-4:]) if len(tb_lines) >= 4 else self.traceback_info
        )
        if len(snippet) > max_length:
            return snippet[:max_length] + "\n...[сокращено]"
        return snippet

    def get_user_info(self) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """Получение информации о пользователе"""
        if not self.update:
            return None, None, None
        if hasattr(self.update, "message") and self.update.message:
            return (
                self.update.message.from_user.id,
                self.update.message.from_user.full_name,
                self.update.message.text,
            )
        elif hasattr(self.update, "callback_query") and self.update.callback_query:
            return (
                self.update.callback_query.from_user.id,
                self.update.callback_query.from_user.full_name,
                self.update.callback_query.data,
            )
        return None, None, None


@error_router.errors()
class MyHandler(ErrorHandler):
    """Обработчик ошибок в боте"""

    async def handle(self) -> None:
        logger.info("Обработчик ошибок вызван")
        exception = getattr(self.event, "exception", None)
        update = getattr(self.event, "update", None)
        if not exception:
            logger.error("Событие без исключения: %s", self.event)
            return
        error_info = ErrorInfo(exception, update)
        logger.error(
            "Ошибка %s: %s\nМестоположение: %s\nTraceback: %s",
            error_info.exception_name,
            error_info.exception_message,
            error_info.error_location.replace("\n", " | "),
            error_info.traceback_snippet,
        )
        await self._handle_notifications(error_info)

    async def _handle_notifications(self, error_info: ErrorInfo) -> None:
        """Управление уведомлениями об ошибке"""
        try:
            await self._notify_user(error_info.update)
        except Exception as e:
            logger.error(
                "Ошибка при уведомлении пользователя: %s\n%s",
                str(e),
                traceback.format_exc(),
            )
        try:
            await self._notify_admins(error_info)
        except Exception as e:
            logger.error(
                "Ошибка при уведомлении администраторов: %s\n%s",
                str(e),
                traceback.format_exc(),
            )

    async def _notify_user(self, update: Optional[Update]) -> None:
        """Отправка сообщения пользователю"""
        if not update:
            logger.warning("Нет update для уведомления пользователя")
            return
        user_message = (
            "⚠️ Произошла ошибка!\n\n"
            "Пожалуйста, сделайте скриншот этого сообщения и отправьте его администратору, описав, что вы делали перед ошибкой.\n"
            "Спасибо за помощь в улучшении бота! 😊"
        )
        try:
            if update.message:
                await update.message.answer(user_message)
                logger.info("Сообщение об ошибке отправлено пользователю (Message)")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.answer(user_message)
                logger.info(
                    "Сообщение об ошибке отправлено пользователю (CallbackQuery)"
                )
            else:
                logger.warning("Неизвестный тип update: %s", type(update))
        except Exception as e:
            logger.error("Ошибка при отправке сообщения пользователю: %s", str(e))

    async def _notify_admins(self, error_info: ErrorInfo) -> None:
        """Отправка уведомления администраторам"""
        user_id, user_name, user_message = error_info.get_user_info()
        admin_message = (
            f"⚠️ <b>Ошибка в боте!</b>\n\n"
            f"⏰ <b>Время:</b> {error_info.error_time}\n\n"
            f"👤 <b>Пользователь:</b> @{user_name or 'Неизвестно'}\n"
            f"🆔 <b>ID:</b> {user_id or 'Неизвестно'}\n"
            f"💬 <b>Сообщение:</b> {user_message or 'Неизвестно'}\n\n"
            f"❌ <b>Тип ошибки:</b> {error_info.exception_name}\n"
            f"📝 <b>Описание:</b> {error_info.exception_message}\n\n"
            f"📍 <b>Местоположение:</b>\n{error_info.error_location}\n\n"
            f"📚 <b>Трейсбек:</b>\n<pre>{error_info.traceback_snippet}</pre>"
        )
        bot: Bot = self.bot
        # FOR_LOGS = os.getenv("FOR_LOGS")
        try:
            await bot.send_message(FOR_LOGS, admin_message, parse_mode="HTML")
            logger.info("Сообщение отправлено администратору %s", FOR_LOGS)
        except Exception as e:
            logger.error(
                "Не удалось отправить сообщение владельцу %s: %s", FOR_LOGS, str(e)
            )
