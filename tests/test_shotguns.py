from __future__ import annotations

from collections import Counter

from app import db, shotguns

from .conftest import SEASON, rid_by_name


def _rule(**kw):
    return {"season": SEASON, "label": "Test rule", **kw}


def test_item_points_and_keys(items):
    assert items, "demo data should contain at least one shotgun"
    for it in items:
        if it["reason"] != "rule":
            assert it["points"] <= 0, it
    keys = [it["key"] for it in items]
    assert len(keys) == len(set(keys))
    assert {it["reason"] for it in items} <= {"zero", "negative", "empty_slot"}


def test_empty_slots_can_be_disabled(ctx, st, make_ctx):
    ctx_off = make_ctx(shotguns={"count_empty_slots": False})
    off = shotguns.detect(ctx_off, st)
    assert not [i for i in off if i["reason"] == "empty_slot"]
    on = shotguns.detect(ctx, st)
    assert len(off) <= len(on)


def test_score_less_than_team_rule(st, make_ctx):
    rule = _rule(type="score_less_than_team", owners=["Dan", "Sam"], target="Jordan")
    ctx = make_ctx(special_rules=[rule])
    found = [i for i in shotguns.detect(ctx, st) if i["reason"] == "rule"]
    dan, sam, jordan = (rid_by_name(ctx, n) for n in ("Dan", "Sam", "Jordan"))
    assert {i["roster_id"] for i in found} <= {dan, sam}
    expected = set()
    for rid in (dan, sam):
        for week, mine in st["teams"][rid]["scores"].items():
            if mine < st["teams"][jordan]["scores"][week]:
                expected.add((week, rid))
    assert {(i["week"], i["roster_id"]) for i in found} == expected
    assert len(found) == len(expected)


def test_score_below_rule_hits_everyone(ctx, st, make_ctx):
    owners = [t["display_name"] for t in ctx["teams"].values()]
    rule = _rule(type="score_below", owners=owners, points=500)
    ctx2 = make_ctx(special_rules=[rule])
    found = [i for i in shotguns.detect(ctx2, st) if i["reason"] == "rule"]
    assert len(found) == 12 * ctx2["last_completed"]
    assert {(i["week"], i["roster_id"]) for i in found} == {
        (w, r) for r in ctx2["teams"] for w in range(1, ctx2["last_completed"] + 1)}


def test_rule_for_other_season_is_ignored(st, make_ctx):
    rule = {"season": "1999", "type": "score_below", "owners": ["Dan"], "points": 500}
    ctx = make_ctx(special_rules=[rule])
    assert not [i for i in shotguns.detect(ctx, st) if i["reason"] == "rule"]


def test_leaderboard_totals(ctx, items):
    its = [dict(i) for i in items]
    board = shotguns.leaderboard(ctx, its, {})
    counts = Counter(i["roster_id"] for i in its)
    assert len(board) == 12
    for row in board:
        assert row["total"] == counts.get(row["roster_id"], 0)
        assert row["completed"] == 0
        assert row["outstanding"] == row["total"]
    assert [r["rank"] for r in board] == list(range(1, 13))
    totals = [r["total"] for r in board]
    assert totals == sorted(totals, reverse=True)


def test_toggle_updates_leaderboard(ctx, items):
    store = db.Store(":memory:")
    its = [dict(i) for i in items]
    key, rid = its[0]["key"], its[0]["roster_id"]

    assert store.toggle(SEASON, key) is True
    assert key in store.completed(SEASON)
    row = next(r for r in shotguns.leaderboard(ctx, its, store.completed(SEASON)) if r["roster_id"] == rid)
    assert row["completed"] == 1
    assert row["outstanding"] == row["total"] - 1
    assert its[0]["completed"] is True

    assert store.toggle(SEASON, key) is False
    assert store.completed(SEASON) == {}
    row = next(r for r in shotguns.leaderboard(ctx, its, store.completed(SEASON)) if r["roster_id"] == rid)
    assert row["completed"] == 0
    assert row["outstanding"] == row["total"]


def test_manual_shotguns_round_trip(ctx):
    store = db.Store(":memory:")
    created = store.add_manual(SEASON, 3, 1, "Late lineup", "Forgot to set it")
    items = db.manual_to_items(SEASON, store.manual(SEASON))
    assert [i["key"] for i in items] == [f"{SEASON}:manual:{created['id']}"]
    assert items[0]["reason"] == "manual"
    board = shotguns.leaderboard(ctx, items, {})
    assert next(r for r in board if r["roster_id"] == 1)["total"] == 1

    store.toggle(SEASON, items[0]["key"])
    store.delete_manual(SEASON, created["id"])
    assert store.manual(SEASON) == []
    assert store.completed(SEASON) == {}
    assert db.manual_to_items(SEASON, store.manual(SEASON)) == []
