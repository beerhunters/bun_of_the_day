import asyncio

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import ADMIN
from database.queries import (
    get_all_users,
    remove_user_from_game,
    delete_user_completely,
    get_all_buns,
    remove_bun,
    edit_bun,
    add_bun,
    get_inactive_users_count,
    get_inactive_users_by_chat,
    bulk_delete_inactive_users,
)
from handlers.in_game import pluralize_points
from collections import defaultdict

from handlers.random_user import send_random_message
from handlers.evening_humor import send_evening_humor, get_evening_schedule_info

admin_cntr = Router()

# Временное хранение состояний для многошаговых команд
user_states = {}

# Состояния для отправки сообщений и управления булочками
MESSAGE_STATES = {
    "waiting_for_message": "waiting_for_message"
}

BUN_STATES = {
    "waiting_for_add_bun_name": "waiting_for_add_bun_name",
    "waiting_for_add_bun_points": "waiting_for_add_bun_points", 
    "waiting_for_edit_bun_points": "waiting_for_edit_bun_points"
}

POINTS_STATES = {
    "waiting_for_chat_id_all": "waiting_for_chat_id_all",
    "waiting_for_points_all": "waiting_for_points_all",
    "waiting_for_chat_id_user": "waiting_for_chat_id_user",
    "waiting_for_username": "waiting_for_username", 
    "waiting_for_points_user": "waiting_for_points_user",
    "waiting_for_chat_id_set": "waiting_for_chat_id_set",
    "waiting_for_username_set": "waiting_for_username_set",
    "waiting_for_points_set": "waiting_for_points_set"
}


# ========== ОБРАБОТЧИКИ ИНЛАЙН КНОПОК ==========

@admin_cntr.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: CallbackQuery):
    """Меню управления пользователями."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Список всех пользователей", callback_data="cmd_user_list")
        ],
        [
            InlineKeyboardButton(text="🗑 Полностью удалить пользователя", callback_data="cmd_remove_from_game")
        ],
        [
            InlineKeyboardButton(text="🧹 Удалить всех неактивных игроков", callback_data="cmd_cleanup_inactive_users")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main")
        ]
    ])
    
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "admin_buns")
async def admin_buns_menu(callback: CallbackQuery):
    """Меню управления булочками."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Список всех булочек", callback_data="cmd_list_buns")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить булочку", callback_data="cmd_add_bun")
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить булочку", callback_data="cmd_edit_bun"),
            InlineKeyboardButton(text="🗑 Удалить булочку", callback_data="cmd_remove_bun")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main")
        ]
    ])
    
    await callback.message.edit_text(
        "🥐 <b>Управление булочками</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "admin_points")
async def admin_points_menu(callback: CallbackQuery):
    """Меню управления очками."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить очки всем в чате", callback_data="cmd_add_points_all")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить очки пользователю", callback_data="cmd_add_points")
        ],
        [
            InlineKeyboardButton(text="🎯 Установить очки пользователю", callback_data="cmd_set_points")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main")
        ]
    ])
    
    await callback.message.edit_text(
        "🎯 <b>Управление очками</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "admin_other")
async def admin_other_menu(callback: CallbackQuery):
    """Меню других команд."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📬 Отправить сообщение в чат", callback_data="cmd_send_to_chat")
        ],
        [
            InlineKeyboardButton(text="🌇 Отправить вечернее юморное сообщение", callback_data="cmd_send_evening_humor")
        ],
        [
            InlineKeyboardButton(text="🕐 Статус расписания вечерних сообщений", callback_data="cmd_evening_schedule_status")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="back_to_main")
        ]
    ])
    
    await callback.message.edit_text(
        "🔧 <b>Другие команды</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    """Возвращение к главному меню."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="🥐 Управление булочками", callback_data="admin_buns")
        ],
        [
            InlineKeyboardButton(text="🎯 Управление очками", callback_data="admin_points")
        ],
        [
            InlineKeyboardButton(text="🔧 Другие команды", callback_data="admin_other")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Справка по командам", callback_data="admin_help")
        ]
    ])
    
    await callback.message.edit_text(
        "🔧 <b>Админская панель Бота Булочка Дня</b>\n\n"
        "Добро пожаловать в панель управления! Выберите нужный раздел:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


# ========== ОБРАБОТЧИКИ КОМАНД ЧЕРЕЗ КНОПКИ ==========

@admin_cntr.callback_query(F.data == "cmd_user_list")
async def callback_user_list(callback: CallbackQuery):
    """Обработчик кнопки 'Список пользователей'."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Вызываем существующую функцию
    await user_list_handler_internal(callback.message, callback.bot)
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_list_buns")
async def callback_list_buns(callback: CallbackQuery):
    """Обработчик кнопки 'Список булочек'."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await list_buns_handler_internal(callback.message)
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_remove_from_game")
async def callback_remove_from_game_start(callback: CallbackQuery):
    """Начало интерактивного удаления пользователя."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем список чатов с пользователями
    users = await get_all_users()
    if not users:
        await callback.message.edit_text(
            "❌ В базе данных нет пользователей.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
            ])
        )
        await callback.answer()
        return
    
    # Группируем по чатам
    chats = defaultdict(list)
    for user in users:
        chats[user["chat_id"]].append(user)
    
    # Создаем кнопки для выбора чата
    keyboard_rows = []
    for chat_id in sorted(chats.keys()):
        try:
            chat = await callback.bot.get_chat(chat_id)
            chat_title = chat.title if chat.title else f"Чат {chat_id}"
        except:
            chat_title = f"Чат {chat_id}"
        
        active_users = len([u for u in chats[chat_id] if u["in_game"]])
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"💬 {chat_title} ({active_users} игроков)",
                callback_data=f"remove_select_chat_{chat_id}"
            )
        ])
    
    keyboard_rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")
    ])
    
    await callback.message.edit_text(
        "🗑 <b>Полное удаление пользователя из базы данных</b>\n\n"
        "⚠️ <i>Внимание: Пользователь будет полностью удален из БД со всеми данными!</i>\n\n"
        "Шаг 1/2: Выберите чат:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )
    await callback.answer()


@admin_cntr.callback_query(F.data.startswith("remove_select_chat_"))
async def callback_remove_select_user(callback: CallbackQuery):
    """Выбор пользователя для удаления из конкретного чата."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    chat_id = int(callback.data.split("_")[-1])
    
    # Получаем пользователей из этого чата
    users = await get_all_users()
    chat_users = [u for u in users if u["chat_id"] == chat_id and u["in_game"]]
    
    if not chat_users:
        await callback.message.edit_text(
            f"❌ В чате {chat_id} нет активных игроков.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к выбору чата", callback_data="cmd_remove_from_game")]
            ])
        )
        await callback.answer()
        return
    
    # Получаем название чата
    try:
        chat = await callback.bot.get_chat(chat_id)
        chat_title = chat.title if chat.title else f"Чат {chat_id}"
    except:
        chat_title = f"Чат {chat_id}"
    
    # Создаем кнопки для выбора пользователя
    keyboard_rows = []
    for user in sorted(chat_users, key=lambda x: x["full_name"]):
        display_name = f"@{user['username']}" if user["username"] else user["full_name"]
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"👤 {display_name} (ID: {user['telegram_id']})",
                callback_data=f"remove_confirm_{chat_id}_{user['telegram_id']}"
            )
        ])
    
    keyboard_rows.append([
        InlineKeyboardButton(text="⬅️ Назад к выбору чата", callback_data="cmd_remove_from_game")
    ])
    
    await callback.message.edit_text(
        f"🗑 <b>Полное удаление пользователя из базы данных</b>\n\n"
        f"Чат: <b>{chat_title}</b>\n"
        f"⚠️ <i>Внимание: Будут удалены ВСЕ данные пользователя!</i>\n\n"
        f"Шаг 2/2: Выберите пользователя для полного удаления:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )
    await callback.answer()


@admin_cntr.callback_query(F.data.startswith("remove_confirm_") & ~F.data.startswith("remove_confirm_bun_"))
async def callback_remove_confirm(callback: CallbackQuery):
    """Подтверждение и выполнение удаления пользователя."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    parts = callback.data.split("_")
    chat_id = int(parts[2])
    telegram_id = int(parts[3])
    
    # Получаем информацию о пользователе
    users = await get_all_users()
    target_user = None
    for user in users:
        if user["chat_id"] == chat_id and user["telegram_id"] == telegram_id:
            target_user = user
            break
    
    if not target_user:
        await callback.message.edit_text(
            "❌ Пользователь не найден.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="cmd_remove_from_game")]
            ])
        )
        await callback.answer()
        return
    
    # Выполняем полное удаление пользователя из БД
    display_name = f"@{target_user['username']}" if target_user["username"] else target_user["full_name"]
    
    try:
        deleted = await delete_user_completely(telegram_id=telegram_id, chat_id=chat_id)
        
        success_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить еще пользователя", callback_data="cmd_remove_from_game")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_users")]
        ])
        
        if deleted:
            await callback.message.edit_text(
                f"✅ <b>Пользователь полностью удален из базы данных!</b>\n\n"
                f"Пользователь: {display_name}\n"
                f"Telegram ID: <code>{telegram_id}</code>\n"
                f"Чат ID: <code>{chat_id}</code>\n\n"
                f"🗑️ Удалены:\n"
                f"• Запись пользователя\n"
                f"• Все булочки и очки\n"
                f"• История ежедневных выборов\n\n"
                f"Если пользователь снова напишет /play, он будет зарегистрирован заново.",
                parse_mode="HTML",
                reply_markup=success_keyboard
            )
        else:
            await callback.message.edit_text(
                f"❌ <b>Пользователь не найден</b>\n\n"
                f"Пользователь с ID <code>{telegram_id}</code> не найден в чате <code>{chat_id}</code>.\n"
                f"Возможно, он уже был удален ранее.",
                parse_mode="HTML",
                reply_markup=success_keyboard
            )
            
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_remove_from_game")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_users")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при удалении пользователя</b>\n\n"
            f"Пользователь: {display_name}\n"
            f"Telegram ID: <code>{telegram_id}</code>\n"
            f"Чат ID: <code>{chat_id}</code>\n\n"
            f"Детали ошибки: <code>{str(e)}</code>\n\n"
            f"Попробуйте снова или обратитесь к разработчику.",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_send_to_chat")
async def callback_send_to_chat_start(callback: CallbackQuery):
    """Начало интерактивной отправки сообщения в чат."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем список всех чатов
    users = await get_all_users()
    if not users:
        await callback.message.edit_text(
            "❌ В базе данных нет пользователей и чатов.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")]
            ])
        )
        await callback.answer()
        return
    
    # Группируем по чатам
    chats = defaultdict(list)
    for user in users:
        chats[user["chat_id"]].append(user)
    
    # Создаем кнопки для выбора чата
    keyboard_rows = []
    for chat_id in sorted(chats.keys()):
        try:
            chat = await callback.bot.get_chat(chat_id)
            chat_title = chat.title if chat.title else f"Чат {chat_id}"
        except:
            chat_title = f"Чат {chat_id}"
        
        total_users = len(chats[chat_id])
        active_users = len([u for u in chats[chat_id] if u["in_game"]])
        
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"💬 {chat_title} ({active_users}/{total_users})",
                callback_data=f"send_select_chat_{chat_id}"
            )
        ])
    
    # Добавляем опцию отправить булочку дня
    keyboard_rows.append([
        InlineKeyboardButton(
            text="🥐 Отправить Булочку Дня во все чаты",
            callback_data="send_bun_to_all"
        )
    ])
    
    keyboard_rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")
    ])
    
    await callback.message.edit_text(
        "📬 <b>Отправка сообщения в чат</b>\n\n"
        "Шаг 1/2: Выберите чат или действие:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )
    await callback.answer()


@admin_cntr.callback_query(F.data.startswith("send_select_chat_"))
async def callback_send_message_input(callback: CallbackQuery):
    """Ожидание ввода сообщения для отправки в чат."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    chat_id = int(callback.data.split("_")[-1])
    
    # Получаем название чата
    try:
        chat = await callback.bot.get_chat(chat_id)
        chat_title = chat.title if chat.title else f"Чат {chat_id}"
    except:
        chat_title = f"Чат {chat_id}"
    
    # Сохраняем состояние пользователя
    user_states[callback.from_user.id] = {
        "state": MESSAGE_STATES["waiting_for_message"],
        "chat_id": chat_id,
        "chat_title": chat_title
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="send_cancel")]
    ])
    
    await callback.message.edit_text(
        f"📬 <b>Отправка сообщения в чат</b>\n\n"
        f"Чат: <b>{chat_title}</b>\n"
        f"ID: <code>{chat_id}</code>\n\n"
        f"Шаг 2/2: Напишите сообщение, которое хотите отправить в этот чат.\n\n"
        f"💡 <i>Поддерживается HTML-разметка</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "send_bun_to_all")
async def callback_send_bun_to_all(callback: CallbackQuery):
    """Отправка Булочки Дня во все активные чаты."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        # Получаем активные чаты
        from database.queries import get_active_chat_ids
        chat_ids = await get_active_chat_ids()
        
        if not chat_ids:
            await callback.message.edit_text(
                "❌ Нет активных чатов для отправки Булочки Дня.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="cmd_send_to_chat")]
                ])
            )
            await callback.answer()
            return
        
        success_count = 0
        error_count = 0
        errors = []
        
        await callback.message.edit_text(
            f"🔄 <b>Отправка Булочки Дня...</b>\n\n"
            f"Найдено {len(chat_ids)} активных чатов.\n"
            f"Начинаю отправку...",
            parse_mode="HTML"
        )
        
        for chat_id in chat_ids:
            try:
                await send_random_message(callback.bot, chat_id=chat_id)
                success_count += 1
            except Exception as e:
                error_count += 1
                try:
                    chat = await callback.bot.get_chat(chat_id)
                    chat_name = chat.title if chat.title else f"Чат {chat_id}"
                except:
                    chat_name = f"Чат {chat_id}"
                errors.append(f"• {chat_name}: {str(e)[:50]}...")
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🥐 Отправить еще раз", callback_data="send_bun_to_all")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cmd_send_to_chat")]
        ])
        
        result_text = f"✅ <b>Отправка завершена!</b>\n\n"
        result_text += f"📊 <b>Результат:</b>\n"
        result_text += f"• Успешно: {success_count}\n"
        result_text += f"• Ошибки: {error_count}\n\n"
        
        if errors:
            result_text += f"❌ <b>Ошибки:</b>\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                result_text += f"\n... и еще {len(errors) - 5}"
        
        await callback.message.edit_text(
            result_text,
            parse_mode="HTML",
            reply_markup=result_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="send_bun_to_all")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cmd_send_to_chat")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при массовой отправке</b>\n\n"
            f"Детали: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


