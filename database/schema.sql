-- =====================================================================
-- SpaceBuddy Telegram Bot - Relational Database Schema (SQLite 3NF)
-- =====================================================================
-- Enforce Foreign Key Integrity and Write-Ahead Logging (WAL)
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ---------------------------------------------------------------------
-- Table: users
-- Description: Stores registered Telegram users and their profile details.
-- Normal Form: 3NF (Primary Key: user_id; all non-key attributes depend
--              directly on user_id with no transitive dependencies).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,            -- Telegram User ID (64-bit signed int)
    username    TEXT,                           -- Telegram @username (nullable)
    first_name  TEXT NOT NULL,                  -- User's first name
    joined_at   TEXT NOT NULL                   -- ISO-8601 UTC timestamp of initial registration
);

-- ---------------------------------------------------------------------
-- Table: saved_apods
-- Description: Stores user-bookmarked Astronomy Pictures of the Day.
-- Normal Form: 3NF (Primary Key: id; Foreign Key references users(user_id)
--              with ON DELETE CASCADE; composite UNIQUE on (user_id, apod_date)).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_apods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT, -- Surrogate Primary Key
    user_id     INTEGER NOT NULL,                  -- Reference to users(user_id)
    apod_date   TEXT NOT NULL,                     -- ISO-8601 date (YYYY-MM-DD, e.g. '2024-05-12')
    title       TEXT NOT NULL,                     -- APOD title
    media_url   TEXT NOT NULL,                     -- Direct HD/image or video URL
    saved_at    TEXT NOT NULL,                     -- ISO-8601 UTC timestamp when bookmarked
    
    -- Constraints:
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    UNIQUE (user_id, apod_date)                    -- Prevents duplicate bookmarks per user
);

-- ---------------------------------------------------------------------
-- Performance Indexes
-- ---------------------------------------------------------------------
-- Speed up community feed queries ordered by saved_at descending:
CREATE INDEX IF NOT EXISTS idx_saved_apods_saved_at 
    ON saved_apods (saved_at DESC);

-- Speed up user bookmark lookups ordered by apod_date descending:
CREATE INDEX IF NOT EXISTS idx_saved_apods_user_date 
    ON saved_apods (user_id, apod_date DESC);
