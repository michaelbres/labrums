"""Projected rookie draft order: the pure ordering rule, the bracket, locking real results, and the payload."""
from __future__ import annotations

import importlib

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import draft_order as D, playoffs, values as V


# ---- the ordering rule ---------------------------------------------------------------------------------------
def picks(rows):
    return [r["roster_id"] for r in rows]


def test_ten_team_rule_non_playoff_lowest_max_pf_first():
    pf = {1: 1900, 2: 1500, 3: 1700, 4: 1400, 5: 2000, 6: 1800, 7: 1600, 8: 1300, 9: 1650, 10: 1750}
    play = [1, 5, 6, 10, 3, 9]
    exit_round = {10: 1, 9: 1, 6: 2, 3: 2, 1: 3}       # 5 is the champion
    rows = D.order_picks(pf, play, exit_round, champion=5)
    assert picks(rows)[:4] == [8, 4, 2, 7]              # the four that missed, lowest max PF first
    # round-1 exits by max PF (9: 1650 < 10: 1750), round-2 exits (3: 1700 < 6: 1800), runner-up, champion
    assert picks(rows)[4:] == [9, 10, 3, 6, 1, 5]
    assert [r["pick"] for r in rows] == list(range(1, 11))
    assert [r["reason"] for r in rows] == ["missed"] * 4 + ["eliminated"] * 4 + ["runner_up", "champion"]
    assert rows[4]["round"] == 1 and rows[6]["round"] == 2 and rows[8]["round"] == 3


def test_same_round_tie_goes_to_lower_max_pf_and_ids_break_exact_ties():
    rows = D.order_picks({1: 10, 2: 5, 3: 5, 4: 7, 5: 1}, [1, 2, 3, 4], {2: 1, 3: 1, 4: 2}, champion=1)
    assert picks(rows) == [5, 2, 3, 4, 1]               # exact tie 2/3 -> roster id; round-2 exit before champion


def test_champion_last_runner_up_second_to_last_even_with_lowest_max_pf():
    pf = {1: 100, 2: 900, 3: 800, 4: 700}
    rows = D.order_picks(pf, [1, 2, 3, 4], {2: 1, 3: 1, 4: 2}, champion=1)
    assert picks(rows)[-2:] == [4, 1]                   # runner-up 4, champion 1 despite the lowest max PF


@pytest.mark.parametrize("n,k", [(4, 2), (6, 4), (8, 6), (10, 6), (12, 6), (12, 8), (14, 7), (10, 1), (5, 0)])
def test_any_league_size_is_a_permutation_and_non_playoff_first(n, k):
    rng = np.random.default_rng(n * 100 + k)
    rids = list(range(1, n + 1))
    pf = {r: float(rng.integers(1000, 2000)) for r in rids}
    play = [int(x) for x in rng.permutation(rids)[:k]]
    # play a real bracket in seed order to get consistent exits
    S = np.array([[r - 1 for r in play]]) if k else np.zeros((1, 0), dtype=np.int64)
    seed_of = np.full((1, n), n + 1)
    for pos, r in enumerate(play):
        seed_of[0, r - 1] = pos + 1
    lvl = D.run_bracket(S, seed_of, n, k, lambda a, b, r: seed_of[0, a] < seed_of[0, b])[0]
    R = D.rounds_for(k)
    champ = next((r for r in play if lvl[r - 1] == R + 1), None)
    ex = {r: int(lvl[r - 1]) for r in play if r != champ}
    rows = D.order_picks(pf, play, ex, champ)
    assert sorted(picks(rows)) == rids
    nonplay = [r for r in picks(rows)[: n - k]]
    assert set(nonplay) == set(rids) - set(play)
    assert nonplay == sorted(nonplay, key=lambda r: (pf[r], r))
    if k:
        assert picks(rows)[-1] == champ
    if k >= 2:
        assert rows[-2]["reason"] == "runner_up"


def test_order_picks_validates():
    with pytest.raises(ValueError):
        D.order_picks({1: 1, 2: 2}, [1, 2], {}, champion=1)       # 2 has no exit round
    with pytest.raises(ValueError):
        D.order_picks({1: 1, 2: 2}, [1], {}, champion=2)           # champion not a playoff team
    with pytest.raises(ValueError):
        D.order_picks({1: 1}, [1, 9], {9: 1}, champion=1)          # unknown playoff team


# ---- the bracket ---------------------------------------------------------------------------------------------
def test_standard_order():
    assert D.standard_order(2) == [1, 2]
    assert D.standard_order(4) == [1, 4, 2, 3]
    assert D.standard_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]
    assert [D.rounds_for(k) for k in (1, 2, 3, 4, 5, 6, 8, 9)] == [0, 1, 2, 2, 3, 3, 3, 4]


def _chalk(k, n=None, reseed=False, forced=None):
    n = n or k + 2
    S = np.array([list(range(k))])
    seed_of = np.array([list(range(1, k + 1)) + [n + 1] * (n - k)])
    return D.run_bracket(S, seed_of, n, k, lambda a, b, r: seed_of[0, a] < seed_of[0, b], reseed, forced)[0]


