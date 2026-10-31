"""Unit tests for configuration loading and validation."""
import os
import pytest
from unittest.mock import patch
from config import Config, load_config


def test_config_loads_with_valid_token(monkeypatch):
    """Test that config loads successfully when BOT_TOKEN is present."""
    monkeypatch.setenv("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setenv("NASA_API_KEY", "TEST_KEY_123")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    cfg = load_config()
    assert cfg.BOT_TOKEN == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert cfg.NASA_API_KEY == "TEST_KEY_123"
    assert cfg.LOG_LEVEL == "DEBUG"
    assert "SpaceBuddy" in cfg.USER_AGENT


def test_config_falls_back_to_demo_key(monkeypatch):
    """Test that NASA_API_KEY defaults to DEMO_KEY when not set."""
    monkeypatch.setenv("BOT_TOKEN", "fake_token_for_test")
    monkeypatch.delenv("NASA_API_KEY", raising=False)

    cfg = load_config()
    assert cfg.NASA_API_KEY == "DEMO_KEY"


def test_config_missing_token_raises_exit(monkeypatch):
    """Test that missing BOT_TOKEN cleanly raises SystemExit."""
    monkeypatch.delenv("BOT_TOKEN", raising=False)

    with pytest.raises(SystemExit):
        load_config()
