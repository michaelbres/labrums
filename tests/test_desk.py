"""Editorial desk, stable keys, release calendar, and the Sunday column / Monday analytics types."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app import articles, config
from app.newsroom import Newsroom, calendar, desk, families, lint, tools
from app.newsroom.voices import VOICES

from .test_api import _load_app
from .test_newsroom import _demo, LIVE_2026, _live

ROOT = Path(config.ROOT)
START = date(2026, 9, 9)   # a Wednesday: the 2026 season start in the live cache


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def demo7():
    return _demo(7)


@pytest.fixture(scope="module")
def demo7_arts(demo7):
    nr = Newsroom(*demo7, debug=True)
    return nr, nr.generate(use_desk=False)


@pytest.fixture
def desk_dir(tmp_path, monkeypatch):
    """A scratch content/articles tree; the desk reads it instead of the repo's."""
    d = tmp_path / "articles"
    (d / "2026").mkdir(parents=True)
    monkeypatch.setattr(desk, "CONTENT_DIR", d)
    desk.clear_cache()
    yield d / "2026"
    desk.clear_cache()


def _write_desk(folder: Path, week: int, entries: list[dict]) -> Path:
    p = folder / f"week-{week}.json"
    p.write_text(json.dumps({"week": week, "articles": entries}), encoding="utf-8")
    return p


def _first(arts, kind):
    return next(a for a in arts if a["type"] == kind)


def _body_naming(nr, a, extra=""):
    """A hand-written body that names every owner the template article names (the coherence lint wants that)."""
    names = ", ".join(nr.name(r) for r in a["teams"])
    return [f"The desk wrote this one by hand, and it covers {names}. {extra}".strip(),
            "A second paragraph, because the desk files at least two."]


# ---------------------------------------------------------------- stable keys
def test_every_article_has_a_unique_stable_key(demo7_arts):
    nr, arts = demo7_arts
    keys = [a["key"] for a in arts]
    assert len(set(keys)) == len(keys)
    for a in arts:
        season, kind, week, teams = a["key"].split(":")[:4]
        assert (season, kind, int(week)) == (nr.season, a["type"], a["week"]), a["key"]
        assert a["source"] == "template" and "_created" not in a and "_txid" not in a
    assert any(a["key"].endswith(":all") for a in arts if a["type"] in ("recap", "preview"))
    pair_types = {"feud", "column", "rivalry", "trade"}
    assert all(a["key"].split(":")[3] != "all" for a in arts if a["type"] in pair_types)


def test_keys_identical_across_runs_and_independent_of_reporter_assignment(demo7, monkeypatch):
    a = Newsroom(*demo7, debug=True).generate(use_desk=False)
    b = Newsroom(*demo7, debug=True).generate(use_desk=False)
    assert [x["key"] for x in a] == [x["key"] for x in b]
    # Reverse the casting: different reporters write everything, but every key is the same.
    from app.newsroom import Assigner
    real = Assigner.pick

    def reversed_pick(self, beat, week):
        elig = [v for v in self.voices if beat in v.beats]
        free = [v for v in elig if v.id not in self.week_used[week]] or elig
        return max(free, key=lambda v: (-self.fam[(beat, v.family)], -self.beat_use[(beat, v.id)], -self.total[v.id], self.rank(beat, v.id)))
    monkeypatch.setattr(Assigner, "pick", reversed_pick)
    c = Newsroom(*demo7, debug=True).generate(use_desk=False)
    monkeypatch.setattr(Assigner, "pick", real)
    assert sorted(x["key"] for x in c) == sorted(x["key"] for x in a)
    assert {x["key"]: x["reporter"]["id"] for x in c} != {x["key"]: x["reporter"]["id"] for x in a}


