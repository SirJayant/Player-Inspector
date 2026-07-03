import asyncio
import pandas as pd
import streamlit as st
from clash_intel.models import process_player_inspector, process_clan_auditor, run_ping_a_donor
from clash_intel.ui.components import show_donation_modal

# ==========================================
#         PAGE CONFIG & SESSION STATE
# ==========================================
st.set_page_config(page_title="Clash Intel by VICTORIOUS", page_icon="🛡️", layout="wide")

# --- OPEN SOURCE BYOK TOKEN HANDLER ---
def get_api_token() -> str:
    if "COC_TOKEN" in st.secrets:
        return st.secrets["COC_TOKEN"]
    st.sidebar.markdown("### 🔑 API Access")
    st.sidebar.caption("Running in open-source mode. Enter your Supercell API token from developer.clashofclans.com.")
    return st.sidebar.text_input("Enter Token:", type="password")

COC_TOKEN = get_api_token()
if not COC_TOKEN:
    st.info("👋 **Welcome to Clash Intel by VICTORIOUS!**")
    st.markdown("To use this open-source dashboard safely without central server risks, enter your own Supercell Developer API Token in the sidebar.")
    st.stop()
# --------------------------------------

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

# ==========================================
#         GUI RENDERER (STREAMLIT)
# ==========================================
st.title("🛡️ Clash Intel by VICTORIOUS")

with st.sidebar:
    st.header("⚙️ Configuration")
    app_mode = st.radio(
        "Select Module:",
        ["🕵️ Player Inspector", "🏰 Clan & Raid Auditor"],
        key="app_mode"
    )

    st.divider()

    if st.button("⚡ Fund the Elixir Pipeline", use_container_width=True):
        show_donation_modal()

