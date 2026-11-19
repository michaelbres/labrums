"""Our own dynasty player valuation model and the league power rankings built on it.

Pure functions over already-loaded data (see loader.load_power). Every tunable number is a named constant
below. Units: a "value" is roughly "points per game above a replacement player, summed over the next few
seasons with an age discount" (a prime starter is worth ~20-40, a replacement player 0).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from .sleeper import player_label

# ---- tunable constants ----------------------------------------------------------------------------------
POSITIONS = ("QB", "RB", "WR", "TE")
SEASON_WEIGHTS = (0.55, 0.30, 0.15)          # current season, -1, -2
FULL_SEASON_GAMES = 17
PRIOR_GAMES = 4.0                            # shrink toward replacement PPG as if worth this many games
REPLACEMENT_RANK = {"QB": 30, "RB": 30, "WR": 40, "TE": 12}   # Nth best at the position across the NFL
MIN_EFF_GAMES = 4.0                          # weighted games needed to count when finding replacement level
LONGEVITY_YEARS = 5
LONGEVITY_DISCOUNT = 0.8                     # per year into the future
PRIME_END = {"RB": 26, "WR": 28, "TE": 29, "QB": 33}          # age curve is 1.0 up to here ...
CLIFF = {"RB": 31, "WR": 33, "TE": 34, "QB": 39}              # ... and falls linearly to 0 here
DEFAULT_AGE = 26                             # when Sleeper has neither age nor years_exp
ROOKIE_AGE = 22                              # fallback age = this + years_exp
CURVE_FALLBACK = (14.0, 0.145)               # a * exp(-b * slot), used when there is too little draft history
CURVE_MIN_SAMPLES = 30
CURVE_B_RANGE = (0.002, 0.8)
ROOKIE_MAX_ROUNDS = 5                        # drafts with more rounds are startup drafts
DEFAULT_ROUNDS = 4
YOUNG_MAX_YEARS_EXP = 2                      # prior applies to players with <= this many years of experience
CAREER_GAMES_HALF = 17.0                     # w = games / (games + this): trust in production vs. draft slot
PICK_YEAR_DISCOUNT = 0.9                     # per year until that draft
FUTURE_SEASONS = 3                           # how many drafts ahead Sleeper lets teams trade picks
CURVE_REPORT_SLOTS = (1, 5, 10, 20, 30, 40)


def constants() -> dict[str, Any]:
    return {"season_weights": list(SEASON_WEIGHTS), "prior_games": PRIOR_GAMES, "replacement_rank": dict(REPLACEMENT_RANK),
            "longevity_years": LONGEVITY_YEARS, "longevity_discount": LONGEVITY_DISCOUNT,
            "prime_end": dict(PRIME_END), "cliff": dict(CLIFF), "pick_year_discount": PICK_YEAR_DISCOUNT,
            "career_games_half": CAREER_GAMES_HALF, "young_max_years_exp": YOUNG_MAX_YEARS_EXP}


# ---- production -------------------------------------------------------------------------------------------
def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def season_games_possible(season_stats: dict) -> float:
    """Games a full-time player could have in this (possibly unfinished) season: the max games anyone has."""
    mx = max((_f(v.get("gp")) for v in (season_stats or {}).values()), default=0.0)
    return min(float(FULL_SEASON_GAMES), mx) if mx > 0 else float(FULL_SEASON_GAMES)


def blend_ppg(lines: list[tuple[float, float, float, float]], replacement: float | None = None) -> tuple[float, float]:
    """Blend per-season PPG. `lines` = (ppg, games played, games possible, season weight).

    Each season counts weight * 17 * (gp / possible) "games", so a thin sample counts less. With `replacement`,
    PRIOR_GAMES of replacement-level PPG are added. Returns (blended ppg, effective weighted games)."""
    num = tot = 0.0
    for ppg, gp, possible, w in lines:
        if gp <= 0 or possible <= 0:
            continue
        eff = w * FULL_SEASON_GAMES * min(gp, possible) / possible
        num += eff * ppg
        tot += eff
    if replacement is None:
        return (num / tot if tot > 0 else 0.0), tot
    return (num + PRIOR_GAMES * replacement) / (tot + PRIOR_GAMES), tot


def replacement_levels(raw: dict[str, tuple[str, float, float]]) -> dict[str, float]:
    """raw: pid -> (position, unshrunk blended ppg, effective games). Replacement = PPG of the Nth best."""
    out = {}
    for pos in POSITIONS:
        vals = sorted((p for (q, p, g) in raw.values() if q == pos and g >= MIN_EFF_GAMES), reverse=True)
        n = REPLACEMENT_RANK[pos]
        out[pos] = vals[n - 1] if len(vals) >= n else (vals[-1] if vals else 0.0)
    return out


def vorp(blended: float, replacement: float) -> float:
    return max(0.0, blended - replacement)


def age_curve(pos: str, age: float) -> float:
    prime, cliff = PRIME_END[pos], CLIFF[pos]
    if age <= prime:
        return 1.0
    if age >= cliff:
        return 0.0
    return (cliff - age) / (cliff - prime)


def longevity(pos: str, age: float) -> float:
    return sum(LONGEVITY_DISCOUNT ** t * age_curve(pos, age + t) for t in range(LONGEVITY_YEARS))


def player_age(p: dict) -> float:
    if p.get("age") is not None:
        return _f(p["age"], DEFAULT_AGE)
    if p.get("years_exp") is not None:
        return ROOKIE_AGE + _f(p["years_exp"])
    return float(DEFAULT_AGE)


def compute_production(players: dict[str, dict], stats: dict[str, dict], current_season: str,
                       include: set[str] | frozenset = frozenset()) -> tuple[dict[str, dict], dict[str, float]]:
    """stats: season -> pid -> {gp, pts_half_ppr}. Returns (pid -> production row, replacement by position)."""
    cur = int(current_season)
    order = [str(cur - i) for i in range(len(SEASON_WEIGHTS))]
    possible = {s: season_games_possible(stats.get(s) or {}) for s in order}
    pids = set(include)
    for s in order:
        pids.update((stats.get(s) or {}).keys())
    lines: dict[str, list] = {}
    pos_of: dict[str, str] = {}
    for pid in pids:
        pos = (players.get(pid) or {}).get("position")
        if pos not in POSITIONS:
            continue
        pos_of[pid] = pos
        ls = []
        for s, w in zip(order, SEASON_WEIGHTS):
            row = (stats.get(s) or {}).get(pid)
            gp = _f((row or {}).get("gp"))
            if row and gp > 0:
                ls.append((_f(row.get("pts_half_ppr")) / gp, gp, possible[s], w))
        lines[pid] = ls
    raw = {}
    for pid, ls in lines.items():
        b, g = blend_ppg(ls)
        raw[pid] = (pos_of[pid], b, g)
    repl = replacement_levels(raw)
    out = {}
    for pid, ls in lines.items():
        pos = pos_of[pid]
        blended, eff = blend_ppg(ls, repl[pos])
        v = vorp(blended, repl[pos])
        age = player_age(players.get(pid) or {})
        lng = longevity(pos, age)
        games = sum(g for (_, g, _, _) in ls)
        out[pid] = {"pos": pos, "ppg": blended, "vorp": v, "age": age, "longevity": lng, "games": games,
                    "production": v * lng}
    return out, repl


# ---- rookie pick curve ------------------------------------------------------------------------------------
def fit_pick_curve(samples: list[tuple[float, float]]) -> dict[str, Any]:
    """Least-squares a * exp(-b * slot) over (slot, value) samples; falls back to constants on thin data."""
    fb = {"a": CURVE_FALLBACK[0], "b": CURVE_FALLBACK[1], "source": "fallback", "n": len(samples)}
    if len(samples) < CURVE_MIN_SAMPLES:
        return fb
    s = np.array([x[0] for x in samples], dtype=float)
    v = np.array([x[1] for x in samples], dtype=float)
    if not np.any(v > 0):
        return fb
    best = None
    for b in np.linspace(CURVE_B_RANGE[0], CURVE_B_RANGE[1], 800):
        e = np.exp(-b * s)
        a = float((v * e).sum() / (e * e).sum())
        sse = float(((v - a * e) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, a, float(b))
    if best is None or best[1] <= 0:
        return fb
    return {"a": best[1], "b": best[2], "source": "fit", "n": len(samples)}


def curve_value(curve: dict, slot: float) -> float:
    return curve["a"] * math.exp(-curve["b"] * slot)


def is_rookie_draft(d: dict) -> bool:
    return d.get("status", "complete") == "complete" and 0 < int(d.get("rounds") or 0) <= ROOKIE_MAX_ROUNDS


def rookie_samples(drafts: list[dict], production: dict[str, dict], current_season: str) -> list[tuple[float, float]]:
    """(overall slot, production value today of the player taken) from rookie drafts at least a season old."""
    out = []
    for d in drafts:
        if not is_rookie_draft(d) or int(d["season"]) >= int(current_season):
            continue
        for pk in d.get("picks") or []:
            if pk.get("player_id") and pk.get("pick_no"):
                out.append((float(pk["pick_no"]), (production.get(str(pk["player_id"])) or {}).get("production", 0.0)))
    return out


def draft_slots(drafts: list[dict], current_season: str) -> dict[str, float]:
    """pid -> overall slot in the league's most recent rookie draft that took them."""
    slots: dict[str, float] = {}
    for d in sorted((x for x in drafts if is_rookie_draft(x) and int(x["season"]) <= int(current_season)),
                    key=lambda x: int(x["season"])):
        for pk in d.get("picks") or []:
            if pk.get("player_id") and pk.get("pick_no"):
                slots[str(pk["player_id"])] = float(pk["pick_no"])
    return slots


