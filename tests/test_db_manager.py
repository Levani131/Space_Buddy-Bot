"""Unit tests for DatabaseManager."""
import sqlite3
import pytest

from database.db_manager import DatabaseManager


def test_default_db_path(tmp_path, monkeypatch):
    """Verify default db_path is 'space_buddy.db'."""
    db = DatabaseManager(":memory:")
    assert db.db_path == ":memory:"
    db.close()

    monkeypatch.chdir(tmp_path)
    default_db = DatabaseManager()
    try:
        assert default_db.db_path == "space_buddy.db"
    finally:
        default_db.close()


def test_in_memory_persistence():
    """Verify :memory: maintains a single persistent connection across get_connection calls."""
    db = DatabaseManager(":memory:")
    conn1 = db.get_connection()
    conn2 = db.get_connection()

    assert conn1 is conn2

    # Register user and ensure it persists across calls
    db.register_user(user_id=1, username="stargazer", first_name="Alex")
    user = db.get_user(1)
    assert user is not None
    assert user["username"] == "stargazer"
    assert user["first_name"] == "Alex"
    db.close()


def test_row_factory_and_pragmas_memory():
    """Verify row_factory and PRAGMA settings on :memory: connection."""
    db = DatabaseManager(":memory:")
    conn = db.get_connection()

    assert conn.row_factory == sqlite3.Row

    fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk == 1

    db.close()


def test_row_factory_and_pragmas_file(tmp_path):
    """Verify row_factory, foreign_keys, and journal_mode=WAL on file database."""
    test_db_path = str(tmp_path / "test_space.db")
    db = DatabaseManager(test_db_path)

    conn = db.get_connection()
    try:
        assert conn.row_factory == sqlite3.Row

        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk == 1

        journal = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert journal.lower() == "wal"
    finally:
        conn.close()
        db.close()


def test_tables_schema_created():
    """Verify users and saved_apods tables exist with the required columns."""
    db = DatabaseManager(":memory:")
    conn = db.get_connection()

    # Check tables exist
    tables = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    assert "users" in tables
    assert "saved_apods" in tables

    # Check columns in users
    users_cols = {row["name"]: row for row in conn.execute("PRAGMA table_info(users);").fetchall()}
    assert "user_id" in users_cols
    assert users_cols["user_id"]["pk"] == 1
    assert "username" in users_cols
    assert "first_name" in users_cols
    assert users_cols["first_name"]["notnull"] == 1
    assert "joined_at" in users_cols
    assert users_cols["joined_at"]["notnull"] == 1

    # Check columns in saved_apods
    apods_cols = {row["name"]: row for row in conn.execute("PRAGMA table_info(saved_apods);").fetchall()}
    assert "id" in apods_cols
    assert apods_cols["id"]["pk"] == 1
    assert "user_id" in apods_cols
    assert apods_cols["user_id"]["notnull"] == 1
    assert "apod_date" in apods_cols
    assert apods_cols["apod_date"]["notnull"] == 1
    assert "title" in apods_cols
    assert apods_cols["title"]["notnull"] == 1
    assert "media_url" in apods_cols
    assert apods_cols["media_url"]["notnull"] == 1
    assert "saved_at" in apods_cols
    assert apods_cols["saved_at"]["notnull"] == 1

    db.close()


