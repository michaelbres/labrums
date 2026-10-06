"""Regression tests for fix round 1."""
from __future__ import annotations

import copy

import pytest

from app import articles, loader, playoffs, shotguns, stats
from app.demo import DemoClient

from .conftest import LEAGUE_ID, SEASON, rid_by_name
from .test_api import api, locked_api  # noqa: F401  (fixtures)


def _build(ctx):
    st = stats.compute(ctx)
    po = playoffs.simulate(ctx, st, sims=300)
    items = shotguns.detect(ctx, st)
    return st, po, items, articles.generate(ctx, st, po, items)


def test_catchphrase_with_braces_survives(make_ctx):
    phrase = "Brace yourselves {x} {0} {} }{ ok"
    ctx = make_ctx(owners={n: {"catchphrase": phrase}
                           for n in (t["display_name"] for t in make_ctx().get("teams", {}).values())})
    assert ctx["teams"][1]["profile"].get("catchphrase") == phrase
    _, _, _, arts = _build(ctx)
    bodies = [p for a in arts for p in a["body"]]
    assert any(phrase in p for p in bodies)


def test_catchphrase_placeholders_are_filled(make_ctx):
    ctx = make_ctx(owners={t["display_name"]: {"catchphrase": "ping {them} from {me}"}
                           for t in make_ctx()["teams"].values()})
    _, _, _, arts = _build(ctx)
    assert any("ping " in p and "{them}" not in p and "{me}" not in p for a in arts for p in a["body"])


def test_no_playoff_week_items_when_not_playing():
    client = DemoClient(current_week=18)
    from app import config
    ctx = loader.load_season(client, config.load_config(), LEAGUE_ID)
    st = stats.compute(ctx)
    items = shotguns.detect(ctx, st)
    assert not [i for i in items if i["week"] >= 15]


@pytest.mark.parametrize("week", [10, 13, 14, 15])
def test_status_is_exact(week):
    from app import config
    ctx = loader.load_season(DemoClient(current_week=week), config.load_config(), LEAGUE_ID)
    st = stats.compute(ctx)
    po = playoffs.simulate(ctx, st, sims=500)
    k = ctx["playoff_teams"]
    cur = {r: t["wins"] + 0.5 * t["ties"] for r, t in st["teams"].items()}
    left = {r: po["teams"][r]["games_left"] for r in cur}
    for rid, t in po["teams"].items():
        others = [o for o in cur if o != rid]
        clinched = sum(1 for o in others if cur[o] + left[o] >= cur[rid]) < k
        elim = sum(1 for o in others if cur[o] > cur[rid] + left[rid]) >= k
        want = "clinched" if clinched else "eliminated" if elim else "alive"
        assert t["status"] == want, (rid, t["status"], want)
        if t["status"] == "clinched":
            assert t["playoff_pct"] == 1.0
        if t["status"] == "eliminated":
            assert t["playoff_pct"] == 0.0
        if t["playoff_pct"] < 1.0:
            assert t["status"] != "clinched"


def test_duplicate_rule_owners_make_no_duplicate_keys(st, make_ctx):
    rule = {"season": SEASON, "label": "dup", "type": "score_below",
            "owners": ["Dan", "dan", "Dan", "Sam"], "points": 500}
    ctx = make_ctx(special_rules=[rule])
    items = shotguns.detect(ctx, st)
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys))
    found = [i for i in items if i["reason"] == "rule"]
    assert len(found) == 2 * ctx["last_completed"]


def test_tie_recap(ctx):
    c = copy.deepcopy(ctx)
    rows = c["matchups"][2]
    mid = rows[0]["matchup_id"]
    pair = [r for r in rows if r["matchup_id"] == mid]
    assert len(pair) == 2
    pair[1]["points"] = pair[0]["points"]
    _, _, _, arts = _build(c)
    recaps = [a for a in arts if a["type"] == "recap" and a["week"] == 2
              and {int(pair[0]["roster_id"]), int(pair[1]["roster_id"])} == set(a["teams"])]
    assert len(recaps) == 1
    assert "Tie" in recaps[0]["headline"]
    for a in arts:
        for p in [a["headline"], a["dek"], *a["body"]]:
            assert "{" not in p and "}" not in p, p
    assert not any("beat" in p or "drops to" in p for p in recaps[0]["body"])


