"""Writer: renders one article in one reporter's voice from facts. All randomness is seeded."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from . import families, quotes
from .util import placeholders, polish, split_sentences
import re

CATCH_KINDS = frozenset({"recap", "preview", "trade", "shotgun", "feud"})   # types where an owner can be a main party
CATCH_SHARE = 0.18   # build-wide: at most this share of articles may carry any catchphrase (the test bar is 20%)
# Phrases that may appear at most once in a whole build (family tics): matched case-insensitively on rendered text.
ONCE_PHRASES = ("n = 1",)

_PH = re.compile(r"\{(\w+)\}")


def _render(tpl: str, vals: dict) -> str:
    """{key} replacement; a lexicon word that opens a sentence gets its first letter capitalized."""
    out, last = [], 0
    for m in _PH.finditer(tpl):
        out.append(tpl[last:m.start()])
        v = vals[m.group(1)]
        before = "".join(out)
        if m.group(1) in ("verb", "noun", "tier", "wl") and (not before.strip() or re.search(r"[.!?]\s*$", before)):
            v = v[:1].upper() + v[1:]
        out.append(v)
        last = m.end()
    out.append(tpl[last:])
    res = "".join(out)
    return res[:1].upper() + res[1:]


_SINGULAR = {"have": "has", "are": "is", "were": "was", "climb": "climbs", "fall": "falls", "hold": "holds",
             "advance": "advances", "occupy": "occupies", "depart": "departs", "slip": "slips", "do": "does",
             "move": "moves", "jump": "jumps", "sit": "sits", "stand": "stands", "don't": "doesn't",
             "lead": "leads", "take": "takes", "break": "breaks", "win": "wins", "lose": "loses", "keep": "keeps",
             "owe": "owes", "make": "makes", "get": "gets", "need": "needs"}
_AGREE_RE = re.compile("(" + "|".join(sorted(_SINGULAR, key=len, reverse=True)) + r")\b")


_COUNT_SING = {"were": "was", "are liable": "is liable", "are": "is", "have": "has", "owe": "owes", "observe": "observes",
               "account": "accounts", "go": "goes", "come": "comes", "change": "changes", "drift": "drifts", "find": "finds"}
_COUNT_RE = re.compile(r"(?<![\d.,-])\b1 (?:owner|player|shotgun|pick|add|game|trade|move|week|point) (are liable|were|are|have|owe|observe|"
                       r"account|go|come|change|drift|find)\b")
_COMBINED_ONE = re.compile(r"\ba combined (1 shotgun)\b")
_COMBINED_OWNER = re.compile(r"(\b1 owner [^.!?]*?)\ba combined ")
# Weather metaphors are for recaps, previews and standings; trades, waivers and the Beer Report read plain.
PLAIN_KINDS = {"weather": frozenset({"trade", "waiver", "shotgun"})}
WEATHER_RX = re.compile(r"radar|\bsky\b|skies|satellite|\bwind|pressure|forecast|storm|\bfront\b|\brain|weather|conditions|outlook|gust|cloud|\bsun", re.I)
BUSY_RX = re.compile(r"busy|likes a deal|handshake|sit still|restless|appetite|plenty of movement|on the move|making deals|"
                     r"portfolio|serial|high-turnover|phone bills|wonder about|can't sit|counting")


def agree(text: str, facts: dict) -> str:
    """Lists of names may hold one name: 'Nick are out' becomes 'Nick is out'; '1 owner owe' becomes '1 owner owes'."""
    text = _COUNT_RE.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)] + _COUNT_SING[m.group(1)], text)
    text = _COMBINED_ONE.sub(r"\1", text)
    text = _COMBINED_OWNER.sub(r"\1", text)
    for key in ("names", "in_names", "out_names"):
        v = str(facts.get(key) or "")
        if not v or " and " in v or "," in v:
            continue
        pat = re.compile(re.escape(v) + r"(,? who| now| still| just)? (" + "|".join(sorted(_SINGULAR, key=len, reverse=True)) + r")\b")
        text = pat.sub(lambda m: f"{v}{m.group(1) or ''} {_SINGULAR[m.group(2)]}", text)
    return text


def _nick_slot_ok(tpl: str, key: str) -> bool:
    """A nickname aside ('Colin, "Colon Burns" to the group chat,') fits only where a subject opens a clause:
    at the start of the template or after a comma/colon/period, and directly before a lowercase verb."""
    at = tpl.find("{" + key + "}")
    if at < 0:
        return False
    before, after = tpl[:at], tpl[at + len(key) + 2:]
    if before.strip() and not re.search(r"[.!?:;,\u2014-]\s*$", before):
        return False
    return bool(re.match(r" [a-z{]", after))


class Writer:
    def __init__(self, book, voice, rng: random.Random, kind: str | None = None, week: int | None = None):
        self.book, self.voice, self.rng = book, voice, rng
        self.kind, self.week = kind, week
        self.fam = families.get(voice.family)
        self.used: dict[str, set[int]] = defaultdict(set)
        self.used_q: set = set()
        self.used_lex: set = set()
        self.nick_used = False
        self.trait_used = False
        self.catch_used = False
        self.art_keys: set[str] = set()   # sentence keys already written in THIS article (no sentence twice)
        self.paras: list[tuple[str, dict]] = []
        self.beats: list[str] = []
        self.quote_log: list[dict] = []

    # ---- template choice ---------------------------------------------------
    def _perm(self, slot: str, n: int) -> list[int]:
        r = random.Random(f"{self.voice.id}:{slot}")
        idx = list(range(n))
        r.shuffle(idx)
        return idx

    def _has(self, facts: dict, k: str) -> bool:
        if k == "verb" or k == "noun":
            return bool(facts.get("mclass")) and facts["mclass"] in self.fam.lex[k]
        if k == "tier":
            return facts.get("tier") in self.fam.lex["tier"]
        v = facts.get(k)
        return v is not None and v != ""

    def _lex(self, kind: str, tag: str) -> str:
        words = self.fam.lex[kind][tag]
        fresh = [w for w in words if (kind, w) not in self.used_lex] or words
        w = self.rng.choice(fresh)
        self.used_lex.add((kind, w))
        return w

    def line(self, slot: str, facts: dict[str, Any], *, repeat: bool = False, prefer: tuple = (), need: str | None = None,
             avoid: "re.Pattern | None" = None) -> str | None:
        """One rendered sentence (or short run of sentences) for `slot`, or None if no template fits the facts.
        `need`: only templates containing this literal text (e.g. "over {l}") are eligible; `avoid`: templates
        matching this pattern are not."""
        tpls = self.fam.T[slot]
        cand = [i for i, t in enumerate(tpls) if all(self._has(facts, k) for k in placeholders(t)) and (need is None or need in t)
                and (avoid is None or not avoid.search(t))]
        if not cand:
            return None
        fresh = [i for i in cand if i not in self.used[slot]]
        if not fresh:
            if not repeat:
                return None
            fresh = cand
        if prefer:
            pref = [i for i in fresh if any("{" + k + "}" in tpls[i] for k in prefer)]
            fresh = pref or fresh
        order = self._perm(slot, len(tpls))
        fresh.sort(key=order.index)
        top = fresh[: max(2, (len(fresh) + 1) // 2)]
        start = fresh.index(self.rng.choice(top))
        # Try the chosen template first, then the others in rotation, preferring one whose sentences have not
        # been written yet in this build (names and numbers stripped).
        base_state = (self.rng.getstate(), set(self.used_lex), self.nick_used)
        best = None
        for step in range(len(fresh)):
            i = fresh[(start + step) % len(fresh)]
            self.rng.setstate(base_state[0]); self.used_lex = set(base_state[1]); self.nick_used = base_state[2]
            text = self._fill(tpls[i], facts)
            keys = self.book.sentence_keys(text, 2)   # short fragments ('Recent results!') are language too
            score = sum(10 for k in keys if self.book.seen[k]) + max((self.book.seen[k] for k in keys), default=0)
            low = text.lower()
            if any(p in low and p in self.book.once_used for p in ONCE_PHRASES):
                score += 1000   # a family tic already used in this build: only if nothing else fits
            if any(k in self.art_keys for k in keys):
                score += 500    # this article already says that, word for word
            snap = (self.rng.getstate(), set(self.used_lex), self.nick_used)
            if best is None or score < best[0]:
                best = (score, i, text, keys, snap)
            if score == 0:
                break
        score, i, text, keys, snap = best
        self.rng.setstate(snap[0]); self.used_lex = snap[1]; self.nick_used = snap[2]
        self.used[slot].add(i)
        for k in keys:
            self.book.seen[k] += 1
        self.art_keys.update(keys)
        low = text.lower()
        self.book.once_used.update(p for p in ONCE_PHRASES if p in low)
        self.beats.append(slot)
        return text

    def _fill(self, tpl: str, facts: dict[str, Any]) -> str:
        vals: dict[str, str] = {}
        for k in dict.fromkeys(_PH.findall(tpl)):   # template order, never set order: seeds must give the same text everywhere
            if k in ("verb", "noun"):
                vals[k] = self._lex(k, facts["mclass"])
            elif k == "tier":
                vals[k] = self._lex("tier", facts["tier"])
            elif k.endswith("_nick") and k[:-5] in facts:
                plain = str(facts[k[:-5]])
                if self.nick_used or not facts.get(k) or facts[k] == plain or not _nick_slot_ok(tpl, k):
                    vals[k] = plain
                else:
                    # once per article, and only as an appositive aside, never as a bare name
                    vals[k] = f"{plain}, \u201c{facts[k]}\u201d to the group chat,"; self.nick_used = True
            else:
                vals[k] = str(facts[k])
        return agree(_render(tpl, vals), facts)

    def head(self, slot: str, facts: dict[str, Any]) -> str:
        h = self.line(slot, facts, repeat=True)
        if h is None:
            raise ValueError(f"no usable {slot} template for {self.voice.id} with {sorted(facts)}")
        return h

    # ---- quotes ----------------------------------------------------------
    def quote(self, rid: int, situation: str, facts: dict[str, Any], *, multi: bool = False,
              sig_ok: bool = False) -> str | None:
        """'“…,” said Name.' for a speaker in a situation; None if no quote fits the facts."""
        commish = self.book.commissioner is not None and rid == self.book.commissioner
        q = quotes.pick(situation, facts, self.rng, self.used_q, multi=multi, commish=commish, counts=self.book.quote_use,
                        scorer=lambda t: max((self.book.seen[k] for k in self.book.sentence_keys(t)), default=0))
        if not q:
            return None
        q = q.strip()
        q = q[:1].upper() + q[1:]
        if q.endswith(".") and not q.endswith("..."):
            q = q[:-1]
        qc = q if q[-1] in "!?" else q + ","
        qp = q if q[-1] in "!?" else q + "."
        name = self.book.name(rid)
        plain = self._plain()
        text = self.line("x.attr", {"n": name, "qc": qc, "qp": qp}, repeat=True, avoid=WEATHER_RX if plain else None)
        self.quote_log.append({"situation": situation, "speaker": name, "commissioner": commish})
        catch = (self.book.profile(rid).get("catchphrase") or "").strip()
        if sig_ok and catch and self._catch_allowed(rid) and self.rng.random() < 0.5:
            catch = catch.replace("{me}", name).replace("{them}", str(facts.get("opp") or "everyone"))
            sig = self.line("x.sig", {"n": name, "catch": catch}, repeat=True, avoid=WEATHER_RX if plain else None)
            if sig:
                self.catch_used = True
                self.book.catch_week.add((rid, self.week))
                text = f"{text} {sig}"
        return text

    def _plain(self) -> bool:
        """True when this family must keep a plain register for this article type (weather: trade/waiver/shotgun)."""
        return self.kind in PLAIN_KINDS.get(self.fam.id, ())

    def _catch_allowed(self, rid: int) -> bool:
        """One catchphrase per article, one per owner per week across the build, only in types where the owner can
        be a main party, and never beyond CATCH_SHARE of the articles built so far (this one included)."""
        b = self.book
        if self.catch_used or self.kind not in CATCH_KINDS or (rid, self.week) in b.catch_week:
            return False
        return (b.n_catch + 1) <= CATCH_SHARE * (b.n_articles + 1)

    def aside(self, rid: int, event: str, wl: str, wk: str) -> str | None:
        traits = self.book.profile(rid).get("traits") or []
        if self.trait_used or not traits:
            return None
        s = self.line("g.aside", {"n": self.book.name(rid), "trait": self.rng.choice(traits).strip().rstrip("."),
                                  "event": event, "wl": wl, "wk": wk})
        if s:
            self.trait_used = True
        return s

    # ---- assembly --------------------------------------------------------
    def add(self, sentences: list[str | None], meta: dict | None = None) -> None:
        text = " ".join(s for s in sentences if s)
        if text:
            self.paras.append((text, meta or {}))

    def finish(self) -> tuple[list[str], list[dict]]:
        """Voice dressing: signature opener on the first paragraph, one tic mid-article, signature closer last.
        A piece of dressing that repeats a sentence the article already holds is dropped."""
        v = self.voice
        paras = [[t, dict(m)] for t, m in self.paras]
        if not paras:
            return [], []
        protect = self.book.protected_rx()
        if self._plain():   # no weather-flavored opener, tic or sign-off on a plain-register piece
            return [polish(p[0], protect) for p in paras], [p[1] for p in paras]

        def sents(text: str) -> set[str]:
            return {re.sub(r"\W+", " ", x).strip().lower() for x in split_sentences(text) if x.strip()}
        have: set[str] = set()
        for p in paras:
            have |= sents(p[0])

        def fresh(dressing: str) -> bool:
            return not (sents(dressing) & have)
        if v.openers:
            op = self.rng.choice(v.openers)
            if fresh(op):
                paras[0][0] = f"{op} {paras[0][0]}"
                have |= sents(op)
        mids = [p for p in paras[1:-1] if not p[0].startswith("\u201c")] or [p for p in paras[:-1] if len(paras) > 1]
        if v.tics and mids:
            p = self.rng.choice(mids)
            tic = self.rng.choice(v.tics)
            if tic not in self.book.once_used and fresh(tic):   # a tic is a joke: it runs once per build, then the reporter moves on
                self.book.once_used.add(tic)
                p[0] = f"{p[0]} {tic}"
                have |= sents(tic)
        out = [polish(p[0], protect) for p in paras]
        metas = [p[1] for p in paras]
        if v.closers:
            cl = self.rng.choice(v.closers)
            if fresh(cl):
                out.append(polish(cl, protect))
                metas.append({})
        return out, metas
