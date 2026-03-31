import sys
import os

# Ensure project root is on the path so sibling modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

import config
from database import init_db
from handlers.misc import start, help_cmd, error_handler
from handlers.list_cmd import list_deadlines
from handlers.modules import addmodule_conv, deletemodule_conv, listmodules
from handlers.deadlines import adddeadline_conv, editdeadline_conv, deletedeadline_conv

app = FastAPI()

# Module-level PTB application — reused across warm Vercel invocations.
# NOTE: ConversationHandler state lives in memory; a cold start resets it.
_ptb_app = None
_initialized = False


async def _get_ptb_app():
    global _ptb_app, _initialized
    if _ptb_app is None:
        _ptb_app = ApplicationBuilder().token(config.BOT_TOKEN).build()

        # Conversation handlers first (entry points take priority over plain commands)
        _ptb_app.add_handler(addmodule_conv)
        _ptb_app.add_handler(deletemodule_conv)
        _ptb_app.add_handler(adddeadline_conv)
        _ptb_app.add_handler(editdeadline_conv)
        _ptb_app.add_handler(deletedeadline_conv)

        # Simple command handlers
        _ptb_app.add_handler(CommandHandler("list", list_deadlines))
        _ptb_app.add_handler(CommandHandler("listmodules", listmodules))
        _ptb_app.add_handler(CommandHandler("help", help_cmd))
        _ptb_app.add_handler(CommandHandler("start", start))

        _ptb_app.add_error_handler(error_handler)

    if not _initialized:
        await init_db()
        await _ptb_app.initialize()
        _initialized = True

    return _ptb_app


@app.post("/webhook")
async def webhook(request: Request):
    ptb = await _get_ptb_app()
    data = await request.json()
    update = Update.de_json(data, ptb.bot)
    await ptb.process_update(update)
    return {"ok": True}


@app.get("/")
def index():
    return {"message": "TAISP Reminder is running"}


# ── Vercel Cron endpoints ─────────────────────────────────────────────────────
# Scheduled in vercel.json; both run at 00:00 UTC = 08:00 SGT.

@app.get("/api/cron/daily")
async def cron_daily():
    from scheduler import daily_notification_job
    ptb = await _get_ptb_app()
    await daily_notification_job(ptb)
    return {"ok": True}


@app.get("/api/cron/weekly")
async def cron_weekly():
    from scheduler import weekly_notification_job
    ptb = await _get_ptb_app()
    await weekly_notification_job(ptb)
    return {"ok": True}
