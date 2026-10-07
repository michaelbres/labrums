"""Newsroom fix round 1: feuds about their two parties, grammar helpers, trade/waiver timing, quote/catchphrase
discipline and per-type sentence diversity."""
from __future__ import annotations

import copy
import re
from collections import Counter, defaultdict
from datetime import timedelta

import pytest

from app.newsroom import Newsroom, calendar, families, quotes
from app.newsroom.util import a_an, ordinal, plural, polish, sentence_case, split_sentences, verb

from .test_newsroom import LIVE_2025, LIVE_2026, _demo, _live

CATCH_TYPES = {"recap", "preview", "trade", "shotgun", "feud"}


@pytest.fixture(scope="module")
def demo14_arts():
    nr = Newsroom(*_demo(14), debug=True)
    return nr, nr.generate()


@pytest.fixture(scope="module")
def live25_arts():
    nr = Newsroom(*_live(LIVE_2025), debug=True)
    return nr, nr.generate()


@pytest.fixture(scope="module")
def live26_arts():
    nr = Newsroom(*_live(LIVE_2026), debug=True)
    return nr, nr.generate()


# ---------------------------------------------------------------- helpers (util)
def test_ordinal_tens_digit():
    got = {n: ordinal(n) for n in (1, 2, 3, 4, 10, 11, 12, 13, 14, 20, 21, 22, 23, 24, 101, 102, 111, 112, 113, 121, 122)}
    assert got == {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 10: "10th", 11: "11th", 12: "12th", 13: "13th", 14: "14th",
                   20: "20th", 21: "21st", 22: "22nd", 23: "23rd", 24: "24th", 101: "101st", 102: "102nd", 111: "111th",
                   112: "112th", 113: "113th", 121: "121st", 122: "122nd"}


def test_agreement_and_article_helpers():
    assert plural(1, "owner", "owners") == "1 owner" and plural(2, "owner", "owners") == "2 owners"
    assert verb(1, "owes", "owe") == "owes" and verb(3, "owes", "owe") == "owe"
    for phrase in ("83.21-point", "8-point", "11.61-point", "18.2-point", "80", "812-point"):
        assert a_an(phrase).startswith("an "), phrase
    for phrase in ("12.5-point", "118.5-point", "100.49", "1-point", "28-point"):
        assert a_an(phrase).startswith("a ") and not a_an(phrase).startswith("an "), phrase
    assert sentence_case("hello there") == "Hello there"


def test_polish_final_pass():
    assert polish("It ended.  two shotguns ,  and that is it.") == "It ended. Two shotguns, and that is it."
    assert polish("A 83.21-point win and a 12-point loss.") == "An 83.21-point win and a 12-point loss."
    assert polish("Cian: “Somebody tell my liver. two shotguns.”") == "Cian: “Somebody tell my liver. Two shotguns.”"
    assert polish("Nick beat Tom. iPhone Mafia lost.", re.compile("iPhone Mafia")) == "Nick beat Tom. iPhone Mafia lost."


def test_count_agreement_in_rendered_text():
    from app.newsroom.engine import agree
    out = agree("1 owner owe a combined 3 shotguns. 1 owner are liable for a combined 1 shotgun. 1 player were added.", {})
    assert "owner owes 3 shotguns" in out and "owner is liable for 1 shotgun" in out and "1 player was added" in out
    assert agree("3 owners owe a combined 5 shotguns. 3 players were added.", {}) == "3 owners owe a combined 5 shotguns. 3 players were added."


# ---------------------------------------------------------------- feud
def _team_words(book, text, exclude):
    scrubbed = book.scrub_players(text)
    return [nm for rid, nm in ((r, book.name(r)) for r in book.teams) if nm not in exclude
            and re.search(rf"\b{re.escape(nm)}\b", scrubbed)]


def test_feuds_name_only_their_two_parties(demo14_arts, live25_arts, live26_arts):
    n_feuds = 0
    for nr, arts in (demo14_arts, live25_arts, live26_arts):
        for a in arts:
            if a["type"] != "feud":
                continue
            n_feuds += 1
            parties = set(a["facts"]["teams"])
            assert len(parties) == 2
            for where, text in (("headline", a["headline"]), ("dek", a["dek"]), ("lede", a["body"][0])):
                assert not _team_words(nr, text, parties), (a["id"], where, text)
            for para in a["body"]:
                for sent in split_sentences(para):
                    for third in _team_words(nr, sent, parties):
                        assert f"over {third}" in sent, (a["id"], third, sent)
            # the primary incident is one of the two parties' own business, never somebody else's game
            assert a["facts"]["primary"] in {"h2h", "trade", "adj", "sg", "story", "trait"}
    assert n_feuds >= 20


