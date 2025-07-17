from sqlalchemy import func, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import with_session
from database.models import User, UserBun, Bun, GameSetting
import random

from logger import logger


@with_session
async def add_user(
    session: AsyncSession, telegram_id: int, chat_id: int, username: str, full_name: str
):
    """Добавление нового пользователя или обновление статуса в игре."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()
    if user:
        if not user.in_game:
            user.in_game = True
            await session.commit()
        return user
    new_user = User(
        telegram_id=telegram_id,
        chat_id=chat_id,
        username=username,
        full_name=full_name,
        in_game=True,
    )
    session.add(new_user)
    await session.commit()
    return new_user


@with_session
async def get_user_by_id(session: AsyncSession, telegram_id: int, chat_id: int):
    """Получение пользователя по telegram_id и chat_id."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id, User.chat_id == chat_id)
    )
    return result.scalars().first()


@with_session
async def add_user_to_game(session: AsyncSession, telegram_id: int, chat_id: int):
    """Включение пользователя в игру."""
    user = await session.execute(
        select(User).where(User.telegram_id == telegram_id, User.chat_id == chat_id)
    )
    user = user.scalar_one_or_none()
    if user and not user.in_game:
        user.in_game = True
        await session.commit()
        return True
    return False


@with_session
async def set_user_out_of_game(session: AsyncSession, telegram_id: int, chat_id: int):
    """Установка статуса in_game=False для пользователя, покинувшего чат."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id, User.chat_id == chat_id)
    )
    user = result.scalars().first()
    if user and user.in_game:
        user.in_game = False
        await session.commit()
        return True
    return False


@with_session
async def get_random_user(session: AsyncSession, chat_id: int):
    """Получение случайного пользователя из чата."""
    result = await session.execute(
        select(User).where(User.chat_id == chat_id, User.in_game == True)
    )
    users = result.scalars().all()
    return random.choice(users) if users else None


@with_session
async def add_or_update_user_bun(
    session: AsyncSession, user_id: int, bun: str, chat_id: int
):
    """Добавление или обновление записи о булочке для пользователя с учетом очков."""
    # Получаем баллы за булочку из таблицы buns
    result = await session.execute(select(Bun).where(Bun.name == bun))
    bun_record = result.scalar_one_or_none()

    if not bun_record:
        logger.error(f"Булочка '{bun}' не найдена в таблице buns")
        return  # Или можно выбросить исключение, если это критично

    points_per_bun = bun_record.points  # Баллы за одну булочку из базы

    try:
        # Проверяем, есть ли уже запись для этой булочки у пользователя
        result = await session.execute(
            select(UserBun).where(
                UserBun.user_id == user_id,
                UserBun.bun == bun,
                UserBun.chat_id == chat_id,
            )
        )
        user_bun = result.scalar_one_or_none()

        if user_bun:
            # Если запись существует, увеличиваем счётчик и пересчитываем очки
            user_bun.count += 1
            user_bun.points = user_bun.count * points_per_bun
            logger.debug(
                f"Обновлена запись для user_id={user_id}, bun={bun}, count={user_bun.count}, points={user_bun.points}"
            )
        else:
            # Если записи нет, создаём новую
            user_bun = UserBun(
                user_id=user_id,
                bun=bun,
                chat_id=chat_id,
                count=1,
                points=points_per_bun,
            )
            session.add(user_bun)
            logger.info(
                f"Добавлена новая булочка '{bun}' для user_id={user_id} в чате {chat_id}"
            )

        await session.commit()
        return user_bun  # Можно вернуть объект для дальнейшего использования
    except IntegrityError as e:
        await session.rollback()
        logger.error(
            f"Ошибка целостности при добавлении булочки '{bun}' для user_id={user_id}: {e}"
        )
        raise
    except Exception as e:
        await session.rollback()
        logger.error(
            f"Неизвестная ошибка при обновлении булочки '{bun}' для user_id={user_id}: {e}"
        )
        raise


@with_session
async def get_user_buns_stats(session: AsyncSession, telegram_id: int, chat_id: int):
    """Получение статистики булочек пользователя: булочка - количество - очки."""
    query = (
        select(UserBun.bun, UserBun.count, UserBun.points)
        .join(User, User.id == UserBun.user_id)
        .where(User.telegram_id == telegram_id, UserBun.chat_id == chat_id)
    )
    result = await session.execute(query)
    user_buns = result.fetchall()
    return (
        [
            {"bun": bun, "count": count, "points": points}
            for bun, count, points in user_buns
        ]
        if user_buns
        else []
    )


@with_session
async def get_top_users_by_points(session: AsyncSession, chat_id: int):
    """Получение топ-10 пользователей по очкам с их лучшей булочкой."""
    # Подзапрос для получения максимальных очков по булочке для каждого пользователя
    subquery = (
        select(
            UserBun.user_id,
            func.max(UserBun.points).label("max_points"),
            UserBun.bun.label("top_bun"),
            UserBun.count.label("top_count"),
        )
        .where(UserBun.chat_id == chat_id)
        .group_by(UserBun.user_id)
        .subquery()
    )

    # Основной запрос: соединяем с пользователями и сортируем по очкам
    query = (
        select(
            User.username,
            User.full_name,
            subquery.c.max_points,
            subquery.c.top_bun,
            subquery.c.top_count,
        )
        .join(subquery, User.id == subquery.c.user_id)
        .where(User.chat_id == chat_id, User.in_game == True)
        .order_by(subquery.c.max_points.desc())
        .limit(10)
    )

    result = await session.execute(query)
    top_users = result.fetchall()
    return (
        [
            {
                "username": username,
                "full_name": full_name,
                "points": max_points,
                "bun": top_bun,
                "count": top_count,
            }
            for username, full_name, max_points, top_bun, top_count in top_users
        ]
        if top_users
        else []
    )


@with_session
async def get_all_users(session: AsyncSession):
    """Получение списка всех пользователей."""
    result = await session.execute(
        select(
            User.telegram_id, User.username, User.full_name, User.chat_id, User.in_game
        )
    )
    users = result.fetchall()
    return [
        {
            "telegram_id": telegram_id,
            "username": username,
            "full_name": full_name,
            "chat_id": chat_id,
            "in_game": in_game,
        }
        for telegram_id, username, full_name, chat_id, in_game in users
    ]


@with_session
async def remove_user_from_game(session: AsyncSession, telegram_id: int, chat_id: int):
    """Удаление пользователя из розыгрыша (установка in_game=False)."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id, User.chat_id == chat_id)
    )
    user = result.scalars().first()
    if user and user.in_game:
        user.in_game = False
        await session.commit()
        return True
    return False