def test_six_team_bracket_byes_and_chalk():
    lvl = _chalk(6)
    # seeds 1,2 have byes: they cannot lose in round 1; 5 and 6 lose in round 1; chalk final 1 v 2
    assert list(lvl[:6]) == [4, 3, 2, 2, 1, 1] and list(lvl[6:]) == [0, 0]


def test_bye_team_exits_no_earlier_than_round_two():
    S = np.array([[0, 1, 2, 3, 4, 5]])
    seed_of = np.array([[1, 2, 3, 4, 5, 6]])
    lvl = D.run_bracket(S, seed_of, 6, 6, lambda a, b, r: seed_of[0, a] > seed_of[0, b])[0]   # underdogs always win
    assert lvl[0] >= 2 and lvl[1] >= 2 and lvl[4] >= 1
    assert sorted(lvl) == [1, 1, 2, 2, 3, 4]


def test_fixed_vs_reseed_differ_when_upset():
    # underdogs win round 1 (3v6 -> 6, 4v5 -> 5). Fixed: 1 meets the 4/5 winner (5), 2 meets the 3/6 winner (6).
    # Reseed: 1 meets the worst remaining seed (6), 2 meets 5.
    seeds = np.array([[0, 1, 2, 3, 4, 5]])
    seed_of = np.array([[1, 2, 3, 4, 5, 6]])
    seen = {}

    def decide(a, b, r):
        seen.setdefault(r, []).append((int(seed_of[0, a[0]]), int(seed_of[0, b[0]])))
        return seed_of[0, a] > seed_of[0, b] if r == 1 else seed_of[0, a] < seed_of[0, b]
    D.run_bracket(seeds, seed_of, 6, 6, decide, reseed=False)
    assert sorted(tuple(sorted(x)) for x in seen[2]) == [(1, 5), (2, 6)]
    seen.clear()
    D.run_bracket(seeds, seed_of, 6, 6, decide, reseed=True)
    assert sorted(tuple(sorted(x)) for x in seen[2]) == [(1, 6), (2, 5)]


def test_forced_results_win_over_the_decider():
    lvl = _chalk(6, forced=[(5, 2)])           # the 6 seed (idx 5) beat the 3 seed (idx 2) in round 1
    assert lvl[2] == 1 and lvl[5] >= 2


def test_numpy_ranking_matches_reference():
    rng = np.random.default_rng(5)
    n, k = 10, 6
    for _ in range(30):
        pf = rng.integers(1000, 1100, n).astype(float)            # many ties on purpose
        perm = rng.permutation(n)
        S = perm[None, :k]
        seed_of = np.empty((1, n), dtype=int); seed_of[0, perm] = np.arange(1, n + 1)
        lvl = D.run_bracket(S, seed_of, n, k, lambda a, b, r: rng.random(a.shape) < 0.5)
        order, slot = D._rank_levels(lvl, pf[None, :])
        champ = int(np.argmax(lvl[0])) + 1
        ex = {int(i) + 1: int(lvl[0, i]) for i in perm[:k] if int(i) + 1 != champ}
        ref = D.order_picks({i + 1: pf[i] for i in range(n)}, [int(i) + 1 for i in perm[:k]], ex, champ)
        assert [int(i) + 1 for i in order[0]] == picks(ref)
        assert [int(slot[0, i]) for i in range(n)] == [next(r["pick"] for r in ref if r["roster_id"] == i + 1) for i in range(n)]


# ---- the block: demo league, determinism, locking ---------------------------------------------------------------
def _block(ctx, st, sims=800, seed=42, bracket=None):
    cap: dict = {}
    po = playoffs.simulate(ctx, st, sims=sims, seed=seed, capture=cap)
    return po, D.build_block(ctx, st, po, cap, bracket)


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
    assert n == 12 and a["playoff_teams"] == 6 and a["status"] == "projected"
    odds = np.array([r["slot_odds"] for r in a["simulated"]["order"]])
    assert odds.shape == (n, n)
    assert np.allclose(odds.sum(axis=1), 1, atol=1e-3)          # per team
    assert np.allclose(odds.sum(axis=0), 1, atol=1e-2)          # per slot (rounding of 4 dp)
    exp = [r["expected_pick"] for r in a["simulated"]["order"]]
    assert exp == sorted(exp) and sum(exp) == pytest.approx(n * (n + 1) / 2, abs=0.1)
    assert sorted(r["roster_id"] for r in a["simulated"]["order"]) == sorted(r["roster_id"] for r in a["today"]["order"])
    # today view: those outside the playoff seeds pick first, lowest max PF first
    today = a["today"]["order"]
    assert [r["reason"] for r in today[:6]] == ["missed"] * 6
    assert [r["max_pf"] for r in today[:6]] == sorted(r["max_pf"] for r in today[:6])
    assert today[-1]["reason"] == "champion" and today[-2]["reason"] == "runner_up"


