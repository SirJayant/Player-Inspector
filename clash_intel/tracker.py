import json
import os
import requests

TARGET_TAG = "#PYU0VYGL2"
BASELINE_FILE = "baseline.json"

def update_monthly_baseline():
    token = os.getenv("COC_TOKEN")
    if not token:
        raise ValueError("COC_TOKEN environment variable is missing.")

    # Format tag for URL (# -> %23)
    formatted_tag = TARGET_TAG.replace("#", "%23")
    
    # RoyaleAPI Proxy URL (bypasses GitHub Actions dynamic IP blocks)
    url = f"https://cocproxy.royaleapi.dev/v1/players/{formatted_tag}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
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

    print(f"Updated baseline for {TARGET_TAG}: {conqueror_value} lifetime attacks.")

if __name__ == "__main__":
    update_monthly_baseline()