@admin_cntr.callback_query(F.data == "send_cancel")
async def callback_send_cancel(callback: CallbackQuery):
    """Отмена отправки сообщения."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Очищаем состояние
    if callback.from_user.id in user_states:
        del user_states[callback.from_user.id]
    
    await callback.message.edit_text(
        "❌ <b>Отправка сообщения отменена</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cmd_send_to_chat")]
        ])
    )
    await callback.answer()


# Обработчик текстовых сообщений для отправки в чаты и управления булочками
@admin_cntr.message(F.text)
async def handle_admin_text_input(message: types.Message):
    """Обработчик текстовых сообщений от админа."""
    if message.from_user.id != ADMIN or message.chat.type != "private":
        return
    
    # Проверяем, есть ли состояние для этого админа
    if message.from_user.id not in user_states:
        return
    
    state_data = user_states[message.from_user.id]
    state = state_data.get("state")
    
    # Обработка отправки сообщения
    if state == MESSAGE_STATES["waiting_for_message"]:
        await handle_send_message(message, state_data)
    
    # Обработка добавления булочки - название
    elif state == BUN_STATES["waiting_for_add_bun_name"]:
        await handle_add_bun_name(message, state_data)
    
    # Обработка добавления булочки - баллы
    elif state == BUN_STATES["waiting_for_add_bun_points"]:
        await handle_add_bun_points(message, state_data)
    
    # Обработка редактирования булочки
    elif state == BUN_STATES["waiting_for_edit_bun_points"]:
        await handle_edit_bun_points(message, state_data)
    
    # Обработка управления очками
    elif state == POINTS_STATES["waiting_for_chat_id_all"]:
        await handle_points_all_chat_id(message, state_data)
    elif state == POINTS_STATES["waiting_for_points_all"]:
        await handle_points_all_amount(message, state_data)
    elif state == POINTS_STATES["waiting_for_chat_id_user"]:
        await handle_points_user_chat_id(message, state_data)
    elif state == POINTS_STATES["waiting_for_username"]:
        await handle_points_user_username(message, state_data)
    elif state == POINTS_STATES["waiting_for_points_user"]:
        await handle_points_user_amount(message, state_data)
    elif state == POINTS_STATES["waiting_for_chat_id_set"]:
        await handle_set_points_chat_id(message, state_data)
    elif state == POINTS_STATES["waiting_for_username_set"]:
        await handle_set_points_username(message, state_data)
    elif state == POINTS_STATES["waiting_for_points_set"]:
        await handle_set_points_amount(message, state_data)


async def handle_send_message(message: types.Message, state_data: dict):
    """Обработка отправки сообщения в чат."""
    chat_id = state_data["chat_id"]
    chat_title = state_data["chat_title"]
    user_message = message.text
    
    # Очищаем состояние
    del user_states[message.from_user.id]
    
    try:
        # Отправляем сообщение в выбранный чат
        sent_message = await message.bot.send_message(
            chat_id=chat_id,
            text=user_message,
            parse_mode="HTML"
        )
        
        success_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📬 Отправить другое сообщение", callback_data="cmd_send_to_chat")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_other")]
        ])
        
        await message.reply(
            f"✅ <b>Сообщение успешно отправлено!</b>\n\n"
            f"Чат: <b>{chat_title}</b>\n"
            f"ID: <code>{chat_id}</code>\n"
            f"Message ID: <code>{sent_message.message_id}</code>\n\n"
            f"<b>Отправленное сообщение:</b>\n"
            f"<blockquote>{user_message[:200]}{'...' if len(user_message) > 200 else ''}</blockquote>",
            parse_mode="HTML",
            reply_markup=success_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_send_to_chat")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_other")]
        ])
        
        await message.reply(
            f"❌ <b>Ошибка при отправке сообщения</b>\n\n"
            f"Чат: <b>{chat_title}</b>\n"
            f"ID: <code>{chat_id}</code>\n\n"
            f"Ошибка: <code>{str(e)}</code>\n\n"
            f"Возможные причины:\n"
            f"• Бот не добавлен в чат\n"
            f"• Бот не является администратором\n"
            f"• Чат был удален",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )


async def handle_add_bun_name(message: types.Message, state_data: dict):
    """Обработка ввода названия новой булочки."""
    bun_name = message.text.strip()
    
    # Валидация названия
    if len(bun_name) < 2 or len(bun_name) > 50:
        await message.reply(
            "❌ <b>Некорректное название булочки</b>\n\n"
            "Название должно содержать от 2 до 50 символов.\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Проверяем, не существует ли уже такая булочка
    existing_buns = await get_all_buns()
    if bun_name in existing_buns:
        await message.reply(
            f"❌ <b>Булочка уже существует</b>\n\n"
            f"Булочка с названием <b>{bun_name}</b> уже есть в базе данных.\n"
            f"Текущие баллы: <b>{existing_buns[bun_name]}</b>\n\n"
            f"Используйте другое название или отредактируйте существующую булочку.",
            parse_mode="HTML"
        )
        return
    
    # Обновляем состояние
    user_states[message.from_user.id] = {
        "state": BUN_STATES["waiting_for_add_bun_points"],
        "bun_name": bun_name
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="add_bun_cancel")]
    ])
    
    await message.reply(
        f"➕ <b>Добавление новой булочки</b>\n\n"
        f"Название: <b>{bun_name}</b>\n\n"
        f"Шаг 2/2: Введите количество баллов для этой булочки.\n\n"
        f"💡 <i>Число должно быть больше 0</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def handle_add_bun_points(message: types.Message, state_data: dict):
    """Обработка ввода баллов для новой булочки."""
    bun_name = state_data["bun_name"]
    
    try:
        points = int(message.text.strip())
        if points <= 0:
            raise ValueError("Баллы должны быть больше 0")
    except ValueError:
        await message.reply(
            "❌ <b>Некорректное количество баллов</b>\n\n"
            "Введите целое положительное число (больше 0).\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Очищаем состояние
    del user_states[message.from_user.id]
    
    try:
        # Добавляем булочку
        bun = await add_bun(name=bun_name, points=points)
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить еще булочку", callback_data="cmd_add_bun")],
            [InlineKeyboardButton(text="📋 Посмотреть список булочек", callback_data="cmd_list_buns")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_buns")]
        ])
        
        if bun:
            await message.reply(
                f"✅ <b>Булочка успешно добавлена!</b>\n\n"
                f"Название: <b>{bun_name}</b>\n"
                f"Баллы: <b>{points}</b>\n\n"
                f"🥐 Теперь игроки могут получить эту булочку в ежедневном розыгрыше!",
                parse_mode="HTML",
                reply_markup=result_keyboard
            )
        else:
            await message.reply(
                f"❌ <b>Ошибка при добавлении</b>\n\n"
                f"Булочка с названием <b>{bun_name}</b> уже существует.",
                parse_mode="HTML",
                reply_markup=result_keyboard
            )
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_add_bun")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_buns")]
        ])
        
        await message.reply(
            f"❌ <b>Ошибка при добавлении булочки</b>\n\n"
            f"Название: <b>{bun_name}</b>\n"
            f"Баллы: <b>{points}</b>\n"
            f"Ошибка: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )


async def handle_edit_bun_points(message: types.Message, state_data: dict):
    """Обработка редактирования баллов булочки."""
    bun_name = state_data["bun_name"]
    current_points = state_data["current_points"]
    
    try:
        new_points = int(message.text.strip())
        if new_points <= 0:
            raise ValueError("Баллы должны быть больше 0")
    except ValueError:
        await message.reply(
            "❌ <b>Некорректное количество баллов</b>\n\n"
            "Введите целое положительное число (больше 0).\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Очищаем состояние
    del user_states[message.from_user.id]
    
    try:
        # Редактируем булочку
        bun = await edit_bun(name=bun_name, points=new_points)
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить еще булочку", callback_data="cmd_edit_bun")],
            [InlineKeyboardButton(text="📋 Посмотреть список булочек", callback_data="cmd_list_buns")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_buns")]
        ])
        
        if bun:
            await message.reply(
                f"✅ <b>Булочка успешно изменена!</b>\n\n"
                f"Название: <b>{bun_name}</b>\n"
                f"Было баллов: <b>{current_points}</b>\n"
                f"Стало баллов: <b>{new_points}</b>\n\n"
                f"🔄 Изменения применены к базе данных!",
                parse_mode="HTML",
                reply_markup=result_keyboard
            )
        else:
            await message.reply(
                f"❌ <b>Булочка не найдена</b>\n\n"
                f"Булочка с названием <b>{bun_name}</b> не найдена в базе данных.",
                parse_mode="HTML",
                reply_markup=result_keyboard
            )
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_edit_bun")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_buns")]
        ])
        
        await message.reply(
            f"❌ <b>Ошибка при редактировании булочки</b>\n\n"
            f"Название: <b>{bun_name}</b>\n"
            f"Новые баллы: <b>{new_points}</b>\n"
            f"Ошибка: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )


# ========== УПРАВЛЕНИЕ БУЛОЧКАМИ ==========

@admin_cntr.callback_query(F.data == "cmd_add_bun")
async def callback_add_bun_start(callback: CallbackQuery):
    """Начало интерактивного добавления булочки."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Сохраняем состояние
    user_states[callback.from_user.id] = {
        "state": BUN_STATES["waiting_for_add_bun_name"]
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="add_bun_cancel")]
    ])
    
    await callback.message.edit_text(
        "➕ <b>Добавление новой булочки</b>\n\n"
        "Шаг 1/2: Введите название новой булочки.\n\n"
        "💡 <i>Например: Круассан, Багет, Чиабатта</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_edit_bun")
