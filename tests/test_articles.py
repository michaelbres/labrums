from __future__ import annotations

import re

from app import articles, shotguns, stats

from .conftest import SEASON


def test_generates_articles(arts):
    assert isinstance(arts, list) and arts


def test_deterministic(ctx, st, po, items):
    a = articles.generate(ctx, st, po, items)
    b = articles.generate(ctx, st, po, items)
    assert [x["headline"] for x in a] == [x["headline"] for x in b]
    assert a == b


def test_one_roundup_per_completed_week(ctx, st, arts):
    recaps = [a for a in arts if a["type"] == "recap"]
    weeks = sorted({g["week"] for g in st["games"]})
    assert sorted(a["week"] for a in recaps) == weeks and len(recaps) == len(weeks)
    for a in recaps:
        week_teams = {t for g in st["games"] if g["week"] == a["week"] for t in (g["a"], g["b"])}
        assert set(a["teams"]) == week_teams
        assert a["tags"] == ["recap", f"week-{a['week']}"]


def test_single_standings_article(arts):
    assert len([a for a in arts if a["type"] == "standings"]) == 1


def test_one_weekly_preview(st, arts):
    previews = [a for a in arts if a["type"] == "preview"]
    assert len(previews) == 1 and previews[0]["week"] == 7
    games = {frozenset((g["a"], g["b"])) for g in st["schedule"][7]}
    assert len(previews[0]["facts"]["games"]) == len(games)
    assert set(previews[0]["teams"]) == {t for g in st["schedule"][7] for t in (g["a"], g["b"])}


def test_rivalry_article(ctx, st, po, make_ctx):
    game = st["schedule"][7][0]
    name_a = ctx["teams"][game["a"]]["display_name"]
    name_b = ctx["teams"][game["b"]]["display_name"]
    ctx2 = make_ctx(rivalries=[{"name": "The Test Feud", "owners": [name_a, name_b],
                                "backstory": "Born in a group chat."}])
    items = shotguns.detect(ctx2, st)
    arts = articles.generate(ctx2, st, po, items)
    riv = [a for a in arts if a["type"] == "rivalry"]
    assert len(riv) == 1
    assert riv[0]["week"] == 7
    assert set(riv[0]["teams"]) == {game["a"], game["b"]}
    assert riv[0]["reporter"]["name"] and riv[0]["reporter"]["outlet"] and riv[0]["reporter"]["bio"]
    assert "Born in a group chat." in " ".join(riv[0]["body"])


def test_owner_profile_shows_up(ctx, po, make_ctx):
    names = [ctx["teams"][r]["display_name"] for r in sorted(ctx["teams"])]
    owners = {n: {"nickname": f"Nick{i}Zed", "catchphrase": f"Catch{i}Phrase", "traits": [f"trait{i}ok"]}
              for i, n in enumerate(names)}
    ctx2 = make_ctx(owners=owners)
    st2 = stats.compute(ctx2)  # profiles flow ctx -> stats -> articles
    arts = articles.generate(ctx2, st2, po, shotguns.detect(ctx2, st2))
    text = " ".join(" ".join([a["headline"], a["dek"], *a["body"]]) for a in arts)
    assert re.search(r"Nick\d+Zed", text), "nickname never used"
    assert re.search(r"Catch\d+Phrase", text), "catchphrase never used"


def test_no_unfilled_placeholders(arts):
    for a in arts:
        for para in a["body"]:
            assert "{" not in para and "}" not in para, (a["id"], para)
        assert "{" not in a["headline"], a["id"]
        assert "{" not in a["dek"], a["id"]
