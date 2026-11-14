"""Standalone SQLite diagnostic verification script for SpaceBuddy.

Can be run via:
    python -m scripts.verify_sqlite
or:
    python scripts/verify_sqlite.py
"""
import os
import sys
from typing import Any, List

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from database.db_manager import DatabaseManager


def format_ascii_table(headers: List[str], rows: List[List[Any]]) -> str:
    """Render headers and row data as a formatted ASCII border table."""
    str_rows = [[str(cell) if cell is not None else "NULL" for cell in row] for row in rows]
    col_widths = [len(h) for h in headers]

    for row in str_rows:
        for idx, cell in enumerate(row):
            if idx < len(col_widths):
                col_widths[idx] = max(col_widths[idx], len(cell))
            else:
                col_widths.append(len(cell))

    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"

    lines = [separator, header_line, separator]
    if not str_rows:
        empty_msg = "(No rows returned)"
        total_inner_width = sum(col_widths) + (len(col_widths) * 3) - 1
        lines.append(f"| {empty_msg.center(total_inner_width)} |")
    else:
        for row in str_rows:
            row_line = "| " + " | ".join(row[i].ljust(col_widths[i]) for i in range(len(col_widths))) + " |"
            lines.append(row_line)

    lines.append(separator)
    return "\n".join(lines)


def main() -> None:
    db_filename = "dev_space_buddy.db"
    print("=" * 70)
    print(f"🛰️  SPACEBUDDY SQLITE DIAGNOSTIC VERIFICATION TOOL")
    print(f"📁 Target Database: {db_filename}")
    print("=" * 70)

    # 1. Connect to dev_space_buddy.db using DatabaseManager
    print("\n[Step 1] Initializing DatabaseManager...")
    db = DatabaseManager(db_filename)
    print(f"✅ Successfully connected to '{db.db_path}' and initialized schema.")

    # 2. Query sqlite_master and PRAGMA table_info(...) for table schema
    print("\n[Step 2] Querying schema definitions and column specifications...")
    conn = db.get_connection()
    try:
        # Check sqlite_master
        master_rows = conn.execute(
            "SELECT type, name, tbl_name FROM sqlite_master WHERE type='table' AND name IN ('users', 'saved_apods') ORDER BY name;"
        ).fetchall()
        print(f"Found {len(master_rows)} core table(s) registered in sqlite_master:")
        for r in master_rows:
            print(f"  • {r['name']} ({r['type']})")

        # Column inspection for users and saved_apods
        for table_name in ["users", "saved_apods"]:
            print(f"\n--- PRAGMA table_info({table_name}) ---")
            cols = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
            headers = ["CID", "Column Name", "Type", "Not Null", "Default Value", "Primary Key"]
            table_rows = [
                [
                    col["cid"],
                    col["name"],
                    col["type"],
                    "YES" if col["notnull"] == 1 else "NO",
                    col["dflt_value"],
                    "YES" if col["pk"] >= 1 else "NO",
                ]
                for col in cols
            ]
            print(format_ascii_table(headers, table_rows))

        # 3. Verify and print active PRAGMA foreign_keys and journal_mode
        print("\n[Step 3] Verifying active connection PRAGMAs...")
        fk_val = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        journal_mode_val = conn.execute("PRAGMA journal_mode;").fetchone()[0]

        fk_status = "ON (1)" if fk_val == 1 else "OFF (0)"
        print(f"  • PRAGMA foreign_keys = {fk_status}")
        print(f"  • PRAGMA journal_mode = {journal_mode_val.upper()}")

        assert fk_val == 1, "Security violation: PRAGMA foreign_keys is not active!"
        assert journal_mode_val.lower() == "wal", f"Unexpected journal_mode: {journal_mode_val}"
        print("✅ PRAGMA configuration passed integrity checks (Foreign Keys ON, Journal Mode WAL).")

    finally:
        if db.db_path != ":memory:":
            conn.close()

    # 4. Insert 2 test users and 3 test APOD bookmarks, test duplicate, print community saves
    print("\n[Step 4] Executing test data operations and uniqueness verification...")

    # Reset any previous diagnostic run entries for deterministic execution
    with db._get_connection() as c:
        c.execute("DELETE FROM users WHERE user_id IN (101, 102);")

    # Insert 2 test users
    print("  -> Registering 2 test users:")
    db.register_user(user_id=101, username="astro_alex", first_name="Alex")
    db.register_user(user_id=102, username="cosmic_cassie", first_name="Cassie")
    print("     ✓ User 101: Alex (@astro_alex)")
    print("     ✓ User 102: Cassie (@cosmic_cassie)")

    # Insert 3 test APOD bookmarks
    print("  -> Inserting 3 distinct APOD bookmarks:")
    b1 = db.save_apod(
        user_id=101,
        apod_date="2026-11-01",
        title="Andromeda Galaxy Rising",
        media_url="https://apod.nasa.gov/apod/image/andromeda.jpg",
    )
    print(f"     ✓ Bookmark 1 (User 101, 2026-11-01): inserted = {b1}")
    assert b1 is True, "Error: Bookmark 1 insertion failed!"

    b2 = db.save_apod(
        user_id=101,
        apod_date="2026-11-02",
        title="Pillars of Creation",
        media_url="https://apod.nasa.gov/apod/image/pillars.jpg",
    )
    print(f"     ✓ Bookmark 2 (User 101, 2026-11-02): inserted = {b2}")
    assert b2 is True, "Error: Bookmark 2 insertion failed!"

    b3 = db.save_apod(
        user_id=102,
        apod_date="2026-11-03",
        title="Orion Nebula Mosaic",
        media_url="https://apod.nasa.gov/apod/image/orion.jpg",
    )
    print(f"     ✓ Bookmark 3 (User 102, 2026-11-03): inserted = {b3}")
    assert b3 is True, "Error: Bookmark 3 insertion failed!"

    # Deliberately attempt 1 duplicate bookmark
    print("  -> Deliberately testing duplicate insertion (User 101, 2026-11-01)...")
    duplicate_result = db.save_apod(
        user_id=101,
        apod_date="2026-11-01",
        title="Duplicate Andromeda",
        media_url="https://apod.nasa.gov/apod/image/andromeda_dup.jpg",
    )
    print(f"     ✓ Duplicate attempt result: {duplicate_result}")
    assert duplicate_result is False, "Error: duplicate APOD insertion did not return False!"
    print("✅ Duplicate constraint successfully verified: save_apod returned False.")

    # Fetch and format get_recent_community_saves()
    print("\n[Step 5] Fetching recent community saves (INNER JOIN):")
    community_saves = db.get_recent_community_saves(limit=10)
    headers = ["First Name", "Username", "APOD Date", "Title"]
    save_rows = [
        [
            save.get("first_name"),
            "@" + save["username"] if save.get("username") else "N/A",
            save.get("apod_date"),
            save.get("title"),
        ]
        for save in community_saves
    ]
    print(format_ascii_table(headers, save_rows))

    db.close()
    print("\n" + "=" * 70)
    print("🎉 ALL SQLITE DIAGNOSTIC CHECKS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
