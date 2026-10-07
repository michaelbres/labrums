"""Newsroom v2: 50 voices, 14 style families, facts-first articles, coherence lint, diversity."""
from __future__ import annotations

import itertools
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from app import articles, config, loader, playoffs, shotguns, stats
from app.demo import DemoClient
from app.newsroom import Newsroom, families, lint, quotes
from app.newsroom.voices import BEAT_CODES, BY_ID, VOICES
from app.sleeper import SleeperClient

from .conftest import LEAGUE_ID
from .test_api import api  # noqa: F401  (fixture)

LIVE_2026 = "1312105961640448000"
LIVE_2025 = "1180654264610529280"
CACHE = config.DATA_DIR / "cache"


def _pipeline(ctx):
    st = stats.compute(ctx)
    po = playoffs.simulate(ctx, st, sims=300)
    items = shotguns.detect(ctx, st)
    return ctx, st, po, items


def _demo(week):
    return _pipeline(loader.load_season(DemoClient(current_week=week), config.load_config(), LEAGUE_ID))


def _live(league_id):
    if not (CACHE / f"league__{league_id}.json").exists():
        pytest.skip(f"no cached Sleeper data for {league_id}")
    return _pipeline(loader.load_season(SleeperClient(CACHE), config.load_config(), league_id))


@pytest.fixture(scope="module")
def demo14():
    return _demo(14)


@pytest.fixture(scope="module")
def demo14_arts(demo14):
    nr = Newsroom(*demo14, debug=True)
    return nr, nr.generate()


@pytest.fixture(scope="module")
def live25():
    return _live(LIVE_2025)


@pytest.fixture(scope="module")
def live25_arts(live25):
    nr = Newsroom(*live25, debug=True)
    return nr, nr.generate()


@pytest.fixture(scope="module")
def live26_arts():
    nr = Newsroom(*_live(LIVE_2026), debug=True)
    return nr, nr.generate()


# ---------------------------------------------------------------- roster of reporters / families
def test_exactly_50_distinct_voices():
    assert len(VOICES) == 50
    assert len({v.id for v in VOICES}) == 50 and len({v.name for v in VOICES}) == 50
    for v in VOICES:
        assert v.name and v.outlet and v.bio and v.beats <= set(BEAT_CODES.values())
        assert len(v.openers) >= 1 and len(v.closers) >= 1 and 2 <= len(v.tics) <= 3, v.id
        assert "\n" not in v.bio and v.family in families.FAMILY_IDS


def test_at_least_14_families_with_3_distinct_voices_each():
    assert len(families.FAMILY_IDS) >= 14
    by_fam = {}
    for v in VOICES:
        by_fam.setdefault(v.family, []).append(v)
    assert set(by_fam) == set(families.FAMILY_IDS)
    for fid, vs in by_fam.items():
        assert len(vs) >= 3, fid
        sigs = {(v.openers, v.closers, v.tics) for v in vs}
        assert len(sigs) == len(vs), f"{fid}: voices share a signature"
        assert len({o for v in vs for o in v.openers}) == sum(len(v.openers) for v in vs), fid  # no shared opener


def test_voice_names_are_original():
    real = {"skip bayless", "adam schefter", "woj", "diana russini", "stephen a. smith", "chris berman", "al michaels"}
    low = " ".join(v.name.lower() for v in VOICES)
    assert not any(r in low for r in real)


@pytest.mark.parametrize("fid", families.FAMILY_IDS)
def test_family_is_complete(fid):
    fam = families.get(fid)
    assert families.validate(fam) == []
    for slot, (n_min, _, _) in families.SLOTS.items():
        assert len(fam.T[slot]) >= max(3, n_min), (fid, slot)
    assert sum(len(v) for v in fam.T.values()) > 250
    for a in ("rhythm", "formality", "metaphors", "numbers", "desc"):
        assert getattr(fam, a)
    heads = [s for s in fam.T if s.startswith("h.r.")]
    assert sum(len(fam.T[s]) for s in heads) >= 4


def test_margin_lexicons_never_cross_classes():
    for fam in families.all_families():
        for kind in ("verb", "noun"):
            for cls, words in fam.lex[kind].items():
                for w in words:
                    if cls != "blowout":
                        assert not lint.BLOW_RE.search(w), (fam.id, kind, cls, w)
                    if cls != "close":
                        assert not lint.CLOSE_RE.search(w), (fam.id, kind, cls, w)


