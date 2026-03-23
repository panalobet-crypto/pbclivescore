# 🏏 Cricket Score Telegram Bot

Pushes live cricket score updates to a Telegram channel/group using AllSportsAPI v2.

## Features

| Event | Trigger |
|-------|---------|
| 🏏 Match started | When `event_live` flips to `"1"` |
| 📊 Score update | Every completed **over** |
| 💥 Wicket alert | Each wicket fallen |
| 🏁 Final result | When `event_status` = Finished |

Adaptive polling: **60s** during live matches, **5min** when idle.

---

## Quick Start

### 1. Get your credentials

- **AllSportsAPI key**: https://allsportsapi.com → Dashboard → API Key
- **Telegram bot token**: Message `@BotFather` → `/newbot`
- **Chat ID**: Add bot to channel/group, then use `@userinfobot` or the Telegram API to get the ID

### 2. Find your league IDs (run locally once)

```bash
pip install httpx
CRICKET_API_KEY=your_key python find_leagues.py ipl
CRICKET_API_KEY=your_key python find_leagues.py bangladesh
```

Copy the IDs you want into `WATCHED_LEAGUE_IDS`.

### 3. Deploy to Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and init
railway login
railway init        # name it: cricket-score-bot

# Set environment variables
railway variables set CRICKET_API_KEY=xxx
railway variables set TELEGRAM_BOT_TOKEN=xxx
railway variables set TELEGRAM_CHAT_ID=-1001234567890
railway variables set WATCHED_LEAGUE_IDS=968,800,801

# Add a Volume for state persistence
# Railway dashboard → your project → Add Volume → mount at /data

# Deploy
railway up
```

### 4. Monitor

```bash
railway logs        # tail live logs
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CRICKET_API_KEY` | ✅ | — | AllSportsAPI key |
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | — | Channel/group ID (negative number) |
| `WATCHED_LEAGUE_IDS` | ✅ | `968,800,801,802` | Comma-separated league keys |
| `POLL_INTERVAL_LIVE` | ❌ | `60` | Seconds between polls during live matches |
| `POLL_INTERVAL_IDLE` | ❌ | `300` | Seconds between polls when no live match |
| `STATE_FILE` | ❌ | `/data/state.json` | Where to persist match state |

---

## Sample Messages

**Match Start**
```
🏏 MATCH STARTED

*Mumbai Indians* vs *Chennai Super Kings*
🏆 IPL 2025 — Match 1
📍 Wankhede Stadium, Mumbai
🎯 T20

🪙 Toss: Mumbai Indians, elected to bat first
```

**Over Update**
```
📊 LIVE UPDATE

*Mumbai Indians*  87/2
*Chennai Super Kings*  -

📋 Over 8 - Mumbai batting
🎙️ Bumrah to Conway, 1 run

🏆 IPL 2025 | Match 1
```

**Wicket Alert**
```
💥 LIVE UPDATE

*Mumbai Indians*  87/3
*Chennai Super Kings*  -

📋 Over 8 - Wicket!
💥 Wicket: Conway c Rohit b Bumrah at 87/3

🏆 IPL 2025 | Match 1
```

**Final Result**
```
🏁 MATCH ENDED

*Mumbai Indians*  165/7
*Chennai Super Kings*  162/8

🎯 *Mumbai Indians won by 3 runs*
⭐ Player of the Match: Rohit Sharma

🏆 IPL 2025 | Match 1
```

---

## Tips

- For **IPL season**, once confirmed, pin the IPL league ID in `WATCHED_LEAGUE_IDS`
- Railway **Volume** at `/data` is required so state survives redeploys; without it the bot will re-announce already-started matches after every deploy
- AllSportsAPI free tier rate limits to ~100 req/day; a paid plan is needed for real-time polling
