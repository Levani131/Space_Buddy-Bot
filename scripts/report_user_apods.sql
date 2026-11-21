-- =============================================================================
-- SpaceBuddy Bot — User Favourites Report
-- Run against: space_buddy.db  (or dev_space_buddy.db)
-- Usage:  sqlite3 space_buddy.db < scripts/report_user_apods.sql
-- =============================================================================

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1.  SUMMARY — one row per user, total saves + date range
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    '=== USER SUMMARY ===' AS section;

SELECT
    u.user_id,
    u.first_name,
    COALESCE(u.username, '(no username)')    AS username,
    COUNT(s.id)                              AS total_favourites,
    MIN(s.apod_date)                         AS earliest_save,
    MAX(s.apod_date)                         AS latest_save,
    u.joined_at
FROM users u
LEFT JOIN saved_apods s ON u.user_id = s.user_id
GROUP BY u.user_id
ORDER BY total_favourites DESC, u.first_name ASC;


-- ─────────────────────────────────────────────────────────────────────────────
-- 2.  DETAIL — every bookmark with full metadata, newest first
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    '' AS '',
    '=== FAVOURITE APODS (DETAIL) ===' AS section;

SELECT
    u.first_name,
    COALESCE(u.username, '(no username)')    AS username,
    u.user_id,
    s.apod_date,
    s.title,
    s.saved_at,
    s.media_url
FROM users u
INNER JOIN saved_apods s ON u.user_id = s.user_id
ORDER BY s.saved_at DESC, u.first_name ASC;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3.  TOP APODs — most bookmarked across all users
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    '' AS '',
    '=== TOP APODs BY POPULARITY ===' AS section;

SELECT
    s.apod_date,
    s.title,
    COUNT(*)                                 AS times_saved,
    GROUP_CONCAT(u.first_name, ', ')         AS saved_by
FROM saved_apods s
INNER JOIN users u ON s.user_id = u.user_id
GROUP BY s.apod_date, s.title
ORDER BY times_saved DESC, s.apod_date DESC;


-- ─────────────────────────────────────────────────────────────────────────────
-- 4.  USERS WITH NO SAVES (registered but never bookmarked)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    '' AS '',
    '=== USERS WITH NO FAVOURITES ===' AS section;

SELECT
    u.user_id,
    u.first_name,
    COALESCE(u.username, '(no username)')    AS username,
    u.joined_at
FROM users u
LEFT JOIN saved_apods s ON u.user_id = s.user_id
WHERE s.id IS NULL
ORDER BY u.first_name ASC;