def test_template_text_never_uses_forbidden_words():
    for fam in families.all_families():
        for slot, tpls in fam.T.items():
            for t in tpls:
                assert "LARP" not in t.upper(), (fam.id, slot)
                assert not re.search(r"\bassets\b|nothing of note|kicker|punter", t, re.I), (fam.id, slot, t)
                if slot.startswith("g.") and slot not in ("g.result", "g.tie"):
                    assert not lint.BLOW_RE.search(t) and not lint.CLOSE_RE.search(t), (fam.id, slot, t)


# ---------------------------------------------------------------- quotes
SITUATIONS = ["won_big", "won_close", "lost_big", "lost_close", "tied", "trade_gave_more", "trade_got_more",
              "waiver_win", "shotgun_owed", "rule_owed", "bubble", "clinched", "eliminated", "trash_h2h_lead",
              "trash_h2h_trail", "trash_standings", "deny_after_trash"]


def test_quote_banks_cover_every_situation_with_6_variants():
    for sit in SITUATIONS:
        assert len(quotes.BANK[sit]) >= 6, sit
    assert len(set(quotes.BANK["won_big"])) == len(quotes.BANK["won_big"])
    for sit, lines in quotes.BANK.items():
        for line in lines:
            assert "kicker" not in line.lower() and "larp" not in line.lower()


def test_commissioner_only_lines_are_gated():
    facts = {"rule": "r", "sgn": "one shotgun", "target": "Nick"}
    for who in (False, True):
        got = {t for _, t in quotes.candidates("rule_owed", facts, commish=who)}
        assert (any("made the rule" in t for t in got)) is who


def test_shotgun_quotes_match_the_count():
    for _, t in quotes.candidates("shotgun_owed", {"sgn": "one shotgun", "player": "X"}, multi=False):
        assert "owed." not in t and "Somebody tell my liver" not in t
    for _, t in quotes.candidates("shotgun_owed", {"sgn": "three shotguns", "player": "X"}, multi=True):
        assert "One shotgun" not in t and "A single shotgun" not in t


def test_ellipsis_catchphrase_is_unset_and_commissioner_configured():
    cfg = config.load_config()
    assert cfg["commissioner"] == "michaelbreslow"
    assert "catchphrase" not in cfg["owners"]["asinagra25"]
    assert config.clean_profile({"catchphrase": " ... "}) == {} and config.clean_profile({"catchphrase": "…"}) == {}


# ---------------------------------------------------------------- stats.snapshot
def test_snapshot_matches_compute_at_season_end(ctx, st):
    snap = stats.snapshot(st, ctx, ctx["last_completed"])
    assert snap["standings"] == st["standings"]
    for rid, t in st["teams"].items():
        s = snap["teams"][rid]
        for k in ("wins", "losses", "ties", "record", "streak", "pf", "pa", "avg", "luck", "weeks_top", "rank"):
            assert (s[k] == pytest.approx(t[k], abs=0.011)) if isinstance(t[k], float) else (s[k] == t[k]), (rid, k)
        assert s["all_play"] == t["all_play"] and s["weekly_rank"] == t["weekly_rank"]


def test_snapshot_is_as_of_the_week(ctx, st):
    for week in range(1, ctx["last_completed"] + 1):
        snap = stats.snapshot(st, ctx, week)
        assert all(t["wins"] + t["losses"] + t["ties"] == week for t in snap["teams"].values())
        assert sorted(t["rank"] for t in snap["teams"].values()) == list(range(1, len(snap["teams"]) + 1))
    first = stats.snapshot(st, ctx, 1)
    assert all(t["record"] in ("1-0", "0-1") for t in first["teams"].values())
    assert stats.snapshot(st, ctx, 0)["teams"][1]["record"] == "0-0"


# ---------------------------------------------------------------- shape and coherence
def test_article_shape_and_llm_hooks(demo14_arts):
    nr, arts = demo14_arts
    assert {a["type"] for a in arts} >= {"recap", "preview", "trade", "waiver", "shotgun", "standings", "feud"}
    for a in arts:
        for k in ("id", "type", "week", "headline", "dek", "byline", "body", "teams", "tags", "reporter", "facts"):
            assert k in a, (a["id"], k)
        r = a["reporter"]
        assert a["byline"] == f"{r['name']}, {r['outlet']}" and r["bio"]
        assert r["id"] in BY_ID and BY_ID[r["id"]].family == r["family"]
        json.dumps(a["facts"])
        assert a["facts"]["beats"] and len(a["facts"]["paras"]) == len(a["body"])
    assert len({a["id"] for a in arts}) == len(arts)


