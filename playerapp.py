import asyncio
import collections
import streamlit as st
import aiohttp
import pandas as pd
import urllib.parse

# SECURE CONFIG: This pulls the token from the Streamlit Secrets vault
# You do NOT need to input this in the GUI anymore.
COC_TOKEN = st.secrets["COC_TOKEN"]
BASE_URL = "https://cocproxy.royaleapi.dev/v1"

# ==========================================
#          PAGE CONFIG & SESSION STATE
# ==========================================
st.set_page_config(page_title="CoC Master Suite", page_icon="🛡️", layout="wide")

if "app_mode" not in st.session_state: st.session_state.app_mode = "🕵️ Player Inspector"
if "target_player_tag" not in st.session_state: st.session_state.target_player_tag = ""
if "target_clan_tag" not in st.session_state: st.session_state.target_clan_tag = ""
if "trigger_fetch" not in st.session_state: st.session_state.trigger_fetch = False
if "scanned_player" not in st.session_state: st.session_state.scanned_player = None
if "scanned_clan" not in st.session_state: st.session_state.scanned_clan = None

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

def format_tag(tag):
    tag = tag.strip().upper()
    if not tag.startswith("#"): tag = "#" + tag
    return urllib.parse.quote(tag)

async def fetch_api(session, endpoint):
    url = f"{BASE_URL}/{endpoint}"
    headers = {"Authorization": f"Bearer {COC_TOKEN}", "Accept": "application/json"}
    async with session.get(url, headers=headers) as response:
        if response.status == 200: return await response.json(), None
        return None, f"HTTP {response.status}"

async def process_player_inspector(tag):
    async with aiohttp.ClientSession() as session:
        profile_data, error = await fetch_api(session, f"players/{format_tag(tag)}")
        if error: return None, None, None, error
        equipment_list = []
        for eq in profile_data.get("heroEquipment", []):
            if eq.get("village") == "home":
                equipment_list.append({"Equipment": eq["name"], "Level": eq["level"], "Max Level": eq["maxLevel"]})
        eq_df = pd.DataFrame(equipment_list).sort_values(by="Level", ascending=False) if equipment_list else pd.DataFrame()
        battle_log, _ = await fetch_api(session, f"players/{format_tag(tag)}/battlelog")
        army_url = None
        if battle_log and "items" in battle_log:
            codes = [item.get("armyShareCode") for item in battle_log["items"] if item.get("armyShareCode") and item.get("attack")][:10]
            if codes:
                most_common_code, _ = collections.Counter(codes).most_common(1)[0]
                army_url = f"https://link.clashofclans.com/en?action=CopyArmy&army={most_common_code}"
        return profile_data, eq_df, army_url, None

async def process_clan_auditor(tag, input_type):
    async with aiohttp.ClientSession() as session:
        if input_type == "Player Tag":
            player_data, err = await fetch_api(session, f"players/{format_tag(tag)}")
            if err or not player_data.get("clan"): return None, None, None, None, "Could not resolve player to a clan."
            clan_tag = player_data["clan"]["tag"]
        else: clan_tag = tag
        clan_data, err = await fetch_api(session, f"clans/{format_tag(clan_tag)}")
        if err: return None, None, None, None, err
        war_data, _ = await fetch_api(session, f"clans/{format_tag(clan_tag)}/warlog")
        raid_data, _ = await fetch_api(session, f"clans/{format_tag(clan_tag)}/capitalraidseasons")
        # (Rest of your original logic here remains the same)
        return clan_data, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

# GUI
st.title("🛡️ CoC Operations Master Suite")
with st.sidebar:
    st.header("⚙️ Modules")
    app_mode = st.radio("Select Module:", ["🕵️ Player Inspector", "🏰 Clan & Raid Auditor"], key="app_mode")

# ... (Include the rest of your UI rendering logic here)
