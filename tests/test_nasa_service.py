"""Unit tests for NasaService (APOD, NeoWs, caching, validation)."""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from services.nasa import NasaService


def test_validate_date_valid_recent():
    """Valid YYYY-MM-DD date within the past year should pass."""
    service = NasaService(api_key="TEST_KEY")
    past_date = (date.today() - timedelta(days=30)).isoformat()
    is_valid, err = service.validate_date(past_date)
    assert is_valid is True
    assert err is None


def test_validate_date_valid_today():
    """Today's date should pass validation."""
    service = NasaService(api_key="TEST_KEY")
    today_str = date.today().isoformat()
    is_valid, err = service.validate_date(today_str)
    assert is_valid is True
    assert err is None


def test_validate_date_invalid_format():
    """Non YYYY-MM-DD formats should be rejected with helpful message."""
    service = NasaService(api_key="TEST_KEY")

    for bad_date in ["25-10-2026", "2026/10/25", "hello", "2026-99-99", "2026-02-31"]:
        is_valid, err = service.validate_date(bad_date)
        assert is_valid is False
        assert "YYYY-MM-DD" in err


def test_validate_date_older_than_one_year():
    """Dates older than 1 year (365 days ago) should be rejected."""
    service = NasaService(api_key="TEST_KEY")
    old_date = (date.today() - timedelta(days=370)).isoformat()
    is_valid, err = service.validate_date(old_date)
    assert is_valid is False
    assert "within the last year" in err.lower()


def test_validate_date_future():
    """Future dates should be rejected."""
    service = NasaService(api_key="TEST_KEY")
    future_date = (date.today() + timedelta(days=1)).isoformat()
    is_valid, err = service.validate_date(future_date)
    assert is_valid is False
    assert "future" in err.lower()


def test_apod_fetch_default_today(sample_apod_wp_json):
    """When no date is provided, service should fetch today's APOD."""
    service = NasaService(api_key="TEST_KEY")

    mock_resp = MagicMock()
    mock_resp.json.return_value = sample_apod_wp_json
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        result = service.fetch_apod(None)

    assert result is not None
    assert result["title"] == "Night on a Spooky Planet"


def test_apod_fetch_valid_past_date(sample_apod_legacy_json):
    """When a specific past date is provided, passes it to the API."""
    service = NasaService(api_key="TEST_KEY")

    mock_resp = MagicMock()
    mock_resp.json.return_value = sample_apod_legacy_json
    mock_resp.raise_for_status = MagicMock()

    with patch.object(service, "_fetch_from_apod_basic", return_value=None):
        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = service.fetch_apod("2026-10-25")
            assert result is not None
            assert result["title"] == "The Pillars of Creation"
            # Verify date parameter was passed in API query
            mock_get.assert_called_once()
            _, kwargs = mock_get.call_args
            assert kwargs["params"]["date"] == "2026-10-25"


def test_apod_caching(sample_apod_wp_json):
    """Subsequent requests for the same date must hit in-memory cache without HTTP calls."""
    service = NasaService(api_key="TEST_KEY")

    mock_resp = MagicMock()
    mock_resp.json.return_value = sample_apod_wp_json
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp) as mock_get:
        # First call hits mock HTTP
        res1 = service.fetch_apod("2026-10-31")
        assert mock_get.call_count == 1

        # Second call must come from cache
        res2 = service.fetch_apod("2026-10-31")
        assert mock_get.call_count == 1
        assert res1 == res2


def test_apod_fallback_to_archive_redirect():
    """When legacy API returns scraper bug, falls back to archive redirect."""
    service = NasaService(api_key="TEST_KEY")
    fake_archive = {
        "title": "R3 PanSTARRS: An Orion Comet",
        "explanation": "Comet in Orion.",
        "media_type": "image",
        "url": "https://assets.science.nasa.gov/apod/image.jpg",
        "hdurl": "https://assets.science.nasa.gov/apod/image.jpg",
        "date": "2026-05-15",
    }

    with patch.object(service, "_fetch_from_apod_basic", return_value=None):
        with patch.object(service, "safe_get", return_value={"title": "NASA Science", "url": "nasa-logo.png"}):
            with patch.object(service, "_fetch_from_archive_redirect", return_value=fake_archive):
                result = service.fetch_apod("2026-05-15")

    assert result is not None
    assert result["title"] == "R3 PanSTARRS: An Orion Comet"


def test_fetch_today_asteroids_parsing(sample_neows_json):
    """Test parsing NeoWs JSON payload into structured asteroid records."""
    service = NasaService(api_key="TEST_KEY")

    mock_resp = MagicMock()
    mock_resp.json.return_value = sample_neows_json
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        asteroids = service.fetch_today_asteroids()

    assert len(asteroids) == 3
    a1 = asteroids[0]
    assert a1["name"] == "Asteroid Alpha"
    assert a1["diameter_m"] == 450.5
    assert a1["is_hazardous"] is True
    assert a1["velocity_kmh"] == 72000.0
    assert a1["miss_distance_km"] == 1500000.0


def test_fetch_today_asteroids_empty():
    """Handle empty or failed response from NeoWs safely."""
    service = NasaService(api_key="TEST_KEY")

    with patch.object(service, "safe_get", return_value=None):
        asteroids = service.fetch_today_asteroids()

    assert asteroids == []
