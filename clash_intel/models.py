import re
import collections
import pandas as pd
from typing import List, Optional, Dict, Any, Tuple
from clash_intel.constants import SUPER_TROOP_MAP, PET_NAMES, get_th_hero_max

def get_smart_army_code(share_codes: List[str]) -> Optional[str]:
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

def parse_player_assets(profile: Dict[str, Any]) -> Tuple[pd.DataFrame, list, int]:
    th_level = profile.get("townHallLevel", 1)

    equipment = []
    for eq in profile.get("heroEquipment", []):
        if eq.get("village") == "home":
            equipment.append({
                "Equipment": eq["name"], "Level": eq["level"], "Max Level": eq["maxLevel"],
                "Status": "MAXED" if eq["level"] == eq["maxLevel"] else "Upgrading"
            })
    eq_df = pd.DataFrame(equipment).sort_values(by="Level", ascending=False) if equipment else pd.DataFrame()

    home_heroes = []
    hero_sum = 0
    for h in profile.get("heroes", []):
        if h.get("village") == "home" and h["name"] not in PET_NAMES:
            hero_sum += h["level"]
            th_max = get_th_hero_max(h["name"], th_level, h["maxLevel"])
            home_heroes.append({
                "Name": h["name"], "Level": h["level"], "TH_Max": th_max, "IsMax": (h["level"] >= th_max)
            })

    return eq_df, home_heroes, hero_sum

def process_defensive_log(battle_log: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], list, bool]:
    if not battle_log or "items" not in battle_log:
        return None, None, [], False

    is_maintenance = (len(battle_log["items"]) == 0)
    ranked_offensive = []
    unranked_offensive = []
    ranked_defenses = []

    for item in battle_log["items"]:
        code = item.get("armyShareCode")
        if code and item.get("attack"):
            if item.get("battleType") in ["ranked", "legend"]:
                ranked_offensive.append(code)
            else:
                unranked_offensive.append(code)

    ranked_code = get_smart_army_code(ranked_offensive)
    unranked_code = get_smart_army_code(unranked_offensive)

    for item in reversed(battle_log["items"]):
        if item.get("battleType") in ["ranked", "legend"] and not item.get("attack"):
            code = item.get("armyShareCode")
            ranked_defenses.append({
                "Opponent": item.get("opponentName", "Unknown"),
                "Tag": item.get("opponentPlayerTag", ""),
                "TH": item.get("opponentTownHallLevel", ""),
                "Stars": item.get("stars", 0),
                "Destruction": f"{item.get('destructionPercentage', 0)}%",
                "Type": str(item.get("battleType")).capitalize(),
                "Army Link": f"https://link.clashofclans.com/en?action=CopyArmy&army={code}" if code else None
            })

    return ranked_code, unranked_code, ranked_defenses, is_maintenance
