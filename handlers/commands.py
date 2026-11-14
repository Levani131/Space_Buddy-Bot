"""Telegram bot command and callback handlers for SpaceBuddy."""
import asyncio
from datetime import date, timedelta
import logging
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from handlers.apod_handler import (
    apod,
    apod_callback,
    get_apod_keyboard,
    save_apod_callback,
    send_apod_content,
)
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
    today_str = date.today().isoformat()
    help_text = (
        "🌌 **SpaceBuddy Commands:**\n\n"
        "/start - Greet the bot\n"
        f"/apod `[YYYY-MM-DD]` - Get NASA's photo of the day (e.g. `/apod 2024-05-12`)\n"
        f"   • *Date Range:* Within the last year or back to 1995-06-16 (1995-06-16 to {today_str})\n"
        "   • *Default:* If no date is given, today's APOD is shown\n"
        "/asteroids - View today's biggest approaching asteroids\n"
        "/help - Show all available commands"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")


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


__all__ = [
    "start",
    "help_cmd",
    "apod",
    "apod_callback",
    "save_apod_callback",
    "asteroids",
    "send_apod_content",
    "get_apod_keyboard",
]
