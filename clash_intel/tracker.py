import json
import os
import urllib.parse
import requests

TARGET_TAG = "#PYU0VYGL2"
BASELINE_FILE = "baseline.json"

def update_monthly_baseline():
    raw_token = os.getenv("COC_TOKEN")
    if not raw_token:
        raise ValueError("COC_TOKEN environment variable is missing.")

    # Strip newlines, spaces, or tabs accidentally pasted into GitHub Secrets
    token = raw_token.strip()

    # URL-encode tag properly (#PYU0VYGL2 -> %23PYU0VYGL2)
    encoded_tag = urllib.parse.quote(TARGET_TAG)
    
    # RoyaleAPI Proxy URL
    url = f"https://cocproxy.royaleapi.dev/v1/players/{encoded_tag}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "ClashIntelTracker/1.0"
    }

    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch profile ({response.status_code}): {response.text}")

    player_data = response.json()
    
    # Extract "Conqueror" achievement (Lifetime Multiplayer Battles Won)
    conqueror_value = 0
    for achievement in player_data.get("achievements", []):
        if achievement.get("name") == "Conqueror":
            conqueror_value = achievement.get("value", 0)
            break

    payload = {
        "tag": TARGET_TAG,
        "conqueror_baseline": conqueror_value
    }

    with open(BASELINE_FILE, "w") as f:
        json.dump(payload, f, indent=4)

    print(f"Successfully updated baseline for {TARGET_TAG}: {conqueror_value} lifetime attacks.")

if __name__ == "__main__":
    update_monthly_baseline()
