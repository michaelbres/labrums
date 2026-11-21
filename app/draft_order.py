"""Projected rookie-draft order under the league's own rule: every team, by season max PF, lowest first.

Max PF = the best legal lineup's score each week, summed over the regular season. Checked against Sleeper for the
2023, 2024 and 2025 seasons: Sleeper's per-roster `ppts` is exactly that regular-season sum (weeks before
`playoff_week_start`) and ordering all teams by it, lowest first, reproduces the real 2024, 2025 and 2026 rookie
draft slots. Playoff results play no part. Equal max PF: the team with the worse record picks first, then lower
points for, then the lower roster id.

`rank_order` is the one ranking key, used by the Monte Carlo (many seasons at once) and by `order_picks` (one season).
"""
from __future__ import annotations

from typing import Any

import numpy as np

RULE_TEXT = "Order is by max PF (best possible lineup each week), lowest first: the same rule as the 2024 to 2026 drafts."
TIEBREAK_TEXT = "Equal max PF: worse record first, then fewer points for, then lower roster id."


def rank_order(max_pf: np.ndarray, wins: np.ndarray, pf: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """max_pf (S, n); wins, pf (n,) break exact ties. Returns (order, slot): order[s, j] = team index making pick
    j+1; slot[s, i] = pick number (1-based) of team index i."""
    S, n = max_pf.shape
    idx = np.broadcast_to(np.arange(n), (S, n))
    order = np.lexsort((idx, np.broadcast_to(pf, (S, n)), np.broadcast_to(wins, (S, n)), max_pf), axis=1)
    slot = np.empty_like(order)
    slot[np.arange(S)[:, None], order] = np.arange(1, n + 1)[None, :]
    return order, slot


def order_picks(max_pf: dict[int, float], wins: dict[int, float] | None = None,
                pf: dict[int, float] | None = None) -> list[dict]:
    """One season: [{pick, roster_id, max_pf, gap_to_next}] lowest max PF first. `gap_to_next` is how far the next
    pick's max PF is above this one's (None for the last pick)."""
    rids = sorted(max_pf)
    if not rids:
        return []
    order, _ = rank_order(np.array([[float(max_pf[r]) for r in rids]]),
                          np.array([float((wins or {}).get(r, 0.0)) for r in rids]),
                          np.array([float((pf or {}).get(r, 0.0)) for r in rids]))
    seq = [rids[int(i)] for i in order[0]]
    out = []
    for j, rid in enumerate(seq):
        gap = round(float(max_pf[seq[j + 1]]) - float(max_pf[rid]), 2) if j + 1 < len(seq) else None
        out.append({"pick": j + 1, "roster_id": rid, "max_pf": round(float(max_pf[rid]), 2), "gap_to_next": gap})
    return out


def build_block(ctx: dict, st: dict, po: dict, cap: dict) -> dict[str, Any]:
    """The `draft_order` block of the season payload: today's order, the simulated order, and the rule.
    `cap` is what playoffs.simulate captured: rids, pf (simulated season points for), base_pf, sims."""
    teams = st["teams"]
    rids: list[int] = cap["rids"]
    n = len(rids)
    final = po.get("next_week") is None          # every regular-season game is played: max PF is final
    notes: list[str] = []
    sources = {teams[r].get("max_pf_source") for r in rids}
    if len(sources) > 1:
        notes.append("Max PF mixes Sleeper's value and our own calculation for some teams.")
    if sources == {"computed"}:
        notes.append("Sleeper gave no max PF (ppts); every value is our own best-lineup calculation.")

    max_now = np.array([float(teams[r]["max_pf"]) for r in rids])
    base_pf = np.array([float(teams[r]["pf"]) for r in rids])
    wins = np.array([float(teams[r]["wins"]) + 0.5 * float(teams[r].get("ties") or 0) for r in rids])

    # --- Today: max PF to date.
    today = order_picks({r: float(teams[r]["max_pf"]) for r in rids}, dict(zip(rids, wins)), dict(zip(rids, base_pf)))
    today_pos = {row["roster_id"]: row["pick"] for row in today}

    # --- Simulated: season max PF = max PF so far + the simulated remaining points scaled by max PF / PF.
    if final:
        S = 1
        max_sim = max_now[None, :]
    else:
        S = int(cap["sims"])
        ratio = np.where(base_pf > 0, max_now / np.where(base_pf > 0, base_pf, 1.0), 1.0)
        max_sim = max_now[None, :] + (cap["pf"] - cap["base_pf"][None, :]) * ratio[None, :]
    _, slot_s = rank_order(max_sim, wins, base_pf)
    slot_p = np.stack([np.bincount(slot_s[:, i] - 1, minlength=n) / len(slot_s) for i in range(n)])  # (team, slot)
    exp_pick = slot_s.mean(axis=0)
    proj = max_sim.mean(axis=0)
    ranked = sorted(range(n), key=lambda i: (round(float(exp_pick[i]), 9), today_pos[rids[i]], rids[i]))
    sim_rows = []
    for j, i in enumerate(ranked):
        nxt = ranked[j + 1] if j + 1 < n else None
        sim_rows.append({
            "pick": j + 1, "roster_id": rids[i], "expected_pick": round(float(exp_pick[i]), 2),
            "slot_odds": [round(float(x), 4) for x in slot_p[i]],
            "most_likely_slot": int(np.argmax(slot_p[i])) + 1,
            "max_pf": round(float(max_now[i]), 2), "proj_max_pf": round(float(proj[i]), 1),
            "gap_to_next": round(float(proj[nxt] - proj[i]), 1) if nxt is not None else None,
        })

    return {
        "season": str(int(ctx["season"]) + 1),
        "teams": n,
        "status": "final" if final else "projected",
        "rule": RULE_TEXT, "tiebreak": TIEBREAK_TEXT,
        "today": {"basis": "Final max PF" if final else "Max PF to date, lowest first", "order": today},
        "simulated": {"sims": 0 if final else S, "locked": final, "order": sim_rows,
                      "basis": ("Final max PF" if final else
                                f"{S:,} simulated seasons: remaining regular-season games, with each team's season "
                                "max PF = max PF so far + simulated points scaled by its max PF / PF ratio")},
        "max_pf": {str(r): {"value": round(float(teams[r]["max_pf"]), 2), "source": teams[r].get("max_pf_source"),
                            "sleeper": teams[r].get("ppts"), "computed": teams[r].get("max_pf_calc")} for r in rids},
        "notes": notes,
    }
