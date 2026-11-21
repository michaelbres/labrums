"""Projected rookie-draft order under the league's own rule.

Picks 1..(teams that missed the playoffs): the non-playoff teams, LOWEST max PF first (max PF = the best legal
lineup's score each week, summed over the regular season). Then the playoff teams by when they lose in the winners
bracket, earlier exit first; teams out in the same round: lower max PF first; the runner-up is second to last and
the champion last. The 3rd-place game and consolation games are ignored. Nothing here is hardcoded to 10 teams,
6 playoff teams or 4 rounds: the sizes come from the league.

Everything funnels through one ranking key, level = 0 (missed) / round lost / rounds + 1 (champion), then max PF,
then roster id. `order_picks` is the plain reference implementation; `_rank_levels` is the same key in numpy, used
for the Monte Carlo (a test asserts they agree).
"""
from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np

MISSED, ELIMINATED, RUNNER_UP, CHAMPION = "missed", "eliminated", "runner_up", "champion"


def rounds_for(k: int) -> int:
    """Rounds in a single-elimination bracket of k teams (top seeds get byes when k is not a power of two)."""
    return math.ceil(math.log2(k)) if k > 1 else 0


def reason_text(reason: str, rnd: int | None) -> str:
    return {MISSED: "Missed the playoffs", RUNNER_UP: "Runner-up (lost the final)", CHAMPION: "Champion"}.get(
        reason, f"Lost in round {rnd}")


def order_picks(max_pf: dict[int, float], playoff_rids: list[int], exit_round: dict[int, int],
                champion: int | None) -> list[dict]:
    """Reference ordering. `max_pf`: every team's max PF. `playoff_rids`: the teams in the playoffs. `exit_round`:
    round (1-based) in which each non-champion playoff team lost. Returns [{pick, roster_id, max_pf, reason, round}]."""
    play = set(playoff_rids)
    unknown = play - set(max_pf)
    if unknown:
        raise ValueError(f"playoff teams without a max PF: {sorted(unknown)}")
    if champion is not None and champion not in play:
        raise ValueError("champion is not a playoff team")
    for rid in play:
        if rid != champion and rid not in exit_round:
            raise ValueError(f"playoff team {rid} has no elimination round and is not the champion")
    rounds = max([exit_round[r] for r in play if r in exit_round] + [0])
    level: dict[int, int] = {}
    for rid in max_pf:
        level[rid] = 0 if rid not in play else (rounds + 1 if rid == champion else exit_round[rid])
    ranked = sorted(max_pf, key=lambda r: (level[r], max_pf[r], r))
    out = []
    for i, rid in enumerate(ranked):
        lv = level[rid]
        if lv == 0:
            reason = MISSED
        elif rid == champion:
            reason = CHAMPION
        elif lv == rounds:
            reason = RUNNER_UP
        else:
            reason = ELIMINATED
        out.append({"pick": i + 1, "roster_id": rid, "max_pf": round(float(max_pf[rid]), 2), "reason": reason,
                    "round": lv if reason in (ELIMINATED, RUNNER_UP) else None})
    return out


# ---- bracket ------------------------------------------------------------------------------------------------
def standard_order(p: int) -> list[int]:
    """Seeds in bracket order for a bracket of size p (power of two): adjacent entries meet in round 1 and the
    winners of adjacent pairs meet next (fixed bracket). 8 -> [1, 8, 4, 5, 2, 7, 3, 6]."""
    order = [1]
    while len(order) < p:
        m = len(order) * 2
        order = [x for s in order for x in (s, m + 1 - s)]
    return order