async def callback_edit_bun_start(callback: CallbackQuery):
    """Начало интерактивного редактирования булочки."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем список булочек
    buns = await get_all_buns()
    if not buns:
        await callback.message.edit_text(
            "❌ В базе данных нет булочек для редактирования.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить булочку", callback_data="cmd_add_bun")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_buns")]
            ])
        )
        await callback.answer()
        return
    
    # Создаем кнопки для выбора булочки
    keyboard_rows = []
    for name, points in sorted(buns.items()):
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"🥐 {name} ({points} баллов)",
                callback_data=f"edit_select_bun_{name}"
            )
        ])
    
    keyboard_rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_buns")
    ])
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование булочки</b>\n\n"
        "Выберите булочку для изменения количества баллов:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )
    await callback.answer()


@admin_cntr.callback_query(F.data.startswith("edit_select_bun_"))
async def callback_edit_bun_input(callback: CallbackQuery):
    """Ввод новых баллов для булочки."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    bun_name = callback.data.split("edit_select_bun_", 1)[1]
    
    # Получаем текущие баллы
    buns = await get_all_buns()
    current_points = buns.get(bun_name, 0)
    
    # Сохраняем состояние
    user_states[callback.from_user.id] = {
        "state": BUN_STATES["waiting_for_edit_bun_points"],
        "bun_name": bun_name,
        "current_points": current_points
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="edit_bun_cancel")]
    ])
    
    await callback.message.edit_text(
        f"✏️ <b>Редактирование булочки</b>\n\n"
        f"Булочка: <b>{bun_name}</b>\n"
        f"Текущие баллы: <b>{current_points}</b>\n\n"
        f"Введите новое количество баллов для этой булочки.\n\n"
        f"💡 <i>Число должно быть больше 0</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_remove_bun")
