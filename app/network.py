"""Player network: which NFL players sat on which fantasy teams across seasons.

Pure functions over already-loaded season dicts (see loader.load_season). A team's identity across
seasons is the Sleeper owner user_id (roster ids and team names change yearly).
"""
from __future__ import annotations

from typing import Any

from .sleeper import player_label

MAX_WEEK = 18


def _owner_key(season: str, team: dict) -> str:
    return str(team.get("owner_id") or f"roster:{season}:{team.get('roster_id')}")


def _runs(weeks: list[int]) -> list[tuple[int, int]]:
    """Contiguous (start, end) runs from a sorted list of distinct weeks."""
    out: list[tuple[int, int]] = []
    for w in weeks:
        if out and w == out[-1][1] + 1:
            out[-1] = (out[-1][0], w)
        else:
            out.append((w, w))
    return out


def _last_week(s: dict) -> int | None:
    """Last counted week of a completed season: league settings last_scored_leg, else the last week with points.
    Sleeper lists extra NFL weeks after the playoffs end."""
    if (s.get("league") or {}).get("status") != "complete":
        return None
    leg = int(((s.get("league") or {}).get("settings") or {}).get("last_scored_leg") or 0)
    if leg > 0:
        return leg  # Sleeper's own record of the last week that counted (later NFL weeks may still carry points)
    scored = [int(w) for w, rows in (s.get("matchups") or {}).items()
              if any(float(r.get("points") or 0) > 0 for r in rows or [])]
    return max(scored) if scored else None


def _snapshots(s: dict) -> dict[int, dict[int, set[str]]]:
    """week -> roster_id -> player ids, from the weekly matchup entries (commissioner moves included)."""
    complete = (s.get("league") or {}).get("status") == "complete"
    cur = s.get("current_week")
    last = _last_week(s)
    snaps: dict[int, dict[int, set[str]]] = {}
    for week, rows in (s.get("matchups") or {}).items():
        week = int(week)
        if last and week > last:
            continue  # empty weeks after the real end of the season
        if not complete and cur and week > int(cur):
            continue  # future weeks of an in-progress season are just a copy of today's rosters
        for r in rows or []:
            pl = [str(p) for p in (r.get("players") or []) if p not in (None, "", "0")]
            if pl and r.get("roster_id") is not None:
                snaps.setdefault(week, {})[int(r["roster_id"])] = set(pl)
    if not complete and cur:
        # In-progress season: current rosters are the freshest truth, so this week's adds count.
        week = int(cur)
        for rid, t in (s.get("teams") or {}).items():
            pl = {str(p) for p in (t.get("players") or []) if p not in (None, "", "0")}
            if pl:
                snaps.setdefault(week, {})[int(rid)] = pl
    return snaps


def _tx_events(s: dict) -> list[dict]:
    """Flattened adds/drops: {week, created, rid, pid, kind, added}. Sorted chronologically."""
    ev = []
    for week, txs in (s.get("transactions") or {}).items():
        for t in txs or []:
            kind = t.get("type")
            created = int(t.get("created") or 0)
            for pid, rid in (t.get("adds") or {}).items():
                ev.append({"week": int(week), "created": created, "rid": int(rid), "pid": str(pid),
                           "kind": kind, "added": True})
            for pid, rid in (t.get("drops") or {}).items():
                ev.append({"week": int(week), "created": created, "rid": int(rid), "pid": str(pid),
                           "kind": kind, "added": False})
    ev.sort(key=lambda e: (e["week"], e["created"]))
    return ev


