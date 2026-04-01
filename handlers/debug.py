import logging
from telegram import Update
from telegram.ext import ContextTypes
from scheduler import morning_digest_job

logger = logging.getLogger(__name__)


async def debug_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hidden command: manually trigger the morning digest."""
    await update.message.reply_text("Triggering morning digest...", quote=True)
    await morning_digest_job(context.application)
