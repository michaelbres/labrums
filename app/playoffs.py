"""Monte Carlo playoff odds.

Each team's weekly score is modeled as Normal(mu, sigma), with mu/sigma shrunk
toward the league average by `prior_games` worth of games so one hot week doesn't
dominate. Remaining regular-season games are simulated, seeds assigned by wins
then points-for, then points-against (Sleeper's default tiebreak; division
winners take the top seeds when the league uses divisions), and the top `playoff_teams` make it.
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
    base_wins = np.zeros(n); base_pf = np.zeros(n); base_pa = np.zeros(n)
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
        base_pa[idx[rid]] = t["pa"]

    remaining = [(w, g["a"], g["b"]) for w, gs in sorted(st["schedule"].items()) for g in gs if w in reg_weeks]
    rng = np.random.default_rng(seed)
    wins = np.tile(base_wins, (sims, 1))
    pf = np.tile(base_pf, (sims, 1))
    pa = np.tile(base_pa, (sims, 1))
    next_week = remaining[0][0] if remaining else None
    next_week_won: dict[int, np.ndarray] = {}
    for w, a, b in remaining:
        ia, ib = idx[a], idx[b]
        sa = rng.normal(mu[ia], sd[ia], sims)
        sb = rng.normal(mu[ib], sd[ib], sims)
        a_won = sa > sb
        wins[:, ia] += a_won; wins[:, ib] += ~a_won
        pf[:, ia] += sa; pf[:, ib] += sb
        pa[:, ia] += sb; pa[:, ib] += sa
        if w == next_week:
            next_week_won[a] = a_won
            next_week_won[b] = ~a_won

    # Tiebreak order: wins desc, then pf desc, then pa desc. lexsort sorts ascending by last key first.
    order = np.lexsort((-pa, -pf, -wins), axis=1)  # shape (sims, n): team index at each tiebreak rank
    rows = np.arange(sims)[:, None]
    tb_rank = np.empty_like(order)
    tb_rank[rows, order] = np.arange(n)[None, :]  # 0 = best by the tiebreak

    # Division winners take seeds 1..D (ordered by the same tiebreak), the rest follow by tiebreak.
    div_of = [teams[rid].get("division") for rid in rids]
    divs = sorted({d for d in div_of if d is not None})
    opt = cfg.get("division_winners_top_seeds", "auto")
    lsettings = ctx.get("settings") or {}
    if isinstance(opt, str) and opt.strip().lower() in ("auto", ""):
        use_divs = len(divs) > 1 and int(lsettings.get("playoff_seed_type") or 0) == 0
    else:
        use_divs = bool(opt) and str(opt).strip().lower() not in ("false", "no", "off", "0") and len(divs) > 1
    key = tb_rank.copy()
    if use_divs:
        for d in divs:
            cols = [i for i, x in enumerate(div_of) if x == d]
            best = np.argmin(tb_rank[:, cols], axis=1)  # position within `cols` of the division's best team
            win_col = np.asarray(cols)[best]
            key[np.arange(sims), win_col] -= n  # winners sort ahead of every non-winner
    seed_order = np.argsort(key, axis=1, kind="stable")
    seeds = np.empty_like(seed_order)
    seeds[rows, seed_order] = np.arange(n)[None, :] + 1
    seeding_rule = (f"Division winners seeded 1-{len(divs)}, then best record; ties by PF, then PA"
                    if use_divs else "Seeded by record; ties by PF, then PA")
    made = seeds <= playoff_teams
    bye_slots = 2 if playoff_teams == 6 else (0 if playoff_teams in (4, 8) else 1)

    # Current seeds: the same seeding rule applied to today's records (no simulation).
    cur_key = [(-(teams[rid]["wins"] + 0.5 * teams[rid]["ties"]), -teams[rid]["pf"], -teams[rid]["pa"]) for rid in rids]
    cur_order = sorted(range(n), key=lambda i: cur_key[i])
    if use_divs:
        winners = {min((i for i in range(n) if div_of[i] == d), key=lambda i: cur_key[i]) for d in divs}
        cur_order = sorted(winners, key=lambda i: cur_key[i]) + [i for i in cur_order if i not in winners]
    current_seeds = {rids[i]: (pos + 1 if pos < playoff_teams else None) for pos, i in enumerate(cur_order)}

    out: dict[int, dict] = {}
    games_left = {rid: sum(1 for w, a, b in remaining if rid in (a, b)) for rid in rids}
    cur_wins = {rid: teams[rid]["wins"] + 0.5 * teams[rid]["ties"] for rid in rids}
    max_wins = {rid: cur_wins[rid] + games_left[rid] for rid in rids}

    leaders = st.get("division_leaders") or {}

    def exact_status(rid: int) -> str:
        if not remaining:  # regular season over: the (division-aware) final seeding is the answer
            return "clinched" if made[:, idx[rid]].all() else "eliminated"
        others = [o for o in rids if o != rid]
        # Teams that could finish level with me can still win the tiebreak, so count >= here.
        can_pass = sum(1 for o in others if max_wins[o] >= cur_wins[rid])
        already_ahead = sum(1 for o in others if cur_wins[o] > max_wins[rid])
        if can_pass < playoff_teams:
            # Sufficient by record alone; with division winners a lower-ranked winner could still bump a team.
            return "clinched" if (not use_divs or made[:, idx[rid]].all()) else "alive"
        if already_ahead >= playoff_teams:
            # Still alive if it could yet win its own division.
            lead = leaders.get(teams[rid].get("division")) if use_divs else None
            if lead is not None and max_wins[rid] >= cur_wins[lead]:
                return "alive"
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
    return {"sims": sims, "playoff_teams": playoff_teams, "seeding_rule": seeding_rule, "current_seeds": current_seeds, "next_week": next_week,
            "league_mu": round(league_mu, 2), "league_sd": round(league_sd, 2), "teams": out}
