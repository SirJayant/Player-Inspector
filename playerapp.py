import asyncio
import collections
import urllib.parse
import aiohttp
import pandas as pd
import streamlit as st

# SECURE CONFIG: Pulls from Streamlit Cloud Secrets vault natively. No .env needed.
COC_TOKEN = st.secrets["COC_TOKEN"]
BASE_URL = "https://cocproxy.royaleapi.dev/v1"

# ==========================================
#         PAGE CONFIG & SESSION STATE
# ==========================================
st.set_page_config(page_title="CoC Master Suite", page_icon="🛡️", layout="wide")

# Initialize routing states
if "app_mode" not in st.session_state: st.session_state.app_mode = "🕵️ Player Inspector"
if "target_player_tag" not in st.session_state: st.session_state.target_player_tag = ""
if "target_clan_tag" not in st.session_state: st.session_state.target_clan_tag = ""
if "trigger_fetch" not in st.session_state: st.session_state.trigger_fetch = False

# Initialize data cache states
if "scanned_player" not in st.session_state: st.session_state.scanned_player = None
if "scanned_clan" not in st.session_state: st.session_state.scanned_clan = None

# ==========================================
#         NAVIGATION CALLBACKS
# ==========================================
def jump_to_clan(clan_tag):
    st.session_state.target_clan_tag = clan_tag
    st.session_state.app_mode = "🏰 Clan & Raid Auditor"
    st.session_state.trigger_fetch = True
    st.session_state.scanned_player = None 

def jump_to_player(player_tag):
    st.session_state.target_player_tag = player_tag
    st.session_state.app_mode = "🕵️ Player Inspector"
    st.session_state.trigger_fetch = True
    st.session_state.scanned_clan = None 

# ==========================================
#         HELPERS & API WRAPPERS
# ==========================================
def format_tag(tag):
    tag = tag.strip().upper()
    if not tag.startswith("#"): tag = "#" + tag
    return urllib.parse.quote(tag)

async def fetch_api(session, endpoint, headers):
    url = f"{BASE_URL}/{endpoint}"
    async with session.get(url, headers=headers) as response:
        if response.status == 200: return await response.json(), None
        return None, f"HTTP {response.status}"

async def fetch_player_profile(session, tag, headers):
    url = f"{BASE_URL}/players/{format_tag(tag)}"
    async with session.get(url, headers=headers) as response:
        if response.status == 200: return await response.json()
        return None

# ==========================================
#         CORE LOGIC ENGINES
# ==========================================
async def process_player_inspector(tag, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        profile_data, error = await fetch_api(session, f"players/{format_tag(tag)}", headers)
        if error: return None, None, None, error

        equipment_list = []
        for eq in profile_data.get("heroEquipment", []):
            if eq.get("village") == "home":
                equipment_list.append({
                    "Equipment": eq["name"], "Level": eq["level"], "Max Level": eq["maxLevel"],
                    "Status": "🔥 MAXED" if eq["level"] == eq["maxLevel"] else "Upgrading"
                })
        eq_df = pd.DataFrame(equipment_list).sort_values(by="Level", ascending=False) if equipment_list else pd.DataFrame()

        battle_log, _ = await fetch_api(session, f"players/{format_tag(tag)}/battlelog", headers)
        army_url = None
        if battle_log and "items" in battle_log:
            codes = [item.get("armyShareCode") for item in battle_log["items"] if item.get("armyShareCode") and item.get("attack")][:10]
            if codes:
                most_common_code, _ = collections.Counter(codes).most_common(1)[0]
                army_url = f"https://link.clashofclans.com/en?action=CopyArmy&army={most_common_code}"

        return profile_data, eq_df, army_url, None

async def process_clan_auditor(tag, input_type, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        if input_type == "Player Tag":
            player_data, err = await fetch_api(session, f"players/{format_tag(tag)}", headers)
            if err or not player_data.get("clan"): return None, None, None, None, "Could not resolve player to a clan."
            clan_tag = player_data["clan"]["tag"]
        else:
            clan_tag = tag

        clan_data, err = await fetch_api(session, f"clans/{format_tag(clan_tag)}", headers)
        if err: return None, None, None, None, err
        master_roster = clan_data.get("memberList", [])

        war_data, _ = await fetch_api(session, f"clans/{format_tag(clan_tag)}/warlog", headers)
        war_log = []
        if war_data and "items" in war_data:
            for war in war_data["items"][:10]:
                raw_result = war.get("result")
                war_log.append({
                    "Opponent": war.get("opponent", {}).get("name", "Unknown"),
                    "Result": str(raw_result).capitalize() if raw_result else "In Progress / Hidden",
                    "Team Size": war.get("teamSize", "N/A")
                })
        war_df = pd.DataFrame(war_log)

        raid_data, err = await fetch_api(session, f"clans/{format_tag(clan_tag)}/capitalraidseasons", headers)
        slacker_rows, roster_rows = [], []

        if raid_data and "items" in raid_data:
            ended_seasons = [s for s in raid_data["items"] if s.get("state") == "ended"]
            if ended_seasons:
                raid_map = {p["tag"]: p for p in ended_seasons[0].get("members", [])}
                for member in master_roster:
                    m_tag, role = member["tag"], member["role"].replace("admin", "Elder").replace("coLeader", "Co-Leader").capitalize()
                    if m_tag not in raid_map:
                        slacker_rows.append({"Player": member["name"], "Role": role, "Tag": m_tag, "Attacks Used": 0, "Max Possible": 6, "Gold": 0, "Violation": "ZERO ATTACKS"})
                    else:
                        p = raid_map[m_tag]
                        done, mx = p["attacks"], p["attackLimit"] + p["bonusAttackLimit"]
                        if done < mx: slacker_rows.append({"Player": member["name"], "Role": role, "Tag": m_tag, "Attacks Used": done, "Max Possible": mx, "Gold": p["capitalResourcesLooted"], "Violation": f"Incomplete ({mx-done} missed)"})

                for m_tag, p in raid_map.items():
                    roster_rows.append({"Player": p["name"], "Tag": m_tag, "Attacks": p["attacks"], "Max Possible": p["attackLimit"] + p["bonusAttackLimit"], "Gold": p["capitalResourcesLooted"]})

        slacker_df = pd.DataFrame(slacker_rows).sort_values(
