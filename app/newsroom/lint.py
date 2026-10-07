"""Coherence lint. Run in generate() (debug mode raises) and in the test-suite."""
from __future__ import annotations

import re

BLOW_RE = re.compile(r"massacre|\brout(?:ed|s)?\b|demoli|obliterat|annihilat|steamroll|pummel|dismantl|thrash|humiliat|"
                     r"shellack|landslide|blowout|flatten|\bcrush|destroy|decimat|bulldoz|\bmauled?\b|wreck", re.I)
CLOSE_RE = re.compile(r"\bescap|thriller|nail-?bit|squeaker|photo finish|whisker|\bedged\b|\bedges\b|razor|"
                      r"survived|survives|heart-?stop|sweated|sweating|cliffhanger|knife-?edge|by a hair", re.I)
PLAYOFF_BAD = re.compile(r"drops to|moved to|moves to|bylaws|alive for|\bstanding ovation\b", re.I)
GENERIC_BAD = re.compile(r"\bassets\b|nothing of note|\bnan\b|(?<![\w.])1 (?:points|shotguns|players|picks|wins|games|trades)\b|"
                         r"\bLARP|\bkicker|\bpunter|\bundefined\b", re.I)
CASE_BAD = re.compile(r"\bNone\b")


def _paras(a: dict) -> list[tuple[str, dict]]:
    metas = (a.get("facts") or {}).get("paras") or []
    out = []
    for i, p in enumerate(a["body"]):
        out.append((p, metas[i] if i < len(metas) else {}))
    return out


def check(a: dict, book=None) -> list[str]:
    probs: list[str] = []
    head, dek, body = a["headline"], a["dek"], a["body"]
    text = " ".join([head, dek, *body])
    aid = a["id"]

    def bad(msg: str) -> None:
        probs.append(f"{aid}: {msg}")

    scrub = text
    themes = sorted({n.theme for n in getattr(book, "narrs", []) if n.theme}, key=len, reverse=True) if book is not None else []
    if book is not None:  # owner-written text (catchphrases, traits, narrative themes) may legitimately contain braces
        for t in book.teams.values():
            prof = t.get("profile") or {}
            for chunk in [prof.get("catchphrase")] + list(prof.get("traits") or []):
                for variant in (chunk, str(chunk or "").replace("{me}", "").replace("{them}", "")):
                    if variant:
                        scrub = scrub.replace(str(variant), "")
        for th in themes:   # a deadpan sentence may open with the theme, which then gets a capital
            scrub = re.sub(re.escape(th), "", scrub, flags=re.I)
    if re.search(r"[{}]", scrub):
        bad("unfilled braces")
    if "  " in text:
        bad("double space")
    if re.search(r"(?<!\.)\.\.(?!\.)|,,|\s,|\s\.(?!\d)|\.\s\.", text):
        bad("double/stray punctuation")
    for p in [head, dek, *body]:
        if re.search(r"[.!?]”\s+[a-z]", p):
            bad(f"lowercase sentence start after a quote: {p[:80]!r}")
        if p != p.strip() or not p:
            bad("empty or untrimmed paragraph")
    if re.search(r"larp", text, re.I):
        bad("LARP")
    m = GENERIC_BAD.search(text)
    if m and not (m.group(0).lower() in ("kicker", "punter") and book is not None and ({"K", "DEF", "DST"} & book.positions)):
        bad(f"banned phrase {m.group(0)!r}")
    if CASE_BAD.search(text):
        bad(f"banned token {CASE_BAD.search(text).group(0)!r}")
    for p in body:
        if "typo" in p and not re.search(r"(?<![\d.])0(?:\.0+)? points|zero", p):
            bad("'typo' joke on a non-zero score")
    body_text = " ".join(body)
    if book is not None:
        for rid in a["teams"]:
            if book.name(rid) not in body_text and book.nickname(rid) not in body_text:
                bad(f"team {book.name(rid)!r} in teams but not mentioned in the body")
        owner_text = book.scrub_players(text)
        for th in themes:
            owner_text = re.sub(re.escape(th), "", owner_text, flags=re.I)
        for chunk in [rv["backstory"].strip() for rv in book.rivalries if rv.get("backstory")] + \
                [str(c).strip() for t in book.teams.values() for c in [(t.get("profile") or {}).get("catchphrase")] + list((t.get("profile") or {}).get("traits") or []) if c]:
            if chunk:   # owner-written text keeps the owner's own wording, nicknames included
                owner_text = owner_text.replace(chunk, "")
        for rid, t in book.teams.items():
            nick = str(t.get("nickname") or "").strip()
            if nick and nick != book.name(rid):
                uses = len(re.findall(rf"\b{re.escape(nick)}\b", owner_text))
                if uses > 1:
                    bad(f"nickname {nick!r} used more than once")
                asides = len(re.findall(rf"{re.escape(book.name(rid))}, \u201c{re.escape(nick)}\u201d to the group chat,", owner_text))
                if uses and asides != uses:
                    bad(f"nickname {nick!r} used as a bare name (only '<name>, \u201c{nick}\u201d to the group chat,' is allowed)")
    facts = a.get("facts") or {}
    kind = a["type"]
    _lint_slant(a, facts, bad)
    if kind == "feud" and book is not None:
        _lint_feud(a, book, bad)
    if kind == "recap":
        _lint_recap(a, facts, bad, {book.name(r): (book.nickname(r),) for r in book.teams} if book is not None else None)
    if kind == "column":
        for nm in facts.get("teams") or []:
            if nm not in body_text and not (book is not None and any(book.nickname(r) in body_text for r in book.teams if book.name(r) == nm)):
                bad(f"column does not mention {nm!r}")
    if kind == "analytics":
        for k in ("luck_index", "lineup_efficiency", "bench_points_left", "weekly_rank_consistency", "trade_early_returns", "biggest_bench_blunder"):
            blob = facts.get(k)
            if blob:
                for v in blob.values():
                    if isinstance(v, str) and book is not None and v in {book.name(r) for r in book.teams} and v not in body_text:
                        bad(f"analytics fact {k} names {v!r} but the body does not")
    if kind == "preview":
        hf = facts.get("headline_favorite")
        if hf is not None and hf != facts.get("favorite"):
            bad("preview headline favorite differs from facts.favorite")
        if hf is not None and hf not in head:
            bad("preview headline does not name its favorite")
    return probs


