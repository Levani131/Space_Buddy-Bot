"""Shared test fixtures for SpaceBuddy."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.fixture
def sample_apod_wp_json():
    """Sample data matching science.nasa.gov/wp-json/wp/v2/apod-basic."""
    return [
        {
            "date": "2026-10-31",
            "title": "Night on a Spooky Planet",
            "explanation": "<strong>Explanation:</strong> What spooky planet is this? Planet Earth on a dark and stormy night.",
            "media_type": "image",
            "url": "https://science.nasa.gov/image-article/apod-2026-october-31-night-on-a-spooky-planet/",
            "hdurl": "https://assets.science.nasa.gov/apod/Hverir_Vetter_1300.jpg",
        }
    ]


@pytest.fixture
def sample_apod_legacy_json():
    """Sample data matching api.nasa.gov/planetary/apod."""
    return {
        "date": "2026-10-25",
        "title": "The Pillars of Creation",
        "explanation": "An iconic view of cosmic star-forming pillars in the Eagle Nebula.",
        "media_type": "image",
        "url": "https://apod.nasa.gov/apod/image/pillars.jpg",
        "hdurl": "https://apod.nasa.gov/apod/image/pillars_hd.jpg",
    }


@pytest.fixture
def sample_neows_json():
    """Sample data matching api.nasa.gov/neo/rest/v1/feed."""
    today_str = date.today().isoformat()
    return {
        "element_count": 3,
        "near_earth_objects": {
            today_str: [
                {
                    "name": "Asteroid Alpha",
                    "estimated_diameter": {"meters": {"estimated_diameter_max": 450.5}},
                    "is_potentially_hazardous_asteroid": True,
                    "close_approach_data": [
                        {
                            "relative_velocity": {"kilometers_per_hour": "72000.0"},
                            "miss_distance": {"kilometers": "1500000.0"},
                        }
                    ],
                },
                {
                    "name": "Asteroid Beta",
                    "estimated_diameter": {"meters": {"estimated_diameter_max": 85.0}},
                    "is_potentially_hazardous_asteroid": False,
                    "close_approach_data": [
                        {
                            "relative_velocity": {"kilometers_per_hour": "35000.0"},
                            "miss_distance": {"kilometers": "4200000.0"},
                        }
                    ],
                },
                {
                    "name": "Asteroid Gamma",
                    "estimated_diameter": {"meters": {"estimated_diameter_max": 920.0}},
                    "is_potentially_hazardous_asteroid": True,
                    "close_approach_data": [
                        {
                            "relative_velocity": {"kilometers_per_hour": "98000.0"},
                            "miss_distance": {"kilometers": "890000.0"},
                        }
                    ],
                },
            ]
        },
    }


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update."""
    update = MagicMock()
    update.effective_user.first_name = "Alex"
    update.effective_user.id = 12345
    update.effective_chat.id = 67890

    update.message.reply_text = AsyncMock()
    update.message.reply_photo = AsyncMock()
    update.effective_message = update.message
    return update


@pytest.fixture
def mock_context():
    """Create a mock Telegram Context."""
    context = MagicMock()
    context.args = []
    context.bot.send_chat_action = AsyncMock()
    return context
