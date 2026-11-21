"""The weekly team report: one article per team per completed week, bylined by that team's beat reporter
(beat_reporters.py), and always harshly critical of the OWNER, win or lose.

A win gets backhanded credit, a loss gets the blame. Every claim comes from facts already in the season context (the
week's score and result, the bench, the standings as of that week, streaks, the week's trades and waiver moves, season
patterns); personal jabs come from the owner profile in config.yaml (nickname, traits, hometown, catchphrase) and the
piece reads fine without one. Line pools live in beat_text.py. Everything is seeded: same inputs, same text.
"""
from __future__ import annotations

import random
import re
from typing import Any

from .. import stats
from . import beat_text as T
from .beat_reporters import STRUCTURES, BeatReporter, assign
from .beats_extra import Beats3
from .util import fill, fmt, join_and, mclass, num_word, ordinal, pct, plural, polish, pts, sentence_case, split_sentences, times

CATCH_SHARE = 0.15   # a team report may carry a catchphrase only while the whole build stays under this share
# conflict groups: a report uses at most one fact per group (so it never says the same thing twice)
GROUPS = {"bench": "bench", "bench_n": "bench", "bench_nr": "bench", "consol": "rank", "bench_gt": "bench", "standing": "rank", "leader": "rank", "cellar": "rank",
          "up": "rank", "down": "rank", "finish": "rank", "streak": "streak", "streak_end": "streak", "snap": "streak",
          "luck_pos": "luck", "luck_neg": "luck", "subpar": "luck", "lowscore": "wk", "highscore": "wk", "luckywin": "wk",
          "unlucky": "wk", "avgweek_up": "wk", "avgweek_dn": "wk", "avg_up": "avg", "avg_dn": "avg",
          "trade_pending": "trade", "trade_lead": "trade", "trade_trail": "trade",
          "waiver_bid": "waiver", "waiver_free": "waiver", "waiver_multi": "waiver", "waiver_low": "waiver",
          "waiver_mid": "waiver", "waiver_hi": "waiver", "odds_low": "odds", "odds_mid": "odds", "odds_high": "odds",
          "odds_clinched": "odds", "odds_out": "odds"}
HW_KEY = {"bench_n": "bench", "bench_nr": "bench", "bench_gt": "bench", "trade_pending": "trade", "trade_lead": "trade", "trade_trail": "trade",
          "waiver_bid": "waiver", "waiver_free": "waiver", "waiver_multi": "waiver", "luckywin": "wk", "unlucky": "wk", "lowscore": "wk"}
HEAD_KEY = {"trade_lead": "trade_pending", "trade_trail": "trade_pending", "bench_n": "bench", "bench_nr": "bench_n"}


SENSITIVE = re.compile(r"blood sugar|diabet|insulin|cancer|disease|illness|\bsick|hospital|surgery|medic|depress|anxiety|mental|therap|rehab|"
                       r"addict|sober|\bdied\b|death|funeral|passed away|grief|widow|divorce|miscarr|disab|wheelchair|suicid|overdos", re.I)
_UNITS = re.compile(r"\b(?:points?|shotguns?)\b")


def _picks(text: str) -> str:
    """'two 2028 round 1 picks' -> 'two 2028 round one picks' (a bare '1 picks' reads as a typo and fails the lint)."""
    return re.sub(r"\bround 1 picks\b", "round one picks", text)


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


_AM_PM = re.compile(r"\b([ap]\.m)\.(?=\s+[a-z])")


def _polish(text: str, protect) -> str:
    """polish() capitalizes the word after every ". ", including after "a.m." / "p.m." in the middle of a sentence
    ("at 4 a.m. with Daft Punk on"); shield that dot for the pass."""
    return polish(_AM_PM.sub("\\1\ue000", text), protect).replace("\ue000", ".")


def _sent_keys(text: str) -> list[str]:
    return [" ".join(x.casefold().split()) for x in split_sentences(text)]


def _pos_of(ctx_players: dict, pid: str) -> set[str]:
    return stats._player_pos(ctx_players, pid)   # noqa: SLF001  (read-only reuse of the league's own position rules)


