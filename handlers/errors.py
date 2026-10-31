"""Global error handling for Telegram bot."""
import logging
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log exception and notify user if appropriate."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)

    # If update has an active message context, notify the user
    message = getattr(update, "effective_message", None)
    if message:
        try:
            await message.reply_text(
                "⚠️ Oops! Something went wrong while processing your request. Please try again later."
            )
        except Exception as e:
            logger.error(f"Failed to send error notification message: {e}")