def test_max_pf_in_stats_matches_computed_when_no_sleeper_value(ctx, st):
    for t in st["teams"].values():
        assert t["max_pf"] >= t["pf"] - 0.01 and t["max_pf_source"] in ("sleeper", "computed")


def _tiny(reg_over=True):
    """6 teams, 4 make the playoffs (seeds 1-4 = rids 1-4), regular season over unless told otherwise."""
    rids = [1, 2, 3, 4, 5, 6]
    maxpf = {1: 1500.0, 2: 1600.0, 3: 1400.0, 4: 1700.0, 5: 1300.0, 6: 1200.0}
    teams = {r: {"max_pf": maxpf[r], "pf": maxpf[r] * 0.85, "max_pf_source": "computed", "ppts": None, "max_pf_calc": maxpf[r]}
             for r in rids}
    st = {"teams": teams}
    ctx = {"season": "2026", "settings": {"playoff_round_type": 0}}
    po = {"playoff_teams": 4, "current_seeds": {1: 1, 2: 2, 3: 3, 4: 4, 5: None, 6: None},
          "next_week": None if reg_over else 12}
    S = 200
    seeds = np.tile(np.arange(1, 7), (S, 1))
    cap = {"rids": rids, "seeds": seeds, "pf": np.tile([t["pf"] for t in teams.values()], (S, 1)),
           "base_pf": np.array([t["pf"] for t in teams.values()]), "mu": np.full(6, 100.0), "sd": np.full(6, 20.0),
           "seed": 1, "sims": S}
    return ctx, st, po, cap


def _bracket(r1=None, r2=None, final=None, third=None):
    def m(i, r, t1, t2, res=None, p=None):
        d = {"m": i, "r": r, "t1": t1, "t2": t2, "w": None, "l": None}
        if res:
            d["w"], d["l"] = res
        if p:
            d["p"] = p
        return d
    return [m(1, 1, 1, 4, r1), m(2, 1, 2, 3, r2), m(3, 2, None, None, final, p=1), m(4, 2, None, None, third, p=3)]


def test_regular_season_over_locks_non_playoff_picks_by_actual_max_pf():
    ctx, st, po, cap = _tiny()
    b = D.build_block(ctx, st, po, cap, [])
    assert b["status"] == "playoffs"
    first = b["simulated"]["order"][:2]
    assert [r["roster_id"] for r in first] == [6, 5]                       # lowest max PF first, no uncertainty
    assert all(r["slot_odds"][i] == 1.0 for i, r in enumerate(first))
    assert b["today"]["order"][0]["roster_id"] == 6


def test_played_playoff_games_lock_eliminated_teams():
    ctx, st, po, cap = _tiny()
    # seed 1 (rid 1) lost to seed 4 (rid 4) in round 1; seed 2 beat seed 3
    br = _bracket(r1=(4, 1), r2=(2, 3))
    b = D.build_block(ctx, st, po, cap, br)
    by = {r["roster_id"]: r for r in b["simulated"]["order"]}
    assert b["status"] == "playoffs"
    # rid 1 (max PF 1500) and rid 3 (1400) are out in round 1: picks 3 and 4 (after the two non-playoff teams)
    assert by[3]["slot_odds"][2] == 1.0 and by[1]["slot_odds"][3] == 1.0
    assert by[3]["reason"] == "eliminated" and by[3]["round"] == 1 and by[3]["why_pct"] == 1.0
    assert [r["roster_id"] for r in b["today"]["order"][:4]] == [6, 5, 3, 1]


def test_finished_season_gives_final_order_with_no_simulation():
    ctx, st, po, cap = _tiny()
    br = _bracket(r1=(4, 1), r2=(2, 3), final=(2, 4), third=(1, 3))
    b = D.build_block(ctx, st, po, cap, br)
    assert b["status"] == "final" and b["simulated"]["locked"] and b["simulated"]["sims"] == 0
    # missed: 6, 5; round 1 exits 3 (1400), 1 (1500); runner-up 4; champion 2 (the 3rd-place game is ignored)
    expected = [6, 5, 3, 1, 4, 2]
    assert [r["roster_id"] for r in b["today"]["order"]] == expected
    assert [r["roster_id"] for r in b["simulated"]["order"]] == expected
    assert all(max(r["slot_odds"]) == 1.0 for r in b["simulated"]["order"])
    assert [r["reason"] for r in b["today"]["order"]][-2:] == ["runner_up", "champion"]


def test_before_regular_season_ends_bracket_placeholders_are_ignored():
    ctx, st, po, cap = _tiny(reg_over=False)
    cap["seeds"] = np.tile(np.arange(1, 7), (200, 1))
    b = D.build_block(ctx, st, po, cap, _bracket(r1=(4, 1)))      # stale/odd data must not be forced
    assert b["status"] == "projected"


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
        assert d["season"] == "2027" and d["status"] == "projected" and d["bracket"] == "fixed"
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
