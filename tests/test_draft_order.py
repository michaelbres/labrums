"""Projected rookie draft order: the max-PF rule (every team, lowest first), the simulation block, the payload."""
from __future__ import annotations

import importlib

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import draft_order as D, playoffs, values as V


# ---- the ordering rule ---------------------------------------------------------------------------------------
def picks(rows):
    return [r["roster_id"] for r in rows]


# Real Sleeper numbers (roster settings.ppts = regular-season max PF) and the real rookie draft order that followed
# (draft.slot_to_roster_id, slot 1..10). Verified live against the league's 2023, 2024 and 2025 seasons.
REAL = {
    "2025->2026": ({10: 2046.89, 8: 2068.78, 6: 2182.64, 4: 2255.06, 9: 2368.6, 2: 2431.53, 7: 2433.67, 1: 2535.09,
                    5: 2680.46, 3: 2749.42}, [10, 8, 6, 4, 9, 2, 7, 1, 5, 3]),
    "2024->2025": ({4: 2232.06, 1: 2249.24, 6: 2273.86, 10: 2289.48, 3: 2290.1, 9: 2390.29, 7: 2500.31, 8: 2521.11,
                    2: 2576.91, 5: 2579.94}, [4, 1, 6, 10, 3, 9, 7, 8, 2, 5]),
    "2023->2024": ({1: 2045.8, 7: 2208.14, 9: 2282.34, 10: 2293.44, 6: 2299.14, 2: 2384.54, 8: 2451.52, 4: 2483.28,
                    5: 2527.16, 3: 2596.54}, [1, 7, 9, 10, 6, 2, 8, 4, 5, 3]),
}


@pytest.mark.parametrize("key", sorted(REAL))
def test_rule_reproduces_the_real_rookie_draft_orders(key):
    maxpf, real = REAL[key]
    rows = D.order_picks(maxpf)
    assert picks(rows) == real
    assert [r["pick"] for r in rows] == list(range(1, 11))


def test_gap_to_next_pick():
    rows = D.order_picks({1: 100.0, 2: 90.0, 3: 95.5})
    assert picks(rows) == [2, 3, 1]
    assert [r["gap_to_next"] for r in rows] == [5.5, 4.5, None]


def test_ties_worse_record_first_then_lower_pf_then_roster_id():
    maxpf = {1: 100, 2: 100, 3: 100, 4: 100, 5: 50}
    wins = {1: 9, 2: 4, 3: 4, 4: 4, 5: 7}
    pf = {1: 1, 2: 20, 3: 10, 4: 10, 5: 1}
    assert picks(D.order_picks(maxpf, wins, pf)) == [5, 3, 4, 2, 1]


@pytest.mark.parametrize("n", [1, 4, 10, 12, 14])
def test_any_league_size_is_a_permutation_in_max_pf_order(n):
    rng = np.random.default_rng(n)
    pf = {r: float(rng.integers(1000, 2000)) for r in range(1, n + 1)}
    rows = D.order_picks(pf)
    assert sorted(picks(rows)) == sorted(pf)
    assert [r["max_pf"] for r in rows] == sorted(pf.values())


def test_numpy_ranking_matches_reference():
    rng = np.random.default_rng(5)
    n = 10
    for _ in range(30):
        pf = rng.integers(1000, 1100, n).astype(float)            # many ties on purpose
        wins = rng.integers(0, 14, n).astype(float)
        ptf = rng.integers(0, 3, n).astype(float)
        order, slot = D.rank_order(pf[None, :], wins, ptf)
        ref = D.order_picks({i + 1: pf[i] for i in range(n)}, {i + 1: wins[i] for i in range(n)},
                            {i + 1: ptf[i] for i in range(n)})
        assert [int(i) + 1 for i in order[0]] == picks(ref)
        assert [int(slot[0, i]) for i in range(n)] == [next(r["pick"] for r in ref if r["roster_id"] == i + 1) for i in range(n)]


