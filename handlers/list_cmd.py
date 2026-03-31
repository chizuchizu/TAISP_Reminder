from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from database import get_all_deadlines
from models import Deadline


def _format_deadlines(deadlines: list[Deadline]) -> str:
    if not deadlines:
        return "No deadlines! Either you're on top of things, or you've missed them all. Hopefully the former."

    today = date.today().isoformat()
    lines = ["*Your upcoming deadlines:*\n"]
    current_module = None

    for d in deadlines:
        if d.module_name != current_module:
            current_module = d.module_name
            lines.append(f"\n*{d.module_name}*")

        time_str = f" {d.due_time}" if d.due_time else ""
        urgency = " ← TODAY" if d.due_date == today else ""
        notes_str = f"\n   _{d.notes}_" if d.notes else ""
        lines.append(f"  • {d.title} — {d.due_date}{time_str}{urgency}{notes_str}")

    return "\n".join(lines)


async def list_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deadlines = await get_all_deadlines()
    text = _format_deadlines(deadlines)

    user_id = update.effective_user.id
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
        # Only acknowledge in the group if the command came from a group
        if update.effective_chat.id != user_id:
            await update.message.reply_text("Check your DMs!", quote=True)
    except Exception:
        # User hasn't started the bot in private — fall back to in-chat reply
        await update.message.reply_text(
            text + "\n\n_Start the bot privately (/start) so I can DM you next time._",
            parse_mode="Markdown",
        )
