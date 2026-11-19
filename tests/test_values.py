"""Player valuation model and power rankings: hand-built inputs."""
from __future__ import annotations

import importlib
import math

import pytest
from fastapi.testclient import TestClient

from app import values as V


def test_blend_weights_games_share_and_shrinkage():
    # full seasons: 0.55/0.30/0.15 weights
    full = [(20.0, 17, 17, 0.55), (10.0, 17, 17, 0.30), (0.0, 17, 17, 0.15)]
    b, g = V.blend_ppg(full)
    assert b == pytest.approx(0.55 * 20 + 0.30 * 10)
    assert g == pytest.approx(17)
    # half the games counts half as much
    b2, g2 = V.blend_ppg([(20.0, 8.5, 17, 0.55), (10.0, 17, 17, 0.30)])
    assert g2 == pytest.approx(0.55 * 8.5 + 0.30 * 17)
    assert b2 == pytest.approx((0.55 * 8.5 * 20 + 0.30 * 17 * 10) / g2)
    # gp is measured against games possible (a season still in progress)
    assert V.blend_ppg([(10.0, 5, 5, 1.0)])[1] == pytest.approx(17)
    # shrinkage toward replacement: PRIOR_GAMES of replacement PPG
    s, _ = V.blend_ppg([(20.0, 17, 17, 1.0)], replacement=8.0)
    assert s == pytest.approx((17 * 20 + V.PRIOR_GAMES * 8) / (17 + V.PRIOR_GAMES))
    # no games at all: exactly replacement
    assert V.blend_ppg([], replacement=8.0)[0] == pytest.approx(8.0)
    # a thin sample is pulled much closer to replacement than a full one
    thin, _ = V.blend_ppg([(30.0, 1, 17, 1.0)], replacement=8.0)
    assert thin < V.blend_ppg([(30.0, 17, 17, 1.0)], replacement=8.0)[0] - 5


def test_replacement_level_and_vorp():
    raw = {f"q{i}": ("QB", 30.0 - i, 10.0) for i in range(40)}
    raw["fluke"] = ("QB", 99.0, 1.0)          # too few games: ignored
    raw["w1"] = ("WR", 12.0, 10.0)
    repl = V.replacement_levels(raw)
    assert repl["QB"] == pytest.approx(30.0 - (V.REPLACEMENT_RANK["QB"] - 1))
    assert repl["WR"] == 12.0                 # fewer than N players: the last one
    assert repl["TE"] == 0.0                  # nobody
    assert V.vorp(15.0, 9.0) == 6.0 and V.vorp(5.0, 9.0) == 0.0


def test_age_curve_and_longevity():
    pos = "RB"
    assert V.age_curve(pos, 24) == 1.0 and V.age_curve(pos, V.PRIME_END[pos]) == 1.0
    assert V.age_curve(pos, V.CLIFF[pos]) == 0.0 and V.age_curve(pos, 40) == 0.0
    mid = (V.PRIME_END[pos] + V.CLIFF[pos]) / 2
    assert V.age_curve(pos, mid) == pytest.approx(0.5)
    full = sum(V.LONGEVITY_DISCOUNT ** t for t in range(V.LONGEVITY_YEARS))
    assert V.longevity("QB", 24) == pytest.approx(full)
    assert V.longevity("RB", 40) == pytest.approx(1.0)      # current season in full, then nothing
    assert V.longevity("RB", V.CLIFF["RB"] - 2.5) > 1.0
    assert V.longevity("RB", 30) < 0.35 * full
    assert V.longevity("QB", 33) > V.longevity("RB", 27) > V.longevity("RB", 29)
    assert V.longevity("WR", 22) > V.longevity("WR", 30)


def _stats(rows):
    return {pid: {"gp": gp, "pts_half_ppr": gp * ppg} for pid, (gp, ppg) in rows.items()}