async def callback_remove_bun_start(callback: CallbackQuery):
    """Начало интерактивного удаления булочки."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Получаем список булочек
    buns = await get_all_buns()
    if not buns:
        await callback.message.edit_text(
            "❌ В базе данных нет булочек для удаления.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить булочку", callback_data="cmd_add_bun")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_buns")]
            ])
        )
        await callback.answer()
        return
    
    # Создаем кнопки для выбора булочки
    keyboard_rows = []
    for name, points in sorted(buns.items()):
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"🗑 {name} ({points} баллов)",
                callback_data=f"remove_confirm_bun_{name}"
            )
        ])
    
    keyboard_rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_buns")
    ])
    
    await callback.message.edit_text(
        "🗑 <b>Удаление булочки</b>\n\n"
        "⚠️ <i>Внимание: Булочка будет удалена из базы данных!</i>\n\n"
        "Выберите булочку для удаления:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )
    await callback.answer()


@admin_cntr.callback_query(F.data.startswith("remove_confirm_bun_"))
async def callback_remove_bun_confirm(callback: CallbackQuery):
    """Подтверждение и выполнение удаления булочки."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    bun_name = callback.data.split("remove_confirm_bun_", 1)[1]
    
    try:
        success = await remove_bun(name=bun_name)
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить еще булочку", callback_data="cmd_remove_bun")],
            [InlineKeyboardButton(text="➕ Добавить новую булочку", callback_data="cmd_add_bun")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_buns")]
        ])
        
        if success:
            await callback.message.edit_text(
                f"✅ <b>Булочка успешно удалена!</b>\n\n"
                f"Название: <b>{bun_name}</b>\n\n"
                f"🗑️ Булочка полностью удалена из базы данных.\n"
                f"Игроки больше не смогут получить эту булочку.",
                parse_mode="HTML",
                reply_markup=result_keyboard
            )
        else:
            await callback.message.edit_text(
                f"❌ <b>Булочка не найдена</b>\n\n"
                f"Булочка с названием <b>{bun_name}</b> не найдена в базе данных.\n"
                f"Возможно, она уже была удалена ранее.",
                parse_mode="HTML",
                reply_markup=result_keyboard
            )
            
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_remove_bun")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_buns")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при удалении булочки</b>\n\n"
            f"Название: <b>{bun_name}</b>\n"
            f"Ошибка: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


# Обработчики отмены для булочек
@admin_cntr.callback_query(F.data.in_(["add_bun_cancel", "edit_bun_cancel"]))
async def callback_bun_cancel(callback: CallbackQuery):
    """Отмена операций с булочками."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Очищаем состояние
    if callback.from_user.id in user_states:
        del user_states[callback.from_user.id]
    
    action_name = "добавление" if "add" in callback.data else "редактирование"
    
    await callback.message.edit_text(
        f"❌ <b>{action_name.capitalize()} булочки отменено</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_buns")]
        ])
    )
    await callback.answer()


# ========== УПРАВЛЕНИЕ ОЧКАМИ ==========

@admin_cntr.callback_query(F.data == "cmd_add_points_all")
async def callback_add_points_all_start(callback: CallbackQuery):
    """Начало интерактивного добавления очков всем пользователям."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Сохраняем состояние
    user_states[callback.from_user.id] = {
        "state": POINTS_STATES["waiting_for_chat_id_all"]
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="points_cancel")]
    ])
    
    await callback.message.edit_text(
        "➕ <b>Добавление очков всем пользователям в чате</b>\n\n"
        "Шаг 1/2: Введите ID чата, в котором нужно добавить очки всем пользователям.\n\n"
        "💡 <i>Получить ID чата можно из списка пользователей</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_add_points")