# ---------------------------------------------------------------- desk overrides
def test_desk_override_replaces_text_and_reporter(demo7, desk_dir):
    nr0 = Newsroom(*demo7, debug=True)
    tmpl = nr0.generate(use_desk=False)
    target = _first(tmpl, "recap")
    guest = {"name": "Imogen Plume", "outlet": "The Desk Gazette", "bio": "Wrote this by hand."}
    _write_desk(desk_dir, target["week"], [{
        "key": target["key"], "headline": "A hand-written headline", "dek": "A hand-written dek.",
        "body": _body_naming(nr0, target), "reporter": guest, "tags": ["recap", "desk"], "publish_on": "2020-01-01"}])
    nr = Newsroom(*demo7, debug=True)
    out = nr.generate()
    a = next(x for x in out if x["key"] == target["key"])
    assert a["source"] == "desk" and a["headline"] == "A hand-written headline" and a["dek"] == "A hand-written dek."
    assert a["byline"] == "Imogen Plume, The Desk Gazette" and a["reporter"]["name"] == "Imogen Plume"
    assert a["tags"] == ["recap", "desk"] and a["publish_on"] == "2020-01-01"
    assert len(a["facts"]["paras"]) == len(a["body"]) and a["facts"]["games"]
    assert [r["ok"] for r in nr.desk_report] == [True]
    assert all(x["source"] == "template" for x in out if x["key"] != target["key"])
    # keeps the assigned reporter when none is given
    _write_desk(desk_dir, target["week"], [{"key": target["key"], "headline": "Again", "body": _body_naming(nr0, target)}])
    desk.clear_cache()
    b = next(x for x in Newsroom(*demo7, debug=True).generate() if x["key"] == target["key"])
    assert b["source"] == "desk" and b["reporter"] == target["reporter"] and b["dek"] == target["dek"]


def test_desk_unknown_key_is_ignored_and_logged(demo7, desk_dir, caplog):
    _write_desk(desk_dir, 3, [{"key": "2026:recap:99:all", "headline": "Nope", "body": ["Nothing here."]}])
    with caplog.at_level("WARNING"):
        nr = Newsroom(*demo7, debug=True)
        out = nr.generate()
    assert all(a["source"] == "template" for a in out)
    assert nr.desk_report[0]["ok"] is False and "unknown key" in nr.desk_report[0]["problems"][0]
    assert "unknown key" in caplog.text


@pytest.mark.parametrize("bad", [
    {"headline": "", "body": ["x"]},
    {"headline": "Fine", "body": []},
    {"headline": "Has {braces}", "body": ["x"]},
    {"headline": "Fine", "body": ["A LARP joke."]},
    {"headline": "Fine", "body": ["Two  spaces."]},
    {"headline": "Fine", "body": ["Fine."], "publish_on": "tuesday"},
])
def test_desk_lint_failure_is_skipped_and_template_stays(demo7, desk_dir, bad):
    tmpl = Newsroom(*demo7, debug=True).generate(use_desk=False)
    target = _first(tmpl, "waiver")
    _write_desk(desk_dir, target["week"], [{"key": target["key"], **bad}])
    nr = Newsroom(*demo7, debug=True)
    out = nr.generate()
    a = next(x for x in out if x["key"] == target["key"])
    assert a["source"] == "template" and a["headline"] == target["headline"] and a["body"] == target["body"]
    assert nr.desk_report[0]["ok"] is False and nr.desk_report[0]["problems"]


def test_desk_article_must_mention_every_team_it_covers(demo7, desk_dir):
    tmpl = Newsroom(*demo7, debug=True).generate(use_desk=False)
    target = _first(tmpl, "recap")
    _write_desk(desk_dir, target["week"], [{"key": target["key"], "headline": "Short", "body": ["Nobody is named here."]}])
    nr = Newsroom(*demo7, debug=True)
    out = nr.generate()
    assert next(x for x in out if x["key"] == target["key"])["source"] == "template"
    assert any("not mentioned" in p for p in nr.desk_report[0]["problems"])


