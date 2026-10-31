"""Main entrypoint and backwards-compatible interface for SpaceBuddy."""
from bot import main
from services.nasa import default_nasa_service, fetch_apod, fetch_today_asteroids

# Expose safe_get as a convenience method
safe_get = default_nasa_service.safe_get

__all__ = ["main", "fetch_apod", "fetch_today_asteroids", "safe_get"]

if __name__ == "__main__":
    main()
