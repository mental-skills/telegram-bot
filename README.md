# Mental Skills Telegram Bot MVP

MVP Telegram-бота Mental Skills — образовательного тренажёра решений для родителей юных футболистов. Сейчас подключены две футбольные ситуации: `PREMATCH_GAME_REFUSAL_01` и `PREMATCH_INSTRUCTIONS_02`.

## Что реализовано

- `/start`, `/help`, `/privacy`, `/reset`.
- Главное меню и выбор возраста: 6–8, 9–12, 13–16 лет.
- Универсальный сценарный движок для JSON Schema 1.2.
- Каталог сценариев с порядком прохождения: ситуация №1 → ситуация №2.
- Загрузка текстов, кнопок, переходов, советов, готовых фраз и медиа из JSON.
- Проверка сценария до старта бота.
- Проверка asset manifest, runtime-ассетов и запрет отправки reference-изображений.
- Сохранение прогресса, истории выборов и версии сценария.
- Продолжение незавершённого прохождения.
- Повтор ситуации как новая попытка.
- Отдельный запуск ситуации №2 без смешивания с полным маршрутом.
- Text-only fallback при ошибке изображения.
- Защита от устаревших и повторных callback.

## Локальный запуск

1. Создайте бота через BotFather и получите токен.
2. Скопируйте `.env.example` в `.env`.
3. Укажите `TELEGRAM_BOT_TOKEN`.
4. Запустите:

```bash
docker compose up --build
```

Контейнер `bot` перед стартом применяет миграции Alembic.

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота.
- `DATABASE_URL` — DSN PostgreSQL для SQLAlchemy async.
- `LOG_LEVEL` — уровень логирования.
- `CONTENT_DIR` — папка JSON-сценариев.
- `ASSETS_DIR` — папка визуальных ассетов.
- `SCENARIO_ID` — совместимость с одиночной загрузкой сценария; основной порядок берётся из `content/scenario_catalog.json`.
- `PRIVACY_VERSION` — версия текста приватности.
- `RATE_LIMIT_MESSAGES_PER_MINUTE` — базовый лимит входящих событий.

## BotFather

1. Откройте Telegram и найдите `@BotFather`.
2. Выполните `/newbot`.
3. Задайте название и username бота.
4. Скопируйте токен в `.env`.
5. При необходимости задайте описание через `/setdescription` и команды через `/setcommands`.

Рекомендуемые команды:

```text
start - открыть Mental Skills
help - помощь
privacy - какие данные сохраняются
reset - удалить текущий прогресс
```

## Проверки

```bash
make test
make lint
make mypy
docker compose build
```

## Telegram Mini App

Mini App запускается вместе с ботом и использует тот же `ScenarioRegistry`,
`ScenarioEngine`, `ProgressService` и PostgreSQL. Сценарные тексты остаются в `content/`.

Основные настройки:

- `MINI_APP_URL` — публичный HTTPS URL frontend;
- `TELEGRAM_BOT_USERNAME` — username бота для возврата из вводного экрана ситуации №2;
- `WEBAPP_SESSION_SECRET` — отдельный секрет подписи web-сессии, минимум 32 символа;
- `TELEGRAM_AUTH_MAX_AGE_SECONDS` — максимальный возраст Telegram `initData`;
- `DEV_AUTH_ENABLED` — локальный вход без Telegram, всегда `false` в production.

Docker Compose запускает `db`, одноразовый `migrate`, затем `bot`, `api` и `frontend`.
Миграции не запускаются из `bot` или `api`.

```bash
docker compose up --build
```

Frontend доступен на `http://localhost:8080`, API — через тот же origin по `/api/v1/`.
Для реального запуска из Telegram задайте HTTPS URL и добавьте приложение в BotFather.

## Важные ограничения MVP

- Подключены только ситуации №1 и №2.
- Mini App в первой итерации полностью проводит ситуацию №1 и показывает только вводный экран ситуации №2; CRM, оплаты, генеративного ИИ и административной панели нет.
- Итог семи ситуаций не формируется, потому что ситуации №3–7 ещё не перенесены.
- Системные inline-кнопки Telegram не стилизуются, бренд передаётся через готовые runtime-карточки и структуру сообщений.