# ---------------------------------------------------------------- trade timing, counts
def _synthetic_trades(week_hint=2):
    ctx, st, po, items = _demo(7)
    base = next(t for w in sorted(ctx["transactions"]) for t in ctx["transactions"][w]
                if t["type"] == "trade" and t["status"] == "complete" and not str(t["transaction_id"]).startswith("off")
                and w >= week_hint and len(t["roster_ids"]) == 2)
    wk = next(w for w in ctx["transactions"] if base in ctx["transactions"][w])
    rids = [int(x) for x in base["roster_ids"]]
    ctx = copy.deepcopy(ctx)
    ctx["transactions"] = {w: [t for t in v if t["type"] != "trade"] for w, v in ctx["transactions"].items()}
    txs = []
    for i in range(3):
        t = copy.deepcopy(base)
        t["transaction_id"] = f"zz{i}"
        t["created"] = int(base["created"]) + i * 3600_000
        txs.append(t)
    ctx["transactions"].setdefault(wk, []).extend(txs)
    return ctx, st, po, items, wk, rids, txs


def test_trade_count_is_chronological_per_owner():
    ctx, st, po, items, wk, rids, txs = _synthetic_trades()
    nr = Newsroom(ctx, st, po, items, debug=True)
    for i, tx in enumerate(txs, 1):
        assert [nr.moves_before(r, tx, wk)["trades"] for r in rids] == [i, i]
    words = ["first", "second", "third"]
    seen = []
    from app.newsroom.voices import BY_ID
    for i, tx in enumerate(txs):
        art = nr.trade(tx, wk, BY_ID["hollis-tanager"])
        text = " ".join(art["body"]).lower()
        seen.append(words[i] in text)
        assert art["facts"]["trade_counts"][nr.name(rids[0])]["trades"] == i + 1
    assert all(seen)


def test_trade_week_filter_both_branches():
    ctx, st, po, items, wk, rids, txs = _synthetic_trades()
    start = calendar.season_start(ctx)
    tuesday = calendar.week_tuesday(start, wk)
    nr = Newsroom(ctx, st, po, items, debug=True)
    tx = txs[0]
    from datetime import datetime, timezone
    # made the Monday before the Tuesday: week `wk` has not been counted out yet -> its points count
    before = datetime.combine(tuesday - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=20)
    tx["created"] = int(before.timestamp() * 1000)
    assert not nr.after_games(tx, wk) and nr.first_week_after(tx, wk) == wk and nr.records_week(tx, wk) == wk - 1
    # made on the Tuesday itself: that week's games are in the books -> returns start the next week
    after = datetime.combine(tuesday, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=16)
    tx["created"] = int(after.timestamp() * 1000)
    assert nr.after_games(tx, wk) and nr.first_week_after(tx, wk) == wk + 1 and nr.records_week(tx, wk) == wk
    # the number of weeks of evidence follows the same rule, and drives "too early" vs graded
    tx["created"] = int(before.timestamp() * 1000)
    w_during = nr.trade_info(tx, wk)["weeks"]
    tx["created"] = int(after.timestamp() * 1000)
    w_after = nr.trade_info(tx, wk)["weeks"]
    assert w_during == w_after + 1
    last = ctx["last_completed"]
    late = datetime.combine(calendar.week_tuesday(start, last), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=16)
    tx["created"] = int(late.timestamp() * 1000)
    ti = nr.trade_info(tx, last)
    assert ti["weeks"] == 0 and not ti["graded"]   # a deal made after the final completed week is "too early", not graded


def test_points_never_count_unplayed_weeks_or_rows_without_matchup_id():
    ctx, st, po, items = _demo(7)
    ctx = copy.deepcopy(ctx)
    nr = Newsroom(ctx, st, po, items, debug=True)
    last = ctx["last_completed"]
    assert nr.counted_weeks(1) == [w for w in sorted(ctx["matchups"]) if 1 <= w <= last]
    assert all(w <= last for w in nr.counted_weeks(1, 99))
    # a week whose rows carry no matchup_id (a week 18 nobody plays) is not a week of evidence
    for r in ctx["matchups"][last]:
        r["matchup_id"] = None
    nr2 = Newsroom(ctx, st, po, items, debug=True)
    assert last not in nr2.counted_weeks(1)
    rid = int(ctx["matchups"][1][0]["roster_id"])
    pid = next(iter(ctx["matchups"][last][0]["players_points"]), None)
    if pid:
        assert nr2.points_from(pid, last, rid) == 0.0