def run_bracket(seed_team: np.ndarray, seed_of: np.ndarray, n: int, k: int,
                decide: Callable[[np.ndarray, np.ndarray, int], np.ndarray],
                reseed: bool = False, forced: list[tuple[int, int]] | None = None) -> np.ndarray:
    """Play the winners bracket for many seasons at once.

    seed_team: (S, k) team index holding seed 1..k. seed_of: (S, n) seed of each team index. decide(a, b, round)
    -> bool array, True where team a beats team b. forced: [(winner_idx, loser_idx)] results already played.
    Returns level (S, n): 0 = missed, r = lost in round r, rounds + 1 = champion. Top seeds get byes when k is not a
    power of two. `reseed` re-pairs best vs worst remaining seed after round 1 (fixed bracket otherwise)."""
    S = seed_team.shape[0]
    level = np.zeros((S, n), dtype=np.int64)
    if k <= 0:
        return level
    R = rounds_for(k)
    rows = np.arange(S)
    if R == 0:
        level[rows, seed_team[:, 0]] = 1
        return level
    p = 2 ** R
    bye = np.full(S, -1, dtype=np.int64)
    cur = [seed_team[:, s - 1] if s <= k else bye for s in standard_order(p)]
    forced = forced or []
    for r in range(1, R + 1):
        if reseed and r > 1:
            stack = np.stack(cur, axis=1)
            by_seed = np.argsort(seed_of[rows[:, None], stack], axis=1, kind="stable")
            stack = stack[rows[:, None], by_seed]
            cur = [stack[:, j] for j in range(stack.shape[1])]
            cur = [x for j in range(len(cur) // 2) for x in (cur[j], cur[len(cur) - 1 - j])]
        nxt = []
        for i in range(0, len(cur), 2):
            a, b = cur[i], cur[i + 1]
            a_bye, b_bye = a < 0, b < 0
            a_wins = np.array(decide(np.where(a_bye, 0, a), np.where(b_bye, 0, b), r), dtype=bool)
            for w, l in forced:
                a_wins = np.where((a == w) & (b == l), True, np.where((a == l) & (b == w), False, a_wins))
            winner = np.where(b_bye, a, np.where(a_bye, b, np.where(a_wins, a, b)))
            loser = np.where(a_wins, b, a)
            played = ~(a_bye | b_bye)
            level[rows[played], loser[played]] = r
            nxt.append(winner)
        cur = nxt
    level[rows, cur[0]] = R + 1
    return level


def _rank_levels(level: np.ndarray, max_pf: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(order, slot): order[s, j] = team index making pick j+1; slot[s, i] = pick number (1-based) of team i."""
    S, n = level.shape
    idx = np.broadcast_to(np.arange(n), (S, n))
    order = np.lexsort((idx, max_pf, level), axis=1)
    slot = np.empty_like(order)
    slot[np.arange(S)[:, None], order] = np.arange(1, n + 1)[None, :]
    return order, slot


# ---- real results -------------------------------------------------------------------------------------------
def _main_matches(bracket: list[dict]) -> list[dict]:
    """Winners-bracket games that decide elimination: everything except the placement (3rd, 5th, ...) games."""
    return [m for m in bracket or [] if m.get("p") in (None, 1)]


def bracket_results(bracket: list[dict]) -> dict[str, Any]:
    """{teams: rids in the bracket, results: [(winner, loser, round)], rounds, champion, runner_up}."""
    ms = _main_matches(bracket)
    teams: set[int] = set()
    results = []
    champion = runner_up = None
    for m in ms:
        for key in ("t1", "t2"):
            if isinstance(m.get(key), int):
                teams.add(m[key])
        if m.get("w") is not None and m.get("l") is not None:
            results.append((int(m["w"]), int(m["l"]), int(m["r"])))
            if m.get("p") == 1:
                champion, runner_up = int(m["w"]), int(m["l"])
    return {"teams": teams, "results": results, "rounds": max([int(m["r"]) for m in ms] + [0]),
            "champion": champion, "runner_up": runner_up}


# ---- assembling the block -----------------------------------------------------------------------------------
def build_block(ctx: dict, st: dict, po: dict, cap: dict, bracket: list[dict] | None = None) -> dict[str, Any]:
    """The `draft_order` block of the season payload: today's order, the simulated order, and the rule."""
    teams = st["teams"]
    rids: list[int] = cap["rids"]
    idx = {r: i for i, r in enumerate(rids)}
    n, k = len(rids), int(po["playoff_teams"])
    k = min(k, n)
    cfg_rt = int((ctx.get("settings") or {}).get("playoff_round_type") or 0)
    reseed = cfg_rt == 1
    R = rounds_for(k)
    seeds_now: dict[int, int | None] = {int(r): s for r, s in po["current_seeds"].items()}
    reg_over = po.get("next_week") is None
    info = bracket_results(bracket or [])
    notes: list[str] = []

    # Who is in the playoffs: today's seeds, unless the regular season is over and Sleeper's bracket names the field.
    seed_order = sorted((r for r in rids if seeds_now.get(r)), key=lambda r: seeds_now[r])
    field = list(seed_order)
    if reg_over and info["teams"] and len(info["teams"]) == k:
        if set(info["teams"]) != set(field):
            notes.append("Playoff field taken from Sleeper's bracket (it differs from our seeding).")
        field = sorted(info["teams"], key=lambda r: (seeds_now.get(r) or 99, r))
    final = bool(info["champion"] is not None and reg_over and set(info["teams"]) >= set(field))

    max_now = np.array([float(teams[r]["max_pf"]) for r in rids])
    base_pf = np.array([float(teams[r]["pf"]) for r in rids])
    forced = [(idx[w], idx[l]) for w, l, _ in info["results"] if reg_over and w in idx and l in idx]

    # --- Today: current seeds, higher seed wins each remaining game, actual results where played.
    seed_of1 = np.full((1, n), n + 1, dtype=np.int64)
    for pos, r in enumerate(field):
        seed_of1[0, idx[r]] = pos + 1
    seed_team1 = np.array([[idx[r] for r in field]], dtype=np.int64).reshape(1, len(field))
    lvl_today = run_bracket(seed_team1, seed_of1, n, len(field),
                            lambda a, b, r: seed_of1[0, a] < seed_of1[0, b], reseed, forced)
    order_t, _ = _rank_levels(lvl_today, max_now[None, :])
    today = _describe(lvl_today[0], order_t[0], rids, max_now, R)

    # --- Simulated.
    S = int(cap["sims"])
    if final:
        sim_levels = lvl_today
        max_sim = max_now[None, :]
        S_eff = 1
    else:
        rng = np.random.default_rng([int(cap["seed"]), 7])
        mu, sd = cap["mu"], cap["sd"]
        seeds = cap["seeds"]
        seed_team = np.argsort(seeds, axis=1, kind="stable")[:, :k]
        seed_of = seeds
        if reg_over and len(field) == k:
            seed_team = np.tile(seed_team1[0], (S, 1))
            seed_of = np.tile(seed_of1[0], (S, 1))

        def decide(a, b, r):
            return rng.normal(mu[a], sd[a]) > rng.normal(mu[b], sd[b])

        sim_levels = run_bracket(seed_team, seed_of, n, k, decide, reseed, forced)
        # Season max PF = max PF so far + the simulated remaining points scaled by the team's max-PF / PF ratio.
        ratio = np.where(base_pf > 0, max_now / np.where(base_pf > 0, base_pf, 1.0), 1.0)
        max_sim = max_now[None, :] + (cap["pf"] - cap["base_pf"][None, :]) * ratio[None, :]
        S_eff = S
    order_s, slot_s = _rank_levels(sim_levels, max_sim)
    slot_p = np.stack([np.bincount(slot_s[:, i] - 1, minlength=n) / len(slot_s) for i in range(n)])  # (team, slot)
    exp_pick = slot_s.mean(axis=0)
    today_pos = {row["roster_id"]: row["pick"] for row in today}
    ranked = sorted(range(n), key=lambda i: (round(float(exp_pick[i]), 9), today_pos[rids[i]], rids[i]))
    sim_rows = []
    for j, i in enumerate(ranked):
        lv = np.bincount(sim_levels[:, i], minlength=R + 2) / len(sim_levels)   # P(missed), P(out r1..R), P(champ)
        outcomes = [{"reason": MISSED, "round": None, "p": round(float(lv[0]), 4)}]
        outcomes += [{"reason": (RUNNER_UP if r == R else ELIMINATED), "round": r, "p": round(float(lv[r]), 4)}
                     for r in range(1, R + 1)]
        outcomes.append({"reason": CHAMPION, "round": None, "p": round(float(lv[R + 1]), 4)}) if k else None
        modal = max(outcomes, key=lambda o: o["p"])
        sim_rows.append({
            "pick": j + 1, "roster_id": rids[i], "expected_pick": round(float(exp_pick[i]), 2),
            "slot_odds": [round(float(x), 4) for x in slot_p[i]],
            "most_likely_slot": int(np.argmax(slot_p[i])) + 1,
            "max_pf": round(float(max_now[i]), 2), "proj_max_pf": round(float(max_sim[:, i].mean()), 1),
            "reason": modal["reason"], "round": modal["round"], "why": reason_text(modal["reason"], modal["round"]),
            "why_pct": modal["p"], "outcomes": outcomes,
            "playoff_pct": round(float(1 - lv[0]), 4),
        })
    for row in today:
        row["why"] = reason_text(row["reason"], row["round"])

    return {
        "season": str(int(ctx["season"]) + 1),
        "teams": n, "playoff_teams": k, "rounds": R,
        "bracket": "reseed" if reseed else "fixed",
        "status": "final" if final else ("playoffs" if reg_over else "projected"),
        "rule": (f"Picks 1-{n - k}: teams that miss the playoffs, lowest max PF first. Then playoff teams by when they "
                 "lose in the winners bracket (earlier exit picks earlier; same round: lower max PF first); the "
                 "runner-up is second to last, the champion last. Max PF = best possible lineup each week, summed."),
        "today": {"basis": ("Final results" if final else "Seeds as of today, the higher seed wins every game "
                  "(played games count), max PF to date"), "order": today},
        "simulated": {"sims": 0 if final else S_eff, "locked": final, "order": sim_rows,
                      "basis": ("Final results" if final else
                                f"{S_eff:,} simulated seasons: remaining games, seeding and the bracket, with each team's "
                                "season max PF = max PF so far + simulated points scaled by its max PF / PF ratio")},
        "max_pf": {str(r): {"value": round(float(teams[r]["max_pf"]), 2), "source": teams[r].get("max_pf_source"),
                            "sleeper": teams[r].get("ppts"), "computed": teams[r].get("max_pf_calc")} for r in rids},
        "notes": notes,
    }


def _describe(level: np.ndarray, order: np.ndarray, rids: list[int], max_pf: np.ndarray, R: int) -> list[dict]:
    rows = []
    for j, i in enumerate(order):
        lv = int(level[i])
        if lv == 0:
            reason, rnd = MISSED, None
        elif lv == R + 1:
            reason, rnd = CHAMPION, None
        elif lv == R:
            reason, rnd = RUNNER_UP, lv
        else:
            reason, rnd = ELIMINATED, lv
        rows.append({"pick": j + 1, "roster_id": rids[int(i)], "max_pf": round(float(max_pf[i]), 2),
                     "reason": reason, "round": rnd})
    return rows
