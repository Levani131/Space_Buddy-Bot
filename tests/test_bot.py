"""Unit tests for bot application creation and backwards-compatibility shims."""
from bot import create_app
import main
import nasa_service
from telegram.ext import CommandHandler


def test_create_app_registers_all_handlers():
    """Verify create_app registers start, help, apod, and asteroids handlers."""
    app = create_app()
    handlers = app.handlers.get(0, [])

    registered_commands = [
        cmd for h in handlers if isinstance(h, CommandHandler) for cmd in h.commands
    ]

    assert "start" in registered_commands
    assert "help" in registered_commands
    assert "apod" in registered_commands
    assert "asteroids" in registered_commands
    assert len(app.error_handlers) >= 1


def test_nasa_service_shim_compatibility():
    """Verify nasa_service.py exports fetch_apod and fetch_today_asteroids."""
    assert hasattr(nasa_service, "fetch_apod")
    assert hasattr(nasa_service, "fetch_today_asteroids")
    assert callable(nasa_service.fetch_apod)
    assert callable(nasa_service.fetch_today_asteroids)


def test_main_shim_compatibility():
    """Verify main.py exports fetch_apod, fetch_today_asteroids, and main."""
    assert hasattr(main, "main")
    assert hasattr(main, "fetch_apod")
    assert hasattr(main, "fetch_today_asteroids")
    assert callable(main.main)
