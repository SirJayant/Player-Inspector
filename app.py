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

def get_name_tag_dict(df):
    if "Name" in df.columns:
        return {f"{row['Name']} ({row['Tag']})": row["Tag"] for _, row in df.iterrows()}
    return {row["Tag"]: row["Tag"] for _, row in df.iterrows()}

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

    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1: target_tag = st.text_input("Enter Player Tag:", key="target_player_tag", placeholder="#QYJ89QR")
    with col2: inspect_btn = st.button("Inspect Player", use_container_width=True, type="primary")

    if (inspect_btn or st.session_state.trigger_fetch) and target_tag:
        st.session_state.trigger_fetch = False
        with st.spinner("Infiltrating Supercell Servers..."):
            st.session_state.scanned_player = asyncio.run(process_player_inspector(target_tag, COC_TOKEN))

    if st.session_state.scanned_player:
        profile, eq_df, ranked_code, unranked_code, home_heroes, hero_sum, ranked_defenses, ranked_attacks, is_maintenance, error = st.session_state.scanned_player

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

            # --- CUSTOM BATTLE LOG UI ---
            st.markdown(f"### 🛡️ Battle Log: {profile.get('name')} | Total: {profile.get('trophies')} 🏆")

            if is_maintenance or (not ranked_attacks and not ranked_defenses):
                st.info("🧹 **Server Scrub!** The Supercell goblins recently wiped the battle logs (usually due to a maintenance break). We gotta wait for this player to drop some troops before we can steal their intel!")
            else:
                st.caption("🕵️ **Intel Note:** Supercell's servers have a short memory. This ledger only reflects the most recent skirmishes, not the entire season's history. What you see here is just the tip of the iceberg!")

            def render_stars(star_count):
                filled = "★" * star_count
                empty = "☆" * (3 - star_count)
                return f"<span style='color: white; text-shadow: 1px 1px 2px black;'>{filled}{empty}</span>"

            def get_row_style(is_attack, stars):
                gold_bg = "linear-gradient(to right, #f4d068, #e8a838)"
                gold_border = "#c98c1c"
                
                grey_bg = "linear-gradient(to right, #e0e0e0, #b8b8b8)"
                grey_border = "#9e9e9e"
                
                red_bg = "linear-gradient(to right, #f4a298, #e36a6a)"
                red_border = "#b74b4b"

                if is_attack:
                    if stars == 3:
                        bg, border = gold_bg, gold_border
                    elif stars > 0:
                        bg, border = grey_bg, grey_border
                    else:
                        bg, border = red_bg, red_border
                else:
                    if stars == 3:
                        bg, border = red_bg, red_border
                    elif stars > 0:
                        bg, border = grey_bg, grey_border
                    else:
                        bg, border = gold_bg, gold_border
                
                return f"background: {bg}; color: black; border-radius: 4px; padding: 6px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid {border}; font-family: sans-serif;"

            total_atk_trophies = sum(atk.get("Trophies", 0) for atk in ranked_attacks) if ranked_attacks else 0
            total_def_trophies = sum(def_rec.get("Trophies", 0) for def_rec in ranked_defenses) if ranked_defenses else 0

            log_col1, log_col2 = st.columns(2)

            with log_col1:
                st.markdown(f"**Attacks** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **+{total_atk_trophies} 🏆**")
                atk_html = ""
                for atk in ranked_attacks:
                    row_style = get_row_style(is_attack=True, stars=atk['Stars'])
                    atk_html += f"""
                    <div style="{row_style}">
                        <div style="font-weight: bold; width: 40%; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{atk['Name']}</div>
                        <div style="width: 35%; text-align: center;">{atk['Destruction']} {render_stars(atk['Stars'])}</div>
                        <div style="font-weight: bold; width: 25%; text-align: right;">+{atk.get('Trophies', 0)} 🏆</div>
                    </div>
                    """
                if atk_html:
                    st.markdown(atk_html, unsafe_allow_html=True)
                if not ranked_attacks and not is_maintenance:
                    st.info("No recent attacks found. Are they slacking?")

            with log_col2:
                st.markdown(f"**Defenses** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **+{total_def_trophies} 🏆**")
                def_html = ""
                for dfns in ranked_defenses:
                    row_style = get_row_style(is_attack=False, stars=dfns['Stars'])
                    def_html += f"""
                    <div style="{row_style}">
                        <div style="font-weight: bold; width: 40%; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{dfns['Name']}</div>
                        <div style="width: 35%; text-align: center;">{dfns['Destruction']} {render_stars(dfns['Stars'])}</div>
                        <div style="font-weight: bold; width: 25%; text-align: right;">+{dfns.get('Trophies', 0)} 🏆</div>
                    </div>
                    """
                if def_html:
                    st.markdown(def_html, unsafe_allow_html=True)
                if not ranked_defenses and not is_maintenance:
                    st.info("No recent defenses found. Flying under the radar!")

            st.divider()

            # Symmetrical Inspectors Row below Battle Logs
            inv_col1, inv_col2 = st.columns(2)

            with inv_col1:
                if ranked_attacks:
                    st.markdown("##### 🔎 Investigate Defender")
                    df_attacks = pd.DataFrame(ranked_attacks)
                    attacker_dict = get_name_tag_dict(df_attacks)
                    
                    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
                    with c1:
                        target_def_key = st.selectbox("Select defender to inspect:", list(attacker_dict.keys()), key="sel_atk")
                    with c2:
                        st.button("Inspect Profile", on_click=jump_to_player, args=(attacker_dict[target_def_key],), key="btn_atk", use_container_width=True)

            with inv_col2:
                if ranked_defenses:
                    st.markdown("##### 🔎 Investigate Attacker")
                    df_defenses = pd.DataFrame(ranked_defenses)
                    defender_dict = get_name_tag_dict(df_defenses)
                    
                    c3, c4 = st.columns([3, 1], vertical_alignment="bottom")
                    with c3:
                        target_opp_key = st.selectbox("Select attacker to inspect:", list(defender_dict.keys()), key="sel_def")
                    with c4:
                        st.button("Inspect Profile", on_click=jump_to_player, args=(defender_dict[target_opp_key],), key="btn_def", use_container_width=True)

            st.divider()

            if not eq_df.empty:
                st.write("### 🔨 Hero Equipment Loadout")
                st.dataframe(eq_df, use_container_width=True, hide_index=True)

# ------------------------------------------
# MODULE 2: CLAN & Raid Auditor
# ------------------------------------------
elif app_mode == "🏰 Clan & Raid Auditor":
    st.subheader("🏰 Clan & Raid Auditor")

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
