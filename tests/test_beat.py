"""Team beat reporters: one reporter per team (a roster separate from the 50 staff), one weekly team report per team per
completed week, harshly critical of the owner, from real facts, deterministic, lint-clean, desk-replaceable."""
from __future__ import annotations

import copy
import json
import logging
import re
from datetime import date
from pathlib import Path

import pytest

from app import config, loader
from app.demo import DemoClient
from app.newsroom import Newsroom, beat_reporters, calendar, desk, lint, tools
from app.newsroom.beat_reporters import BEAT_VOICES
from app.newsroom.util import fmt
from app.newsroom.voices import BEAT_CODES, BY_ID, VOICES

from .conftest import LEAGUE_ID
from .test_api import api  # noqa: F401  (fixture)
from .test_newsroom import LIVE_2026, _live, _pipeline

REAL_OWNERS = ["michaelbreslow", "JimmyWoods10", "colonbuns", "cianmahoney", "PatrickHanrahan", "trottner", "styerech",
               "bowieshreiber", "asinagra25", "ncarney7502"]


def _teams(names):
    return {i + 1: {"display_name": n, "owner_id": f"u{i + 1}", "name": n, "team_name": f"Team {n}", "profile": {}}
            for i, n in enumerate(names)}


def _demo_with(week=7, **cfg_edits):
    cfg = copy.deepcopy(config.load_config())
    cfg.update(cfg_edits)
    return _pipeline(loader.load_season(DemoClient(current_week=week), cfg, LEAGUE_ID))


@pytest.fixture(scope="module")
def demo7():
    return _demo_with(7)


@pytest.fixture(scope="module")
def demo7_arts(demo7):
    nr = Newsroom(*demo7, debug=True)
    return nr, nr.generate(use_desk=False)


def _beats(arts):
    return [a for a in arts if a["type"] == "beat"]


# ---------------------------------------------------------------- roster
def test_beat_roster_is_separate_from_the_staff():
    assert len(VOICES) == 50
    assert len(BEAT_VOICES) == 10
    assert len({v.id for v in BEAT_VOICES}) == 10 and len({v.name for v in BEAT_VOICES}) == 10
    assert not {v.id for v in BEAT_VOICES} & set(BY_ID)
    assert not {v.name for v in BEAT_VOICES} & {v.name for v in VOICES}
    assert "beat" not in BEAT_CODES.values() and all("beat" not in v.beats for v in VOICES)
    for v in BEAT_VOICES:
        assert v.name and v.outlet and v.bio and v.column and "\n" not in v.bio
        assert len(v.openers) >= 2 and len(v.closers) >= 2 and len(v.tics) >= 2 and len(v.favs) == 2
    # every reporter has their own signature lines
    sigs = [x for v in BEAT_VOICES for x in (*v.openers, *v.closers, *v.tics)]
    assert len(sigs) == len(set(sigs))
    real = {"skip bayless", "adam schefter", "woj", "diana russini", "stephen a. smith", "chris berman", "al michaels",
            "ian rapoport", "mina kimes", "jay glazer", "tom pelissero", "dan graziano"}
    assert not any(r in " ".join(v.name.lower() for v in BEAT_VOICES) for r in real)


def test_beat_reporters_never_take_staff_assignments(demo7_arts):
    nr, arts = demo7_arts
    beat_ids = {v.id for v in BEAT_VOICES}
    assert not any(a["reporter"]["id"] in beat_ids for a in arts if a["type"] != "beat")
    assert all(a["reporter"]["id"] in BY_ID for a in arts if a["type"] != "beat")
    assert all(a["reporter"]["id"] in beat_ids for a in _beats(arts))
    assert not {v.id for v in nr.voices} & beat_ids


def test_staff_articles_are_untouched_by_the_beat_pass(demo7, monkeypatch):
    with_beat = Newsroom(*demo7, debug=True).generate(use_desk=False)
    monkeypatch.setattr(Newsroom, "beat_reports", lambda self: [])
    without = Newsroom(*demo7, debug=True).generate(use_desk=False)
    assert [a for a in with_beat if a["type"] != "beat"] == without


