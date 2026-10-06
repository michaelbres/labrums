"""Deterministic fake league in the exact shape the Sleeper API returns.

Used for local development without network access, for tests, and for the
`LABRUMS_DEMO=1` mode. Everything is seeded so results are stable.
"""
from __future__ import annotations

import random
from typing import Any

DEMO_LEAGUE_ID = "demo2026"
DEMO_PREV_LEAGUE_ID = "demo2025"

OWNERS = [
    ("Mike", "The Commish's Revenge"), ("Dan", "Dan With A Plan"), ("Jess", "Jess Gettin Started"),
    ("Tyler", "Tyler's Tires"), ("Ray", "Ray of Sunshine"), ("Sam", "Sam I Am"),
    ("Kyle", "Kyle's Kingdom"), ("Nina", "Nina's Ninjas"), ("Brett", "Brett's Threats"),
    ("Chris", "Crisis Mode"), ("Alex", "Alex The Great"), ("Jordan", "Air Jordan"),
]

FIRST = ["Josh", "Lamar", "Jalen", "Patrick", "Joe", "Bijan", "Saquon", "Derrick", "Jahmyr", "Breece",
         "Ja'Marr", "Justin", "CeeDee", "Tyreek", "Amon-Ra", "Puka", "Garrett", "Nico", "Travis", "Sam",
         "Trey", "George", "Mark", "Brock", "Jake", "Harrison", "Justin", "Cam", "Tua", "Dak",
         "Kyren", "Kenneth", "Chase", "Rachaad", "De'Von", "Drake", "Malik", "DK", "Davante", "Mike",
         "Brandon", "Jaylen", "Chris", "Tee", "Zay", "Rome", "Ladd", "Marvin", "Jayden", "Caleb"]
LAST = ["Allen", "Jackson", "Hurts", "Mahomes", "Burrow", "Robinson", "Barkley", "Henry", "Gibbs", "Hall",
        "Chase", "Jefferson", "Lamb", "Hill", "St. Brown", "Nacua", "Wilson", "Collins", "Kelce", "LaPorta",
        "McBride", "Kittle", "Andrews", "Bowers", "Ferguson", "Butker", "Tucker", "Dicker", "Tagovailoa", "Prescott",
        "Williams", "Walker", "Brown", "White", "Achane", "London", "Nabers", "Metcalf", "Adams", "Evans",
        "Aiyuk", "Waddle", "Olave", "Higgins", "Flowers", "Odunze", "McConkey", "Harrison", "Daniels", "Williams"]
NFL_TEAMS = ["KC", "BUF", "PHI", "SF", "DAL", "DET", "BAL", "CIN", "MIA", "GB", "NYJ", "LAR",
             "HOU", "JAX", "MIN", "ATL", "TB", "SEA", "LAC", "PIT", "CLE", "IND", "NO", "DEN",
             "LV", "ARI", "NYG", "CHI", "WAS", "NE", "CAR", "TEN"]

ROSTER_POSITIONS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF",
                    "BN", "BN", "BN", "BN", "BN", "BN", "IR"]
POS_TALENT = {"QB": (19, 6), "RB": (12, 7), "WR": (11, 7), "TE": (8, 6), "K": (8, 3), "DEF": (7, 6)}


def _make_players(rng: random.Random) -> dict[str, dict]:
    players: dict[str, dict] = {}
    pid = 1000
    counts = {"QB": 36, "RB": 70, "WR": 90, "TE": 36, "K": 30}
    for pos, n in counts.items():
        for _ in range(n):
            pid += 1
            players[str(pid)] = {
                "full_name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                "position": pos, "fantasy_positions": [pos],
                "team": rng.choice(NFL_TEAMS), "number": rng.randint(1, 99),
                "_talent": max(2.0, rng.gauss(*POS_TALENT[pos])),
                "_bye": rng.randint(5, 14),
            }
    for t in NFL_TEAMS:
        players[t] = {"full_name": None, "first_name": t, "last_name": "D/ST", "position": "DEF",
                      "fantasy_positions": ["DEF"], "team": t,
                      "_talent": max(2.0, rng.gauss(*POS_TALENT["DEF"])), "_bye": rng.randint(5, 14)}
    return players


