"""Unit tests for NasaService (APOD, NeoWs, caching, validation)."""
from unittest.mock import MagicMock, patch
from services.nasa import NasaService


def test_validate_date_valid():
    """Valid YYYY-MM-DD date within archive range should pass."""
    service = NasaService(api_key="TEST_KEY")
    is_valid, err = service.validate_date("2026-10-25")
    assert is_valid is True
    assert err is None


def test_validate_date_invalid_format():
    """Non YYYY-MM-DD formats should be rejected with helpful message."""
    service = NasaService(api_key="TEST_KEY")

    for bad_date in ["25-10-2026", "2026/10/25", "hello", "2026-99-99"]:
        is_valid, err = service.validate_date(bad_date)
        assert is_valid is False
        assert "YYYY-MM-DD" in err


def test_validate_date_pre_archive():
    """Dates prior to June 16, 1995 should be rejected."""
    service = NasaService(api_key="TEST_KEY")
    is_valid, err = service.validate_date("1995-06-15")
    assert is_valid is False
    assert "1995-06-16" in err


def test_validate_date_future():
    """Future dates should be rejected."""
    service = NasaService(api_key="TEST_KEY")
    is_valid, err = service.validate_date("2099-01-01")
    assert is_valid is False
    assert "future" in err.lower()


def test_apod_fetch_from_wp_json(sample_apod_wp_json):
    """Test successful fetching from science.nasa.gov WP-JSON endpoint."""
    service = NasaService(api_key="TEST_KEY")

    mock_resp = MagicMock()
    mock_resp.json.return_value = sample_apod_wp_json
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        result = service.fetch_apod("2026-10-31")

    assert result is not None
    assert result["title"] == "Night on a Spooky Planet"
    # Verify HTML tags were stripped from explanation
    assert "<strong>" not in result["explanation"]
    assert "What spooky planet is this?" in result["explanation"]
    # Verify high-res image URL was selected
    assert result["url"] == "https://assets.science.nasa.gov/apod/Hverir_Vetter_1300.jpg"


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


def test_apod_fallback_to_legacy(sample_apod_legacy_json):
    """When WP-JSON fails, service must fall back to api.nasa.gov."""
    service = NasaService(api_key="TEST_KEY")

    def side_effect(url, *args, **kwargs):
        mock_r = MagicMock()
        if "science.nasa.gov" in url:
            # Simulate WP-JSON missing or error
            mock_r.raise_for_status.side_effect = Exception("404 Not Found")
        else:
            # Legacy api.nasa.gov succeeds
            mock_r.json.return_value = sample_apod_legacy_json
            mock_r.raise_for_status = MagicMock()
        return mock_r

    with patch("requests.get", side_effect=side_effect):
        result = service.fetch_apod("2026-10-25")

    assert result is not None
    assert result["title"] == "The Pillars of Creation"
    assert result["url"] == "https://apod.nasa.gov/apod/image/pillars.jpg"


def test_apod_legacy_scraper_bug_detected(sample_apod_legacy_json):
    """If legacy API returns 'NASA Science' with the logo PNG, it should be rejected."""
    service = NasaService(api_key="TEST_KEY")
    buggy_legacy = {
        "title": "NASA Science",
        "url": "https://science.nasa.gov/wp-content/themes/nasa-child/assets/images/nasa-logo@2x.png",
        "explanation": "Buggy scraper output",
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = buggy_legacy
    mock_resp.raise_for_status = MagicMock()

    with patch.object(service, "_fetch_from_apod_basic", return_value=None):
        with patch("requests.get", return_value=mock_resp):
            result = service.fetch_apod()

    # The buggy data should be rejected
    assert result is None


def test_fetch_today_asteroids_parsing(sample_neows_json):
    """Test parsing NeoWs JSON payload into structured asteroid records."""
    service = NasaService(api_key="TEST_KEY")

    mock_resp = MagicMock()
    mock_resp.json.return_value = sample_neows_json
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        asteroids = service.fetch_today_asteroids()

    assert len(asteroids) == 3
    # Check first asteroid
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
