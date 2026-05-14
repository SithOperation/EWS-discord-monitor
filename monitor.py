import json
import os
import requests
from pathlib import Path
from datetime import datetime, timezone

SITE_URL = "https://ews.kylemcdonald.net/"
DATA_URL = "https://pub-49bb6a6f314c47be9b481c25e5f6ca9e.r2.dev/dashboard.json"
STATE_FILE = Path("state.json")

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

def fetch_data():
    response = requests.get(
        DATA_URL,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 EWS-Discord-Monitor"}
    )
    response.raise_for_status()
    return response.json()

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def send_discord_alert(message):
    response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=20)
    response.raise_for_status()

def main():
    data = fetch_data()

    current = data.get("current", {})
    live_status = data.get("liveStatus", {})
    signal = data.get("signals", {}).get("composite", {})

    current_level = current.get("emergencyLevel")
    concurrent_count = current.get("concurrentCount")
    expected_count = signal.get("expectedConcurrentCount")
    z_score = current.get("zScore")
    as_of = current.get("asOf") or live_status.get("latestSampledAt")

    if current_level is None:
        send_discord_alert(
            "⚠️ EWS Monitor could not read current.emergencyLevel from the public dashboard JSON.\n"
            f"{SITE_URL}"
        )
        return

    state = load_state()
    previous_level = state.get("level")
    previous_count = state.get("concurrent_count")

    now = datetime.now(timezone.utc).isoformat()

    message = None

    if previous_level is None:
        message = (
            "✅ EWS Monitor is now active.\n"
            f"Current level: **{current_level}/5**\n"
            f"Airborne tracked aircraft: **{concurrent_count}**\n"
            f"Expected: **{round(expected_count, 1) if expected_count is not None else 'unknown'}**\n"
            f"Deviation: **{round(z_score, 2) if z_score is not None else 'unknown'}σ**\n"
            f"As of: `{as_of}`\n"
            f"{SITE_URL}"
        )

    elif current_level != previous_level:
        message = (
            "🚨 EWS level changed.\n"
            f"Level: **{previous_level}/5 → {current_level}/5**\n"
            f"Airborne tracked aircraft: **{concurrent_count}**\n"
            f"Expected: **{round(expected_count, 1) if expected_count is not None else 'unknown'}**\n"
            f"Deviation: **{round(z_score, 2) if z_score is not None else 'unknown'}σ**\n"
            f"As of: `{as_of}`\n"
            f"{SITE_URL}"
        )

    elif previous_count is not None and concurrent_count is not None:
        jump = concurrent_count - previous_count
        if jump >= 75:
            message = (
                "⚠️ EWS aircraft activity jumped sharply.\n"
                f"Tracked aircraft: **{previous_count} → {concurrent_count}**\n"
                f"Jump: **+{jump}**\n"
                f"Level: **{current_level}/5**\n"
                f"Deviation: **{round(z_score, 2) if z_score is not None else 'unknown'}σ**\n"
                f"As of: `{as_of}`\n"
                f"{SITE_URL}"
            )

    if message:
        send_discord_alert(message)

    state["level"] = current_level
    state["concurrent_count"] = concurrent_count
    state["z_score"] = z_score
    state["last_checked"] = now
    state["as_of"] = as_of
    save_state(state)

if __name__ == "__main__":
    main()