async def callback_add_points_user_start(callback: CallbackQuery):
    """Начало интерактивного добавления очков пользователю."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Сохраняем состояние
    user_states[callback.from_user.id] = {
        "state": POINTS_STATES["waiting_for_chat_id_user"]
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="points_cancel")]
    ])
    
    await callback.message.edit_text(
        "➕ <b>Добавление очков пользователю</b>\n\n"
        "Шаг 1/3: Введите ID чата, в котором находится пользователь.\n\n"
        "💡 <i>Получить ID чата можно из списка пользователей</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_set_points")
async def callback_set_points_start(callback: CallbackQuery):
    """Начало интерактивного установки очков пользователю."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Сохраняем состояние
    user_states[callback.from_user.id] = {
        "state": POINTS_STATES["waiting_for_chat_id_set"]
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="points_cancel")]
    ])
    
    await callback.message.edit_text(
        "🎯 <b>Установка очков пользователю</b>\n\n"
        "Шаг 1/3: Введите ID чата, в котором находится пользователь.\n\n"
        "💡 <i>Получить ID чата можно из списка пользователей</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@admin_cntr.callback_query(F.data == "admin_help")
async def callback_admin_help(callback: CallbackQuery):
    """Обработчик справки."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await admin_help_handler_internal(callback.message)
    await callback.answer()


# ========== ВНУТРЕННИЕ ФУНКЦИИ (ПЕРЕНЕСЕННЫЕ ИЗ КОМАНД) ==========

async def user_list_handler_internal(message, bot):
    """Внутренняя функция для списка пользователей."""
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
            user_line = f"{user_count}. {display_name} (ID: <code>{user['telegram_id']}</code>) — {status}\n"

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


async def list_buns_handler_internal(message):
    """Внутренняя функция для списка булочек."""
    buns = await get_all_buns()
    if not buns:
        await message.reply("Булочек пока нет!")
        return
    text = "<b>Список булочек:</b>\n\n"
    for name, points in buns.items():
        from handlers.in_game import pluralize_points
        text += f"- {name}: {pluralize_points(points)}\n"
    await message.reply(text, parse_mode="HTML")


async def admin_help_handler_internal(message):
    """Внутренняя функция для справки админа."""
    help_text = (
        "🤖 <b>Админская панель Бота Булочка Дня</b>\n\n"
        "🎯 <b>Главное нововведение:</b> Все команды теперь доступны через удобный интерактивный интерфейс с кнопками! Просто нажмите /start в этом чате и выберите нужный раздел.\n\n"
        
        "📱 <b>ИНТЕРАКТИВНЫЕ МЕНЮ (рекомендуется):</b>\n\n"
        
        "<b>👥 Управление пользователями:</b>\n"
        "• 📋 Просмотр списка всех пользователей по чатам\n"
        "• 🗑 Полное удаление пользователя из БД (интерактивно)\n"
        "  → Выбор чата → Выбор пользователя → Подтверждение\n"
        "• 🧹 Массовое удаление всех неактивных игроков (новое!)\n"
        "  → Статистика → Подробный список → Подтверждение → Очистка БД\n\n"
        
        "<b>🥐 Управление булочками:</b>\n"
        "• 📋 Просмотр списка всех булочек с баллами\n"
        "• ➕ Добавление новой булочки (пошагово)\n"
        "  → Название → Баллы → Подтверждение\n"
        "• ✏️ Редактирование булочки (интерактивно)\n"
        "  → Выбор булочки → Новые баллы → Сохранение\n"
        "• 🗑 Удаление булочки (интерактивно)\n"
        "  → Выбор булочки → Подтверждение удаления\n\n"
        
        "<b>🎯 Управление очками:</b>\n"
        "• ➕ Добавить очки всем в чате (пошагово)\n"
        "  → ID чата → Количество очков → Автоотправка\n"
        "• ➕ Добавить очки пользователю (пошагово)\n"
        "  → ID чата → Username → Очки → Автоотправка\n"
        "• 🎯 Установить точное количество очков (новое!)\n"
        "  → ID чата → Username → Итоговые очки\n"
        "• 💡 Поддержка диапазонов: 5-10 (случайное значение)\n"
        "• 💡 Отрицательные числа отнимают очки\n\n"
        
        "<b>🔧 Другие функции:</b>\n"
        "• 📬 Отправка сообщений в чаты (интерактивно)\n"
        "  → Выбор чата → Ввод сообщения → Отправка\n"
        "• 🥐 Массовая отправка Булочки Дня во все чаты\n"
        "• 🌇 Отправка вечернего юморного сообщения (тест функции)\n"
        "  → Автоматически отправляется каждый день в случайное время 18:00-22:00 МСК\n"
        "• 🕐 Статус расписания вечерних сообщений (диагностика)\n"
        "  → Проверка времени, статуса планировщика, следующей отправки\n\n"
        
        "⌨️ <b>КЛАССИЧЕСКИЕ КОМАНДЫ (для экспертов):</b>\n"
        "<code>/user_list</code> - Список пользователей\n"
        "<code>/list_buns</code> - Список булочек\n"
        "<code>/add_bun название баллы</code> - Добавить булочку\n"
        "<code>/edit_bun название баллы</code> - Изменить булочку\n"
        "<code>/remove_bun название</code> - Удалить булочку\n"
        "<code>/add_points_all chat_id баллы</code> - Очки всем\n"
        "<code>/add_points chat_id @username баллы</code> - Очки пользователю\n"
        "<code>/send_to_chat chat_id</code> - Отправить Булочку Дня\n\n"
        
        "✨ <b>Почему интерактивный интерфейс лучше?</b>\n"
        "• 🎯 Не нужно запоминать синтаксис команд\n"
        "• 🛡️ Автоматическая валидация данных\n"
        "• 📝 Пошаговые подсказки и помощь\n"
        "• ❌ Возможность отменить операцию на любом этапе\n"
        "• 🔄 Удобные кнопки для повторных действий\n\n"
        
        "<b>🚀 Для начала работы нажмите</b> <code>/start</code> <b>в этом чате!</b>"
    )
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Перейти к панели управления", callback_data="back_to_main")],
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="🥐 Управление булочками", callback_data="admin_buns")],
        [InlineKeyboardButton(text="🎯 Управление очками", callback_data="admin_points")]
    ])
    
    await message.reply(help_text, parse_mode="HTML", reply_markup=back_keyboard)


@admin_cntr.message(Command(commands="user_list"))
async def user_list_handler(message: types.Message, bot):
    """Вывод списка всех пользователей по чатам с названиями чатов (только для admin в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return
    
    await user_list_handler_internal(message, bot)


@admin_cntr.message(Command(commands="remove_from_game"))
async def remove_from_game_handler(message: types.Message):
    """Удаление пользователя из розыгрыша по chat_id и telegram_id (только для admin в ЛС)."""
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply(
            "Эта команда доступна только администратору в личных сообщениях!"
        )
        return

    # Ожидаем два аргумента: chat_id и telegram_id
    args = message.text.split()[1:]  # Пропускаем саму команду
    if len(args) != 2:
        await message.reply(
            "Использование: /remove_from_game <chat_id> <telegram_id>\n\n"
            "Получить telegram_id можно из команды /user_list"
        )
        return

    try:
        chat_id = int(args[0])  # chat_id как целое число
        telegram_id = int(args[1])  # telegram_id пользователя
    except ValueError:
        await message.reply("chat_id и telegram_id должны быть целыми числами!")
        return

    # Получаем список всех пользователей для проверки существования
    users = await get_all_users()
    if not users:
        await message.reply("Список пользователей пуст.")
        return

    # Ищем пользователя с указанными chat_id и telegram_id
    target_user = None
    for user in users:
        if user["chat_id"] == chat_id and user["telegram_id"] == telegram_id:
            target_user = user
            break

    if not target_user:
        await message.reply(
            f"Пользователь с telegram_id {telegram_id} не найден в чате {chat_id}.\n"
            f"Проверьте правильность данных с помощью /user_list"
        )
        return

    display_name = (
        f"@{target_user['username']}"
        if target_user["username"]
        else target_user["full_name"]
    )

    # Удаляем пользователя из розыгрыша
    removed = await remove_user_from_game(telegram_id=telegram_id, chat_id=chat_id)
    if removed:
        await message.reply(
            f"✅ Пользователь {display_name} (ID: {telegram_id}) удален из розыгрыша в чате {chat_id}."
        )
    else:
        await message.reply(
            f"ℹ️ Пользователь {display_name} (ID: {telegram_id}) уже не участвует в игре в чате {chat_id}."
        )


@admin_cntr.message(Command(commands="list_buns"))
async def list_buns_handler(message: types.Message):
    if message.chat.type != "private" or message.from_user.id != ADMIN:
        await message.reply("Эта команда доступна только администратору в ЛС!")
        return
    await list_buns_handler_internal(message)


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
    
    await admin_help_handler_internal(message)


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


# ========== ОБРАБОТЧИКИ ДЛЯ УПРАВЛЕНИЯ ОЧКАМИ ==========

async def handle_points_all_chat_id(message: types.Message, state_data: dict):
    """Обработка ввода chat_id для добавления очков всем."""
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.reply(
            "❌ <b>Некорректный ID чата</b>\n\n"
            "ID чата должен быть целым числом.\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Проверяем существование чата и пользователей
    users = await get_all_users()
    chat_users = [u for u in users if u["chat_id"] == chat_id and u["in_game"]]
    
    if not chat_users:
        await message.reply(
            f"❌ <b>Чат не найден или нет активных игроков</b>\n\n"
            f"В чате с ID <code>{chat_id}</code> нет активных пользователей игры.\n"
            f"Проверьте правильность ID чата или добавьте пользователей в игру.",
            parse_mode="HTML"
        )
        return
    
    # Получаем название чата
    try:
        chat = await message.bot.get_chat(chat_id)
        chat_title = chat.title if chat.title else f"Чат {chat_id}"
    except:
        chat_title = f"Чат {chat_id}"
    
    # Обновляем состояние
    user_states[message.from_user.id] = {
        "state": POINTS_STATES["waiting_for_points_all"],
        "chat_id": chat_id,
        "chat_title": chat_title,
        "user_count": len(chat_users)
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="points_cancel")]
    ])
    
    await message.reply(
        f"➕ <b>Добавление очков всем пользователям</b>\n\n"
        f"Чат: <b>{chat_title}</b>\n"
        f"ID: <code>{chat_id}</code>\n"
        f"Активных игроков: <b>{len(chat_users)}</b>\n\n"
        f"Шаг 2/2: Введите количество очков для добавления всем пользователям.\n\n"
        f"💡 <i>Можно использовать диапазон: 5-10 (каждый получит случайное число из диапазона)</i>\n"
        f"💡 <i>Отрицательные числа отнимают очки</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def handle_points_all_amount(message: types.Message, state_data: dict):
    """Обработка ввода количества очков для всех пользователей."""
    chat_id = state_data["chat_id"]
    chat_title = state_data["chat_title"]
    user_count = state_data["user_count"]
    points_text = message.text.strip()
    
    # Парсим очки
    try:
        if "-" in points_text and not points_text.startswith("-"):
            min_points, max_points = map(int, points_text.split("-"))
            if min_points > max_points:
                raise ValueError("Минимум больше максимума")
            points_display = f"{min_points}-{max_points}"
        else:
            points = int(points_text)
            min_points = max_points = points
            points_display = str(points)
    except ValueError:
        await message.reply(
            "❌ <b>Некорректное количество очков</b>\n\n"
            "Введите целое число или диапазон (например: 5 или 3-7).\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Очищаем состояние
    del user_states[message.from_user.id]
    
    try:
        # Импортируем функцию из admin_points
        from handlers.admin_points import apply_points_to_user
        import random
        
        # Получаем пользователей чата
        users = await get_all_users()
        chat_users = [u for u in users if u["chat_id"] == chat_id and u["in_game"]]
        
        updated_count = 0
        for user_data in chat_users:
            points = random.randint(min_points, max_points) if min_points != max_points else min_points
            new_points, is_new_croissant = await apply_points_to_user(
                user_data["telegram_id"], chat_id, points
            )
            if is_new_croissant:
                await message.bot.send_message(
                    chat_id,
                    f"@{user_data['username']} получил стартовый Круассан с {new_points} очками!"
                )
            updated_count += 1
        
        # Отправляем сообщение в чат
        if min_points > 0:
            chat_message = f"🎉 Хлебобулочная система замесила {points_display} очков для всех в чате! Подкреплено: {updated_count} булочников."
            emoji = "🎉"
        else:
            abs_points = f"{abs(min_points)}-{abs(max_points)}" if min_points != max_points else str(abs(min_points))
            chat_message = f"🍞 Хлебный бунт! У всех булочников чата отнято {abs_points} очков, пострадало: {updated_count} пекарей."
            emoji = "🍞"
        
        await message.bot.send_message(chat_id, chat_message)
        await message.bot.send_message(chat_id, emoji)
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить очки еще раз", callback_data="cmd_add_points_all")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_points")]
        ])
        
        await message.reply(
            f"✅ <b>Очки успешно добавлены!</b>\n\n"
            f"Чат: <b>{chat_title}</b>\n"
            f"ID: <code>{chat_id}</code>\n"
            f"Очки: <b>{points_display}</b>\n"
            f"Обработано пользователей: <b>{updated_count}</b>",
            parse_mode="HTML",
            reply_markup=result_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_add_points_all")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_points")]
        ])
        
        await message.reply(
            f"❌ <b>Ошибка при добавлении очков</b>\n\n"
            f"Чат: <b>{chat_title}</b>\n"
            f"Очки: <b>{points_display}</b>\n"
            f"Ошибка: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )


async def handle_points_user_chat_id(message: types.Message, state_data: dict):
    """Обработка ввода chat_id для добавления очков пользователю."""
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.reply(
            "❌ <b>Некорректный ID чата</b>\n\n"
            "ID чата должен быть целым числом.\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Проверяем существование чата и пользователей
    users = await get_all_users()
    chat_users = [u for u in users if u["chat_id"] == chat_id and u["in_game"]]
    
    if not chat_users:
        await message.reply(
            f"❌ <b>Чат не найден или нет активных игроков</b>\n\n"
            f"В чате с ID <code>{chat_id}</code> нет активных пользователей игры.\n"
            f"Проверьте правильность ID чата.",
            parse_mode="HTML"
        )
        return
    
    # Получаем название чата
    try:
        chat = await message.bot.get_chat(chat_id)
        chat_title = chat.title if chat.title else f"Чат {chat_id}"
    except:
        chat_title = f"Чат {chat_id}"
    
    # Обновляем состояние
    user_states[message.from_user.id] = {
        "state": POINTS_STATES["waiting_for_username"],
        "chat_id": chat_id,
        "chat_title": chat_title
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="points_cancel")]
    ])
    
    await message.reply(
        f"➕ <b>Добавление очков пользователю</b>\n\n"
        f"Чат: <b>{chat_title}</b>\n"
        f"ID: <code>{chat_id}</code>\n\n"
        f"Шаг 2/3: Введите username пользователя (с @).\n\n"
        f"💡 <i>Например: @username</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def handle_points_user_username(message: types.Message, state_data: dict):
    """Обработка ввода username для добавления очков."""
    chat_id = state_data["chat_id"]
    chat_title = state_data["chat_title"]
    username_text = message.text.strip()
    
    # Парсим username
    if not username_text.startswith("@"):
        await message.reply(
            "❌ <b>Некорректный username</b>\n\n"
            "Username должен начинаться с @\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    username = username_text[1:]  # Убираем @
    
    # Проверяем существование пользователя
    from database.queries import get_user_by_username
    user = await get_user_by_username(chat_id, username)
    
    if not user or not user.in_game:
        await message.reply(
            f"❌ <b>Пользователь не найден</b>\n\n"
            f"Пользователь @{username} не найден в чате или не участвует в игре.\n"
            f"Проверьте правильность username.",
            parse_mode="HTML"
        )
        return
    
    # Обновляем состояние
    user_states[message.from_user.id] = {
        "state": POINTS_STATES["waiting_for_points_user"],
        "chat_id": chat_id,
        "chat_title": chat_title,
        "username": username,
        "user": user
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="points_cancel")]
    ])
    
    await message.reply(
        f"➕ <b>Добавление очков пользователю</b>\n\n"
        f"Чат: <b>{chat_title}</b>\n"
        f"Пользователь: <b>@{username}</b>\n\n"
        f"Шаг 3/3: Введите количество очков для добавления.\n\n"
        f"💡 <i>Можно использовать диапазон: 5-10</i>\n"
        f"💡 <i>Отрицательные числа отнимают очки</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def handle_points_user_amount(message: types.Message, state_data: dict):
    """Обработка ввода количества очков для пользователя."""
    chat_id = state_data["chat_id"]
    chat_title = state_data["chat_title"]
    username = state_data["username"]
    user = state_data["user"]
    points_text = message.text.strip()
    
    # Парсим очки
    import random
    try:
        if "-" in points_text and not points_text.startswith("-"):
            min_points, max_points = map(int, points_text.split("-"))
            if min_points > max_points:
                raise ValueError("Минимум больше максимума")
            points = random.randint(min_points, max_points)
            points_display = f"{min_points}-{max_points} (выпало: {points})"
        else:
            points = int(points_text)
            points_display = str(points)
    except ValueError:
        await message.reply(
            "❌ <b>Некорректное количество очков</b>\n\n"
            "Введите целое число или диапазон (например: 5 или 3-7).\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Очищаем состояние
    del user_states[message.from_user.id]
    
    try:
        # Импортируем функцию из admin_points
        from handlers.admin_points import apply_points_to_user
        import random
        
        # Применяем очки
        new_points, is_new_croissant = await apply_points_to_user(
            user.telegram_id, chat_id, points
        )
        
        if is_new_croissant:
            await message.bot.send_message(
                chat_id, f"@{username} получил стартовый Круассан с {new_points} очками!"
            )
        
        # Отправляем сообщение в чат
        if points > 0:
            chat_message = f"Секретный рецепт всыпал {abs(points)} очков булочнику @{username}! Свежая выпечка в деле."
            emoji = "🎉"
        else:
            chat_message = f"У @{username} конфисковали {abs(points)} очков — тесто не подошло!"
            emoji = "🍞"
        
        await message.bot.send_message(chat_id, chat_message)
        await message.bot.send_message(chat_id, emoji)
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить очки еще пользователю", callback_data="cmd_add_points")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_points")]
        ])
        
        await message.reply(
            f"✅ <b>Очки успешно добавлены!</b>\n\n"
            f"Чат: <b>{chat_title}</b>\n"
            f"Пользователь: <b>@{username}</b>\n"
            f"Очки: <b>{points_display}</b>\n"
            f"Новый баланс: <b>{new_points}</b>",
            parse_mode="HTML",
            reply_markup=result_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_add_points")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_points")]
        ])
        
        await message.reply(
            f"❌ <b>Ошибка при добавлении очков</b>\n\n"
            f"Пользователь: <b>@{username}</b>\n"
            f"Очки: <b>{points_display}</b>\n"
            f"Ошибка: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )


async def handle_set_points_chat_id(message: types.Message, state_data: dict):
    """Обработка ввода chat_id для установки очков пользователю."""
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.reply(
            "❌ <b>Некорректный ID чата</b>\n\n"
            "ID чата должен быть целым числом.\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Проверяем существование чата и пользователей
    users = await get_all_users()
    chat_users = [u for u in users if u["chat_id"] == chat_id and u["in_game"]]
    
    if not chat_users:
        await message.reply(
            f"❌ <b>Чат не найден или нет активных игроков</b>\n\n"
            f"В чате с ID <code>{chat_id}</code> нет активных пользователей игры.\n"
            f"Проверьте правильность ID чата.",
            parse_mode="HTML"
        )
        return
    
    # Получаем название чата
    try:
        chat = await message.bot.get_chat(chat_id)
        chat_title = chat.title if chat.title else f"Чат {chat_id}"
    except:
        chat_title = f"Чат {chat_id}"
    
    # Обновляем состояние
    user_states[message.from_user.id] = {
        "state": POINTS_STATES["waiting_for_username_set"],
        "chat_id": chat_id,
        "chat_title": chat_title
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="points_cancel")]
    ])
    
    await message.reply(
        f"🎯 <b>Установка очков пользователю</b>\n\n"
        f"Чат: <b>{chat_title}</b>\n"
        f"ID: <code>{chat_id}</code>\n\n"
        f"Шаг 2/3: Введите username пользователя (с @).\n\n"
        f"💡 <i>Например: @username</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def handle_set_points_username(message: types.Message, state_data: dict):
    """Обработка ввода username для установки очков."""
    chat_id = state_data["chat_id"]
    chat_title = state_data["chat_title"]
    username_text = message.text.strip()
    
    # Парсим username
    if not username_text.startswith("@"):
        await message.reply(
            "❌ <b>Некорректный username</b>\n\n"
            "Username должен начинаться с @\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    username = username_text[1:]  # Убираем @
    
    # Проверяем существование пользователя
    from database.queries import get_user_by_username, get_user_buns_stats
    user = await get_user_by_username(chat_id, username)
    
    if not user or not user.in_game:
        await message.reply(
            f"❌ <b>Пользователь не найден</b>\n\n"
            f"Пользователь @{username} не найден в чате или не участвует в игре.\n"
            f"Проверьте правильность username.",
            parse_mode="HTML"
        )
        return
    
    # Получаем текущие очки
    buns = await get_user_buns_stats(user.telegram_id, chat_id)
    current_points = sum(bun["points"] for bun in buns) if buns else 0
    
    # Обновляем состояние
    user_states[message.from_user.id] = {
        "state": POINTS_STATES["waiting_for_points_set"],
        "chat_id": chat_id,
        "chat_title": chat_title,
        "username": username,
        "user": user,
        "current_points": current_points
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="points_cancel")]
    ])
    
    await message.reply(
        f"🎯 <b>Установка очков пользователю</b>\n\n"
        f"Чат: <b>{chat_title}</b>\n"
        f"Пользователь: <b>@{username}</b>\n"
        f"Текущие очки: <b>{current_points}</b>\n\n"
        f"Шаг 3/3: Введите новое общее количество очков.\n\n"
        f"💡 <i>Это будет итоговое количество очков (не добавляется к текущим)</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def handle_set_points_amount(message: types.Message, state_data: dict):
    """Обработка ввода итогового количества очков для пользователя."""
    chat_id = state_data["chat_id"]
    chat_title = state_data["chat_title"]
    username = state_data["username"]
    user = state_data["user"]
    current_points = state_data["current_points"]
    points_text = message.text.strip()
    
    # Парсим очки
    try:
        new_total = int(points_text)
        if new_total < 0:
            raise ValueError("Очки не могут быть отрицательными")
    except ValueError:
        await message.reply(
            "❌ <b>Некорректное количество очков</b>\n\n"
            "Введите неотрицательное целое число.\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        return
    
    # Вычисляем разницу
    points_diff = new_total - current_points
    
    # Очищаем состояние
    del user_states[message.from_user.id]
    
    try:
        # Применяем изменение очков
        from handlers.admin_points import apply_points_to_user
        
        new_points, is_new_croissant = await apply_points_to_user(
            user.telegram_id, chat_id, points_diff
        )
        
        if is_new_croissant:
            await message.bot.send_message(
                chat_id, f"@{username} получил стартовый Круассан с {new_points} очками!"
            )
        
        # Отправляем сообщение в чат (только если изменение значительное)
        if abs(points_diff) > 0:
            if points_diff > 0:
                chat_message = f"🎯 Админ установил @{username} {new_total} очков! Добавлено: {points_diff}."
            elif points_diff < 0:
                chat_message = f"🎯 Админ установил @{username} {new_total} очков! Убрано: {abs(points_diff)}."
            else:
                chat_message = f"🎯 Очки @{username} остались без изменений: {new_total}."
            
            await message.bot.send_message(chat_id, chat_message)
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Установить очки еще пользователю", callback_data="cmd_set_points")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_points")]
        ])
        
        change_text = ""
        if points_diff > 0:
            change_text = f"(+{points_diff})"
        elif points_diff < 0:
            change_text = f"({points_diff})"
        else:
            change_text = "(без изменений)"
        
        await message.reply(
            f"✅ <b>Очки успешно установлены!</b>\n\n"
            f"Чат: <b>{chat_title}</b>\n"
            f"Пользователь: <b>@{username}</b>\n"
            f"Было очков: <b>{current_points}</b>\n"
            f"Стало очков: <b>{new_total}</b> {change_text}",
            parse_mode="HTML",
            reply_markup=result_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_set_points")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_points")]
        ])
        
        await message.reply(
            f"❌ <b>Ошибка при установке очков</b>\n\n"
            f"Пользователь: <b>@{username}</b>\n"
            f"Новые очки: <b>{new_total}</b>\n"
            f"Ошибка: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )


@admin_cntr.callback_query(F.data == "cmd_send_evening_humor")
async def callback_send_evening_humor(callback: CallbackQuery):
    """Отправка вечернего юморного сообщения во все активные чаты."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        await callback.message.edit_text(
            "🔄 <b>Отправка вечернего юморного сообщения...</b>\n\n"
            "Начинаю отправку во все активные чаты...",
            parse_mode="HTML"
        )
        
        # Получаем активные чаты
        from database.queries import get_active_chat_ids
        chat_ids = await get_active_chat_ids()
        
        if not chat_ids:
            await callback.message.edit_text(
                "❌ Нет активных чатов для отправки вечернего юмора.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")]
                ])
            )
            return
        
        # Используем функцию из evening_humor модуля
        await send_evening_humor(callback.bot)
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌇 Отправить еще раз", callback_data="cmd_send_evening_humor")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")]
        ])
        
        await callback.message.edit_text(
            f"✅ <b>Вечернее юморное сообщение отправлено!</b>\n\n"
            f"📊 <b>Результат:</b>\n"
            f"• Найдено активных чатов: {len(chat_ids)}\n"
            f"• Отправлено случайное юморное сообщение\n\n"
            f"💡 <i>Обычно вечерние сообщения отправляются автоматически каждый день в случайное время с 18:00 до 22:00 по МСК</i>",
            parse_mode="HTML",
            reply_markup=result_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_send_evening_humor")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при отправке вечернего юмора</b>\n\n"
            f"Детали: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_evening_schedule_status")
async def callback_evening_schedule_status(callback: CallbackQuery):
    """Показать статус расписания вечерних сообщений."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        # Получаем информацию о расписании
        schedule_info = get_evening_schedule_info()
        
        # Получаем информацию о статусе cron задачи
        try:
            from main import evening_cron_task
            task_status = "Активна" if evening_cron_task and hasattr(evening_cron_task, 'started') and evening_cron_task.started else "Не активна"
        except (ImportError, AttributeError):
            task_status = "Недоступно"
        
        status_text = f"🕐 <b>Статус расписания вечерних сообщений</b>\n\n"
        status_text += f"⏰ <b>Текущее время МСК:</b> {schedule_info['current_moscow_time']}\n"
        status_text += f"🎯 <b>Рабочее окно:</b> {schedule_info['evening_window']}\n"
        status_text += f"📍 <b>Текущий час:</b> {schedule_info['current_moscow_hour']}:xx МСК\n"
        status_text += f"✅ <b>Подходящее время?</b> {'Да' if schedule_info['is_evening_time'] else 'Нет'}\n\n"
        
        status_text += f"🤖 <b>Статус планировщика:</b> {task_status}\n"
        status_text += f"📅 <b>Следующая возможность:</b> {schedule_info['next_possible_time']}\n\n"
        
        if schedule_info['is_evening_time']:
            status_text += "💡 <b>Сейчас подходящее время для отправки!</b>\n"
            status_text += "Вы можете протестировать функцию прямо сейчас.\n\n"
        else:
            if schedule_info['current_moscow_hour'] < 18:
                hours_left = 18 - schedule_info['current_moscow_hour']
                status_text += f"⏳ <b>До начала окна:</b> {hours_left} ч.\n"
            else:
                hours_left = 24 - schedule_info['current_moscow_hour'] + 18
                status_text += f"⏳ <b>До следующего окна:</b> {hours_left} ч.\n"
        
        status_text += "📋 <b>Справка:</b>\n"
        status_text += "• Каждый день планируется случайное время в окне 18:00-22:00 МСК\n"
        status_text += "• После отправки сообщения автоматически планируется следующее\n"
        status_text += "• Планировщик должен быть всегда активен"
        
        # Добавляем кнопку перезапуска если планировщик неактивен
        keyboard_buttons = [
            [InlineKeyboardButton(text="🌇 Тест отправки", callback_data="cmd_send_evening_humor")]
        ]
        
        if task_status != "Активна":
            keyboard_buttons.append([InlineKeyboardButton(text="🔄 Перезапустить планировщик", callback_data="cmd_restart_evening_scheduler")])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="cmd_evening_schedule_status")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            status_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_evening_schedule_status")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при получении статуса</b>\n\n"
            f"Детали: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_restart_evening_scheduler")