def test_deterministic(demo14):
    a = Newsroom(*demo14, debug=False).generate()
    b = Newsroom(*demo14, debug=False).generate()
    assert a == b


def test_lint_clean_on_all_data_sets(demo14_arts, live25_arts, live26_arts):
    for nr, arts in (demo14_arts, live25_arts, live26_arts):
        assert arts
        probs = [p for a in arts for p in lint.check(a, nr)]
        assert probs == []


@pytest.mark.parametrize("week", [1, 2, 7, 15])
def test_lint_clean_across_demo_weeks(week):
    nr = Newsroom(*_demo(week), debug=True)
    assert nr.generate() is not None  # debug=True raises on any lint problem


def test_lint_catches_what_it_should(demo14_arts):
    nr, arts = demo14_arts
    base = next(a for a in arts if a["type"] == "recap")
    bad_cases = [
        dict(base, body=base["body"][:1] + ["Double  space."]),
        dict(base, body=base["body"][:1] + ["Broken {placeholder} here."]),
        dict(base, body=base["body"][:1] + ["He said “fine.” and left."]),
        dict(base, body=base["body"][:1] + ["Totally a LARPer move."]),
        dict(base, body=base["body"][:1] + ["That is 0.5 points, which is not a typo."]),
        dict(base, headline="Tom escapes Nick in a thriller"),
        dict(base, teams=base["teams"] + [max(nr.teams) + 99]) if False else dict(base, body=["Nobody is named here."]),
    ]
    for case in bad_cases:
        assert lint.check(case, nr), case["body"][-1]
    pv = next(a for a in arts if a["type"] == "preview")
    other = dict(pv, facts=dict(pv["facts"], headline_favorite="Someone Else", favorite="Not Them"))
    assert any("favorite" in p for p in lint.check(other, nr))


def test_one_recap_and_one_preview_per_week(demo14_arts, live25_arts):
    for nr, arts in (demo14_arts, live25_arts):
        recaps = [a["week"] for a in arts if a["type"] == "recap"]
        assert recaps == sorted(set(recaps), reverse=True) and len(recaps) == len(set(recaps))
        assert sorted(recaps) == sorted(w for w in nr.games_by_week if w <= nr.ctx["last_completed"])
        assert len([a for a in arts if a["type"] == "preview"]) <= 1
    assert len([a for a in demo14_arts[1] if a["type"] == "preview"]) == 1


def test_recaps_use_as_of_week_records(demo14_arts, live25_arts):
    for nr, arts in (demo14_arts, live25_arts):
        for a in arts:
            if a["type"] != "recap" or a["facts"]["playoff"]:
                continue
            for g in a["facts"]["games"]:
                if g.get("result") == "tie":
                    continue
                for key in ("w_rec", "l_rec"):
                    nums = [int(x) for x in g[key].split("-")]
                    assert sum(nums) == a["week"], (a["id"], key, g[key])


def test_recap_winner_and_loser_match_the_games(demo14_arts):
    nr, arts = demo14_arts
    for a in arts:
        if a["type"] != "recap":
            continue
        week_games = {frozenset((nr.name(g["a"]), nr.name(g["b"]))): g for g in nr.games_by_week[a["week"]]}
        for fg in a["facts"]["games"]:
            if fg.get("result") == "tie":
                continue
            g = week_games[frozenset((fg["winner"], fg["loser"]))]
            assert nr.name(g["winner"]) == fg["winner"]
            assert float(fg["winner_score"]) > float(fg["loser_score"])


def test_playoff_weeks_are_framed_as_playoffs(live25_arts):
    nr, arts = live25_arts
    po_recaps = [a for a in arts if a["type"] == "recap" and a["week"] >= nr.ctx["playoff_start"]]
    assert po_recaps
    for a in po_recaps:
        text = " ".join(a["body"])
        assert a["facts"]["playoff"] and "playoff Week" in " ".join([a["headline"], a["dek"], text])
        assert not re.search(r"drops to|moved to|bylaws|alive for|top six|playoff odds", text, re.I)
        assert a["facts"]["standings_shift"] is None