# ------------------------------------------
# MODULE 1: PLAYER INSPECTOR
# ------------------------------------------
if app_mode == "🕵️ Player Inspector":
    st.subheader("🕵️ Player Inspector")

    # FIXED: vertical_alignment locks button to bottom of input box
    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1: target_tag = st.text_input("Enter Player Tag:", key="target_player_tag", placeholder="#QYJ89QR")
    with col2: inspect_btn = st.button("Inspect Player", use_container_width=True, type="primary")

    if (inspect_btn or st.session_state.trigger_fetch) and target_tag:
        st.session_state.trigger_fetch = False
        with st.spinner("Infiltrating Supercell Servers..."):
            st.session_state.scanned_player = asyncio.run(process_player_inspector(target_tag, COC_TOKEN))

    if st.session_state.scanned_player:
        profile, eq_df, ranked_code, unranked_code, home_heroes, hero_sum, ranked_defenses, is_maintenance, error = st.session_state.scanned_player

        if error:
            st.error(error)
        else:
            st.success(f"Successfully located **{profile.get('name')}**!")

            if profile.get("clan"):
                st.info(f"🔰 **Clan Detected:** {profile['clan']['name']} ({profile['clan']['tag']})")
                st.button("Run Audit on this Clan", use_container_width=True, on_click=jump_to_clan, args=(profile['clan']['tag'],))

            st.markdown("#### 🏛️ Account Overview")
            t1_c1, t1_c2, t1_c3, t1_c4, t1_c5 = st.columns(5)
            t1_c1.metric("Town Hall", profile.get("townHallLevel"))
            t1_c2.metric("League", profile.get("league", {}).get("name", "Unranked"))
            t1_c3.metric("Trophies", profile.get("trophies"))
            t1_c4.metric("War Stars", f"⭐ {profile.get('warStars', 0)}")
            t1_c5.metric("Total Hero Power", f"⚡ {hero_sum}")

            st.markdown("#### 📊 Monthly Ledger")
            t2_c1, t2_c2, t2_c3, t2_c4, t2_c5 = st.columns(5)
            t2_c1.metric("Attack Wins", profile.get("attackWins", 0))
            t2_c2.metric("Defense Wins", profile.get("defenseWins", 0))

            donated = profile.get("donations", 0)
            received = profile.get("donationsReceived", 0)
            ratio = round(donated / received, 2) if received > 0 else donated
            t2_c3.metric("Troops Donated", donated)
            t2_c4.metric("Troops Received", received)
            t2_c5.metric("Donation Ratio", f"{ratio}x")

            if home_heroes:
                st.markdown("#### 👑 Hero Altar")
                h_cols = st.columns(len(home_heroes))
                for idx, h in enumerate(home_heroes):
                    h_cols[idx].metric(label=h["Name"], value=f"Lvl {h['Level']}", delta="TH MAX!" if h["IsMax"] else f"Cap: {h['TH_Max']}", delta_color="normal" if h["IsMax"] else "off")

            st.divider()

            st.markdown("#### ⚔️ Detected Offensive Armies")
            if ranked_code and unranked_code and (ranked_code == unranked_code):
                st.toast("One-trick pony alert! 🦄")
                st.info("😏 **Note:** This player runs the exact same strategy in Ranked matches and casual multiplayer. Consistency or lack of creativity? You decide.")

            arm_col1, arm_col2 = st.columns(2)
            with arm_col1:
                st.markdown("**🏆 Ranked / Legend Army**")
                if ranked_code:
                    st.success("Main strategy found!")
                    st.link_button("🔗 Copy Ranked Army", f"https://link.clashofclans.com/en?action=CopyArmy&army={ranked_code}", use_container_width=True)
                else:
                    st.warning("No recent Ranked/Legend offensive data.")

            with arm_col2:
                st.markdown("**🏡 Unranked (Farming/Multiplayer) Army**")
                if unranked_code:
                    st.success("Casual strategy found!")
                    st.link_button("🔗 Copy Unranked Army", f"https://link.clashofclans.com/en?action=CopyArmy&army={unranked_code}", use_container_width=True)
                else:
                    st.warning("No recent Unranked offensive data.")

            st.divider()

            st.markdown("#### 🛡️ Recent Ranked/Legend Defenses")
            if is_maintenance:
                st.info("ℹ️ Note: Log is currently empty. This often occurs during or immediately after a maintenance break.")

            if ranked_defenses:
                show_3star_only = st.checkbox("Filter: Show only 3-Star Defenses")
                df_defenses = pd.DataFrame(ranked_defenses)
                if show_3star_only:
                    df_defenses = df_defenses[df_defenses["Stars"] == 3]

                if not df_defenses.empty:
                    st.dataframe(df_defenses, column_config={"Army Link": st.column_config.LinkColumn("Copy Army", display_text="🔗 Copy"), "Tag": st.column_config.TextColumn("Player Tag")}, use_container_width=True, hide_index=True)

                    st.markdown("##### 🔎 Investigate Opponent")
                    # FIXED: vertical_alignment
                    col_tgt1, col_tgt2 = st.columns([3, 1], vertical_alignment="bottom")
                    with col_tgt1: target_opp = st.selectbox("Select opponent tag to inspect:", df_defenses["Tag"].unique())
                    with col_tgt2: st.button("Inspect Profile", on_click=jump_to_player, args=(target_opp,), use_container_width=True)
                else:
                    st.warning("No 3-star defenses found in the current logs.")
            elif not is_maintenance:
                st.warning("No recent defensive data found.")

            st.divider()

            if not eq_df.empty:
                st.write("### 🔨 Hero Equipment Loadout")
                st.dataframe(eq_df, use_container_width=True, hide_index=True)

