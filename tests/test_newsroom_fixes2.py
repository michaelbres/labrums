"""Newsroom fix round 2: game win probability in preview favorite/underdog lines, possessive trade counts,
shotgun 'times' wording, rule labels, readability."""
from __future__ import annotations

import re

import pytest

from app.newsroom import Newsroom, families
from app.newsroom.util import rule_ref, times

from .test_newsroom import LIVE_2025, LIVE_2026, _demo, _live

BODY = lambda a: " ".join(a["body"]) + " " + a["headline"]   # noqa: E731


@pytest.fixture(scope="module")
def demo14():
    nr = Newsroom(*_demo(14), debug=True)
    return nr, nr.generate()


@pytest.fixture(scope="module")
def live26():
    nr = Newsroom(*_live(LIVE_2026), debug=True)
    return nr, nr.generate()


@pytest.fixture(scope="module")
def live25():
    nr = Newsroom(*_live(LIVE_2025), debug=True)
    return nr, nr.generate()


def _all(*sets):
    for _, arts in sets:
        yield from arts


# ---- 1. game win probability, not playoff odds
def test_simulate_exposes_next_game_win_pct(demo14):
    nr, _ = demo14
    nxt = [t["next_game"] for t in nr.po["teams"].values() if t["next_game"]]
    assert nxt and all(0.0 <= g["win_pct"] <= 1.0 for g in nxt)
    games = nr.st["schedule"][nr.po["next_week"]]
    for g in games:   # the two sides of one game sum to 1
        a, b = nr.po["teams"][g["a"]]["next_game"], nr.po["teams"][g["b"]]["next_game"]
        assert a["win_pct"] + b["win_pct"] == pytest.approx(1.0, abs=2e-4)


def test_preview_facts_carry_win_pct_and_lines_say_to_win(live26, demo14, live25):
    previews = [a for a in _all(live26, demo14, live25) if a["type"] == "preview"]
    assert previews
    for a in previews:
        for g in a["facts"]["games"]:
            assert g["win_pct_a"] and g["win_pct_b"] and g["win_pct"] == [g["win_pct_a"], g["win_pct_b"]]
        text = BODY(a)
        assert not re.search(r"underdog at \d+%(?! to win)", text), text
        assert not re.search(r"underdog at 9\d%", text), text


def test_live_2026_favorite_matches_win_probability(live26):
    nr, arts = live26
    for a in arts:
        if a["type"] != "preview":
            continue
        for g in a["facts"]["games"]:
            if g["favorite"]:
                i = 0 if g["favorite"] == g["teams"][0] else 1
                assert int(g["win_pct"][i].rstrip("%")) > int(g["win_pct"][1 - i].rstrip("%"))
                assert g["favorite_basis"] == "win probability"


@pytest.mark.parametrize("fid", families.FAMILY_IDS)
def test_favorite_templates_cite_game_odds(fid):
    fam = families.get(fid)
    for t in fam.T["p.favorite"]:
        assert "{fav_odds}" not in t and "{dog_odds}" not in t
        assert "to win" in t or "chance to win" in t or "{dog_win}" in t


# ---- 2. trade counts are per-owner
def test_trade_counts_are_possessive(live26, demo14, live25):
    bad = re.compile(r"(?<!['’]s )\bthe (?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+(?:st|nd|rd|th)) "
                     r"(?:trade|deal|exchange|acquisition|merger) of (?:the|this) (?:season|year)\b")
    for a in _all(live26, demo14, live25):
        if a["type"] == "trade":
            assert not bad.search(BODY(a)), a["id"]
    for fid in families.FAMILY_IDS:
        for t in families.get(fid).T["t.count"]:
            assert not re.search(r"the \{nth\} \w+ of (?:the|this) (?:season|year)", t), (fid, t)


# ---- 3. shotgun times wording
def test_times_helper_and_no_ritual_n_shotguns_times(demo14, live25, live26):
    assert times(1) == "once" and times(3) == "3 times"
    for a in _all(demo14, live25, live26):
        t = BODY(a)
        assert not re.search(r"\d+ shotguns? times", t), a["id"]
        assert "ritual 1 " not in t, a["id"]


# ---- 4. rule labels
def test_rule_ref_lowercases_unless_owner_name():
    assert rule_ref("Scored less than Nick") == "the “scored less than Nick” rule"
    assert rule_ref("Nick's curse", {"Nick"}) == "the “Nick's curse” rule"
    assert rule_ref("Nick vs the world", {"Nick"}) == "the “Nick vs the world” rule"
    assert rule_ref("Scored less than Nick", {"Nick"}) == "the “scored less than Nick” rule"


def test_live_2026_rule_label_rendering(live26):
    seen = [BODY(a) for a in live26[1] if "rule" in BODY(a)]
    assert any("“scored less than Nick” rule" in t for t in seen)
    assert not any("the Scored less than" in t for t in seen)


# ---- 5. pronoun
def test_all_play_luck_pronoun():
    for fid in families.FAMILY_IDS:
        for tpls in families.get(fid).T.values():
            for t in tpls:
                assert "wins it has not earned" not in t and "wins it hasn't earned" not in t, (fid, t)


# ---- 6. readability
def test_no_points_apart_in_points_or_one_rank_band(demo14, live25, live26):
    for a in _all(demo14, live25, live26):
        t = BODY(a)
        assert "apart in points" not in t, a["id"]
        assert not re.search(r"\b(\d+)(?:st|nd|rd|th) to \1(?:st|nd|rd|th)\b", t), a["id"]
        assert "from 1st every week" not in t and not re.search(r"from \d+\w+ every week", t), a["id"]


def test_sample_is_small_only_for_three_weeks_or_fewer(demo14, live25, live26):
    for a in _all(demo14, live25, live26):
        if a["type"] == "trade" and "the sample is small" in BODY(a):
            m = re.search(r"Over the (\d+) weeks? since", BODY(a)) or re.search(r"across (\d+) weeks?", BODY(a))
            assert not m or int(m.group(1)) <= 3, a["id"]


def test_analytics_steady_and_wild_differ(demo14, live25, live26):
    for a in _all(demo14, live25, live26):
        c = a["facts"].get("weekly_rank_consistency") if a["type"] == "analytics" else None
        if c:
            assert c["steadiest"] != c["wildest"], a["id"]


def test_third_party_blowout_cited_once_per_build(demo14, live25, live26):
    for pack in (demo14, live25, live26):
        cited = [a["facts"]["background"]["blowout_over_third_team"] for a in pack[1]
                 if a["type"] == "feud" and a["facts"].get("background")]
        keys = [(c["w"], c["l"], c["gwk"]) for c in cited]
        assert len(keys) == len(set(keys))