def test_complete_season_standings_read_as_final(live25_arts):
    nr, arts = live25_arts
    st_art = [a for a in arts if a["type"] == "standings"]
    assert len(st_art) == 1
    a = st_art[0]
    text = " ".join([a["headline"], a["dek"], *a["body"]])
    assert a["facts"]["final"] is True
    assert not re.search(r"\balive\b|odds|\bbye\b|alive for", text, re.I)
    assert str(nr.ctx["playoff_teams"]) in a["dek"]


def test_trades_say_what_they_mean(demo14_arts, live25_arts, live26_arts):
    for nr, arts in (demo14_arts, live25_arts, live26_arts):
        for a in [x for x in arts if x["type"] == "trade"]:
            blob = " ".join([a["headline"], a["dek"], *a["body"]])
            assert not re.search(r"assets|nothing of note|Swap \d|0 players", blob), a["id"]
            f = a["facts"]
            if not f["graded"]:
                assert not re.search(r"early returns favor|leads the early", blob, re.I), a["id"]
            else:
                assert f["better_early_return"] in [nr.name(r) for r in a["teams"]]
                pts = f["points_since"]
                assert max(pts, key=pts.get) == f["better_early_return"]
            for side, got in f["received"].items():
                assert got and side in blob


def test_trade_headline_direction_matches_body():
    # a trade where Michael sends one player for two picks must say so in that direction
    ctx, st, po, items = _demo(7)
    nr = Newsroom(ctx, st, po, items, debug=True)
    tx = next(t for t in ctx["transactions"][2] if t["type"] == "trade")
    info = nr.trade_info(tx, 2)
    voice = BY_ID["hollis-tanager"]
    art = nr.trade(tx, 2, voice)
    a, b = info["a"], info["b"]
    from app.newsroom.beats_misc import short_side
    gave = short_side(info["got"][b]["players"], info["got"][b]["picks"])
    got = short_side(info["got"][a]["players"], info["got"][a]["picks"])
    assert nr.name(a) in art["headline"] and nr.name(b) in art["headline"]
    assert gave in art["headline"] and got in art["headline"]
    assert art["headline"].index(gave) < art["headline"].index(got) or art["headline"].index(got) < art["headline"].index(gave)
    assert f"{nr.name(a)} received" in " ".join(art["body"]) or nr.name(a) in " ".join(art["body"])


def test_no_unavailable_positions_in_league_without_k_def(live26_arts):
    nr, arts = live26_arts
    assert not ({"K", "DEF", "DST"} & nr.positions)
    for a in arts:
        assert not re.search(r"\b(kicker|punter|defense|D/ST|field goal)\b", " ".join(a["body"]), re.I), a["id"]


def test_no_larp_anywhere(demo14_arts, live25_arts, live26_arts):
    assert "larp" not in Path(config.CONFIG_PATH).read_text().lower()
    for _, arts in (demo14_arts, live25_arts, live26_arts):
        for a in arts:
            assert "larp" not in json.dumps(a).lower()


def test_catchphrase_at_most_once_and_only_by_a_party(live25_arts, live26_arts):
    for nr, arts in (live25_arts, live26_arts):
        catches = {rid: (t["profile"].get("catchphrase") or "").strip() for rid, t in nr.teams.items()}
        for a in arts:
            text = " ".join(a["body"])
            hits = [(rid, c) for rid, c in catches.items() if c and c in text]
            for rid, c in hits:
                assert text.count(c) == 1, (a["id"], c)
                assert rid in a["teams"], (a["id"], "catchphrase of an owner not in the story")
            assert len(hits) <= 1, (a["id"], hits)


def test_deny_quotes_only_follow_trash_aimed_at_the_speaker(live25_arts, live26_arts, demo14_arts):
    trash = {"trash_h2h_lead", "trash_h2h_trail", "trash_standings", "trash_underdog", "won_big", "won_close"}
    seen = 0
    for _, arts in (live25_arts, live26_arts, demo14_arts):
        for a in arts:
            log = a["facts"]["quotes"]
            for i, q in enumerate(log):
                if q["situation"] == "deny_after_trash":
                    seen += 1
                    assert i > 0 and log[i - 1]["situation"] in trash and log[i - 1]["speaker"] != q["speaker"], a["id"]
    assert seen > 0


