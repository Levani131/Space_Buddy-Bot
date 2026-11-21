"""Print a formatted user-favourites report from space_buddy.db."""
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "space_buddy.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON;")


def hr(label):
    print()
    print("=" * 72)
    print(f"  {label}")
    print("=" * 72)


# ── 1. SUMMARY ──────────────────────────────────────────────────────────────
hr("1. USER SUMMARY")
rows = conn.execute(
    """
    SELECT
        u.user_id,
        u.first_name,
        COALESCE(u.username, '') AS username,
        COUNT(s.id)              AS total_favourites,
        MIN(s.apod_date)         AS earliest_save,
        MAX(s.apod_date)         AS latest_save
    FROM users u
    LEFT JOIN saved_apods s ON u.user_id = s.user_id
    GROUP BY u.user_id
    ORDER BY total_favourites DESC, u.first_name ASC
    """
).fetchall()
print(f"  {'user_id':<14} {'first_name':<12} {'username':<18} {'saves':>6}  {'earliest':<12} {'latest'}")
print(f"  {'-'*14} {'-'*12} {'-'*18} {'-'*6}  {'-'*12} {'-'*12}")
for r in rows:
    uname = r["username"] or "(no username)"
    print(
        f"  {r['user_id']:<14} {r['first_name']:<12} {uname:<18} "
        f"{r['total_favourites']:>6}  "
        f"{str(r['earliest_save'] or '-'):<12} {str(r['latest_save'] or '-')}"
    )

# ── 2. DETAIL ───────────────────────────────────────────────────────────────
hr("2. FAVOURITE APODs — DETAIL (newest first)")
rows = conn.execute(
    """
    SELECT
        u.first_name,
        COALESCE(u.username, '') AS username,
        s.apod_date,
        s.title,
        s.saved_at
    FROM users u
    INNER JOIN saved_apods s ON u.user_id = s.user_id
    ORDER BY s.saved_at DESC
    """
).fetchall()
print(f"  {'first_name':<10} {'username':<18} {'apod_date':<12} {'saved_at':<20}  title")
print(f"  {'-'*10} {'-'*18} {'-'*12} {'-'*20}  {'-'*35}")
for r in rows:
    ts = r["saved_at"][:19] if r["saved_at"] else "-"
    uname = r["username"] or "(no username)"
    print(f"  {r['first_name']:<10} {uname:<18} {r['apod_date']:<12} {ts:<20}  {r['title']}")

# ── 3. TOP APODs ─────────────────────────────────────────────────────────────
hr("3. TOP APODs BY POPULARITY")
rows = conn.execute(
    """
    SELECT
        s.apod_date,
        s.title,
        COUNT(*)                        AS times_saved,
        GROUP_CONCAT(u.first_name, ', ') AS saved_by
    FROM saved_apods s
    INNER JOIN users u ON s.user_id = u.user_id
    GROUP BY s.apod_date, s.title
    ORDER BY times_saved DESC, s.apod_date DESC
    """
).fetchall()
print(f"  {'apod_date':<12} {'saves':>5}  {'saved_by':<24} title")
print(f"  {'-'*12} {'-'*5}  {'-'*24} {'-'*35}")
for r in rows:
    print(f"  {r['apod_date']:<12} {r['times_saved']:>5}  {r['saved_by']:<24} {r['title']}")

# ── 4. USERS WITH NO SAVES ───────────────────────────────────────────────────
hr("4. USERS WITH NO FAVOURITES")
rows = conn.execute(
    """
    SELECT u.user_id, u.first_name, COALESCE(u.username, '') AS username
    FROM users u
    LEFT JOIN saved_apods s ON u.user_id = s.user_id
    WHERE s.id IS NULL
    ORDER BY u.first_name ASC
    """
).fetchall()
if rows:
    for r in rows:
        uname = r["username"] or "(no username)"
        print(f"  user_id={r['user_id']}  name={r['first_name']}  username={uname}")
else:
    print("  (all registered users have at least one favourite)")

print()
conn.close()
