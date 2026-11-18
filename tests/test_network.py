"""Player network: stints and aggregation from hand-built season dicts."""
from __future__ import annotations

from app.network import build_network, build_stints

PLAYERS = {"p1": {"full_name": "Alpha One", "position": "QB"}, "p2": {"full_name": "Bravo Two", "position": "RB"},
           "p3": {"full_name": "Charlie Three", "position": "WR"}, "p4": {"full_name": "Delta Four", "position": "TE"},
           "p5": {"full_name": "Echo Five", "position": "WR"}, "p6": {"full_name": "Foxtrot Six", "position": "K"}}


def season(year, rosters, snaps, txs=None, status="complete", current_week=None):
    """rosters: {rid: (owner_id, name, team_name)}; snaps: {week: {rid: [pids]}}; txs: {week: [tx]}."""
    return {
        "season": year, "league": {"status": status}, "players": PLAYERS, "current_week": current_week,
        "teams": {rid: {"roster_id": rid, "owner_id": o, "name": n, "team_name": tn, "players": []}
                  for rid, (o, n, tn) in rosters.items()},
        "matchups": {w: [{"roster_id": rid, "players": pl} for rid, pl in rows.items()] for w, rows in snaps.items()},
        "transactions": txs or {},
    }


def tx(kind, adds, drops=None, created=1):
    return {"type": kind, "status": "complete", "adds": adds, "drops": drops or {}, "created": created}


def by(stints, pid, owner=None, season=None):
    return [s for s in stints if s["player_id"] == pid and (owner is None or s["owner_id"] == owner)
            and (season is None or s["season"] == season)]


R24 = {1: ("uA", "Ann", "Ann FC"), 2: ("uB", "Bob", "Bob FC")}


def test_contiguous_weeks_merge_and_gap_splits():
    s = season("2024", R24, {1: {1: ["p1"], 2: []}, 2: {1: ["p1"], 2: []}, 3: {1: [], 2: ["p2"]},
                             4: {1: ["p1"], 2: ["p2"]}})
    st = build_stints([s])
    p1 = sorted(by(st, "p1"), key=lambda x: x["start_week"])
    assert [(x["start_week"], x["end_week"], x["weeks"]) for x in p1] == [(1, 2, 2), (4, 4, 1)]
    p2 = by(st, "p2")
    assert [(x["start_week"], x["end_week"]) for x in p2] == [(3, 4)]
    assert p1[0]["player"] == "Alpha One" and p1[0]["position"] == "QB" and p1[0]["owner"] == "Ann"


def test_owner_identity_across_seasons_survives_roster_and_team_rename():
    s24 = season("2024", {1: ("uA", "Ann", "Old Name")}, {1: {1: ["p1"]}})
    s25 = season("2025", {7: ("uA", "Ann", "New Name")}, {1: {7: ["p1"]}})
    st = build_stints([s24, s25])
    assert {x["owner_id"] for x in st} == {"uA"}
    net = build_network(st)
    assert len(net["edges"]) == 1
    assert net["edges"][0]["seasons"] == ["2024", "2025"] and net["edges"][0]["weeks"] == 2
    assert net["teams"] == [{"owner_id": "uA", "owner": "Ann", "team_name": "New Name", "players_count": 1,
                             "seasons": ["2024", "2025"]}]
    assert net["players"][0]["team_count"] == 1