def build_stints(seasons: list[dict], drafts: dict[str, list[dict]] | None = None) -> list[dict]:
    """One row per uninterrupted (player, owner, season) holding. `seasons` is oldest to newest.

    `drafts` maps season -> list of draft picks (Sleeper shape: player_id, roster_id). A season dict
    may also carry them under "draft_picks".
    """
    drafts = drafts or {}
    players: dict[str, dict] = {}
    for s in seasons:  # newest wins
        players = {**players, **(s.get("players") or {})}

    stints: list[dict] = []
    prev_last: dict[str, tuple[dict, int]] = {}  # pid -> (final stint, roster_id) in the previous season
    for s in seasons:
        season = str(s["season"])
        teams = s.get("teams") or {}
        snaps = _snapshots(s)
        last = _last_week(s)
        events = [e for e in _tx_events(s) if not last or e["week"] <= last]
        first_week = min(snaps) if snaps else 1
        picks = drafts.get(season) if season in drafts else s.get("draft_picks")
        drafted = {(int(p["roster_id"]), str(p["player_id"])) for p in picks or []
                   if p.get("roster_id") is not None and p.get("player_id")}

        def owner_of(rid: int) -> str:
            t = teams.get(rid) or teams.get(str(rid)) or {"roster_id": rid}
            return _owner_key(season, t)

        # (rid, pid) -> weeks on that roster
        held: dict[tuple[int, str], list[int]] = {}
        for week in sorted(snaps):
            for rid, pl in snaps[week].items():
                for pid in pl:
                    held.setdefault((rid, pid), []).append(week)

        # Sub-week stints: added by a transaction but never in a snapshot for that roster.
        spans: list[tuple[int, str, int, int]] = []  # rid, pid, start, end
        for (rid, pid), weeks in held.items():
            for a, b in _runs(sorted(set(weeks))):
                spans.append((rid, pid, a, b))
        seen = set(held)
        for e in events:
            if e["added"] and (e["rid"], e["pid"]) not in seen:
                w = e["week"]
                spans.append((e["rid"], e["pid"], w, w))
                seen.add((e["rid"], e["pid"]))

        # Brief stints: on a roster before the first weekly snapshot (or between snapshots) and gone again.
        def covered(rid: int, pid: str, w: int, strict: bool) -> bool:
            return any(r == rid and q == pid and (a <= w <= b or (not strict and b == w - 1))
                       for r, q, a, b in spans)

        brief: set[tuple[int, str, int]] = set()
        for rid, pid in sorted(drafted):
            if not covered(rid, pid, first_week, True):
                spans.append((rid, pid, first_week, first_week))
                brief.add((rid, pid, first_week))
        for e in events:
            if e["added"]:
                continue
            w = max(e["week"], first_week)
            if not covered(e["rid"], e["pid"], w, False):
                spans.append((e["rid"], e["pid"], w, w))
                brief.add((e["rid"], e["pid"], w))

        pairs: list[tuple[int, dict]] = []  # (roster_id, stint)
        for rid, pid, a, b in spans:
            is_brief = (rid, pid, a) in brief and a == b
            t = teams.get(rid) or teams.get(str(rid)) or {}
            owner = owner_of(rid)
            via = _acquired(events, rid, pid, a, drafted, first_week, prev_last, owner)
            lab = player_label(players, pid)
            pairs.append((rid, {
                "player_id": pid, "player": lab["name"], "position": lab["position"],
                "owner_id": owner, "owner": t.get("name") or t.get("display_name") or owner,
                "team_name": t.get("team_name") or owner, "season": season,
                "start_week": a, "end_week": b, "weeks": 0 if is_brief else b - a + 1,
                "brief": is_brief, "acquired_via": via,
            }))
        pairs.sort(key=lambda z: (z[1]["owner"], z[1]["start_week"], z[1]["player"], z[1]["player_id"]))
        stints.extend(st for _, st in pairs)
        prev_last = {}
        for rid, st in pairs:
            cur = prev_last.get(st["player_id"])
            # Same end week: the later start is the later holder (a trade processed after that week's lock);
            # a brief stint never outranks a real one.
            key = (st["end_week"], not st["brief"], st["start_week"])
            if cur is None or key > (cur[0]["end_week"], not cur[0]["brief"], cur[0]["start_week"]):
                prev_last[st["player_id"]] = (st, rid)
    return stints


def _acquired(events, rid, pid, start, drafted, first_week, prev_last, owner) -> str:
    if (rid, pid) in drafted and start == first_week:
        return "draft"
    add = None
    for e in events:
        if e["rid"] != rid or e["pid"] != pid or e["week"] > start:
            continue
        if e["added"]:
            add = e
        elif add is not None and e["week"] < start:
            add = None  # dropped / traded away again before this stint began (same-week drops are the stint's end)
    if add is not None:
        if add["kind"] == "trade":
            return "trade"
        if add["kind"] in ("waiver", "free_agent"):
            return add["kind"]
    prev = prev_last.get(pid)
    if prev is not None and start == first_week:
        if prev[0]["owner_id"] == owner:
            return "kept"
        if prev[1] == rid:
            return "inherited"  # same roster slot, new manager: the roster was handed over
    return "unknown"


def build_network(stints: list[dict]) -> dict[str, Any]:
    """Aggregate stints into teams, players and one edge per (player, owner) pair."""
    ordered = sorted(stints, key=lambda st: (st["season"], st["start_week"]))

    owners: dict[str, dict] = {}
    pl: dict[str, dict] = {}
    edges: dict[tuple[str, str], dict] = {}
    for st in ordered:
        o = owners.setdefault(st["owner_id"], {"owner_id": st["owner_id"], "players": set(), "seasons": set()})
        o["seasons"].add(st["season"])
        o["owner"], o["team_name"] = st["owner"], st["team_name"]  # latest wins
        o["players"].add(st["player_id"])
        p = pl.setdefault(st["player_id"], {"player_id": st["player_id"], "owners": set(), "total_weeks": 0})
        p["name"], p["position"] = st["player"], st["position"]
        p["owners"].add(st["owner_id"])
        p["total_weeks"] += st["weeks"]
        e = edges.setdefault((st["player_id"], st["owner_id"]),
                             {"player_id": st["player_id"], "owner_id": st["owner_id"],
                              "seasons": [], "weeks": 0, "via": []})
        if st["season"] not in e["seasons"]:
            e["seasons"].append(st["season"])
        e["weeks"] += st["weeks"]
        if st["acquired_via"] not in e["via"]:
            e["via"].append(st["acquired_via"])

    teams = sorted(({"owner_id": o["owner_id"], "owner": o["owner"], "team_name": o["team_name"],
                     "players_count": len(o["players"]), "seasons": sorted(o["seasons"])} for o in owners.values()),
                   key=lambda t: (t["owner"], t["owner_id"]))
    players = sorted(({"player_id": p["player_id"], "name": p["name"], "position": p["position"],
                       "team_count": len(p["owners"]), "total_weeks": p["total_weeks"]} for p in pl.values()),
                     key=lambda p: (-p["team_count"], -p["total_weeks"], p["name"], p["player_id"]))
    return {"teams": teams, "players": players,
            "edges": sorted(edges.values(), key=lambda e: (e["player_id"], e["owner_id"])),
            "stints": ordered}
