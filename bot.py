import logging
from telegram.ext import Application, ApplicationBuilder, CommandHandler

import config
from database import init_db
from scheduler import setup_scheduler
from handlers.misc import start, help_cmd, error_handler
from handlers.debug import debug_digest
from handlers.list_cmd import list_deadlines
from handlers.modules import addmodule_conv, deletemodule_conv, listmodules
from handlers.deadlines import adddeadline_conv, editdeadline_conv, deletedeadline_conv

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    await init_db()
    setup_scheduler(application)
    logger.info("Bot initialised. NTU deadlines will be tracked mercilessly.")


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Conversation handlers must be registered before plain CommandHandlers
    # so their entry points take priority.
    application.add_handler(addmodule_conv)
    application.add_handler(deletemodule_conv)
    application.add_handler(adddeadline_conv)
    application.add_handler(editdeadline_conv)
    application.add_handler(deletedeadline_conv)

    # Simple command handlers
    application.add_handler(CommandHandler("list", list_deadlines))
    application.add_handler(CommandHandler("listmodules", listmodules))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("start", start))

    application.add_handler(CommandHandler("debugdigest", debug_digest))

    application.add_error_handler(error_handler)

    logger.info("Polling...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
