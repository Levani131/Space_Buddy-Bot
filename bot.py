import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from nasa_service import fetch_apod, fetch_today_asteroids

load_dotenv()
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO 1: Greet the user by first name
    first_name = update.effective_user.first_name or "Explorer"
    welcome_message = (
        f"Hello, {first_name}! 🚀 Welcome to SpaceBuddy.\n\n"
        "I can fetch NASA's Astronomy Picture of the Day and track today's asteroids.\n"
        "Type /help to see all available commands."
    )
    await update.message.reply_text(welcome_message)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO 2: Reply with a list of all commands
    help_text = (
        "🌌 **SpaceBuddy Commands:**\n\n"
        "/start - Greet the bot\n"
        "/apod - Get NASA's photo of the day\n"
        "/asteroids - View today's biggest approaching asteroids\n"
        "/help - Show all available commands"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def apod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO 3: Call fetch_apod with asyncio.to_thread, handle None, send photo + caption
    await update.message.reply_text("🔭 Fetching NASA's Picture of the Day...")
    
    # Check if a specific date was passed as an argument (Stretch Goal b)
    target_date = context.args[0] if context.args else None
    
    data = await asyncio.to_thread(fetch_apod, target_date)
    
    if not data:
        await update.message.reply_text("❌ Failed to fetch APOD from NASA. Please try again later.")
        return

    media_type = data.get("media_type")
    title = data.get("title", "Untitled")
    explanation = data.get("explanation", "No description available.")
    
    if media_type == "image":
        image_url = data.get("url")
        # Telegram captions have a 1024 character limit
        caption = f"*{title}*\n\n{explanation}"
        if len(caption) > 1024:
            caption = caption[:1021] + "..."
            
        try:
            await update.message.reply_photo(photo=image_url, caption=caption, parse_mode="Markdown")
        except Exception:
            # Fall back to plain text caption if markdown parsing fails
            plain_caption = f"{title}\n\n{explanation}"
            if len(plain_caption) > 1024:
                plain_caption = plain_caption[:1021] + "..."
            await update.message.reply_photo(photo=image_url, caption=plain_caption)
    else:
        # Handle videos (like YouTube embeds)
        url = data.get("url")
        try:
            await update.message.reply_text(f"*{title}*\n\n{explanation}\n\nWatch here: {url}", parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(f"{title}\n\n{explanation}\n\nWatch here: {url}")

async def asteroids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO 4: Call fetch_today_asteroids, sort by size, show the top 5
    await update.message.reply_text("☄️ Scanning for today's near-Earth asteroids...")
    
    neos = await asyncio.to_thread(fetch_today_asteroids)
    
    if not neos:
        await update.message.reply_text("📭 No asteroid data retrieved for today or none found.")
        return

    # Sort asteroids by estimated maximum diameter in descending order (biggest first)
    sorted_neos = sorted(neos, key=lambda x: x["diameter_m"], reverse=True)
    top_5 = sorted_neos[:5]

    response_lines = ["☄️ **Top 5 Biggest Asteroids Today:**\n"]
    for i, ast in enumerate(top_5, 1):
        hazard_emoji = "⚠️ (Hazardous)" if ast["is_hazardous"] else "✅ (Safe)"
        response_lines.append(
            f"*{i}. {ast['name']}* {hazard_emoji}\n"
            f"   • Diameter: ~{ast['diameter_m']:.1f} meters\n"
            f"   • Velocity: {ast['velocity_kmh']:,.0f} km/h\n"
            f"   • Miss Distance: {ast['miss_distance_km']:,.0f} km\n"
        )

    await update.message.reply_text("\n".join(response_lines), parse_mode="Markdown")

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    # TODO 5: Log context.error and tell the user something went wrong
    logging.error(f"Exception while handling an update: {context.error}")
    
    if isinstance(update, Update) and update.effective_message:
        await update.message.reply_text("⚠️ Oops! Something went wrong while processing your request.")

def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN missing in .env")
    
    app = Application.builder().token(TOKEN).build()
    
    # TODO 6: Add a CommandHandler for each command + the error handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("apod", apod))
    app.add_handler(CommandHandler("asteroids", asteroids))
    
    app.add_error_handler(on_error)
    
    print("SpaceBuddy is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
