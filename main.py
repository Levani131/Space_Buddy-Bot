import html
import os
import re
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

DEFAULT_HEADERS = {
    "User-Agent": "SpaceBuddy/1.0 (Mozilla/5.0, Windows NT 10.0; Win64; x64)"
}

def safe_get(url, params=None):
    """Safely make a GET request to an external API with basic error handling."""
    try:
        response = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

def _fetch_from_apod_basic(target_date=None):
    """Fetch from NASA Science's modern WP-JSON APOD endpoint."""
    try:
        response = requests.get(
            "https://science.nasa.gov/wp-json/wp/v2/apod-basic",
            headers=DEFAULT_HEADERS,
            timeout=10
        )
        response.raise_for_status()
        items = response.json()
        if not items:
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
                return None
        
        # Clean HTML tags and prefixes from explanation
        raw_exp = selected.get("explanation", "")
        clean_exp = re.sub(r'<[^>]+>', '', raw_exp)
        clean_exp = re.sub(r'^Explanation:\s*', '', clean_exp.strip())
        clean_exp = html.unescape(clean_exp)
        
        media_type = selected.get("media_type", "image")
        image_url = selected.get("hdurl") or selected.get("url")
        
        return {
            "title": selected.get("title", "Astronomy Picture of the Day"),
            "explanation": clean_exp,
            "media_type": media_type,
            "url": image_url,
            "hdurl": selected.get("hdurl"),
            "date": selected.get("date")
        }
    except Exception as e:
        print(f"Failed to fetch from apod-basic: {e}")
        return None

def fetch_apod(target_date=None):
    """Fetch Astronomy Picture of the Day.
    
    1. Tries NASA Science WP-JSON endpoint first (fast, reliable, and avoids the
       legacy api.nasa.gov 500 Server Error and 'NASA Science' logo scraper bug).
    2. Falls back to api.nasa.gov/planetary/apod if needed.
    """
    # 1. Try modern NASA Science endpoint first
    basic_data = _fetch_from_apod_basic(target_date)
    if basic_data:
        return basic_data

    # 2. Fall back to legacy api.nasa.gov
    url = "https://api.nasa.gov/planetary/apod"
    params = {"api_key": NASA_API_KEY}
    if target_date:
        params["date"] = target_date
    data = safe_get(url, params=params)
    
    if data and data.get("title") != "NASA Science" and "nasa-logo" not in data.get("url", ""):
        return data
        
    return basic_data or data

def fetch_today_asteroids():
    """Fetch close approach asteroids for today's date from NASA NeoWs API."""
    today_str = date.today().isoformat()
    url = "https://api.nasa.gov/neo/rest/v1/feed"
    params = {
        "start_date": today_str,
        "end_date": today_str,
        "api_key": NASA_API_KEY
    }
    data = safe_get(url, params=params)
    if not data or "near_earth_objects" not in data:
        return []
    
    # Extract today's asteroid list
    todays_neos = data["near_earth_objects"].get(today_str, [])
    asteroids = []
    
    for neo in todays_neos:
        name = neo.get("name", "Unknown")
        # Get maximum estimated diameter in meters
        diameter_max = neo.get("estimated_diameter", {}).get("meters", {}).get("estimated_diameter_max", 0)
        is_hazardous = neo.get("is_potentially_hazardous_asteroid", False)
        
        # Get close approach velocity and miss distance
        approach_data = neo.get("close_approach_data", [{}])[0]
        velocity_kmh = float(approach_data.get("relative_velocity", {}).get("kilometers_per_hour", 0))
        miss_distance_km = float(approach_data.get("miss_distance", {}).get("kilometers", 0))
        
        asteroids.append({
            "name": name,
            "diameter_m": diameter_max,
            "is_hazardous": is_hazardous,
            "velocity_kmh": velocity_kmh,
            "miss_distance_km": miss_distance_km
        })
        
    return asteroids
