"""Main entry point for SpaceBuddy Telegram bot."""
import logging
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from config import config
from handlers.commands import apod, apod_callback, asteroids, help_cmd, start
from handlers.errors import on_error

# Configure application logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger(__name__)


def create_app() -> Application:
    """Build and configure the Telegram bot Application."""
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("apod", apod))
    app.add_handler(CommandHandler("asteroids", asteroids))

    # Register interactive callback query handlers for date selection
    app.add_handler(CallbackQueryHandler(apod_callback, pattern="^apod_"))

    # Register error handler
    app.add_error_handler(on_error)

    return app


def main() -> None:
    """Initialize and start polling."""
    app = create_app()
    logger.info("SpaceBuddy bot started successfully. Polling for updates...")
    print("SpaceBuddy is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
