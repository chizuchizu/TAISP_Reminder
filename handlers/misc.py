from telegram import Update
from telegram.ext import ContextTypes
from jokes import get_joke

HELP_TEXT = """
*TAISP Reminder* — your friendly deadline overlord

*Deadlines*
/adddeadline — add a new deadline
/editdeadline — edit an existing deadline
/deletedeadline — delete a deadline
/list — get your personal deadline list (DM only)

*Modules*
/addmodule — add a module
/listmodules — list all modules
/deletemodule — remove a module

*Fun*
/joke — get an NTU/TAISP joke
/help — show this message

_Deadlines are shared across the group. Suffering is too._
"""

START_TEXT = """
Welcome to *TAISP Reminder*!

I track assignment deadlines so your brain doesn't have to.

Use /help to see what I can do.

_Tip: I'll DM you your deadlines when you use /list — make sure you've messaged me privately at least once so Telegram lets me slide into your DMs._
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(START_TEXT, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=HELP_TEXT,
            parse_mode="Markdown",
        )
        if update.message.chat.type != "private":
            await update.message.reply_text("Sent you the help info in DM!", quote=True)
    except Exception:
        # Bot can't DM the user (they haven't started a private chat yet)
        await update.message.reply_text(
            "I couldn't DM you — please send me a private message first, then try /help again.",
            quote=True,
        )


async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(get_joke())


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    import logging
    logging.getLogger(__name__).error("Exception while handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Something broke. Tell Yuma. (Or just blame NTU WiFi.)"
        )
