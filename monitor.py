import json
import os
import requests
from pathlib import Path
from datetime import datetime, timezone


SITE_URL = "https://ews.kylemcdonald.net/"
DATA_URL = "https://pub-49bb6a6f314c47be9b481c25e5f6ca9e.r2.dev/dashboard.json"

STATE_FILE = Path("state.json")

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def fetch_data():

    try:

        response = requests.get(
            DATA_URL,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 EWS-Discord-Monitor"
            }
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        print(f"EWS data fetch failed: {e}")

        return None



def load_state():

    if STATE_FILE.exists():

        try:

            return json.loads(
                STATE_FILE.read_text(
                    encoding="utf-8"
                )
            )

        except json.JSONDecodeError:

            print("Invalid state.json. Resetting.")

    return {}



def save_state(state):

    STATE_FILE.write_text(
        json.dumps(
            state,
            indent=2
        ),
        encoding="utf-8"
    )



def send_discord_alert(message):

    if not DISCORD_WEBHOOK_URL:

        print("Discord webhook missing. Alert skipped.")

        return


    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json={
            "content": message
        },
        timeout=20
    )


    response.raise_for_status()



def main():

    data = fetch_data()


    if data is None:

        return



    print("Dashboard data received")


    current = data.get(
        "current",
        {}
    )


    live_status = data.get(
        "liveStatus",
        {}
    )


    signal = data.get(
        "signals",
        {}
    ).get(
        "composite",
        {}
    )



    current_level = current.get(
        "emergencyLevel"
    )


    concurrent_count = current.get(
        "concurrentCount"
    )


    expected_count = signal.get(
        "expectedConcurrentCount"
    )


    z_score = current.get(
        "zScore"
    )


    as_of = (
        current.get("asOf")
        or
        live_status.get("latestSampledAt")
    )



    if current_level is None:

        send_discord_alert(
            "⚠️ EWS Monitor could not read emergency level.\n"
            f"{SITE_URL}"
        )

        return



    state = load_state()


    previous_level = state.get(
        "level"
    )


    previous_count = state.get(
        "concurrent_count"
    )



    now = datetime.now(
        timezone.utc
    ).isoformat()



    message = None



    if previous_level is None:

        message = (
            "✅ EWS Monitor active.\n"
            f"Level: **{current_level}/5**\n"
            f"Aircraft: **{concurrent_count}**\n"
            f"Expected: **{expected_count}**\n"
            f"Deviation: **{z_score}σ**\n"
            f"As of: `{as_of}`\n"
            f"{SITE_URL}"
        )



    elif current_level != previous_level:

        message = (
            "🚨 EWS level changed.\n"
            f"{previous_level}/5 → {current_level}/5\n"
            f"Aircraft: **{concurrent_count}**\n"
            f"As of: `{as_of}`\n"
            f"{SITE_URL}"
        )



    elif (
        previous_count is not None
        and concurrent_count is not None
    ):

        jump = concurrent_count - previous_count


        if jump >= 75:

            message = (
                "⚠️ EWS aircraft activity jump.\n"
                f"{previous_count} → {concurrent_count}\n"
                f"Increase: +{jump}\n"
                f"{SITE_URL}"
            )



    if message:

        send_discord_alert(
            message
        )



    state.update(
        {
            "level": current_level,
            "concurrent_count": concurrent_count,
            "z_score": z_score,
            "last_checked": now,
            "as_of": as_of
        }
    )


    save_state(state)



    print("state.json updated")



if __name__ == "__main__":

    main()
