"""The Labrums newsroom: 50 reporters (renamable in config.yaml), 14 style families, facts-first articles.

Public API (re-exported by app.articles): Newsroom, generate(ctx, st, po, shotgun_items).
Every article dict carries `reporter` ({id, name, outlet, bio, family, known_for}) and `facts` (a JSON-friendly
packet of everything the article states, plus `beats` and `paras`) so an LLM writer can re-tell
the same story from the same facts in the same reporter's voice.
"""
from __future__ import annotations

import logging
import os
import random
from collections import Counter, defaultdict

from . import calendar, desk, lint, narratives
from .beats_extra import Beats3
from .voices import BY_ID, VOICES, Voice

log = logging.getLogger("labrums.newsroom")

# Casting a narrative reporter: (chance, slack). When he is free and the article involves his target he is chosen
# outright with this chance, as long as his family has not been used more than `slack` times beyond the least-used
# family for that beat (so a recap or preview, where an owner is always involved, keeps the family rotation intact
# and only decides WHICH voice of the family writes it). Seeded, never random.
FAVOR = {"recap": (0.8, 0), "preview": (0.8, 0)}
FAVOR_DEFAULT = (0.5, 1)

TYPE_ORDER = {"preview": 0, "rivalry": 0, "recap": 1, "standings": 2, "shotgun": 3, "trade": 4, "offseason": 4,
              "waiver": 5, "feud": 6, "column": 7, "analytics": 8}


class Assigner:
    """Deterministic reporter assignment: rotate families per beat, spread load across voices, and keep a
    voice from writing twice in the same week when anyone else is available."""

    def __init__(self, season: str, voices: list[Voice]):
        self.season, self.voices = season, voices
        self.total: Counter = Counter()
        self.fam: Counter = Counter()
        self.beat_use: Counter = Counter()
        self.week_used: dict[int, set] = defaultdict(set)
        self._rank: dict[tuple, float] = {}
        self._favored = False   # the last pick() was a narrative casting (it does not count against the voice's turn)

    def rank(self, beat: str, vid: str) -> float:
        k = (beat, vid)
        if k not in self._rank:
            self._rank[k] = random.Random(f"{self.season}:{beat}:{vid}").random()
        return self._rank[k]

    def pick(self, beat: str, week: int, favor: dict[str, tuple[float, int]] | None = None) -> Voice:
        """`favor`: voice id -> (chance, slack) of casting that voice outright (a narrative reporter whose target is in the story)."""
        elig = [v for v in self.voices if beat in v.beats]
        free = [v for v in elig if v.id not in self.week_used[week]] or elig
        self._favored = False
        if favor:
            low = min(self.fam[(beat, v.family)] for v in free)
            for v in free:
                p, slack = favor.get(v.id) or (0, 0)
                if p and self.fam[(beat, v.family)] <= low + slack and \
                        random.Random(f"{self.season}:favor:{beat}:{week}:{v.id}").random() < p:
                    self._favored = True
                    return v
        return min(free, key=lambda v: (self.fam[(beat, v.family)], self.beat_use[(beat, v.id)], self.total[v.id], self.rank(beat, v.id)))

    def commit(self, beat: str, week: int, v: Voice) -> None:
        if not self._favored:   # a narrative casting is on top of the voice's normal turns, not instead of one
            self.total[v.id] += 1
            self.beat_use[(beat, v.id)] += 1
        self._favored = False
        self.fam[(beat, v.family)] += 1
        self.week_used[week].add(v.id)


