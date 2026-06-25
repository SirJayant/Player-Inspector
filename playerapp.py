import asyncio
import collections
import streamlit as st
import aiohttp
import pandas as pd
import urllib.parse

# SECURE: API token is fetched from Streamlit Secrets (configured on the hosting dashboard)
COC_TOKEN = st.secrets["COC_TOKEN"]
BASE_URL = "https://cocproxy.royaleapi.dev/v1"

st.set_page_config(page_title="CoC Master Suite", page_icon="🛡️", layout="wide")

# --- Initialize Session State ---
if "app_mode" not in st.session_state: st.session_state.app_mode = "🕵️ Player Inspector"
if "target_player_tag" not in st.session_state: st.session_state.target_player_tag = ""
if "target_clan_tag" not in st.session_state: st.session_state.target_clan_tag = ""
if "trigger_fetch" not in st.session_state: st.session_state.trigger_fetch = False
if "scanned_player" not in st.session_state: st.session_state.scanned_player = None
if "scanned_clan" not in st.session_state: st.session_state.scanned_clan = None

# --- Callbacks ---
def jump_to_clan(clan_tag):
    st.session_state.target_clan_tag = clan_tag
    st.session_state.app_mode = "🏰 Clan & Raid Auditor"
    st.session_state.trigger_fetch = True

def jump_to_player(player_tag):
    st.session_state.target_player_tag = player_tag
    st.session_state.app_mode = "🕵️ Player Inspector"
    st.session_state.trigger_fetch = True

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

# --- Logic Engines ---
async def process_player_inspector(tag):
    async with aiohttp.ClientSession() as session:
        profile_data, error = await fetch_api(session, f"players/{format_tag(tag)}")
        if error: return None, None, None, error
        equipment_list = []
        for eq in profile_data.get("heroEquipment", []):
            if eq.get("village") == "home":
                equipment_list.append({"Equipment": eq["name"], "Level": eq["level"], "Max Level": eq["maxLevel"], "Status": "🔥 MAXED" if eq["level"] == eq["maxLevel"] else "Upgrading"})
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
        # Logic simplified for clarity, ensure your processing logic matches this structure
        return clan_data, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

# --- UI Rendering ---
st.title("🛡️ CoC Operations Master Suite")
with st.sidebar:
    app_mode = st.radio("Select Module:", ["🕵️ Player Inspector", "🏰 Clan & Raid Auditor"], key="app_mode")

if app_mode == "🕵️ Player Inspector":
    target_tag = st.text_input("Enter Player Tag:", key="target_player_tag")
    if st.button("Inspect Player") or st.session_state.trigger_fetch:
        st.session_state.trigger_fetch = False
        st.session_state.scanned_player = asyncio.run(process_player_inspector(st.session_state.target_player_tag))
    
    if st.session_state.scanned_player:
        profile, eq_df, army_url, error = st.session_state.scanned_player
        if error: st.error(error)
        else: st.write(f"Displaying: {profile.get('name')}")

elif app_mode == "🏰 Clan & Raid Auditor":
    input_type = st.selectbox("Search By:", ["Clan Tag", "Player Tag"])
    target_tag = st.text_input("Enter Tag:", key="target_clan_tag")
    if st.button("Run Audit") or st.session_state.trigger_fetch:
        st.session_state.trigger_fetch = False
        st.session_state.scanned_clan = asyncio.run(process_clan_auditor(st.session_state.target_clan_tag, input_type))

    if st.session_state.scanned_clan:
        clan, _, _, _, error = st.session_state.scanned_clan
        if error: st.error(error)
        else: st.write(f"Audit Complete for: {clan.get('name')}")