def test_compute_production_replacement_and_value():
    players = {f"w{i}": {"position": "WR", "age": 25} for i in range(60)}
    players["old"] = {"position": "WR", "age": 40}
    players["k"] = {"position": "K", "age": 30}
    cur = _stats({**{f"w{i}": (17, 30.0 - i * 0.4) for i in range(60)}, "old": (17, 40.0)})
    prod, repl = V.compute_production(players, {"2026": cur}, "2026")
    assert "k" not in prod
    assert repl["WR"] == pytest.approx((V.REPLACEMENT_RANK["WR"] and sorted(
        [30.0 - i * 0.4 for i in range(60)] + [40.0], reverse=True)[V.REPLACEMENT_RANK["WR"] - 1]))
    assert prod["w0"]["production"] > prod["w10"]["production"] > 0
    # past the cliff: only the current season is left (t = 0 counts in full, nothing after)
    assert prod["old"]["production"] == pytest.approx(prod["old"]["vorp"])
    # one-season-only players are shrunk, not treated as having three full seasons
    assert prod["w0"]["ppg"] < 30.0


def test_fantasy_points_use_league_scoring_te_bonus_only_for_te():
    scoring = {"rec": 0.5, "rec_yd": 0.1, "rec_td": 6, "pass_int": -2, "bonus_rec_te": 0.75, "rec_fd": 0.5, "sack": 1}
    line = {"gp": 10, "rec": 10, "rec_yd": 100, "rec_td": 1, "rec_fd": 4, "bonus_rec_te": 10, "pass_int": 1, "other": 99}
    base = 10 * 0.5 + 100 * 0.1 + 6 + 4 * 0.5 - 2
    assert V.fantasy_points(line, "TE", scoring) == pytest.approx(base + 7.5)
    assert V.fantasy_points(line, "WR", scoring) == pytest.approx(base)   # bonus never applies to a WR
    assert V.fantasy_points({"pts_half_ppr": 12.5}, "WR", {}) == 12.5     # no scoring: Sleeper's own number
    players = {"te": {"position": "TE", "age": 25}}
    prod, _ = V.compute_production(players, {"2026": {"te": line}}, "2026", scoring=scoring)
    assert prod["te"]["ppg"] > 0
    ppg = (base + 7.5) / 10
    assert V.blend_ppg([(ppg, 10, 9, 0.55)])[0] == pytest.approx(ppg)


def test_fantasy_positions_fallback():
    assert V.fantasy_pos({"position": "DB", "fantasy_positions": ["DB", "WR"]}) == "WR"
    assert V.fantasy_pos({"position": "RB", "fantasy_positions": ["WR"]}) == "RB"
    assert V.fantasy_pos({"position": "K", "fantasy_positions": ["K"]}) is None
    players = {"hunter": {"position": "DB", "fantasy_positions": ["DB", "WR"], "age": 22}}
    prod, _ = V.compute_production(players, {"2026": {"hunter": {"gp": 8, "pts_half_ppr": 80.0}}}, "2026",
                                   include={"hunter"})
    assert prod["hunter"]["pos"] == "WR"


def test_blend_never_lowers_proven_player():
    curve = {"a": 2.0, "b": 0.1, "source": "fit", "n": 99}     # tiny prior
    prod = {"vet": {"production": 30.0, "games": 17.0}}
    out = V.player_values(prod, {"vet": {"years_exp": 1}}, {"vet": 1.0}, curve)
    assert out["vet"] == 30.0


def test_current_season_bye_does_not_penalise():
    st = {"a": {"gp": 9}, "b": {"gp": 8}}
    assert V.season_games_possible(st, current=True) == 8       # max - 1
    assert V.season_games_possible(st) == 9                     # past seasons: plain max
    assert V.season_games_possible({"a": {"gp": 1}}, current=True) == 1   # floor 1
    assert V.season_games_possible({"a": {"gp": 17}}, current=True) == 17  # finished season
    # a player with every game but the bye has a full share (capped at 1)
    assert V.blend_ppg([(10.0, 9, 8, 1.0)])[1] == pytest.approx(17)