def test_duplicate_picks_collapse():
    nr = Newsroom(*_demo(7), debug=True)
    tx = {"roster_ids": [1, 2], "adds": {}, "draft_picks": [
        {"season": "2026", "round": 2, "owner_id": 1}, {"season": "2026", "round": 2, "owner_id": 1},
        {"season": "2027", "round": 1, "owner_id": 1}, {"season": "2026", "round": 3, "owner_id": 2}]}
    d = nr.tx_desc(tx)
    assert d[1]["picks"] == ["two 2026 round 2 picks", "a 2027 round 1 pick"] and d[1]["n_picks"] == 3
    assert d[2]["picks"] == ["a 2026 round 3 pick"]
    from app.newsroom.beats_misc import short_side
    assert short_side([], d[1]["picks"], d[1]["n_picks"]) == "3 picks"


# ---------------------------------------------------------------- recap lines
def _num(s):
    return float(re.search(r"-?\d+(?:\.\d+)?", s).group(0))


def test_bench_player_never_outscores_the_total_left(demo14_arts, live25_arts, live26_arts):
    seen = 0
    for nr, arts in (demo14_arts, live25_arts, live26_arts):
        for a in arts:
            if a["type"] != "recap":
                continue
            for g in a["facts"]["games"]:
                if g.get("bench_name"):
                    seen += 1
                    assert _num(g["bench_pts"]) <= _num(g["bench_left"]), (a["id"], g)
    assert seen > 0


def test_roster_combined_superlative_needs_a_majority(demo14_arts, live25_arts, live26_arts):
    said = 0
    for nr, arts in (demo14_arts, live25_arts, live26_arts):
        for a in arts:
            body = " ".join(a["body"])
            if re.search(r"rest of the roster combined|more than the rest", body):
                said += 1
                shares = [_num(g["sshare"]) for g in a["facts"].get("games", []) if g.get("sshare")]
                assert any(s > 50 for s in shares), (a["id"], shares)


# ---------------------------------------------------------------- waivers, previews, finance
def test_waiver_quotes_follow_the_outcome(demo14_arts, live25_arts, live26_arts):
    wanted = {"waiver_pending", "waiver_brag", "waiver_neutral", "waiver_miss"}
    seen = Counter()
    for nr, arts in (demo14_arts, live25_arts, live26_arts):
        for a in arts:
            if a["type"] != "waiver":
                continue
            since = a["facts"]["top"]["points_since"]
            sits = {q["situation"] for q in a["facts"]["quotes"]}
            assert len(sits) == 1 and sits <= wanted, (a["id"], sits)
            sit = next(iter(sits))
            expect = ("waiver_pending" if since is None else "waiver_brag" if since >= 15
                      else "waiver_neutral" if since >= 5 else "waiver_miss")
            assert sit == expect, (a["id"], since, sit)
            seen[sit] += 1
            if sit != "waiver_brag":
                assert not re.search(r"genius|\bproof\b|never been happier|visionary", " ".join(a["body"]), re.I), a["id"]
    assert len(seen) >= 2


def test_waiver_quote_banks_match_their_outcome():
    for sit in ("waiver_neutral", "waiver_miss", "waiver_pending"):
        for line in quotes.BANK[sit]:
            assert not re.search(r"genius|\bproof\b|never been happier|visionary", line, re.I), (sit, line)
    for sit in ("waiver_brag", "waiver_neutral", "waiver_miss", "waiver_pending", "trash_even"):
        assert len(quotes.BANK[sit]) >= 6


def test_previews_quote_every_game_and_underdog_talk_needs_worse_odds(demo14_arts, live26_arts):
    n = 0
    for nr, arts in (demo14_arts, live26_arts):
        for a in arts:
            if a["type"] not in ("preview",):
                continue
            n += 1
            metas = a["facts"]["paras"]
            games = {m["game"] for m in metas if m.get("game") is not None}
            assert games and games == set(range(len(a["facts"]["games"])))
            for k in games:
                paras = [p for p, m in zip(a["body"], metas) if m.get("game") == k]
                assert any("“" in p for p in paras), (a["id"], k)
            odds = {}
            for g in a["facts"]["games"]:
                pa, pb = (int(str(x).rstrip("%")) if x is not None else None for x in g["playoff_odds"])
                odds[g["teams"][0]] = (pa, pb)
                odds[g["teams"][1]] = (pb, pa)
            for q in a["facts"]["quotes"]:
                if q["situation"] == "trash_underdog":
                    me, opp = odds[q["speaker"]]
                    assert me is not None and opp is not None and me < opp, (a["id"], q)
    assert n >= 1