def player_values(production: dict[str, dict], players: dict[str, dict], slots: dict[str, float],
                  curve: dict) -> dict[str, float]:
    """Production value, with young league-drafted players blended toward their draft-slot prior."""
    out = {}
    for pid, row in production.items():
        val = row["production"]
        ye = (players.get(pid) or {}).get("years_exp")
        if pid in slots and ye is not None and _f(ye, 99) <= YOUNG_MAX_YEARS_EXP:
            w = row["games"] / (row["games"] + CAREER_GAMES_HALF)
            val = w * val + (1 - w) * curve_value(curve, slots[pid])
        out[pid] = val
    return out


# ---- future picks -----------------------------------------------------------------------------------------
def future_seasons(drafts: list[dict], traded: list[dict], current_season: str) -> list[str]:
    done = [int(d["season"]) for d in drafts if is_rookie_draft(d)]
    last = max(done) if done else int(current_season) - 1
    top = max([last + FUTURE_SEASONS] + [int(t["season"]) for t in traded if t.get("season")])
    return [str(y) for y in range(last + 1, top + 1)]


def pick_owners(traded: list[dict], roster_ids: list[int], seasons: list[str], rounds: int) -> dict[tuple, int]:
    """(season, round, original roster) -> current owner roster. A pick listed several times (traded on) ends
    with the owner who never appears as a later entry's previous owner; for a cycle (traded away and back) the
    last listed entry wins."""
    groups: dict[tuple, list[dict]] = {}
    for t in traded:
        if str(t.get("season")) in seasons and t.get("round") and t.get("roster_id") is not None:
            groups.setdefault((str(t["season"]), int(t["round"]), int(t["roster_id"])), []).append(t)
    owners = {}
    known = set(roster_ids)
    for s in seasons:
        for r in range(1, rounds + 1):
            for rid in roster_ids:
                owners[(s, r, rid)] = rid
    for key, es in groups.items():
        if key not in owners:
            continue
        prevs = {int(e["previous_owner_id"]) for e in es if e.get("previous_owner_id") is not None}
        cands = [e for e in es if e.get("owner_id") is not None and int(e["owner_id"]) not in prevs]
        final = (cands or es)[-1]
        if final.get("owner_id") is not None and int(final["owner_id"]) in known:
            owners[key] = int(final["owner_id"])
    return owners


