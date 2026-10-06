"""Regression tests for fix round 3 (live league: divisions, offseason, seeding)."""
from __future__ import annotations

import copy

import pytest

from app import articles, config, loader, playoffs, stats
from app.demo import DemoClient

from .conftest import LEAGUE_ID


def _arts(ctx):
    st = stats.compute(ctx)
    po = playoffs.simulate(ctx, st, sims=300)
    return articles.generate(ctx, st, po, [])


def test_schedule_has_only_regular_season_weeks(ctx):
    c = copy.deepcopy(ctx)
    for week in (15, 16, 17):  # Sleeper pre-fills playoff weeks with matchup ids
        for i, row in enumerate(c["matchups"][week]):
            row["matchup_id"] = i // 2 + 1
    st = stats.compute(c)
    assert st["schedule"]
    assert max(st["schedule"]) <= 14 and min(st["schedule"]) > c["last_completed"]


def test_offseason_trades_make_one_article(ctx, arts):
    off = [a for a in arts if a["type"] == "offseason"]
    assert len(off) == 1
    assert off[0]["week"] == 1
    assert off[0]["headline"].startswith("Offseason Report: 4 Trades, 6 Pickups")
    trades = [a for a in arts if a["type"] == "trade"]
    assert sorted(a["week"] for a in trades) == [2, 4, 6]  # in-season trades keep their own articles


def test_commissioner_and_failed_transactions_ignored(ctx):
    c = copy.deepcopy(ctx)
    for txs in c["transactions"].values():
        for t in txs:
            assert t["type"] != "commissioner" and t["status"] == "complete"
    base = [a["headline"] for a in _arts(c)]
    # Inject junk straight into ctx (bypassing the loader filter): the newsroom must also skip it.
    trade = next(t for t in c["transactions"][2] if t["type"] == "trade")
    c["transactions"][2].append(dict(trade, transaction_id="x1", status="failed"))
    c["transactions"][1].append(dict(trade, transaction_id="x2", status="failed", created=1))
    c["transactions"][1].append(dict(trade, transaction_id="x3", type="commissioner", created=1))
    assert [a["headline"] for a in _arts(c)] == base


def test_in_season_trade_still_gets_article(ctx, arts):
    tx = next(t for t in ctx["transactions"][2] if t["type"] == "trade")
    assert any(a["type"] == "trade" and a["week"] == 2 and set(a["teams"]) == {int(x) for x in tx["roster_ids"]} for a in arts)


def test_offseason_not_split_without_season_start(ctx):
    c = copy.deepcopy(ctx)
    c["season_start_ms"] = None
    arts = _arts(c)
    assert not [a for a in arts if a["type"] == "offseason"]


def test_waivers_ignore_offseason(ctx, arts):
    wv = [a for a in arts if a["type"] == "waiver"]
    assert wv and all(a["week"] != 1 or "Offseason" not in a["headline"] for a in wv)
    start = ctx["season_start_ms"]
    assert start and all(t["created"] >= start for t in ctx["transactions"][2])


def test_divisions_on_ctx_and_stats(ctx, st):
    assert ctx["divisions"] == {1: "Odds", 2: "Evens"}
    for t in st["teams"].values():
        assert t["division_name"] in ("Odds", "Evens")
        assert t["division_record"]
    members = [r for rids in st["division_standings"].values() for r in rids]
    assert sorted(members) == sorted(st["teams"])
    for d, rids in st["division_standings"].items():
        assert st["division_leaders"][d] == rids[0]
        ranks = [st["teams"][r]["rank"] for r in rids]
        assert ranks == sorted(ranks)


def test_division_record_counts_only_division_games(ctx, st):
    for rid, t in st["teams"].items():
        w = l = tie = 0
        for g in st["games"]:
            if not g["regular"] or rid not in (g["a"], g["b"]):
                continue
            o = g["b"] if g["a"] == rid else g["a"]
            if st["teams"][o]["division"] != t["division"]:
                continue
            if g["winner"] is None:
                tie += 1
            elif g["winner"] == rid:
                w += 1
            else:
                l += 1
        assert t["division_record"] == f"{w}-{l}" + (f"-{tie}" if tie else "")


