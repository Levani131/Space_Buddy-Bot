"""Global error handling for Telegram bot."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log exception and notify user if appropriate."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Oops! Something went wrong while processing your request. Please try again later."
            )
        except Exception as e:
            logger.error(f"Failed to send error notification message: {e}")

