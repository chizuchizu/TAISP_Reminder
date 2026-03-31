# TAISP Reminder

A Telegram bot that tracks assignment deadlines for NTU TAISP students. Deadlines are shared across the group, and the bot sends automatic daily and weekly reminders.

---

## Table of Contents

- [Features](#features)
- [Commands](#commands)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Database](#database)
- [Running Locally](#running-locally)
- [Deploying to Vercel](#deploying-to-vercel)
- [How the Bot Works](#how-the-bot-works)
- [Contributing](#contributing)

---

## Features

- Add, edit, and delete deadlines shared across the group
- Organise deadlines by module (e.g. SC1015, SC1003)
- Personal `/list` command — sent as a private DM
- `/help` silently DMs you the command list
- Automatic reminders at **8:00 AM SGT**:
  - **Daily** — deadlines due today or tomorrow
  - **Weekly (Mondays)** — all deadlines in the next 7 days
- Random NTU/TAISP jokes via `/joke`

---

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | Receive the command list via DM |
| `/list` | Get your personal deadline list via DM |
| `/adddeadline` | Add a new deadline (guided conversation) |
| `/editdeadline` | Edit an existing deadline |
| `/deletedeadline` | Delete a deadline |
| `/addmodule` | Register a new module |
| `/listmodules` | List all registered modules |
| `/deletemodule` | Remove a module and all its deadlines |
| `/joke` | Get a random NTU/TAISP joke |
| `/cancel` | Cancel any in-progress command |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | [python-telegram-bot](https://python-telegram-bot.org/) v20+ |
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) |
| ASGI server | [Uvicorn](https://www.uvicorn.org/) |
| Database | PostgreSQL via [asyncpg](https://magicstack.github.io/asyncpg/) |
| Scheduler | [APScheduler](https://apscheduler.readthedocs.io/) |
| Deployment | [Vercel](https://vercel.com/) (serverless) |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Python version | 3.11 |

---

## Project Structure

```
TAISP_Nerd_Bot/
├── api/
│   └── index.py          # FastAPI app — webhook endpoint + Vercel cron handlers
├── handlers/
│   ├── misc.py           # /start, /help, /joke, error handler
│   ├── list_cmd.py       # /list command
│   ├── modules.py        # /addmodule, /listmodules, /deletemodule
│   └── deadlines.py      # /adddeadline, /editdeadline, /deletedeadline
├── bot.py                # Entry point for local polling mode
├── config.py             # Loads environment variables
├── database.py           # All database queries (asyncpg)
├── models.py             # Module and Deadline dataclasses
├── scheduler.py          # Daily and weekly notification jobs
├── jokes.py              # Joke list
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project metadata
├── vercel.json           # Vercel deployment config (rewrites + cron)
└── .env.example          # Template for environment variables
```

---

## Prerequisites

- **Python 3.11** — check with `python --version`
- **uv** — install with `pip install uv` or see [uv docs](https://github.com/astral-sh/uv)
- **PostgreSQL** — a running instance locally, or a free cloud database (see below)
- **A Telegram bot token** — create one via [@BotFather](https://t.me/BotFather) on Telegram
- **A Telegram group** with the bot added as a member

---

## Local Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd TAISP_Nerd_Bot
```

### 2. Create a virtual environment and install dependencies

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Then open `.env` and fill in your values (see [Environment Variables](#environment-variables) below).

### 4. Set up the database

You need a PostgreSQL database. Options:

**Option A — Local PostgreSQL:**
```bash
createdb taisp_reminder
# Set DATABASE_URL=postgresql://localhost/taisp_reminder in .env
```

**Option B — Free cloud database (recommended for beginners):**
- [Neon](https://neon.tech) — free tier, easy setup, works perfectly with Vercel
- [Supabase](https://supabase.com) — free tier with a PostgreSQL connection string

Copy the connection string from your provider into `.env` as `DATABASE_URL`.

The tables are created automatically when the bot starts — no migrations needed.

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather | `1234567890:AABC...` |
| `GROUP_CHAT_ID` | Telegram group chat ID (negative number) | `-1001234567890` |
| `ADMIN_USER_ID` | Your personal Telegram user ID | `987654321` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |

**How to get your GROUP_CHAT_ID:**
1. Add [@userinfobot](https://t.me/userinfobot) to your group temporarily
2. It will display the group's chat ID
3. Remove it afterwards

**How to get your ADMIN_USER_ID:**
1. Message [@userinfobot](https://t.me/userinfobot) directly
2. It will show your user ID

---

## Database

The bot uses two tables:

**`modules`** — stores registered modules
```
id          serial primary key
name        text unique          -- e.g. "SC1015"
description text                 -- optional
created_at  timestamptz
```

**`deadlines`** — stores assignments
```
id          serial primary key
module_id   integer → modules(id) ON DELETE CASCADE
title       text                 -- assignment name
due_date    date                 -- YYYY-MM-DD
due_time    text                 -- HH:MM (optional)
notes       text                 -- optional
created_by  bigint               -- Telegram user ID
created_at  timestamptz
```

Deleting a module also deletes all its deadlines (cascade).

---

## Running Locally

```bash
python bot.py
```

The bot runs in **polling mode** — it continuously checks Telegram for new messages. The scheduler also runs in the background and will fire daily/weekly notifications at 8:00 AM SGT.

To stop it, press `Ctrl+C`.

---

## Deploying to Vercel

The bot runs as a **serverless webhook** on Vercel. Telegram sends updates to a POST endpoint instead of the bot polling.

### 1. Install the Vercel CLI

```bash
npm install -g vercel
```

### 2. Deploy

```bash
vercel
```

### 3. Set environment variables

In the [Vercel dashboard](https://vercel.com/), go to your project → **Settings → Environment Variables** and add:

- `BOT_TOKEN`
- `GROUP_CHAT_ID`
- `ADMIN_USER_ID`
- `DATABASE_URL`

### 4. Register the webhook with Telegram

Open this URL in your browser (replace with your actual values):

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<your-vercel-domain>/webhook
```

You should see `{"ok":true}`. The bot is now live.

### How Vercel cron jobs work

`vercel.json` schedules two cron endpoints:

```json
{ "path": "/api/cron/daily",  "schedule": "0 0 * * *"  }   // daily at 00:00 UTC = 08:00 SGT
{ "path": "/api/cron/weekly", "schedule": "0 0 * * 1"  }   // Mondays at 00:00 UTC
```

These replace the APScheduler that runs locally in `bot.py`.

---

## How the Bot Works

### Two modes

| Mode | File | Used for |
|---|---|---|
| Polling | `bot.py` | Local development |
| Webhook | `api/index.py` | Vercel production |

### Conversation flows

Multi-step commands (e.g. `/adddeadline`) use python-telegram-bot's `ConversationHandler`. The bot guides the user through steps, storing temporary data in `context.user_data`. This state lives in memory — a Vercel cold start resets any in-progress conversations.

### Notifications

`scheduler.py` contains `daily_notification_job` and `weekly_notification_job`. Both query upcoming deadlines and send a formatted message to `GROUP_CHAT_ID`. On Vercel, these are triggered by the cron endpoints in `api/index.py`.

---

## Contributing

1. **Fork** the repository and clone your fork
2. **Create a branch** for your change: `git checkout -b your-feature-name`
3. Make your changes — keep them focused and small
4. **Test locally** with `python bot.py` before submitting
5. **Open a pull request** with a short description of what you changed and why

### Adding a new command

1. Write the handler function in the appropriate file under `handlers/`
2. Register it in `api/index.py` inside `_get_ptb_app()` (and in `bot.py` for local mode)
3. Add it to the `HELP_TEXT` in `handlers/misc.py`

### Adding jokes

Open `jokes.py` and append to the list. Keep them NTU/TAISP-relevant.

### Code style

- Use `async`/`await` throughout — all handlers and DB calls are async
- Keep handlers thin; put DB logic in `database.py`
- Don't commit `.env` or any credentials

