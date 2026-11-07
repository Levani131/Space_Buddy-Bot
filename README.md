# 🚀 SpaceBuddy - NASA Telegram Bot

SpaceBuddy is a Telegram bot that brings astronomy directly to your chat. It delivers NASA's Astronomy Picture of the Day (APOD) with high-definition imagery and tracks the largest near-Earth asteroids approaching our planet today.

---

## 📸 Bot Chat Preview

![SpaceBuddy Telegram Chat](screenshot.png)

*(Add your screenshot as `screenshot.png` in the project root)*

---

## ✨ Features

- **Astronomy Picture of the Day (`/apod`)**:
  - View **today's** APOD by default.
  - View any historical APOD from the **past year** by passing a date: `/apod YYYY-MM-DD` (e.g., `/apod 2026-10-30`).
  - Interactive **Inline Keyboard**: Quick buttons for `[📅 Yesterday]`, `[🎲 Random Date]`, and `[ℹ️ Custom Date Help]`.
  - Strict validation: dates must be in `YYYY-MM-DD` format, cannot be in the future, and must be within the past 365 days.
  - Resilient dual-endpoint routing and in-memory caching for sub-millisecond responses.
- **Planetary Defense Tracking (`/asteroids`)**:
  - Scans today's near-Earth objects (NEOs) from NASA's NeoWs feed.
  - Ranks and displays the top 5 largest approaching asteroids with size, speed, and hazard alerts.

---

## 🛠️ Setup Instructions (Steps 2–5)

Follow these steps to set up and run SpaceBuddy locally:

### Step 2: Create & Activate a Virtual Environment
Isolate the project's dependencies from your global Python installation:
```bash
# Create the virtual environment
python -m venv .venv

# Activate on Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Activate on macOS / Linux:
source .venv/bin/activate
```

### Step 3: Install Required Dependencies
Install the required packages:
```bash
pip install -r requirements.txt
```

### Step 4: Configure API Credentials (.env)
Create a `.env` file in the root folder to securely store your API tokens (refer to `.env.example`):
1. **Telegram Bot Token (`BOT_TOKEN`)**: 
   - Open Telegram and message [@BotFather](https://t.me/BotFather).
   - Use `/newbot` to create your bot, follow the prompts, and copy the HTTP API token provided.
2. **NASA API Key (`NASA_API_KEY`)**:
   - Register for a free API key at [api.nasa.gov](https://api.nasa.gov/).
   - *(Optional: If left blank, NASA's public `"DEMO_KEY"` is used as a fallback).*

Add them to your `.env` file:
```env
BOT_TOKEN=your_telegram_bot_token_here
NASA_API_KEY=your_nasa_api_key_here
```

> **Security Note:** The `.env` file is included in `.gitignore` and is **never** committed to the Git repository to protect your private credentials.

### Step 5: Run and Test the Bot
Start the bot with:
```bash
python bot.py
```
Open Telegram, search for your bot username, and test the commands:
- `/start` — Greets you by your first name.
- `/help` — Lists all available bot commands and date guidelines.
- `/apod` — Fetches today's Astronomy Picture of the Day.
- `/apod 2026-10-30` — Fetches the APOD for a specific date in the past year.
- `/asteroids` — Ranks and displays today's top 5 largest near-Earth objects.

---

## 🧪 Running Automated Tests

Run the test suite with `pytest`:
```bash
pytest -v
```

---

## 📁 Project Structure

```text
├── config.py              # Centralized environment configuration and validator
├── bot.py                 # Bot application builder, polling entry point & callback router
├── main.py                # Primary entrypoint alias & backward-compatible runner
├── nasa_service.py        # Root service shim for backwards compatibility
├── handlers/
│   ├── __init__.py        # Handlers exports
│   ├── commands.py        # /start, /help, /apod (with date picker), and /asteroids handlers
│   └── errors.py          # Global Telegram error handler
├── services/
│   ├── __init__.py        # Services exports
│   └── nasa.py            # NasaService class (caching, date validation, resilient APIs)
├── tests/
│   ├── conftest.py        # Shared test fixtures & mocks
│   ├── test_bot.py        # Application builder & shim tests
│   ├── test_config.py     # Configuration unit tests
│   ├── test_handlers.py   # Command & callback query unit tests
│   └── test_nasa_service.py # NASA API & date validation unit tests
├── requirements.txt       # List of Python dependencies
├── .env.example           # Template for required environment variables
├── .gitignore             # Ignores .env, .venv/, cache, and IDE files
├── PROJECT_BLUEPRINT.md   # Architectural design and specifications
├── TODO.md                # Project roadmap and technical analysis
└── README.md              # Setup guide and documentation
```
