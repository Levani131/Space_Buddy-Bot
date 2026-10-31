"""Configuration loader and validator for SpaceBuddy."""
import logging
import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str
    NASA_API_KEY: str = "DEMO_KEY"
    LOG_LEVEL: str = "INFO"
    USER_AGENT: str = "SpaceBuddy/1.0 (Mozilla/5.0, Windows NT 10.0; Win64; x64)"

def load_config() -> Config:
    """Load and validate environment configuration."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.error("BOT_TOKEN is missing in .env")
        sys.exit("Error: BOT_TOKEN is missing in .env. Please add your Telegram Bot Token.")
        
    nasa_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    return Config(
        BOT_TOKEN=token.strip().strip('"').strip("'"),
        NASA_API_KEY=nasa_key.strip().strip('"').strip("'"),
        LOG_LEVEL=log_level
    )

config = load_config()
