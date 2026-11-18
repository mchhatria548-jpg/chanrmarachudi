# Chandramara Chudi Telegram Mock Test Bot

## Files
- bot.py: Telegram bot source
- questions.json: 50 Odia MCQs and answer key
- requirements.txt: Python dependency

## Run locally
1. Install Python 3.10+
2. `pip install -r requirements.txt`
3. Set your bot token as environment variable `BOT_TOKEN` (never share it publicly)
4. Run `python bot.py`

Linux/macOS:
`export BOT_TOKEN="YOUR_TOKEN"`
`python bot.py`

Windows PowerShell:
`$env:BOT_TOKEN="YOUR_TOKEN"`
`python bot.py`

## Commands
/start – start/restart the test
/result – show own score
/leaderboard – top 20 completed attempts
/help – command list

Scoring: +1 correct, -0.25 wrong, 0 unanswered. 45-minute limit.
Note: This starter bot stores data in SQLite. On free hosting, local disk may be temporary or reset on redeploy/restart; use persistent storage or a managed database if you need a durable shared leaderboard. Do not expose BOT_TOKEN.
