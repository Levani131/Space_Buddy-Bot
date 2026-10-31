# 📋 SpaceBuddy Project Analysis & TODO Roadmap

> **Audit, Technical Analysis, and Action Plan for SpaceBuddy Telegram Bot**  
> **Date:** October 2026  
> **Status:** Phase 1 & Phase 2 Complete | Phase 3 (Testing Suite) Complete (23/23 Passing)

---

## 🔍 1. Current Project Health & Analysis

### What Is Currently Working Well ✅
- **Dual-Endpoint Fallback:** `fetch_apod` seamlessly mitigates NASA's broken scraper (`"NASA Science"` logo issue) and API 500 crashes by routing to `science.nasa.gov/wp-json/wp/v2/apod-basic`.
- **In-Memory APOD Caching:** High-speed cache prevents duplicate network requests for the same day (sub-millisecond responses).
- **Date Input Validation:** Strictly validates `YYYY-MM-DD` and limits bounds (between June 16, 1995 and today).
- **Non-blocking Event Loop:** `asyncio.to_thread` ensures synchronous HTTP calls do not block Telegram bot polling.
- **Visual Feedback:** Chat actions (`upload_photo`, `typing`) keep user informed while data loads.
- **Caption Truncation & Formatting:** Strict handling of Telegram's 1024-character caption limit with Markdown entity fallback.
- **Credential Isolation:** `.env` is properly ignored by Git, with an onboarding `.env.example` template provided.
- **Comprehensive Test Suite:** 23 passing unit and integration tests covering config, services, caching, and handlers.

---

## 🎯 2. Identified Technical Debt & Gaps

| Area | Current Status | Risk / Limitation | Priority |
| :--- | :--- | :--- | :--- |
| **HTTP Client Architecture** | Synchronous `requests` wrapped in threads | Higher memory/thread footprint under high concurrency | **Medium** |
| **User Interactivity** | Plain text commands only | Opportunity for inline buttons (e.g. "Random", "Next") | **Medium** |
| **Deployment Readiness** | Manual terminal polling | No process supervisor or containerization for 24/7 uptime | **Medium** |

---

## 📌 3. Prioritized Task Checklist

### Phase 1: Core Stabilisation & Safety (Completed ✅)
- [x] Fix missing `python-telegram-bot` module in `.venv`
- [x] Connect `bot.py` imports with `main.py` via `nasa_service.py`
- [x] Fix NASA APOD scraper bug (`"NASA Science"` logo bug)
- [x] Handle Telegram 1024-character caption limit
- [x] Add Markdown parsing error fallback
- [x] Configure `.gitignore` to prevent secret leakage
- [x] Write project documentation ([README.md](README.md) & [PROJECT_BLUEPRINT.md](PROJECT_BLUEPRINT.md))
- [x] **Input Validation:** Add ISO date validator (`YYYY-MM-DD`) for `/apod` argument
- [x] **Chat Action Indicators:** Add `context.bot.send_chat_action(chat_id, "upload_photo")` while loading media

### Phase 2: Performance & Caching (Completed ✅)
- [x] **In-Memory / TTL Cache:** Implement caching for daily APOD (sub-millisecond repeat queries)
- [x] **Modular Architecture Refactoring:** Decoupled into `config.py`, `services/`, `handlers/`, with backwards compatibility shims
- [ ] **Switch to Native Async HTTP (`httpx`):** Replace synchronous `requests` with async `httpx.AsyncClient`
- [ ] **Robust Asteroid Filtering:** Allow user to filter asteroids by minimum diameter or hazard only

### Phase 3: Testing & Quality Assurance (Completed ✅)
- [x] **Unit Tests:** Set up `pytest` and `pytest-asyncio`
- [x] **API Mocking:** Create mock fixtures for NASA APOD and NeoWs responses (testing 200, 400, 500, and malformed JSON)
- [x] **Error Path Coverage:** Test behavior when NASA API is unreachable or rate-limited
- [x] **Handler Tests:** Verify command responses, caption truncation, and error notifications (23 passing tests)

### Phase 4: Enhanced User Experience (UI/UX)
- [ ] **Interactive Inline Buttons:**
  - `[📅 Random Date]`
  - `[⬅️ Yesterday]`
  - `[🔍 HD Image Link]`
- [ ] **Subscription & Broadcast (`JobQueue`):**
  - Allow users to subscribe via `/subscribe`
  - Daily automatic broadcast of APOD at 09:00 UTC
- [ ] **Stretch Goal — Mars Rover Photos (`/mars`):**
  - Fetch photos from Curiosity or Perseverance rovers

### Phase 5: Production Deployment & Monitoring
- [ ] **Containerization:** Create `Dockerfile` and `docker-compose.yml`
- [ ] **Health Monitoring:** Add a simple heartbeat/ping command (`/ping`)
- [ ] **Structured Logging:** Direct logs to a rotating log file (`logs/bot.log`) with log timestamps and user IDs