def test_desk_files_are_reread_when_they_change(demo7, desk_dir):
    tmpl = Newsroom(*demo7, debug=True).generate(use_desk=False)
    target = _first(tmpl, "waiver")
    nr0 = Newsroom(*demo7, debug=True)
    p = _write_desk(desk_dir, target["week"], [{"key": target["key"], "headline": "One", "body": _body_naming(nr0, target)}])
    assert next(x for x in Newsroom(*demo7, debug=True).generate() if x["key"] == target["key"])["headline"] == "One"
    p.write_text(json.dumps({"week": target["week"], "articles": [{"key": target["key"], "headline": "Two", "body": _body_naming(nr0, target)}]}))
    assert next(x for x in Newsroom(*demo7, debug=True).generate() if x["key"] == target["key"])["headline"] == "Two"


def test_check_file_reports_pass_and_fail_per_article(demo7, desk_dir):
    nr = Newsroom(*demo7, debug=True)
    tmpl = nr.generate(use_desk=False)
    good, other = _first(tmpl, "waiver"), _first(tmpl, "recap")
    p = _write_desk(desk_dir, good["week"], [
        {"key": good["key"], "headline": "Good", "body": _body_naming(nr, good)},
        {"key": other["key"], "headline": "Bad {x}", "body": ["x"]},
        {"key": "2026:nope:1:all", "headline": "x", "body": ["x"]},
    ])
    rows = tools.check_file(p, tmpl, nr)
    assert [r["ok"] for r in rows] == [True, False, False]
    assert any("unknown key" in x for x in rows[2]["problems"])
    assert any("words" in w for w in rows[0]["warnings"])   # a 20-word recap is under target: warned, not failed
    bad = desk_dir / "week-9.json"
    bad.write_text("{not json")
    assert tools.check_file(bad, tmpl, nr)[0]["ok"] is False