def test_pa_is_third_tiebreak():
    teams = {i: {"roster_id": i, "display_name": f"T{i}", "wins": 0, "losses": 0, "ties": 0, "pf": 0, "pa": 0,
                 "players": [], "starters": [], "profile": {}, "division": None, "ppts": None} for i in (1, 2, 3, 4)}
    rows = [{"roster_id": 1, "matchup_id": 1, "points": 100}, {"roster_id": 2, "matchup_id": 1, "points": 90},
            {"roster_id": 3, "matchup_id": 2, "points": 100}, {"roster_id": 4, "matchup_id": 2, "points": 50}]
    ctx = {"teams": teams, "players": {}, "roster_positions": [], "matchups": {1: rows}, "regular_weeks": [1],
           "last_completed": 1, "playoff_teams": 2, "divisions": {}}
    st = stats.compute(ctx)
    # Teams 1 and 3 tie on wins and PF; team 1 faced the higher-scoring opponent, so it advances.
    assert st["standings"][:2] == [1, 3]


def test_division_winner_gets_bye_even_with_worse_record():
    ctx = loader.load_season(DemoClient(current_week=18), config.load_config(), LEAGUE_ID)
    order = stats.compute(ctx)["standings"]
    for i, rid in enumerate(order):  # division 1 = the six worst teams, division 2 = the six best
        ctx["teams"][rid]["division"] = 1 if i >= 6 else 2
    st = stats.compute(ctx)
    po = playoffs.simulate(ctx, st, sims=400)
    weak_winner = st["division_leaders"][1]
    assert st["teams"][weak_winner]["rank"] == 7
    p = po["teams"][weak_winner]
    assert all(po["teams"][r]["games_left"] == 0 for r in po["teams"])
    assert sum(p["seed_dist"][2:]) == 0 and sum(p["seed_dist"][:2]) == pytest.approx(1)
    assert p["bye_pct"] == p["playoff_pct"] == 1.0
    # The 6th-best record, in the stronger division, is shut out by the 7th-best team's division title.
    assert po["teams"][order[5]]["playoff_pct"] == 0.0
    assert po["teams"][order[5]]["status"] == "eliminated"
    assert "Division winners seeded 1-2" in po["seeding_rule"]


def test_seeding_rule_off_without_divisions():
    ctx = loader.load_season(DemoClient(current_week=18), config.load_config(), LEAGUE_ID)
    ctx["config"]["playoffs"]["division_winners_top_seeds"] = False
    st = stats.compute(ctx)
    po = playoffs.simulate(ctx, st, sims=200)
    assert "Division" not in po["seeding_rule"]
    for i, rid in enumerate(st["standings"]):
        assert po["teams"][rid]["playoff_pct"] == (1.0 if i < 6 else 0.0)


def test_empty_owner_profiles_are_not_set(make_ctx):
    empty = {"nickname": "", "bio": "", "traits": [], "catchphrase": ""}
    names = [t["display_name"] for t in make_ctx()["teams"].values()]
    ctx = make_ctx(owners={n: dict(empty) for n in names})
    assert all(not t["nickname"] and not t["profile"] for t in ctx["teams"].values())
    arts = _arts(ctx)
    text = "\n".join(p for a in arts for p in [a["headline"], a["dek"], *a["body"]])
    assert "“”" not in text and "“ ”" not in text
    assert "” said " in text


def test_config_yaml_has_blank_live_owners():
    cfg = config.load_config()
    for name in ("michaelbreslow", "PatrickHanrahan", "JimmyWoods10", "bowieshreiber", "trottner",
                 "asinagra25", "styerech", "cianmahoney", "ncarney7502", "colonbuns"):
        assert name in cfg["owners"] and cfg["owners"][name] == {}
    assert cfg["playoffs"]["division_winners_top_seeds"] == "auto"


def test_ppts_overrides_greedy_optimal(ctx):
    c = copy.deepcopy(ctx)
    c["teams"][1]["ppts"] = 5000.0
    st = stats.compute(c)
    assert st["teams"][1]["optimal_pf"] == 5000.0
    assert st["teams"][1]["lineup_efficiency"] == pytest.approx(st["teams"][1]["pf"] / 5000.0, abs=1e-3)
    assert st["teams"][2]["optimal_pf"] < 5000.0  # others fall back to the greedy calc