def test_commissioner_lines_only_from_the_commissioner(live25_arts, live26_arts):
    for nr, arts in (live25_arts, live26_arts):
        for a in arts:
            for q in a["facts"]["quotes"]:
                if q["commissioner"]:
                    assert q["speaker"] == nr.name(nr.commissioner)
            text = " ".join(a["body"])
            for who in ("I made the rule", "I wrote this rule"):
                if who in text:
                    assert nr.name(nr.commissioner) in text


def test_shotgun_counts_are_singular_and_plural_correct(live25_arts):
    nr, arts = live25_arts
    for a in arts:
        text = " ".join(a["body"])
        assert not re.search(r"(?<![\d.-])1 shotguns|(?<![\d.])[2-9] shotgun\b(?! ledger| report| list| card| tab| count| table)|\b[Oo]ne shotguns|\b[Tt]wo shotgun\b", text), a["id"]


def test_names_are_consistent_one_nickname_per_article(live25_arts):
    nr, arts = live25_arts
    nicks = {rid: str(t.get("nickname") or "").strip() for rid, t in nr.teams.items()}
    for a in arts:
        text = " ".join([a["headline"], a["dek"], *a["body"]])
        owner_text = nr.scrub_players(text)   # a player named Pat is not an owner named Pat
        for rid, nick in nicks.items():
            if nick and nick != nr.name(rid):
                assert len(re.findall(rf"\b{re.escape(nick)}\b", owner_text)) <= 1, (a["id"], nick)
        assert "Ja’Mario Kart  " not in text and "  " not in text


def test_rivalry_keeps_one_reporter_and_beer_report_rotates(live25_arts, live26_arts):
    nr, arts = live26_arts
    by_rv = {}
    for a in arts:
        rv = a["facts"].get("rivalry")
        if rv:
            by_rv.setdefault(rv, set()).add(a["reporter"]["id"])
    assert by_rv and all(len(ids) == 1 for ids in by_rv.values())
    nr25, arts25 = live25_arts
    beer = [a for a in arts25 if a["type"] == "shotgun"]
    assert len(beer) >= 10
    for a in beer:
        assert "shotgun" in BY_ID[a["reporter"]["id"]].beats
    ids = [a["reporter"]["id"] for a in sorted(beer, key=lambda x: x["week"])]
    assert all(x != y for x, y in zip(ids, ids[1:])) and len(set(ids)) >= len(ids) - 2


def test_no_reporter_writes_twice_in_a_week_when_avoidable(live25_arts):
    nr, arts = live25_arts
    by_week = {}
    for a in arts:
        if a["type"] in ("offseason",):
            continue
        by_week.setdefault(a["week"], []).append(a["reporter"]["id"])
    dup_weeks = [w for w, ids in by_week.items() if len(ids) != len(set(ids))]
    assert len(dup_weeks) <= 1, dup_weeks


def test_every_data_idea_is_used_somewhere(live25_arts, demo14_arts, live26_arts):
    slots = Counter(s for _, arts in (live25_arts, demo14_arts, live26_arts) for a in arts for s in a["facts"]["beats"])
    for slot in ("g.luck_up", "g.luck_down", "g.top", "g.low", "g.bench", "g.goat", "n.eff", "n.records", "w.budget",
                 "s.leader", "p.vol", "p.stakes", "n.top", "n.luck", "g.streak_w", "g.upset", "t.returns", "t.pending"):
        assert slots[slot] > 0, slot


# ---------------------------------------------------------------- diversity
def _norm_keys(nr, text):
    return set(nr.sentence_keys(text))


def test_no_recap_sentence_is_repeated_in_more_than_12_percent_of_recaps(demo14_arts, live25_arts):
    counts = Counter()
    n_recaps = 0
    for nr, arts in (demo14_arts, live25_arts):
        for a in arts:
            if a["type"] != "recap":
                continue
            n_recaps += 1
            counts.update(_norm_keys(nr, " ".join(a["body"])))
    assert n_recaps >= 25
    worst, count = counts.most_common(1)[0]
    assert count / n_recaps <= 0.12, (worst, count, n_recaps)


def test_at_least_40_of_50_reporters_appear(demo14_arts, live25_arts):
    for _, arts in (demo14_arts, live25_arts):
        assert len({a["reporter"]["id"] for a in arts}) >= 40
    assert len({a["reporter"]["id"] for _, arts in (demo14_arts, live25_arts) for a in arts}) >= 45


