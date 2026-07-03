import asyncio
import streamlit as st
import pandas as pd
from clash_intel.client import ClashAPIClient
from clash_intel.models import parse_player_assets, process_defensive_log, get_smart_army_code
from clash_intel.ui.components import show_donation_modal

st.set_page_config(page_title="Clash Intel", page_icon="🛡️", layout="wide")

# --- CUSTOM CREDENTIAL DISCOVERY LAYER ---
def resolve_api_token() -> str:
    if "COC_TOKEN" in st.secrets:
        return st.secrets["COC_TOKEN"]

    st.sidebar.markdown("### 🔑 API Access Configuration")
    st.sidebar.caption("Provide an authorized access key from developer.clashofclans.com to interface with production nodes locally.")
    return st.sidebar.text_input("Supercell Token Entry", type="password")

auth_token = resolve_api_token()

if not auth_token:
    st.info("💡 **Developer Key Required**")
    st.markdown(
        "To verify security integrity and remain open-source, this framework requires users to present their own API context. "
        "Please provide your proxy-authorized token within the sidebar panel to proceed initialization."
    )
    st.stop()

# Instantiate runtime environment client
api = ClashAPIClient(token=auth_token)

# --- SYSTEM STATE RETENTION ---
if "app_mode" not in st.session_state: st.session_state.app_mode = "🕵️ Player Inspector"
if "target_player_tag" not in st.session_state: st.session_state.target_player_tag = ""
if "target_clan_tag" not in st.session_state: st.session_state.target_clan_tag = ""
if "trigger_fetch" not in st.session_state: st.session_state.trigger_fetch = False
if "scanned_player" not in st.session_state: st.session_state.scanned_player = None
if "scanned_clan" not in st.session_state: st.session_state.scanned_clan = None

def route_to_clan(clan_tag):
    st.session_state.target_clan_tag = clan_tag
    st.session_state.app_mode = "🏰 Clan & Raid Auditor"
    st.session_state.trigger_fetch = True
    st.session_state.scanned_player = None

def route_to_player(player_tag):
    st.session_state.target_player_tag = player_tag
    st.session_state.app_mode = "🕵️ Player Inspector"
    st.session_state.trigger_fetch = True
    st.session_state.scanned_clan = None

# --- LAYOUT NAVIGATION ---
st.title("🛡️ Clash Intel Dashboard")

with st.sidebar:
    st.header("Navigation Modules")
    app_mode = st.radio("Select Active Module:", ["🕵️ Player Inspector", "🏰 Clan & Raid Auditor"], key="app_mode")
    st.divider()
    if st.button("Project Maintenance Support", use_container_width=True):
        show_donation_modal()

# --- MODULE EXECUTION PIPELINES ---
if app_mode == "🕵️ Player Inspector":
    st.subheader("Player Profile Inspection Engine")

    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1: target_tag = st.text_input("Target Player Tag:", key="target_player_tag", placeholder="#QYJ89QR")
    with col2: inspect_btn = st.button("Query Profile Data", use_container_width=True, type="primary")

    if (inspect_btn or st.session_state.trigger_fetch) and target_tag:
        st.session_state.trigger_fetch = False
        with st.spinner("Querying API node targets..."):
            profile, err = asyncio.run(api.get_player_profile(target_tag))
            if err:
                st.error(err)
            else:
                log_data, _ = asyncio.run(api.get_player_battlelog(target_tag))
                st.session_state.scanned_player = (profile, log_data)

    if st.session_state.scanned_player:
        profile, log_data = st.session_state.scanned_player
        eq_df, home_heroes, hero_sum = parse_player_assets(profile)
        ranked_code, unranked_code, ranked_defenses, is_maintenance = process_defensive_log(log_data)

        st.success(f"Record Active: **{profile.get('name')}**")
        if profile.get("clan"):
            st.info(f"🔰 **Affiliated Association:** {profile['clan']['name']} ({profile['clan']['tag']})")
            st.button("Execute Auditor Pipeline on Clan", use_container_width=True, on_click=route_to_clan, args=(profile['clan']['tag'],))

        st.markdown("#### Account Status Metrics")
        t1_c1, t1_c2, t1_c3, t1_c4, t1_c5 = st.columns(5)
        t1_c1.metric("Town Hall Level", profile.get("townHallLevel"))
        t1_c2.metric("Current League", profile.get("league", {}).get("name", "Unranked"))
        t1_c3.metric("Trophy Volume", profile.get("trophies"))
        t1_c4.metric("Accumulated War Stars", f"⭐ {profile.get('warStars', 0)}")
        t1_c5.metric("Aggregate Hero Level", f"⚡ {hero_sum}")

        if home_heroes:
            st.markdown("#### Hero Progression Array")
            h_cols = st.columns(len(home_heroes))
            for idx, h in enumerate(home_heroes):
                h_cols[idx].metric(label=h["Name"], value=f"Lvl {h['Level']}", delta="Max Standard" if h["IsMax"] else f"Cap: {h['TH_Max']}", delta_color="normal" if h["IsMax"] else "off")

        st.divider()
        st.markdown("#### Army Configuration Offense Links")
        arm_col1, arm_col2 = st.columns(2)
        with arm_col1:
            st.markdown("**Competitive/Legend Standard Strategy**")
            if ranked_code:
                st.link_button("Copy High-Tier Layout", f"https://link.clashofclans.com/en?action=CopyArmy&army={ranked_code}", use_container_width=True)
            else:
                st.warning("No high-tier system records found.")
        with arm_col2:
            st.markdown("**Standard Multiplayer Strategy**")
            if unranked_code:
                st.link_button("Copy General Layout", f"https://link.clashofclans.com/en?action=CopyArmy&army={unranked_code}", use_container_width=True)
            else:
                st.warning("No standard system records found.")

        if not eq_df.empty:
            st.divider()
            st.markdown("#### Active Hero Subsystem Upgrades")
            st.dataframe(eq_df, use_container_width=True, hide_index=True)

# --- CLAN STRUCTURAL AUDITING MODULE ---
elif app_mode == "🏰 Clan & Raid Auditor":
    st.subheader("Clan Infrastructure Auditor")

    col1, col2, col3 = st.columns([1, 2, 1], vertical_alignment="bottom")
    with col1: target_type = st.selectbox("Search Context:", ["Clan Tag", "Player Tag"])
    with col2: context_tag = st.text_input("Enter Tag Context:", key="target_clan_tag", placeholder="#2RV082C9Y")
    with col3: audit_btn = st.button("Execute Core Audit", use_container_width=True, type="primary")

    if (audit_btn or st.session_state.trigger_fetch) and context_tag:
        st.session_state.trigger_fetch = False
        with st.spinner("Processing structural network maps..."):
            resolved_clan_tag = context_tag
            if target_type == "Player Tag":
                p_data, err = asyncio.run(api.get_player_profile(context_tag))
                if not err and p_data.get("clan"):
                    resolved_clan_tag = p_data["clan"]["tag"]
                else:
                    st.error("Failed to map target player to a valid clan node identifier.")
                    st.stop()

            clan_data, err = asyncio.run(api.get_clan_data(resolved_clan_tag))
            if err:
                st.error(err)
            else:
                st.session_state.scanned_clan = clan_data

    if st.session_state.scanned_clan:
        clan = st.session_state.scanned_clan
        st.success(f"Audit Target Confirmed: **{clan.get('name')}**")
        st.dataframe(pd.DataFrame(clan.get("memberList", []))[["name", "tag", "role", "expLevel"]], use_container_width=True, hide_index=True)
