# Telegram → Notion Bot

Async Telegram bot (aiogram 3) that saves text and links into a Notion database. Users connect their own Notion Integration Token + Database ID; media handlers are stubs with a 20 MB size gate.

## Stack

- Python 3.11+
- [aiogram](https://docs.aiogram.dev/) 3.x
- [notion-client](https://github.com/ramnes/notion-sdk-py) + httpx
- pydantic-settings
- SQLAlchemy 2 (async) — SQLite by default, PostgreSQL via `DATABASE_URL`
- Docker (Alpine, multi-stage, low-RAM)

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
# edit BOT_TOKEN (and optional limits / DATABASE_URL)
```

| Variable | Default | Meaning |
|---|---|---|
| `BOT_TOKEN` | — | Telegram bot token (required) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./bot.db` | Async SQLAlchemy URL |
| `DAILY_REQUEST_LIMIT` | `100` | Per-user daily quota |
| `MONTHLY_REQUEST_LIMIT` | `2000` | Per-user monthly quota |
| `THROTTLE_RATE_SECONDS` | `2.0` | Min interval between messages |
| `MAX_FILE_SIZE_BYTES` | `20971520` | 20 MB media gate |
| `DEFAULT_LOCALE` | `en` | Fallback if `language_code` is unknown |

PostgreSQL example:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/telegram_notion
```

(Install `asyncpg` additionally when using Postgres.)

## 4. Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m bot.main
```

Locale is chosen automatically from Telegram `language_code` (`ru` / `en`).

## 5. Run with Docker

From the **repo root** (so `bot/` is the build context sibling of requirements):

```bash
docker build -f bot/Dockerfile -t telegram-notion-bot .
docker run --rm \
  --env-file .env \
  -v notion-bot-data:/data \
  telegram-notion-bot
```

The image runs as a non-root user, uses Alpine, and stores SQLite under `/data/bot.db` by default.

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
