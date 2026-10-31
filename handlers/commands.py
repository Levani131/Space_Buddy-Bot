"""Telegram bot command handlers for SpaceBuddy."""
import asyncio
import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.nasa import default_nasa_service

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - greets user and introduces bot capabilities."""
    first_name = update.effective_user.first_name if update.effective_user else "Explorer"
    welcome_message = (
        f"Hello, {first_name}! 🚀 Welcome to SpaceBuddy.\n\n"
        "I can fetch NASA's Astronomy Picture of the Day and track today's asteroids.\n"
        "Type /help to see all available commands."
    )
    if update.message:
        await update.message.reply_text(welcome_message)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - lists all available commands."""
    help_text = (
        "🌌 **SpaceBuddy Commands:**\n\n"
        "/start - Greet the bot\n"
        "/apod - Get NASA's photo of the day (or specify a date, e.g. `/apod 2026-10-25`)\n"
        "/asteroids - View today's biggest approaching asteroids\n"
        "/help - Show all available commands"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")


async def apod(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /apod command - fetches and sends APOD with image and description."""
    if not update.message:
        return

    # Check for optional target date argument (/apod YYYY-MM-DD)
    target_date = context.args[0] if context.args else None

    # Validate date format and range if provided
    if target_date:
        is_valid, error_msg = default_nasa_service.validate_date(target_date)
        if not is_valid:
            await update.message.reply_text(f"⚠️ {error_msg}")
            return

    # Show Telegram typing / uploading indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    status_msg = await update.message.reply_text("🔭 Fetching NASA's Picture of the Day...")

    # Fetch data in thread pool to prevent blocking the asyncio event loop
    data = await asyncio.to_thread(default_nasa_service.fetch_apod, target_date)

    if not data:
        await status_msg.edit_text("❌ Failed to fetch APOD from NASA. Please try again later.")
        return

    media_type = data.get("media_type")
    title = data.get("title", "Astronomy Picture of the Day")
    explanation = data.get("explanation", "No description available.")
    url = data.get("url")

    # Delete the temporary status message
    try:
        await status_msg.delete()
    except Exception:
        pass

    if media_type == "image" and url:
        # Telegram captions have a 1024-character limit
        caption = f"*{title}*\n\n{explanation}"
        if len(caption) > 1024:
            caption = caption[:1021] + "..."

        try:
            await update.message.reply_photo(photo=url, caption=caption, parse_mode="Markdown")
        except Exception:
            # Fall back to plain text caption if markdown parsing fails
            plain_caption = f"{title}\n\n{explanation}"
            if len(plain_caption) > 1024:
                plain_caption = plain_caption[:1021] + "..."
            await update.message.reply_photo(photo=url, caption=plain_caption)
    else:
        # Video or web embed link
        text = f"*{title}*\n\n{explanation}\n\nWatch here: {url}"
        try:
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(f"{title}\n\n{explanation}\n\nWatch here: {url}")


async def asteroids(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /asteroids command - fetches, ranks, and displays top 5 approaching asteroids."""
    if not update.message:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    status_msg = await update.message.reply_text("☄️ Scanning for today's near-Earth asteroids...")

    neos = await asyncio.to_thread(default_nasa_service.fetch_today_asteroids)

    if not neos:
        await status_msg.edit_text("📭 No asteroid data retrieved for today or none found.")
        return

    # Delete status message
    try:
        await status_msg.delete()
    except Exception:
        pass

    # Sort descending by estimated maximum diameter (biggest first)
    sorted_neos = sorted(neos, key=lambda x: x["diameter_m"], reverse=True)
    top_5 = sorted_neos[:5]

    response_lines = ["☄️ **Top 5 Biggest Asteroids Approaching Today:**\n"]
    for i, ast in enumerate(top_5, 1):
        hazard_emoji = "⚠️ (Hazardous)" if ast["is_hazardous"] else "✅ (Safe)"
        response_lines.append(
            f"*{i}. {ast['name']}* {hazard_emoji}\n"
            f"   • Diameter: ~{ast['diameter_m']:.1f} meters\n"
            f"   • Velocity: {ast['velocity_kmh']:,.0f} km/h\n"
            f"   • Miss Distance: {ast['miss_distance_km']:,.0f} km\n"
        )

    await update.message.reply_text("\n".join(response_lines), parse_mode="Markdown")

