"""Regression tests for fix round 4 (season start, division-aware current seeds, quote wording)."""
from __future__ import annotations

import copy
import re

from app import articles, loader, playoffs

from .test_api import api  # noqa: F401  (fixture)


def test_season_start_ignores_state_date_for_other_season(client, cfg):
    prev = loader.load_season(client, cfg, "demo2025")
    assert str(client.state()["season"]) != prev["season"]
    start = prev["season_start_ms"]
    assert start is not None and start != loader.season_start_ms(client.state(), {})
    wk2 = [int(t["created"]) for t in prev["transactions"][2]]
    assert start == min(wk2) - 7 * 86_400_000
    assert all(int(t["created"]) >= start for w, ts in prev["transactions"].items() if w >= 2 for t in ts)


def test_season_start_fallbacks():
    day = 86_400_000
    league, state = {"season": "2025"}, {"season": "2026", "season_start_date": "2026-09-01"}
    assert loader.season_start_ms(state, {}, league) is None
    assert loader.season_start_ms(state, {3: [{"created": 5 * day}], 4: [{"created": 9 * day}]}, league) == 5 * day
    assert loader.season_start_ms(state, {2: [{"created": 20 * day}], 3: [{"created": 5 * day}]}, league) == 13 * day
    same = loader.season_start_ms({"season": "2025", "season_start_date": "2025-09-01"}, {2: [{"created": day}]}, league)
    assert same == loader.season_start_ms({"season_start_date": "2025-09-01"}, {})  # state date trusted


def test_current_seeds_are_division_aware(ctx, st):
    st2 = copy.deepcopy(st)
    div1 = [r for r, t in st2["teams"].items() if t["division"] == 1]
    for r, t in st2["teams"].items():  # division 2 owns the six best records; division 1 is all 1-0
        t.update(wins=10 if t["division"] == 2 else 1, losses=0, ties=0, pf=100.0 + r, pa=100.0)
    leader = max(div1, key=lambda r: st2["teams"][r]["pf"])
    raw = sorted(st2["teams"], key=lambda r: (-st2["teams"][r]["wins"], -st2["teams"][r]["pf"]))
    assert raw.index(leader) == 6  # 7th by raw record
    seeds = playoffs.simulate(ctx, st2, sims=200)["current_seeds"]
    assert seeds[leader] is not None and seeds[leader] <= 2
    assert sorted(v for v in seeds.values() if v is not None) == list(range(1, ctx["playoff_teams"] + 1))


def test_current_seeds_in_demo(po, st):
    assert set(po["current_seeds"]) == set(st["teams"])


def test_api_in_playoff_spot_follows_seeds(api):
    data = api.get("/api/season/2026").json()
    seeds = data["playoffs"]["current_seeds"]
    for rid, t in data["teams"].items():
        assert t["current_seed"] == seeds[rid]
        assert t["in_playoff_spot"] == (seeds[rid] is not None)


def test_quotes_read_cleanly_and_pluralize(ctx, st, po, items):
    arts = articles.generate(ctx, st, po, items)
    bad = re.compile(r"[.]” said|” Said")
    for a in arts:
        for para in a["body"]:
            assert not bad.search(para), para
    quoted = [p for a in arts for p in a["body"] if p.startswith("“")]
    assert quoted and all(re.search(r"[,!?]” said \S", p) for p in quoted)
    assert not [a for a in arts if "1 Other Moves" in a["headline"]]
    assert not re.search(r"\d+ round \d+ pick", " ".join(p.replace("a 20", "") for a in arts if a["type"] == "trade" for p in a["body"]))
