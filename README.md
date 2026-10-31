# 🚀 SpaceBuddy - NASA Telegram Bot

SpaceBuddy is a Telegram bot that brings astronomy directly to your chat. It delivers NASA's Astronomy Picture of the Day (APOD) with high-definition imagery and tracks the largest near-Earth asteroids approaching our planet today.

---

## 📸 Bot Chat Preview

![SpaceBuddy Telegram Chat](screenshot.png)

*(Add your screenshot as `screenshot.png` in the project root)*

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
Install the required packages (`python-telegram-bot`, `requests`, and `python-dotenv`):
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
- `/help` — Lists all available bot commands.
- `/apod` — Fetches today's Astronomy Picture of the Day with an image and description (or pass a date like `/apod 2026-10-25`).
- `/asteroids` — Ranks and displays today's top 5 largest near-Earth objects.

---

## 📁 Project Structure

```text
├── bot.py             # Main Telegram bot handlers and polling logic
├── main.py            # NASA API service integrations (APOD & Asteroids)
├── nasa_service.py    # Bridge module exposing NASA API service functions
├── requirements.txt   # List of Python dependencies
├── .env.example       # Template for required environment variables
├── .gitignore         # Ignores .env, .venv/, cache, and IDE files
├── README.md          # Setup guide and documentation
└── screenshot.png     # Screenshot of the bot running in Telegram
```

