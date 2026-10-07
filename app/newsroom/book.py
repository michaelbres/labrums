"""Read-only access to everything the newsroom may state as fact: as-of-week league state, lineups,
transactions, shotguns, rivalries. Nothing here writes prose."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .. import shotguns, stats
from . import calendar
from ..loader import is_offseason
from ..sleeper import player_label
from .util import fmt, num_word, ordinal, pts, rule_ref, split_sentences


class Book:
    def __init__(self, ctx: dict, st: dict, po: dict, shotgun_items: list[dict]):
        self.ctx, self.st, self.po = ctx, st, po
        self.shotguns = shotgun_items
        self.cfg = ctx["config"]
        self.teams = st["teams"]
        self.season = ctx["season"]
        self.positions = {p for p in ctx["roster_positions"] if p not in ("BN", "IR", "TAXI")}
        self.rivalries = self._resolve_rivalries()
        self.commissioner = shotguns.team_by_name(ctx, self.cfg.get("commissioner")) if self.cfg.get("commissioner") else None
        self._snaps: dict[int, dict] = {}
        self._bench: dict[tuple[int, int], tuple[float, dict | None]] = {}
        self.seen: Counter = Counter()        # normalized sentence -> times written in this build
        self.quote_use: Counter = Counter()   # (situation, variant) -> times quoted in this build
        self.once_used: set[str] = set()      # family tics / voice tics already spent in this build (each runs once)
        self.third_cited: set[tuple] = set()  # (week, a, b) of third-team blowouts already cited as feud background
        self.catch_week: set[tuple] = set()   # (roster_id, week) pairs that already got their catchphrase
        self.n_articles = 0                   # finished articles so far (the catchphrase budget is a share of these)
        self.n_catch = 0                      # of which carry a catchphrase
        self._protect_rx: re.Pattern | None = None
        self._norm_rx: re.Pattern | None = None
        self._players_rx: re.Pattern | None = None
        self.games_by_week: dict[int, list[dict]] = {}
        for g in st["games"]:
            self.games_by_week.setdefault(g["week"], []).append(g)

    # ---- names -----------------------------------------------------------
    def name(self, rid: int) -> str:
        t = self.teams[rid]
        return str(t.get("name") or t["display_name"]).strip()

    def nickname(self, rid: int) -> str:
        t = self.teams[rid]
        return str(t.get("nickname") or "").strip() or self.name(rid)

    def rule_ref(self, label: str, quote: str = "\u201c\u201d") -> str:
        """'the “scored less than Nick” rule' (first letter lowercased unless it is an owner's name)."""
        return rule_ref(label, {self.name(r) for r in self.teams}, quote)

    def tname(self, rid: int) -> str:
        return " ".join(str(self.teams[rid]["team_name"]).split())

    def profile(self, rid: int) -> dict:
        return self.teams[rid].get("profile") or {}

    # ---- league state ----------------------------------------------------
    def is_playoff(self, week: int) -> bool:
        return week >= self.ctx["playoff_start"]

    @property
    def final_reg_week(self) -> int:
        return min(self.ctx["last_completed"], self.ctx["playoff_start"] - 1)

    def snap(self, week: int) -> dict:
        week = max(0, min(week, self.final_reg_week))
        if week not in self._snaps:
            self._snaps[week] = stats.snapshot(self.st, self.ctx, week)
        return self._snaps[week]

    def season_over(self) -> bool:
        return self.ctx["league"].get("status") == "complete" or self.ctx["last_completed"] >= self.ctx["playoff_start"] + 2

    def regular_over(self) -> bool:
        return self.ctx["last_completed"] >= self.ctx["playoff_start"] - 1

    # ---- lineups ---------------------------------------------------------
    def week_row(self, week: int, rid: int) -> dict | None:
        for r in self.ctx["matchups"].get(week, []):
            if int(r["roster_id"]) == rid:
                return r
        return None

    def starters_with_points(self, week: int, rid: int) -> list[dict]:
        row = self.week_row(week, rid)
        if not row:
            return []
        out = []
        sp = row.get("starters_points") or []
        pp = row.get("players_points") or {}
        for i, pid in enumerate(row.get("starters") or []):
            if pid in (None, "", "0"):
                continue
            p = float(sp[i]) if i < len(sp) else float(pp.get(pid, 0) or 0)
            out.append({**player_label(self.ctx["players"], pid), "points": round(p, 2)})
        return out

    def best_starter(self, week: int, rid: int) -> dict | None:
        s = self.starters_with_points(week, rid)
        return max(s, key=lambda x: x["points"]) if s else None

    def worst_starter(self, week: int, rid: int) -> dict | None:
        s = self.starters_with_points(week, rid)
        return min(s, key=lambda x: x["points"]) if s else None

    def bench_left(self, week: int, rid: int) -> tuple[float, dict | None]:
        """(points the optimal lineup would have added, best scorer who sat) for that week."""
        if (week, rid) in self._bench:
            return self._bench[(week, rid)]
        res = self._bench_left(week, rid)
        self._bench[(week, rid)] = res
        return res

    def _bench_left(self, week: int, rid: int) -> tuple[float, dict | None]:
        row = self.week_row(week, rid)
        if not row:
            return 0.0, None
        left = round(stats.optimal_lineup_points(self.ctx, row) - float(row.get("points") or 0), 2)
        starters = {str(p) for p in (row.get("starters") or [])}
        pp = row.get("players_points") or {}
        bench = [(pid, float(v or 0)) for pid, v in pp.items() if str(pid) not in starters]
        best = None
        if bench:
            pid, v = max(bench, key=lambda kv: kv[1])
            best = {**player_label(self.ctx["players"], pid), "points": round(v, 2)}
        return max(left, 0.0), best

    # ---- trade / waiver timing ---------------------------------------------
    def counted_weeks(self, first: int, upto: int | None = None) -> list[int]:
        """Weeks first..upto (default: last completed) that count as played: never beyond the last completed week,
        never a week whose matchup rows carry no matchup_id (e.g. a week 18 that nobody plays)."""
        last = self.ctx["last_completed"] if upto is None else min(upto, self.ctx["last_completed"])
        out = []
        for w in sorted(self.ctx["matchups"]):
            if w < first or w > last:
                continue
            if any(r.get("matchup_id") is not None for r in self.ctx["matchups"][w]):
                out.append(w)
        return out

    def points_from(self, pid: str, first_week: int, rid: int, upto: int | None = None) -> float:
        """Points `pid` scored for `rid` over the counted weeks first_week..upto (see counted_weeks)."""
        total = 0.0
        for w in self.counted_weeks(first_week, upto):
            for r in self.ctx["matchups"][w]:
                if int(r["roster_id"]) == rid and r.get("matchup_id") is not None:
                    total += float((r.get("players_points") or {}).get(pid, 0) or 0)
        return round(total, 2)

    def after_games(self, tx: dict, week: int) -> bool:
        """True when the move was made on or after the Tuesday that follows week `week`'s games, so week `week`
        was already in the books. (Unknown season start or timestamp: treated as made during the week.)"""
        start = calendar.season_start(self.ctx)
        ms = tx.get("created")
        if start is None or not ms:
            return False
        return calendar._to_et(ms).date() >= calendar.week_tuesday(start, week)

    def first_week_after(self, tx: dict, week: int) -> int:
        """First week whose points count toward the move's early returns."""
        return week + 1 if self.after_games(tx, week) else week

    def records_week(self, tx: dict, week: int) -> int:
        """The snapshot week that shows the standings 'before the deal'."""
        return week if self.after_games(tx, week) else week - 1

    def label(self, pid: str) -> dict:
        return player_label(self.ctx["players"], pid)

    # ---- transactions ----------------------------------------------------
    def live_txs(self, week: int) -> list[dict]:
        return [t for t in self.ctx["transactions"].get(week, [])
                if t.get("type") != "commissioner" and t.get("status") == "complete"
                and not is_offseason(t, self.ctx.get("season_start_ms"))]

    def moves_before(self, rid: int, tx: dict, week: int) -> dict[str, int]:
        """In-season trades / waiver-or-FA claims that involve `rid` made up to and including `tx` (chronological:
        created <= tx.created, ties broken by transaction id)."""
        key = (int(tx.get("created") or 0), str(tx.get("transaction_id") or ""))
        out = {"trades": 0, "claims": 0}
        for w in sorted(self.ctx["transactions"]):
            if w > week:
                break
            for t in self.live_txs(w):
                if rid not in [int(x) for x in t.get("roster_ids") or []]:
                    continue
                if (int(t.get("created") or 0), str(t.get("transaction_id") or "")) > key:
                    continue
                if t["type"] == "trade":
                    out["trades"] += 1
                elif t["type"] in ("waiver", "free_agent"):
                    out["claims"] += 1
        return out

    # ---- shotguns --------------------------------------------------------
    def sg_week(self, week: int, rid: int | None = None) -> list[dict]:
        return [s for s in self.shotguns if s["week"] == week and (rid is None or s["roster_id"] == rid)]

    def sg_counts(self, upto: int) -> dict[int, int]:
        out: dict[int, int] = {}
        for s in self.shotguns:
            if s["week"] <= upto:
                out[s["roster_id"]] = out.get(s["roster_id"], 0) + 1
        return out

    # ---- rivalries -------------------------------------------------------
    def _resolve_rivalries(self) -> list[dict]:
        out = []
        for rv in self.cfg.get("rivalries") or []:
            owners = [shotguns.team_by_name({"teams": self.teams}, o) for o in rv.get("owners") or []]
            owners = [o for o in owners if o is not None]
            if len(owners) >= 2:
                out.append({"name": rv.get("name") or f"{self.name(owners[0])} vs. {self.name(owners[1])}",
                            "owners": owners[:2], "owner_names": [self.name(o) for o in owners[:2]],
                            "backstory": rv.get("backstory") or ""})
        return out

    def rivalry_between(self, a: int, b: int) -> dict | None:
        for rv in self.rivalries:
            if set(rv["owners"]) == {a, b}:
                return rv
        return None

    # ---- shared fact snippets -------------------------------------------
    def h2h_games(self, a: int, b: int, upto: int) -> list[dict]:
        return [g for g in self.st["games"] if g["week"] <= upto and {g["a"], g["b"]} == {a, b}]

    def tx_desc(self, tx: dict) -> dict[int, dict]:
        """What each roster received in a trade: players as 'Name (POS)', picks as 'a 2027 round 2 pick'
        (identical picks collapse: 'two 2026 round 2 picks'; `n_picks` keeps the true count)."""
        rids = [int(x) for x in tx.get("roster_ids") or []]
        got: dict[int, dict] = {r: {"players": [], "picks": [], "pids": [], "n_picks": 0} for r in rids}
        raw: dict[int, Counter] = {r: Counter() for r in rids}
        for pid, to in (tx.get("adds") or {}).items():
            if int(to) in got:
                lab = self.label(pid)
                got[int(to)]["players"].append(f"{lab['name']} ({lab['position']})")
                got[int(to)]["pids"].append(pid)
        for p in tx.get("draft_picks") or []:
            if p.get("owner_id") is not None and int(p["owner_id"]) in got:
                raw[int(p["owner_id"])][(p.get("season"), p.get("round"))] += 1
        for r, c in raw.items():
            for (season, rnd), n in c.items():
                got[r]["n_picks"] += n
                got[r]["picks"].append(f"a {season} round {rnd} pick" if n == 1 else f"{num_word(n)} {season} round {rnd} picks")
        return got

    # ---- repetition memory ----------------------------------------------
    def _names_rx(self) -> re.Pattern | None:
        if self._norm_rx is None:
            names: set[str] = set()
            for rid, t in self.teams.items():
                for k in ("name", "team_name", "nickname", "display_name"):
                    v = " ".join(str(t.get(k) or "").split())
                    if v:
                        names.add(v)
            players = self.ctx["players"]
            for rows in self.ctx["matchups"].values():
                for r in rows:
                    for pid in r.get("players") or []:
                        lab = players.get(str(pid)) or {}
                        n = " ".join(str(x) for x in (lab.get("first_name"), lab.get("last_name")) if x)
                        if n:
                            names.add(n)
            ordered = sorted(names, key=len, reverse=True)
            self._norm_rx = re.compile("|".join(re.escape(n) for n in ordered)) if ordered else re.compile(r"(?!x)x")
        return self._norm_rx

    def protected_rx(self) -> re.Pattern | None:
        """Names (teams, owners, nicknames, players) that must keep their own capitalization in the final pass."""
        if self._protect_rx is None:
            rx = self._names_rx()
            self._protect_rx = rx
        return self._protect_rx

    def scrub_players(self, text: str) -> str:
        """`text` without player names: a player named Pat is not an owner nicknamed Pat."""
        if self._players_rx is None:
            names: set[str] = set()
            players = self.ctx["players"]
            for rows in self.ctx["matchups"].values():
                for r in rows:
                    for pid in r.get("players") or []:
                        lab = players.get(str(pid)) or {}
                        n = " ".join(str(x) for x in (lab.get("first_name"), lab.get("last_name")) if x)
                        if n:
                            names.add(n)
            ordered = sorted(names, key=len, reverse=True)
            self._players_rx = re.compile("|".join(re.escape(n) for n in ordered)) if ordered else re.compile(r"(?!x)x")
        return self._players_rx.sub("", text)

    def sentence_keys(self, text: str, min_words: int = 4) -> list[str]:
        """Sentences of `text` with names and numbers stripped, lowercased: two sentences are 'the same
        language' when their keys match."""
        rx = self._names_rx()
        out = []
        for sent in split_sentences(rx.sub("X", text)):
            k = sent.replace("\u201c", "").replace("\u201d", "").replace('"', "")
            k = re.sub(r"-?\d[\d.,]*%?", "N", k)
            k = re.sub(r"\s+", " ", k.lower()).strip()
            if len(k.split()) >= min_words:   # fragments like "N points." are not 'language'
                out.append(k)
        return out