def test_fit_is_monotone_and_recovers_curve():
    samples = [(float(s), 20.0 * math.exp(-0.1 * s) + (0.3 if s % 2 else -0.3)) for s in range(1, 41) for _ in range(2)]
    c = V.fit_pick_curve(samples)
    assert c["source"] == "fit" and c["n"] == 80
    assert c["a"] == pytest.approx(20.0, rel=0.1) and c["b"] == pytest.approx(0.1, rel=0.1)
    vals = [V.curve_value(c, s) for s in range(1, 41)]
    assert all(x > y for x, y in zip(vals, vals[1:]))


def test_fit_falls_back_on_thin_or_flat_data():
    thin = V.fit_pick_curve([(1.0, 9.0), (2.0, 8.0)])
    assert thin["source"] == "fallback" and (thin["a"], thin["b"]) == V.CURVE_FALLBACK
    flat = V.fit_pick_curve([(float(s), 0.0) for s in range(1, 60)])
    assert flat["source"] == "fallback"


def test_rookie_samples_only_old_complete_rookie_drafts():
    prod = {"p1": {"production": 12.0}, "p2": {"production": 3.0}}
    mk = lambda season, rounds, status="complete", picks=None: {  # noqa: E731
        "season": season, "rounds": rounds, "status": status, "picks": picks or [{"pick_no": 1, "player_id": "p1"}, {"pick_no": 2, "player_id": "p2"}]}
    drafts = [mk("2025", 4), mk("2026", 4), mk("2023", 16), mk("2024", 4, "drafting")]
    assert V.rookie_samples(drafts, prod, "2026") == [(1.0, 12.0), (2.0, 3.0)]
    assert V.draft_slots(drafts, "2026") == {"p1": 1.0, "p2": 2.0}   # 2026 draft counts for the prior


def test_young_player_prior_blend():
    curve = {"a": 20.0, "b": 0.1, "source": "fit", "n": 99}
    prior = V.curve_value(curve, 3)
    prod = {"rook": {"production": 0.0, "games": 0.0}, "vet": {"production": 10.0, "games": 17.0},
            "old": {"production": 10.0, "games": 17.0}, "udfa": {"production": 10.0, "games": 17.0}}
    players = {"rook": {"years_exp": 0}, "vet": {"years_exp": 1}, "old": {"years_exp": 6}, "udfa": {"years_exp": 1}}
    slots = {"rook": 3.0, "vet": 3.0, "old": 3.0}
    out = V.player_values(prod, players, slots, curve)
    assert out["rook"] == pytest.approx(prior)                       # no games: all prior
    assert out["vet"] == pytest.approx(0.5 * 10 + 0.5 * prior)       # 17 games: w = 0.5
    assert out["old"] == 10.0 and out["udfa"] == 10.0                # too experienced / never drafted here


def test_pick_ownership_traded_twice_and_back():
    traded = [
        # A's 2027 1st: A -> B, then B -> C
        {"season": "2027", "round": 1, "roster_id": 1, "owner_id": 2, "previous_owner_id": 1},
        {"season": "2027", "round": 1, "roster_id": 1, "owner_id": 3, "previous_owner_id": 2},
        # B's 2027 2nd: B -> C, then C -> B (back home)
        {"season": "2027", "round": 2, "roster_id": 2, "owner_id": 3, "previous_owner_id": 2},
        {"season": "2027", "round": 2, "roster_id": 2, "owner_id": 2, "previous_owner_id": 3},
        # single trade, listed out of order relative to chain logic
        {"season": "2028", "round": 3, "roster_id": 3, "owner_id": 1, "previous_owner_id": 3},
        {"season": "2026", "round": 1, "roster_id": 1, "owner_id": 2, "previous_owner_id": 1},  # past draft: ignored
    ]
    o = V.pick_owners(traded, [1, 2, 3], ["2027", "2028"], 4)
    assert len(o) == 3 * 4 * 2
    assert o[("2027", 1, 1)] == 3
    assert o[("2027", 2, 2)] == 2
    assert o[("2028", 3, 3)] == 1
    assert o[("2027", 1, 2)] == 2 and o[("2028", 4, 1)] == 1        # untouched picks stay home