def test_acquired_via_every_value():
    snaps = {1: {1: ["p1", "p3", "p6"], 2: ["p2"]},
             2: {1: ["p1", "p3", "p6"], 2: ["p2"]},
             3: {1: ["p1", "p3", "p6", "p4"], 2: ["p2", "p5"]},
             4: {1: ["p1", "p3", "p6", "p2"], 2: ["p5", "p4"]}}
    txs = {2: [tx("waiver", {"p5": 2})], 3: [tx("trade", {"p2": 1, "p4": 2}, {"p2": 2, "p4": 1})]}
    # p4 is added to roster 1 at week 3 via free agency before the trade; p6 has no matching move.
    txs[2].append(tx("free_agent", {"p4": 1}, created=5))
    s25 = season("2025", R24, {1: {1: ["p3"], 2: []}}, {})
    s26 = season("2026", R24, snaps, txs)
    drafts = {"2026": [{"roster_id": 1, "player_id": "p1"}]}
    # p3 finished 2025 on Ann's roster -> kept. p6 is only in 2026 with no move -> unknown.
    st = build_stints([s25, s26], drafts)
    via = lambda pid, o, season="2026": {x["start_week"]: x["acquired_via"] for x in by(st, pid, o, season)}
    assert via("p1", "uA") == {1: "draft"}
    assert via("p3", "uA") == {1: "kept"}
    assert via("p6", "uA") == {1: "unknown"}
    assert via("p5", "uB") == {3: "waiver"}
    assert via("p4", "uA") == {3: "free_agent"}
    assert via("p2", "uA") == {4: "trade"}
    assert via("p4", "uB") == {4: "trade"}


def test_sub_week_transaction_stint_and_commissioner_free_snapshot():
    # p5 is picked up by Bob in week 2 and traded to Ann in the same week; it never shows in Bob's snapshot.
    s = season("2024", R24, {1: {1: ["p1"], 2: ["p2"]}, 2: {1: ["p1"], 2: ["p2"]}, 3: {1: ["p1", "p5"], 2: ["p2"]}},
               {2: [tx("free_agent", {"p5": 2}, created=1), tx("trade", {"p5": 1}, {"p5": 2}, created=2)]})
    st = build_stints([s])
    sub = by(st, "p5", "uB")
    assert [(x["start_week"], x["end_week"], x["weeks"], x["acquired_via"]) for x in sub] == [(2, 2, 1, "free_agent")]
    ann = by(st, "p5", "uA")
    assert [(x["start_week"], x["acquired_via"]) for x in ann] == [(3, "trade")]


def test_in_progress_season_uses_current_rosters_and_ignores_future_weeks():
    s = season("2026", R24, {1: {1: ["p1"], 2: ["p2"]}, 2: {1: ["p1"], 2: ["p2"]}, 3: {1: ["p1"], 2: ["p2"]}},
               {2: [tx("waiver", {"p3": 1})]}, status="in_season", current_week=2)
    s["teams"][1]["players"] = ["p1", "p3"]   # p3 was added this week and is not in any matchup entry
    st = build_stints([s])
    assert [(x["start_week"], x["end_week"], x["acquired_via"]) for x in by(st, "p3")] == [(2, 2, "waiver")]
    assert max(x["end_week"] for x in st) == 2


def test_edge_aggregation_one_edge_per_player_owner_pair():
    s = season("2024", R24, {1: {1: ["p1"], 2: ["p2"]}, 2: {1: [], 2: ["p1", "p2"]}, 3: {1: ["p1"], 2: ["p2"]},
                             4: {1: ["p1"], 2: ["p2"]}},
               {2: [tx("trade", {"p1": 2}, {"p1": 1})], 3: [tx("trade", {"p1": 1}, {"p1": 2})]})
    net = build_network(build_stints([s]))
    edges = {(e["player_id"], e["owner_id"]): e for e in net["edges"]}
    assert len(net["edges"]) == 3
    e = edges[("p1", "uA")]
    assert e["weeks"] == 3 and e["seasons"] == ["2024"] and e["via"] == ["unknown", "trade"]
    assert edges[("p1", "uB")]["weeks"] == 1
    top = net["players"][0]
    assert (top["player_id"], top["team_count"], top["total_weeks"]) == ("p1", 2, 4)
    assert {t["owner_id"]: t["players_count"] for t in net["teams"]} == {"uA": 1, "uB": 2}
    assert len(net["stints"]) == 4
