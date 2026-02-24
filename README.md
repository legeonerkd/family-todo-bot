# Family TODO Bot

Телеграм-бот для управления семейными задачами и списками покупок.

## Возможности

- ➕ Добавление задач и покупок
- 📋 Просмотр списка задач
- 🛒 Просмотр списка покупок
- 👨‍👩‍👧‍👦 Управление семьей
- 📜 История действий (только для родителей)
- 👑 Разделение ролей (родители/дети)

## Установка

1. Клонируйте репозиторий
2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

4. Заполните переменные окружения в `.env`:
   - `BOT_TOKEN` - 7918573197:AAEurp4Sl5NVAyNU6FHiYOYY-7lfJp4bmJc
   - `DATABASE_URL` - postgresql://postgres:TamzdUQrFxFobWyNWRdJOmwbWcCDYbPb@postgres.railway.internal:5432/railway
   - `WEBHOOK_SECRET` - s8df98sdf98sdf98
   - `RAILWAY_STATIC_URL` - family-todo-bot-production.up.railway.app

## Запуск

### Локальное тестирование (polling)

Для локального тестирования используйте режим polling:

```bash
python bot_polling.py
```

### Продакшн (webhook)

Для продакшн-окружения с webhook:

```bash
python bot.py
```

## Структура проекта

```
family_todo_bot/
├── bot.py              # Главный файл запуска
├── config.py           # Конфигурация
├── db.py              # Работа с базой данных
├── handlers/          # Обработчики команд
│   ├── start.py       # Команда /start
│   ├── tasks.py       # Работа с задачами
│   ├── shopping.py    # Работа с покупками
│   ├── family.py      # Управление семьей
│   └── history.py     # История действий
├── keyboards/         # Клавиатуры
│   ├── main_meny.py   # Главное меню
│   ├── confirm.py     # Подтверждение действий
│   └── history.py     # Навигация по истории
└── states/            # FSM состояния
    └── user_states.py # Состояния пользователя
```

## База данных

Бот использует PostgreSQL. При первом запуске автоматически создаются следующие таблицы:
- `families` - семьи
- `family_members` - члены семей
- `tasks` - задачи
- `shopping` - покупки
- `activity_log` - история действий

## Деплой на Railway

Подробная инструкция по настройке на Railway: [RAILWAY_SETUP.md](RAILWAY_SETUP.md)

**Краткая инструкция:**

1. Создайте новый проект на Railway
2. Подключите PostgreSQL плагин
3. Добавьте переменные окружения:
   - `BOT_TOKEN` - токен от @BotFather
   - `DATABASE_URL` - автоматически из PostgreSQL
   - `WEBHOOK_SECRET` - случайная строка
   - `RAILWAY_STATIC_URL` - домен приложения (без https://)
4. Railway автоматически задеплоит приложение

## Лицензия

MIT