# ------------------------------------------
# MODULE 2: CLAN & Raid Auditor
# ------------------------------------------
elif app_mode == "🏰 Clan & Raid Auditor":
    st.subheader("🏰 Clan & Raid Auditor")

    # FIXED: vertical_alignment
    col1, col2, col3 = st.columns([1, 2, 1], vertical_alignment="bottom")
    with col1: input_type = st.selectbox("Search By:", ["Clan Tag", "Player Tag"])
    with col2: target_tag = st.text_input("Enter Tag:", key="target_clan_tag", placeholder="#2RV082C9Y")
    with col3: audit_btn = st.button("Run Audit", use_container_width=True, type="primary")

    if (audit_btn or st.session_state.trigger_fetch) and target_tag:
        st.session_state.trigger_fetch = False
        with st.spinner("Compiling Ledgers..."):
            st.session_state.scanned_clan = asyncio.run(process_clan_auditor(target_tag, input_type, COC_TOKEN))

    if st.session_state.scanned_clan:
        clan, slacker_df, roster_df, war_df, clan_units, error = st.session_state.scanned_clan

        if error:
            st.error(error)
        else:
            st.success(f"Audit Complete for Clan: **{clan.get('name')}**")

            st.divider()
            st.markdown("### 🔍 Quick Member Inspector")
            role_map = {"admin": "Elder", "coLeader": "Co-Leader", "leader": "Leader", "member": "Member"}
            member_dict = {f"{m['name']} ({m['tag']}) - {role_map.get(m['role'], m['role'])}": m['tag'] for m in clan.get("memberList", [])}

            # FIXED: vertical_alignment
            col_sel, col_btn = st.columns([3, 1], vertical_alignment="bottom")
            with col_sel: selected_member = st.selectbox("Select a Clan Member to investigate:", options=list(member_dict.keys()))
            with col_btn: st.button("Inspect Profile", use_container_width=True, on_click=jump_to_player, args=(member_dict[selected_member],))
            st.divider()

            tab1, tab2, tab3, tab4 = st.tabs(["🚨 Slacker Report", "🛡️ Full Raid Roster", "⚔️ Recent War Log", "🎯 Ping-A-Donor"])

            with tab1:
                if not slacker_df.empty: st.dataframe(slacker_df.style.highlight_max(subset=["Violation"], color="#5c2b2b"), use_container_width=True, hide_index=True)
                else: st.write("✨ Incredible! Every single clan member showed up and finished their attacks.")

            with tab2:
                if not roster_df.empty: st.dataframe(roster_df, use_container_width=True, hide_index=True)
                else: st.write("No Raid data found.")

            with tab3:
                if not war_df.empty: st.dataframe(war_df, use_container_width=True, hide_index=True)
                else: st.write("War log is private or empty.")

            with tab4:
                clan_lvl = clan.get('clanLevel', 1)
                boost = 2 if clan_lvl >= 10 else (1 if clan_lvl >= 5 else 0)
                st.markdown(f"### 🎯 Ping-A-Donor")
                st.caption(f"**Clan Level {clan_lvl}** | Active Donation Boost: **+{boost} Levels**")

                # FIXED: vertical_alignment
                req_col1, req_col2, req_col3 = st.columns([2, 1, 1], vertical_alignment="bottom")
                with req_col1: unit_name = st.selectbox("Select Unit to Request:", options=clan_units if clan_units else ["No units found"])
                with req_col2: desired_lvl = st.number_input("Minimum Level:", min_value=1, value=1, step=1)
                with req_col3: is_max = st.checkbox("🔥 I just want MAX", value=False)

                if st.button("Search Donors", type="secondary"):
                    if unit_name and unit_name != "No units found":
                        member_list = clan.get("memberList", [])
                        with st.spinner(f"Scanning {len(member_list)} loadouts for {unit_name}..."):
                            tags = [m["tag"] for m in member_list]
                            df_donors = asyncio.run(run_ping_a_donor(tags, clan_lvl, unit_name, desired_lvl, is_max, COC_TOKEN))

                            if not df_donors.empty:
                                st.success(f"Found {len(df_donors)} members who can donate your requested {unit_name}!")
                                st.dataframe(df_donors, use_container_width=True, hide_index=True)
                            else:
                                st.warning(f"Nobody in the clan can donate that level of {unit_name}. Time to recruit better players.")
                    else:
                        st.error("Please enter a valid unit name.")
