"""The shotgun rule: start a player who scores 0 or negative, shotgun a beer.

Plus any special rules from config (e.g. three owners who owe a shotgun whenever
they score less than a given team).
"""
from __future__ import annotations

from typing import Any

from .sleeper import player_label


def _slot_names(ctx: dict) -> list[str]:
    return [s for s in ctx["roster_positions"] if s not in ("BN", "IR", "TAXI")]


def team_by_name(ctx: dict, name: str) -> int | None:
    name = str(name or "").strip().lower()
    if not name:
        return None
    for rid, t in ctx["teams"].items():
        if name in {str(t["display_name"]).lower(), str(t.get("owner_id")).lower(),
                    str(t.get("team_name", "")).lower(), str(t.get("name") or "").lower(), str(rid)}:
            return rid
    return None


_team_by_name = team_by_name


def detect(ctx: dict, st: dict) -> list[dict]:
    cfg = ctx["config"]["shotguns"]
    threshold = float(cfg.get("threshold", 0))
    count_empty = bool(cfg.get("count_empty_slots", True))
    include_playoffs = bool(cfg.get("include_playoff_weeks", True))
    season = ctx["season"]
    players = ctx["players"]
    slots = _slot_names(ctx)
    reg_weeks = set(ctx["regular_weeks"])
    items: list[dict] = []

    for week in sorted(ctx["matchups"]):
        if week > ctx["last_completed"]:
            continue
        if week not in reg_weeks and not include_playoffs:
            continue
        for r in ctx["matchups"][week]:
            rid = int(r["roster_id"])
            if rid not in ctx["teams"]:
                continue
            if r.get("matchup_id") is None:
                continue  # not playing this week (e.g. out of the playoffs)
            starters = r.get("starters") or []
            sp = r.get("starters_points") or []
            pp = r.get("players_points") or {}
            for i, pid in enumerate(starters):
                slot = slots[i] if i < len(slots) else f"SLOT{i+1}"
                if pid in (None, "", "0"):
                    if not count_empty:
                        continue
                    pts = 0.0
                    reason = "empty_slot"
                else:
                    pts = float(sp[i]) if i < len(sp) else float(pp.get(str(pid), 0) or 0)
                    if pts > threshold:
                        continue
                    reason = "negative" if pts < 0 else "zero" if pts == 0 else "low"
                lab = player_label(players, pid)
                items.append({
                    "key": f"{season}:{week}:{rid}:{lab['player_id']}:{i}",
                    "season": season, "week": week, "roster_id": rid, "slot": slot,
                    "player": lab, "points": round(pts, 2), "reason": reason,
                    "label": {"empty_slot": "Empty starting slot", "negative": "Negative points",
                              "zero": "Zero points", "low": f"Under the {threshold:g}-point line"}[reason],
                })

    # Special rules.
    for rule in ctx["config"].get("special_rules") or []:
        if rule.get("season") and str(rule["season"]) != season:
            continue
        rtype = rule.get("type")
        owners = [(team_by_name(ctx, o), o) for o in rule.get("owners") or []]
        owners = [(rid, o) for rid, o in owners if rid is not None]
        seen_owners: set[int] = set()
        owners = [(rid, o) for rid, o in owners if not (rid in seen_owners or seen_owners.add(rid))]
        if not owners:
            continue
        label = rule.get("label") or rtype
        target_rid = team_by_name(ctx, rule.get("target")) if rtype == "score_less_than_team" else None
        if rtype == "score_less_than_team" and target_rid is None:
            continue
        for week in sorted(ctx["matchups"]):
            if week > ctx["last_completed"] or (week not in reg_weeks and not include_playoffs):
                continue
            for rid, oname in owners:
                mine = st["teams"][rid]["scores"].get(week)
                if mine is None:
                    continue
                if rtype == "score_less_than_team":
                    theirs = st["teams"][target_rid]["scores"].get(week)
                    if theirs is None or rid == target_rid or mine >= theirs:
                        continue
                    tname = st["teams"][target_rid].get("name") or st["teams"][target_rid]["display_name"]
                    detail = f"Scored {mine:.2f}, {tname} scored {theirs:.2f}"
                    pkey = f"rule-{target_rid}"
                elif rtype == "score_below":
                    floor = float(rule.get("points") or 0)
                    if mine >= floor:
                        continue
                    detail = f"Scored {mine:.2f}, below the {floor:g}-point floor"
                    pkey = f"rule-{floor:g}"
                else:
                    continue
                items.append({
                    "key": f"{season}:{week}:{rid}:{pkey}:rule",
                    "season": season, "week": week, "roster_id": rid, "slot": "RULE",
                    "player": {"player_id": None, "name": label, "position": "RULE", "team": None},
                    "points": round(mine, 2), "reason": "rule", "label": label, "detail": detail,
                })
    seen_keys: set[str] = set()
    unique = []
    for it in items:
        if it["key"] in seen_keys:
            continue
        seen_keys.add(it["key"])
        unique.append(it)
    items = unique
    items.sort(key=lambda x: (x["week"], x["roster_id"], x["slot"]))
    return items


def leaderboard(ctx: dict, items: list[dict], completed: dict[str, dict]) -> list[dict]:
    rows: dict[int, dict] = {}
    for rid, t in ctx["teams"].items():
        rows[rid] = {"roster_id": rid, "display_name": t["display_name"], "name": t.get("name") or t["display_name"],
                     "team_name": t["team_name"],
                     "avatar": t["avatar"], "total": 0, "completed": 0, "outstanding": 0,
                     "by_reason": {}, "worst_week": None}
    per_week: dict[tuple[int, int], int] = {}
    for it in items:
        row = rows.get(it["roster_id"])
        if not row:
            continue
        done = it["key"] in completed
        it["completed"] = done
        it["completed_at"] = completed.get(it["key"], {}).get("completed_at")
        row["total"] += 1
        row["completed"] += int(done)
        row["outstanding"] += int(not done)
        row["by_reason"][it["reason"]] = row["by_reason"].get(it["reason"], 0) + 1
        k = (it["roster_id"], it["week"])
        per_week[k] = per_week.get(k, 0) + 1
    for (rid, week), cnt in per_week.items():
        row = rows[rid]
        if row["worst_week"] is None or cnt > row["worst_week"]["count"]:
            row["worst_week"] = {"week": week, "count": cnt}
    out = sorted(rows.values(), key=lambda r: (-r["total"], -r["outstanding"], r["name"].lower(), r["display_name"]))
    for i, r in enumerate(out):
        r["rank"] = i + 1
    return out
