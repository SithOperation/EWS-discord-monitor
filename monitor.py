import json
import os
import re
import requests
from pathlib import Path
from datetime import datetime, timezone
from html import unescape

SITE_URL = "https://ews.kylemcdonald.net/"
STATE_FILE = Path("state.json")

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

def fetch_site():
    response = requests.get(
        SITE_URL,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0 EWS-Discord-Monitor"}
    )
    response.raise_for_status()
    return response.text

def extract_level(html):
    text = unescape(html)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    match = re.search(r"Emergency\s+Level\s+([1-5])\s*/\s*5", text, re.IGNORECASE)
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
    html = fetch_site()
    current_level = extract_level(html)

    if current_level is None:
        send_discord_alert(
            "⚠️ EWS Monitor could not read the current level from the webpage HTML.\n"
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
