"""Unit tests for Telegram command and error handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.commands import start, help_cmd, apod, asteroids
from handlers.errors import on_error


@pytest.mark.asyncio
async def test_start_handler(mock_update, mock_context):
    """Test /start greets the user with their first name."""
    await start(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, kwargs = mock_update.message.reply_text.call_args
    assert "Hello, Alex!" in args[0]
    assert "SpaceBuddy" in args[0]


@pytest.mark.asyncio
async def test_help_handler(mock_update, mock_context):
    """Test /help replies with command listing."""
    await help_cmd(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, kwargs = mock_update.message.reply_text.call_args
    assert "/start" in args[0]
    assert "/apod" in args[0]
    assert "/asteroids" in args[0]
    assert "/help" in args[0]


@pytest.mark.asyncio
async def test_apod_handler_invalid_date(mock_update, mock_context):
    """Test /apod with malformed date immediately notifies user without API call."""
    mock_context.args = ["invalid-date"]

    await apod(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "⚠️ Date must be in YYYY-MM-DD format" in args[0]


@pytest.mark.asyncio
async def test_apod_handler_successful_photo(mock_update, mock_context):
    """Test /apod successfully sends photo with title and explanation."""
    fake_apod = {
        "title": "Night on a Spooky Planet",
        "explanation": "What spooky planet is this? Planet Earth.",
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/image.jpg",
    }

    mock_status_msg = MagicMock()
    mock_status_msg.delete = AsyncMock()
    mock_update.message.reply_text = AsyncMock(return_value=mock_status_msg)

    with patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod):
        await apod(mock_update, mock_context)

    mock_update.message.reply_photo.assert_called_once()
    _, kwargs = mock_update.message.reply_photo.call_args
    assert kwargs["photo"] == "https://assets.science.nasa.gov/apod/image.jpg"
    assert "Night on a Spooky Planet" in kwargs["caption"]


@pytest.mark.asyncio
async def test_apod_caption_truncation(mock_update, mock_context):
    """Test captions longer than 1024 characters are truncated to avoid Telegram API error."""
    very_long_text = "A" * 1500
    fake_apod = {
        "title": "Cosmic Wonder",
        "explanation": very_long_text,
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/image.jpg",
    }

    mock_status_msg = MagicMock()
    mock_status_msg.delete = AsyncMock()
    mock_update.message.reply_text = AsyncMock(return_value=mock_status_msg)

    with patch("services.nasa.default_nasa_service.fetch_apod", return_value=fake_apod):
        await apod(mock_update, mock_context)

    mock_update.message.reply_photo.assert_called_once()
    _, kwargs = mock_update.message.reply_photo.call_args
    assert len(kwargs["caption"]) <= 1024
    assert kwargs["caption"].endswith("...")


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

    # Verify largest asteroid is first
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
