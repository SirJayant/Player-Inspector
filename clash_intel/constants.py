SUPER_TROOP_MAP = {
    "super barbarian": "barbarian", "super archer": "archer", "sneaky goblin": "goblin",
    "super giant": "giant", "super wall breaker": "wall breaker", "rocket balloon": "balloon",
    "super balloon": "balloon", "super wizard": "wizard", "super dragon": "dragon",
    "inferno dragon": "baby dragon", "super minion": "minion", "super valkyrie": "valkyrie",
    "super witch": "witch", "ice hound": "lava hound", "super bowler": "bowler",
    "super miner": "miner", "super hog rider": "hog rider"
}

PET_NAMES = {
    "L.A.S.S.I", "Mighty Yak", "Electro Owl", "Unicorn",
    "Diggy", "Poison Lizard", "Phoenix", "Spirit Fox", "Angry Jelly"
}

HERO_TH_CAPS = {
    "Barbarian King": {4: 1, 5: 1, 6: 1, 7: 10, 8: 20, 9: 30, 10: 40, 11: 50, 12: 65, 13: 75, 14: 80, 15: 90, 16: 95, 17: 100},
    "Archer Queen": {9: 30, 10: 40, 11: 50, 12: 65, 13: 75, 14: 80, 15: 90, 16: 95, 17: 100},
    "Grand Warden": {11: 20, 12: 40, 13: 50, 14: 55, 15: 65, 16: 70, 17: 75},
    "Royal Champion": {13: 25, 14: 30, 15: 40, 16: 45, 17: 50},
    "Minion Prince": {9: 10, 10: 20, 11: 30, 12: 40, 13: 50, 14: 60, 15: 70, 16: 80, 17: 90},
    "Dragon Duke": {15: 10, 16: 15, 17: 20}
}

def get_th_hero_max(hero_name, th_level, global_max):
    caps = HERO_TH_CAPS.get(hero_name, {})
    if th_level in caps: return caps[th_level]
    if th_level > max(caps.keys(), default=0): return global_max
    return global_max
