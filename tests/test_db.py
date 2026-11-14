"""In-memory SQLite unit tests for DatabaseManager using Python unittest."""
import os
import sqlite3
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Test suite running DatabaseManager entirely in RAM (:memory:)."""

    def setUp(self) -> None:
        """Initialize a fresh in-memory DatabaseManager for each test."""
        self.db = DatabaseManager(":memory:")

    def tearDown(self) -> None:
        """Close the in-memory database connection after each test."""
        self.db.close()

    def test_register_and_update_user(self) -> None:
        """Verify registering a user and updating their username via ON CONFLICT(user_id) DO UPDATE."""
        user_id = 1001
        initial_username = "stargazer_alex"
        updated_username = "alex_cosmic"
        first_name = "Alex"

        # 1. Initial user registration
        self.db.register_user(user_id=user_id, username=initial_username, first_name=first_name)
        user = self.db.get_user(user_id)
        self.assertIsNotNone(user, "User record should exist after initial registration.")
        self.assertEqual(user["user_id"], user_id)
        self.assertEqual(user["username"], initial_username)
        self.assertEqual(user["first_name"], first_name)
        original_joined_at = user["joined_at"]

        # 2. Update user's username on conflict
        self.db.register_user(user_id=user_id, username=updated_username, first_name="Alexander")
        updated_user = self.db.get_user(user_id)
        self.assertIsNotNone(updated_user, "User record should still exist after update.")
        self.assertEqual(updated_user["user_id"], user_id)
        self.assertEqual(updated_user["username"], updated_username)
        self.assertEqual(updated_user["first_name"], "Alexander")
        self.assertEqual(
            updated_user["joined_at"],
            original_joined_at,
            "Original joined_at timestamp should be preserved on conflict update.",
        )

    def test_save_apod_and_block_duplicate(self) -> None:
        """Verify first save returns True, duplicate returns False, and count remains 1."""
        user_id = 2001
        apod_date = "2026-11-01"
        title = "Pillars of Creation"
        media_url = "https://apod.nasa.gov/apod/image/pillars.jpg"

        # Register user first to satisfy foreign key constraint
        self.db.register_user(user_id=user_id, username="neil_a", first_name="Neil")

        # 1. First save must return True
        first_save_result = self.db.save_apod(
            user_id=user_id,
            apod_date=apod_date,
            title=title,
            media_url=media_url,
        )
        self.assertTrue(first_save_result, "First APOD save should return True.")

        # 2. Saving the exact same (user_id, apod_date) second time must return False
        duplicate_save_result = self.db.save_apod(
            user_id=user_id,
            apod_date=apod_date,
            title="Duplicate Title Attempt",
            media_url="https://apod.nasa.gov/apod/image/different.jpg",
        )
        self.assertFalse(duplicate_save_result, "Duplicate APOD save must return False.")

        # 3. Total saved count for user must remain 1
        favorites = self.db.get_user_favorites(user_id=user_id)
        self.assertEqual(len(favorites), 1, "Total saved APODs count must remain exactly 1.")
        self.assertEqual(favorites[0]["apod_date"], apod_date)
        self.assertEqual(favorites[0]["title"], title)

    def test_foreign_key_blocks_unregistered_user(self) -> None:
        """Verify saving an APOD for a non-existent user_id raises sqlite3.IntegrityError."""
        unregistered_user_id = 99999
        apod_date = "2026-11-02"
        title = "Orion Nebula"
        media_url = "https://apod.nasa.gov/apod/image/orion.jpg"

        # Ensure user is NOT registered
        self.assertIsNone(self.db.get_user(unregistered_user_id))

        # Attempting to save APOD for unregistered user must trigger foreign key failure
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.save_apod(
                user_id=unregistered_user_id,
                apod_date=apod_date,
                title=title,
                media_url=media_url,
            )

    def test_delete_favorite(self) -> None:
        """Verify deleting an existing bookmark returns True and deleting non-existent returns False."""
        user_id = 3001
        apod_date = "2026-11-03"

        self.db.register_user(user_id=user_id, username="sally_ride", first_name="Sally")
        self.db.save_apod(
            user_id=user_id,
            apod_date=apod_date,
            title="Andromeda Galaxy",
            media_url="https://apod.nasa.gov/apod/image/andromeda.jpg",
        )
        self.assertEqual(len(self.db.get_user_favorites(user_id)), 1)

        # 1. Delete existing bookmark -> True
        deleted_existing = self.db.delete_favorite(user_id=user_id, apod_date=apod_date)
        self.assertTrue(deleted_existing, "Deleting an existing bookmark must return True.")
        self.assertEqual(len(self.db.get_user_favorites(user_id)), 0)

        # 2. Delete non-existent bookmark -> False
        deleted_nonexistent = self.db.delete_favorite(user_id=user_id, apod_date=apod_date)
        self.assertFalse(deleted_nonexistent, "Deleting a non-existent bookmark must return False.")

    def test_inner_join_community_saves(self) -> None:
        """Verify get_recent_community_saves() joins user details with saved_apods data."""
        # Setup 2 users
        user1_id = 4001
        user2_id = 4002
        self.db.register_user(user_id=user1_id, username="hubble_ed", first_name="Edwin")
        self.db.register_user(user_id=user2_id, username="carl_sagan", first_name="Carl")

        # Save APODs
        self.db.save_apod(
            user_id=user1_id,
            apod_date="2026-10-30",
            title="Sombrero Galaxy",
            media_url="https://apod.nasa.gov/apod/image/sombrero.jpg",
        )
        self.db.save_apod(
            user_id=user2_id,
            apod_date="2026-10-31",
            title="Spooky Dark Nebula",
            media_url="https://apod.nasa.gov/apod/image/spooky.jpg",
        )

        community_saves = self.db.get_recent_community_saves(limit=10)
        self.assertGreaterEqual(len(community_saves), 2)

        # Verify columns exist on returned dictionary rows
        for save in community_saves:
            self.assertIn("first_name", save)
            self.assertIn("username", save)
            self.assertIn("apod_date", save)
            self.assertIn("title", save)

        # Find specific user entries and verify matched join values
        edwin_save = next((s for s in community_saves if s["apod_date"] == "2026-10-30"), None)
        self.assertIsNotNone(edwin_save)
        self.assertEqual(edwin_save["first_name"], "Edwin")
        self.assertEqual(edwin_save["username"], "hubble_ed")
        self.assertEqual(edwin_save["title"], "Sombrero Galaxy")

        carl_save = next((s for s in community_saves if s["apod_date"] == "2026-10-31"), None)
        self.assertIsNotNone(carl_save)
        self.assertEqual(carl_save["first_name"], "Carl")
        self.assertEqual(carl_save["username"], "carl_sagan")
        self.assertEqual(carl_save["title"], "Spooky Dark Nebula")


if __name__ == "__main__":
    unittest.main()