# ---- the block: demo league, determinism, final ---------------------------------------------------------------
def _block(ctx, st, sims=800, seed=42):
    cap: dict = {}
    po = playoffs.simulate(ctx, st, sims=sims, seed=seed, capture=cap)
    return po, D.build_block(ctx, st, po, cap)


def test_capture_does_not_change_playoff_odds(ctx, st):
    plain = playoffs.simulate(ctx, st, sims=500, seed=9)
    cap: dict = {}
    assert playoffs.simulate(ctx, st, sims=500, seed=9, capture=cap) == plain


def test_block_deterministic_and_probabilities_sum_to_one(ctx, st):
    _, a = _block(ctx, st)
    _, b = _block(ctx, st)
    assert a == b
    _, c = _block(ctx, st, seed=7)
    assert c["simulated"]["order"] != a["simulated"]["order"]
    n = a["teams"]
    assert n == 12 and a["status"] == "projected"
    odds = np.array([r["slot_odds"] for r in a["simulated"]["order"]])
    assert odds.shape == (n, n)
    assert np.allclose(odds.sum(axis=1), 1, atol=1e-3)          # per team
    assert np.allclose(odds.sum(axis=0), 1, atol=1e-2)          # per slot (rounding of 4 dp)
    exp = [r["expected_pick"] for r in a["simulated"]["order"]]
    assert exp == sorted(exp) and sum(exp) == pytest.approx(n * (n + 1) / 2, abs=0.1)
    assert sorted(r["roster_id"] for r in a["simulated"]["order"]) == sorted(r["roster_id"] for r in a["today"]["order"])
    today = a["today"]["order"]       # every team, lowest max PF first; playoff seeding plays no part
    assert [r["max_pf"] for r in today] == sorted(r["max_pf"] for r in today)
    assert today[-1]["gap_to_next"] is None and all(r["gap_to_next"] >= 0 for r in today[:-1])


def test_max_pf_in_stats_matches_computed_when_no_sleeper_value(ctx, st):
    for t in st["teams"].values():
        assert t["max_pf"] >= t["pf"] - 0.01 and t["max_pf_source"] in ("sleeper", "computed")


def _tiny(reg_over: bool):
    rids = [1, 2, 3, 4]
    maxpf = {1: 1500.0, 2: 1600.0, 3: 1400.0, 4: 1700.0}
    teams = {r: {"max_pf": maxpf[r], "pf": maxpf[r] * 0.85, "wins": 5, "ties": 0, "max_pf_source": "sleeper",
                 "ppts": maxpf[r], "max_pf_calc": maxpf[r]} for r in rids}
    S = 200
    cap = {"rids": rids, "pf": np.tile([t["pf"] for t in teams.values()], (S, 1)),
           "base_pf": np.array([t["pf"] for t in teams.values()]), "sims": S}
    return {"season": "2026"}, {"teams": teams}, {"next_week": None if reg_over else 12}, cap


def test_regular_season_over_is_final_with_no_simulation():
    ctx, st, po, cap = _tiny(True)
    b = D.build_block(ctx, st, po, cap)
    assert b["status"] == "final" and b["simulated"]["locked"] and b["simulated"]["sims"] == 0
    assert [r["roster_id"] for r in b["today"]["order"]] == [3, 1, 2, 4]
    assert [r["roster_id"] for r in b["simulated"]["order"]] == [3, 1, 2, 4]
    assert all(max(r["slot_odds"]) == 1.0 for r in b["simulated"]["order"])


def test_games_left_means_projected_and_flat_scoring_keeps_the_order():
    ctx, st, po, cap = _tiny(False)
    b = D.build_block(ctx, st, po, cap)       # no simulated scoring beyond today's: the to-date order holds
    assert b["status"] == "projected" and b["simulated"]["sims"] == 200
    assert [r["roster_id"] for r in b["simulated"]["order"]] == [3, 1, 2, 4]


