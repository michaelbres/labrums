"""Writer: renders one article in one reporter's voice from facts. All randomness is seeded."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from . import families, quotes
from .util import placeholders
import re

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
             "move": "moves", "jump": "jumps", "sit": "sits", "stand": "stands", "don't": "doesn't"}
_AGREE_RE = re.compile("(" + "|".join(sorted(_SINGULAR, key=len, reverse=True)) + r")\b")


def agree(text: str, facts: dict) -> str:
    """Lists of names may hold one name: 'Nick are out' becomes 'Nick is out'."""
    for key in ("names", "in_names", "out_names"):
        v = str(facts.get(key) or "")
        if not v or " and " in v or "," in v:
            continue
        pat = re.compile(re.escape(v) + r"(,? who| now| still| just)? (" + "|".join(sorted(_SINGULAR, key=len, reverse=True)) + r")\b")
        text = pat.sub(lambda m: f"{v}{m.group(1) or ''} {_SINGULAR[m.group(2)]}", text)
    return text


class Writer:
    def __init__(self, book, voice, rng: random.Random):
        self.book, self.voice, self.rng = book, voice, rng
        self.fam = families.get(voice.family)
        self.used: dict[str, set[int]] = defaultdict(set)
        self.used_q: set = set()
        self.used_lex: set = set()
        self.nick_used = False
        self.trait_used = False
        self.catch_used = False
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

    def line(self, slot: str, facts: dict[str, Any], *, repeat: bool = False, prefer: tuple = ()) -> str | None:
        """One rendered sentence (or short run of sentences) for `slot`, or None if no template fits the facts."""
        tpls = self.fam.T[slot]
        cand = [i for i, t in enumerate(tpls) if all(self._has(facts, k) for k in placeholders(t))]
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
            keys = self.book.sentence_keys(text)
            score = sum(10 for k in keys if self.book.seen[k]) + max((self.book.seen[k] for k in keys), default=0)
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
                if self.nick_used or not facts.get(k) or facts[k] == plain:
                    vals[k] = plain
                else:
                    vals[k] = str(facts[k]); self.nick_used = True
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
              sig_ok: bool = True) -> str | None:
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
        text = self.line("x.attr", {"n": name, "qc": qc, "qp": qp}, repeat=True)
        self.quote_log.append({"situation": situation, "speaker": name, "commissioner": commish})
        catch = (self.book.profile(rid).get("catchphrase") or "").strip()
        if sig_ok and catch and not self.catch_used and self.rng.random() < 0.5:
            self.catch_used = True
            catch = catch.replace("{me}", name).replace("{them}", str(facts.get("opp") or "everyone"))
            sig = self.line("x.sig", {"n": name, "catch": catch}, repeat=True)
            if sig:
                text = f"{text} {sig}"
        return text

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
        """Voice dressing: signature opener on the first paragraph, one tic mid-article, signature closer last."""
        v = self.voice
        paras = [[t, dict(m)] for t, m in self.paras]
        if not paras:
            return [], []
        if v.openers:
            paras[0][0] = f"{self.rng.choice(v.openers)} {paras[0][0]}"
        mids = [p for p in paras[1:-1] if not p[0].startswith("“")] or [p for p in paras[:-1] if len(paras) > 1]
        if v.tics and mids:
            p = self.rng.choice(mids)
            p[0] = f"{p[0]} {self.rng.choice(v.tics)}"
        out = [p[0] for p in paras]
        metas = [p[1] for p in paras]
        if v.closers:
            out.append(self.rng.choice(v.closers))
            metas.append({})
        return out, metas