@with_session
async def get_active_chat_ids(session: AsyncSession):
    """Получение списка уникальных chat_id, где есть активные пользователи."""
    result = await session.execute(
        select(User.chat_id).where(User.in_game == True).distinct()
    )
    return [row[0] for row in result.fetchall()]


@with_session
async def get_all_buns(session: AsyncSession):
    """Получение всех булочек из таблицы buns."""
    result = await session.execute(select(Bun))
    buns = result.scalars().all()
    return {
        bun.name: bun.points for bun in buns
    }  # Возвращаем словарь вида {name: points}


@with_session
async def add_bun(session: AsyncSession, name: str, points: int):
    """Добавление новой булочки в таблицу buns."""
    try:
        bun = Bun(name=name, points=points)
        session.add(bun)
        await session.commit()
        logger.info(f"Добавлена булочка: {name} ({points} баллов)")
        return bun  # Возвращаем объект Bun для подтверждения
    except IntegrityError:
        await session.rollback()
        logger.warning(f"Булочка '{name}' уже существует")
        return None  # Возвращаем None, если булочка уже есть


@with_session
async def edit_bun(session: AsyncSession, name: str, points: int):
    """Редактирование баллов существующей булочки."""
    bun = await session.execute(select(Bun).where(Bun.name == name))
    bun = bun.scalar_one_or_none()
    if bun:
        bun.points = points
        await session.commit()
        logger.info(f"Обновлена булочка: {name} ({points} баллов)")
        return bun
    logger.warning(f"Булочка '{name}' не найдена для редактирования")
    return None


@with_session
async def remove_bun(session: AsyncSession, name: str):
    """Удаление булочки из таблицы buns."""
    bun = await session.execute(select(Bun).where(Bun.name == name))
    bun = bun.scalar_one_or_none()
    if bun:
        await session.delete(bun)
        await session.commit()
        logger.info(f"Удалена булочка: {name}")
        return True
    logger.warning(f"Булочка '{name}' не найдена для удаления")
    return False


@with_session
async def get_user_points(session: AsyncSession, telegram_id: int, chat_id: int) -> int:
    """Получает сумму баллов пользователя из user_buns."""
    query = (
        select(func.sum(UserBun.points).label("total_points"))
        .join(User, User.id == UserBun.user_id)
        .where(User.telegram_id == telegram_id, UserBun.chat_id == chat_id)
    )
    result = await session.execute(query)
    total_points = result.scalar() or 0
    return total_points