def test_mixed_max_pf_sources_are_flagged():
    ctx, st, po, cap = _tiny(True)
    st["teams"][1]["max_pf_source"] = "computed"
    assert D.build_block(ctx, st, po, cap)["notes"]


# ---- API payload, demo mode ---------------------------------------------------------------------------------
@pytest.fixture
def demo_main(monkeypatch):
    monkeypatch.setenv("LABRUMS_DEMO", "1")
    monkeypatch.setenv("LABRUMS_DEMO_DB", "memory")
    import app.main as main
    return importlib.reload(main)


def test_api_season_has_draft_order(demo_main):
    with TestClient(demo_main.app) as c:
        d = c.get("/api/season/2026").json()["draft_order"]
        assert d["season"] == "2027" and d["status"] == "projected"
        assert len(d["today"]["order"]) == len(d["simulated"]["order"]) == d["teams"] == 12
        assert sorted(r["pick"] for r in d["simulated"]["order"]) == list(range(1, 13))
        assert all(abs(sum(r["slot_odds"]) - 1) < 1e-3 for r in d["simulated"]["order"])
        assert set(d["max_pf"]) == {str(r["roster_id"]) for r in d["today"]["order"]}


def test_power_uses_simulated_order(demo_main):
    with TestClient(demo_main.app) as c:
        dro = c.get("/api/season/2026").json()["draft_order"]
        pw = c.get("/api/power-rankings").json()
        assert pw["pick_order_source"] == "simulated"
        exp = {r["roster_id"]: r["expected_pick"] for r in dro["simulated"]["order"]}
        nxt = dro["season"]
        picks_r1 = [p for t in pw["teams"] for p in t["picks"] if p["season"] == nxt and p["round"] == 1]
        assert len(picks_r1) == 12
        for p in picks_r1:
            assert p["slot"] == pytest.approx(exp[p["original_roster_id"]], abs=0.06)
        assert pw["next_draft_order"][0] == dro["simulated"]["order"][0]["roster_id"]


# ---- pick valuation -------------------------------------------------------------------------------------------
def test_projected_slot_uses_expected_pick_for_next_draft_only():
    order = [7, 3, 9]
    ep = {7: 2.4, 3: 1.2, 9: 3.0}
    assert V.projected_slot(1, 7, order, 3, True, expected_picks=ep) == 2.4
    assert V.projected_slot(2, 3, order, 3, True, expected_picks=ep) == 4.2
    assert V.projected_slot(1, 7, order, 10, False, expected_picks=ep) == 5.5          # later years stay mid-round
    assert V.projected_slot(1, 7, order, 3, True, expected_picks=None) == 1            # fallback: reverse standings


def test_pick_values_follow_expected_order_not_standings():
    rosters = {1: {"name": "A", "team_name": "a", "players": []}, 2: {"name": "B", "team_name": "b", "players": []},
               3: {"name": "C", "team_name": "c", "players": []}}
    drafts = [{"season": "2026", "rounds": 1, "status": "complete", "type": "linear", "picks": []}]
    base = dict(players={}, stats={"2026": {}}, drafts=drafts, traded=[], standings=[1, 2, 3], current_season="2026")
    plain = V.build_power_rankings(rosters, **base)
    sim = V.build_power_rankings(rosters, **base, expected_picks={1: 3.0, 2: 1.0, 3: 2.0})
    slot = lambda out, rid: next(p["slot"] for t in out["teams"] for p in t["picks"]
                                 if p["season"] == "2027" and p["round"] == 1 and p["original_roster_id"] == rid)
    assert [slot(plain, r) for r in (1, 2, 3)] == [3, 2, 1]        # reverse standings: team 3 picks first
    assert [slot(sim, r) for r in (1, 2, 3)] == [3, 1, 2]
    val = lambda out, rid: next(t["values"]["picks"] for t in out["teams"] if t["roster_id"] == rid)
    assert val(sim, 2) > val(sim, 3) > val(sim, 1)
    assert sim["next_draft_order"] == [2, 3, 1] and sim["pick_order_source"] == "simulated"
