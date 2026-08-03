import json
import os
import requests
from datetime import datetime, timezone

# Target configuration
PLAYER_TAG = "%23PYU0VYGL2"  # #PYU0VYGL2 URL-encoded
API_TOKEN = os.getenv("COC_TOKEN")
BASE_URL = "https://cocproxy.royaleapi.dev/v1"

DATA_FILE = "conqueror_data.json"
README_FILE = "README.md"


def fetch_conqueror_value() -> int:
    """Fetch the Conqueror achievement value from the Supercell API."""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json",
    }
    url = f"{BASE_URL}/players/{PLAYER_TAG}"

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()

    for achievement in data.get("achievements", []):
        if achievement.get("name") == "Conqueror":
            return achievement.get("value", 0)

    raise ValueError("Conqueror achievement not found in player profile.")


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def update_readme(
    current_val: int, baseline_val: int, month_str: str, history: list
):
    """Renders a public Markdown log on the repository front page."""
    attacks_this_month = current_val - baseline_val

    content = f"""# ⚔️ Clash of Clans Conqueror Tracker

**Player Tag:** `#PYU0VYGL2`  
**Current Tracking Month:** `{month_str}`  

---

### 📊 Monthly Progress Summary
* **Month Baseline:** `{baseline_val:,}`
* **Current Total Conqueror Count:** `{current_val:,}`
* **Attacks Made This Month:** **`+{attacks_this_month:,}`** ⚔️

---

### 📜 Historical Monthly Ledger
| Month | Starting Value | Ending Value | Attacks Made |
| :--- | :--- | :--- | :--- |
"""
    for entry in reversed(history):
        content += f"| {entry['month']} | {entry['start']:,} | {entry['end']:,} | +{entry['attacks']:,} |\n"

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    current_val = fetch_conqueror_value()
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")

    data = load_data()

    # Initial setup for first run
    if not data:
        data = {
            "current_month": current_month,
            "baseline_value": current_val,
            "latest_value": current_val,
            "history": [],
        }

    # Month rollover check
    if data.get("current_month") != current_month:
        prev_start = data.get("baseline_value", current_val)
        prev_end = data.get("latest_value", current_val)
        prev_attacks = max(0, prev_end - prev_start)

        # Record completed month history
        data.setdefault("history", []).append(
            {
                "month": data.get("current_month"),
                "start": prev_start,
                "end": prev_end,
                "attacks": prev_attacks,
            }
        )

        # Reset baseline for the new month
        data["current_month"] = current_month
        data["baseline_value"] = current_val

    # Update latest stats
    data["latest_value"] = current_val
    save_data(data)

    # Update public README display
    update_readme(
        current_val,
        data["baseline_value"],
        current_month,
        data.get("history", []),
    )


if __name__ == "__main__":
    main()