# ---------------------------------------------------------------- binding to owners
def test_laurel_hanrahan_covers_patrick_with_the_real_config():
    cfg = config.load_config()
    assert cfg["reporters"]["beat"]["PatrickHanrahan"]["name"] == "Laurel Hanrahan"
    teams = _teams(REAL_OWNERS)
    out = beat_reporters.assign(cfg, teams)
    by_owner = {teams[rid]["display_name"]: v for rid, v in out.items()}
    assert by_owner["PatrickHanrahan"].name == "Laurel Hanrahan"
    assert len({v.id for v in out.values()}) == 10               # ten teams, ten different reporters
    assert all(v.name != "Laurel Hanrahan" for o, v in by_owner.items() if o != "PatrickHanrahan")
    # bound to the OWNER, not the roster id: shuffle the roster ids and the pairing follows the owners
    rev = _teams(list(reversed(REAL_OWNERS)))
    out2 = beat_reporters.assign(cfg, rev)
    assert {rev[r]["display_name"]: v.id for r, v in out2.items()} == {o: v.id for o, v in by_owner.items()}
    # the owner key may also be the Sleeper user_id
    cfg2 = copy.deepcopy(cfg)
    cfg2["reporters"] = {"overrides": {}, "beat": {"u5": {"name": "Via UserId"}}}
    assert beat_reporters.assign(cfg2, teams)[5].name == "Via UserId"


def test_unknown_owners_still_get_a_reporter_each_deterministically(demo7_arts):
    nr, arts = demo7_arts
    assert set(nr.beat_by_rid) == set(nr.teams)                  # 12 demo owners, none of them in the built-in table
    first = {r: v.id for r, v in nr.beat_by_rid.items()}
    assert first == {r: v.id for r, v in beat_reporters.assign(nr.cfg, nr.teams).items()}
    ten = _teams(["Ann", "Bo", "Cy", "Di", "Ed", "Flo", "Gus", "Hal", "Ivy", "Jo"])
    got = beat_reporters.assign({}, ten)
    assert len({v.id for v in got.values()}) == 10
    assert got == beat_reporters.assign({}, ten)


def test_config_rename_and_malformed_entries(caplog):
    teams = _teams(REAL_OWNERS)
    cfg = {"reporters": {"beat": {
        "colonbuns": {"name": "  Rina   Voss ", "outlet": "The Rename Times", "bio": "Newly hired.", "mood": "x"},
        "ncarney7502": {"outlet": "Outlet Only"},
        "trottner": "just a string",
        "cianmahoney": {},
        "styerech": {"name": "   "},
        "Nobody": {"name": "Ghost"},
    }}}
    with caplog.at_level(logging.WARNING):
        out = beat_reporters.assign(cfg, teams)
    by_owner = {teams[r]["display_name"]: v for r, v in out.items()}
    assert (by_owner["colonbuns"].name, by_owner["colonbuns"].outlet, by_owner["colonbuns"].bio) == ("Rina Voss", "The Rename Times", "Newly hired.")
    assert by_owner["ncarney7502"].outlet == "Outlet Only" and by_owner["ncarney7502"].name
    base = {teams[r]["display_name"]: v for r, v in beat_reporters.assign({}, teams).items()}
    for dropped in ("trottner", "cianmahoney", "styerech"):    # malformed: the built-in placeholder stays
        assert by_owner[dropped].name == base[dropped].name
    assert len({v.id for v in out.values()}) == 10
    msgs = " ".join(r.getMessage() for r in caplog.records)
    assert "reporters.beat.trottner" in msgs and "reporters.beat.cianmahoney" in msgs and "reporters.beat.styerech" in msgs
    # a renamed reporter keeps the same stable seed (same id), so the text does not reshuffle; the column carries the new name
    assert by_owner["colonbuns"].id == base["colonbuns"].id and "Voss" in by_owner["colonbuns"].column