def test_low_reason_between_zero_and_threshold(ctx, make_ctx):
    c = copy.deepcopy(make_ctx(shotguns={"threshold": 1.5}))
    row = next(r for r in c["matchups"][1] if r.get("matchup_id") is not None)
    row["starters_points"][0] = 1.0
    row["starters"][0] = next(p for p in row["starters"] if p not in (None, "", "0"))
    st = stats.compute(c)
    items = shotguns.detect(c, st)
    low = [i for i in items if i["reason"] == "low"]
    assert low
    for i in low:
        assert 0 < i["points"] <= 1.5
        assert i["label"] == "Under the 1.5-point line"
    assert all(i["points"] == 0 for i in items if i["reason"] == "zero")
    assert all(i["points"] < 0 for i in items if i["reason"] == "negative")


def test_standings_sort_counts_ties(ctx):
    st = stats.compute(ctx)
    order = [st["teams"][r] for r in st["standings"]]
    keys = [(-(t["wins"] + 0.5 * t["ties"]), -t["pf"]) for t in order]
    assert keys == sorted(keys)


def test_owner_profile_lookup_case_insensitive(client, cfg):
    c = copy.deepcopy(cfg)
    c["owners"] = {"dAN": {"nickname": "Danimal"}}
    ctx = loader.load_season(client, c, LEAGUE_ID)
    assert ctx["teams"][rid_by_name(ctx, "Dan")]["nickname"] == "Danimal"


def test_pre_season_cutoff_is_zero():
    assert loader.completed_week_cutoff({"status": "in_season", "season": "2026"},
                                        {"season": "2026", "season_type": "pre", "week": 1}) == 0
    assert loader.completed_week_cutoff({"status": "in_season", "season": "2026"},
                                        {"season": "2026", "season_type": "regular", "week": 0}) == 0


def test_all_zero_matchups_not_cached_as_final(tmp_path, monkeypatch):
    from app import sleeper
    client = sleeper.SleeperClient(tmp_path)
    calls = []

    def fake_fetch(path):
        calls.append(path)
        return [{"roster_id": 1, "points": 0}, {"roster_id": 2, "points": 0}]
    monkeypatch.setattr(client, "_fetch", fake_fetch)
    client.matchups("L", 3, final=True)
    path = client._cache_path("league/L/matchups/3")
    import json
    blob = json.loads(path.read_text())
    blob["fetched_at"] -= sleeper.LIVE_TTL + 10
    path.write_text(json.dumps(blob))
    client.matchups("L", 3, final=True)
    assert len(calls) == 2


def test_clear_cache_keeps_players(tmp_path):
    from app import sleeper
    client = sleeper.SleeperClient(tmp_path)
    client._write_cache("players/nfl", {"a": 1})
    client._write_cache("league/L", {"b": 2})
    client.clear_cache(keep_players=True)
    assert client._read_cache("players/nfl") is not None
    assert client._read_cache("league/L") is None


# ---- API ------------------------------------------------------------------
def test_manual_shotgun_validation(api):  # noqa: F811
    base = {"label": "x"}
    assert api.post("/api/season/2026/shotguns/manual", json={**base, "week": 99, "roster_id": 1}).status_code == 400
    assert api.post("/api/season/2026/shotguns/manual", json={**base, "week": 0, "roster_id": 1}).status_code == 400
    assert api.post("/api/season/2026/shotguns/manual", json={**base, "week": 2, "roster_id": 999}).status_code == 400
    assert api.post("/api/season/2026/shotguns/manual", json={**base, "week": 2, "roster_id": 1}).status_code == 200


def test_toggle_unknown_key_404(api):  # noqa: F811
    assert api.post("/api/season/2026/shotguns/nope:nope/toggle").status_code == 404


def test_toggle_manual_key_ok(api):  # noqa: F811
    mid = api.post("/api/season/2026/shotguns/manual", json={"label": "x", "week": 2, "roster_id": 1}).json()["id"]
    assert api.post(f"/api/season/2026/shotguns/2026:manual:{mid}/toggle").status_code == 200


def test_refresh_requires_admin_pin(locked_api):  # noqa: F811
    assert locked_api.post("/api/season/2026/refresh").status_code == 401
    assert locked_api.post("/api/season/2026/refresh", headers={"X-Admin-Pin": "secret"}).status_code == 200


def test_refresh_open_without_pin(api):  # noqa: F811
    assert api.post("/api/season/2026/refresh").status_code == 200
