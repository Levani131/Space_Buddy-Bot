"""NASA Open API service integration.

Provides resilient access to:
1. Astronomy Picture of the Day (APOD) via dual-endpoint routing and caching.
2. Near-Earth Object Web Service (NeoWs) for daily close-approach tracking.
"""
import html
import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from config import config

logger = logging.getLogger(__name__)

# The very first NASA APOD was published on June 16, 1995
APOD_MIN_DATE = date(1995, 6, 16)


class NasaService:
    """Service client for NASA public APIs."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.NASA_API_KEY
        self.headers = {"User-Agent": config.USER_AGENT}
        self.timeout = 10
        # In-memory daily cache: { "YYYY-MM-DD": apod_dict }
        self._apod_cache: Dict[str, Dict[str, Any]] = {}

    def validate_date(self, date_str: str) -> Tuple[bool, Optional[str]]:
        """Validate if a string is a valid APOD date (YYYY-MM-DD between 1995-06-16 and today)."""
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return False, "Date must be in YYYY-MM-DD format (e.g., 2026-10-25)."

        today = date.today()
        if parsed_date < APOD_MIN_DATE:
            return False, f"APOD archive begins on {APOD_MIN_DATE.isoformat()}."
        if parsed_date > today:
            return False, "Cannot fetch APOD for future dates."

        return True, None

    def safe_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Safely make a GET request to an external API with error logging."""
        try:
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"GET request failed for {url}: {e}")
            return None

    def _fetch_from_apod_basic(self, target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch from NASA Science WP-JSON endpoint.
        
        Bypasses legacy api.nasa.gov scraper bugs (such as title='NASA Science' and site logo png)
        and rate limit restrictions.
        """
        url = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            items = response.json()
            if not items or not isinstance(items, list):
                return None

            selected = items[0]
            if target_date:
                matched = False
                for item in items:
                    if item.get("date") == target_date:
                        selected = item
                        matched = True
                        break
                if not matched:
                    # Target date is older than the recent cache of apod-basic
                    return None

            # Clean HTML tags and prefixes from explanation
            raw_exp = selected.get("explanation", "")
            clean_exp = re.sub(r"<[^>]+>", "", raw_exp)
            clean_exp = re.sub(r"^Explanation:\s*", "", clean_exp.strip())
            clean_exp = html.unescape(clean_exp)

            media_type = selected.get("media_type", "image")
            # hdurl has the direct high-res image asset URL; url is article link
            image_url = selected.get("hdurl") or selected.get("url")

            return {
                "title": selected.get("title", "Astronomy Picture of the Day"),
                "explanation": clean_exp,
                "media_type": media_type,
                "url": image_url,
                "hdurl": selected.get("hdurl"),
                "date": selected.get("date"),
            }
        except Exception as e:
            logger.debug(f"WP-JSON apod-basic fetch failed: {e}")
            return None

    def fetch_apod(self, target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch Astronomy Picture of the Day.
        
        Checks memory cache first, then queries NASA Science endpoint,
        and finally falls back to legacy api.nasa.gov if required.
        """
        cache_key = target_date or date.today().isoformat()
        if cache_key in self._apod_cache:
            logger.info(f"Serving APOD for {cache_key} from cache.")
            return self._apod_cache[cache_key]

        # 1. Try modern NASA Science endpoint first
        data = self._fetch_from_apod_basic(target_date)

        # 2. Fall back to legacy api.nasa.gov if needed
        if not data:
            url = "https://api.nasa.gov/planetary/apod"
            params = {"api_key": self.api_key}
            if target_date:
                params["date"] = target_date
            legacy_data = self.safe_get(url, params=params)

            if legacy_data and legacy_data.get("title") != "NASA Science" and "nasa-logo" not in legacy_data.get("url", ""):
                data = legacy_data

        if data:
            self._apod_cache[cache_key] = data

        return data

    def fetch_today_asteroids(self) -> List[Dict[str, Any]]:
        """Fetch and structure today's approaching near-Earth asteroids from NASA NeoWs API."""
        today_str = date.today().isoformat()
        url = "https://api.nasa.gov/neo/rest/v1/feed"
        params = {
            "start_date": today_str,
            "end_date": today_str,
            "api_key": self.api_key,
        }

        data = self.safe_get(url, params=params)
        if not data or "near_earth_objects" not in data:
            return []

        todays_neos = data["near_earth_objects"].get(today_str, [])
        asteroids: List[Dict[str, Any]] = []

        for neo in todays_neos:
            name = neo.get("name", "Unknown")
            diameter_max = neo.get("estimated_diameter", {}).get("meters", {}).get("estimated_diameter_max", 0.0)
            is_hazardous = neo.get("is_potentially_hazardous_asteroid", False)

            approach_list = neo.get("close_approach_data", [])
            approach_data = approach_list[0] if approach_list else {}

            velocity_kmh = float(
                approach_data.get("relative_velocity", {}).get("kilometers_per_hour", 0.0)
            )
            miss_distance_km = float(
                approach_data.get("miss_distance", {}).get("kilometers", 0.0)
            )

            asteroids.append({
                "name": name,
                "diameter_m": diameter_max,
                "is_hazardous": is_hazardous,
                "velocity_kmh": velocity_kmh,
                "miss_distance_km": miss_distance_km,
            })

        return asteroids


# Default shared instance
default_nasa_service = NasaService()

# Exportable functional API for drop-in compatibility
def fetch_apod(target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return default_nasa_service.fetch_apod(target_date)

def fetch_today_asteroids() -> List[Dict[str, Any]]:
    return default_nasa_service.fetch_today_asteroids()
