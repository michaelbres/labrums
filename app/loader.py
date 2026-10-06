"""Assemble everything we know about one season into a plain dict ("ctx")."""
from __future__ import annotations

import logging
from typing import Any

from .sleeper import avatar_url

log = logging.getLogger("labrums.loader")

MAX_WEEK = 18


def discover_seasons(client, cfg: dict) -> list[dict]:
    """Seasons from config plus anything reachable via previous_league_id."""
    found: dict[str, dict] = {}
    queue = list(cfg["seasons"].values())
    seen = set()
    while queue:
        lid = queue.pop(0)
        if not lid or lid in seen:
            continue
        seen.add(lid)
        try:
            league = client.league(lid)
        except Exception as e:  # network down and nothing cached
            log.warning("could not load league %s: %s", lid, e)
            league = None
        if not league:
            continue
        season = str(league.get("season"))
        found[season] = {"season": season, "league_id": lid, "name": league.get("name"),
                         "status": league.get("status")}
        prev = league.get("previous_league_id")
        if prev and str(prev) not in seen:
            queue.append(str(prev))
    # Config entries whose league couldn't be loaded still show up (keyed by config season).
    for season, lid in cfg["seasons"].items():
        if not any(s["league_id"] == lid for s in found.values()):
            found.setdefault(season, {"season": season, "league_id": lid, "name": None, "status": "unavailable"})
    out = sorted(found.values(), key=lambda s: s["season"], reverse=True)
    for s in out:
        s["is_current"] = s["season"] == cfg.get("current_season")
    return out


def completed_week_cutoff(league: dict, state: dict) -> int:
    """Highest week number whose scoring is final."""
    status = league.get("status")
    if status == "complete":
        return MAX_WEEK
    state_season = str(state.get("season") or state.get("league_season") or "")
    if state_season and state_season != str(league.get("season")):
        # Looking at an old season while the NFL is in a new one: everything's final.
        return MAX_WEEK
    if state.get("season_type") == "pre" or not state.get("week"):
        return 0
    week = int(state.get("week"))
    if state.get("season_type") == "post" or state.get("season_type") == "off":
        return MAX_WEEK
    return max(0, week - 1)


def load_season(client, cfg: dict, league_id: str) -> dict[str, Any]:
    league = client.league(league_id)
    if not league:
        raise ValueError(f"League {league_id} not found on Sleeper")
    state = client.state() or {}
    users = client.users(league_id)
    rosters = client.rosters(league_id)
    players = client.players()

    settings = league.get("settings") or {}
    playoff_start = int(settings.get("playoff_week_start") or 15)
    regular_weeks = list(range(1, playoff_start))
    last_completed = min(completed_week_cutoff(league, state), MAX_WEEK)
    current_week = min(last_completed + 1, MAX_WEEK)
    if league.get("status") in ("pre_draft", "drafting"):
        last_completed, current_week = 0, 1

    matchups: dict[int, list[dict]] = {}
    transactions: dict[int, list[dict]] = {}
    last_week_with_data = 0
    for week in range(1, MAX_WEEK + 1):
        final = week <= last_completed
        try:
            rows = client.matchups(league_id, week, final=final)
        except Exception as e:
            log.warning("matchups week %s failed: %s", week, e)
            rows = []
        if rows:
            matchups[week] = rows
            last_week_with_data = week
        try:
            tx = client.transactions(league_id, week, final=final)
        except Exception as e:
            log.warning("transactions week %s failed: %s", week, e)
            tx = []
        if tx:
            transactions[week] = tx
        if week > playoff_start + 3 and not rows:
            break
    last_completed = min(last_completed, last_week_with_data)

    user_by_id = {u["user_id"]: u for u in users}
    owners_cfg = cfg.get("owners") or {}
    owners_cfg_ci = {str(k).lower(): v for k, v in owners_cfg.items()}
    teams: dict[int, dict] = {}
    for r in rosters:
        u = user_by_id.get(r.get("owner_id")) or {}
        meta = u.get("metadata") or {}
        display = u.get("display_name") or f"Roster {r['roster_id']}"
        prof = (owners_cfg_ci.get(str(display).lower()) or owners_cfg.get(str(u.get("user_id")))
                or owners_cfg.get(display) or {})
        s = r.get("settings") or {}
        teams[int(r["roster_id"])] = {
            "roster_id": int(r["roster_id"]),
            "owner_id": u.get("user_id"),
            "display_name": display,
            "team_name": meta.get("team_name") or f"Team {display}",
            "avatar": avatar_url(meta.get("avatar") or u.get("avatar")) if not str(meta.get("avatar") or "").startswith("http") else meta.get("avatar"),
            "nickname": prof.get("nickname"),
            "profile": prof,
            "wins": int(s.get("wins") or 0), "losses": int(s.get("losses") or 0), "ties": int(s.get("ties") or 0),
            "pf": float(s.get("fpts") or 0) + float(s.get("fpts_decimal") or 0) / 100.0,
            "pa": float(s.get("fpts_against") or 0) + float(s.get("fpts_against_decimal") or 0) / 100.0,
            "waiver_budget_used": s.get("waiver_budget_used"),
            "total_moves": s.get("total_moves"),
            "division": s.get("division"),
            "players": list(r.get("players") or []),
            "starters": list(r.get("starters") or []),
        }

    return {
        "league_id": league_id,
        "season": str(league.get("season")),
        "league": league,
        "state": state,
        "settings": settings,
        "roster_positions": list(league.get("roster_positions") or []),
        "playoff_teams": int(cfg["playoffs"].get("teams") or settings.get("playoff_teams") or 6),
        "playoff_start": playoff_start,
        "regular_weeks": regular_weeks,
        "last_completed": last_completed,
        "current_week": current_week,
        "teams": teams,
        "matchups": matchups,
        "transactions": transactions,
        "players": players,
        "config": cfg,
    }