def _lint_recap(a: dict, facts: dict, bad, nicks: dict | None = None) -> None:
    nicks = nicks or {}
    games = facts.get("games") or []
    story = facts.get("story") or {}
    sg = games[story["game"]] if games and story.get("game") is not None and story["game"] < len(games) else None
    cls = (sg.get("mclass") if sg and sg.get("result") != "tie" else "tie") if sg else None
    texts = [("headline", a["headline"], cls)] + [(f"para {i}", p, m.get("mclass") if m else None)
                                                  for i, (p, m) in enumerate(_paras(a))]
    for where, t, c in texts:
        if c is None and where != "headline":
            continue
        if c != "blowout" and BLOW_RE.search(t):
            bad(f"blowout wording in {where} but game class is {c}: {BLOW_RE.search(t).group(0)!r}")
        if c != "close" and CLOSE_RE.search(t):
            bad(f"close-game wording in {where} but game class is {c}: {CLOSE_RE.search(t).group(0)!r}")
    if facts.get("playoff") and PLAYOFF_BAD.search(" ".join(a["body"])):
        bad(f"regular-season framing in a playoff week: {PLAYOFF_BAD.search(' '.join(a['body'])).group(0)!r}")
    for i, (p, m) in enumerate(_paras(a)):
        if m and m.get("game") is not None and m.get("teams"):
            for nm in m["teams"]:
                if nm not in p and not any(nick and nick in p for nick in nicks.get(nm, ())):
                    bad(f"game paragraph {i} does not mention {nm!r}")
            g = games[m["game"]] if m["game"] < len(games) else None
            if g and g.get("winner") and (g["winner"] not in m["teams"] or g["loser"] not in m["teams"]):
                bad(f"paragraph {i} teams do not match the game")


def _lint_feud(a: dict, book, bad) -> None:
    """A feud is about its two parties. A third team may appear only in a sentence that says 'over <third>'
    and never in the headline, the dek or the first paragraph."""
    from .util import split_sentences
    pair = list(a["teams"][:2]) if len(a["teams"]) >= 2 else []
    names = {rid: book.name(rid) for rid in book.teams}
    parties = {names[r] for r in a["teams"][:2]}
    facts_teams = set((a.get("facts") or {}).get("teams") or [])
    parties |= facts_teams
    others = {rid: nm for rid, nm in names.items() if nm not in parties}

    def mentioned(text: str) -> list[str]:
        t = book.scrub_players(text)
        return [nm for nm in others.values() if re.search(rf"\b{re.escape(nm)}\b", t)]
    for where, text in (("headline", a["headline"]), ("dek", a["dek"]), ("lede", a["body"][0] if a["body"] else "")):
        hit = mentioned(text)
        if hit:
            bad(f"feud {where} names a third team: {hit}")
    for p in a["body"]:
        for sent in split_sentences(p):
            for nm in mentioned(sent):
                if f"over {nm}" not in sent:
                    bad(f"feud sentence names third team {nm!r} without 'over {nm}': {sent[:80]!r}")


_NUM = re.compile(r"\d+(?:\.\d+)?")


def _lint_slant(a: dict, facts: dict, bad) -> None:
    """Narratives only change framing: the slanted lines carry no number that did not come from a fact, a hater never
    writes a warm line (nor a homer a sour one), and the thesis is stated at most once."""
    beats = facts.get("beats") or []
    sl = facts.get("slant")
    if not sl:
        if any("~" in b for b in beats):
            bad("slanted beats without a facts.slant summary")
        return
    if not facts.get("paras"):   # a desk article replaces the template text; its hand-written body is not slanted by template
        return
    neg = sum(1 for b in beats if b.endswith("~neg"))
    pos = sum(1 for b in beats if b.endswith("~pos"))
    if (sl.get("neg"), sl.get("pos")) != (neg, pos):
        bad("slant summary disagrees with the beats")
    stances = {n.get("stance") for n in sl.get("narratives") or []}
    if stances <= {"hater", "skeptic"} and pos:
        bad("a hater/skeptic article contains a warm (pos) variant")
    if stances <= {"homer"} and neg:
        bad("a homer article contains a sour (neg) variant")
    if sum(1 for b in beats if b.startswith("x.theme~")) > 1:
        bad("the narrative theme is stated more than once")
    for ln in sl.get("lines") or []:
        extra = set(_NUM.findall(ln.get("text") or "")) - set(ln.get("nums") or [])
        if extra:
            bad(f"slanted line states numbers that are not facts: {sorted(extra)} in {ln.get('slot')}")