def test_load_config_normalizes_reporters_beat(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("reporters:\n  beat:\n    Zed: {name: ' A  B '}\n    Bad: 3\n")
    assert config.load_config(p)["reporters"]["beat"] == {"Zed": {"name": "A B"}}
    p.write_text("reporters: []\n")
    assert config.load_config(p)["reporters"] == {"overrides": {}}


# ---------------------------------------------------------------- the reports
def test_one_report_per_team_per_completed_week_with_stable_keys(demo7_arts):
    nr, arts = demo7_arts
    beats = _beats(arts)
    keys = [a["key"] for a in beats]
    assert len(keys) == len(set(keys))
    last = nr.ctx["last_completed"]
    want = {(w, r) for w in range(1, last + 1) for g in nr.games_by_week.get(w, []) for r in (g["a"], g["b"])}
    assert {(a["week"], a["teams"][0]) for a in beats} == want and len(beats) == len(want)
    for a in beats:
        rid = a["teams"][0]
        assert a["teams"] == [rid] and a["key"] == f"{nr.season}:beat:{a['week']}:{rid}"
        rep = nr.beat_by_rid[rid]
        assert a["byline"] == f"{rep.name}, {rep.outlet}" and a["reporter"]["id"] == rep.id and a["reporter"]["family"] == "beat"
        assert nr.name(rid) in " ".join(a["body"]) and a["source"] == "template" and a["week"] <= last
    for r in nr.teams:   # every team has a report for every week it played, all by its own reporter
        mine = [a for a in beats if a["teams"] == [r]]
        assert len({a["reporter"]["id"] for a in mine}) == 1 and len(mine) == last


def test_reports_are_critical_grounded_and_in_range(demo7_arts):
    nr, arts = demo7_arts
    games = {(g["week"], r): g for g in nr.st["games"] for r in (g["a"], g["b"])}
    harsh = re.compile(r"owner|lineup|blame|decision|credit|front office|management|bench", re.I)
    for a in _beats(arts):
        rid, wk = a["teams"][0], a["week"]
        g = games[(wk, rid)]
        mine, theirs = (g["a_pts"], g["b_pts"]) if g["a"] == rid else (g["b_pts"], g["a_pts"])
        res = a["facts"]["result"]
        assert res["score"] == fmt(mine) and res["opponent_score"] == fmt(theirs)
        assert res["result"] == ("T" if g["winner"] is None else "W" if g["winner"] == rid else "L")
        text = " ".join(a["body"])
        assert fmt(mine) in text and nr.name(g["b"] if g["a"] == rid else g["a"]) in text
        assert harsh.search(text), a["key"]
        n = len(text.split())
        assert 90 <= n <= 260, (a["key"], n)
        margin = g["margin"]   # margin words only for the margins that earn them
        if margin < 30:
            assert not lint.BLOW_RE.search(text + " " + a["headline"]), a["key"]
        if margin >= 7:
            assert not lint.CLOSE_RE.search(text + " " + a["headline"]), a["key"]


def test_no_owner_pronouns_in_template_text(demo7_arts):
    """Template lines never guess the owner's gender: 'he/she/him/her' only ever come from the owner's own profile text."""
    nr, arts = demo7_arts
    for a in _beats(arts):
        text = " ".join(a["body"])
        assert not re.search(r"\b(he|she|him|her)\b", text, re.I), a["key"]


def test_every_beat_report_passes_the_lint(demo7_arts):
    nr, arts = demo7_arts
    for a in _beats(arts):
        assert lint.check(a, nr) == [], a["key"]
        assert not re.search(r"[{}]|\bNone\b|\bnan\b|  ", " ".join([a["headline"], a["dek"], *a["body"]]))
        assert json.dumps(a["facts"]) and len(a["facts"]["paras"]) == len(a["body"]) and a["facts"]["beats"]


def test_variety_within_a_week_and_across_a_season(demo7_arts):
    nr, arts = demo7_arts
    beats = _beats(arts)
    assert len({a["facts"]["structure"] for a in beats}) >= 4
    for wk in {a["week"] for a in beats}:
        wkb = [a for a in beats if a["week"] == wk]
        assert len({a["headline"] for a in wkb}) == len(wkb)
        firsts = [nr.sentence_keys(a["body"][0])[:1] for a in wkb]
        assert len({tuple(f) for f in firsts}) >= len(wkb) - 3, wk
    # the same reporter does not repeat a fact sentence back to back
    for rid in nr.teams:
        if sum(1 for v in nr.beat_by_rid.values() if v.id == nr.beat_by_rid[rid].id) > 1:
            continue   # 12 demo teams, 10 reporters: two reporters cover two teams and share one rotation between them
        mine = sorted((a for a in beats if a["teams"] == [rid]), key=lambda a: a["week"])
        for x, y in zip(mine, mine[1:]):
            sx = set(nr.sentence_keys(" ".join(x["body"]), min_words=7))
            sy = set(nr.sentence_keys(" ".join(y["body"]), min_words=7))
            assert not (sx & sy), (x["key"], y["key"], sx & sy)


def test_deterministic(demo7):
    a = _beats(Newsroom(*demo7, debug=True).generate(use_desk=False))
    b = _beats(Newsroom(*demo7, debug=True).generate(use_desk=False))
    assert [(x["id"], x["key"], x["headline"], x["body"]) for x in a] == [(x["id"], x["key"], x["headline"], x["body"]) for x in b]


# ---------------------------------------------------------------- owner profile jabs
PROFILE_OWNERS = {
    "Mike": {"name": "Mike", "nickname": "Big Mike", "hometown": "Scranton",
             "traits": ["overpays for rookies", "never sets his lineup before Sunday", "has been treated for diabetes and jokes about blood sugar"]},
    "Dan": {"name": "Dan", "nickname": "Dan the Plan", "catchphrase": "It's a marathon, not a sprint."},
}


def test_owner_profile_jabs_appear_and_an_empty_profile_reads_clean():
    cfg = copy.deepcopy(config.load_config())
    cfg["owners"] = {**cfg["owners"], **PROFILE_OWNERS}
    ctx, st, po, items = _pipeline(loader.load_season(DemoClient(current_week=14), cfg, LEAGUE_ID))
    nr = Newsroom(ctx, st, po, items, debug=True)
    arts = nr.generate(use_desk=False)
    mike = next(r for r, t in nr.teams.items() if t["display_name"] == "Mike")
    dan = next(r for r, t in nr.teams.items() if t["display_name"] == "Dan")
    blank = next(r for r, t in nr.teams.items() if t["display_name"] == "Kyle")
    text_of = lambda rid: " ".join(" ".join([a["headline"], *a["body"]]) for a in _beats(arts) if a["teams"] == [rid])  # noqa: E731
    mt = text_of(mike)
    assert "overpays for rookies" in mt or "never sets his lineup before Sunday" in mt
    assert "Mike, “Big Mike” to the group chat," in mt and "Scranton" in mt
    assert "diabetes" not in mt and "blood sugar" not in mt     # health jokes are never repeated, even from the profile
    assert "Dan, “Dan the Plan” to the group chat," in text_of(dan)
    kt = text_of(blank)   # no profile: harsh and complete, nothing blank or unfilled
    assert kt and "None" not in kt and "{" not in kt and "  " not in kt and "Kyle" in kt
    for a in _beats(arts):   # nickname once per article, only as the aside; at most one catchphrase per owner-week; lint-clean
        assert lint.check(a, nr) == [], a["key"]
        assert a["body"][0] == a["body"][0].strip()
    catches = [a for a in _beats(arts) if PROFILE_OWNERS["Dan"]["catchphrase"] in " ".join(a["body"])]
    assert len({(a["teams"][0], a["week"]) for a in catches}) == len(catches)
    assert len(catches) <= 0.2 * len(_beats(arts))


# ---------------------------------------------------------------- desk, calendar, API
def test_desk_replaces_a_beat_report_by_key(demo7, tmp_path, monkeypatch):
    d = tmp_path / "articles" / "2026"
    d.mkdir(parents=True)
    monkeypatch.setattr(desk, "CONTENT_DIR", d.parent)
    desk.clear_cache()
    try:
        nr0 = Newsroom(*demo7, debug=True)
        target = _beats(nr0.generate(use_desk=False))[0]
        rid = target["teams"][0]
        body = [f"{nr0.name(rid)} was written up by hand at the desk, and the owner will not enjoy it.", "Second paragraph."]
        (d / f"week-{target['week']}.json").write_text(json.dumps({"week": target["week"], "articles": [
            {"key": target["key"], "headline": "Hand-written beat", "body": body}]}), encoding="utf-8")
        out = Newsroom(*demo7, debug=True).generate()
        a = next(x for x in out if x["key"] == target["key"])
        assert a["source"] == "desk" and a["headline"] == "Hand-written beat" and a["body"] == body
        assert a["reporter"]["id"] == target["reporter"]["id"] and a["byline"] == target["byline"]   # still the team's reporter
        assert sum(1 for x in out if x["source"] == "desk") == 1
    finally:
        desk.clear_cache()


def test_beat_reports_post_on_wednesday():
    start = date(2026, 9, 9)
    assert calendar.publish_on("beat", 1, start) == "2026-09-16"
    assert date.fromisoformat(calendar.publish_on("beat", 3, start)) == date.fromisoformat(calendar.publish_on("recap", 3, start)) + (date(2026, 9, 17) - date(2026, 9, 16))


def test_facts_export_has_beat_reporters_and_the_standing_order(demo7, demo7_arts):
    nr, arts = demo7_arts
    week = nr.ctx["last_completed"]
    data = tools.export_week(nr.season, nr, arts, week)
    assert "HARSHLY CRITICAL" in data["beat_standing_order"] and ":beat:" in data["beat_standing_order"]
    assert all(o["beat_reporter"] for o in data["owners"])
    brs = [a for a in data["articles"] if a["type"] == "beat"]
    assert len(brs) == len(nr.teams)
    for a in brs:
        c = a["reporter"]
        assert c["family_description"] and c["signature_openers"] and c["verbal_tics"] and c["beats"] == ["beat"]
        assert a["facts"]["instruction"] and a["facts"]["result"]["score"]


def test_api_payload_includes_beat_reports_and_masthead_group(api):
    data = api.get("/api/season/2026").json()
    assert len(data["reporters"]) == 50                       # the staff masthead is unchanged
    bs = data["beat_reporters"]
    assert len(bs) == len(data["teams"]) and all(b["team"]["roster_id"] and b["name"] and b["outlet"] for b in bs)
    beats = [a for a in data["articles"] if a["type"] == "beat"]
    assert beats and all(a["reporter"]["family"] == "beat" and len(a["teams"]) == 1 for a in beats)
    assert all("facts" not in a for a in beats)
    assert {a["teams"][0] for a in beats} <= {b["team"]["roster_id"] for b in bs}


def test_frontend_has_beat_filter_team_card_and_masthead_group():
    js = (Path(config.ROOT) / "static" / "app.js").read_text()
    assert "beat_reporters" in js and "Team beat" in js and "'beat'" in js and "news-team" in js
    assert "pickHeadlines(d.articles.filter((a) => a.type !== 'beat')" in js


# ---------------------------------------------------------------- the real league (skipped without a cached Sleeper pull)
def test_real_league_has_ten_reporters_and_laurel_covers_patrick():
    nr = Newsroom(*_live(LIVE_2026), debug=False)
    arts = nr.generate(use_desk=False)
    beats = _beats(arts)
    assert len({v.id for v in nr.beat_by_rid.values()}) == len(nr.teams) == 10
    patrick = next(r for r, t in nr.teams.items() if t["display_name"] == "PatrickHanrahan")
    assert nr.beat_by_rid[patrick].name == "Laurel Hanrahan"
    assert all(a["byline"].startswith("Laurel Hanrahan") for a in beats if a["teams"] == [patrick])
    assert len(beats) == 10 * nr.ctx["last_completed"]
    assert all(lint.check(a, nr) == [] for a in beats)
