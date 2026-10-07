"""Read-only access to everything the newsroom may state as fact: as-of-week league state, lineups,
transactions, shotguns, rivalries. Nothing here writes prose."""
from __future__ import annotations

from typing import Any

from .. import shotguns, stats
from ..loader import is_offseason
from ..sleeper import player_label
from .util import fmt, ordinal, pts


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

    def points_since(self, pid: str, after_week: int, rid: int) -> float:
        total = 0.0
        for w, rows in self.ctx["matchups"].items():
            if w <= after_week or w > self.ctx["last_completed"]:
                continue
            for r in rows:
                if int(r["roster_id"]) == rid:
                    total += float((r.get("players_points") or {}).get(pid, 0) or 0)
        return round(total, 2)

    def label(self, pid: str) -> dict:
        return player_label(self.ctx["players"], pid)

    # ---- transactions ----------------------------------------------------
    def live_txs(self, week: int) -> list[dict]:
        return [t for t in self.ctx["transactions"].get(week, [])
                if t.get("type") != "commissioner" and t.get("status") == "complete"
                and not is_offseason(t, self.ctx.get("season_start_ms"))]

    def moves_through(self, rid: int, week: int) -> dict[str, int]:
        """In-season trades / waiver-or-FA claims that involve `rid`, weeks <= week."""
        out = {"trades": 0, "claims": 0}
        for w in sorted(self.ctx["transactions"]):
            if w > week:
                break
            for t in self.live_txs(w):
                if rid not in [int(x) for x in t.get("roster_ids") or []]:
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
        """What each roster received in a trade: players as 'Name (POS)', picks as 'a 2027 round 2 pick'."""
        rids = [int(x) for x in tx.get("roster_ids") or []]
        got: dict[int, dict] = {r: {"players": [], "picks": [], "pids": []} for r in rids}
        for pid, to in (tx.get("adds") or {}).items():
            if int(to) in got:
                lab = self.label(pid)
                got[int(to)]["players"].append(f"{lab['name']} ({lab['position']})")
                got[int(to)]["pids"].append(pid)
        for p in tx.get("draft_picks") or []:
            if p.get("owner_id") is not None and int(p["owner_id"]) in got:
                got[int(p["owner_id"])]["picks"].append(f"a {p.get('season')} round {p.get('round')} pick")
        return got
