"""Writer: renders one article in one reporter's voice from facts. All randomness is seeded."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from . import families, quotes
from .util import fill, placeholders


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

    def line(self, slot: str, facts: dict[str, Any], *, repeat: bool = False) -> str | None:
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
        order = self._perm(slot, len(tpls))
        fresh.sort(key=order.index)
        top = fresh[: max(2, (len(fresh) + 1) // 2)]
        i = self.rng.choice(top)
        self.used[slot].add(i)
        vals: dict[str, str] = {}
        for k in placeholders(tpls[i]):
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
        self.beats.append(slot)
        return fill(tpls[i], vals)

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
        q = quotes.pick(situation, facts, self.rng, self.used_q, multi=multi, commish=commish)
        if not q:
            return None
        q = q.strip()
        if q.endswith(".") and not q.endswith("..."):
            q = q[:-1]
        qc = q if q[-1] in "!?" else q + ","
        qp = q if q[-1] in "!?" else q + "."
        name = self.book.name(rid)
        text = self.line("x.attr", {"n": name, "qc": qc, "qp": qp}, repeat=True)
        catch = (self.book.profile(rid).get("catchphrase") or "").strip()
        if sig_ok and catch and not self.catch_used and self.rng.random() < 0.5:
            self.catch_used = True
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
