# Настройка бота на Railway

## Шаг 1: Создание проекта

1. Зайдите на [railway.app](https://railway.app)
2. Создайте новый проект
3. Выберите "Deploy from GitHub repo"
4. Подключите репозиторий `family-todo-bot`

## Шаг 2: Добавление PostgreSQL

1. В проекте нажмите "+ New"
2. Выберите "Database" → "PostgreSQL"
3. Railway автоматически создаст переменную `DATABASE_URL`

## Шаг 3: Настройка переменных окружения

В разделе "Variables" вашего сервиса добавьте:

### Обязательные переменные:

1. **BOT_TOKEN**
   - Получите токен от [@BotFather](https://t.me/BotFather)
   - Команда: `/newbot`
   - Пример: `7918573197:AAHxxx...`

2. **DATABASE_URL**
   - Автоматически создаётся Railway при добавлении PostgreSQL
   - Формат: `postgresql://user:password@host:port/database`
   - Если не создалась автоматически, скопируйте из настроек PostgreSQL

3. **WEBHOOK_SECRET**
   - Любая случайная строка для безопасности
   - Пример: `my_super_secret_webhook_token_12345`
   - Можно сгенерировать: `openssl rand -hex 32`

4. **RAILWAY_STATIC_URL**
   - URL вашего приложения на Railway
   - Формат: `your-app-name.up.railway.app`
   - Найдите в разделе "Settings" → "Domains"
   - **ВАЖНО:** Указывайте БЕЗ `https://`

### Пример переменных:

```
BOT_TOKEN=7918573197:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxx
DATABASE_URL=postgresql://postgres:password@containers-us-west-123.railway.app:5432/railway
WEBHOOK_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
RAILWAY_STATIC_URL=family-todo-bot.up.railway.app
```

## Шаг 4: Настройка домена

1. Перейдите в "Settings" → "Networking"
2. Нажмите "Generate Domain"
3. Скопируйте сгенерированный домен (без `https://`)
4. Вставьте его в переменную `RAILWAY_STATIC_URL`

## Шаг 5: Деплой

1. Railway автоматически задеплоит приложение после коммита
2. Проверьте логи в разделе "Deployments"
3. Должны увидеть:
   ```
   ✅ Database initialized
   ✅ Webhook set
   ✅ Running on http://0.0.0.0:8080
   ```

## Шаг 6: Проверка работы

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Должно появиться главное меню

## Возможные проблемы

### Ошибка: "cannot import name 'log_activity'"
- **Решение:** Убедитесь, что используете последнюю версию кода из GitHub

### Ошибка: "column 'completed' does not exist"
- **Решение:** Перезапустите приложение - миграция выполнится автоматически

### Ошибка: "Webhook failed"
- **Проверьте:** Правильно ли указан `RAILWAY_STATIC_URL` (без `https://`)
- **Проверьте:** Совпадает ли `WEBHOOK_SECRET` в переменных

### База данных не подключается
- **Проверьте:** Правильность `DATABASE_URL`
- **Проверьте:** Что PostgreSQL сервис запущен
- **Попробуйте:** Пересоздать PostgreSQL плагин

## Полезные команды

### Просмотр логов
```bash
railway logs
```

### Перезапуск сервиса
В Railway UI: "Deployments" → "Restart"

### Подключение к базе данных
```bash
railway connect postgres
```

## Структура проекта на Railway

```
Railway Project
├── family-todo-bot (Service)
│   ├── Variables
│   │   ├── BOT_TOKEN
│   │   ├── WEBHOOK_SECRET
│   │   └── RAILWAY_STATIC_URL
│   └── Settings
│       └── Domain: family-todo-bot.up.railway.app
└── PostgreSQL (Database)
    └── Variables
        └── DATABASE_URL (автоматически)
```

## Обновление бота

1. Сделайте изменения в коде
2. Закоммитьте и запушьте на GitHub:
   ```bash
   git add .
   git commit -m "Update bot"
   git push origin main
   ```
3. Railway автоматически задеплоит новую версию

## Мониторинг

- **Логи:** Railway Dashboard → Deployments → View Logs
- **Метрики:** Railway Dashboard → Metrics
- **База данных:** Railway Dashboard → PostgreSQL → Metrics
