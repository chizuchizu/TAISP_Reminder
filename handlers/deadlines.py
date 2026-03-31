from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from database import (
    add_deadline,
    get_all_deadlines,
    get_deadline_by_id,
    get_module_by_name,
    get_all_modules,
    update_deadline,
    delete_deadline,
)

# States for add flow
(
    ADD_MODULE,
    ADD_TITLE,
    ADD_DATE,
    ADD_TIME,
    ADD_NOTES,
    ADD_CONFIRM,
) = range(6)

# States for edit/delete flows
SELECT_EDIT, EDIT_FIELD, EDIT_VALUE = range(6, 9)
SELECT_DELETE, DELETE_CONFIRM = range(9, 11)


def _parse_date(text: str):
    """Accept DD/MM/YYYY or YYYY-MM-DD."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(text: str):
    for fmt in ("%H:%M", "%H%M"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def _deadline_summary(data: dict) -> str:
    time_str = f" at {data['time']}" if data.get("time") else ""
    notes_str = f"\nNotes: {data['notes']}" if data.get("notes") else ""
    return (
        f"*Module:* {data['module_name']}\n"
        f"*Title:* {data['title']}\n"
        f"*Due:* {data['date']}{time_str}{notes_str}"
    )


# ── Add deadline ──────────────────────────────────────────────────────────────

async def adddeadline_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    modules = await get_all_modules()
    if not modules:
        await update.message.reply_text("No modules yet! Add one with /addmodule first.")
        return ConversationHandler.END
    context.user_data["new_dl"] = {}
    names = ", ".join(m.name for m in modules)
    await update.message.reply_text(f"Which module? ({names})")
    return ADD_MODULE


async def adddeadline_module(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip().upper()
    module = await get_module_by_name(name)
    if module is None:
        await update.message.reply_text(
            f"Module '{name}' not found. Try /addmodule first, or check the spelling."
        )
        return ADD_MODULE
    context.user_data["new_dl"]["module_id"] = module.id
    context.user_data["new_dl"]["module_name"] = module.name
    await update.message.reply_text("Assignment title?")
    return ADD_TITLE


async def adddeadline_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_dl"]["title"] = update.message.text.strip()
    await update.message.reply_text("Due date? (DD/MM/YYYY)")
    return ADD_DATE


async def adddeadline_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = _parse_date(update.message.text)
    if d is None:
        await update.message.reply_text("Invalid date. Use DD/MM/YYYY (e.g. 15/04/2025).")
        return ADD_DATE
    context.user_data["new_dl"]["date"] = d.isoformat()
    await update.message.reply_text("Due time? (HH:MM, or /skip)")
    return ADD_TIME


async def adddeadline_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = _parse_time(update.message.text)
    if t is None:
        await update.message.reply_text("Invalid time. Use HH:MM (e.g. 23:59), or /skip.")
        return ADD_TIME
    context.user_data["new_dl"]["time"] = t
    await update.message.reply_text("Any notes? (or /skip)")
    return ADD_NOTES


async def adddeadline_skip_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_dl"]["time"] = None
    await update.message.reply_text("Any notes? (or /skip)")
    return ADD_NOTES


async def adddeadline_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_dl"]["notes"] = update.message.text.strip()
    return await _show_confirm(update, context)


async def adddeadline_skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["new_dl"]["notes"] = None
    return await _show_confirm(update, context)


async def _show_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    data = context.user_data["new_dl"]
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Confirm", callback_data="dl_confirm"),
            InlineKeyboardButton("Cancel", callback_data="dl_cancel"),
        ]
    ])
    await update.message.reply_text(
        _deadline_summary(data),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return ADD_CONFIRM


async def adddeadline_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "dl_cancel":
        context.user_data.pop("new_dl", None)
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    data = context.user_data.pop("new_dl")
    await add_deadline(
        module_id=data["module_id"],
        title=data["title"],
        due_date=data["date"],
        due_time=data.get("time"),
        notes=data.get("notes"),
        created_by=query.from_user.id,
    )
    await query.edit_message_text("Deadline added! Good luck (you'll need it).")
    return ConversationHandler.END


# ── Delete deadline ───────────────────────────────────────────────────────────

async def deletedeadline_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    deadlines = await get_all_deadlines()
    if not deadlines:
        await update.message.reply_text("No deadlines to delete. Lucky you.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(
            f"{d.module_name}: {d.title} ({d.due_date})",
            callback_data=f"deldl_{d.id}",
        )]
        for d in deadlines
    ]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="deldl_cancel")])
    await update.message.reply_text(
        "Which deadline to delete?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_DELETE


async def deletedeadline_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "deldl_cancel":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    deadline_id = int(query.data.split("_")[1])
    dl = await get_deadline_by_id(deadline_id)
    if dl is None:
        await query.edit_message_text("Deadline not found.")
        return ConversationHandler.END

    context.user_data["del_dl_id"] = deadline_id
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Yes, delete", callback_data="deldl_yes"),
            InlineKeyboardButton("No", callback_data="deldl_no"),
        ]
    ])
    await query.edit_message_text(
        f"Delete *{dl.module_name}: {dl.title}* (due {dl.due_date})?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return DELETE_CONFIRM


async def deletedeadline_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "deldl_no":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    deadline_id = context.user_data.pop("del_dl_id")
    ok = await delete_deadline(deadline_id)
    if ok:
        await query.edit_message_text("Deadline deleted.")
    else:
        await query.edit_message_text("Deadline not found (already deleted?).")
    return ConversationHandler.END


# ── Edit deadline ─────────────────────────────────────────────────────────────

EDIT_FIELDS = ["title", "due_date", "due_time", "notes"]


async def editdeadline_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    deadlines = await get_all_deadlines()
    if not deadlines:
        await update.message.reply_text("No deadlines to edit.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(
            f"{d.module_name}: {d.title} ({d.due_date})",
            callback_data=f"editdl_{d.id}",
        )]
        for d in deadlines
    ]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="editdl_cancel")])
    await update.message.reply_text(
        "Which deadline to edit?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_EDIT


async def editdeadline_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "editdl_cancel":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    deadline_id = int(query.data.split("_")[1])
    context.user_data["edit_dl_id"] = deadline_id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f.replace("_", " ").title(), callback_data=f"editfield_{f}")]
        for f in EDIT_FIELDS
    ] + [[InlineKeyboardButton("Cancel", callback_data="editfield_cancel")]])
    await query.edit_message_text("What do you want to edit?", reply_markup=keyboard)
    return EDIT_FIELD


async def editdeadline_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "editfield_cancel":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    field = query.data.split("_", 1)[1]
    context.user_data["edit_field"] = field
    prompts = {
        "title": "New title?",
        "due_date": "New due date? (DD/MM/YYYY)",
        "due_time": "New due time? (HH:MM, or type 'none' to clear)",
        "notes": "New notes? (or type 'none' to clear)",
    }
    await query.edit_message_text(prompts[field])
    return EDIT_VALUE


async def editdeadline_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.pop("edit_field")
    deadline_id = context.user_data.pop("edit_dl_id")
    text = update.message.text.strip()

    kwargs = {}
    if field == "title":
        kwargs["title"] = text
    elif field == "due_date":
        d = _parse_date(text)
        if d is None:
            await update.message.reply_text("Invalid date. Use DD/MM/YYYY.")
            context.user_data["edit_field"] = field
            context.user_data["edit_dl_id"] = deadline_id
            return EDIT_VALUE
        kwargs["due_date"] = d.isoformat()
    elif field == "due_time":
        if text.lower() == "none":
            kwargs["due_time"] = ""
        else:
            t = _parse_time(text)
            if t is None:
                await update.message.reply_text("Invalid time. Use HH:MM.")
                context.user_data["edit_field"] = field
                context.user_data["edit_dl_id"] = deadline_id
                return EDIT_VALUE
            kwargs["due_time"] = t
    elif field == "notes":
        kwargs["notes"] = "" if text.lower() == "none" else text

    ok = await update_deadline(deadline_id, **kwargs)
    if ok:
        await update.message.reply_text("Updated!")
    else:
        await update.message.reply_text("Update failed. Deadline not found?")
    return ConversationHandler.END


# ── Cancel fallback ───────────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── ConversationHandlers ──────────────────────────────────────────────────────

adddeadline_conv = ConversationHandler(
    entry_points=[CommandHandler("adddeadline", adddeadline_start)],
    states={
        ADD_MODULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adddeadline_module)],
        ADD_TITLE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, adddeadline_title)],
        ADD_DATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, adddeadline_date)],
        ADD_TIME: [
            CommandHandler("skip", adddeadline_skip_time),
            MessageHandler(filters.TEXT & ~filters.COMMAND, adddeadline_time),
        ],
        ADD_NOTES: [
            CommandHandler("skip", adddeadline_skip_notes),
            MessageHandler(filters.TEXT & ~filters.COMMAND, adddeadline_notes),
        ],
        ADD_CONFIRM: [CallbackQueryHandler(adddeadline_confirm, pattern=r"^dl_")],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

deletedeadline_conv = ConversationHandler(
    entry_points=[CommandHandler("deletedeadline", deletedeadline_start)],
    states={
        SELECT_DELETE:  [CallbackQueryHandler(deletedeadline_select, pattern=r"^deldl_")],
        DELETE_CONFIRM: [CallbackQueryHandler(deletedeadline_confirm, pattern=r"^deldl_")],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=True,
)

editdeadline_conv = ConversationHandler(
    entry_points=[CommandHandler("editdeadline", editdeadline_start)],
    states={
        SELECT_EDIT: [CallbackQueryHandler(editdeadline_select, pattern=r"^editdl_")],
        EDIT_FIELD:  [CallbackQueryHandler(editdeadline_field, pattern=r"^editfield_")],
        EDIT_VALUE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, editdeadline_value)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
