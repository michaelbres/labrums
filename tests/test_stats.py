from __future__ import annotations


def test_demo_shape(ctx):
    assert ctx["season"] == "2026"
    assert len(ctx["teams"]) == 12
    assert ctx["last_completed"] == 6
    assert ctx["current_week"] == 7
    assert ctx["playoff_start"] == 15


def test_standings_sorted_by_wins_then_pf(st):
    teams = st["teams"]
    order = st["standings"]
    assert sorted(order) == sorted(teams)
    keys = [(-teams[r]["wins"], teams[r]["losses"], -teams[r]["pf"]) for r in order]
    assert keys == sorted(keys)
    assert [teams[r]["rank"] for r in order] == list(range(1, 13))


def test_games_played_is_six(st):
    for rid, t in st["teams"].items():
        assert t["wins"] + t["losses"] + t["ties"] == 6, rid


def test_expected_wins_in_range(st):
    for t in st["teams"].values():
        games = t["wins"] + t["losses"] + t["ties"]
        assert 0 <= t["expected_wins"] <= games


def test_lineup_efficiency_in_range(st):
    for t in st["teams"].values():
        eff = t["lineup_efficiency"]
        assert eff is not None
        assert 0 < eff <= 1


def test_records(st):
    rec = st["records"]
    assert rec["high_score"]["points"] >= rec["low_score"]["points"]
    assert rec["high_score"]["roster_id"] in st["teams"]


def test_schedule_only_future_regular_weeks(ctx, st):
    assert st["schedule"], "expected remaining games"
    for week in st["schedule"]:
        assert ctx["last_completed"] < week <= 14
    assert 7 in st["schedule"]
    assert len(st["schedule"][7]) == 6


def test_power_rating_scale_and_order(st):
    teams = st["teams"]
    for t in teams.values():
        assert isinstance(t["power_rating"], int) and 1 <= t["power_rating"] <= 100
        assert t["power_score"] == t["power_rating"] / 100
    order = [teams[r] for r in st["power_rankings"]]
    keys = [(-t["power_rating"], -t["all_play"]["pct"], -t["avg"]) for t in order]
    assert keys == sorted(keys)
