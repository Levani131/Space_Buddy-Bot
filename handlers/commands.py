"""Telegram bot command and callback handlers for SpaceBuddy."""
import asyncio
import logging
import random
from datetime import date, timedelta
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from services.nasa import default_nasa_service

logger = logging.getLogger(__name__)


def get_apod_keyboard(current_date: Optional[str] = None) -> InlineKeyboardMarkup:
    """Generate interactive date-selection inline keyboard."""
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()

    # Pick a random date within the last year (between 2 and 365 days ago)
    random_days = random.randint(2, 365)
    random_past_date = (today - timedelta(days=random_days)).isoformat()

    buttons = [
        [
            InlineKeyboardButton("📅 Yesterday", callback_data=f"apod_date:{yesterday}"),
            InlineKeyboardButton("🎲 Random Date", callback_data=f"apod_date:{random_past_date}"),
        ],
        [
            InlineKeyboardButton("ℹ️ Custom Date Help", callback_data="apod_help"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


async def send_apod_content(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    target_date: Optional[str] = None,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """Fetch and deliver APOD content to the user with interactive controls."""
    display_date = target_date or date.today().isoformat()

    # Show Telegram uploading indicator
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔭 Fetching NASA's Picture of the Day for {display_date}...",
        reply_to_message_id=reply_to_message_id,
    )

    # Fetch data in thread pool
    data = await asyncio.to_thread(default_nasa_service.fetch_apod, target_date)

    if not data:
        await status_msg.edit_text(f"❌ Failed to fetch APOD for {display_date} from NASA. Please try again later.")
        return

    media_type = data.get("media_type")
    title = data.get("title", "Astronomy Picture of the Day")
    explanation = data.get("explanation", "No description available.")
    url = data.get("url")
    item_date = data.get("date", display_date)

    # Delete temporary status message
    try:
        await status_msg.delete()
    except Exception:
        pass

    keyboard = get_apod_keyboard(item_date)

    if media_type == "image" and url:
        caption = f"*{title}* ({item_date})\n\n{explanation}"
        if len(caption) > 1024:
            caption = caption[:1021] + "..."

        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=url,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
                reply_to_message_id=reply_to_message_id,
            )
        except Exception:
            # Fall back to plain text caption if markdown parsing fails
            plain_caption = f"{title} ({item_date})\n\n{explanation}"
            if len(plain_caption) > 1024:
                plain_caption = plain_caption[:1021] + "..."
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=url,
                caption=plain_caption,
                reply_markup=keyboard,
                reply_to_message_id=reply_to_message_id,
            )
    else:
        text = f"*{title}* ({item_date})\n\n{explanation}\n\nWatch here: {url}"
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                reply_to_message_id=reply_to_message_id,
            )
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{title} ({item_date})\n\n{explanation}\n\nWatch here: {url}",
                reply_markup=keyboard,
                reply_to_message_id=reply_to_message_id,
            )


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
    today_str = date.today().isoformat()
    one_year_ago = (date.today() - timedelta(days=365)).isoformat()
    help_text = (
        "🌌 **SpaceBuddy Commands:**\n\n"
        "/start - Greet the bot\n"
        f"/apod `[YYYY-MM-DD]` - Get NASA's photo of the day (e.g. `/apod 2026-10-30`)\n"
        f"   • *Date Range:* Within the last year ({one_year_ago} to {today_str})\n"
        "   • *Default:* If no date is given, today's APOD is shown\n"
        "/asteroids - View today's biggest approaching asteroids\n"
        "/help - Show all available commands"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")


async def apod(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /apod command - validates date and dispatches APOD retrieval."""
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

    await send_apod_content(
        chat_id=update.effective_chat.id,
        context=context,
        target_date=target_date,
        reply_to_message_id=update.message.message_id,
    )


async def apod_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle interactive inline keyboard button presses for APOD."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data

    if data == "apod_help":
        today_str = date.today().isoformat()
        one_year_ago = (date.today() - timedelta(days=365)).isoformat()
        await query.answer(
            text=(
                f"To view a custom date, type:\n"
                f"/apod YYYY-MM-DD\n\n"
                f"Valid range: {one_year_ago} to {today_str} (past year only)."
            ),
            show_alert=True,
        )
        return

    if data.startswith("apod_date:"):
        selected_date = data.split("apod_date:")[1]
        await query.answer(f"Loading APOD for {selected_date}...")
        await send_apod_content(
            chat_id=update.effective_chat.id,
            context=context,
            target_date=selected_date,
        )


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
