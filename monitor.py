import json
import os
import re
import requests
from pathlib import Path
from datetime import datetime, timezone

SITE_URL = "https://ews.kylemcdonald.net/"
DATA_URL = "https://ews.kylemcdonald.net/dashboard.json"
STATE_FILE = Path("state.json")

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

def fetch_json():
    response = requests.get(DATA_URL, timeout=20)
    response.raise_for_status()
    return response.json()

def find_level(data):
    text = json.dumps(data)

    patterns = [
        r'"level"\s*:\s*([1-5])',
        r'"emergency_level"\s*:\s*([1-5])',
        r'"emergencyLevel"\s*:\s*([1-5])',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None

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
    data = fetch_json()
    current_level = find_level(data)

    if current_level is None:
        send_discord_alert(
            "⚠️ EWS Monitor still could not read the current level from dashboard.json.\n"
            f"{SITE_URL}"
        )
        return

    state = load_state()
    previous_level = state.get("level")
    now = datetime.now(timezone.utc).isoformat()

    if previous_level is None:
        send_discord_alert(
            f"✅ EWS Monitor is now active.\n"
            f"Current level: **{current_level}/5**\n"
            f"{SITE_URL}"
        )
    elif current_level != previous_level:
        send_discord_alert(
            f"🚨 EWS level changed.\n"
            f"Level: **{previous_level}/5 → {current_level}/5**\n"
            f"{SITE_URL}"
        )

    state["level"] = current_level
    state["last_checked"] = now
    save_state(state)

if __name__ == "__main__":
    main()
