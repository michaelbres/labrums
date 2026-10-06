from __future__ import annotations

import pytest

from app import playoffs


def test_playoff_pct_bounds(po):
    assert len(po["teams"]) == 12
    for t in po["teams"].values():
        assert 0 <= t["playoff_pct"] <= 1


def test_playoff_pct_sums_to_spots(po):
    total = sum(t["playoff_pct"] for t in po["teams"].values())
    assert total == pytest.approx(6, abs=0.05)


def test_seed_dist_sums_to_one(po):
    for t in po["teams"].values():
        assert sum(t["seed_dist"]) == pytest.approx(1, abs=0.01)


def test_unbeaten_team_has_best_odds(st, po):
    unbeaten = [rid for rid, t in st["teams"].items() if t["wins"] == 6 and t["losses"] == 0]
    if not unbeaten:
        pytest.skip("no 6-0 team in this fixture")
    best = max(po["teams"].values(), key=lambda t: t["playoff_pct"])["playoff_pct"]
    top = max(po["teams"][r]["playoff_pct"] for r in unbeaten)
    assert top == best


def test_next_game_conditional_odds(st, po):
    assert po["next_week"] == 7
    playing = {r for g in st["schedule"][7] for r in (g["a"], g["b"])}
    assert len(playing) == 12
    for rid in playing:
        cond = po["teams"][rid]["next_game"]
        assert cond is not None, rid
        if cond["if_win"] is not None and cond["if_loss"] is not None:
            assert cond["if_win"] >= cond["if_loss"], rid


def test_deterministic_with_same_seed(ctx, st):
    a = playoffs.simulate(ctx, st, sims=500, seed=123)
    b = playoffs.simulate(ctx, st, sims=500, seed=123)
    assert a == b


def test_different_seed_changes_output(ctx, st):
    a = playoffs.simulate(ctx, st, sims=500, seed=1)
    b = playoffs.simulate(ctx, st, sims=500, seed=2)
    assert a != b