def test_future_seasons_derived_from_drafts():
    drafts = [{"season": "2026", "rounds": 4, "status": "complete"}, {"season": "2023", "rounds": 16, "status": "complete"}]
    assert V.future_seasons(drafts, [], "2026") == ["2027", "2028", "2029"]
    assert V.future_seasons(drafts, [{"season": "2030"}], "2026") == ["2027", "2028", "2029", "2030"]
    assert V.future_seasons([], [], "2026") == ["2026", "2027", "2028"]     # no draft yet: current one is pending


def test_projected_slot_ordering():
    order = [7, 3, 9]                       # worst first
    s = [V.projected_slot(1, r, order, 3, True) for r in order]
    assert s == [1, 2, 3]
    assert V.projected_slot(2, 7, order, 3, True) == 4
    assert V.projected_slot(2, 7, order, 3, True, snake=True) == 6
    assert V.projected_slot(1, 7, order, 10, False) == 5.5            # later drafts: middle of the round
    assert V.projected_slot(4, 7, order, 10, False) == 35.5


def test_team_aggregation_and_ranks():
    players = {}
    stats = {}
    for i in range(40):
        players[f"w{i}"] = {"position": "WR", "age": 24, "full_name": f"Wide {i}", "team": "AAA"}
        stats[f"w{i}"] = {"gp": 17, "pts_half_ppr": 17 * (30.0 - i * 0.5)}
    for i in range(40):
        players[f"q{i}"] = {"position": "QB", "age": 25, "full_name": f"Quarter Back {i}", "team": "BBB"}
        stats[f"q{i}"] = {"gp": 17, "pts_half_ppr": 17 * (30.0 - i * 0.5)}
    players["k1"] = {"position": "K", "age": 25}
    rosters = {1: {"name": "Ann", "team_name": "A", "players": ["w0", "w1", "q0", "k1"]},
               2: {"name": "Bob", "team_name": "B", "players": ["w2", "w39"]},
               3: {"name": "Cy", "team_name": "C", "players": []}}
    traded = [{"season": "2027", "round": 1, "roster_id": 3, "owner_id": 2, "previous_owner_id": 3}]
    drafts = [{"season": "2026", "rounds": 2, "status": "complete", "type": "linear", "picks": []}]
    out = V.build_power_rankings(rosters, players, {"2026": stats}, drafts, traded, standings=[1, 2, 3], current_season="2026")
    by = {t["roster_id"]: t for t in out["teams"]}
    assert out["future_seasons"] == ["2027", "2028", "2029"] and out["rounds"] == 2
    assert all(len(t["picks"]) for t in by.values()) and sum(len(t["picks"]) for t in by.values()) == 3 * 2 * 3
    assert len(by[2]["picks"]) == 7 and len(by[3]["picks"]) == 5
    # worst team (3) picks first in the next draft; Bob owns that pick
    p = next(x for x in by[2]["picks"] if x["season"] == "2027" and x["round"] == 1 and x["original_roster_id"] == 3)
    assert p["slot"] == 1 and p["traded"] and p["original"] == "Cy"
    p_later = next(x for x in by[1]["picks"] if x["season"] == "2028" and x["round"] == 1)
    assert p_later["slot"] == 2.0   # mid-round for later drafts
    p29 = next(x for x in by[1]["picks"] if x["season"] == "2029" and x["round"] == 1)
    assert p29["slot"] == 2.0 and p29["value"] < p_later["value"]   # same slot, further away: discounted
    v1 = by[1]["values"]
    assert v1["WR"] > 0 and v1["QB"] > 0 and v1["TE"] == 0 and v1["RB"] == 0
    assert v1["players"] == pytest.approx(v1["QB"] + v1["WR"], abs=0.11)
    assert v1["combined"] == pytest.approx(v1["players"] + v1["picks"], abs=0.11)
    assert [t["roster_id"] for t in out["teams"]][0] == 1 and by[1]["ranks"]["combined"] == 1
    assert by[1]["ranks"]["players"] == 1 and by[1]["ranks"]["WR"] == 1 and by[2]["ranks"]["WR"] == 2
    assert by[2]["ranks"]["picks"] == 1                      # owns an extra early pick
    assert sorted(t["ranks"]["QB"] for t in out["teams"]) == [1, 2, 3]
    names = [x["name"] for x in out["players"]]
    assert names[0] in ("Quarter Back 0", "Wide 0")
    assert all(x["value"] > 0 for x in out["players"]) and "k1" not in {x["player_id"] for x in out["players"]}
    assert [x["rank"] for x in out["players"]] == list(range(1, len(out["players"]) + 1))
    assert next(x for x in out["players"] if x["player_id"] == "w1")["pos_rank"] == 2


