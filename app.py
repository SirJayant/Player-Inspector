import asyncio
import pandas as pd
import streamlit as st
from clash_intel.models import process_player_inspector, process_clan_auditor, run_ping_a_donor
from clash_intel.ui.components import show_donation_modal

# ==========================================
#         PAGE CONFIG & SESSION STATE
# ==========================================
st.set_page_config(page_title="Clash Intel by VICTORIOUS", page_icon="🛡️", layout="wide")

# --- CUSTOM CSS FOR METRIC CARDS, FONTS & HEROES ---
st.markdown("""
<style>
    @font-face {
        font-family: 'SupercellMagic';
        src: url('https://cdn.jsdelivr.net/gh/YunYouJun/coc@master/assets/fonts/Supercell-Magic_5.ttf') format('truetype');
    }
    
    .sc-font {
        font-family: 'SupercellMagic', sans-serif;
        letter-spacing: 1px;
        text-shadow: 2px 2px 0px #000;
    }

    .card-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 25px;
    }
    .stat-card {
        flex: 1 1 calc(20% - 15px);
        min-width: 140px;
        background: linear-gradient(180deg, #2a3342, #1a202c);
        border: 2px solid #4a5568;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.6);
        transition: transform 0.2s ease;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .stat-card:hover {
        transform: translateY(-4px);
        border-color: #718096;
    }
    .stat-img {
        height: 70px;
        object-fit: contain;
        margin-bottom: 10px;
        filter: drop-shadow(0px 4px 4px rgba(0,0,0,0.6));
    }
    .stat-title {
        font-size: 0.85rem;
        color: #cbd5e1;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 8px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .stat-value {
        font-size: 1.5rem;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }
    .hero-card {
        flex: 1 1 calc(16.6% - 15px);
        min-width: 120px;
        background: linear-gradient(180deg, #374151, #1f2937);
        border: 2px solid #4b5563;
        border-radius: 12px;
        padding: 15px 10px;
        text-align: center;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.6);
    }
    .hero-name {
        font-size: 0.8rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .hero-lvl {
        font-size: 1.4rem;
        color: #fbbf24;
    }
    .hero-cap {
        font-size: 0.75rem;
        margin-top: 4px;
        color: #94a3b8;
    }
    .hero-cap-max {
        font-size: 0.75rem;
        margin-top: 4px;
        color: #4ade80;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

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
        profile, eq_df, ranked_code, unranked_code, home_heroes, hero_sum, ranked_defenses, ranked_attacks, is_maintenance, has_only_old_logs, error = st.session_state.scanned_player

        if error:
            st.error(error)
        else:
            st.success(f"Successfully located **{profile.get('name')}**!")

            if profile.get("clan"):
                st.info(f"🔰 **Clan Detected:** {profile['clan']['name']} ({profile['clan']['tag']})")
                st.button("Run Audit on this Clan", use_container_width=True, on_click=jump_to_clan, args=(profile['clan']['tag'],))

            # --- DYNAMIC ASSET URLS ---
            th_level = profile.get("townHallLevel", 1)
            league = profile.get("league", {})
            league_name = league.get("name", "Unranked")
            
            # Keep only the League Icon as an image since the API provides it reliably
            league_icon = league.get("iconUrls", {}).get("medium", "https://clashofclans.fandom.com/wiki/Special:FilePath/Unranked_League_Icon.png")
            war_stars = profile.get('warStars', 0)

            # --- NEW UI: ACCOUNT OVERVIEW ---
            st.markdown("<h4 class='sc-font'>🏛️ Account Overview</h4>", unsafe_allow_html=True)
            
            # Restored Emojis for everything else, merged Town Hall into one massive block
            overview_html = (
                f'<div class="card-grid">'
                f'<div class="stat-card"><div class="stat-value sc-font" style="text-align: center; flex-wrap: wrap;">TOWN HALL {th_level}</div></div>'
                f'<div class="stat-card"><img src="{league_icon}" class="stat-img" alt="League" onerror="this.style.display=\'none\'"><div class="stat-title">League</div><div class="stat-value sc-font" style="font-size:1.1rem;">{league_name}</div></div>'
                f'<div class="stat-card"><div class="stat-title">Trophies</div><div class="stat-value sc-font">{profile.get("trophies")}🏆</div></div>'
                f'<div class="stat-card"><div class="stat-title">War Stars</div><div class="stat-value sc-font">{war_stars}⭐</div></div>'
                f'<div class="stat-card"><div class="stat-title">Total Hero Power</div><div class="stat-value sc-font">{hero_sum}⚡</div></div>'
                f'</div>'
            )
            st.markdown(overview_html, unsafe_allow_html=True)

            # --- NEW UI: MONTHLY LEDGER ---
            st.markdown("<h4 class='sc-font'>📊 Monthly Ledger</h4>", unsafe_allow_html=True)
            donated = profile.get("donations", 0)
            received = profile.get("donationsReceived", 0)
            ratio = round(donated / received, 2) if received > 0 else donated
            
            ledger_html = (
                f'<div class="card-grid">'
                f'<div class="stat-card"><div class="stat-title">Attack Wins</div><div class="stat-value sc-font" style="font-size:1.8rem; color:#4ade80;">{profile.get("attackWins", 0)}</div></div>'
                f'<div class="stat-card"><div class="stat-title">Defense Wins</div><div class="stat-value sc-font" style="font-size:1.8rem; color:#38bdf8;">{profile.get("defenseWins", 0)}</div></div>'
                f'<div class="stat-card"><div class="stat-title">Troops Donated</div><div class="stat-value sc-font" style="font-size:1.8rem;">{donated}</div></div>'
                f'<div class="stat-card"><div class="stat-title">Troops Received</div><div class="stat-value sc-font" style="font-size:1.8rem;">{received}</div></div>'
                f'<div class="stat-card"><div class="stat-title">Donation Ratio</div><div class="stat-value sc-font" style="font-size:1.8rem; color:#fbbf24;">{ratio}x</div></div>'
                f'</div>'
            )
            st.markdown(ledger_html, unsafe_allow_html=True)

            # --- NEW UI: HERO ALTAR ---
            if home_heroes:
                st.markdown("<h4 class='sc-font'>👑 Hero Altar</h4>", unsafe_allow_html=True)
                heroes_html = '<div class="card-grid">'
                for h in home_heroes:
                    cap_class = "hero-cap-max" if h["IsMax"] else "hero-cap"
                    cap_text = "TH MAX!" if h["IsMax"] else f"Cap: {h['TH_Max']}"
                    
                    heroes_html += f'<div class="hero-card"><div class="hero-name">{h["Name"]}</div><div class="hero-lvl sc-font">Lvl {h["Level"]}</div><div class="{cap_class}">{cap_text}</div></div>'
                
                heroes_html += '</div>'
                st.markdown(heroes_html, unsafe_allow_html=True)

            st.divider()

            # ==========================================
            #   RANKED UI REMAINS UNTOUCHED BELOW THIS
            # ==========================================
            st.markdown("#### ⚔️ Detected Offensive Armies")
            if ranked_code and unranked_code and (ranked_code == unranked_code):
                st.toast("Boring player alert!")
                st.info("😏 **Note:** This player runs the exact same strategy in Ranked matches and casual multiplayer. Consistency or lack of creativity? You decide, but this player doesn't farm efficiently for sure.")

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

            if is_maintenance:
                st.info("🧹 **Server Scrub!** The Supercell goblins recently wiped the battle logs (usually due to a maintenance break). We gotta wait for this player to drop some troops before we can steal their intel!")
            elif has_only_old_logs:
                st.warning("⏳ **Outdated Intel!** This player has not taken participation in the new tournament yet. The logs we found are from before the Monday morning reset (10:30 AM IST). We are only seeing old ghosts!")
            elif not ranked_attacks and not ranked_defenses:
                st.info("🧹 **Empty Ledger!** We couldn't find any recent Ranked or Legend league battles for this player.")
            else:
                st.caption("🕵️ **Intel Note: Supercell’s servers have the memory span of a goldfish. This ledger only shows recent skirmishes, not your target’s lifetime history. We don’t log past attacks, so take a breather, you can't stalk what isnt there**")

            def render_stars(star_count):
                filled = "★" * star_count
                empty = "☆" * (3 - star_count)
                return f"<span style='color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); letter-spacing: 1px;'>{filled}{empty}</span>"

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
                
                return f"background: {bg}; color: black; border-radius: 4px; padding: 6px 8px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; border: 1px solid {border}; font-family: sans-serif; font-size: 0.9em;"

            def get_link_button(link):
                if link:
                    return f'<a href="{link}" target="_blank" style="text-decoration: none; color: black; background: rgba(255,255,255,0.4); padding: 2px 6px; border-radius: 4px; font-size: 0.85em; border: 1px solid rgba(0,0,0,0.4); white-space: nowrap;">🔗 Copy</a>'
                return '<span style="font-size: 0.85em; opacity: 0.5; white-space: nowrap;">Hidden</span>'

            total_atk_trophies = sum(atk.get("Trophies", 0) for atk in ranked_attacks) if ranked_attacks else 0
            total_def_trophies = sum(def_rec.get("Trophies", 0) for def_rec in ranked_defenses) if ranked_defenses else 0

            log_col1, log_col2 = st.columns(2)

            with log_col1:
                st.markdown(f"**Attacks** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **+{total_atk_trophies} 🏆**")
                atk_html = ""
                for atk in ranked_attacks:
                    row_style = get_row_style(is_attack=True, stars=atk['Stars'])
                    link_btn = get_link_button(atk.get('Army Link'))
                    
                    atk_html += f"""
                    <div style="{row_style}">
                        <div title="{atk['Name']}" style="font-weight: bold; flex: 1 1 auto; min-width: 0; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{atk['Name']}</div>
                        <div style="flex: 0 0 auto; white-space: nowrap; text-align: center; min-width: 60px;">{atk['Destruction']} {render_stars(atk['Stars'])}</div>
                        <div style="font-weight: bold; flex: 0 0 auto; white-space: nowrap; text-align: right; min-width: 45px;">+{atk.get('Trophies', 0)} 🏆</div>
                        <div style="flex: 0 0 auto; white-space: nowrap; text-align: right;">{link_btn}</div>
                    </div>
                    """
                if atk_html:
                    st.markdown(atk_html, unsafe_allow_html=True)
                if not ranked_attacks and not is_maintenance and not has_only_old_logs:
                    st.info("No recent attacks found. Are they slacking? Or.... they attacked so early the server forgot? Check trophies above, thankfully we have that info accurate.")

            with log_col2:
                st.markdown(f"**Defenses** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **+{total_def_trophies} 🏆**")
                def_html = ""
                for dfns in ranked_defenses:
                    row_style = get_row_style(is_attack=False, stars=dfns['Stars'])
                    link_btn = get_link_button(dfns.get('Army Link'))
                    
                    def_html += f"""
                    <div style="{row_style}">
                        <div title="{dfns['Name']}" style="font-weight: bold; flex: 1 1 auto; min-width: 0; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{dfns['Name']}</div>
                        <div style="flex: 0 0 auto; white-space: nowrap; text-align: center; min-width: 60px;">{dfns['Destruction']} {render_stars(dfns['Stars'])}</div>
                        <div style="font-weight: bold; flex: 0 0 auto; white-space: nowrap; text-align: right; min-width: 45px;">+{dfns.get('Trophies', 0)} 🏆</div>
                        <div style="flex: 0 0 auto; white-space: nowrap; text-align: right;">{link_btn}</div>
                    </div>
                    """
                if def_html:
                    st.markdown(def_html, unsafe_allow_html=True)
                if not ranked_defenses and not is_maintenance and not has_only_old_logs:
                    st.info("No recent defenses found. Flying under the radar!")

            st.divider()

            # Symmetrical Inspectors Row below Battle Logs
            inv_col1, inv_col2 = st.columns(2)

            with inv_col1:
                if ranked_attacks:
                    st.markdown("##### 🔎 Investigate Opponent")
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