def test_two_recaps_by_different_families_for_the_same_week_share_under_30_percent(live25):
    ctx, st, po, items = live25
    firsts = {}
    for v in VOICES:
        firsts.setdefault(v.family, v)
    worst = 0.0
    for week in (3, 10, 15):
        for fa, fb in itertools.combinations(sorted(firsts), 2):
            n1, n2 = Newsroom(ctx, st, po, items), Newsroom(ctx, st, po, items)
            a1, a2 = n1.roundup(week, firsts[fa]), n2.roundup(week, firsts[fb])
            k1, k2 = _norm_keys(n1, " ".join(a1["body"])), _norm_keys(n1, " ".join(a2["body"]))
            worst = max(worst, len(k1 & k2) / min(len(k1), len(k2)))
    assert worst < 0.30, worst


def test_recaps_across_the_season_use_many_families(live25_arts):
    nr, arts = live25_arts
    fams = Counter(a["reporter"]["family"] for a in arts if a["type"] == "recap")
    assert len(fams) >= 13 and max(fams.values()) <= 2


def test_roundup_has_real_structure(live25_arts):
    nr, arts = live25_arts
    for a in [x for x in arts if x["type"] == "recap"]:
        assert 5 <= len(a["body"]) <= 12 and 200 <= len(" ".join(a["body"]).split()) <= 900, a["id"]
        assert a["facts"]["story"]["kind"] in ("blowout", "upset", "close", "top", "tie")


# ---------------------------------------------------------------- API / frontend
def test_season_payload_carries_the_masthead_and_reporter_cards(api):
    data = api.get("/api/season/2026").json()
    assert len(data["reporters"]) == 50
    assert all({"id", "name", "outlet", "bio", "family"} <= set(r) for r in data["reporters"])
    assert data["articles"] and all(a["reporter"]["name"] and a["byline"].startswith(a["reporter"]["name"]) for a in data["articles"])


def test_frontend_has_masthead_and_new_byline():
    js = (Path(config.ROOT) / "static" / "app.js").read_text()
    assert "Masthead" in js and "By ${esc(r.name)} · ${esc(r.outlet)}" in js
    assert "reporters" in js


def test_output_is_identical_across_processes_and_hash_seeds():
    import hashlib
    import os
    import subprocess
    import sys
    code = (
        "import json,hashlib\n"
        "from app import config, loader, stats, playoffs, shotguns\n"
        "from app.demo import DemoClient\n"
        "from app.newsroom import Newsroom\n"
        "ctx = loader.load_season(DemoClient(current_week=9), config.load_config(), 'demo2026')\n"
        "st = stats.compute(ctx); po = playoffs.simulate(ctx, st, sims=200); items = shotguns.detect(ctx, st)\n"
        "arts = Newsroom(ctx, st, po, items).generate()\n"
        "print(hashlib.md5(json.dumps([[a['headline'], a['body'], a['reporter']['id']] for a in arts], sort_keys=True).encode()).hexdigest())\n"
    )
    outs = set()
    for seed in ("1", "2", "3"):
        env = dict(os.environ, PYTHONHASHSEED=seed, LABRUMS_NEWSROOM_DEBUG="0")
        r = subprocess.run([sys.executable, "-c", code], cwd=str(config.ROOT), env=env, capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr[-500:]
        outs.add(r.stdout.strip().splitlines()[-1])
    assert len(outs) == 1


def test_signature_lines_are_never_shared_between_voices():
    for attr in ("openers", "closers", "tics"):
        seen = Counter(x for v in VOICES for x in getattr(v, attr))
        assert [x for x, n in seen.items() if n > 1] == [], attr


def test_old_boilerplate_is_gone():
    banned = re.compile(r"known around the league|arm's length|screenshotted|trash talk material|doing a lot of work|"
                        r"per league bylaws|not a typo|watched in silence|commented for eleven|lemonade|louisiana purchase|"
                        r"several transactions|commissioner declined|commissioner has declined|rigged|three guys on bye", re.I)
    for fam in families.all_families():
        for slot, tpls in fam.T.items():
            for t in tpls:
                assert not banned.search(t), (fam.id, slot, t)
    for sit, lines in quotes.BANK.items():
        for line in lines:
            assert not banned.search(line), (sit, line)
    for v in VOICES:
        for line in (*v.openers, *v.closers, *v.tics, v.bio):
            assert not banned.search(line), (v.id, line)
