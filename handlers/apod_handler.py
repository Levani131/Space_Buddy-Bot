"""APOD command and callback query handlers for SpaceBuddy."""
import asyncio
from datetime import date, datetime, timedelta
import logging
import random
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from config import config
from database.db_manager import DatabaseManager
from services.nasa import default_nasa_service, validate_apod_date

logger = logging.getLogger(__name__)

# Shared database instance for APOD handlers
db = DatabaseManager(config.DATABASE_PATH)


def get_apod_keyboard(apod_date: str) -> InlineKeyboardMarkup:
    """Generate interactive inline keyboard with Save to Favorites and navigation controls."""
    today = date.today()
    try:
        current_dt = datetime.strptime(apod_date, "%Y-%m-%d").date()
    except Exception:
        current_dt = today

    yesterday = (current_dt - timedelta(days=1)).isoformat()
    random_days = random.randint(1, 365 * 10)
    random_date = (today - timedelta(days=random_days)).isoformat()

    buttons = [
        [
            InlineKeyboardButton("⭐ Save to Favorites", callback_data=f"save_apod:{apod_date}"),
        ],
        [
            InlineKeyboardButton("📅 Yesterday", callback_data=f"apod_date:{yesterday}"),
            InlineKeyboardButton("🎲 Random Date", callback_data=f"apod_date:{random_date}"),
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
    """Fetch and deliver APOD content to the user with media routing and interactive controls."""
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
    url = data.get("url", "")
    item_date = data.get("date", display_date)

    # Delete temporary status message
    try:
        await status_msg.delete()
    except Exception:
        pass

    keyboard = get_apod_keyboard(item_date)

    # Gracefully handle media_type == "video" (e.g. YouTube / Vimeo video URLs)
    if media_type == "video":
        text = f"🎥 *{title}* ({item_date})\n\n{explanation}\n\nWatch here: {url}"
        if len(text) > 4096:
            text = text[:4093] + "..."

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                reply_to_message_id=reply_to_message_id,
            )
        except Exception:
            plain_text = f"🎥 {title} ({item_date})\n\n{explanation}\n\nWatch here: {url}"
            if len(plain_text) > 4096:
                plain_text = plain_text[:4093] + "..."
            await context.bot.send_message(
                chat_id=chat_id,
                text=plain_text,
                reply_markup=keyboard,
                reply_to_message_id=reply_to_message_id,
            )
    else:
        # media_type == "image" (or standard image URLs)
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
            plain_caption = f"{title} ({item_date})\n\n{explanation}"
            if len(plain_caption) > 1024:
                plain_caption = plain_caption[:1021] + "..."
            try:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=url,
                    caption=plain_caption,
                    reply_markup=keyboard,
                    reply_to_message_id=reply_to_message_id,
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{plain_caption}\n\n{url}",
                    reply_markup=keyboard,
                    reply_to_message_id=reply_to_message_id,
                )


async def apod(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /apod command - registers user, validates date, and dispatches APOD retrieval."""
    if not update.message:
        return

    # Register user in SQLite database if valid user_id is present
    user = update.effective_user
    if user:
        raw_uid = getattr(user, "id", None)
        raw_uname = getattr(user, "username", None)
        raw_fname = getattr(user, "first_name", "Explorer")

        user_id = raw_uid if isinstance(raw_uid, int) else None
        username = raw_uname if isinstance(raw_uname, str) else None
        first_name = raw_fname if isinstance(raw_fname, str) else "Explorer"

        if user_id is not None:
            try:
                db.register_user(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                )
            except Exception as e:
                logger.warning(f"Failed to register user in DB: {e}")

    # Check for optional target date argument (/apod YYYY-MM-DD)
    target_date = context.args[0] if context.args else None

    # Validate date format and bounds if provided
    if target_date:
        is_valid, error_msg = validate_apod_date(target_date)
        if not is_valid:
            await update.message.reply_text(f"⚠️ {error_msg}")
            return

    await send_apod_content(
        chat_id=update.effective_chat.id,
        context=context,
        target_date=target_date,
        reply_to_message_id=update.message.message_id,
    )


async def save_apod_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'save_apod:{apod_date}' callback queries to save bookmark to SQLite."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    if not data.startswith("save_apod:"):
        return

    apod_date = data.split("save_apod:")[1]
    user = update.effective_user or query.from_user

    # Ensure user is registered in database before saving bookmark
    raw_uid = getattr(user, "id", None) if user else None
    raw_uname = getattr(user, "username", None) if user else None
    raw_fname = getattr(user, "first_name", "Explorer") if user else "Explorer"

    user_id = raw_uid if isinstance(raw_uid, int) else (update.effective_chat.id if update.effective_chat else 1)
    username = raw_uname if isinstance(raw_uname, str) else None
    first_name = raw_fname if isinstance(raw_fname, str) else "Explorer"

    if isinstance(user_id, int):
        try:
            db.register_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
            )
        except Exception as e:
            logger.warning(f"Failed to register user during save callback: {e}")

    # Fetch APOD metadata
    apod_info = await asyncio.to_thread(default_nasa_service.fetch_apod, apod_date)
    if apod_info:
        title = apod_info.get("title", f"APOD ({apod_date})")
        media_url = apod_info.get("hdurl") or apod_info.get("url", "")
    else:
        title = f"APOD ({apod_date})"
        media_url = ""

    user_id = user.id if user else update.effective_chat.id
    is_new = db.save_apod(
        user_id=user_id,
        apod_date=apod_date,
        title=title,
        media_url=media_url,
    )

    toast_text = "⭐ Saved to favorites!" if is_new else "ℹ️ Already in your favorites!"

    # Show popup toast via bot.answer_callback_query
    await context.bot.answer_callback_query(
        callback_query_id=query.id,
        text=toast_text,
        show_alert=False,
    )


async def apod_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle interactive inline keyboard button presses for APOD."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data

    if data.startswith("save_apod:"):
        await save_apod_callback(update, context)
        return

    if data == "apod_help":
        today_str = date.today().isoformat()
        await query.answer(
            text=(
                f"To view a custom date, type:\n"
                f"/apod YYYY-MM-DD\n\n"
                f"Valid range: 1995-06-16 to {today_str}."
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
