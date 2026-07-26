import asyncio
import collections
import urllib.parse
import re
import math
import aiohttp
import pandas as pd
from datetime import datetime, timezone, timedelta
from clash_intel.constants import SUPER_TROOP_MAP, PET_NAMES, get_th_hero_max

BASE_URL = "https://cocproxy.royaleapi.dev/v1"

def format_tag(tag):
    tag = tag.strip().upper()
    if not tag.startswith("#"): tag = "#" + tag
    return urllib.parse.quote(tag)

def get_last_tournament_start_utc():
    """Returns the datetime of the most recent Monday at 05:00 UTC (10:30 AM IST)."""
    now = datetime.now(timezone.utc)
    days_since_monday = now.weekday() # Monday is 0
    
    this_monday_start = (now - timedelta(days=days_since_monday)).replace(
        hour=5, minute=0, second=0, microsecond=0
    )
    
    # If today is Monday but we haven't hit 10:30 AM IST yet, the tournament hasn't ended.
    # Therefore, the "start" of the active tournament was actually the previous week.
    if now < this_monday_start:
        return this_monday_start - timedelta(days=7)
        
    return this_monday_start

def parse_coc_time(time_str: str):
    """Parses Supercell API timestamp '20260722T103543.000Z' into timezone-aware UTC datetime."""
    try:
        return datetime.strptime(time_str, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)

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

def get_smart_army_code(share_codes):
    if not share_codes:
        return None
    strategy_groups = collections.defaultdict(list)
    for code in share_codes:
        u_match = re.search(r'u([0-9x\-]+)', code)
        s_match = re.search(r's([0-9x\-]+)', code)
        u_str = u_match.group(1) if u_match else ""
        s_str = s_match.group(1) if s_match else ""
        combined_str = f"{u_str}-{s_str}".strip('-')
        items = [item for item in combined_str.split('-') if 'x' in item]
        ids = set()
        total_weight = 0
        for item in items:
            parts = item.split('x')
            if len(parts) == 2:
                try:
                    count = int(parts[0])
                    unit_id = int(parts[1])
                    ids.add(unit_id)
                    total_weight += count
                except ValueError:
                    continue
        if ids:
            fingerprint = frozenset(ids)
            strategy_groups[fingerprint].append((total_weight, code))
    if not strategy_groups:
        return collections.Counter(share_codes).most_common(1)[0][0]
    best_fingerprint = max(
        strategy_groups.keys(),
        key=lambda f: (len(strategy_groups[f]), sum(w for w, c in strategy_groups[f]))
    )
    return max(strategy_groups[best_fingerprint], key=lambda x: x[0])[1]

def calculate_trophies(stars: int, destruction: int) -> tuple[int, int]:
    """Calculates attacker (t_a) and defender (t_d) trophies strictly based on Ranked mechanics."""
    D = max(0, min(100, int(destruction)))
    stars = int(stars)
    
    if stars == 3:
        t_a = 40
    elif stars == 2:
        t_a = 16 + math.floor((D - 50) / 3)
    elif stars == 1:
        t_a = 5 + math.floor((D - 1) / 9)
    else:  # 0 stars
        t_a = math.floor(D / 10) if D >= 10 else 0
        t_a = min(4, t_a)
        
    if stars > 0:
        t_d = 40 - t_a
    else:
        t_d = 40
        
    return t_a, t_d

