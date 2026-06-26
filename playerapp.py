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

        slacker_df = pd.DataFrame(slacker_rows).sort_values(by=["Attacks Used", "Gold"]) if slacker_rows else pd.DataFrame()
        roster_df = pd.DataFrame(roster_rows).sort_values(by="Gold", ascending=False) if roster_rows else pd.DataFrame()
        return clan_data, slacker_df, roster_df, war_df, None

async def run_ping_a_donor(member_tags, clan_level, unit_name, desired_level, is_max, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    # Fetch all 50 profiles concurrently - SUPER fast
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_player_profile(session, tag, headers) for tag in member_tags]
        profiles = await asyncio.gather(*tasks)

    # Determine clan perk boost
    level_boost = 0
    if clan_level >= 10: level_boost = 2
    elif clan_level >= 5: level_boost = 1

    eligible_players = []
    unit_name_lower = unit_name.lower().strip()

    for p in profiles:
        if not p: continue
        # Combine troops, spells, and sieges (sieges are housed in the 'troops' array in the API)
        inventory = p.get("troops", []) + p.get("spells", [])
        
        for item in inventory:
            if item["name"].lower() == unit_name_lower and item.get("village") == "home":
                actual_level = item["level"]
                max_possible = item["maxLevel"]
                effective_level = min(actual_level + level_boost, max_possible)
                
                meets_req = False
                if is_max:
                    if effective_level >= max_possible: meets_req = True
                else:
                    if effective_level >= desired_level: meets_req = True
                    
                if meets_req:
                    eligible_players.append({
                        "Player": p["name"],
                        "Role": p.get("role", "member").replace("admin", "Elder").replace("coLeader", "Co-Leader").capitalize(),
                        "Base Level": actual_level,
                        "Boosted Level": effective_level,
                        "Is Max?": "🔥 MAX" if effective_level >= max_possible else "No"
                    })
                break # Move to next player once the unit is found and evaluated
    
    return pd.DataFrame(eligible_players).sort_values(by="Base Level", ascending=False) if eligible_players else pd.DataFrame()

# ==========================================
#         GUI RENDERER (STREAMLIT)
# ==========================================
st.title("🛡️ CoC Operations Master Suite")

with st.sidebar:
    st.header("⚙️ Configuration")
    app_mode = st.radio("Select Module:", ["🕵️ Player Inspector", "🏰 Clan & Raid Auditor"], key="app_mode")

# ------------------------------------------
# MODULE 1: PLAYER INSPECTOR
# ------------------------------------------
if app_mode == "🕵️ Player Inspector":
    st.subheader("🕵️ Player Inspector")

    col1, col2 = st.columns([3, 1])
    with col1: target_tag = st.text_input("Enter Player Tag:", key="target_player_tag", placeholder="#QYJ89QR")
    with col2:
        st.write(""); st.write("")
        inspect_btn = st.button("Inspect Player", width="stretch", type="primary")

    if (inspect_btn or st.session_state.trigger_fetch) and target_tag:
        st.session_state.trigger_fetch = False
        with st.spinner("Infiltrating Supercell Servers..."):
            st.session_state.scanned_player = asyncio.run(process_player_inspector(target_tag, COC_TOKEN))

    if st.session_state.scanned_player:
        profile, eq_df, army_url, error = st.session_state.scanned_player

        if error:
            st.error(error)
        else:
            st.success(f"Successfully located {profile.get('name')}!")

            if profile.get("clan"):
                st.info(f"🔰 **Clan Detected:** {profile['clan']['name']} ({profile['clan']['tag']})")
                st.button(
                    "Run Audit on this Clan",
                    width="stretch",
                    on_click=jump_to_clan,
                    args=(profile['clan']['tag'],)
                )

            # --- ADDED NEW METRICS HERE ---
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Town Hall", profile.get("townHallLevel"))
            c2.metric("Trophies", profile.get("trophies"))
            c3.metric("Attack Wins", profile.get("attackWins", 0))
            c4.metric("Defense Wins", profile.get("defenseWins", 0))
            
            # Calculate Donation Ratio
            donated = profile.get("donations", 0)
            received = profile.get("donationsReceived", 0)
            ratio = round(donated / received, 2) if received > 0 else donated
            c5.metric("Donation Ratio", f"{ratio}x", help=f"{donated} Donated / {received} Received")

            st.divider()

            if army_url: st.info(f"⚔️ **Most Used Army Detected!** [Click here to copy to game]({army_url})")
            else: st.warning("No recent offensive army data found.")

            if not eq_df.empty:
                st.write("### Hero Equipment Loadout")
                st.dataframe(eq_df, width="stretch", hide_index=True)
            else: st.write("No Hero Equipment found.")