async def callback_restart_evening_scheduler(callback: CallbackQuery):
    """Перезапуск планировщика вечерних сообщений."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        await callback.message.edit_text(
            "🔄 <b>Перезапуск планировщика вечерних сообщений...</b>\n\n"
            "⏳ Останавливаем старую задачу...\n"
            "⏳ Создаем новое расписание...\n"
            "⏳ Запускаем планировщик...",
            parse_mode="HTML"
        )
        
        # Импортируем функцию планирования
        from main import schedule_random_evening_message
        
        # Перезапускаем планировщик
        await schedule_random_evening_message(callback.bot)
        
        # Получаем обновленную информацию
        schedule_info = get_evening_schedule_info()
        
        success_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕐 Проверить статус", callback_data="cmd_evening_schedule_status")],
            [InlineKeyboardButton(text="🌇 Тест отправки", callback_data="cmd_send_evening_humor")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")]
        ])
        
        await callback.message.edit_text(
            f"✅ <b>Планировщик перезапущен!</b>\n\n"
            f"🤖 <b>Новое расписание создано</b>\n"
            f"⏰ <b>Текущее время МСК:</b> {schedule_info['current_moscow_time']}\n"
            f"🎯 <b>Рабочее окно:</b> {schedule_info['evening_window']}\n"
            f"✅ <b>Подходящее время?</b> {'Да' if schedule_info['is_evening_time'] else 'Нет'}\n\n"
            f"📋 <b>Что произошло:</b>\n"
            f"• Остановлена предыдущая задача\n"
            f"• Создано новое случайное время в окне 18:00-22:00 МСК\n"
            f"• Планировщик активирован\n\n"
            f"💡 <b>Проверьте логи</b> для подтверждения времени отправки!",
            parse_mode="HTML",
            reply_markup=success_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_restart_evening_scheduler")],
            [InlineKeyboardButton(text="🕐 Статус", callback_data="cmd_evening_schedule_status")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_other")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при перезапуске планировщика</b>\n\n"
            f"Детали: <code>{str(e)}</code>\n\n"
            f"💡 Попробуйте перезапустить весь бот или обратитесь к разработчику.",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


@admin_cntr.callback_query(F.data == "cmd_cleanup_inactive_users")
async def callback_cleanup_inactive_users(callback: CallbackQuery):
    """Массовое удаление всех неактивных пользователей."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        # Получаем количество неактивных пользователей для предварительной информации
        inactive_count = await get_inactive_users_count()
        
        if inactive_count == 0:
            await callback.message.edit_text(
                "✅ <b>Нет неактивных пользователей</b>\n\n"
                "Все пользователи в базе данных активно участвуют в игре.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
                ])
            )
            return
        
        # Получаем детальную информацию по чатам
        inactive_by_chat = await get_inactive_users_by_chat()
        
        # Формируем подробный отчет
        report_text = f"🧹 <b>Массовое удаление неактивных пользователей</b>\n\n"
        report_text += f"📊 <b>Найдено неактивных пользователей: {inactive_count}</b>\n\n"
        
        chat_count = len(inactive_by_chat)
        if chat_count > 0:
            report_text += f"📈 <b>Распределение по чатам:</b>\n"
            for chat_id, users in inactive_by_chat.items():
                user_count = len(users)
                report_text += f"• Чат {chat_id}: {user_count} пользователей\n"
            report_text += "\n"
        
        report_text += "⚠️ <b>Внимание:</b> Будут полностью удалены:\n"
        report_text += "• Профили пользователей\n"
        report_text += "• Все их булочки и очки\n"
        report_text += "• История ежедневных выборов\n\n"
        report_text += "❗ <b>Это действие необратимо!</b>\n\n"
        report_text += "Продолжить массовое удаление?"
        
        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить всех", callback_data="confirm_bulk_cleanup"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="👀 Показать подробный список", callback_data="show_inactive_details")
            ]
        ])
        
        await callback.message.edit_text(
            report_text,
            parse_mode="HTML",
            reply_markup=confirm_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_cleanup_inactive_users")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при подготовке удаления</b>\n\n"
            f"Детали: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


@admin_cntr.callback_query(F.data == "show_inactive_details")
async def callback_show_inactive_details(callback: CallbackQuery):
    """Показать детальный список неактивных пользователей."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        inactive_by_chat = await get_inactive_users_by_chat()
        
        if not inactive_by_chat:
            await callback.message.edit_text(
                "✅ <b>Нет неактивных пользователей</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
                ])
            )
            return
        
        # Формируем детальный отчет
        report_parts = []
        current_part = "👀 <b>Неактивные пользователи по чатам:</b>\n\n"
        
        for chat_id, users in inactive_by_chat.items():
            chat_section = f"📍 <b>Чат {chat_id}:</b>\n"
            for user in users:
                display_name = f"@{user['username']}" if user['username'] else user['full_name']
                chat_section += f"• {display_name} (ID: {user['telegram_id']})\n"
            chat_section += "\n"
            
            # Проверяем, не превысит ли добавление новой секции лимит сообщения
            if len(current_part + chat_section) > 3500:  # Оставляем запас для кнопок
                report_parts.append(current_part)
                current_part = chat_section
            else:
                current_part += chat_section
        
        # Добавляем последнюю часть
        if current_part.strip():
            report_parts.append(current_part)
        
        # Отправляем части отчета
        for i, part in enumerate(report_parts):
            if i == 0:
                # Редактируем первое сообщение
                await callback.message.edit_text(
                    part,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Назад к удалению", callback_data="cmd_cleanup_inactive_users")]
                    ])
                )
            else:
                # Отправляем дополнительные сообщения
                await callback.message.answer(part, parse_mode="HTML")
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cmd_cleanup_inactive_users")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при получении списка</b>\n\n"
            f"Детали: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


@admin_cntr.callback_query(F.data == "confirm_bulk_cleanup")
async def callback_confirm_bulk_cleanup(callback: CallbackQuery):
    """Подтверждение и выполнение массового удаления неактивных пользователей."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        await callback.message.edit_text(
            "🔄 <b>Выполнение массового удаления...</b>\n\n"
            "Удаление неактивных пользователей из всех таблиц...\n"
            "⏳ Пожалуйста, подождите...",
            parse_mode="HTML"
        )
        
        # Выполняем массовое удаление
        deleted_count, deleted_by_chat = await bulk_delete_inactive_users()
        
        if deleted_count == 0:
            await callback.message.edit_text(
                "✅ <b>Удаление завершено</b>\n\n"
                "Неактивных пользователей не найдено.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
                ])
            )
            return
        
        # Формируем отчет об удалении
        report_text = f"✅ <b>Массовое удаление завершено!</b>\n\n"
        report_text += f"🗑️ <b>Удалено пользователей: {deleted_count}</b>\n\n"
        
        if deleted_by_chat:
            report_text += f"📊 <b>Статистика по чатам:</b>\n"
            for chat_id, users in deleted_by_chat.items():
                report_text += f"📍 <b>Чат {chat_id}:</b> {len(users)} пользователей\n"
                # Показываем первых нескольких пользователей
                for i, user in enumerate(users[:3]):
                    report_text += f"  • {user['display_name']}\n"
                if len(users) > 3:
                    report_text += f"  • ... и еще {len(users) - 3}\n"
                report_text += "\n"
        
        report_text += "🧹 <b>Очищены данные:</b>\n"
        report_text += "• Профили пользователей\n"
        report_text += "• Все булочки и очки\n"
        report_text += "• История ежедневных выборов\n\n"
        report_text += "💾 База данных оптимизирована!"
        
        result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Очистить еще раз", callback_data="cmd_cleanup_inactive_users")],
            [InlineKeyboardButton(text="📋 Список пользователей", callback_data="cmd_user_list")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        
        await callback.message.edit_text(
            report_text,
            parse_mode="HTML",
            reply_markup=result_keyboard
        )
        
    except Exception as e:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="cmd_cleanup_inactive_users")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        
        await callback.message.edit_text(
            f"❌ <b>Ошибка при массовом удалении</b>\n\n"
            f"Некоторые пользователи могли быть удалены частично.\n"
            f"Детали: <code>{str(e)}</code>",
            parse_mode="HTML",
            reply_markup=error_keyboard
        )
    
    await callback.answer()


# Обработчик отмены для очков
@admin_cntr.callback_query(F.data == "points_cancel")
async def callback_points_cancel(callback: CallbackQuery):
    """Отмена операций с очками."""
    if callback.from_user.id != ADMIN:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    # Очищаем состояние
    if callback.from_user.id in user_states:
        del user_states[callback.from_user.id]
    
    await callback.message.edit_text(
        "❌ <b>Операция с очками отменена</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_points")]
        ])
    )
    await callback.answer()
