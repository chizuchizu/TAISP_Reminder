import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application
from datetime import datetime
from zoneinfo import ZoneInfo
from database import get_deadlines_due_within, get_upcoming_deadlines
import config

logger = logging.getLogger(__name__)


def _format_notification(deadlines, window_label: str) -> str:
    if not deadlines:
        return None  # caller decides whether to send or stay silent
    lines = [f"*Upcoming deadlines — {window_label}:*\n"]
    for d in deadlines:
        time_str = f" {d.due_time}" if d.due_time else ""
        notes_str = f"\n   _{d.notes}_" if d.notes else ""
        lines.append(f"  • *{d.module_name}* — {d.title} (due {d.due_date}{time_str}){notes_str}")
    return "\n".join(lines)


async def morning_digest_job(app: Application) -> None:
    """Every day 09:00 SGT — full digest of all upcoming deadlines."""
    today = datetime.now(tz=ZoneInfo(config.TIMEZONE)).strftime("%A, %d %B %Y")
    deadlines = await get_upcoming_deadlines()
    lines = [f"*Good morning! Today is {today}.*\n"]
    if deadlines:
        lines.append("*Upcoming deadlines:*\n")
        for d in deadlines:
            time_str = f" {d.due_time}" if d.due_time else ""
            notes_str = f"\n   _{d.notes}_" if d.notes else ""
            lines.append(f"  • *{d.module_name}* — {d.title} (due {d.due_date}{time_str}){notes_str}")
    else:
        lines.append("No upcoming deadlines. Enjoy the peace!")
    text = "\n".join(lines)
    try:
        await app.bot.send_message(
            chat_id=config.GROUP_CHAT_ID,
            text=text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Morning digest failed: %s", e)


async def weekly_notification_job(app: Application) -> None:
    """Every Monday 08:00 SGT — deadlines due in the next 7 days."""
    deadlines = await get_deadlines_due_within(7)
    text = _format_notification(deadlines, "this week")
    if text is None:
        text = "No deadlines this week! Enjoy the peace."
    try:
        await app.bot.send_message(
            chat_id=config.GROUP_CHAT_ID,
            text=text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Weekly notification failed: %s", e)


async def daily_notification_job(app: Application) -> None:
    """Every day 08:00 SGT — deadlines due today or tomorrow only."""
    deadlines = await get_deadlines_due_within(1)
    if not deadlines:
        return  # Stay silent when nothing is imminent
    text = _format_notification(deadlines, "today & tomorrow")
    try:
        await app.bot.send_message(
            chat_id=config.GROUP_CHAT_ID,
            text=text,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("Daily notification failed: %s", e)


def setup_scheduler(app: Application) -> None:
    scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)

    scheduler.add_job(
        morning_digest_job,
        CronTrigger(hour=9, minute=0, timezone=config.TIMEZONE),
        args=[app],
        misfire_grace_time=60,
        id="morning_digest",
    )
    scheduler.add_job(
        weekly_notification_job,
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone=config.TIMEZONE),
        args=[app],
        misfire_grace_time=60,
        id="weekly",
    )
    scheduler.add_job(
        daily_notification_job,
        CronTrigger(hour=8, minute=0, timezone=config.TIMEZONE),
        args=[app],
        misfire_grace_time=60,
        id="daily",
    )

    scheduler.start()
    logger.info("Scheduler started (SGT morning digest 09:00, weekly Mon 08:00, daily 08:00).")
