"""Article builders for the Sunday trash-talk column and the Monday analytics report.

Both are written as of the end of a regular-season week (the snapshot through that week) and state only
what the data supports: h2h, standings gaps, recent margins, rivalry backstory (column); luck index, lineup
efficiency, bench points, weekly-rank consistency, trade early returns (analytics).
"""
from __future__ import annotations

from statistics import pstdev
from typing import Any

from .beats_misc import Beats2
from .engine import Writer
from .util import fmt, join_and, ordinal, pct, plural, pts, signed


class Beats3(Beats2):
    # ======================================================================
    # Sunday column
    # ======================================================================
    def column_pair(self, week: int, feud_pair: frozenset | None, used: set, r) -> tuple[int, int, dict | None, int | None] | None:
        """(a, b, rivalry, upcoming_week) for the column: next week's matchup when we know it (so the column can
        look ahead), otherwise a game of this week. Avoids the pair the week's feud used and earlier columns."""
        if week < 1 or week > self.final_reg_week:
            return None
        nxt = week + 1
        games = self.games_by_week.get(nxt) or self.st["schedule"].get(nxt) or []
        upcoming = nxt if games and nxt > self.ctx["last_completed"] else None
        if not games:
            games = self.games_by_week.get(week, [])
        games = [g for g in games if g["a"] in self.teams and g["b"] in self.teams]
        if not games:
            return None
        S = self.snap(week)
        scored = []
        for g in games:
            a, b = g["a"], g["b"]
            pair = frozenset((a, b))
            sc = r.random()
            rv = self.rivalry_between(a, b)
            if rv:
                sc += 4
            if abs(S["teams"][a]["rank"] - S["teams"][b]["rank"]) <= 2:
                sc += 2
            if self.h2h_games(a, b, week):
                sc += 1
            if feud_pair is not None and pair == feud_pair:
                sc -= 6
            if pair in used:
                sc -= 4
            scored.append((sc, a, b, rv))
        _, a, b, rv = max(scored, key=lambda x: (x[0], -min(x[1], x[2])))
        if S["teams"][a]["rank"] > S["teams"][b]["rank"]:
            a, b = b, a
        return a, b, rv, upcoming

    def _form(self, rid: int, week: int) -> str | None:
        gs = sorted((g for g in self.st["games"] if g["week"] <= week and rid in (g["a"], g["b"])), key=lambda g: g["week"])[-3:]
        parts = []
        for g in gs:
            if g["winner"] is None:
                parts.append("played to a tie")
            elif g["winner"] == rid:
                parts.append(f"won by {fmt(g['margin'])}")
            else:
                parts.append(f"lost by {fmt(g['margin'])}")
        return join_and(parts) if len(parts) >= 2 else None

    def column(self, week: int, a: int, b: int, rv: dict | None, upcoming: int | None, voice) -> dict | None:
        S = self.snap(week)
        if S["week"] < 1:
            return None
        r = self.rng("column", week, a, b, voice.id)
        w = Writer(self, voice, r, "column", week)
        nar = w.active(a, b)
        nm = self.name
        T = S["teams"]
        wk, wl = str(S["week"]), f"Week {S['week']}"
        A, B = self._pv(a, S), self._pv(b, S)
        f = {"a": nm(a), "b": nm(b), "a_team": self.tname(a), "b_team": self.tname(b), "wk": wk, "wl": wl}
        lede_f = {**f, "a_rec": T[a]["record"], "b_rec": T[b]["record"], "a_rank": ordinal(T[a]["rank"]), "b_rank": ordinal(T[b]["rank"])}
        # headline: the narrative's target > rivalry name > the coming meeting > the generic pairing
        headline = w.head_slanted(nar, "h.sl.any", {"n": nm(nar.rid), "wl": wl, "wk": wk}) if nar else None
        if headline is not None:
            pass
        elif rv:
            headline = w.head("h.c.rv", {**f, "rv_name": rv["name"]})
        elif upcoming:
            headline = w.head("h.c.next", {**f, "nwk": str(upcoming)})
        else:
            headline = w.head("h.c", f)
        p1 = [w.line("c.lede", lede_f, repeat=True)]
        if upcoming:
            p1.append(w.line("c.next", {**f, "nwk": str(upcoming)}, repeat=True))
        w.add(p1, {"column": True})

        ev: list[str | None] = [self._h2h_line(w, A, B, week)]
        fa, fb = self._form(a, week), self._form(b, week)
        if fa and fb:
            ev.append(w.line("c.recent", {**f, "a_form": fa, "b_form": fb}, repeat=True))
        hi, lo = (a, b) if T[a]["rank"] <= T[b]["rank"] else (b, a)
        gap = abs(T[a]["pf"] - T[b]["pf"])
        ev.append(w.line("c.gap", {"hi": nm(hi), "lo": nm(lo), "hi_rank": ordinal(T[hi]["rank"]), "lo_rank": ordinal(T[lo]["rank"]),
                                   "hi_rec": T[hi]["record"], "lo_rec": T[lo]["record"], "pf_gap": pts(gap), "wk": wk, "wl": wl}, repeat=True))
        if rv and rv["backstory"]:
            ev.append(w.line("f.story", {"rv_name": rv["name"], "backstory": rv["backstory"].strip(), "a": nm(a), "b": nm(b)}, repeat=True))
        cnt = self.sg_counts(S["week"])
        ca, cb = cnt.get(a, 0), cnt.get(b, 0)
        if ca != cb and ca + cb >= 2 and r.random() < 0.5:
            ev.append(w.line("f.sg", {"a": nm(a), "b": nm(b), "a_sg": plural(ca, "shotgun") if ca else "no shotguns",
                                      "b_sg": plural(cb, "shotgun") if cb else "no shotguns"}))
        w.add(ev, {"column": True})

        # the pick: only claims what the numbers say
        fav = dog = why = None
        if upcoming and self.po.get("teams") and S["week"] == self.ctx["last_completed"]:
            fv, dg, why = self._favorite(A, B)
            if fv:
                fav, dog = fv["name"], dg["name"]
        if fav is None and T[a]["avg"] != T[b]["avg"]:
            fav, dog = (nm(a), nm(b)) if T[a]["avg"] > T[b]["avg"] else (nm(b), nm(a))
            why = "scoring average"
        s3 = list(self._exchange(w, A, B, week))
        if fav:
            s3.append(w.line("c.pick", {**f, "fav": fav, "dog": dog, "fav_why": why}, repeat=True))
        w.add(s3, {"column": True})
        w.add([w.line("c.close", f, repeat=True)], {"column": True})
        w.add_theme(nar)

        hh = self.h2h_games(a, b, week)
        wa = sum(1 for g in hh if g["winner"] == a)
        wb = sum(1 for g in hh if g["winner"] == b)
        h2h_txt = f"{wa}-{wb}" + (f"-{len(hh) - wa - wb}" if len(hh) - wa - wb else "") if hh else "no meeting yet"
        dek = (f"Through {wl}: {nm(a)} ({T[a]['record']}, {ordinal(T[a]['rank'])}) vs. {nm(b)} ({T[b]['record']}, {ordinal(T[b]['rank'])})"
               f" · head to head: {h2h_txt}" + (f" · they meet in Week {upcoming}" if upcoming else ""))
        facts = {"type": "column", "week": week, "through_week": S["week"], "teams": [nm(a), nm(b)],
                 "records": [T[a]["record"], T[b]["record"]], "ranks": [T[a]["rank"], T[b]["rank"]],
                 "points_for": [fmt(T[a]["pf"]), fmt(T[b]["pf"])], "h2h_this_season": h2h_txt,
                 "recent_margins": {nm(a): fa, nm(b): fb}, "pick": fav, "pick_basis": why if fav else None,
                 "next_meeting_week": upcoming, "rivalry": rv["name"] if rv else None}
        return self._article(w, "column", week, headline, dek, [a, b], ["column"] + (["rivalry"] if rv else []) + [f"week-{week}"],
                             facts, key_teams=[a, b])

    # ======================================================================
    # Monday analytics
    # ======================================================================
    def _eff_table(self, upto: int) -> dict[int, dict]:
        """Per roster through `upto`: points scored, points left on the bench vs the optimal lineup, efficiency."""
        out = {}
        for rid in self.teams:
            act = left = 0.0
            worst: tuple[float, int, dict | None] = (0.0, 0, None)
            for wk in range(1, upto + 1):
                row = self.week_row(wk, rid)
                if not row:
                    continue
                lf, best = self.bench_left(wk, rid)
                act += float(row.get("points") or 0)
                left += lf
                if lf > worst[0]:
                    worst = (lf, wk, best)
            if act + left > 0:
                out[rid] = {"act": act, "left": left, "eff": act / (act + left), "worst": worst}
        return out

    def _trade_grades(self, upto: int) -> dict | None:
        """The most lopsided early return among in-season trades that have had at least one week to play out."""
        best = None
        for tw in sorted(self.ctx["transactions"]):
            if tw > upto:
                break
            for tx in self.live_txs(tw):
                if tx.get("type") != "trade":
                    continue
                ti = self.trade_info(tx, tw)
                if not ti:
                    continue
                a, b = ti["a"], ti["b"]
                ga, gb = ti["got"][a], ti["got"][b]
                if not ga["players"] or not gb["players"]:
                    continue
                first = ti["first"]
                n_weeks = len(self.counted_weeks(first, upto))
                if n_weeks < 1:
                    continue
                pa = round(sum(self.points_from(p, first, a, upto) for p in ga["pids"]), 2)
                pb = round(sum(self.points_from(p, first, b, upto) for p in gb["pids"]), 2)
                if pa == pb:
                    continue
                lead, trail = (a, b) if pa > pb else (b, a)
                cand = {"lead": lead, "trail": trail, "lead_pts": max(pa, pb), "trail_pts": min(pa, pb), "twk": tw,
                        "since": n_weeks, "gap": abs(pa - pb)}
                if best is None or cand["gap"] > best["gap"]:
                    best = cand
        return best

    def analytics(self, week: int, voice) -> dict | None:
        if week < 1 or week > self.final_reg_week:
            return None
        S = self.snap(week)
        T, order = S["teams"], S["standings"]
        nm = self.name
        gp = max((T[x]["games"] for x in order), default=0)
        if gp < 1:
            return None
        r = self.rng("analytics", week, voice.id)
        w = Writer(self, voice, r, "analytics", week)
        wk, wl = str(S["week"]), f"Week {S['week']}"
        base = {"wk": wk, "wl": wl}
        cands: list[int] = []
        facts: dict[str, Any] = {"type": "analytics", "week": week, "through_week": S["week"], "games_played": gp}

        luck_f = None
        if gp >= 3:
            lucky = max(order, key=lambda x: (T[x]["luck"], nm(x)))
            unlucky = min(order, key=lambda x: (T[x]["luck"], nm(x)))
            if T[lucky]["luck"] >= 1 and T[unlucky]["luck"] <= -1:
                luck_f = {"lucky": nm(lucky), "lucky_luck": signed(T[lucky]["luck"]), "lucky_rec": T[lucky]["record"],
                          "lucky_exp": f"{T[lucky]['expected_wins']:.1f}", "unlucky": nm(unlucky),
                          "unlucky_luck": signed(T[unlucky]["luck"]), "unlucky_rec": T[unlucky]["record"],
                          "unlucky_exp": f"{T[unlucky]['expected_wins']:.1f}"}
                cands += [lucky, unlucky]
                facts["luck_index"] = {"luckiest": luck_f["lucky"], "luckiest_luck": luck_f["lucky_luck"], "luckiest_record": luck_f["lucky_rec"],
                                       "luckiest_expected_wins": luck_f["lucky_exp"], "unluckiest": luck_f["unlucky"],
                                       "unluckiest_luck": luck_f["unlucky_luck"], "unluckiest_record": luck_f["unlucky_rec"],
                                       "unluckiest_expected_wins": luck_f["unlucky_exp"]}

        et = self._eff_table(S["week"])
        eff_f = bench_f = blunder_f = None
        if len(et) >= 2:
            hi = max(et, key=lambda x: (et[x]["eff"], nm(x)))
            lo = min(et, key=lambda x: (et[x]["eff"], nm(x)))
            tot_act = sum(v["act"] for v in et.values())
            tot_opt = sum(v["act"] + v["left"] for v in et.values())
            if hi != lo and round(et[hi]["eff"] * 100) != round(et[lo]["eff"] * 100):
                eff_f = {"best_n": nm(hi), "best_pct": f"{round(et[hi]['eff'] * 100)}%", "worst_n": nm(lo),
                         "worst_pct": f"{round(et[lo]['eff'] * 100)}%", "lg_pct": f"{round(tot_act / tot_opt * 100)}%"}
                cands += [hi, lo]
                facts["lineup_efficiency"] = {"best": eff_f["best_n"], "best_pct": eff_f["best_pct"], "worst": eff_f["worst_n"],
                                              "worst_pct": eff_f["worst_pct"], "league_pct": eff_f["lg_pct"]}
            most = max(et, key=lambda x: (et[x]["left"], nm(x)))
            least = min(et, key=lambda x: (et[x]["left"], nm(x)))
            if et[most]["left"] > 0 and most != least and round(et[most]["left"], 2) != round(et[least]["left"], 2):
                bench_f = {"bench_n": nm(most), "bench_pts": pts(et[most]["left"]), "bench_low_n": nm(least), "bench_low_pts": pts(et[least]["left"])}
                cands += [most, least]
                facts["bench_points_left"] = {"most": bench_f["bench_n"], "most_pts": bench_f["bench_pts"], "least": bench_f["bench_low_n"],
                                              "least_pts": bench_f["bench_low_pts"]}
            wr = max(((v["worst"][0], v["worst"][1], rid, v["worst"][2]) for rid, v in et.items() if v["worst"][2]),
                     key=lambda x: (x[0], -x[1], nm(x[2])), default=None)
            if wr and wr[0] > 0 and 0 < wr[3]["points"] <= wr[0]:   # a named bench player must fit inside the points left
                blunder_f = {"bl_n": nm(wr[2]), "bl_pts": pts(wr[0]), "bl_wk": str(wr[1]), "bl_player": wr[3]["name"],
                             "bl_pos": wr[3]["position"], "bl_player_pts": pts(wr[3]["points"])}
                cands.append(wr[2])
                facts["biggest_bench_blunder"] = {"owner": blunder_f["bl_n"], "week": wr[1], "points_left": blunder_f["bl_pts"],
                                                  "player": blunder_f["bl_player"], "position": blunder_f["bl_pos"], "player_points": blunder_f["bl_player_pts"]}

        steady_f = None
        if gp >= 3:
            spread = {}
            for x in order:
                ranks = [v for k, v in T[x]["weekly_rank"].items() if k <= S["week"]]
                if len(ranks) >= 3:
                    spread[x] = (pstdev(ranks), sum(ranks) / len(ranks), min(ranks), max(ranks))
            if len(spread) >= 2:
                st_x = min(spread, key=lambda x: (spread[x][0], nm(x)))
                wd_x = max(spread, key=lambda x: (spread[x][0], nm(x)))
                if st_x != wd_x and round(spread[st_x][0], 2) != round(spread[wd_x][0], 2):
                    def band(x):
                        lo_r, hi_r = spread[x][2], spread[x][3]
                        if lo_r == hi_r:
                            return f"{ordinal(lo_r)} every week"
                        return f"{ordinal(lo_r)} to {ordinal(hi_r)}"
                    steady_f = {"steady_n": nm(st_x), "steady_avg": f"{spread[st_x][1]:.1f}", "steady_band": band(st_x),
                                "wild_n": nm(wd_x), "wild_band": band(wd_x)}
                    cands += [st_x, wd_x]
                    facts["weekly_rank_consistency"] = {"steadiest": nm(st_x), "steadiest_average_rank": steady_f["steady_avg"],
                                                        "steadiest_range": steady_f["steady_band"], "wildest": nm(wd_x), "wildest_range": steady_f["wild_band"]}

        tg = self._trade_grades(S["week"])
        trade_f = None
        if tg:
            trade_f = {"lead": nm(tg["lead"]), "trail": nm(tg["trail"]), "lead_pts": pts(tg["lead_pts"]), "trail_pts": pts(tg["trail_pts"]),
                       "since_wk": plural(tg["since"], "week"), "twk": str(tg["twk"])}
            cands += [tg["lead"], tg["trail"]]
            facts["trade_early_returns"] = {"better_return": trade_f["lead"], "other_side": trade_f["trail"], "better_points": trade_f["lead_pts"],
                                            "other_points": trade_f["trail_pts"], "trade_week": tg["twk"], "weeks_since": tg["since"]}

        themes = [(k, wt) for k, wt, ok in (("luck", 3.0, luck_f), ("eff", 2.0, eff_f), ("bench", 2.0, bench_f), ("steady", 1.5, steady_f)) if ok]
        if not themes:
            return None
        theme = r.choices([t for t, _ in themes], weights=[wt for _, wt in themes])[0]
        head_f = {"luck": luck_f, "eff": eff_f, "bench": bench_f, "steady": steady_f}[theme]
        headline = w.head(f"h.a.{theme}", {**base, **head_f})

        w.add([w.line("a.lede", {**base, "gp": plural(gp, "game")}, repeat=True),
               w.line("a.luck", {**base, **luck_f}, repeat=True) if luck_f else None], {"analytics": True})
        w.add([w.line("a.eff", {**base, **eff_f}, repeat=True) if eff_f else None,
               w.line("a.bench", {**base, **bench_f}, repeat=True) if bench_f else None,
               w.line("a.blunder", {**base, **blunder_f}, repeat=True) if blunder_f else None], {"analytics": True})
        w.add([w.line("a.steady", {**base, **steady_f}, repeat=True) if steady_f else None,
               w.line("a.trade", {**base, **trade_f}, repeat=True) if trade_f else None], {"analytics": True})
        w.add([w.line("a.close", base, repeat=True)], {"analytics": True})
        dek_bits = [f"Through {wl}"]
        if luck_f:
            dek_bits.append(f"luckiest: {luck_f['lucky']} ({luck_f['lucky_luck']})")
        if eff_f:
            dek_bits.append(f"most efficient lineup: {eff_f['best_n']} ({eff_f['best_pct']})")
        elif bench_f:
            dek_bits.append(f"most bench points left: {bench_f['bench_n']} ({bench_f['bench_pts']})")
        dek = " · ".join(dek_bits)
        return self._article(w, "analytics", week, headline, dek, cands, ["analytics", f"week-{week}"], facts)
