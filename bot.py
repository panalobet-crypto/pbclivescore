"""
Cricket Score Telegram Bot
AllSportsAPI v2 → Telegram Push
Tracks: IPL + Bangladesh leagues
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from telegram import Bot
from telegram.constants import ParseMode

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
CRICKET_API_KEY   = "c9bd324007d1a3e531155efb21abade9b85f6cc6cd7dd499bf27744ea4eff52e"
TELEGRAM_TOKEN    = "8753904006:AAEqdJQEl6GuwjWewn3olpX4iPlB5iq8esE"
TELEGRAM_CHAT_ID  = "-1002918240048"

WATCHED_LEAGUE_IDS = {"745", "8453", "8062", "10533", "746"}

POLL_INTERVAL_LIVE    = int(os.environ.get("POLL_INTERVAL_LIVE", "60"))    # seconds
POLL_INTERVAL_IDLE    = int(os.environ.get("POLL_INTERVAL_IDLE", "300"))   # seconds

STATE_FILE = Path(os.environ.get("STATE_FILE", "/data/state.json"))

API_BASE = "https://apiv2.allsportsapi.com/cricket/"

# ── State helpers ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load persisted match states."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ── API calls ─────────────────────────────────────────────────────────────────

async def fetch_livescore(client: httpx.AsyncClient) -> list[dict]:
    """Fetch all live matches."""
    try:
        r = await client.get(
            API_BASE,
            params={"met": "Livescore", "APIkey": CRICKET_API_KEY},
            timeout=15,
            follow_redirects=True,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("success") == 1:
            return data.get("result") or []
    except Exception as e:
        log.error("Livescore fetch error: %s", e)
    return []


async def fetch_today_fixtures(client: httpx.AsyncClient) -> list[dict]:
    """Fetch today's scheduled matches (to detect match-start events)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        r = await client.get(
            API_BASE,
            params={
                "met": "Fixtures",
                "APIkey": CRICKET_API_KEY,
                "from": today,
                "to": today,
            },
            timeout=15,
            follow_redirects=True,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("success") == 1:
            return data.get("result") or []
    except Exception as e:
        log.error("Fixtures fetch error: %s", e)
    return []


# ── Message formatters ────────────────────────────────────────────────────────

CRICKET_EMOJI = "🏏"
FLAG_MAP = {
    "india": "🇮🇳", "bangladesh": "🇧🇩", "pakistan": "🇵🇰",
    "australia": "🇦🇺", "england": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "south africa": "🇿🇦",
    "new zealand": "🇳🇿", "sri lanka": "🇱🇰", "west indies": "🌴",
}

def team_emoji(name: str) -> str:
    low = name.lower()
    for key, flag in FLAG_MAP.items():
        if key in low:
            return flag
    return "🏏"


def fmt_match_start(m: dict) -> str:
    home = m["event_home_team"]
    away = m["event_away_team"]
    toss = m.get("event_toss", "")
    league = m.get("league_name", "")
    round_ = m.get("league_round", "")
    stadium = m.get("event_stadium", "")
    match_type = m.get("event_type", "")

    lines = [
        f"🏏 *ম্যাচ শুরু হয়েছে!*",
        f"",
        f"*{home}* বনাম *{away}*",
        f"🏆 {league}" + (f" — {round_}" if round_ else ""),
        f"📍 {stadium}" if stadium else "",
        f"🎯 {match_type}" if match_type else "",
        f"",
        f"🪙 টস: {toss}" if toss else "",
    ]
    return "\n".join(l for l in lines if l is not None and l != "")


def fmt_score_update(m: dict, trigger: str) -> str:
    home  = m["event_home_team"]
    away  = m["event_away_team"]
    h_score = m.get("event_home_final_result", "-")
    a_score = m.get("event_away_final_result", "-")
    status_info = m.get("event_status_info", "")
    league = m.get("league_name", "")
    round_ = m.get("league_round", "")

    # Last ball commentary
    comments = m.get("comments", {})
    last_ball = ""
    for inn_comments in _vals(comments):
        if isinstance(inn_comments, list) and inn_comments:
            last_ball = inn_comments[0].get("post", "")
            break

    # Wickets this innings
    wickets_str = ""
    wickets = m.get("wickets", {})
    for inn_name, wkts in (wickets.items() if isinstance(wickets, dict) else []):
        if isinstance(wkts, list) and wkts:
            latest = wkts[0]
            wickets_str = f"💥 উইকেট: {latest.get('batsman','').strip()} — {latest.get('score','')}"
            break

    if trigger == "wicket":
        icon = "💥"
        title = "*উইকেট পড়েছে!*"
    else:
        icon = "📊"
        title = "*লাইভ স্কোর*"

    lines = [
        f"{icon} {title}",
        f"",
        f"*{home}*  {h_score}",
        f"*{away}*  {a_score}",
        f"",
        f"📋 {status_info}" if status_info else "",
        f"{wickets_str}" if wickets_str and trigger == "wicket" else "",
        f"🎙️ _{last_ball}_" if last_ball else "",
        f"",
        f"🏆 {league}" + (f" | {round_}" if round_ else ""),
    ]
    return "\n".join(l for l in lines if l is not None and l != "")


def fmt_match_end(m: dict) -> str:
    home  = m["event_home_team"]
    away  = m["event_away_team"]
    h_score = m.get("event_home_final_result", "-")
    a_score = m.get("event_away_final_result", "-")
    status_info = m.get("event_status_info", "চূড়ান্ত ফলাফল")
    mom = m.get("event_man_of_match", "")
    league = m.get("league_name", "")
    round_ = m.get("league_round", "")

    lines = [
        f"🏁 *ম্যাচ শেষ!*",
        f"",
        f"*{home}*  {h_score}",
        f"*{away}*  {a_score}",
        f"",
        f"🎯 *{status_info}*",
        f"⭐ ম্যাচ সেরা খেলোয়াড়: {mom}" if mom else "",
        f"",
        f"🏆 {league}" + (f" | {round_}" if round_ else ""),
    ]
    return "\n".join(l for l in lines if l is not None and l != "")