# ------------------------------------------
# MODULE 2: CLAN & Raid Auditor
# ------------------------------------------
elif app_mode == "🏰 Clan & Raid Auditor":
    st.subheader("🏰 Clan & Raid Auditor")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1: input_type = st.selectbox("Search By:", ["Clan Tag", "Player Tag"])
    with col2: target_tag = st.text_input("Enter Tag:", key="target_clan_tag", placeholder="#2RV082C9Y")
    with col3:
        st.write(""); st.write("")
        audit_btn = st.button("Run Audit", width="stretch", type="primary")

    if (audit_btn or st.session_state.trigger_fetch) and target_tag:
        st.session_state.trigger_fetch = False
        with st.spinner("Compiling Ledgers..."):
            st.session_state.scanned_clan = asyncio.run(process_clan_auditor(target_tag, input_type, COC_TOKEN))

    if st.session_state.scanned_clan:
        clan, slacker_df, roster_df, war_df, error = st.session_state.scanned_clan

        if error:
            st.error(error)
        else:
            st.success(f"Audit Complete for Clan: {clan.get('name')}")

            st.divider()
            st.markdown("### 🔍 Quick Member Inspector")
            role_map = {"admin": "Elder", "coLeader": "Co-Leader", "leader": "Leader", "member": "Member"}
            member_dict = {f"{m['name']} ({m['tag']}) - {role_map.get(m['role'], m['role'])}": m['tag'] for m in clan.get("memberList", [])}

            col_sel, col_btn = st.columns([3, 1])
            with col_sel: selected_member = st.selectbox("Select a Clan Member to investigate:", options=list(member_dict.keys()))
            with col_btn:
                st.write(""); st.write("")
                st.button(
                    "Inspect Profile",
                    width="stretch",
                    on_click=jump_to_player,
                    args=(member_dict[selected_member],)
                )
            st.divider()

            # --- ADDED PING-A-DONOR TAB HERE ---
            tab1, tab2, tab3, tab4 = st.tabs(["🚨 Slacker Report", "🛡️ Full Raid Roster", "⚔️ Recent War Log", "🎯 Ping-A-Donor"])
            
            with tab1:
                if not slacker_df.empty: st.dataframe(slacker_df.style.highlight_max(subset=["Violation"], color="#5c2b2b"), width="stretch", hide_index=True)
                else: st.write("✨ Incredible! Every single clan member showed up and finished their attacks.")
            
            with tab2:
                if not roster_df.empty: st.dataframe(roster_df, width="stretch", hide_index=True)
                else: st.write("No Raid data found.")
            
            with tab3:
                if not war_df.empty: st.dataframe(war_df, width="stretch", hide_index=True)
                else: st.write("War log is private or empty.")
            
            # --- PING-A-DONOR LOGIC ---
            with tab4:
                clan_lvl = clan.get('clanLevel', 1)
                boost = 2 if clan_lvl >= 10 else (1 if clan_lvl >= 5 else 0)
                st.markdown(f"### 🎯 Ping-A-Donor")
                st.caption(f"**Clan Level {clan_lvl}** | Active Donation Boost: **+{boost} Levels**")
                
                req_col1, req_col2, req_col3 = st.columns([2, 1, 1])
                with req_col1: unit_name = st.text_input("Unit Name (e.g., Yeti, Poison Spell, Log Launcher):")
                with req_col2: desired_lvl = st.number_input("Minimum Level:", min_value=1, value=1, step=1)
                with req_col3: 
                    st.write(""); st.write("")
                    is_max = st.checkbox("🔥 I just want MAX", value=False)
                
                if st.button("Search Donors", type="secondary"):
                    if unit_name:
                        member_list = clan.get("memberList", [])
                        with st.spinner(f"Scanning {len(member_list)} loadouts for {unit_name}..."):
                            tags = [m["tag"] for m in member_list]
                            df_donors = asyncio.run(run_ping_a_donor(tags, clan_lvl, unit_name, desired_lvl, is_max, COC_TOKEN))
                            
                            if not df_donors.empty:
                                st.success(f"Found {len(df_donors)} members who can donate your requested {unit_name}!")
                                st.dataframe(df_donors, width="stretch", hide_index=True)
                            else:
                                st.warning(f"Nobody in the clan can donate that level of {unit_name}. Time to recruit better players.")
                    else:
                        st.error("Please enter a troop, spell, or siege machine name.")import asyncio
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