def test_foreign_key_constraint():
    """Verify that saving an APOD for a non-existent user raises IntegrityError."""
    db = DatabaseManager(":memory:")
    conn = db.get_connection()

    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute(
                """
                INSERT INTO saved_apods (user_id, apod_date, title, media_url, saved_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (99999, "2026-11-01", "Nonexistent User APOD", "https://example.com/test.jpg", "2026-11-07T12:00:00"),
            )

    db.close()


def test_foreign_key_cascade_delete():
    """Verify that deleting a user cascades and deletes all associated saved_apods."""
    db = DatabaseManager(":memory:")
    conn = db.get_connection()

    db.register_user(user_id=42, username="cascade_user", first_name="Cascade")
    db.save_apod(user_id=42, apod_date="2026-11-01", title="Photo 1", media_url="https://example.com/1.jpg")
    db.save_apod(user_id=42, apod_date="2026-11-02", title="Photo 2", media_url="https://example.com/2.jpg")

    assert len(db.get_user_favorites(42)) == 2

    # Delete the user
    with conn:
        conn.execute("DELETE FROM users WHERE user_id = ?;", (42,))

    # Associated apods should be automatically removed due to ON DELETE CASCADE
    assert len(db.get_user_favorites(42)) == 0

    apods_count = conn.execute("SELECT COUNT(*) FROM saved_apods WHERE user_id = ?;", (42,)).fetchone()[0]
    assert apods_count == 0

    db.close()


def test_composite_unique_constraint():
    """Verify that inserting duplicate (user_id, apod_date) raises IntegrityError when using raw INSERT."""
    db = DatabaseManager(":memory:")
    conn = db.get_connection()

    db.register_user(user_id=10, username="duplicate_tester", first_name="Tester")

    with conn:
        conn.execute(
            """
            INSERT INTO saved_apods (user_id, apod_date, title, media_url, saved_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (10, "2026-11-07", "First Insert", "https://example.com/apod1.jpg", "2026-11-07T10:00:00"),
        )

    # Attempting to insert another record with identical (user_id, apod_date) must fail
    with pytest.raises(sqlite3.IntegrityError):
        with conn:
            conn.execute(
                """
                INSERT INTO saved_apods (user_id, apod_date, title, media_url, saved_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (10, "2026-11-07", "Second Insert", "https://example.com/apod2.jpg", "2026-11-07T10:05:00"),
            )

    db.close()


def test_register_user_upsert():
    """Verify register_user creates new user and updates existing username without crashing."""
    db = DatabaseManager(":memory:")

    # Initial registration
    db.register_user(user_id=101, username="initial_handle", first_name="Hubble")
    user = db.get_user(101)
    assert user["username"] == "initial_handle"
    assert user["first_name"] == "Hubble"
    original_joined_at = user["joined_at"]

    # Update username on existing user
    db.register_user(user_id=101, username="updated_handle", first_name="Edwin Hubble")
    user_updated = db.get_user(101)
    assert user_updated["username"] == "updated_handle"
    assert user_updated["first_name"] == "Edwin Hubble"
    assert user_updated["joined_at"] == original_joined_at  # Preserves initial joined_at

    # Register user with None username
    db.register_user(user_id=102, username=None, first_name="Anonymous")
    user_anon = db.get_user(102)
    assert user_anon["username"] is None
    assert user_anon["first_name"] == "Anonymous"

    db.close()


def test_save_apod_insert_or_ignore():
    """Verify save_apod returns True on insert and False on duplicate."""
    db = DatabaseManager(":memory:")
    db.register_user(user_id=200, username="space_fan", first_name="Elena")

    # Initial save
    res1 = db.save_apod(
        user_id=200,
        apod_date="2026-10-31",
        title="Spooky Planet",
        media_url="https://assets.science.nasa.gov/apod/spooky.jpg",
    )
    assert res1 is True

    # Duplicate save with same user_id and apod_date
    res2 = db.save_apod(
        user_id=200,
        apod_date="2026-10-31",
        title="Spooky Planet Duplicate",
        media_url="https://assets.science.nasa.gov/apod/spooky.jpg",
    )
    assert res2 is False

    # Check only one row was saved
    favs = db.get_user_favorites(200)
    assert len(favs) == 1
    assert favs[0]["title"] == "Spooky Planet"

    db.close()


def test_get_user_favorites():
    """Verify get_user_favorites returns list of dicts ordered by apod_date DESC with limit."""
    db = DatabaseManager(":memory:")
    db.register_user(user_id=300, username="astro_geek", first_name="Neil")

    db.save_apod(300, "2026-01-01", "New Year APOD", "https://example.com/1.jpg")
    db.save_apod(300, "2026-05-15", "Mid Year APOD", "https://example.com/2.jpg")
    db.save_apod(300, "2026-03-10", "Spring APOD", "https://example.com/3.jpg")

    favorites = db.get_user_favorites(user_id=300, limit=10)
    assert isinstance(favorites, list)
    assert len(favorites) == 3
    assert all(isinstance(item, dict) for item in favorites)

    # Check ordering: apod_date DESC
    dates = [f["apod_date"] for f in favorites]
    assert dates == ["2026-05-15", "2026-03-10", "2026-01-01"]

    # Check limit parameter
    limited_favs = db.get_user_favorites(user_id=300, limit=2)
    assert len(limited_favs) == 2
    assert limited_favs[0]["apod_date"] == "2026-05-15"
    assert limited_favs[1]["apod_date"] == "2026-03-10"

    db.close()


def test_delete_favorite():
    """Verify delete_favorite removes bookmark and returns True or False."""
    db = DatabaseManager(":memory:")
    db.register_user(user_id=400, username="star_gazer", first_name="Sally")

    db.save_apod(400, "2026-07-20", "Apollo Anniversary", "https://example.com/apollo.jpg")
    assert len(db.get_user_favorites(400)) == 1

    # Delete existing bookmark
    deleted = db.delete_favorite(400, "2026-07-20")
    assert deleted is True
    assert len(db.get_user_favorites(400)) == 0

    # Delete non-existent bookmark
    deleted_again = db.delete_favorite(400, "2026-07-20")
    assert deleted_again is False

    db.close()


def test_get_recent_community_saves():
    """Verify get_recent_community_saves uses INNER JOIN between saved_apods and users."""
    db = DatabaseManager(":memory:")

    db.register_user(user_id=501, username="user_one", first_name="Alice")
    db.register_user(user_id=502, username="user_two", first_name="Bob")
    db.register_user(user_id=503, username=None, first_name="Charlie")

    db.save_apod(501, "2026-10-01", "Alice APOD 1", "https://example.com/a1.jpg")
    db.save_apod(502, "2026-10-02", "Bob APOD 1", "https://example.com/b1.jpg")
    db.save_apod(503, "2026-10-03", "Charlie APOD 1", "https://example.com/c1.jpg")
    db.save_apod(501, "2026-10-04", "Alice APOD 2", "https://example.com/a2.jpg")

    community_saves = db.get_recent_community_saves(limit=3)
    assert isinstance(community_saves, list)
    assert len(community_saves) == 3
    assert all(isinstance(entry, dict) for entry in community_saves)

    # Check fields present
    first_entry = community_saves[0]
    assert "first_name" in first_entry
    assert "username" in first_entry
    assert "apod_date" in first_entry
    assert "title" in first_entry

    # The most recent save is Alice's second APOD
    assert first_entry["first_name"] == "Alice"
    assert first_entry["username"] == "user_one"
    assert first_entry["apod_date"] == "2026-10-04"
    assert first_entry["title"] == "Alice APOD 2"

    db.close()


def test_context_manager_usage():
    """Verify DatabaseManager works as a context manager."""
    with DatabaseManager(":memory:") as db:
        db.register_user(user_id=1, username="ada_dev", first_name="Ada")
        assert db.get_user(1) is not None
    assert db._connection is None