def projected_slot(rnd: int, original: int, order_worst_first: list[int], n: int, is_next: bool,
                   snake: bool = False) -> float:
    """Overall slot: the next draft follows the (worst-first) order; later drafts get the middle of the round."""
    pos = order_worst_first.index(original) + 1 if is_next and original in order_worst_first else (n + 1) / 2
    if snake and rnd % 2 == 0:
        pos = n + 1 - pos
    return (rnd - 1) * n + pos


# ---- team tables ------------------------------------------------------------------------------------------
RANK_KEYS = ("QB", "RB", "WR", "TE", "players", "picks", "combined")


def _ranks(values: dict[int, dict]) -> dict[int, dict]:
    out: dict[int, dict] = {rid: {} for rid in values}
    for k in RANK_KEYS:
        for i, rid in enumerate(sorted(values, key=lambda r: (-values[r][k], r))):
            out[rid][k] = i + 1
    return out


def build_power_rankings(rosters: dict[int, dict], players: dict[str, dict], stats: dict[str, dict],
                         drafts: list[dict], traded: list[dict], standings: list[int],
                         current_season: str) -> dict[str, Any]:
    """rosters: roster_id -> {name, team_name, avatar, players: [pid]} (taxi/reserve included in players)."""
    rostered = {str(p) for t in rosters.values() for p in t.get("players") or [] if p not in (None, "", "0")}
    production, repl = compute_production(players, stats, current_season, include=rostered)
    samples = rookie_samples(drafts, production, current_season)
    curve = fit_pick_curve(samples)
    slots = draft_slots(drafts, current_season)
    values = player_values(production, players, slots, curve)

    rids = sorted(rosters)
    n = len(rids)
    rookie = sorted((d for d in drafts if is_rookie_draft(d)), key=lambda d: int(d["season"]))
    rounds = int(rookie[-1]["rounds"]) if rookie else DEFAULT_ROUNDS
    snake = bool(rookie) and rookie[-1].get("type") == "snake"
    fut = future_seasons(drafts, traded, current_season)
    order = [r for r in reversed([r for r in standings if r in rosters])] if standings else []
    order = order + [r for r in rids if r not in order]   # worst first; unlisted teams last
    owners = pick_owners(traded, rids, fut, rounds)

    team_rows: dict[int, dict] = {}
    player_rows = []
    for rid in rids:
        t = rosters[rid]
        by_pos = {p: 0.0 for p in POSITIONS}
        for pid in t.get("players") or []:
            pid = str(pid)
            v = values.get(pid)
            if v is None:
                continue
            by_pos[production[pid]["pos"]] += v
            if v > 0:
                lab = player_label(players, pid)
                player_rows.append({"player_id": pid, "name": lab["name"], "position": production[pid]["pos"],
                                    "nfl_team": lab["team"], "age": players.get(pid, {}).get("age"),
                                    "years_exp": players.get(pid, {}).get("years_exp"),
                                    "value": v, "roster_id": rid, "owner": t.get("name")})
        team_rows[rid] = {"pos": by_pos, "picks": []}
    for (s, r, orig), owner in sorted(owners.items()):
        slot = projected_slot(r, orig, order, n, s == fut[0], snake)
        yrs = max(0, int(s) - int(current_season))
        team_rows[owner]["picks"].append({
            "season": s, "round": r, "original_roster_id": orig, "original": rosters[orig].get("name"),
            "traded": orig != owner, "slot": slot, "value": curve_value(curve, slot) * PICK_YEAR_DISCOUNT ** yrs})

    vals = {}
    for rid, tr in team_rows.items():
        tot = sum(tr["pos"].values())
        picks = sum(p["value"] for p in tr["picks"])
        vals[rid] = {**tr["pos"], "players": tot, "picks": picks, "combined": tot + picks}
    ranks = _ranks(vals)

    player_rows.sort(key=lambda p: (-p["value"], p["name"], p["player_id"]))
    seen: dict[str, int] = {}
    for i, p in enumerate(player_rows):
        seen[p["position"]] = seen.get(p["position"], 0) + 1
        p["rank"], p["pos_rank"] = i + 1, seen[p["position"]]
        p["value"] = round(p["value"], 1)

    teams = []
    for rid in sorted(rids, key=lambda r: ranks[r]["combined"]):
        t = rosters[rid]
        picks = sorted(team_rows[rid]["picks"], key=lambda p: (int(p["season"]), p["round"], p["slot"]))
        for p in picks:
            p["value"], p["slot"] = round(p["value"], 1), round(p["slot"], 1)
        teams.append({"roster_id": rid, "name": t.get("name"), "team_name": t.get("team_name"), "avatar": t.get("avatar"),
                      "values": {k: round(v, 1) for k, v in vals[rid].items()}, "ranks": ranks[rid], "picks": picks})
    return {
        "season": str(current_season), "teams": teams, "players": player_rows,
        "curve": {"a": curve["a"], "b": curve["b"], "source": curve["source"], "samples": curve["n"],
                  "values": {str(s): round(curve_value(curve, s), 1) for s in CURVE_REPORT_SLOTS}},
        "future_seasons": fut, "rounds": rounds, "next_draft_order": order,
        "replacement": {k: round(v, 2) for k, v in repl.items()}, "constants": constants(),
    }