@with_session
async def update_user_points(
    session: AsyncSession, telegram_id: int, chat_id: int, new_points: int
):
    """Обновляет баллы пользователя в user_buns, распределяя новые очки по булочкам с 0 или равномерно."""
    # Получаем пользователя
    user = await get_user_by_id(telegram_id, chat_id)
    if not user:
        logger.warning(
            f"Пользователь telegram_id={telegram_id} не найден в чате {chat_id}"
        )
        return

    # Получаем все записи user_buns для пользователя
    result = await session.execute(
        select(UserBun).where(UserBun.user_id == user.id, UserBun.chat_id == chat_id)
    )
    user_buns = result.scalars().all()

    if not user_buns:
        logger.warning(
            f"Нет записей user_buns для telegram_id={telegram_id}, chat_id={chat_id}"
        )
        return

    # Если новые очки отрицательные, приводим итог к 0
    total_points = sum(bun.points for bun in user_buns)
    new_total = max(0, total_points + new_points)

    if new_total == 0:
        for bun in user_buns:
            bun.points = 0
    else:
        # Считаем булочки с 0 очков
        zero_buns = [bun for bun in user_buns if bun.points == 0]
        non_zero_buns = [bun for bun in user_buns if bun.points > 0]

        if zero_buns and new_points > 0:
            # Распределяем новые очки только по булочкам с 0
            points_per_zero = new_points // len(zero_buns)
            extra_points = new_points % len(zero_buns)
            for i, bun in enumerate(zero_buns):
                bun.points = points_per_zero + (1 if i < extra_points else 0)
        elif new_points > 0:
            # Если нет булочек с 0, распределяем по всем равномерно
            points_per_bun = new_points // len(user_buns)
            extra_points = new_points % len(user_buns)
            for i, bun in enumerate(user_buns):
                bun.points += points_per_bun + (1 if i < extra_points else 0)
        elif new_points < 0:
            # При уменьшении очков распределяем убыток пропорционально
            remaining_loss = abs(new_points)
            for bun in sorted(user_buns, key=lambda x: x.points, reverse=True):
                if remaining_loss <= 0:
                    break
                loss = min(bun.points, remaining_loss)
                bun.points -= loss
                remaining_loss -= loss

    await session.commit()
    logger.debug(
        f"Обновлены баллы для telegram_id={telegram_id}, chat_id={chat_id}: {new_points} добавлено, итого {new_total}"
    )


@with_session
async def get_user_by_username(session: AsyncSession, chat_id: int, username: str):
    """Получение пользователя по username и chat_id."""
    result = await session.execute(
        select(User).where(User.username == username, User.chat_id == chat_id)
    )
    return result.scalars().first()


@with_session
async def get_game_setting(session: AsyncSession, key: str) -> int:
    result = await session.execute(select(GameSetting).where(GameSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        return setting.value
    logger.warning(f"Настройка с ключом '{key}' не найдена")
    return 0


@with_session
async def get_all_game_settings(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(select(GameSetting))
    settings = result.scalars().all()
    return {setting.key: setting.value for setting in settings}


@with_session
async def update_game_setting(session: AsyncSession, key: str, value: int) -> bool:
    result = await session.execute(select(GameSetting).where(GameSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
        await session.commit()
        logger.info(f"Настройка '{key}' обновлена: {value}")
        return True
    logger.warning(f"Настройка с ключом '{key}' не найдена для обновления")
    return False


@with_session
async def get_user_id_by_telegram_id(
    session: AsyncSession, telegram_id: int, chat_id: int
):
    """Получение user_id по telegram_id и chat_id."""
    result = await session.execute(
        select(User.id).where(User.telegram_id == telegram_id, User.chat_id == chat_id)
    )
    user_id = result.scalar()
    return user_id


@with_session
async def delete_user_buns(session: AsyncSession, telegram_id: int, chat_id: int):
    """Удаление всех булок пользователя."""
    user_id = await get_user_id_by_telegram_id(telegram_id, chat_id)
    if user_id:
        await session.execute(
            delete(UserBun).where(
                UserBun.user_id == user_id, UserBun.chat_id == chat_id
            )
        )
        await session.commit()


@with_session
async def reset_user_on_zero_points(
    session: AsyncSession, telegram_id: int, chat_id: int
):
    """Полное удаление булок пользователя при достижении 0 баллов."""
    await delete_user_buns(telegram_id, chat_id)  # Теперь передаем session