def test_api_power_rankings_demo(monkeypatch):
    monkeypatch.setenv("LABRUMS_DEMO", "1")
    monkeypatch.setenv("LABRUMS_DEMO_DB", "memory")
    import app.main as main
    main = importlib.reload(main)
    with TestClient(main.app) as c:
        r = c.get("/api/power-rankings")
        assert r.status_code == 200
        d = r.json()
        assert len(d["teams"]) == 12 and d["curve"]["source"] in ("fit", "fallback")
        assert sum(len(t["picks"]) for t in d["teams"]) == 12 * d["rounds"] * len(d["future_seasons"])
        assert sorted(t["ranks"]["combined"] for t in d["teams"]) == list(range(1, 13))
        assert d["players"] and d["players"][0]["rank"] == 1
        assert c.get("/api/power-rankings").json() == d      # cached, stable
        # essential data failing -> 503, nothing cached
        main.state._power = None

        def boom(*a, **k):
            raise main.SleeperError("down")
        monkeypatch.setattr(main.state.client, "season_stats", boom)
        assert c.get("/api/power-rankings").status_code == 503


def test_stale_players_blob_is_refetched_and_stats_trimmed(tmp_path):
    from app import sleeper as S
    c = S.SleeperClient(tmp_path)
    # a blob written by older code (old key, no years_exp / fantasy_positions) must not be reused
    c._write_cache("players/nfl", {"1": {"full_name": "Old Blob", "position": "WR"}})
    raw = {"1": {"full_name": "New", "position": "DB", "fantasy_positions": ["DB", "WR"], "years_exp": 1, "junk": 5}}
    calls = []
    c._fetch = lambda path: calls.append(path) or raw
    p = c.players()
    assert calls == ["players/nfl"] and p["1"]["fantasy_positions"] == ["DB", "WR"] and p["1"]["years_exp"] == 1
    assert "junk" not in p["1"]
    # stats: keeps gp + scoring fields only, under a versioned key
    rawst = {"1": {"gp": 5, "rec": 30, "bonus_rec_te": 30, "rec_ypr": 11.2, "def_td": 2, "pts_half_ppr": 99},
             "2": {"gp": 0, "rec": 1}, "3": {"gp": 4, "sack": 3}}
    c._fetch = lambda path: calls.append(path) or rawst
    st = c.season_stats("2026")
    assert st == {"1": {"rec": 30, "bonus_rec_te": 30, "gp": 5}}
    assert c._read_cache("stats/nfl/regular/2026/v2") is not None and c._read_cache("stats/nfl/regular/2026") is None
