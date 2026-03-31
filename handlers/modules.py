from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from database import add_module, get_all_modules, delete_module

# States
ASK_NAME, ASK_DESC = range(2)
SELECT_DELETE = 2


# ── Add module ────────────────────────────────────────────────────────────────

async def addmodule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("What's the module code? (e.g. SC1015)")
    return ASK_NAME


async def addmodule_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["mod_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Short description? (or /skip)"
    )
    return ASK_DESC


async def addmodule_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    desc = update.message.text.strip()
    name = context.user_data.pop("mod_name")
    ok = await add_module(name, desc)
    if ok:
        await update.message.reply_text(f"Module *{name.upper()}* added!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"Module *{name.upper()}* already exists.", parse_mode="Markdown")
    return ConversationHandler.END


async def addmodule_skip_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = context.user_data.pop("mod_name")
    ok = await add_module(name, None)
    if ok:
        await update.message.reply_text(f"Module *{name.upper()}* added!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"Module *{name.upper()}* already exists.", parse_mode="Markdown")
    return ConversationHandler.END


# ── List modules ──────────────────────────────────────────────────────────────

async def listmodules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    modules = await get_all_modules()
    if not modules:
        await update.message.reply_text("No modules yet. Use /addmodule to add one.")
        return
    lines = ["*Modules:*"]
    for m in modules:
        desc = f" — {m.description}" if m.description else ""
        lines.append(f"  • *{m.name}*{desc}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Delete module ─────────────────────────────────────────────────────────────

async def deletemodule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    modules = await get_all_modules()
    if not modules:
        await update.message.reply_text("No modules to delete.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(m.name, callback_data=f"delmod_{m.id}")]
        for m in modules
    ]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="delmod_cancel")])
    await update.message.reply_text(
        "Which module do you want to delete? (This will also delete all its deadlines!)",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_DELETE


async def deletemodule_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "delmod_cancel":
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    module_id = int(query.data.split("_")[1])
    ok = await delete_module(module_id)
    if ok:
        await query.edit_message_text("Module and all its deadlines deleted.")
    else:
        await query.edit_message_text("Module not found.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── ConversationHandler ───────────────────────────────────────────────────────

addmodule_conv = ConversationHandler(
    entry_points=[CommandHandler("addmodule", addmodule_start)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addmodule_name)],
        ASK_DESC: [
            CommandHandler("skip", addmodule_skip_desc),
            MessageHandler(filters.TEXT & ~filters.COMMAND, addmodule_desc),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

deletemodule_conv = ConversationHandler(
    entry_points=[CommandHandler("deletemodule", deletemodule_start)],
    states={
        SELECT_DELETE: [CallbackQueryHandler(deletemodule_confirm, pattern=r"^delmod_")],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=True,
)
