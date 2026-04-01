import logging
from telegram import Update
from telegram.ext import ContextTypes
from scheduler import morning_digest_job
import config

logger = logging.getLogger(__name__)


async def debug_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hidden admin command: manually trigger the morning digest."""
    if update.effective_user.id != config.ADMIN_USER_ID:
        return
    await update.message.reply_text("Triggering morning digest...", quote=True)
    await morning_digest_job(context.application)
