"""Reporter overrides and narratives (config.yaml `reporters.overrides`, `narratives`): renamed reporters, a reporter's
take on an owner or a player, and the guarantee that slant is framing only (the facts never change)."""
from __future__ import annotations

import copy
import json
import logging

import pytest

from app import articles, config, loader
from app.demo import DemoClient
from app.newsroom import Newsroom, families, lint, narratives
from app.newsroom.util import pts
from app.newsroom.voices import BASE_VOICES, BY_ID, VOICES
from app.sleeper import SleeperClient

from .conftest import LEAGUE_ID
from .test_newsroom import CACHE, LIVE_2025, _pipeline

KLEIN = "rex-moxley"
RENAMED = {"cody-brandish": "Ricky Sepe", "rex-moxley": "Evan Klein", "felix-okonkwo-brandt": "Evan Glas",
           "candi-moreau": "Doomfist", "everett-lindqvist": "Jon Fascinelli"}


def _cfg(narr=None, overrides=None):
    c = copy.deepcopy(config.load_config())
    if narr is not None:
        c["narratives"] = narr
    if overrides is not None:
        c["reporters"] = {"overrides": overrides}
    return c


def _live25(cfg):
    if not (CACHE / f"league__{LIVE_2025}.json").exists():
        pytest.skip("no cached Sleeper data for 2025")
    return _pipeline(loader.load_season(SleeperClient(CACHE), cfg, LIVE_2025))


def _demo14(cfg):
    return _pipeline(loader.load_season(DemoClient(current_week=14), cfg, LEAGUE_ID))


def neg(a: dict) -> int:
    """The sentiment score: how many negative-tagged variants the article uses."""
    return sum(1 for b in a["facts"]["beats"] if b.endswith("~neg"))


def pos(a: dict) -> int:
    return sum(1 for b in a["facts"]["beats"] if b.endswith("~pos"))


def mean(xs):
    return sum(xs) / len(xs)


@pytest.fixture(scope="module")
def live25():
    return _live25(config.load_config())


@pytest.fixture(scope="module")
def live25_arts(live25):
    nr = Newsroom(*live25, debug=True)
    return nr, nr.generate()


# ---------------------------------------------------------------- config
def test_the_five_renames_and_three_narratives_are_in_config_yaml():
    cfg = config.load_config()
    ov = cfg["reporters"]["overrides"]
    assert {vid: f["name"] for vid, f in ov.items()} == RENAMED
    assert all(vid in BY_ID for vid in ov)
    assert {n["reporter"] for n in cfg["narratives"]} == {"Evan Klein", "Ricky Sepe", "Evan Glas"}
    klein = next(n for n in cfg["narratives"] if n["reporter"] == "Evan Klein")
    assert klein["stance"] == "hater" and klein["about"] == "PatrickHanrahan" and klein["theme"]


def test_config_normalization_drops_what_cannot_work(tmp_path, caplog):
    p = tmp_path / "c.yaml"
    p.write_text("""
reporters: {overrides: {a-voice: {name: " Foo  Bar ", mood: x}, junk: 3}}
narratives:
  - {reporter: X, about: Y, stance: hater}
  - {reporter: X, about: Y, stance: adorer}
  - {reporter: X, stance: hater}
  - {reporter: X, about: Y, player: Z, stance: hater}
  - {reporter: X, about: Y, stance: hype}
  - {reporter: X, player: Z, stance: homer}
  - {reporter: X, player: Z, stance: hype, theme: "A thesis."}
""")
    with caplog.at_level(logging.WARNING, logger="labrums.config"):
        cfg = config.load_config(p)
    assert cfg["reporters"]["overrides"] == {"a-voice": {"name": "Foo Bar"}}
    assert [(n["stance"], n.get("about"), n.get("player"), n["theme"]) for n in cfg["narratives"]] == \
        [("hater", "Y", None, ""), ("hype", None, "Z", "A thesis")]
    assert sum("narratives[" in r.getMessage() for r in caplog.records) == 5