async def process_player_inspector(tag, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        profile_data, error = await fetch_api(session, f"players/{format_tag(tag)}", headers)
        if error: return None, None, None, None, None, None, None, None, False, False, error

        th_level = profile_data.get("townHallLevel", 1)

        equipment_list = []
        for eq in profile_data.get("heroEquipment", []):
            if eq.get("village") == "home":
                equipment_list.append({
                    "Equipment": eq["name"], "Level": eq["level"], "Max Level": eq["maxLevel"],
                    "Status": "🔥 MAXED" if eq["level"] == eq["maxLevel"] else "Upgrading"
                })
        eq_df = pd.DataFrame(equipment_list).sort_values(by="Level", ascending=False) if equipment_list else pd.DataFrame()

        home_heroes = []
        hero_sum = 0
        for h in profile_data.get("heroes", []):
            if h.get("village") == "home" and h["name"] not in PET_NAMES:
                hero_sum += h["level"]
                th_max = get_th_hero_max(h["name"], th_level, h["maxLevel"])
                home_heroes.append({
                    "Name": h["name"], "Level": h["level"], "TH_Max": th_max, "IsMax": (h["level"] >= th_max)
                })

        battle_log, _ = await fetch_api(session, f"players/{format_tag(tag)}/battlelog", headers)

        is_maintenance = (battle_log is not None and "items" in battle_log and len(battle_log["items"]) == 0)
        has_only_old_logs = False
        ranked_code = None
        unranked_code = None
        ranked_defenses = []
        ranked_attacks = []

        if battle_log and "items" in battle_log:
            ranked_offensive_codes = []
            unranked_offensive_codes = []
            
            tournament_start_utc = get_last_tournament_start_utc()
            old_logs_found = 0

            for item in battle_log["items"]:
                if item.get("armyShareCode") and item.get("attack"):
                    b_type = item.get("battleType")
                    if b_type in ["ranked", "legend"]:
                        ranked_offensive_codes.append(item.get("armyShareCode"))
                    else:
                        unranked_offensive_codes.append(item.get("armyShareCode"))

            if ranked_offensive_codes:
                ranked_code = get_smart_army_code(ranked_offensive_codes)
            if unranked_offensive_codes:
                unranked_code = get_smart_army_code(unranked_offensive_codes)

            for item in reversed(battle_log["items"]):
                if item.get("battleType") in ["ranked", "legend"]:
                    
                    # Intercept and block old tournament battles using the correct JSON key
                    battle_time_str = item.get("battleTimestamp")
                    if battle_time_str:
                        battle_time = parse_coc_time(battle_time_str)
                        if battle_time < tournament_start_utc:
                            old_logs_found += 1
                            continue # Skip processing this battle
                            
                    code = item.get("armyShareCode")
                    stars = item.get("stars", 0)
                    destruction = item.get("destructionPercentage", 0)
                    
                    # Compute trophies
                    t_a, t_d = calculate_trophies(stars, destruction)
                    is_attack = item.get("attack", True)

                    record = {
                        "Name": item.get("opponentName", "Unknown"),
                        "Tag": item.get("opponentPlayerTag", ""),
                        "TH": item.get("opponentTownHallLevel", ""),
                        "Stars": stars,
                        "Destruction": f"{destruction}%",
                        "Type": str(item.get("battleType")).capitalize(),
                        "Army Link": f"https://link.clashofclans.com/en?action=CopyArmy&army={code}" if code else None,
                        "Trophies": t_a if is_attack else t_d
                    }
                    
                    if is_attack:
                        ranked_attacks.append(record)
                    else:
                        ranked_defenses.append(record)
                        
            # If we found logs, but they were all completely filtered out due to being old
            if old_logs_found > 0 and len(ranked_attacks) == 0 and len(ranked_defenses) == 0:
                has_only_old_logs = True

        return profile_data, eq_df, ranked_code, unranked_code, home_heroes, hero_sum, ranked_defenses, ranked_attacks, is_maintenance, has_only_old_logs, None

async def process_clan_auditor(tag, input_type, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        if input_type == "Player Tag":
            player_data, err = await fetch_api(session, f"players/{format_tag(tag)}", headers)
            if err or not player_data.get("clan"): return None, None, None, None, None, "Could not resolve player to a clan."
            clan_tag = player_data["clan"]["tag"]
        else:
            clan_tag = tag

        clan_data, err = await fetch_api(session, f"clans/{format_tag(clan_tag)}", headers)
        if err: return None, None, None, None, None, err
        master_roster = clan_data.get("memberList", [])

        top_3_tags = [m["tag"] for m in sorted(master_roster, key=lambda x: x.get("expLevel", 0), reverse=True)[:3]]
        profile_tasks = [fetch_player_profile(session, t, headers) for t in top_3_tags]
        top_profiles = await asyncio.gather(*profile_tasks)

        live_clan_units = set()
        for p in top_profiles:
            if not p: continue
            for item in p.get("troops", []) + p.get("spells", []):
                if item.get("village") == "home" and item["name"] not in PET_NAMES:
                    live_clan_units.add(item["name"])
        sorted_clan_units = sorted(list(live_clan_units))

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

        return clan_data, slacker_df, roster_df, war_df, sorted_clan_units, None

async def run_ping_a_donor(member_tags, clan_level, unit_name, desired_level, is_max, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_player_profile(session, tag, headers) for tag in member_tags]
        profiles = await asyncio.gather(*tasks)

    level_boost = 2 if clan_level >= 10 else (1 if clan_level >= 5 else 0)
    eligible_players = []
    unit_name_lower = unit_name.lower().strip()
    search_unit_name = SUPER_TROOP_MAP.get(unit_name_lower, unit_name_lower)

    for p in profiles:
        if not p: continue
        inventory = p.get("troops", []) + p.get("spells", [])
        for item in inventory:
            if item["name"].lower() == search_unit_name and item.get("village") == "home":
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
                        "Donations (Season)": p.get("donations", 0),
                        "Is Max?": "🔥 MAX" if effective_level >= max_possible else "No"
                    })
                break

    if eligible_players:
        return pd.DataFrame(eligible_players).sort_values(by=["Donations (Season)", "Base Level"], ascending=[False, False])
    return pd.DataFrame()
