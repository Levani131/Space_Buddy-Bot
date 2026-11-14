"""Unit tests for Telegram command and callback handlers."""
from datetime import date, timedelta
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from database.db_manager import DatabaseManager
from handlers.commands import apod, apod_callback, asteroids, help_cmd, save_apod_callback, start
from handlers.errors import on_error


@pytest.mark.asyncio
async def test_start_handler(mock_update, mock_context):
    """Test /start greets the user with their first name."""
    await start(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "Hello, Alex!" in args[0]
    assert "SpaceBuddy" in args[0]


@pytest.mark.asyncio
async def test_help_handler(mock_update, mock_context):
    """Test /help replies with command listing including APOD date options."""
    await help_cmd(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "/start" in args[0]
    assert "/apod" in args[0]
    assert "Within the last year" in args[0]
    assert "/asteroids" in args[0]
    assert "/help" in args[0]


@pytest.mark.asyncio
async def test_apod_handler_no_date_loads_today(mock_update, mock_context):
    """Verify that today's APOD loads when no date argument is provided."""
    mock_context.args = []
    fake_apod = {
        "title": "Today's Cosmic Picture",
        "explanation": "Stunning view of the cosmos today.",
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/today.jpg",
        "date": date.today().isoformat(),
    }

    mock_status_msg = MagicMock()
    mock_status_msg.delete = AsyncMock()
    mock_context.bot.send_message = AsyncMock(return_value=mock_status_msg)
    mock_context.bot.send_photo = AsyncMock()

    with patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod) as mock_fetch:
        await apod(mock_update, mock_context)
        mock_fetch.assert_called_once_with(None)

    mock_context.bot.send_photo.assert_called_once()
    _, kwargs = mock_context.bot.send_photo.call_args
    assert kwargs["photo"] == "https://assets.science.nasa.gov/apod/today.jpg"
    assert "Today's Cosmic Picture" in kwargs["caption"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_apod_handler_valid_past_date(mock_update, mock_context):
    """Verify that a valid past date within the last year loads correctly."""
    valid_past = (date.today() - timedelta(days=20)).isoformat()
    mock_context.args = [valid_past]

    fake_apod = {
        "title": "Past Cosmic Wonder",
        "explanation": "Observing stars from days ago.",
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/past.jpg",
        "date": valid_past,
    }

    mock_status_msg = MagicMock()
    mock_status_msg.delete = AsyncMock()
    mock_context.bot.send_message = AsyncMock(return_value=mock_status_msg)
    mock_context.bot.send_photo = AsyncMock()

    with patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod) as mock_fetch:
        await apod(mock_update, mock_context)
        mock_fetch.assert_called_once_with(valid_past)

    mock_context.bot.send_photo.assert_called_once()
    _, kwargs = mock_context.bot.send_photo.call_args
    assert "Past Cosmic Wonder" in kwargs["caption"]
    assert valid_past in kwargs["caption"]


@pytest.mark.asyncio
async def test_apod_handler_invalid_date_format(mock_update, mock_context):
    """Verify error message when invalid date format is entered."""
    mock_context.args = ["not-a-valid-date"]

    await apod(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "⚠️ Invalid date format" in args[0]
    assert "YYYY-MM-DD" in args[0]


@pytest.mark.asyncio
async def test_apod_handler_future_date_error(mock_update, mock_context):
    """Verify error message when a future date is requested."""
    future_date = (date.today() + timedelta(days=5)).isoformat()
    mock_context.args = [future_date]

    await apod(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "cannot be in the future" in args[0].lower()


@pytest.mark.asyncio
async def test_apod_handler_out_of_range_past_date_error(mock_update, mock_context):
    """Verify error message when date is older than APOD launch date (1995-06-16)."""
    old_date = "1990-01-01"
    mock_context.args = [old_date]

    await apod(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "1995-06-16" in args[0]


@pytest.mark.asyncio
async def test_apod_caption_truncation(mock_update, mock_context):
    """Test captions longer than 1024 characters are truncated to avoid Telegram API error."""
    mock_context.args = []
    fake_apod = {
        "title": "Cosmic Wonder",
        "explanation": "A" * 1500,
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/image.jpg",
        "date": date.today().isoformat(),
    }

    mock_status_msg = MagicMock()
    mock_status_msg.delete = AsyncMock()
    mock_context.bot.send_message = AsyncMock(return_value=mock_status_msg)
    mock_context.bot.send_photo = AsyncMock()

    with patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod):
        await apod(mock_update, mock_context)

    mock_context.bot.send_photo.assert_called_once()
    _, kwargs = mock_context.bot.send_photo.call_args
    assert len(kwargs["caption"]) <= 1024
    assert kwargs["caption"].endswith("...")


@pytest.mark.asyncio
async def test_apod_callback_date_selection(mock_update, mock_context):
    """Verify clicking an inline date button triggers APOD for that date."""
    target_date = (date.today() - timedelta(days=1)).isoformat()
    mock_query = MagicMock()
    mock_query.data = f"apod_date:{target_date}"
    mock_query.answer = AsyncMock()
    mock_update.callback_query = mock_query

    mock_status_msg = MagicMock()
    mock_status_msg.delete = AsyncMock()
    mock_context.bot.send_message = AsyncMock(return_value=mock_status_msg)
    mock_context.bot.send_photo = AsyncMock()

    fake_apod = {
        "title": "Yesterday's Photo",
        "explanation": "Universe yesterday.",
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/yesterday.jpg",
        "date": target_date,
    }

    with patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod) as mock_fetch:
        await apod_callback(mock_update, mock_context)
        mock_fetch.assert_called_once_with(target_date)

    mock_query.answer.assert_called_once()
    mock_context.bot.send_photo.assert_called_once()


@pytest.mark.asyncio
async def test_apod_callback_help(mock_update, mock_context):
    """Verify clicking help button displays custom date guidance alert."""
    mock_query = MagicMock()
    mock_query.data = "apod_help"
    mock_query.answer = AsyncMock()
    mock_update.callback_query = mock_query

    await apod_callback(mock_update, mock_context)

    mock_query.answer.assert_called_once()
    _, kwargs = mock_query.answer.call_args
    assert kwargs["show_alert"] is True
    assert "/apod YYYY-MM-DD" in kwargs["text"]


@pytest.mark.asyncio
async def test_asteroids_handler(mock_update, mock_context):
    """Test /asteroids ranks top 5 asteroids descending by diameter."""
    fake_asteroids = [
        {"name": "Small", "diameter_m": 50.0, "is_hazardous": False, "velocity_kmh": 20000, "miss_distance_km": 500000},
        {"name": "Huge", "diameter_m": 800.0, "is_hazardous": True, "velocity_kmh": 60000, "miss_distance_km": 100000},
        {"name": "Medium", "diameter_m": 300.0, "is_hazardous": False, "velocity_kmh": 40000, "miss_distance_km": 300000},
    ]

    mock_status_msg = MagicMock()
    mock_status_msg.delete = AsyncMock()
    mock_update.message.reply_text = AsyncMock(return_value=mock_status_msg)

    with patch("services.nasa.default_nasa_service.fetch_today_asteroids", return_value=fake_asteroids):
        await asteroids(mock_update, mock_context)

    # First call was status message, second was final message
    assert mock_update.message.reply_text.call_count == 2
    final_args, _ = mock_update.message.reply_text.call_args_list[1]
    final_text = final_args[0]

    assert "1. Huge" in final_text
    assert "2. Medium" in final_text
    assert "3. Small" in final_text
    assert "⚠️ (Hazardous)" in final_text


@pytest.mark.asyncio
async def test_on_error_handler(mock_update, mock_context):
    """Test on_error logs error and informs the user."""
    mock_context.error = RuntimeError("Simulated API failure")

    await on_error(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_called_once()
    args, _ = mock_update.effective_message.reply_text.call_args
    assert "Oops! Something went wrong" in args[0]


class TestSaveApodCallbackIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite verifying offline save_apod callback flow using unittest."""

    async def test_save_apod_callback_integration(self):
        """Verify 'save_apod:2024-05-12' callback stores photo in :memory: DB and answers with toast."""
        # 1. Use DatabaseManager(":memory:") for the database
        db = DatabaseManager(":memory:")

        # 2. Mock fake NASA APOD dictionary
        fake_apod = {
            "date": "2024-05-12",
            "title": "Mock Nebula",
            "url": "https://nasa.gov/nebula.jpg",
        }

        # 3. Create a MagicMock() simulating a Telegram CallbackQuery
        call = MagicMock()
        call.id = "query_42"
        call.data = "save_apod:2024-05-12"
        call.from_user.id = 42
        call.from_user.username = "skywatcher42"
        call.from_user.first_name = "Arthur"

        mock_update = MagicMock()
        mock_update.callback_query = call
        mock_update.effective_user = call.from_user

        mock_context = MagicMock()
        mock_context.bot.answer_callback_query = AsyncMock()

        # 4. Trigger callback handler and assert storage in :memory: DB & toast notification
        with patch("handlers.apod_handler.db", db), \
             patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod):
            await save_apod_callback(mock_update, mock_context)

        # Assert photo is stored in the :memory: SQLite database
        self.assertEqual(len(db.get_user_favorites(42)), 1)
        fav = db.get_user_favorites(42)[0]
        self.assertEqual(fav["apod_date"], "2024-05-12")
        self.assertEqual(fav["title"], "Mock Nebula")
        self.assertEqual(fav["media_url"], "https://nasa.gov/nebula.jpg")

        # Assert bot.answer_callback_query was called once with success message
        mock_context.bot.answer_callback_query.assert_called_once()
        _, kwargs = mock_context.bot.answer_callback_query.call_args
        self.assertEqual(kwargs["callback_query_id"], "query_42")
        self.assertIn("Saved to favorites", kwargs["text"])

        db.close()
