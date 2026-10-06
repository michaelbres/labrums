"""Monte Carlo playoff odds.

Each team's weekly score is modeled as Normal(mu, sigma), with mu/sigma shrunk
toward the league average by `prior_games` worth of games so one hot week doesn't
dominate. Remaining regular-season games are simulated, seeds assigned by wins
then points-for (Sleeper's default tiebreak), and the top `playoff_teams` make it.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def simulate(ctx: dict, st: dict, sims: int | None = None, seed: int = 42) -> dict[str, Any]:
    cfg = ctx["config"]["playoffs"]
    sims = int(sims or cfg.get("simulations") or 5000)
    prior_games = float(cfg.get("prior_games") or 3)
    playoff_teams = ctx["playoff_teams"]
    reg_weeks = set(ctx["regular_weeks"])
    teams = st["teams"]
    rids = sorted(teams)
    idx = {rid: i for i, rid in enumerate(rids)}
    n = len(rids)

    all_scores = [s for rid in rids for w, s in teams[rid]["scores"].items() if w in reg_weeks]
    league_mu = float(np.mean(all_scores)) if all_scores else 110.0
    league_sd = float(np.std(all_scores, ddof=1)) if len(all_scores) > 2 else 25.0

    mu = np.zeros(n); sd = np.zeros(n)
    base_wins = np.zeros(n); base_pf = np.zeros(n)
    for rid in rids:
        t = teams[rid]
        own = [s for w, s in t["scores"].items() if w in reg_weeks]
        k = len(own)
        m = float(np.mean(own)) if own else league_mu
        v = float(np.var(own, ddof=1)) if k > 1 else league_sd ** 2
        mu[idx[rid]] = (k * m + prior_games * league_mu) / (k + prior_games)
        sd[idx[rid]] = max(12.0, np.sqrt((k * v + prior_games * league_sd ** 2) / (k + prior_games)))
        base_wins[idx[rid]] = t["wins"] + 0.5 * t["ties"]
        base_pf[idx[rid]] = t["pf"]

    remaining = [(w, g["a"], g["b"]) for w, gs in sorted(st["schedule"].items()) for g in gs if w in reg_weeks]
    rng = np.random.default_rng(seed)
    wins = np.tile(base_wins, (sims, 1))
    pf = np.tile(base_pf, (sims, 1))
    next_week = remaining[0][0] if remaining else None
    next_week_won: dict[int, np.ndarray] = {}
    for w, a, b in remaining:
        ia, ib = idx[a], idx[b]
        sa = rng.normal(mu[ia], sd[ia], sims)
        sb = rng.normal(mu[ib], sd[ib], sims)
        a_won = sa > sb
        wins[:, ia] += a_won; wins[:, ib] += ~a_won
        pf[:, ia] += sa; pf[:, ib] += sb
        if w == next_week:
            next_week_won[a] = a_won
            next_week_won[b] = ~a_won

    # Seed by wins desc, then pf desc. lexsort sorts ascending by last key first.
    order = np.lexsort((-pf, -wins), axis=1)  # shape (sims, n): team index at each seed
    seeds = np.empty_like(order)
    rows = np.arange(sims)[:, None]
    seeds[rows, order] = np.arange(n)[None, :] + 1
    made = seeds <= playoff_teams
    bye_slots = 2 if playoff_teams == 6 else (0 if playoff_teams in (4, 8) else 1)

    out: dict[int, dict] = {}
    games_left = {rid: sum(1 for w, a, b in remaining if rid in (a, b)) for rid in rids}
    cur_wins = {rid: teams[rid]["wins"] + 0.5 * teams[rid]["ties"] for rid in rids}
    max_wins = {rid: cur_wins[rid] + games_left[rid] for rid in rids}

    def exact_status(rid: int) -> str:
        others = [o for o in rids if o != rid]
        # Teams that could finish level with me can still win the tiebreak, so count >= here.
        can_pass = sum(1 for o in others if max_wins[o] >= cur_wins[rid])
        already_ahead = sum(1 for o in others if cur_wins[o] > max_wins[rid])
        if can_pass < playoff_teams:
            return "clinched"
        if already_ahead >= playoff_teams:
            return "eliminated"
        return "alive"

    for rid in rids:
        i = idx[rid]
        p = float(made[:, i].mean())
        seed_dist = [float((seeds[:, i] == s).mean()) for s in range(1, n + 1)]
        cond = None
        if rid in next_week_won:
            won = next_week_won[rid]
            cond = {"if_win": float(made[won, i].mean()) if won.any() else None,
                    "if_loss": float(made[~won, i].mean()) if (~won).any() else None}
        out[rid] = {
            "playoff_pct": round(p, 4),
            "bye_pct": round(float((seeds[:, i] <= bye_slots).mean()), 4) if bye_slots else 0.0,
            "top_seed_pct": round(seed_dist[0], 4),
            "avg_seed": round(float(seeds[:, i].mean()), 2),
            "seed_dist": [round(x, 4) for x in seed_dist],
            "proj_wins": round(float(wins[:, i].mean()), 2),
            "proj_pf": round(float(pf[:, i].mean()), 1),
            "games_left": games_left[rid],
            "status": exact_status(rid),
            "next_game": cond,
            "model": {"mu": round(float(mu[i]), 2), "sd": round(float(sd[i]), 2)},
        }
    return {"sims": sims, "playoff_teams": playoff_teams, "next_week": next_week,
            "league_mu": round(league_mu, 2), "league_sd": round(league_sd, 2), "teams": out}
