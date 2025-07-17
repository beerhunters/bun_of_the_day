# 🥐 Булочка Дня — Telegram-бот для веселья и вкусных игр!

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-supported-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Булочка Дня** — это интерактивный Telegram-бот, который привносит радость и веселье в ваши чаты! Каждый день бот выбирает случайного участника в качестве "Булочки Дня", приветствует новичков забавными стикерами и позволяет играть с виртуальными булочками и сосисками. 🍩✨

## 🎯 Основные возможности

- **Ежедневная Булочка Дня** — бот случайным образом выбирает участника чата и награждает его виртуальной булочкой в 09:00.
- **Приветствие новичков** — новых участников встречают юмористические сообщения и стикеры.
- **Игра с булочками и сосисками** — зарабатывайте очки, бросая сосиски в других участников или получая булочки.
- **Статистика** — отслеживайте свои достижения или смотрите топ-10 игроков в чате.
- **Админские команды** — управляйте игрой, добавляйте или редактируйте булочки, начисляйте очки участникам.

## 📋 Команды бота

### Общие команды
- `/start` — Запускает бота и активирует его в чате.
- `/play` — Присоединяет вас к игре.
- `/stats` — Показывает топ-10 игроков по очкам в чате.
- `/stats_me` — Отображает вашу личную статистику по булочкам.

### Админские команды
- `/user_list` — Показывает список всех пользователей в чатах.
- `/remove_from_game <chat_id> <user_number>` — Удаляет пользователя из игры.
- `/list_buns` — Показывает список всех доступных булочек.
- `/add_bun <name> <points>` — Добавляет новую булочку с указанными очками.
- `/edit_bun <name> <points>` — Изменяет очки для существующей булочки.
- `/remove_bun <name>` — Удаляет булочку.
- `/add_points_all <chat_id> <points>` — Начисляет очки всем участникам чата (можно указать диапазон, например, `5-10`).
- `/add_points <chat_id> @username <points>` — Начисляет очки конкретному пользователю.
- `/help` — Показывает справку по командам.
- `/send_to_chat` — Отправляет сообщение в указанный чат.

## 🛠 Установка и запуск

### Требования
- **Docker** и **Docker Compose** для развертывания.
- Python 3.11 (если запускаете без Docker).
- Файл `.env` с конфигурацией (см. ниже).

### Конфигурация
Создайте файл `.env` в корне проекта со следующими переменными:
```plaintext
API_TOKEN=your-telegram-bot-token
ADMIN_ID=your-admin-telegram-id
FOR_LOGS=some-log-value
DB_ECHO=False
```

- `API_TOKEN` — токен вашего Telegram-бота (получите у [@BotFather](https://t.me/BotFather)).
- `ADMIN_ID` — Telegram ID администратора бота.
- `FOR_LOGS` — значение для логирования (например, ч ascendancy::The file PRS::The PRS::PRETTY_BULLETIN is a Telegram bot, so it cannot be used without Docker.

### Шаги установки
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/beerhunters/bun_of_the_day.git
   cd crewassrun
   ```
2. Создайте файл `.env`:
   ```plaintext
   API_TOKEN=your-telegram-bot-token
   ADMIN_ID=your-admin-telegram-id
   FOR_LOGS=some-log-value
   DB_ECHO=False
   ```
3. Соберите и запустите контейнер:
   ```bash
   docker-compose up --build
   ```

### Остановка
```bash
docker-compose down
```

## 🐳 Развертывание

### Локальный запуск
1. Убедитесь, что файл `.env` настроен правильно (см. выше).
2. Запустите бота:
   ```bash
   python main.py
   ```

## 📡 Технологии

- **Python 3.11** — основной язык программирования.
- **SQLAlchemy** — для работы с базой данных SQLite.
- **aiogram** — библиотека для создания Telegram-ботов.
- **Docker** — для контейнеризации приложения.
- **python-dotenv** — для загрузки переменных окружения.
- **aiohttp** — для асинхронных HTTP-запросов.
- **aiosqlite** — асинхронный драйвер для SQLite.

## 🤝 Контрибьютинг

Мы приветствуем любые улучшения и дополнения! Открывайте Issues или отправляйте Pull Requests на [GitHub](https://github.com/beerhunters/crewassrun).

## 📜 Лицензия

Проект распространяется под лицензией MIT. Подробности см. в файл [LICENSE](LICENSE).

---

Made with ❤️ by [Beerhunters](https://t.me/beerhunters)
[GitHub Profile](https://github.com/beerhunters/) | 2025