def _weekly_points(rng: random.Random, p: dict, week: int) -> float:
    if week == p["_bye"]:
        return 0.0
    pos = p["position"]
    if pos == "DEF":
        pts = rng.gauss(p["_talent"], 7)
        return round(pts, 2)  # can be negative
    if pos == "K":
        return round(max(-1.0, rng.gauss(p["_talent"], 4)), 2)
    if rng.random() < 0.05:  # injured / dud
        return 0.0
    return round(max(0.0, rng.gauss(p["_talent"], p["_talent"] * 0.55)), 2)


def build_demo(season: str = "2026", league_id: str = DEMO_LEAGUE_ID, current_week: int = 7,
               seed: int = 7, status: str = "in_season", previous_league_id: str | None = DEMO_PREV_LEAGUE_ID,
               season_weeks: int = 14) -> dict[str, Any]:
    rng = random.Random(f"{seed}-{season}")
    players = _make_players(rng)
    n = len(OWNERS)
    users = [{"user_id": f"u{i+1}", "display_name": name, "avatar": None,
              "metadata": {"team_name": team}} for i, (name, team) in enumerate(OWNERS)]

    # Draft: snake-ish by position needs.
    pool = {pos: sorted([pid for pid, p in players.items() if p["position"] == pos],
                        key=lambda x: -players[x]["_talent"]) for pos in POS_TALENT}
    for pos in pool:
        # mild shuffle so drafts aren't perfectly ordered
        lst = pool[pos]
        for i in range(len(lst) - 1):
            if rng.random() < 0.3:
                lst[i], lst[i + 1] = lst[i + 1], lst[i]
    needs = ["QB", "RB", "RB", "WR", "WR", "TE", "K", "DEF", "RB", "WR", "WR", "RB", "TE", "QB", "WR"]
    rosters_players: list[list[str]] = [[] for _ in range(n)]
    order = list(range(n))
    for rnd, pos in enumerate(needs):
        seq = order if rnd % 2 == 0 else order[::-1]
        for ri in seq:
            if pool[pos]:
                rosters_players[ri].append(pool[pos].pop(0))

    def best_lineup(pids: list[str], week: int) -> tuple[list[str], dict[str, float]]:
        pts = {pid: _weekly_points(rng, players[pid], week) for pid in pids}
        # owners set lineups by talent, not by result (so duds/byes happen)
        by_pos: dict[str, list[str]] = {}
        for pid in pids:
            by_pos.setdefault(players[pid]["position"], []).append(pid)
        for pos in by_pos:
            by_pos[pos].sort(key=lambda x: -players[x]["_talent"])
            if rng.random() < 0.15:  # sometimes an owner forgets a bye player
                pass
        starters: list[str] = []
        used = set()
        for slot in ROSTER_POSITIONS:
            if slot in ("BN", "IR"):
                continue
            elig = ["RB", "WR", "TE"] if slot == "FLEX" else [slot]
            cands = [pid for pos in elig for pid in by_pos.get(pos, []) if pid not in used]
            if cands and not (slot == "K" and rng.random() < 0.03):
                pick = cands[0]
                used.add(pick)
                starters.append(pick)
            else:
                starters.append("0")
        return starters, pts

    # Schedule: round robin, repeating.
    def round_robin(teams: list[int]) -> list[list[tuple[int, int]]]:
        t = teams[:]
        weeks = []
        for _ in range(len(t) - 1):
            weeks.append([(t[i], t[-1 - i]) for i in range(len(t) // 2)])
            t = [t[0]] + [t[-1]] + t[1:-1]
        return weeks
    rr = round_robin(list(range(1, n + 1)))
    schedule = {w: rr[(w - 1) % len(rr)] for w in range(1, 18)}

    matchups: dict[int, list[dict]] = {}
    totals = {ri: {"w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0} for ri in range(1, n + 1)}
    last_week = season_weeks + 3  # playoffs weeks exist too
    for week in range(1, last_week + 1):
        rows = []
        for mid, (a, b) in enumerate(schedule[week], start=1):
            entry = {}
            for ri in (a, b):
                played = week < current_week
                if played:
                    starters, pts = best_lineup(rosters_players[ri - 1], week)
                    sp = [pts.get(s, 0.0) if s != "0" else 0.0 for s in starters]
                    total = round(sum(sp), 2)
                else:
                    starters = [s for s in rosters_players[ri - 1][:9]]
                    pts = {}
                    sp = [0.0] * len(starters)
                    total = 0.0
                entry[ri] = {"roster_id": ri, "matchup_id": mid if week <= season_weeks else None,
                             "points": total, "starters": starters, "starters_points": sp,
                             "players": rosters_players[ri - 1], "players_points": pts, "custom_points": None}
                rows.append(entry[ri])
            if week < current_week and week <= season_weeks:
                pa, pb = entry[a]["points"], entry[b]["points"]
                totals[a]["pf"] += pa; totals[a]["pa"] += pb
                totals[b]["pf"] += pb; totals[b]["pa"] += pa
                if pa > pb:
                    totals[a]["w"] += 1; totals[b]["l"] += 1
                elif pb > pa:
                    totals[b]["w"] += 1; totals[a]["l"] += 1
                else:
                    totals[a]["t"] += 1; totals[b]["t"] += 1
        matchups[week] = rows

    rosters = []
    for ri in range(1, n + 1):
        t = totals[ri]
        rosters.append({
            "roster_id": ri, "owner_id": f"u{ri}", "league_id": league_id,
            "players": rosters_players[ri - 1], "starters": matchups[1][0]["starters"] if False else rosters_players[ri - 1][:9],
            "reserve": [], "taxi": [],
            "settings": {"wins": t["w"], "losses": t["l"], "ties": t["t"],
                         "fpts": int(t["pf"]), "fpts_decimal": int(round((t["pf"] % 1) * 100)),
                         "fpts_against": int(t["pa"]), "fpts_against_decimal": int(round((t["pa"] % 1) * 100)),
                         "waiver_budget_used": rng.randint(0, 80), "waiver_position": ri, "total_moves": rng.randint(2, 20)},
            "metadata": {},
        })
        rosters[-1]["settings"]["division"] = 1 if ri % 2 else 2  # odd/even

    # Transactions: trades + waivers + free agents on completed weeks.
    transactions: dict[int, list[dict]] = {w: [] for w in range(1, last_week + 1)}
    free_agents = [pid for pid in players if not any(pid in rp for rp in rosters_players)]
    tid = 1
    for week in range(1, current_week):
        for _ in range(rng.randint(2, 4)):
            ri = rng.randint(1, n)
            add = rng.choice(free_agents)
            drop = rng.choice(rosters_players[ri - 1][9:]) if len(rosters_players[ri - 1]) > 9 else None
            ttype = "waiver" if rng.random() < 0.7 else "free_agent"
            transactions[week].append({
                "transaction_id": str(tid), "type": ttype, "status": "complete", "roster_ids": [ri],
                "adds": {add: ri}, "drops": ({drop: ri} if drop else None),
                "settings": ({"waiver_bid": rng.randint(1, 40)} if ttype == "waiver" else None),
                "created": 1_700_000_000_000 + week * 7 * 86_400_000, "leg": week, "draft_picks": [], "creator": f"u{ri}",
            })
            tid += 1
        if week in (2, 4, 6):
            a, b = rng.sample(range(1, n + 1), 2)
            ga = rng.sample(rosters_players[a - 1][:8], rng.randint(1, 2))
            gb = rng.sample(rosters_players[b - 1][:8], rng.randint(1, 2))
            adds = {**{p: b for p in ga}, **{p: a for p in gb}}
            drops = {**{p: a for p in ga}, **{p: b for p in gb}}
            transactions[week].append({
                "transaction_id": str(tid), "type": "trade", "status": "complete", "roster_ids": [a, b],
                "adds": adds, "drops": drops, "settings": None, "draft_picks": [],
                "created": 1_700_000_000_000 + week * 7 * 86_400_000 + 3600_000, "leg": week, "creator": f"u{a}",
            })
            tid += 1

    # Offseason transactions: Sleeper tags them all leg 1, stamped before the season start.
    # Uses its own RNG so the fixture above is unchanged. Includes a commissioner move and a failed trade.
    orng = random.Random(f"{seed}-{season}-offseason")
    off_base = 1_700_000_000_000 - 13 * 86_400_000  # 2023-11-01, before season_start_date
    for k in range(5):
        a, b = orng.sample(range(1, n + 1), 2)
        ga = orng.sample(rosters_players[a - 1][:8], orng.randint(1, 3 if k == 0 else 1))
        gb = orng.sample(rosters_players[b - 1][:8], orng.randint(1, 2 if k == 0 else 1))
        picks = [{"round": 1, "season": str(int(season) + 1), "league_id": None, "roster_id": a, "owner_id": b,
                  "previous_owner_id": a}] if k % 2 == 0 else []
        transactions[1].append({
            "transaction_id": f"off{tid}", "type": "trade", "status": "complete" if k < 4 else "failed",
            "roster_ids": [a, b], "adds": {**{p: b for p in ga}, **{p: a for p in gb}},
            "drops": {**{p: a for p in ga}, **{p: b for p in gb}}, "settings": None, "draft_picks": picks,
            "created": off_base + k * 3600_000, "leg": 1, "creator": f"u{a}"})
        tid += 1
    for k in range(6):
        ri = orng.randint(1, n)
        transactions[1].append({
            "transaction_id": f"off{tid}", "type": "waiver" if k % 2 else "free_agent", "status": "complete",
            "roster_ids": [ri], "adds": {orng.choice(free_agents): ri}, "drops": None,
            "settings": None, "created": off_base + (10 + k) * 3600_000, "leg": 1, "draft_picks": [], "creator": f"u{ri}"})
        tid += 1
    transactions[1].append({
        "transaction_id": f"off{tid}", "type": "commissioner", "status": "complete", "roster_ids": [1],
        "adds": {orng.choice(free_agents): 1}, "drops": None, "settings": None,
        "created": off_base + 20 * 3600_000, "leg": 1, "draft_picks": [], "creator": "u1"})
    tid += 1

    league = {
        "league_id": league_id, "name": "Labrums Demo League", "season": season, "season_type": "regular",
        "status": status, "sport": "nfl", "total_rosters": n, "roster_positions": ROSTER_POSITIONS,
        "previous_league_id": previous_league_id, "draft_id": "draft-demo", "avatar": None,
        "metadata": {"division_1": "Odds", "division_2": "Evens"},
        "settings": {"playoff_teams": 6, "playoff_week_start": season_weeks + 1, "num_teams": n, "leg": current_week,
                     "last_scored_leg": current_week - 1, "playoff_type": 0, "playoff_seed_type": 0, "divisions": 2,
                     "waiver_type": 2, "waiver_budget": 100},
        "scoring_settings": {"rec": 0.5, "pass_td": 4, "rush_td": 6, "rec_td": 6},
    }
    state = {"week": current_week, "leg": current_week, "season": season, "season_type": "regular",
             "display_week": current_week, "league_season": season, "previous_season": str(int(season) - 1),
             "season_start_date": "2023-11-20"}  # in-season demo transactions are stamped after this date
    public_players = {pid: {k: v for k, v in p.items() if not k.startswith("_")} for pid, p in players.items()}
    return {"league": league, "users": users, "rosters": rosters, "matchups": matchups,
            "transactions": transactions, "players": public_players, "state": state}


class DemoClient:
    """Same interface as SleeperClient, served from build_demo()."""

    def __init__(self, current_week: int = 7):
        self.current_week = current_week
        self._cur = build_demo("2026", DEMO_LEAGUE_ID, current_week=current_week)
        self._prev = build_demo("2025", DEMO_PREV_LEAGUE_ID, current_week=18, seed=3,
                                status="complete", previous_league_id=None)
        self._leagues = {DEMO_LEAGUE_ID: self._cur, DEMO_PREV_LEAGUE_ID: self._prev}

    def _l(self, league_id: str) -> dict | None:
        return self._leagues.get(league_id)

    def state(self) -> dict:
        return self._cur["state"]

    def league(self, league_id: str):
        d = self._l(league_id)
        return d["league"] if d else None

    def rosters(self, league_id: str):
        d = self._l(league_id)
        return d["rosters"] if d else []

    def users(self, league_id: str):
        d = self._l(league_id)
        return d["users"] if d else []

    def matchups(self, league_id: str, week: int, final: bool = False):
        d = self._l(league_id)
        return d["matchups"].get(week, []) if d else []

    def transactions(self, league_id: str, week: int, final: bool = False):
        d = self._l(league_id)
        return d["transactions"].get(week, []) if d else []

    def winners_bracket(self, league_id: str):
        return []

    def clear_cache(self, keep_players: bool = True, league_id: str | None = None) -> None:
        pass

    def players(self):
        return self._cur["players"]
