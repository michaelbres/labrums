"""Standings, per-team stats, league records, head-to-head, optimal lineups."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .sleeper import player_label

FLEX_ELIGIBILITY = {
    "FLEX": {"RB", "WR", "TE"},
    "WRRB_FLEX": {"RB", "WR"},
    "REC_FLEX": {"WR", "TE"},
    "SUPER_FLEX": {"QB", "RB", "WR", "TE"},
    "IDP_FLEX": {"DL", "LB", "DB"},
}
NON_STARTING = {"BN", "IR", "TAXI"}


def games_by_week(ctx: dict) -> dict[int, list[dict]]:
    """Pair matchup rows into games: {week: [{a, b, a_pts, b_pts, matchup_id}]}."""
    out: dict[int, list[dict]] = {}
    for week, rows in ctx["matchups"].items():
        by_mid: dict[Any, list[dict]] = defaultdict(list)
        for r in rows:
            if r.get("matchup_id") is None:
                continue
            by_mid[r["matchup_id"]].append(r)
        games = []
        for mid, pair in sorted(by_mid.items(), key=lambda kv: str(kv[0])):
            if len(pair) != 2:
                continue
            a, b = sorted(pair, key=lambda r: int(r["roster_id"]))
            games.append({"week": week, "matchup_id": mid,
                          "a": int(a["roster_id"]), "b": int(b["roster_id"]),
                          "a_pts": float(a.get("points") or 0), "b_pts": float(b.get("points") or 0)})
        if games:
            out[week] = games
    return out


def _player_pos(players: dict, pid: str) -> set[str]:
    p = players.get(str(pid)) or {}
    fp = p.get("fantasy_positions") or ([p["position"]] if p.get("position") else [])
    if not fp and isinstance(pid, str) and pid.isalpha():
        fp = ["DEF"]
    return set(fp)


def optimal_lineup_points(ctx: dict, row: dict) -> float:
    """Best possible score from the full roster that week (greedy by slot scarcity)."""
    players = ctx["players"]
    slots = [s for s in ctx["roster_positions"] if s not in NON_STARTING]
    pts = {str(pid): float(v) for pid, v in (row.get("players_points") or {}).items()}
    if not pts:
        return float(row.get("points") or 0)
    avail = sorted(pts, key=lambda p: -pts[p])
    used: set[str] = set()
    total = 0.0
    fixed = [s for s in slots if s not in FLEX_ELIGIBILITY]
    flex = sorted((s for s in slots if s in FLEX_ELIGIBILITY), key=lambda s: len(FLEX_ELIGIBILITY[s]))
    for slot in fixed:
        for pid in avail:
            if pid in used:
                continue
            if slot in _player_pos(players, pid):
                used.add(pid); total += pts[pid]; break
    for slot in flex:
        elig = FLEX_ELIGIBILITY[slot]
        for pid in avail:
            if pid in used:
                continue
            if _player_pos(players, pid) & elig:
                used.add(pid); total += pts[pid]; break
    return round(total, 2)


def _streak(results: list[str]) -> str:
    if not results:
        return "—"
    last = results[-1]
    n = 0
    for r in reversed(results):
        if r == last:
            n += 1
        else:
            break
    return f"{last}{n}"


def compute(ctx: dict) -> dict[str, Any]:
    teams = ctx["teams"]
    players = ctx["players"]
    games = games_by_week(ctx)
    last_completed = ctx["last_completed"]
    reg_weeks = set(ctx["regular_weeks"])

    scores: dict[int, dict[int, float]] = {rid: {} for rid in teams}        # rid -> week -> pts
    results: dict[int, list[str]] = {rid: [] for rid in teams}
    opp: dict[int, dict[int, int]] = {rid: {} for rid in teams}
    h2h: dict[int, dict[int, dict]] = {rid: defaultdict(lambda: {"w": 0, "l": 0, "t": 0}) for rid in teams}
    div_rec: dict[int, dict[str, int]] = {rid: {"w": 0, "l": 0, "t": 0} for rid in teams}
    completed_games: list[dict] = []
    for week in sorted(games):
        if week > last_completed:
            continue
        for g in games[week]:
            a, b = g["a"], g["b"]
            scores[a][week] = g["a_pts"]; scores[b][week] = g["b_pts"]
            opp[a][week] = b; opp[b][week] = a
            if g["a_pts"] > g["b_pts"]:
                ra, rb = "W", "L"
            elif g["b_pts"] > g["a_pts"]:
                ra, rb = "L", "W"
            else:
                ra = rb = "T"
            g = dict(g, winner=(a if ra == "W" else b if rb == "W" else None),
                     margin=round(abs(g["a_pts"] - g["b_pts"]), 2), regular=week in reg_weeks)
            completed_games.append(g)
            if week in reg_weeks:
                results[a].append(ra); results[b].append(rb)
                h2h[a][b]["w" if ra == "W" else "l" if ra == "L" else "t"] += 1
                h2h[b][a]["w" if rb == "W" else "l" if rb == "L" else "t"] += 1
                da, db = teams[a].get("division"), teams[b].get("division")
                if da is not None and da == db:
                    div_rec[a]["w" if ra == "W" else "l" if ra == "L" else "t"] += 1
                    div_rec[b]["w" if rb == "W" else "l" if rb == "L" else "t"] += 1

    # Weekly ranks for all-play / luck.
    all_play: dict[int, dict[str, int]] = {rid: {"w": 0, "l": 0, "t": 0} for rid in teams}
    weekly_rank: dict[int, dict[int, int]] = {rid: {} for rid in teams}
    weekly_high: dict[int, int] = {}
    weekly_low: dict[int, int] = {}
    for week in sorted({w for s in scores.values() for w in s}):
        if week not in reg_weeks:
            continue
        wk = [(rid, scores[rid][week]) for rid in teams if week in scores[rid]]
        wk.sort(key=lambda x: -x[1])
        if not wk:
            continue
        weekly_high[week] = wk[0][0]; weekly_low[week] = wk[-1][0]
        for i, (rid, pts) in enumerate(wk):
            weekly_rank[rid][week] = i + 1
            for rid2, pts2 in wk:
                if rid2 == rid:
                    continue
                if pts > pts2: all_play[rid]["w"] += 1
                elif pts < pts2: all_play[rid]["l"] += 1
                else: all_play[rid]["t"] += 1

    # Position breakdown + optimal lineups + top scorers (regular + playoff weeks, completed).
    pos_points: dict[int, dict[str, float]] = {rid: defaultdict(float) for rid in teams}
    optimal: dict[int, dict[int, float]] = {rid: {} for rid in teams}
    player_points: dict[int, dict[str, float]] = {rid: defaultdict(float) for rid in teams}
    for week, rows in ctx["matchups"].items():
        if week > last_completed:
            continue
        for r in rows:
            rid = int(r["roster_id"])
            if rid not in teams or r.get("matchup_id") is None:
                continue
            starters = r.get("starters") or []
            sp = r.get("starters_points") or []
            pp = r.get("players_points") or {}
            for i, pid in enumerate(starters):
                pts = float(sp[i]) if i < len(sp) else float(pp.get(pid, 0) or 0)
                lab = player_label(players, pid)
                pos_points[rid][lab["position"]] += pts
                if pid not in ("0", None):
                    player_points[rid][str(pid)] += pts
            if pp:
                optimal[rid][week] = optimal_lineup_points(ctx, r)

    league_scores = [s for rid in teams for s in scores[rid].values()]
    league_mean = sum(league_scores) / len(league_scores) if league_scores else 0.0

    team_stats: dict[int, dict] = {}
    for rid, t in teams.items():
        reg_scores = [scores[rid][w] for w in sorted(scores[rid]) if w in reg_weeks]
        n = len(reg_scores)
        avg = sum(reg_scores) / n if n else 0.0
        std = math.sqrt(sum((x - avg) ** 2 for x in reg_scores) / (n - 1)) if n > 1 else 0.0
        wins = sum(1 for r in results[rid] if r == "W")
        losses = sum(1 for r in results[rid] if r == "L")
        ties = sum(1 for r in results[rid] if r == "T")
        ap = all_play[rid]
        ap_games = ap["w"] + ap["l"] + ap["t"]
        ap_pct = (ap["w"] + 0.5 * ap["t"]) / ap_games if ap_games else 0.0
        expected_wins = ap_pct * n
        pf = sum(reg_scores)
        pa = sum(scores[opp[rid][w]][w] for w in scores[rid] if w in reg_weeks and w in opp[rid])
        opt_total = sum(optimal[rid][w] for w in optimal[rid] if w in reg_weeks)
        act_for_opt = sum(scores[rid][w] for w in optimal[rid] if w in reg_weeks)
        # Sleeper's own season "potential points" (roster settings.ppts, undocumented field) wins over our greedy calc.
        if t.get("ppts"):
            opt_total, act_for_opt = float(t["ppts"]), pf
        top_pid = max(player_points[rid], key=player_points[rid].get) if player_points[rid] else None
        team_stats[rid] = {
            **{k: v for k, v in t.items() if k not in ("players", "starters", "profile")},
            "profile": t.get("profile") or {},
            "wins": wins, "losses": losses, "ties": ties,
            "record": f"{wins}-{losses}" + (f"-{ties}" if ties else ""),
            "division_record": (f"{div_rec[rid]['w']}-{div_rec[rid]['l']}" + (f"-{div_rec[rid]['t']}" if div_rec[rid]['t'] else "")
                                if t.get("division") is not None else None),
            "win_pct": (wins + 0.5 * ties) / n if n else 0.0,
            "pf": round(pf, 2), "pa": round(pa, 2), "avg": round(avg, 2), "std": round(std, 2),
            "high": round(max(reg_scores), 2) if reg_scores else 0.0,
            "low": round(min(reg_scores), 2) if reg_scores else 0.0,
            "scores": {w: round(scores[rid][w], 2) for w in sorted(scores[rid])},
            "results": results[rid],
            "streak": _streak(results[rid]),
            "all_play": {**ap, "pct": round(ap_pct, 3)},
            "expected_wins": round(expected_wins, 2),
            "luck": round(wins - expected_wins, 2),
            "weekly_rank": weekly_rank[rid],
            "weeks_top": sum(1 for w, r in weekly_high.items() if r == rid),
            "weeks_bottom": sum(1 for w, r in weekly_low.items() if r == rid),
            "pos_points": {k: round(v, 2) for k, v in sorted(pos_points[rid].items(), key=lambda kv: -kv[1])},
            "optimal_pf": round(opt_total, 2),
            "lineup_efficiency": round(act_for_opt / opt_total, 3) if opt_total else None,
            "bench_points_left": round(opt_total - act_for_opt, 2),
            "top_player": ({**player_label(players, top_pid), "points": round(player_points[rid][top_pid], 2)} if top_pid else None),
            "h2h": {int(k): dict(v) for k, v in h2h[rid].items()},
            "roster": [player_label(players, pid) | {"season_points": round(player_points[rid].get(str(pid), 0.0), 2),
                                                     "starter": pid in (t.get("starters") or [])}
                       for pid in t.get("players") or []],
        }

    # Tiebreak everywhere: wins (ties = 0.5), then points-for, then points-against (higher PA advances).
    def standing_key(t: dict) -> tuple:
        return (-(t["wins"] + 0.5 * t["ties"]), -t["pf"], -t["pa"])

    standings = sorted(team_stats.values(), key=standing_key)
    for i, t in enumerate(standings):
        t["rank"] = i + 1
        t["in_playoff_spot"] = i < ctx["playoff_teams"]

    division_standings: dict[int, list[int]] = {}
    for d in sorted(ctx.get("divisions") or {}):
        members = [t for t in standings if t.get("division") == d]
        division_standings[d] = [t["roster_id"] for t in members]
    division_leaders = {d: rids[0] for d, rids in division_standings.items() if rids}

    # Power rating (1-100): 35% win pct, 40% all-play pct, 25% scoring (min-max scaled league avg).
    avgs = [t["avg"] for t in team_stats.values()]
    lo_avg, hi_avg = (min(avgs), max(avgs)) if avgs else (0.0, 0.0)
    for t in team_stats.values():
        scoring_pct = (t["avg"] - lo_avg) / (hi_avg - lo_avg) if hi_avg > lo_avg else 0.0
        raw = 0.35 * t["win_pct"] + 0.40 * t["all_play"]["pct"] + 0.25 * scoring_pct
        t["power_rating"] = max(1, min(100, round(100 * raw)))
        t["power_score"] = t["power_rating"] / 100  # backwards compatibility
    power = sorted(team_stats.values(), key=lambda t: (-t["power_rating"], -t["all_play"]["pct"], -t["avg"]))
    for i, t in enumerate(power):
        t["power_rank"] = i + 1

    # League records.
    records: dict[str, Any] = {}
    if completed_games:
        reg_games = [g for g in completed_games if g["regular"]] or completed_games
        hi = max(((g["a"], g["a_pts"], g["week"]) for g in reg_games), key=lambda x: x[1])
        hi_b = max(((g["b"], g["b_pts"], g["week"]) for g in reg_games), key=lambda x: x[1])
        hi = max(hi, hi_b, key=lambda x: x[1])
        lo = min(((g["a"], g["a_pts"], g["week"]) for g in reg_games), key=lambda x: x[1])
        lo_b = min(((g["b"], g["b_pts"], g["week"]) for g in reg_games), key=lambda x: x[1])
        lo = min(lo, lo_b, key=lambda x: x[1])
        blow = max(reg_games, key=lambda g: g["margin"])
        close = min((g for g in reg_games if g["margin"] > 0), key=lambda g: g["margin"], default=None)
        shootout = max(reg_games, key=lambda g: g["a_pts"] + g["b_pts"])
        records = {
            "high_score": {"roster_id": hi[0], "points": hi[1], "week": hi[2]},
            "low_score": {"roster_id": lo[0], "points": lo[1], "week": lo[2]},
            "biggest_blowout": blow,
            "closest_game": close,
            "highest_scoring_game": shootout,
        }

    return {
        "teams": team_stats,
        "standings": [t["roster_id"] for t in standings],
        "power_rankings": [t["roster_id"] for t in power],
        "games": completed_games,
        "division_standings": division_standings,
        "division_leaders": division_leaders,
        "schedule": {w: gs for w, gs in games.items() if w > last_completed and w in reg_weeks},
        "league_avg": round(league_mean, 2),
        "records": records,
    }


def snapshot(st: dict, ctx: dict, week: int) -> dict[str, Any]:
    """League state THROUGH `week` (regular-season games only), rebuilt from per-game results.

    Returns {"week", "teams": {rid: {wins, losses, ties, record, rank, streak, pf, pa, avg, all_play,
    expected_wins, luck, weekly_rank, weeks_top, weeks_bottom, results, games}}, "standings": [rid, ...]}.
    Articles about a past week must use this, never the final-season numbers in st["teams"].
    """
    teams = ctx["teams"]
    reg_weeks = set(ctx["regular_weeks"])
    through = [g for g in st["games"] if g["week"] <= week and g["week"] in reg_weeks]
    results: dict[int, list[str]] = {rid: [] for rid in teams}
    pf = {rid: 0.0 for rid in teams}
    pa = {rid: 0.0 for rid in teams}
    by_week: dict[int, dict[int, float]] = {}
    for g in sorted(through, key=lambda x: x["week"]):
        a, b = g["a"], g["b"]
        if a not in teams or b not in teams:
            continue
        by_week.setdefault(g["week"], {})[a] = g["a_pts"]
        by_week[g["week"]][b] = g["b_pts"]
        pf[a] += g["a_pts"]; pf[b] += g["b_pts"]
        pa[a] += g["b_pts"]; pa[b] += g["a_pts"]
        ra, rb = ("W", "L") if g["a_pts"] > g["b_pts"] else ("L", "W") if g["b_pts"] > g["a_pts"] else ("T", "T")
        results[a].append(ra); results[b].append(rb)
    all_play = {rid: {"w": 0, "l": 0, "t": 0} for rid in teams}
    weekly_rank: dict[int, dict[int, int]] = {rid: {} for rid in teams}
    weeks_top = {rid: 0 for rid in teams}
    weeks_bottom = {rid: 0 for rid in teams}
    for wk in sorted(by_week):
        ranked = sorted(by_week[wk].items(), key=lambda kv: -kv[1])
        weeks_top[ranked[0][0]] += 1
        weeks_bottom[ranked[-1][0]] += 1
        for i, (rid, pts) in enumerate(ranked):
            weekly_rank[rid][wk] = i + 1
            for rid2, pts2 in ranked:
                if rid2 != rid:
                    all_play[rid]["w" if pts > pts2 else "l" if pts < pts2 else "t"] += 1
    out: dict[int, dict] = {}
    for rid in teams:
        res = results[rid]
        w, l, t = res.count("W"), res.count("L"), res.count("T")
        n = len(res)
        ap = all_play[rid]
        apg = ap["w"] + ap["l"] + ap["t"]
        ap_pct = (ap["w"] + 0.5 * ap["t"]) / apg if apg else 0.0
        exp = ap_pct * n
        out[rid] = {
            "roster_id": rid, "wins": w, "losses": l, "ties": t, "games": n,
            "record": f"{w}-{l}" + (f"-{t}" if t else ""),
            "streak": _streak(res), "results": res,
            "pf": round(pf[rid], 2), "pa": round(pa[rid], 2), "avg": round(pf[rid] / n, 2) if n else 0.0,
            "all_play": {**ap, "pct": round(ap_pct, 3)},
            "expected_wins": round(exp, 2), "luck": round(w - exp, 2),
            "weekly_rank": weekly_rank[rid], "weeks_top": weeks_top[rid], "weeks_bottom": weeks_bottom[rid],
        }
    order = sorted(out, key=lambda r: (-(out[r]["wins"] + 0.5 * out[r]["ties"]), -out[r]["pf"], -out[r]["pa"], r))
    for i, rid in enumerate(order):
        out[rid]["rank"] = i + 1
    return {"week": week, "teams": out, "standings": order}
