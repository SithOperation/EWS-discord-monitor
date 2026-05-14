import json
import os
import re
import requests
from pathlib import Path
from datetime import datetime, timezone

SITE_URL = "https://ews.kylemcdonald.net/"
STATE_FILE = Path("state.json")

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

def fetch_site():
    response = requests.get(SITE_URL, timeout=20)
    response.raise_for_status()
    return response.text

def extract_level(html):

    patterns = [
        r'"level"\s*:\s*([1-5])',
        r'Level\s*([1-5])',
        r'CURRENT LEVEL[^0-9]*([1-5])',
        r'emergency level[^0-9]*([1-5])',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
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
    payload = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=20)
    response.raise_for_status()

def main():
    html = fetch_site()
    current_level = extract_level(html)

    if current_level is None:
        send_discord_alert(
            "⚠️ EWS Monitor could not read the current level. "
            "The site layout may have changed.\n"
            f"{SITE_URL}"
        )
        return

    state = load_state()
    previous_level = state.get("level")

    now = datetime.now(timezone.utc).isoformat()

    if previous_level is None:
        send_discord_alert(
            f"✅ EWS Monitor is now active.\n"
            f"Current level: **{current_level}**\n"
            f"{SITE_URL}"
        )

    elif current_level != previous_level:
        direction = "increased" if current_level > previous_level else "decreased"
        send_discord_alert(
            f"🚨 EWS level changed.\n"
            f"Level: **{previous_level} → {current_level}**\n"
            f"Direction: **{direction}**\n"
            f"{SITE_URL}"
        )

    elif current_level >= 4:
        send_discord_alert(
            f"⚠️ EWS level is still high: **{current_level}**\n"
            f"{SITE_URL}"
        )

    state["level"] = current_level
    state["last_checked"] = now
    save_state(state)

if __name__ == "__main__":
    main()
