"""Unit tests for APOD date-selection, save button, and video handling."""
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from database.db_manager import DatabaseManager
from handlers.apod_handler import (
    apod,
    apod_callback,
    get_apod_keyboard,
    save_apod_callback,
    send_apod_content,
)
from services.nasa import validate_apod_date


def test_validate_apod_date_requirements():
    """Verify validate_apod_date checks format and bounds (1995-06-16 to today)."""
    # Valid date
    valid, err = validate_apod_date("2024-05-12")
    assert valid is True
    assert err == ""

    # APOD Launch Date (1995-06-16)
    valid, err = validate_apod_date("1995-06-16")
    assert valid is True
    assert err == ""

    # Date before APOD launch
    valid, err = validate_apod_date("1995-06-15")
    assert valid is False
    assert "1995-06-16" in err

    # Future date
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    valid, err = validate_apod_date(tomorrow)
    assert valid is False
    assert "future" in err.lower()

    # Invalid formats
    for bad in ["2024/05/12", "12-05-2024", "invalid-str", "2024-02-30"]:
        valid, err = validate_apod_date(bad)
        assert valid is False
        assert "YYYY-MM-DD" in err


def test_get_apod_keyboard_contains_save_button():
    """Verify get_apod_keyboard contains '⭐ Save to Favorites' button with save_apod:callback_data."""
    kb = get_apod_keyboard("2024-05-12")
    buttons = [btn for row in kb.inline_keyboard for btn in row]

    save_btn = next((b for b in buttons if b.callback_data == "save_apod:2024-05-12"), None)
    assert save_btn is not None
    assert save_btn.text == "⭐ Save to Favorites"


@pytest.mark.asyncio
async def test_apod_command_registers_user_and_attaches_save_button(mock_update, mock_context):
    """Verify /apod 2024-05-12 registers user in SQLite and attaches save button."""
    test_db = DatabaseManager(":memory:")
    mock_context.args = ["2024-05-12"]

    mock_update.effective_user.id = 777
    mock_update.effective_user.username = "stargazer777"
    mock_update.effective_user.first_name = "Stella"

    fake_apod = {
        "title": "Cosmic Cloud",
        "explanation": "A vast nebula in deep space.",
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/cloud.jpg",
        "date": "2024-05-12",
    }

    mock_status = MagicMock()
    mock_status.delete = AsyncMock()
    mock_context.bot.send_message = AsyncMock(return_value=mock_status)
    mock_context.bot.send_photo = AsyncMock()

    with patch("handlers.apod_handler.db", test_db), \
         patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod):
        await apod(mock_update, mock_context)

    # 1. User was registered in SQLite
    user = test_db.get_user(777)
    assert user is not None
    assert user["username"] == "stargazer777"
    assert user["first_name"] == "Stella"

    # 2. send_photo was called with save button in reply_markup
    mock_context.bot.send_photo.assert_called_once()
    _, kwargs = mock_context.bot.send_photo.call_args
    reply_markup = kwargs["reply_markup"]
    assert reply_markup is not None

    buttons = [btn for row in reply_markup.inline_keyboard for btn in row]
    save_btn = next((b for b in buttons if b.callback_data == "save_apod:2024-05-12"), None)
    assert save_btn is not None
    assert save_btn.text == "⭐ Save to Favorites"

    test_db.close()


@pytest.mark.asyncio
async def test_save_apod_callback_new_and_duplicate(mock_update, mock_context):
    """Verify save_apod_callback saves bookmark to SQLite and displays appropriate toast."""
    test_db = DatabaseManager(":memory:")

    mock_query = MagicMock()
    mock_query.id = "cb_query_123"
    mock_query.data = "save_apod:2024-05-12"
    mock_query.from_user.id = 888
    mock_query.from_user.username = "galaxy_scout"
    mock_query.from_user.first_name = "Gal"
    mock_update.callback_query = mock_query
    mock_update.effective_user = mock_query.from_user

    mock_context.bot.answer_callback_query = AsyncMock()

    fake_apod = {
        "title": "Andromeda Galaxy",
        "explanation": "Our spiral galactic neighbor.",
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/andromeda.jpg",
        "date": "2024-05-12",
    }

    with patch("handlers.apod_handler.db", test_db), \
         patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod):

        # First save -> Newly saved
        await save_apod_callback(mock_update, mock_context)
        mock_context.bot.answer_callback_query.assert_called_once()
        _, kwargs1 = mock_context.bot.answer_callback_query.call_args
        assert "Saved to favorites" in kwargs1["text"]
        assert kwargs1["callback_query_id"] == "cb_query_123"

        # Check bookmark was persisted in DB
        favs = test_db.get_user_favorites(888)
        assert len(favs) == 1
        assert favs[0]["apod_date"] == "2024-05-12"
        assert favs[0]["title"] == "Andromeda Galaxy"

        # Second save -> Already in favorites
        mock_context.bot.answer_callback_query.reset_mock()
        await save_apod_callback(mock_update, mock_context)
        mock_context.bot.answer_callback_query.assert_called_once()
        _, kwargs2 = mock_context.bot.answer_callback_query.call_args
        assert "Already in your favorites" in kwargs2["text"]

    test_db.close()


@pytest.mark.asyncio
async def test_send_apod_content_video_handling(mock_update, mock_context):
    """Verify media_type == 'video' uses bot.send_message instead of bot.send_photo."""
    fake_video_apod = {
        "title": "Tour of the Moon",
        "explanation": "Virtual journey across the lunar craters.",
        "media_type": "video",
        "url": "https://www.youtube.com/watch?v=2iSZMv64wuU",
        "date": "2024-05-12",
    }

    mock_status = MagicMock()
    mock_status.delete = AsyncMock()
    mock_context.bot.send_message = AsyncMock(return_value=mock_status)
    mock_context.bot.send_photo = AsyncMock()

    with patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_video_apod):
        await send_apod_content(chat_id=12345, context=mock_context, target_date="2024-05-12")

    # send_photo should NOT have been called
    mock_context.bot.send_photo.assert_not_called()

    # send_message should have been called (first for status, second for video content)
    assert mock_context.bot.send_message.call_count == 2
    _, kwargs = mock_context.bot.send_message.call_args_list[1]
    assert "https://www.youtube.com/watch?v=2iSZMv64wuU" in kwargs["text"]
    assert "Tour of the Moon" in kwargs["text"]
    assert kwargs["reply_markup"] is not None

