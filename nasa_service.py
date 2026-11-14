"""NASA service interface for backwards compatibility with assignment structure."""
from services.nasa import (
    APOD_LAUNCH_DATE,
    NasaService,
    default_nasa_service,
    fetch_apod,
    fetch_today_asteroids,
    validate_apod_date,
)

__all__ = [
    "APOD_LAUNCH_DATE",
    "NasaService",
    "default_nasa_service",
    "fetch_apod",
    "fetch_today_asteroids",
    "validate_apod_date",
]