class BeatsTeam(Beats3):
    def __init__(self, ctx, st, po, shotgun_items):
        super().__init__(ctx, st, po, shotgun_items)
        self.beat_by_rid: dict[int, BeatReporter] = assign(ctx.get("config"), self.teams)
        self._bt_use: dict[tuple, int] = {}
        self._bt_hist: dict[tuple, list[str]] = {}
        self._bt_week_used: set[tuple] = set()
        self._bt_week_sent: set[str] = set()   # normalized sentences already written in the week being built
        self._bt_bench_c: dict[tuple, tuple] = {}
        self._bt_field_c: set[int] | None = None
        self._bt_eff: dict[int, dict] = {}

    # ---- masthead ------------------------------------------------------------
    def beat_masthead(self) -> list[dict]:
        """The beat reporters of THIS league, each with the team covered."""
        out = []
        for rid, v in sorted(self.beat_by_rid.items(), key=lambda kv: (self.name(kv[0]).casefold(), kv[0])):
            out.append({**v.card(), "team": {"roster_id": rid, "name": self.name(rid), "team_name": self.tname(rid)}})
        return out

    # ---- line choice ----------------------------------------------------------
    def _bt_pool(self, pool: dict, tone: str) -> list[str]:
        out = list(pool.get(tone, [])) + list(pool.get("A", []))
        if not out and tone == "T":
            out = list(pool.get("L", []))
        return out

    def _bt_variant(self, rep: BeatReporter, week: int, key: str, variants: list[str], V: dict | None = None) -> str:
        """The next line of `key` in this reporter's own (seeded) order that this reporter has not used yet, whatever the
        tone of the earlier piece; once the pool is used up, the one used longest ago. No two teams use the same line in one
        week while the pool still has an unused one, and (when the values `V` are given) no sentence of the filled-in
        line has already been written that week by anyone, as long as any line of the pool avoids that."""
        order = sorted(variants, key=lambda v: random.Random(f"beat:{rep.id}:{key}:{v}").random())
        hist = self._bt_hist.setdefault((rep.id, key), [])
        fresh = [v for v in order if v not in hist]
        pool = fresh or sorted(order, key=lambda v: hist.index(v))
        cands = [v for v in pool if not hist or v != hist[-1]] or pool   # never the line this reporter used last time, if avoidable
        wide = [v for v in fresh + sorted((v for v in order if v in hist), key=hist.index) if not hist or v != hist[-1]] or order

        def fresh_sent(v: str) -> bool:
            return V is None or not any(k in self._bt_week_sent for k in _sent_keys(fill(v, V)))
        pick = (next((v for v in cands if (week, key, v) not in self._bt_week_used and fresh_sent(v)), None)
                or next((v for v in wide if (week, key, v) not in self._bt_week_used and fresh_sent(v)), None)
                or next((v for v in wide if fresh_sent(v)), None)
                or next((v for v in cands if (week, key, v) not in self._bt_week_used), cands[0]))
        self._bt_week_used.add((week, key, pick))
        if V is not None:
            self._bt_week_sent.update(_sent_keys(fill(pick, V)))
        if pick in hist:
            hist.remove(pick)
        hist.append(pick)
        return pick

    def _bt_line(self, rep, week, pool_name: str, pool: dict, tone: str, V: dict) -> str | None:
        variants = self._bt_pool(pool, tone)
        if not variants:
            return None
        return fill(self._bt_variant(rep, week, pool_name, variants, V), V)

    # ---- facts -----------------------------------------------------------------
    def _bt_week_scores(self, week: int) -> dict[int, float]:
        out: dict[int, float] = {}
        for g in self.games_by_week.get(week, []):
            if g["a"] in self.teams and g["b"] in self.teams:
                out[g["a"]] = g["a_pts"]
                out[g["b"]] = g["b_pts"]
        return out

    def _bt_eff_table(self, upto: int) -> dict[int, dict]:
        if upto not in self._bt_eff:
            self._bt_eff[upto] = self._eff_table(upto)
        return self._bt_eff[upto]

    def _bt_bench(self, week: int, rid: int) -> tuple[float, dict | None]:
        """(points the best LEGAL lineup would have added, the bench player who should have started) for that week.

        Unlike book.bench_left this only lets players into the optimal lineup who could have started: taxi-squad and
        IR/reserve players are excluded, and the lineup is built slot by slot from the league's roster_positions with the
        same rules and greedy order as stats.optimal_lineup_points (which matches Sleeper's own ppts to the cent). A bench
        player is only named if he is in that optimal lineup and was not in the actual one; `replaces` is the starter the
        optimal lineup drops, when exactly one dropped starter held a slot he could have filled.
        LIMITATION: Sleeper only gives the CURRENT taxi / IR lists (ctx["inactive"]), no weekly snapshot, so those lists are
        applied to every week: a player who was on the taxi squad in week 4 but activated later is treated as legal
        in no week, and one who was on the active roster then and has since been stashed is excluded from that week too."""
        key = (week, rid)
        if key in self._bt_bench_c:
            return self._bt_bench_c[key]
        res: tuple[float, dict | None] = (0.0, None)
        row = self.week_row(week, rid)
        pp = {str(p): float(v or 0) for p, v in ((row or {}).get("players_points") or {}).items()}
        if row and pp:
            res = self._bt_bench_calc(row, rid, pp)
        self._bt_bench_c[key] = res
        return res

    def _bt_bench_calc(self, row: dict, rid: int, pp: dict[str, float]) -> tuple[float, dict | None]:
        players = self.ctx["players"]
        rp = list(self.ctx["roster_positions"])
        inactive = (self.ctx.get("inactive") or {}).get(rid) or {}
        barred = {str(p) for p in (inactive.get("taxi") or []) + (inactive.get("reserve") or [])}
        starters = [str(p) for p in (row.get("starters") or [])]
        started = {p for p in starters if p not in ("", "0", "None")}
        legal = sorted((p for p in pp if p not in barred or p in started), key=lambda p: (-pp[p], p))
        slots = [s for s in rp if s not in stats.NON_STARTING]
        fixed = [s for s in slots if s not in stats.FLEX_ELIGIBILITY]
        flex = sorted((s for s in slots if s in stats.FLEX_ELIGIBILITY), key=lambda s: len(stats.FLEX_ELIGIBILITY[s]))
        chosen: list[str] = []
        for slot in fixed + flex:
            elig = stats.FLEX_ELIGIBILITY.get(slot)
            for pid in legal:
                if pid in chosen:
                    continue
                if (slot in _pos_of(players, pid)) if elig is None else (_pos_of(players, pid) & elig):
                    chosen.append(pid)
                    break
        opt = round(sum(pp[p] for p in chosen), 2)
        left = round(opt - float(row.get("points") or 0), 2)
        if left <= 0:
            return 0.0, None
        added = sorted((p for p in chosen if p not in started), key=lambda p: (-pp[p], p))
        if not added or pp[added[0]] <= 0:
            return left, None
        top = added[0]
        dropped = [(i, p) for i, p in enumerate(starters) if p in started and p not in chosen]
        fits = []
        for i, p in dropped:
            slot = rp[i] if i < len(rp) else ""
            elig = stats.FLEX_ELIGIBILITY.get(slot)
            if (slot in _pos_of(players, top)) if elig is None else (_pos_of(players, top) & elig):
                fits.append(p)
        best = {**self.label(top), "points": round(pp[top], 2), "replaces": None}
        if len(fits) == 1:
            best["replaces"] = {**self.label(fits[0]), "points": round(pp.get(fits[0], 0.0), 2)}
        return left, best

    def _bt_field(self) -> set[int]:
        """The teams that made the playoffs: the top `playoff_teams` of the final regular-season standings."""
        if self._bt_field_c is None:
            order = self.snap(self.final_reg_week)["standings"]
            self._bt_field_c = set(order[: self.ctx["playoff_teams"]])
        return self._bt_field_c

    def _bt_alive(self, week: int, rid: int) -> bool:
        """True when `rid`'s game in playoff week `week` is a winners-bracket game: the team made the playoffs and has not
        lost a playoff game yet (a bye is not a loss). Everyone else is playing a consolation (or placement) game."""
        if rid not in self._bt_field():
            return False
        for w in range(self.ctx["playoff_start"], week):
            for g in self.games_by_week.get(w, []):
                if rid in (g["a"], g["b"]) and g["winner"] != rid:
                    return False
        return True

    def _bt_trade(self, week: int, rid: int) -> dict | None:
        for tx in self.live_txs(week):
            if tx.get("type") != "trade" or rid not in [int(x) for x in tx.get("roster_ids") or []]:
                continue
            ti = self.trade_info(tx, week)
            if not ti or rid not in (ti["a"], ti["b"]):
                continue
            partner = ti["b"] if ti["a"] == rid else ti["a"]
            first = ti["first"]
            weeks = len(self.counted_weeks(first, week))     # only the points through THIS week: the report is as of its week
            mine, theirs = ti["got"][rid], ti["got"][partner]
            out = {"partner": self.name(partner), "got": _picks(ti["text"][rid]), "gave": _picks(ti["text"][partner]), "graded": False}
            if weeks >= 1 and mine["players"] and theirs["players"]:
                a = round(sum(self.points_from(p, first, rid, week) for p in mine["pids"]), 2)
                b = round(sum(self.points_from(p, first, partner, week) for p in theirs["pids"]), 2)
                if a != b:
                    out.update(graded=True, lead=a > b, my_pts=pts(a), their_pts=pts(b), split=f"{fmt(a)} to {fmt(b)} points")
            return out
        return None

    def _bt_waiver(self, week: int, rid: int) -> dict | None:
        moves = []
        for tx in self.live_txs(week):
            if tx.get("type") not in ("waiver", "free_agent"):
                continue
            bid = int((tx.get("settings") or {}).get("waiver_bid") or 0)
            first = self.first_week_after(tx, week)
            weeks = len(self.counted_weeks(first, week))
            for pid, to in (tx.get("adds") or {}).items():
                if int(to) != rid:
                    continue
                lab = self.label(pid)
                moves.append({"name": lab["name"], "pos": lab["position"], "bid": bid,
                              "since": self.points_from(pid, first, rid, week) if weeks >= 1 else None})
        if not moves:
            return None
        moves.sort(key=lambda m: (-m["bid"], -(m["since"] or 0), m["name"]))
        return {"top": moves[0], "n": len(moves)}

    def _bt_facts(self, week: int, g: dict, rid: int) -> dict:
        """Everything the report may say, as plain values (see _bt_cands for which of it is worth saying)."""
        me_a = g["a"] == rid
        opp = g["b"] if me_a else g["a"]
        mine, theirs = (g["a_pts"], g["b_pts"]) if me_a else (g["b_pts"], g["a_pts"])
        res = "T" if g["winner"] is None else "W" if g["winner"] == rid else "L"
        F: dict[str, Any] = {"rid": rid, "opp": opp, "week": week, "mine": mine, "theirs": theirs, "res": res,
                             "margin": float(g["margin"]), "playoff": self.is_playoff(week)}   # playoff: a playoff-calendar week (see alive / consol)
        sc = self._bt_week_scores(week)
        F["n_week"] = len(sc)
        F["wr"] = 1 + sum(1 for x, v in sc.items() if v > mine)
        F["lavg"] = sum(sc.values()) / len(sc) if sc else mine
        F["left"], F["best_bench"] = self._bt_bench(week, rid)
        F["alive"] = F["playoff"] and self._bt_alive(week, rid)
        F["consol"] = F["playoff"] and not F["alive"]
        F["worst"] = self.worst_starter(week, rid)
        F["star"] = self.best_starter(week, rid)
        F["sg"] = self.sg_week(week, rid)
        F["trade"] = self._bt_trade(week, rid)
        F["waiver"] = self._bt_waiver(week, rid)
        F["snap"] = None
        if not F["playoff"] or week > self.final_reg_week:
            S1 = self.snap(week)
            F["snap"] = S1["teams"][rid]
            F["order"] = S1["standings"]
            F["S1"] = S1
            if week >= 2 and not F["playoff"]:
                F["rank0"] = self.snap(week - 1)["teams"][rid]["rank"] if self.snap(week - 1)["teams"][rid]["games"] else None
        F["latest"] = week == self.ctx["last_completed"]
        return F

    def _bt_cands(self, F: dict, rng: random.Random) -> list[dict]:
        """The things worth saying about this team this week, each with a weight (what is actually notable) and the
        placeholder values its lines need. A seeded jitter breaks ties so teams with the same story do not match."""
        o_res, wk = F["res"], F["week"]
        n, wr, mine, margin = F["n_week"], F["wr"], F["mine"], F["margin"]
        out: list[dict] = []

        def add(kind: str, w: float, V: dict | None = None) -> None:
            out.append({"kind": kind, "w": w + rng.random() * 0.9, "V": V or {}})
        left = F["left"]
        if left >= 12:
            bn = F["best_bench"]
            gt = o_res == "L" and margin > 0 and left > margin   # an avoidable loss: the legal lineup would have beaten the margin
            V = {"left": pts(left), "opt": fmt(mine + left), "left_raw": left}
            named = bool(bn) and bn["points"] > 0
            rp = bn["replaces"] if named else None
            if named:
                V.update(bench_name=bn["name"], bench_pos=bn["position"], bench_pts=pts(bn["points"]))
            if rp:
                V.update(rep_name=rp["name"], rep_pos=rp["position"], rep_pts=pts(rp["points"]))
            add("bench_gt" if gt else "bench_nr" if rp else "bench_n" if named else "bench", 2.0 + min(left, 40) / 10 + (2 if gt else 0), V)
        w = F["worst"]
        if w and w["points"] <= 2 and w["name"] and not any(w["name"] in self._sg_phrase([x]) for x in F["sg"]):
            add("dud", 3.6 if w["points"] <= 0 else 3.2, {"dud": w["name"], "dpos": w["position"], "dpts": pts(w["points"])})
        if F["sg"]:
            add("shotgun", 4.6, {"nsg": plural(len(F["sg"]), "shotgun"), "sg_phrase": self._sg_phrase(F["sg"])})
        st = F["star"]
        if st and st["points"] >= 22 and o_res != "T":
            add("star", 1.8, {"star": st["name"], "spos": st["position"], "spts": pts(st["points"])})
        if o_res == "W" and wr > n / 2 + 0.5:
            add("luckywin", 2.6 + (wr - n / 2) * 0.3, {"k_teams": plural(wr - 1, "team")})
        if o_res == "L" and wr <= max(2, (n + 2) // 3):
            add("unlucky", 3.0, {})
        if o_res == "L" and wr == n:
            add("lowscore", 3.6, {})
        if o_res == "W" and wr == 1:
            add("highscore", 2.4, {})
        d = mine - F["lavg"]
        add("avgweek_up" if d >= 0 else "avgweek_dn", 1.0 + min(abs(d), 40) / 40, {"diff": pts(abs(d))})
        tr = F["trade"]
        if tr:
            if tr["graded"]:
                add("trade_lead" if tr["lead"] else "trade_trail", 4.2, {k: tr[k] for k in ("partner", "got", "gave", "my_pts", "their_pts", "split")})
            else:
                add("trade_pending", 4.2, {k: tr[k] for k in ("partner", "got", "gave")})
        wv = F["waiver"]
        if wv:
            t = wv["top"]
            V = {"player": t["name"], "pos": t["pos"], "bid": f"${t['bid']}", "n_adds": str(wv["n"]), "n_adds_cap": _cap(num_word(wv["n"])) if wv["n"] <= 12 else str(wv["n"])}
            bonus = 0.8 if t["bid"] >= 15 else 0
            if t["since"] is not None:
                V["since_pts"] = pts(t["since"])
                add("waiver_hi" if t["since"] >= 15 else "waiver_mid" if t["since"] >= 5 else "waiver_low", 3.0 + bonus, V)
            elif wv["n"] >= 2:
                add("waiver_multi", 2.6 + bonus, V)
            else:
                add("waiver_bid" if t["bid"] else "waiver_free", 2.8 + bonus, V)
        S = F["snap"]
        if S is None:
            return out
        order, S1 = F["order"], F["S1"]
        n_all = len(order)
        rank, rec = S["rank"], S["record"]
        base = {"rec": rec, "rank_ord": ordinal(rank)}
        if F["playoff"]:
            add("finish" if F["alive"] else "consol", 1.5, base)
            return out
        line = "inside" if rank <= self.ctx["playoff_teams"] else "outside"
        if S["games"] >= 2:
            if rank == 1 and n_all > 2:
                add("leader", 2.5, base)
            elif rank == n_all and n_all > 2:
                add("cellar", 2.5, base)
            else:
                add("standing", 1.3, {**base, "line": line})
        r0 = F.get("rank0")
        if r0 and abs(r0 - rank) >= 2:
            add("up" if rank < r0 else "down", 2.4, {**base, "prev_ord": ordinal(r0), "k": num_word(abs(r0 - rank))})
        res = S["results"]
        run = 1
        while run < len(res) and res[-1 - run] == res[-1]:
            run += 1
        if S["games"] >= 3 and res[-1] in ("W", "L") and run >= 3:
            add("streak", 3.0 + 0.3 * (run - 3), {"k": num_word(run), "k_cap": _cap(num_word(run)), "rec": rec})
        elif S["games"] >= 2:
            prev = res[:-1]
            pr = 0
            while pr < len(prev) and prev[-1 - pr] == prev[-1]:
                pr += 1
            if res[-1] == "L" and prev and prev[-1] == "W" and pr >= 3:
                add("streak_end", 2.8, {"k": num_word(pr)})
            elif res[-1] == "W" and prev and prev[-1] == "L" and pr >= 2:
                add("snap", 2.0, {"k": num_word(pr)})
        if S["games"] >= 5 and abs(S["luck"]) >= 1.5:
            exp = int(S["expected_wins"] + 0.5)
            add("luck_pos" if S["luck"] > 0 else "luck_neg", 2.4, {"rec": rec, "exp_rec": f"{exp}-{max(S['games'] - exp, 0)}"})
        wrk = S["weekly_rank"]
        if len(wrk) >= 5:
            below = sum(1 for v in wrk.values() if v > n_all / 2)
            if below / len(wrk) >= 0.6:
                add("subpar", 2.2, {"c": str(below), "m": str(len(wrk))})
        if S["weeks_bottom"] >= 2:
            add("bottom", 2.3, {"k_times": times(S["weeks_bottom"]), "k_times_cap": _cap(times(S["weeks_bottom"]))})
        if S["weeks_top"] >= 2 and o_res == "W":
            add("top", 1.8, {"k_times": times(S["weeks_top"])})
        et = self._bt_eff_table(wk)
        if wk >= 3 and F["rid"] in et and len(et) >= 4:
            by_eff = sorted(et, key=lambda x: (-et[x]["eff"], x))
            er = by_eff.index(F["rid"]) + 1
            if er >= len(et) - 2:
                add("eff", 2.3, {"eff_pct": f"{round(et[F['rid']]['eff'] * 100)}%", "eff_rank_ord": ordinal(er), "season_left": pts(et[F["rid"]]["left"])})
        if S["games"] >= 3:
            avgs = [S1["teams"][x]["avg"] for x in order]
            lav = sum(avgs) / len(avgs)
            dv = S["avg"] - lav
            if abs(dv) >= 3:
                add("avg_up" if dv > 0 else "avg_dn", 1.5, {"avg": fmt(S["avg"]), "lavg_s": fmt(lav), "diff_s": pts(abs(dv))})
        pot = (self.po.get("teams") or {}).get(F["rid"])
        if F["latest"] and pot and not self.season_over():
            p = pot.get("playoff_pct")
            if pot.get("status") == "clinched":
                add("odds_clinched", 3.2, {})
            elif pot.get("status") == "eliminated":
                add("odds_out", 3.2, {})
            elif p is not None:
                add("odds_low" if p < 0.2 else "odds_mid" if p <= 0.65 else "odds_high", 2.6, {"odds": pct(p)})
        return out

    # ---- the article -----------------------------------------------------------
    def _bt_grade(self, F: dict, kinds: list[str]) -> str:
        s = 72.0 + (8 if F["res"] == "W" else -9 if F["res"] == "L" else -2)
        s -= min(14.0, F["left"] / 3)
        s += (F["n_week"] / 2 - F["wr"]) * 1.2
        s -= 6 if "shotgun" in kinds else 0
        s -= 3 if "dud" in kinds else 0
        s += 3 if "streak" in kinds and F["res"] == "W" else -3 if "streak" in kinds else 0
        s = min(s, {"W": 82.0, "L": 69.0, "T": 74.0}[F["res"]])
        if F["res"] == "W":
            s = max(s, 64.0)   # backhanded, not absurd: even the harshest report card does not fail a win
        for cut, letter in ((80, "B-"), (75, "C+"), (70, "C"), (65, "C-"), (60, "D+"), (55, "D"), (50, "D-")):
            if s >= cut:
                return letter
        return "F"

    def _bt_jabs(self, rep: BeatReporter, rid: int, week: int, tone: str, V: dict, rng: random.Random, want: int) -> list[tuple[str, str]]:
        """Personal jabs from the owner profile (kind, text); a generic owner jab when the profile has nothing to use."""
        prof = self.profile(rid)
        name = self.name(rid)
        kinds: list[tuple[str, float]] = []
        traits = [str(t).strip().rstrip(".") for t in prof.get("traits") or []
                  if str(t).strip() and not SENSITIVE.search(str(t))]   # never joke about health, grief or the like, even if the owner's profile does
        nick = str(prof.get("nickname") or "").strip()
        home = str(prof.get("hometown") or "").strip()
        catch = str(prof.get("catchphrase") or "").strip()
        use = lambda k: self._bt_use.get((f"jab:{rid}", k), 0)   # noqa: E731  (how often this owner got this kind of jab)
        if traits:
            kinds.append(("trait", 3.0 / (1 + use("trait"))))
        if nick and nick != name:
            kinds.append(("nick", 2.0 / (1 + use("nick"))))
        if home:
            kinds.append(("home", 1.5 / (1 + use("home"))))
        if catch and (rid, week) not in self.catch_week and (self.n_catch + 1) <= CATCH_SHARE * (self.n_articles + 1):
            kinds.append(("catch", 0.9 / (1 + use("catch"))))
        out: list[tuple[str, str]] = []
        while kinds and len(out) < want:
            tot = sum(w for _, w in kinds)
            x, acc, pick = rng.random() * tot, 0.0, kinds[-1][0]
            for k, w in kinds:
                acc += w
                if x < acc:
                    pick = k
                    break
            kinds = [(k, w) for k, w in kinds if k != pick]
            vals = dict(V)
            if pick == "trait":
                perm = sorted(range(len(traits)), key=lambda i: random.Random(f"trait:{rid}:{i}").random())
                vals["trait"] = traits[perm[use("trait") % len(traits)]]
                text = self._bt_line(rep, week, "trait", T.TRAIT, tone, vals)
            elif pick == "nick":
                vals["nick"] = nick
                text = self._bt_line(rep, week, "nick", T.NICK, tone, vals)
            elif pick == "home":
                vals["home"] = home
                text = self._bt_line(rep, week, "home", T.HOME, tone, vals)
            else:
                c = catch.replace("{me}", name).replace("{them}", str(V.get("opp") or "everyone")).strip()
                vals["q"] = f"“{c}”" if c[-1] in ".!?" else f"“{c}.”"
                text = self._bt_line(rep, week, "catch", T.CATCH, tone, vals)
                self.catch_week.add((rid, week))
                self.n_catch += 1
            if text and nick and pick in ("trait", "nick") and any(nick.casefold() in t.casefold() for _, t in out):
                text = None   # the nickname may appear once per article: a trait that quotes it and the aside never share a report
            self._bt_use[(f"jab:{rid}", pick)] = use(pick) + 1
            if text:
                out.append((pick, text))
        if not out:
            out.append(("generic", self._bt_line(rep, week, "generic", T.GENERIC, tone, V)))
        return out

    def team_report(self, week: int, g: dict, rid: int) -> dict | None:
        rep = self.beat_by_rid.get(rid)
        if rep is None:
            return None
        rng = random.Random(f"{self.season}:beat:{week}:{rid}:{rep.id}")
        F = self._bt_facts(week, g, rid)
        tone = F["res"]
        o, opp = self.name(rid), self.name(F["opp"])
        pn = week - self.ctx["playoff_start"] + 1
        wl = (f"playoff week {pn}" if F["alive"] else f"consolation week {pn}") if F["playoff"] else f"Week {week}"
        tn = self.tname(rid)
        nick = str(self.profile(rid).get("nickname") or "").strip()
        if nick and nick.casefold() in tn.casefold():   # the lint allows a nickname only as the group-chat aside, so never inside a team name
            tn = f"{o}'s team"
        V: dict[str, str] = {"o": o, "t": tn, "opp": opp, "wk": str(week), "wl": wl, "mine": fmt(F["mine"]),
                             "theirs": fmt(F["theirs"]), "margin": fmt(F["margin"]), "n": str(F["n_week"]), "wr_ord": ordinal(F["wr"]),
                             "lavg": fmt(F["lavg"]), "column": rep.column, "left_num": fmt(F["left"])}
        cands = self._bt_cands(F, rng)
        cands.sort(key=lambda c: -c["w"])
        chosen: list[dict] = []
        seen_groups: set[str] = set()
        for c in cands:
            grp = GROUPS.get(c["kind"], c["kind"])
            if grp in seen_groups:
                continue
            seen_groups.add(grp)
            chosen.append(c)
            if len(chosen) == 4:
                break
        kinds = [c["kind"] for c in chosen]
        V.setdefault("rec", "")
        if F["snap"]:
            V["rec"], V["rank_ord"] = F["snap"]["record"], ordinal(F["snap"]["rank"])
            V["streak_raw"] = F["snap"]["streak"]
        grade = self._bt_grade(F, kinds)
        V["grade"] = grade
        for c in chosen:   # each fact's placeholders live in its own dict: two facts both using {k} (a streak and a rank climb) never clash
            c["VV"] = {**V, **c["V"]}
        vv = {c["kind"]: c["VV"] for c in chosen}
        # core line and margin
        core = self._bt_line(rep, week, "core", T.CORE, tone, V)
        mc = mclass(F["margin"])
        mkind = None
        if tone != "T" and (mc == "blowout" or mc == "close") and rng.random() < (1.0 if mc == "blowout" else 0.8):
            mkind = ("blow_" if mc == "blowout" else "close_") + tone.lower()
        margin_line = self._bt_line(rep, week, mkind, {"A": T.MARGIN[mkind]}, tone, V) if mkind else None
        flines: list[tuple[str, str]] = []
        for c in chosen:
            flines.append((c["kind"], self._bt_line(rep, week, c["kind"], T.FACTS[c["kind"]], tone, c["VV"])))
        # structure
        weights = [3.0 if s in rep.favs else 1.0 for s in STRUCTURES]
        structure = rng.choices(STRUCTURES, weights=weights)[0]
        want_jabs = 2 if structure == "verdict" else 1
        jabs = self._bt_jabs(rep, rid, week, tone, V, rng, want_jabs)
        verdict = self._bt_line(rep, week, "verdict", T.VERDICT, tone, V)
        opener = self._bt_variant(rep, week, "opener", list(rep.openers), V) if rng.random() < 0.55 else None
        closer = self._bt_variant(rep, week, "closer", list(rep.closers), V) if rng.random() < 0.65 else None
        tic = self._bt_variant(rep, week, "tic", list(rep.tics), V) if rng.random() < 0.45 else None
        paras = self._bt_structure(structure, rep, rng, V, vv, tone, week, core, margin_line, flines, jabs, verdict, opener, closer, tic, grade, F)
        protect = self.protected_rx()
        body = []
        for p in paras:
            p = _polish(" ".join(p.split()), protect)
            body.append(_cap(p) if not (protect is not None and protect.match(p, 0)) else p)
        # headline
        head_kinds = [HEAD_KEY.get(k, k) for k in ([mkind] if mkind else []) + kinds]
        hl_pools = []
        for src, k in zip(([mkind] if mkind else []) + kinds, head_kinds):
            pool = T.HEAD.get(k)
            if isinstance(pool, dict) and self._bt_pool(pool, tone):
                hl_pools.append((k, pool, vv.get(src, V)))

        def title(vals: dict) -> dict:   # headlines are Title Case: "2 Points", "1 Shotgun", "Three"
            hv = {k: _UNITS.sub(lambda m: m.group(0).capitalize(), v) for k, v in vals.items() if isinstance(v, str)}
            hv["k"] = _cap(vals.get("k", ""))
            return hv
        if hl_pools and rng.random() < 0.6:
            k, pool, hvals = hl_pools[rng.randrange(len(hl_pools))]
            headline = fill(self._bt_variant(rep, week, f"head:{k}", self._bt_pool(pool, tone)), title(hvals))
        else:
            headline = fill(self._bt_variant(rep, week, "head", T.HEAD[tone]), title(V))
        headline = _polish(headline, protect)
        result_word = {"W": "won", "L": "lost", "T": "tied"}[tone]
        dek = f"{wl[:1].upper() + wl[1:]}: {o} {result_word} {fmt(F['mine'])}-{fmt(F['theirs'])} against {opp} · {V['t']} beat report"
        packet = self._bt_packet(F, vv, kinds, jabs, grade, structure, rep, rid)
        packet["beats"] = [structure] + kinds + [j[0] for j in jabs]
        packet["paras"] = [{} for _ in body]
        return self._bt_article(rep, rid, week, headline, dek, body, packet)

    def _bt_structure(self, structure, rep, rng, V, vv, tone, week, core, margin_line, flines, jabs, verdict, opener, closer, tic, grade, F) -> list[str]:
        f = [t for _, t in flines if t]
        fk = [k for k, t in flines if t]
        j = [t for _, t in jabs if t]
        head = " ".join(x for x in (opener, core, margin_line) if x)
        pad = lambda lst, i: lst[i] if i < len(lst) else None   # noqa: E731
        tail = " ".join(x for x in (closer,) if x)
        if structure == "verdict":
            p2 = " ".join(x for x in (pad(f, 0), pad(f, 1), tic) if x)
            p3 = " ".join(x for x in (pad(f, 2), pad(f, 3), pad(j, 0)) if x)
            p4 = " ".join(x for x in (pad(j, 1), verdict, tail) if x)
            return [head, p2, p3, p4]
        if structure == "grade":
            intro = fill(self._bt_variant(rep, week, "grade_intro", T.GRADE_INTRO, V), V)
            case = fill(self._bt_variant(rep, week, "grade_case", T.GRADE_CASE, V), V)
            hw_key = next((HW_KEY.get(k, k) for k in fk if HW_KEY.get(k, k) in T.HOMEWORK), "default")
            hw = fill(self._bt_variant(rep, week, f"hw:{hw_key}", T.HOMEWORK[hw_key], V), V)
            return [" ".join(x for x in (intro, opener, core, margin_line) if x),
                    " ".join(x for x in [case] + f[:3] + [tic] if x),
                    " ".join(x for x in (pad(j, 0), verdict) if x),
                    " ".join(x for x in (hw, tail) if x)]
        if structure == "notebook":
            lab = self._bt_variant(rep, week, "note_label", T.NOTE_LABEL)
            intro = fill(self._bt_variant(rep, week, "note_intro", T.NOTE_INTRO, V), V)
            notes = [f"{fill(lab, {'i': str(i)})} {txt}" for i, txt in enumerate(f[:3], 1)]
            last = f"{fill(lab, {'i': str(len(notes) + 1)})} {pad(j, 0)}" if pad(j, 0) else None
            paras = [" ".join(x for x in (intro, opener, core, margin_line) if x)] + notes + [x for x in (last,) if x]
            paras.append(" ".join(x for x in (verdict, tic, tail) if x))
            return paras
        if structure == "questions":
            qs = []
            for k, t in flines:
                if t and k in T.QUESTIONS:
                    qs.append(fill(self._bt_variant(rep, week, f"q:{k}", T.QUESTIONS[k], vv[k]), vv[k]))
            while len(qs) < 3:
                qs.append(fill(self._bt_variant(rep, week, "q:default", T.Q_DEFAULT, V), V))
            intro = fill(self._bt_variant(rep, week, "q_intro", T.Q_INTRO, V), V)
            outro = self._bt_variant(rep, week, "q_outro", T.Q_OUTRO, V)
            return [head, " ".join(x for x in [intro] + qs[:3] + [tic] if x),
                    " ".join(x for x in (pad(f, 0), pad(j, 0)) if x),
                    " ".join(x for x in (verdict, outro, tail) if x)]
        # ledger
        intro = fill(self._bt_variant(rep, week, "ledger_intro", T.LEDGER_INTRO, V), V)
        lab = lambda k, opts: self._bt_variant(rep, week, k, opts)   # noqa: E731
        lines = [f"{lab('l_score', ['Score', 'Final', 'Result'])}: {V['mine']}-{V['theirs']}.",
                 lab("l_rank", [f"Scoring rank this week: {V['wr_ord']} of {V['n']}.", f"Week rank: {V['wr_ord']} of {V['n']}.", f"Ranked {V['wr_ord']} of {V['n']} in scoring."]),
                 lab("l_bench", [f"Bench points left: {V['left_num']}.", f"Left on the bench: {V['left_num']}.", f"Unused bench points: {V['left_num']}."])]
        if F["snap"]:
            lines.append(f"{'Record' if not F['playoff'] else 'Regular-season record'}: {F['snap']['record']}, {ordinal(F['snap']['rank'])}.")
            if not F["playoff"] and F["snap"]["games"] >= 2:
                lines.append(f"Streak: {F['snap']['streak']}.")
        head = " ".join(x for x in (opener, core, margin_line) if x)
        return [head, f"{intro} " + " ".join(lines), " ".join(x for x in (pad(f, 0), pad(f, 1), tic) if x),
                " ".join(x for x in (pad(f, 2), pad(j, 0), verdict, tail) if x)]

    def _bt_packet(self, F, vv, kinds, jabs, grade, structure, rep, rid) -> dict:
        prof = self.profile(rid)
        S = F["snap"]
        pk: dict[str, Any] = {
            "type": "beat", "week": F["week"], "team": self.name(rid), "team_name": self.tname(rid), "beat_reporter": rep.name,
            "instruction": "Harshly critical of the OWNER, win or lose: a win gets backhanded credit, a loss gets the blame. "
                           "Use only these facts; add personal jabs from `profile`. No slurs, nothing about health or family tragedy.",
            "result": {"result": F["res"], "score": fmt(F["mine"]), "opponent": self.name(F["opp"]), "opponent_score": fmt(F["theirs"]),
                       "margin": fmt(F["margin"]), "week_scoring_rank": f"{F['wr']} of {F['n_week']}", "league_week_average": fmt(F["lavg"]),
                       "bench_points_left": fmt(F["left"]), "playoff": bool(F["alive"]), "consolation": bool(F["consol"])},
            "notable": [{"kind": k} for k in kinds],
            "profile": {k: prof.get(k) for k in ("nickname", "traits", "hometown", "catchphrase") if prof.get(k)},
            "grade": grade, "structure": structure,
        }
        if S:
            pk["standing"] = {"record": S["record"], "rank": S["rank"], "streak": S["streak"], "games": S["games"],
                              "all_play_luck": S["luck"]}
        skip = {"o", "t", "opp", "wk", "wl", "mine", "theirs", "margin", "n", "wr_ord", "lavg", "column", "left_num", "rec", "rank_ord",
                "streak_raw", "grade"}
        for k, vals in vv.items():   # the numbers and names behind each notable fact, by fact kind
            det = {a: b for a, b in vals.items() if isinstance(b, (str, int, float)) and a not in skip and not a.endswith("_cap")}
            if det:
                pk.setdefault("details", {})[k] = det
        return pk

    def _bt_article(self, rep: BeatReporter, rid: int, week: int, headline: str, dek: str, body: list[str], facts: dict) -> dict:
        self.n_articles += 1
        self._id += 1
        text = " ".join(body)
        card = rep.card()
        return {"id": f"{self.season}-beat-{week}-{self._id}", "key": f"{self.season}:beat:{week}:{rid}", "type": "beat", "week": week,
                "headline": headline, "dek": dek, "byline": f"{rep.name}, {rep.outlet}", "reporter": card, "body": body,
                "teams": [rid] if self.name(rid) in text or self.nickname(rid) in text else [rid],
                "tags": ["beat", f"week-{week}"], "facts": facts, "source": "template"}

    # ---- the pass over the season ----------------------------------------------
    def beat_reports(self) -> list[dict]:
        """One team report per team that played in each completed week (regular season and playoffs)."""
        out: list[dict] = []
        last = self.ctx["last_completed"]
        for week in sorted(w for w in self.games_by_week if w <= last):
            self._bt_week_used = {u for u in self._bt_week_used if u[0] == week}
            self._bt_week_sent = set()
            for g in sorted(self.games_by_week[week], key=lambda x: (x["a"], x["b"])):
                if g["a"] not in self.teams or g["b"] not in self.teams:
                    continue
                for rid in sorted((g["a"], g["b"])):
                    art = self._try(f"beat week {week} team {rid}", lambda w=week, gg=g, r=rid: self.team_report(w, gg, r))
                    if art:
                        out.append(art)
        return out


def rid_in(d: dict, rid: int) -> bool:
    return rid in d