def test_lint_script_exit_codes(tmp_path):
    """End to end against the offline demo league: exit 0 for a clean file, 1 for a bad one."""
    d = tmp_path / "2026"
    d.mkdir()
    env = {"LABRUMS_DEMO": "1", "LABRUMS_DEMO_DB": "memory", "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    ctx_, st_, po_, items_ = _demo(7)
    nr = Newsroom(ctx_, st_, po_, items_, debug=True)
    target = _first(nr.generate(use_desk=False), "waiver")
    ok = _write_desk(d, target["week"], [{"key": target["key"], "headline": "Fine", "body": _body_naming(nr, target)}])
    bad = d / "week-1.json"
    bad.write_text(json.dumps({"week": 1, "articles": [{"key": target["key"], "headline": "Has {braces}", "body": ["x"]}]}))
    run = lambda f: subprocess.run([sys.executable, str(ROOT / "scripts" / "newsroom_lint.py"), str(f)], capture_output=True, text=True, env=env, cwd=ROOT)
    r_ok, r_bad = run(ok), run(bad)
    assert r_ok.returncode == 0 and "PASS" in r_ok.stdout, r_ok.stdout + r_ok.stderr
    assert r_bad.returncode == 1 and "FAIL" in r_bad.stdout, r_bad.stdout + r_bad.stderr


# ---------------------------------------------------------------- facts export
def test_facts_export_is_valid_json_with_every_key(demo7, demo7_arts, tmp_path):
    nr, arts = demo7_arts
    week = max(a["week"] for a in arts if a["type"] == "recap")
    data = tools.export_week(nr.season, nr, arts, week)
    p = tmp_path / "facts" / "2026" / f"week-{week}.json"
    tools.write_json(p, data)
    back = json.loads(p.read_text(encoding="utf-8"))
    want = {a["key"] for a in arts if a["week"] == week}
    assert {a["key"] for a in back["articles"]} == want and len(want) >= 4
    assert len(back["owners"]) == len(nr.teams)
    for a in back["articles"]:
        assert a["facts"] and a["beats"] and a["template"]["headline"] and a["template"]["body"]
        assert "paras" not in a["facts"] and "beats" not in a["facts"]
        card = a["reporter"]
        for k in ("name", "outlet", "bio", "family_description", "signature_openers", "signature_closers", "verbal_tics",
                  "sentence_rhythm", "metaphor_domain"):
            assert card[k], (a["key"], k)
        assert a["target_words"]["min"] < a["target_words"]["max"]
    assert tools.pending_weeks("2026", arts)   # no desk files in the scratch tree


def test_facts_export_script_writes_the_file(tmp_path):
    out = tmp_path / "w.json"
    env = {"LABRUMS_DEMO": "1", "LABRUMS_DEMO_DB": "memory", "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "newsroom_facts.py"), "--season", "2026", "--week", "3", "--out", str(out)],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["week"] == 3 and data["articles"]


def test_facts_gitignored_and_never_on_the_wire(monkeypatch):
    assert "content/facts/" in (ROOT / ".gitignore").read_text().splitlines()
    main = _load_app(monkeypatch)
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        data = c.get("/api/season/2026").json()
        assert data["articles"] and all("facts" not in a for a in data["articles"])
        assert all(a["key"] and a["source"] in ("template", "desk") and a["publish_on"] for a in data["articles"])
        assert set(data["meta"]["desk"]) == {"weeks_covered", "upcoming"}
        model = main.state.base_model("2026")
        assert all("facts" in a for a in model["articles"])   # still there for the desk export


# ---------------------------------------------------------------- release calendar
@pytest.mark.parametrize("kind,week,expect", [
    ("recap", 1, "2026-09-15"), ("shotgun", 1, "2026-09-15"), ("waiver", 1, "2026-09-16"), ("trade", 1, "2026-09-16"),
    ("feud", 1, "2026-09-18"), ("standings", 1, "2026-09-19"), ("column", 1, "2026-09-20"), ("analytics", 1, "2026-09-21"),
    ("recap", 4, "2026-10-06"), ("shotgun", 4, "2026-10-06"), ("waiver", 4, "2026-10-07"), ("trade", 4, "2026-10-07"),
    ("preview", 5, "2026-10-08"), ("rivalry", 5, "2026-10-08"), ("feud", 4, "2026-10-09"), ("standings", 4, "2026-10-10"),
    ("column", 4, "2026-10-11"), ("analytics", 4, "2026-10-12"), ("recap", 5, "2026-10-13"), ("preview", 6, "2026-10-15"),
    ("offseason", 1, "2026-09-09"),
])
def test_publish_on_mapping_for_a_known_start_date(kind, week, expect):
    assert calendar.publish_on(kind, week, START) == expect


def test_calendar_weekdays():
    wd = lambda kind, week: date.fromisoformat(calendar.publish_on(kind, week, START)).strftime("%a")
    assert [wd(k, 4) for k in ("recap", "shotgun", "waiver", "trade", "feud", "standings", "column", "analytics")] == \
        ["Tue", "Tue", "Wed", "Wed", "Fri", "Sat", "Sun", "Mon"]
    assert wd("preview", 5) == wd("rivalry", 5) == "Thu"
    # a start date that is itself a Tuesday still gets a Tuesday strictly after it
    assert calendar.week_tuesday(date(2026, 9, 8), 1) == date(2026, 9, 15)


def test_trade_made_after_tuesday_posts_the_next_day_at_6am():
    ms = lambda y, m, d, h: int(datetime(y, m, d, h, tzinfo=timezone(timedelta(hours=-4))).timestamp() * 1000)
    # week 4's Tuesday is Oct 6: the default is Wednesday the 7th
    assert calendar.publish_on("trade", 4, START, tx_created_ms=ms(2026, 10, 5, 12)) == "2026-10-07"
    assert calendar.publish_on("trade", 4, START, tx_created_ms=ms(2026, 10, 6, 21)) == "2026-10-07"
    # made on Wednesday evening: posts Thursday
    assert calendar.publish_on("trade", 4, START, tx_created_ms=ms(2026, 10, 7, 19)) == "2026-10-08"


def test_unknown_start_falls_back_to_today():
    today = date(2026, 10, 7)
    assert calendar.publish_on("column", 3, None, today=today) == "2026-10-07"
    assert calendar.publish_on("offseason", 1, None, today=today) == "2026-10-07"


def test_effective_today_flips_at_6am_eastern(monkeypatch):
    et = timezone(timedelta(hours=-4))
    assert calendar.effective_today(datetime(2026, 10, 9, 5, 59, tzinfo=et)) == date(2026, 10, 8)
    assert calendar.effective_today(datetime(2026, 10, 9, 6, 0, tzinfo=et)) == date(2026, 10, 9)
    monkeypatch.setenv("LABRUMS_NOW", "2026-10-09T05:59:00-04:00")
    assert calendar.now_et().hour == 5
    assert calendar._et_fixed(datetime(2026, 7, 1, 12, tzinfo=timezone.utc)).utcoffset() == timedelta(hours=-4)
    assert calendar._et_fixed(datetime(2026, 1, 1, 12, tzinfo=timezone.utc)).utcoffset() == timedelta(hours=-5)


def test_live_2026_publish_dates_follow_the_calendar():
    ctx, st, po, items = _live(LIVE_2026)
    arts = Newsroom(ctx, st, po, items, debug=True).generate(use_desk=False)
    assert calendar.season_start(ctx) == START
    by = {(a["type"], a["week"]): a["publish_on"] for a in arts}
    assert by[("recap", 4)] == "2026-10-06" and by[("preview", 5)] == "2026-10-08" and by[("standings", 4)] == "2026-10-10"
    assert by[("column", 4)] == "2026-10-11" and by[("analytics", 4)] == "2026-10-12"
    for a in arts:
        assert a["publish_on"] == calendar.publish_on(a["type"], a["week"], START, tx_created_ms=None) or a["type"] == "trade", a["key"]


def test_hidden_and_visible_filtering_with_a_frozen_today(monkeypatch):
    """Demo season 2026 (start 2023-11-20, the current season): later days' articles are held back until 6 am."""
    main = _load_app(monkeypatch)
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        def fetch(now, url="/api/season/2026"):
            monkeypatch.setenv("LABRUMS_NOW", now)
            return c.get(url).json()
        early = fetch("2023-11-27T05:00:00-05:00")         # still Sunday's edition: through 11-26
        assert early["articles"] and all(a["publish_on"] <= "2023-11-26" for a in early["articles"])
        up = early["meta"]["desk"]["upcoming"]
        assert up and all(u["publish_on"] > "2023-11-26" for u in up) and set(up[0]) == {"type", "week", "publish_on"}
        assert up == sorted(up, key=lambda u: (u["publish_on"], u["week"], u["type"]))
        assert ("analytics", "2023-11-27") in {(u["type"], u["publish_on"]) for u in up}
        after = fetch("2023-11-27T06:00:00-05:00")         # Monday 6 am: analytics goes live
        assert any(a["type"] == "analytics" and a["publish_on"] == "2023-11-27" for a in after["articles"])
        assert len(after["articles"]) > len(early["articles"])
        assert len(early["articles"]) + len(up) == len(fetch("2030-01-01T00:00:00-05:00")["articles"])
        assert fetch("2030-01-01T00:00:00-05:00")["meta"]["desk"]["upcoming"] == []
        # ?preview=1 shows everything (no admin pin configured in this fixture)
        assert len(fetch("2023-11-27T05:00:00-05:00", "/api/season/2026?preview=1")["articles"]) == len(early["articles"]) + len(up)


def test_preview_flag_needs_the_admin_pin(monkeypatch):
    main = _load_app(monkeypatch, pin="secret")
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LABRUMS_NOW", "2023-11-27T05:00:00-05:00")
    with TestClient(main.app) as c:
        assert c.get("/api/season/2026?preview=1").status_code == 401
        assert c.get("/api/season/2026?preview=1", headers={"X-Admin-Pin": "secret"}).status_code == 200
        assert c.get("/api/season/2026").status_code == 200   # the normal view needs no pin


def test_past_seasons_show_everything(monkeypatch):
    main = _load_app(monkeypatch)
    from fastapi.testclient import TestClient
    monkeypatch.setenv("LABRUMS_NOW", "2020-01-01T09:00:00-05:00")   # long before any demo date
    with TestClient(main.app) as c:
        past = c.get("/api/season/2025").json()
        assert past["articles"] and past["meta"]["desk"]["upcoming"] == []


# ---------------------------------------------------------------- the two new types
@pytest.mark.parametrize("fid", families.FAMILY_IDS)
def test_every_family_has_the_column_and_analytics_templates(fid):
    fam = families.get(fid)
    for slot in ("h.c", "h.c.rv", "h.c.next", "c.lede", "c.next", "c.recent", "c.gap", "c.pick", "c.close",
                 "h.a.luck", "h.a.eff", "h.a.bench", "h.a.steady", "a.lede", "a.luck", "a.eff", "a.bench", "a.blunder",
                 "a.steady", "a.trade", "a.close"):
        assert len(fam.T[slot]) >= 3, (fid, slot)
        assert slot in families.SLOTS
    assert len(fam.T["h.c"]) >= 4
    assert families.validate(fam) == []


def test_voices_cover_the_new_beats_in_every_family():
    for fid in families.FAMILY_IDS:
        vs = [v for v in VOICES if v.family == fid]
        assert sum("column" in v.beats for v in vs) >= 2 and sum("analytics" in v.beats for v in vs) >= 2, fid


def test_column_and_analytics_exist_for_every_completed_week(demo7_arts):
    nr, arts = demo7_arts
    last = nr.ctx["last_completed"]
    for kind in ("column", "analytics"):
        weeks = {a["week"] for a in arts if a["type"] == kind}
        assert weeks >= set(range(2, last + 1)), (kind, weeks)
        assert all(a["tags"][0] == kind for a in arts if a["type"] == kind)
    assert lint.check(_first(arts, "column"), nr) == [] and lint.check(_first(arts, "analytics"), nr) == []


def test_columns_are_grounded_in_the_data(demo7_arts):
    nr, arts = demo7_arts
    for a in [x for x in arts if x["type"] == "column"]:
        f = a["facts"]
        text = " ".join([a["headline"], a["dek"], *a["body"]])
        assert all(n in text for n in f["teams"]), a["id"]
        assert f["through_week"] == a["week"] and len(f["records"]) == 2
        names = f["teams"]
        # the h2h line and the pick only claim what the facts say
        assert f["h2h_this_season"] == "no meeting yet" or all(ch in "0123456789-" for ch in f["h2h_this_season"])
        if f["pick"]:
            assert f["pick"] in names and f["pick_basis"] in ("playoff odds", "scoring average")
        if f["next_meeting_week"]:
            assert f["next_meeting_week"] > nr.ctx["last_completed"] and str(f["next_meeting_week"]) in a["dek"]
        if f["rivalry"]:
            assert any(r["name"] == f["rivalry"] for r in nr.rivalries)
        assert "{" not in text


def test_analytics_figures_match_the_snapshot(demo7_arts):
    nr, arts = demo7_arts
    for a in [x for x in arts if x["type"] == "analytics"]:
        f = a["facts"]
        S = nr.snap(f["through_week"])
        if "luck_index" in f:
            li = f["luck_index"]
            by_name = {nr.name(r): S["teams"][r] for r in S["teams"]}
            assert by_name[li["luckiest"]]["luck"] == max(t["luck"] for t in S["teams"].values())
            assert by_name[li["unluckiest"]]["luck"] == min(t["luck"] for t in S["teams"].values())
            assert float(li["luckiest_luck"]) >= 1 and float(li["unluckiest_luck"]) <= -1
        if "lineup_efficiency" in f:
            le = f["lineup_efficiency"]
            assert int(le["best_pct"][:-1]) > int(le["worst_pct"][:-1])
        text = " ".join(a["body"])
        for blob in f.values():
            if isinstance(blob, dict):
                for v in blob.values():
                    if isinstance(v, str) and v in {nr.name(r) for r in nr.teams}:
                        assert v in text, (a["id"], v)


def test_every_family_can_write_both_new_types(demo7):
    nr0 = Newsroom(*demo7, debug=True)
    week = nr0.ctx["last_completed"]
    pair = nr0.column_pair(week, None, set(), nr0.rng("t"))
    assert pair
    ca, cb, rv, nxt = pair
    seen = set()
    for fid in families.FAMILY_IDS:
        v = next(x for x in VOICES if x.family == fid and "column" in x.beats and "analytics" in x.beats)
        nr = Newsroom(*demo7, debug=True)
        col = nr.column(week, ca, cb, rv, nxt, v)
        ana = nr.analytics(week, v)
        for art in (col, ana):
            assert art and lint.check(art, nr) == [], (fid, art and lint.check(art, nr))
            assert art["reporter"]["family"] == fid and len(art["body"]) >= 4
        seen.add(col["body"][0])
    assert len(seen) == len(families.FAMILY_IDS)   # fourteen different ledes


def test_new_types_in_live_2026(live26=None):
    ctx, st, po, items = _live(LIVE_2026)
    nr = Newsroom(ctx, st, po, items, debug=True)
    arts = nr.generate(use_desk=False)
    kinds = {a["type"] for a in arts}
    assert {"column", "analytics"} <= kinds
    col4 = next(a for a in arts if a["type"] == "column" and a["week"] == 4)
    assert col4["facts"]["next_meeting_week"] == 5 and "they meet in Week 5" in col4["dek"]


# ---------------------------------------------------------------- frontend
def test_frontend_footer_storage_and_desk_mark():
    js = (ROOT / "static" / "app.js").read_text()
    css = (ROOT / "static" / "styles.css").read_text()
    assert "meta.persistence" in js and "storage: redis" in js and "storage: local" in js
    assert "storage: temporary (check-offs won\\'t persist)" in js and "storage warn" in js
    assert "✎ Desk" in js and "a.source === 'desk'" in js
    assert ".foot .storage.warn" in css and "var(--warn)" in css
    for kind in ("column", "analytics"):
        assert f".article.type-{kind}" in css and f"--c-{kind}" in css
    assert "'column', 'analytics'" in js


def test_readme_mentions_the_editorial_desk():
    assert "Editorial desk" in (ROOT / "README.md").read_text()
    guide = (ROOT / "docs" / "newsroom.md").read_text()
    for needle in ("newsroom_facts.py", "newsroom_lint.py", "content/articles/", "180-320", "120-220", "LARP", "publish_on"):
        assert needle in guide, needle


def test_quote_banks_never_cross_margin_classes():
    """A close-game quote may not say 'blowout' (and vice versa): the recap lint checks quote paragraphs too."""
    from app.newsroom import quotes
    for sit, lines in quotes.BANK.items():
        for line in lines:
            if sit in ("won_close", "lost_close", "tied"):
                assert not lint.BLOW_RE.search(line), (sit, line)
            if sit in ("won_big", "lost_big", "tied"):
                assert not lint.CLOSE_RE.search(line), (sit, line)


@pytest.mark.parametrize("fid", families.FAMILY_IDS)
def test_templates_name_both_parties(fid):
    """The coherence lint wants every owner a piece is about to be named; so does the reader."""
    need = {"a.trade": ("{lead}", "{trail}"), "a.luck": ("{lucky}", "{unlucky}"), "a.eff": ("{best_n}", "{worst_n}"),
            "a.bench": ("{bench_n}", "{bench_low_n}"), "a.steady": ("{steady_n}", "{wild_n}"), "c.gap": ("{hi}", "{lo}"),
            "c.recent": ("{a}", "{b}"), "c.lede": ("{a}", "{b}"), "c.pick": ("{fav}", "{dog}"), "c.close": ("{a}", "{b}")}
    fam = families.get(fid)
    for slot, keys in need.items():
        for t in fam.T[slot]:
            assert all(k in t for k in keys), (fid, slot, t)