def test_finance_never_opens_a_recap_with_trade_closed():
    fam = families.get("finance")
    for slot, tpls in fam.T.items():
        for t in tpls:
            assert "Trade closed" not in t, (slot, t)


def test_new_quote_situations_are_gated_by_the_data():
    # a nobody-picks-me line must never come out of the generic bank
    for line in quotes.BANK["trash_even"]:
        assert not re.search(r"underdog|nobody's picking|spoiler", line, re.I), line


# ---------------------------------------------------------------- catchphrases, nicknames
def test_catchphrases_once_per_owner_per_week_only_for_main_parties_and_rare(live25_arts, live26_arts, demo14_arts):
    total = with_catch = 0
    for nr, arts in (live25_arts, live26_arts, demo14_arts):
        catches = {rid: (t["profile"].get("catchphrase") or "").strip() for rid, t in nr.teams.items()}
        per_week = defaultdict(list)
        for a in arts:
            total += 1
            text = " ".join(a["body"])
            hit = [(rid, c) for rid, c in catches.items() if c and c in text]
            if hit:
                with_catch += 1
                assert a["type"] in CATCH_TYPES, (a["id"], a["type"])
            for rid, c in hit:
                per_week[(rid, a["week"])].append(a["id"])
                assert rid in a["teams"], a["id"]
        assert all(len(v) == 1 for v in per_week.values()), {k: v for k, v in per_week.items() if len(v) > 1}
    assert with_catch / total <= 0.20, (with_catch, total)


def test_live_2025_catchphrase_share_at_most_20_percent(live25_arts):
    nr, arts = live25_arts
    catches = [(t["profile"].get("catchphrase") or "").strip() for t in nr.teams.values()]
    catches = [c for c in catches if c]
    n = sum(1 for a in arts if any(c in " ".join(a["body"]) for c in catches))
    assert n / len(arts) <= 0.20, (n, len(arts))


def test_nickname_only_as_an_aside_once_per_article(live25_arts, live26_arts, demo14_arts):
    uses = 0
    for nr, arts in (live25_arts, live26_arts, demo14_arts):
        for a in arts:
            owner_text = nr.scrub_players(" ".join([a["headline"], a["dek"], *a["body"]]))
            for chunk in [rv["backstory"].strip() for rv in nr.rivalries if rv.get("backstory")] + \
                    [str(c) for t in nr.teams.values() for c in [(t.get("profile") or {}).get("catchphrase")] + list((t.get("profile") or {}).get("traits") or []) if c]:
                owner_text = owner_text.replace(chunk, "")
            for rid, t in nr.teams.items():
                nick = str(t.get("nickname") or "").strip()
                if not nick or nick == nr.name(rid):
                    continue
                found = re.findall(rf"\b{re.escape(nick)}\b", owner_text)
                assert len(found) <= 1, (a["id"], nick)
                if found:
                    uses += 1
                    assert f"{nr.name(rid)}, “{nick}” to the group chat," in owner_text, (a["id"], nick)
    assert uses >= 0


# ---------------------------------------------------------------- per-type diversity
_OWN = re.compile(r"\b(?:[A-Z][a-z]+)(?:'s)?\b")


def _norm(nr, s):
    keys = nr.sentence_keys(s)
    return keys[0] if keys else None


def test_no_sentence_dominates_any_article_type(demo14_arts, live25_arts, live26_arts):
    counts = defaultdict(Counter)
    n_type = Counter()
    for nr, arts in (demo14_arts, live25_arts, live26_arts):
        for a in arts:
            n_type[a["type"]] += 1
            seen = set()
            for para in a["body"]:
                for sent in split_sentences(para):
                    k = _norm(nr, sent)
                    if k:
                        seen.add(k)
            counts[a["type"]].update(seen)
    checked = 0
    for t, c in counts.items():
        n = n_type[t]
        if n < 4:   # three offseason pieces cannot be "12%" of anything
            continue
        checked += 1
        allowed = max(1, int(0.12 * n))
        worst, hits = c.most_common(1)[0]
        assert hits <= allowed, (t, n, hits, allowed, worst)
    assert checked >= 7