class Newsroom(Beats3):
    def __init__(self, ctx: dict, st: dict, po: dict, shotgun_items: list[dict], *, debug: bool | None = None):
        super().__init__(ctx, st, po, shotgun_items)
        self.debug = (os.environ.get("LABRUMS_NEWSROOM_DEBUG", "") in ("1", "true", "yes")) if debug is None else debug
        # the league id is part of the casting seed: two leagues that share a season label do not share a cast
        self.voices, self.narrs = narratives.staff(ctx.get("config") or {}, self.teams)
        self.assign = Assigner(f"lg:{(ctx.get('league') or {}).get('league_id', '')}:{self.season}", self.voices)
        self._rv_voice: dict[str, Voice] = {}
        self.desk_report: list[dict] = []

    def _try(self, label: str, fn):
        """One bad article must never take the site down: log it and move on (debug mode re-raises)."""
        try:
            return fn()
        except Exception:
            if self.debug:
                raise
            log.exception("newsroom: could not write %s", label)
            return None

    def _favor(self, beat: str, rids=(), players=()) -> dict[str, tuple[float, int]]:
        """Casting boost for reporters with a narrative about one of `rids` (owners) or `players` (hype)."""
        p = FAVOR.get(beat, FAVOR_DEFAULT)
        low = {str(x).casefold() for x in players}
        return {n.voice_id: p for n in self.narrs
                if (n.kind == "owner" and n.rid in rids) or (n.kind == "player" and str(n.player).casefold() in low)}

    def _recap_players(self, week: int) -> list[str]:
        """Names a recap would feature: each winner's top starter and each loser's worst one."""
        out = []
        for g in self.games_by_week.get(week, []):
            if g.get("winner") is None or g["a"] not in self.teams or g["b"] not in self.teams:
                continue
            w_, l_ = g["winner"], g["b"] if g["winner"] == g["a"] else g["a"]
            for pl in (self.best_starter(week, w_), self.worst_starter(week, l_)):
                if pl:
                    out.append(pl["name"])
        return out

    def _build(self, beat: str, week: int, builder, favor: dict[str, tuple[float, int]] | None = None):
        v = self.assign.pick(beat, week, favor) if favor else self.assign.pick(beat, week)
        art = self._try(f"{beat} week {week}", lambda: builder(v))
        if art:
            self.assign.commit(beat, week, v)
        return art

    def rivalry_voice(self, rv: dict) -> Voice:
        """A configured rivalry keeps the same reporter all season."""
        if rv["name"] not in self._rv_voice:
            v = self.assign.pick("rivalry", 0)
            self.assign.commit("rivalry", 0, v)
            self._rv_voice[rv["name"]] = v
        return self._rv_voice[rv["name"]]

    def generate(self, use_desk: bool = True) -> list[dict]:
        out: list[dict] = []
        last = self.ctx["last_completed"]
        used_pairs: set = set()
        feud_by_week: dict[int, frozenset | None] = {}
        for week in sorted(w for w in self.games_by_week if w <= last):
            games = [g for g in self.games_by_week.get(week, []) if g["a"] in self.teams and g["b"] in self.teams]
            rids = {x for g in games for x in (g["a"], g["b"])}
            fv = self._favor("recap", rids, self._recap_players(week) if self.narrs else ()) if self.narrs else None
            art = self._build("recap", week, lambda v, wk=week: self.roundup(wk, v), fv)
            if art:
                out.append(art)
            if self.sg_week(week):
                per: Counter = Counter(s["roster_id"] for s in self.sg_week(week))
                top = min(per, key=lambda x: (-per[x], self.name(x)))
                art = self._build("shotgun", week, lambda v, wk=week: self.beer_report(wk, v),
                                  self._favor("shotgun", (top,)) if self.narrs else None)
                if art:
                    out.append(art)
            for tx in self.live_txs(week):
                if tx.get("type") == "trade" and self.trade_info(tx, week):
                    ti = self.trade_info(tx, week)
                    names = [self.label(p)["name"] for x in (ti["a"], ti["b"]) for p in ti["got"][x]["pids"]]
                    art = self._build("trade", week, lambda v, t=tx, wk=week: self.trade(t, wk, v),
                                      self._favor("trade", (ti["a"], ti["b"]), names) if self.narrs else None)
                    if art:
                        out.append(art)
            wmoves = self.waiver_moves(week)
            if wmoves:
                art = self._build("waiver", week, lambda v, wk=week: self.waivers(wk, v),
                                  self._favor("waiver", (wmoves[0]["rid"],), [m["name"] for m in wmoves[:5]]) if self.narrs else None)
                if art:
                    out.append(art)
            pair = self.feud_pair(week, used_pairs, self.rng("feudpair", week))
            feud_by_week[week] = frozenset(pair[:2]) if pair else None
            if pair:
                a, b, rv = pair
                if rv:
                    v = self.rivalry_voice(rv)
                    art = self._try(f"feud week {week}", lambda: self.feud(week, a, b, v))
                    if art:
                        self.assign.commit("feud", week, v)
                else:
                    art = self._build("feud", week, lambda v, wk=week, x=a, y=b: self.feud(wk, x, y, v),
                                      self._favor("feud", (a, b)) if self.narrs else None)
                if art:
                    used_pairs.add(frozenset((a, b)))
                    out.append(art)
        off = [t for w in sorted(self.ctx["transactions"]) for t in self.ctx["transactions"][w]
               if t.get("type") != "commissioner" and t.get("status") == "complete"
               and self._is_off(t)]
        art = self._build("offseason", 1, lambda v: self.offseason(off, v)) if off else None
        if art:
            out.append(art)
        if last >= 1:
            art = self._build("standings", last, lambda v: self.standings_watch(last, v))
            if art:
                out.append(art)
        nxt = self.po.get("next_week")
        if nxt and nxt in self.st["schedule"]:
            prids = {x for g in self.st["schedule"][nxt] for x in (g["a"], g["b"])}
            art = self._build("preview", nxt, lambda v: self.preview(nxt, v), self._favor("preview", prids) if self.narrs else None)
            if art:
                out.append(art)
            for g in self.st["schedule"][nxt]:
                rv = self.rivalry_between(g["a"], g["b"])
                if rv:
                    v = self.rivalry_voice(rv)
                    art = self._try(f"rivalry week {nxt}", lambda: self.rivalry_hype(nxt, g, v))
                    if art:
                        out.append(art)
        # Sunday column and Monday analytics: a second pass so the casting of every older article type is untouched.
        used_cols: set = set()
        for week in sorted(w for w in self.games_by_week if w <= last):
            cp = self.column_pair(week, feud_by_week.get(week), used_cols, self.rng("columnpair", week))
            if cp:
                ca, cb, crv, cnext = cp
                if crv:
                    v = self.rivalry_voice(crv)
                    art = self._try(f"column week {week}", lambda: self.column(week, ca, cb, crv, cnext, v))
                    if art:
                        self.assign.commit("column", week, v)
                else:
                    art = self._build("column", week, lambda v: self.column(week, ca, cb, crv, cnext, v),
                                      self._favor("column", (ca, cb)) if self.narrs else None)
                if art:
                    used_cols.add(frozenset((ca, cb)))
                    out.append(art)
            art = self._build("analytics", week, lambda v, wk=week: self.analytics(wk, v))
            if art:
                out.append(art)
        out.sort(key=lambda a: (-a["week"], TYPE_ORDER.get(a["type"], 9), a["id"]))
        self._finish(out, use_desk)
        return out

    def _finish(self, out: list[dict], use_desk: bool) -> None:
        """Stable keys, release dates, lint, then the editorial desk's overrides."""
        groups: dict[str, list[dict]] = defaultdict(list)
        for a in out:
            groups[a["key"]].append(a)
        for key, grp in groups.items():
            if len(grp) > 1:   # two trades between the same pair in one week: numbered by transaction id, not build order
                for i, a in enumerate(sorted(grp, key=lambda x: x.get("_txid", "")), 1):
                    if i > 1:
                        a["key"] = f"{key}#{i}"
        for a in out:
            a.pop("_txid", None)
        start = calendar.season_start(self.ctx)
        for a in out:
            a["publish_on"] = calendar.publish_on(a["type"], a["week"], start, tx_created_ms=a.pop("_created", None))
        problems = [p for a in out for p in lint.check(a, self)]
        if problems:
            if self.debug:
                raise AssertionError("newsroom lint:\n" + "\n".join(problems))
            for p in problems:
                log.warning("newsroom lint: %s", p)
        if use_desk:
            self.desk_report = desk.apply(out, self.season, self)

    def _is_off(self, t: dict) -> bool:
        from ..loader import is_offseason
        return is_offseason(t, self.ctx.get("season_start_ms"))

    @staticmethod
    def reporters() -> list[dict]:
        return [v.card() for v in VOICES]

    def masthead(self) -> list[dict]:
        """The reporter cards for THIS league's config (overrides and `known_for` resolved against its owners)."""
        return [v.card() for v in self.voices]


def generate(ctx: dict, st: dict, po: dict, shotgun_items: list[dict], *, debug: bool | None = None,
             use_desk: bool = True) -> list[dict]:
    return Newsroom(ctx, st, po, shotgun_items, debug=debug).generate(use_desk=use_desk)