# ── Telegram sender ───────────────────────────────────────────────────────────

async def send(bot: Bot, text: str):
    """Send message with retry."""
    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
            log.info("Sent: %s", text[:60].replace("\n", " "))
            return
        except Exception as e:
            log.warning("Send attempt %d failed: %s", attempt + 1, e)
            await asyncio.sleep(2 ** attempt)


# ── Match state extractor ─────────────────────────────────────────────────────

def _vals(obj) -> list:
    """Return values whether obj is dict or list."""
    if isinstance(obj, dict):
        return list(obj.values())
    if isinstance(obj, list):
        return obj
    return []


def extract_over_count(m: dict) -> Optional[str]:
    """Extract current over from extra block or comments."""
    extra = m.get("extra", {})
    for inn_data in _vals(extra):
        if isinstance(inn_data, dict):
            total_overs = inn_data.get("total_overs") or inn_data.get("total", "")
            if total_overs and "(" in str(total_overs):
                return str(total_overs)
    # Fallback: latest comment overs field
    comments = m.get("comments", {})
    for inn_comments in _vals(comments):
        if isinstance(inn_comments, list) and inn_comments:
            return inn_comments[0].get("overs")
    return None


def extract_wicket_count(m: dict) -> int:
    """Count total wickets fallen across all innings from scorecard."""
    total = 0
    scorecard = m.get("scorecard", {})
    for inn_players in _vals(scorecard):
        if isinstance(inn_players, list):
            for player in inn_players:
                if player.get("type") == "Batsman" and player.get("status", "") not in ("not out", ""):
                    total += 1
    return total


def is_watched(m: dict) -> bool:
    return str(m.get("league_key", "")) == "745"  # IPL only


# ── Main loop ─────────────────────────────────────────────────────────────────

async def main():
    log.info("Cricket bot starting. Watched leagues: %s", WATCHED_LEAGUE_IDS)
    state = load_state()
    bot = Bot(token=TELEGRAM_TOKEN)

    async with httpx.AsyncClient() as client:
        while True:
            try:
                live_matches = await fetch_livescore(client)
                fixtures     = await fetch_today_fixtures(client)

                # Combine: live first, then non-live fixtures (for match-start detection)
                all_matches = {m["event_key"]: m for m in fixtures}
                for m in live_matches:
                    all_matches[m["event_key"]] = m  # live overrides

                has_live = bool(live_matches)
                tasks = []

                for eid, m in all_matches.items():
                    if not is_watched(m):
                        continue

                    prev = state.get(eid, {})
                    cur_status = m.get("event_status", "")
                    is_live    = m.get("event_live") == "1"
                    is_finished = cur_status in ("Finished", "Completed", "Abandoned", "Cancelled")

                    # ── Match START ────────────────────────────────────────────
                    if is_live and not prev.get("notified_start"):
                        tasks.append(send(bot, fmt_match_start(m)))
                        state.setdefault(eid, {})["notified_start"] = True
                        state[eid]["last_over"]    = extract_over_count(m)
                        state[eid]["last_wickets"] = extract_wicket_count(m)

                    # ── Live updates ───────────────────────────────────────────
                    elif is_live and prev.get("notified_start"):
                        cur_over    = extract_over_count(m)
                        cur_wickets = extract_wicket_count(m)
                        prev_over    = prev.get("last_over")
                        prev_wickets = prev.get("last_wickets", 0)

                        # Wicket fell
                        if cur_wickets > prev_wickets:
                            tasks.append(send(bot, fmt_score_update(m, "wicket")))
                            state[eid]["last_wickets"] = cur_wickets
                            state[eid]["last_over"]    = cur_over

                        # New over completed — push whenever the integer over number changes
                        # Use modulo to handle innings reset (e.g. 50 → 0 → 1 → 2...)
                        elif cur_over and cur_over != prev_over:
                            try:
                                cur_int  = int(str(cur_over).split(".")[0])
                                prev_int = int(str(prev_over or "0").split(".")[0]) if prev_over else -1
                                # Push if: over increased, OR innings reset (cur < prev means new innings)
                                if cur_int != prev_int:
                                    tasks.append(send(bot, fmt_score_update(m, "over")))
                            except Exception:
                                tasks.append(send(bot, fmt_score_update(m, "over")))
                            state[eid]["last_over"] = cur_over

                    # ── Match END ──────────────────────────────────────────────
                    if is_finished and not prev.get("notified_end"):
                        tasks.append(send(bot, fmt_match_end(m)))
                        state.setdefault(eid, {})["notified_end"] = True

                    # ── Cleanup old state for finished matches ─────────────────
                    if is_finished and prev.get("notified_end"):
                        # Keep minimal record
                        state[eid] = {"notified_start": True, "notified_end": True, "done": True}

                # Fire all notifications concurrently
                if tasks:
                    await asyncio.gather(*tasks)

                save_state(state)

                # Adaptive polling
                interval = POLL_INTERVAL_LIVE if has_live else POLL_INTERVAL_IDLE
                log.info(
                    "Live=%d watched. Next poll in %ds.",
                    sum(1 for m in live_matches if is_watched(m)),
                    interval,
                )
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                log.info("Bot stopped.")
                break
            except Exception as e:
                log.exception("Unexpected error: %s", e)
                await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
