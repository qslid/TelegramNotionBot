# Telegram → Notion Bot

Async Telegram bot (aiogram 3) that saves text and links into a Notion database. Users connect their own Notion Integration Token + Database ID; media handlers are stubs with a 20 MB size gate.

## Stack

- Python 3.11+
- [aiogram](https://docs.aiogram.dev/) 3.x
- [notion-client](https://github.com/ramnes/notion-sdk-py) + httpx
- pydantic-settings
- SQLAlchemy 2 (async) + **Alembic** migrations
- **PostgreSQL** (recommended) via `asyncpg`; SQLite remains a local fallback
- Docker Compose (Postgres Alpine) + Alpine bot image

## Project layout

```
bot/
  config/         # Pydantic Settings (.env)
  handlers/       # start, settings, content (text→Notion), media
  middlewares/    # throttling, i18n, file size, usage limits, Notion auth
  services/       # notion_service.py
  database/       # SQLAlchemy models + async engine
  locales/        # en.json / ru.json
  main.py
  Dockerfile
alembic/          # Async migrations (source of truth for schema)
alembic.ini
docker-compose.yml
requirements.txt
.env.example
```

## 1. Create a Telegram bot

1. Open [@BotFather](https://t.me/BotFather) → `/newbot`
2. Copy the bot token into `.env` as `BOT_TOKEN`

## 2. Create a Notion integration + database

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration**
2. Copy the **Internal Integration Secret** (token)
3. Create a Notion **database** (full-page) with at least a **Title** property (Name / Title / Название)
4. Open the database → **•••** → **Connections** → add your integration
5. Copy the database ID from the URL:
   `https://www.notion.so/workspace/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...`
   (the 32-hex segment; dashes optional)

In the bot chat: **Settings → Connect Notion** → paste token → paste database ID/URL.

> **OAuth (future):** the schema comments leave room for OAuth `access_token` / `refresh_token`. Today the bot stores the Integration Token per user.

## 3. Configure environment

```bash
cp .env.example .env
# edit BOT_TOKEN; DATABASE_URL defaults to local Postgres from compose
```

| Variable | Default / example | Meaning |
|---|---|---|
| `BOT_TOKEN` | — | Telegram bot token (required to run the bot) |
| `DATABASE_URL` | `postgresql+asyncpg://bot:bot@localhost:5432/telegram_notion` | Async SQLAlchemy URL (Postgres recommended) |
| `DAILY_REQUEST_LIMIT` | `100` | Per-user daily quota |
| `MONTHLY_REQUEST_LIMIT` | `2000` | Per-user monthly quota |
| `THROTTLE_RATE_SECONDS` | `2.0` | Min interval between messages |
| `MAX_FILE_SIZE_BYTES` | `20971520` | 20 MB media gate |
| `DEFAULT_LOCALE` | `en` | Fallback if `language_code` is unknown |

SQLite fallback (no Docker DB):

```env
DATABASE_URL=sqlite+aiosqlite:///./bot.db
```

## 4. Database (Postgres + Alembic)

Schema is owned by **Alembic**. `init_db` opens the engine only — it does **not** call `create_all`.

### Bring up Postgres

```bash
docker compose up -d db
```

Defaults: user `bot`, password `bot`, database `telegram_notion`, port `5432`.

### Apply migrations

From the host (with venv + deps installed):

```bash
alembic upgrade head
```

Or via Compose (builds the Alpine image, runs once):

```bash
docker compose run --rm migrate
```

### Connection string example

```env
DATABASE_URL=postgresql+asyncpg://bot:bot@localhost:5432/telegram_notion
```

Inside Compose (bot → db service):

```env
DATABASE_URL=postgresql+asyncpg://bot:bot@db:5432/telegram_notion
```

### Verify tables

```bash
docker compose exec db psql -U bot -d telegram_notion -c '\dt'
# expect: users, notion_credentials, usage_counters, alembic_version
```

## 5. Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set BOT_TOKEN; keep Postgres URL or switch to SQLite
alembic upgrade head
python -m bot.main
```

Locale is chosen automatically from Telegram `language_code` (`ru` / `en`).

## 6. Run with Docker Compose

```bash
cp .env.example .env   # set BOT_TOKEN
docker compose up -d db
docker compose run --rm migrate
docker compose --profile bot up -d
```

Or build/run the bot image alone (SQLite volume):

```bash
docker build -f bot/Dockerfile -t telegram-notion-bot .
# still run migrations against your DATABASE_URL first
docker run --rm --env-file .env -v notion-bot-data:/data telegram-notion-bot
```

## Features (scaffold)

| Area | Behavior |
|---|---|
| Notion auth | Token + Database ID wizard; validate via Notion API; store in DB |
| Content | Text / links → new Notion database page |
| Media | Photo / document / video stubs; reject ≥ 20 MB before download |
| Middleware | ≤ 1 msg / 2 s; daily & monthly counters; i18n; Notion credential injection |
| UX | Inline: Settings, Connect Notion, Limits; emoji status replies |

## License

MIT (or your choice) — scaffold provided as-is for further productization.