def test_a_legacy_reporters_list_does_not_break_the_loader(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("reporters: []\n")
    assert config.load_config(p)["reporters"] == {"overrides": {}}


# ---------------------------------------------------------------- overrides
def test_overrides_rename_the_staff_and_keep_everything_else():
    by = {v.id: v for v in VOICES}
    base = {v.id: v for v in BASE_VOICES}
    for vid, name in RENAMED.items():
        assert by[vid].name == name and by[vid].outlet == base[vid].outlet and by[vid].family == base[vid].family
        assert by[vid].beats == base[vid].beats and by[vid].openers == base[vid].openers
    assert len(VOICES) == 50 and len({v.name for v in VOICES}) == 50


def test_override_fields_apply_at_build_time_to_bylines_and_cards():
    cfg = _cfg(narr=[], overrides={"hollis-tanager": {"name": "Hollis T. Override", "outlet": "The Override Ledger", "bio": "Renamed by config."}})
    nr = Newsroom(*_demo14(cfg), debug=True)
    arts = nr.generate()
    mine = [a for a in arts if a["reporter"]["id"] == "hollis-tanager"]
    assert mine
    for a in mine:
        assert a["byline"] == "Hollis T. Override, The Override Ledger"
        assert a["reporter"]["bio"] == "Renamed by config."
    card = next(c for c in nr.masthead() if c["id"] == "hollis-tanager")
    assert card["name"] == "Hollis T. Override" and card["outlet"] == "The Override Ledger"
    assert all(c["name"] != "Evan Klein" for c in nr.masthead())   # the staff as written, nothing from config.yaml


def test_unknown_voice_id_in_overrides_is_ignored_with_a_warning(caplog):
    narratives._WARNED.clear()
    with caplog.at_level(logging.WARNING, logger="labrums.newsroom"):
        voices = narratives.apply_overrides({"reporters": {"overrides": {"no-such-voice": {"name": "Ghost"}}}})
    assert [v.name for v in voices] == [v.name for v in BASE_VOICES]
    assert any("no-such-voice" in r.getMessage() for r in caplog.records)


def test_masthead_payload_carries_known_for():
    cards = articles.reporters()
    assert len(cards) == 50 and all(isinstance(c["known_for"], str) for c in cards)
    by = {c["id"]: c for c in cards}
    assert by["rex-moxley"]["known_for"] == "Patrick's roster is a collection of panic moves"
    assert by["felix-okonkwo-brandt"]["known_for"] == "Tom's schedule has been soft"
    assert by["hollis-tanager"]["known_for"] == ""
    # a narrative without a theme falls back to the stance's own line
    cfg = _cfg(narr=[{"reporter": "hollis-tanager", "about": "PatrickHanrahan", "stance": "hater", "theme": ""}])
    voices, _ = narratives.staff(cfg)
    assert next(v for v in voices if v.id == "hollis-tanager").known_for == "a well-documented grudge against Patrick"


# ---------------------------------------------------------------- unknown names
def test_narratives_with_unknown_reporter_or_owner_are_ignored_with_a_warning(caplog):
    narratives._WARNED.clear()
    cfg = _cfg(narr=[
        {"reporter": "Nobody Atall", "about": "PatrickHanrahan", "stance": "hater", "theme": ""},
        {"reporter": "Evan Klein", "about": "NoSuchOwner", "stance": "hater", "theme": ""},
        {"reporter": "Evan Klein", "about": "PatrickHanrahan", "stance": "hater", "theme": "kept"},
    ])
    with caplog.at_level(logging.WARNING, logger="labrums.newsroom"):
        nr = Newsroom(*_live25(cfg), debug=True)
    msgs = " ".join(r.getMessage() for r in caplog.records)
    assert "Nobody Atall" in msgs and "NoSuchOwner" in msgs
    assert [(n.voice_id, n.label) for n in nr.narrs] == [(KLEIN, "Patrick")]
    arts = nr.generate()
    assert arts and all(not a["facts"].get("slant") or a["reporter"]["id"] == KLEIN for a in arts)


def test_a_config_with_no_narratives_slants_nothing():
    arts = Newsroom(*_demo14(_cfg(narr=[])), debug=True).generate()
    assert not any("slant" in a["facts"] or any("~" in b for b in a["facts"]["beats"]) for a in arts)


# ---------------------------------------------------------------- the hater
def _klein(arts):
    return [a for a in arts if a["reporter"]["id"] == KLEIN]


def test_klein_writes_patrick_regularly_and_those_articles_score_more_negative(live25_arts):
    nr, arts = live25_arts
    patrick = next(r for r, t in nr.teams.items() if t["display_name"] == "PatrickHanrahan")
    mine = _klein(arts)
    target = [a for a in mine if a["facts"].get("slant")]
    others = [a for a in mine if not a["facts"].get("slant")]
    assert len(target) >= 4, "Patrick is a party in many weeks; Evan Klein should be on him regularly"
    assert len(target) < len(arts) // 4, "regularly, not always"
    for a in target:
        assert a["facts"]["slant"]["narratives"][0]["target"] == "Patrick"
        assert neg(a) >= 2 and pos(a) == 0, a["id"]
        assert a["reporter"]["known_for"]
    # the target is really a party of each article (a recap is about every game of the week, so check the pair pieces)
    for a in target:
        if a["type"] in ("trade", "feud", "column"):
            assert patrick in a["teams"], a["id"]
    assert others, "a reporter with a narrative still writes other pieces"
    assert all(neg(a) == 0 for a in others)
    assert mean([neg(a) for a in target]) > mean([neg(a) for a in others])


def _patrick(nr) -> int:
    return next(r for r, t in nr.teams.items() if t["display_name"] == "PatrickHanrahan")


def _weeks_with(nr, rid):
    return sorted(w for w, gs in nr.games_by_week.items() if w <= nr.ctx["last_completed"] and any(rid in (g["a"], g["b"]) for g in gs))


def test_klein_recaps_are_more_negative_than_the_same_recaps_without_the_narrative_and_say_the_same_facts(live25):
    voice = next(v for v in VOICES if v.id == KLEIN)
    with_n = Newsroom(*live25, debug=True)
    without = Newsroom(*_live25(_cfg(narr=[])), debug=True)
    weeks = _weeks_with(with_n, _patrick(with_n))
    assert len(weeks) >= 14
    for w in weeks:
        a, b = with_n.roundup(w, voice), without.roundup(w, voice)
        assert neg(a) >= 2 > neg(b) == 0, w
        assert a["facts"]["games"] == b["facts"]["games"], w            # the same results, scores and margins
        assert a["facts"]["story"] == b["facts"]["story"] and a["dek"] == b["dek"]
        assert a["facts"]["standings_shift"] == b["facts"]["standings_shift"]
        assert lint.check(a, with_n) == []


def test_a_hater_never_invents_a_number(live25_arts):
    nr, arts = live25_arts
    lines = 0
    for a in _klein(arts):
        for ln in (a["facts"].get("slant") or {}).get("lines", []):
            lines += 1
            assert set(lint._NUM.findall(ln["text"])) <= set(ln["nums"]), ln
    assert lines >= 15
    a = next(x for x in _klein(arts) if x["facts"].get("slant"))
    bad = dict(a)
    bad["facts"] = copy.deepcopy(a["facts"])
    bad["facts"]["slant"]["lines"].append({"slot": "g.weak~neg", "text": "Patrick left 99 points on the bench.", "nums": []})
    assert any("not facts" in p for p in lint.check(bad, nr))


def test_wins_are_framed_with_a_real_weakness_never_an_invented_one(live25):
    """Every 'won, but ...' line is built from a fact that holds: bench points really left, a dud who really scored
    that little, a luck index that really is that high, a margin that really is thin."""
    voice = next(v for v in VOICES if v.id == KLEIN)
    nr = Newsroom(*live25, debug=True)
    patrick, checked = _patrick(nr), 0
    for w in _weeks_with(nr, patrick):
        art = nr.roundup(w, voice)
        game = next(g for g in nr.games_by_week[w] if patrick in (g["a"], g["b"]))
        if game["winner"] != patrick:
            continue
        weak = [ln for ln in art["facts"]["slant"]["lines"] if ln["slot"] == "g.weak~neg"]
        assert weak, w
        left, _ = nr.bench_left(w, patrick)
        text = " ".join(ln["text"] for ln in weak)
        if "bench" in text:
            assert left >= 10 and pts(left) in text, w
        if "all-play" in text:
            assert nr.snap(w)["teams"][patrick]["luck"] >= 1, w
        if "by just" in text or "margin" in text:
            assert game["margin"] < 7, w
        checked += 1
    assert checked >= 4


def test_hater_on_demo(monkeypatch):
    cfg0 = _cfg(narr=[])
    ctx, st, po, items = _demo14(cfg0)
    owner = ctx["teams"][1]["display_name"]
    cfg = _cfg(narr=[{"reporter": KLEIN, "about": owner, "stance": "hater", "theme": "the books were cooked"}])
    nr = Newsroom(*_demo14(cfg), debug=True)
    arts = nr.generate()
    mine = _klein(arts)
    target = [a for a in mine if a["facts"].get("slant")]
    assert target and all(neg(a) >= 2 for a in target)
    assert all(neg(a) == 0 for a in mine if not a["facts"].get("slant"))
    assert any("the books were cooked" in " ".join(a["body"]) for a in target)
    assert json.dumps([a["facts"] for a in arts])


# ---------------------------------------------------------------- the other stances
def test_homer_is_warm_and_never_sour():
    ctx = _demo14(_cfg(narr=[]))[0]
    owner = ctx["teams"][2]["display_name"]
    cfg = _cfg(narr=[{"reporter": "hollis-tanager", "about": owner, "stance": "homer", "theme": "the best roster nobody respects"}])
    nr = Newsroom(*_demo14(cfg), debug=True)
    mine = [a for a in nr.generate() if a["facts"].get("slant")]
    assert mine
    for a in mine:
        assert neg(a) == 0 and pos(a) >= 1, a["id"]
        assert a["facts"]["slant"]["narratives"][0]["stance"] == "homer"
    assert any("the best roster nobody respects" in " ".join(a["body"]) for a in mine)
    lost = []
    for w in range(1, nr.ctx["last_completed"] + 1):   # a loss gets "despite" framing, from facts
        art = nr.roundup(w, next(v for v in nr.voices if v.id == "hollis-tanager"))
        lost += [ln for ln in (art["facts"].get("slant") or {}).get("lines", []) if ln["slot"] == "g.weak~pos"]
    assert lost


def test_skeptic_says_yes_but_and_cites_the_theme_once(live25):
    cfg = _cfg(narr=[{"reporter": "Evan Glas", "about": "trottner", "stance": "skeptic", "theme": "Tom's schedule has been soft"}])
    nr = Newsroom(*_live25(cfg), debug=True)
    voice = next(v for v in nr.voices if v.name == "Evan Glas")
    n_weak = 0
    tom = next(r for r, t in nr.teams.items() if t["display_name"] == "trottner")
    weeks = [w for w in _weeks_with(nr, tom) if all(g["winner"] is not None for g in nr.games_by_week[w] if tom in (g["a"], g["b"]))]
    assert len(weeks) >= 12
    for w in weeks:
        art = nr.roundup(w, voice)
        sl = art["facts"].get("slant")
        assert sl and pos(art) == 0
        assert " ".join(art["body"]).count("Tom's schedule has been soft") == 1
        n_weak += sum(1 for b in art["facts"]["beats"] if b == "g.weak~neg")
    assert n_weak >= 3


def test_hype_line_follows_the_player_and_is_grounded_in_the_points(live25):
    cfg = _cfg(narr=[{"reporter": "hollis-tanager", "player": "Breece Hall", "stance": "hype", "theme": ""}])
    nr = Newsroom(*_live25(cfg), debug=True)
    voice = next(v for v in nr.voices if v.id == "hollis-tanager")
    hit = None
    for w in range(1, nr.ctx["last_completed"] + 1):
        art = nr.roundup(w, voice)
        for ln in (art["facts"].get("slant") or {}).get("lines", []):
            if ln["slot"] == "x.hype~pos":
                hit = (w, art, ln)
                break
        if hit:
            break
    assert hit, "Breece Hall is a star in some week"
    w, art, ln = hit
    assert "Breece Hall" in ln["text"] and "Hollis" in ln["text"] and "August" in ln["text"]
    pts_in_line = [x for x in lint._NUM.findall(ln["text"])]
    assert pts_in_line, "the line cites the player's actual points"
    star = next(g for g in art["facts"]["games"] if g.get("star") == "Breece Hall")
    assert star["spts"].split()[0] in pts_in_line
    assert all(a["facts"]["slant"]["narratives"][0]["target"] == "Breece Hall" for a in [art])


# ---------------------------------------------------------------- templates and determinism
def test_every_family_has_slanted_variants_in_every_required_slot():
    for fam in families.all_families():
        assert families.validate(fam) == [], fam.id
        for slot in ("g.star", "g.goat", "g.record", "x.theme", "x.attr", "h.sl.win", "h.sl.loss", "h.sl.any"):
            assert len(fam.S[f"{slot}~neg"]) >= 2 and len(fam.S[f"{slot}~pos"]) >= 2, (fam.id, slot)
        assert len(fam.S["x.attr~neg"]) >= 3 and len(fam.S["x.hype~pos"]) >= 2 and len(fam.S["x.theme~neutral"]) >= 2
        assert len(fam.S["g.weak~neg"]) >= 3 and len(fam.S["g.weak~pos"]) >= 3
        blob = " ".join(t for tpls in fam.S.values() for t in tpls)
        assert not any(c.isdigit() for c in blob), fam.id


def test_hater_attributions_turn_sour():
    for fam in families.all_families():
        neg_attr = " ".join(fam.S["x.attr~neg"]).lower()
        assert any(w in neg_attr for w in ("claim", "insist", "maintain")), fam.id


def test_output_with_narratives_is_deterministic(live25):
    a = Newsroom(*live25, debug=True).generate()
    b = Newsroom(*_live25(config.load_config()), debug=True).generate()
    assert [(x["id"], x["reporter"]["id"], x["headline"], x["body"]) for x in a] == [(x["id"], x["reporter"]["id"], x["headline"], x["body"]) for x in b]


def test_casting_boost_keeps_the_family_rotation(live25_arts):
    nr, arts = live25_arts
    from collections import Counter
    fams = Counter(a["reporter"]["family"] for a in arts if a["type"] == "recap")
    assert len(fams) >= 13 and max(fams.values()) <= 2
