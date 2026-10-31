"""NASA service interface for backwards compatibility with assignment structure."""
from services.nasa import NasaService, default_nasa_service, fetch_apod, fetch_today_asteroids

__all__ = ["NasaService", "default_nasa_service", "fetch_apod", "fetch_today_asteroids"]
