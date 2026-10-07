"""Article builders for the weekly roundup, the weekly preview and the rivalry hype piece.

Every sentence comes from a family slot rendered with facts computed here from league data
(as-of the article's week). Nothing is written when the data does not support it.
"""
from __future__ import annotations

import random
from typing import Any

from .book import Book
from .engine import Writer
from .util import fmt, fmt1, join_and, mclass, ordinal, plural, polish, pts, signed, pct


class Beats(Book):
    def __init__(self, ctx, st, po, shotgun_items):
        super().__init__(ctx, st, po, shotgun_items)
        self._id = 0

    # ---- plumbing ----------------------------------------------------------
    def rng(self, *parts) -> random.Random:
        return random.Random(":".join(str(p) for p in (self.season, *parts)))

    def _article(self, w: Writer, kind: str, week: int, headline: str, dek: str, cand_teams: list[int],
                 tags: list[str], facts: dict, key_teams: list[int] | None = None) -> dict:
        body, metas = w.finish()
        headline = polish(headline, self.protected_rx())
        self.n_articles += 1
        self.n_catch += 1 if w.catch_used else 0
        text = " ".join(body)
        teams: list[int] = []
        for r in cand_teams:
            if r not in teams and self.name(r) in text:
                teams.append(r)
        self._id += 1
        v = w.voice
        facts = dict(facts)
        facts["beats"] = list(w.beats)
        facts["paras"] = metas
        facts["quotes"] = list(w.quote_log)
        # Stable key (desk overrides are matched on it): data only, never the reporter, the text or the build order.
        # One-per-week pieces (roundup, preview, Beer Report, ...) use "all"; pair pieces use the two roster ids.
        kt = "all" if key_teams is None else "-".join(sorted(map(str, key_teams)))
        return {"id": f"{self.season}-{kind}-{week}-{self._id}", "key": f"{self.season}:{kind}:{week}:{kt}", "type": kind,
                "week": week, "headline": headline, "dek": dek, "byline": f"{v.name}, {v.outlet}", "reporter": v.card(),
                "body": body, "teams": teams, "tags": tags, "facts": facts, "source": "template"}

    # ======================================================================
    # Weekly roundup
    # ======================================================================
    def game_facts(self, g: dict, week: int, info: dict) -> dict:
        wl = info["wl"]
        f: dict[str, Any] = {"wk": str(week), "wl": wl, "wavg": fmt(info["wavg"]), "_week": week}
        if g["winner"] is None:
            a, b = g["a"], g["b"]
            f.update(a=self.name(a), b=self.name(b), a_team=self.tname(a), b_team=self.tname(b),
                     pts=fmt(g["a_pts"]), mclass="tie", _a=a, _b=b, _margin=0.0)
            return f
        w = g["winner"]
        l = g["b"] if w == g["a"] else g["a"]
        wp = g["a_pts"] if w == g["a"] else g["b_pts"]
        lp = g["b_pts"] if w == g["a"] else g["a_pts"]
        mc = mclass(g["margin"])
        f.update(w=self.name(w), l=self.name(l), w_team=self.tname(w), l_team=self.tname(l),
                 w_nick=self.nickname(w), l_nick=self.nickname(l), wp=fmt(wp), lp=fmt(lp), m=fmt(g["margin"]),
                 mclass=mc, _w=w, _l=l, _wp=wp, _lp=lp, _margin=g["margin"])
        S1, S0 = info["S1"], info["S0"]
        if S1:
            tw, tl = S1["teams"][w], S1["teams"][l]
            f.update(w_rec=tw["record"], l_rec=tl["record"], w_rank=ordinal(tw["rank"]), l_rank=ordinal(tl["rank"]))
            f["_streak_w"] = tw["streak"]; f["_streak_l"] = tl["streak"]
            f["_wrank_w"] = tw["weekly_rank"].get(week); f["_wrank_l"] = tl["weekly_rank"].get(week)
            f["_luck_w"] = (tw["luck"], tw["games"], tw["record"]); f["_luck_l"] = (tl["luck"], tl["games"], tl["record"])
            if S0 and week >= 3:
                r0w, r0l = S0["teams"][w]["rank"], S0["teams"][l]["rank"]
                if r0w - r0l >= 3:
                    f.update(w_rank0=ordinal(r0w), l_rank0=ordinal(r0l))
                    f["_upset_gap"] = r0w - r0l
        star = self.best_starter(week, w)
        if star and wp > 0 and star["points"] > 0:
            share = star["points"] / wp
            f.update(star=star["name"], spos=star["position"], spts=pts(star["points"]), sshare=f"{round(share * 100)}%")
            if share > 0.5:     # superlatives like "more than the rest of the roster combined" need a real majority
                f["over_half"] = "more than the rest of the roster combined"
            else:
                f["part_note"] = "the biggest slice, with plenty left for the rest of the roster"
            if share < 0.5:
                f["elsewhere"] = "so most of the win came from elsewhere in the lineup"
        goat = self.worst_starter(week, l)
        if goat and goat["points"] <= 2:
            f.update(gname=goat["name"], gpos=goat["position"], gpts=pts(goat["points"]))
        left, best = self.bench_left(week, l)
        if left >= 15:
            f["bench_total"] = pts(left)
            # name a bench player only when his points fit inside the total the lineup left behind
            if best and 0 < best["points"] <= left:
                f.update(bench_left=pts(left), bench_name=best["name"], bench_pos=best["position"], bench_pts=pts(best["points"]))
        return f

    def _sg_phrase(self, items: list[dict]) -> str:
        players = [f"{s['player']['name']} ({s['player']['position']})" for s in items if s["reason"] in ("negative", "zero", "low")]
        empties = [f"an empty {s['slot']} slot" for s in items if s["reason"] == "empty_slot"]
        rules = [f"the {s['label']} rule" for s in items if s["reason"] == "rule"]
        groups = []
        if players:
            groups.append("starting " + join_and(players))
        if empties:
            groups.append(join_and(empties))
        if rules:
            groups.append(join_and(rules))
        return ", plus ".join(groups)

    def _extras(self, w: Writer, f: dict, week: int, budget: int, skip_upset: bool = False, skip_top: bool = False) -> list[str]:
        """Context sentences for one game, most notable first, within a budget."""
        playoff = f.get("w_rec") is None
        tier0: list[tuple[str, dict]] = []
        tier1: list[tuple[str, dict]] = []
        tier2: list[tuple[str, dict]] = []
        if f.get("w_rank0") and not skip_upset:
            tier0.append(("g.upset", f))
        for key, rid in (("w", f["_w"]), ("l", f["_l"])):
            its = self.sg_week(week, rid)
            if its:
                tier0.append(("g.shotgun", {**f, "n": f[key], "sgn": plural(len(its), "shotgun"), "why": self._sg_phrase(its)}))
        if f.get("bench_left"):
            tier1.append(("g.bench", f))
        elif f.get("bench_total"):
            tier1.append(("g.bench_total", {**f, "bench_left": f["bench_total"]}))
        sg_names = {s["player"]["name"] for rid in (f["_w"], f["_l"]) for s in self.sg_week(week, rid) if s.get("player")}
        if f.get("gname") and f["gname"] not in sg_names:   # a shotgun player is already named as the dud
            tier1.append(("g.goat", f))
        if f.get("star"):
            tier1.append(("g.star", f))
        if not playoff:
            kw, kl = f["_streak_w"], f["_streak_l"]
            if kw.startswith("W") and int(kw[1:]) >= 3:
                tier1.append(("g.streak_w", {**f, "k": kw[1:]}))
            if kl.startswith("L") and int(kl[1:]) >= 3:
                tier1.append(("g.streak_l", {**f, "k": kl[1:]}))
            if f["_wrank_w"] == 1 and not skip_top:    # the lede of a "top score" story has said it already
                tier1.append(("g.top", f))
            if f["_wrank_l"] == len(self.teams):
                tier1.append(("g.low", f))
            lucks = [(abs(v[0]), key, v) for key, v in (("w", f["_luck_w"]), ("l", f["_luck_l"])) if abs(v[0]) >= 1 and v[1] >= 3]
            if lucks:
                _, key, (lk, _, rec) = max(lucks, key=lambda x: x[0])
                tier2.append(("g.luck_up" if lk > 0 else "g.luck_down", {**f, "n": f[key], "luck": signed(lk), "luck_abs": f"{abs(lk):.1f}", "n_rec": rec}))
            tier2.append(("g.record", f))
        w.rng.shuffle(tier1)
        out: list[str] = []
        for slot, facts in tier0[:2] + tier1 + tier2:
            if len(out) >= budget:
                break
            s = w.line(slot, facts)
            if s:
                out.append(s)
        return out

    def _quotes_for(self, w: Writer, f: dict, who: str, week: int, sig: bool = False) -> str | None:
        """Boast (who='w') or lament (who='l') for a decided game of class blowout/comfortable/close."""
        mc = f["mclass"]
        if mc not in ("blowout", "comfortable", "close"):
            return None
        big = mc in ("blowout", "comfortable")
        base = {"m": f["m"], "wp": f["wp"], "lp": f["lp"], "wk": str(week)}
        if who == "w":
            return w.quote(f["_w"], "won_big" if big else "won_close", {**base, "opp": f["l"]}, sig_ok=sig)
        return w.quote(f["_l"], "lost_big" if big else "lost_close", {**base, "opp": f["w"]}, sig_ok=sig)

    def roundup(self, week: int, voice) -> dict | None:
        games = [g for g in self.games_by_week.get(week, []) if g["a"] in self.teams and g["b"] in self.teams]
        if not games:
            return None
        playoff = self.is_playoff(week)
        wl = f"playoff Week {week}" if playoff else f"Week {week}"
        S1 = None if playoff else self.snap(week)
        S0 = self.snap(week - 1) if (not playoff and week > 1) else None
        scores = [p for g in games for p in (g["a_pts"], g["b_pts"])]
        info = {"wl": wl, "wavg": sum(scores) / len(scores), "S1": S1, "S0": S0}
        gfs = [self.game_facts(g, week, info) for g in games]
        r = self.rng("roundup", week, voice.id)
        w = Writer(self, voice, r, "recap", week)

        # ---- the week's biggest story ----
        decided = [i for i, f in enumerate(gfs) if f["mclass"] != "tie"]
        ties = [i for i, f in enumerate(gfs) if f["mclass"] == "tie"]
        avail: dict[str, tuple[int, float]] = {}
        if ties:
            kind, story = "tie", ties[0]
        else:
            top = max(decided, key=lambda i: gfs[i]["_wp"])
            avail["top"] = (top, 1.0)
            big = max(decided, key=lambda i: gfs[i]["_margin"])
            if gfs[big]["_margin"] >= 30:
                avail["blowout"] = (big, 3.0)
            ups = [i for i in decided if gfs[i].get("w_rank0")]
            if ups:
                avail["upset"] = (max(ups, key=lambda i: gfs[i]["_upset_gap"]), 3.0)
            cl = min(decided, key=lambda i: gfs[i]["_margin"])
            if gfs[cl]["_margin"] < 7:
                avail["close"] = (cl, 2.5)
            kinds = list(avail)
            kind = r.choices(kinds, weights=[avail[k][1] for k in kinds])[0]
            story = avail[kind][0]
        slot_key = {"blowout": "blow", "upset": "upset", "close": "close", "top": "top", "tie": "tie"}[kind]
        sf = gfs[story]
        headline = w.head(f"h.r.{slot_key}", sf)

        def interest(i: int) -> float:
            f = gfs[i]
            base = {"blowout": 2.0, "comfortable": 1.0, "normal": 0.5, "close": 2.0, "tie": 3.0}[f["mclass"]]
            return base + (3.0 if f.get("w_rank0") else 0.0) + r.random() * 0.1
        order = [story] + sorted((i for i in range(len(gfs)) if i != story), key=lambda i: -interest(i))
        boost = 1 if len(games) <= 3 else 0    # a short playoff slate still gets a full-length roundup
        quoted_second = None
        for i in order[1:]:
            if gfs[i]["mclass"] in ("blowout", "comfortable", "close"):
                quoted_second = i
                break

        for rank_i, i in enumerate(order):
            f = gfs[i]
            sents: list[str | None] = []
            meta = {"game": i, "mclass": f["mclass"], "teams": [self.name(g) for g in (f["_a"], f["_b"])] if f["mclass"] == "tie" else [f["w"], f["l"]]}
            qsents: list[str | None] = []
            if rank_i == 0:
                sents.append(w.line(f"r.lede.{slot_key}", f, repeat=True))
                if f["mclass"] != "tie":
                    sents.extend(self._extras(w, f, week, 2 + boost, skip_upset=(slot_key == "upset"), skip_top=(slot_key == "top")))
                    sents.append(w.aside(f["_l"], f"a {f['m']}-point loss to {f['w']}", wl, str(week)))
                    qsents = [self._quotes_for(w, f, "w", week, True), self._quotes_for(w, f, "l", week, True)]
                else:
                    for key, rid in (("a", f["_a"]), ("b", f["_b"])):
                        its = self.sg_week(week, rid)
                        if its:
                            sents.append(w.line("g.shotgun", {**f, "n": f[key], "sgn": plural(len(its), "shotgun"), "why": self._sg_phrase(its)}))
                    qsents = [w.quote(f["_a"], "tied", {"opp": f["b"], "pts": f["pts"], "wk": str(week)}, sig_ok=True),
                              w.quote(f["_b"], "tied", {"opp": f["a"], "pts": f["pts"], "wk": str(week)}, sig_ok=True)]
            elif f["mclass"] == "tie":
                sents.append(w.line("g.tie", f, repeat=True))
            else:
                sents.append(w.line("g.result", f, repeat=True,
                                    prefer=("noun", "m") if f["mclass"] in ("blowout", "close") else ()))
                budget = (3 if (f["mclass"] in ("blowout", "close") or f.get("w_rank0")) else 2) + boost
                sents.extend(self._extras(w, f, week, budget))
                if i == quoted_second:
                    sents.append(self._quotes_for(w, f, "w", week))
            w.add(sents, meta)
            if qsents:
                w.add(qsents, {"mclass": f["mclass"], "quotes": True})

        # ---- closer: the standings shift ----
        n_po = self.ctx["playoff_teams"]
        close_facts: dict[str, Any] = {"wl": wl, "wk": str(week)}
        shift = None
        if playoff:
            top_i = max(decided, key=lambda i: gfs[i]["_wp"]) if decided else None
            big_i = max(decided, key=lambda i: gfs[i]["_margin"]) if decided else None
            if top_i is not None and big_i is not None:
                close_facts.update(top_w=gfs[top_i]["w"], top_pts=gfs[top_i]["wp"], big_w=gfs[big_i]["w"],
                                   big_l=gfs[big_i]["l"], big_m=gfs[big_i]["m"], ngames=plural(len(games), "game"))
                w.add([w.line("r.close_po", close_facts, repeat=True)], {"mclass": None})
        else:
            st1 = S1["standings"]
            leader = st1[0]
            cut = st1[n_po - 1] if len(st1) >= n_po else st1[-1]
            close_facts.update(leader=self.name(leader), leader_rec=S1["teams"][leader]["record"],
                               cut=self.name(cut), cut_rec=S1["teams"][cut]["record"])
            if S0:
                before, after = set(S0["standings"][:n_po]), set(st1[:n_po])
                ins = [x for x in st1[:n_po] if x not in before]
                outs = [x for x in S0["standings"][:n_po] if x not in after]
                if ins and outs:
                    shift = {"in": [self.name(x) for x in ins], "out": [self.name(x) for x in outs]}
                    close_facts.update(in_names=join_and(shift["in"]), out_names=join_and(shift["out"]))
            sent = w.line("r.close_shift", close_facts, repeat=True) if shift else w.line("r.close_table", close_facts, repeat=True)
            w.add([sent], {"mclass": None})

        top_i = max(decided, key=lambda i: gfs[i]["_wp"]) if decided else None
        big_i = max(decided, key=lambda i: gfs[i]["_margin"]) if decided else None
        parts = [f"{wl[:1].upper() + wl[1:]}: {plural(len(games), 'game')}"]
        if big_i is not None:
            parts.append(f"biggest margin {gfs[big_i]['m']} ({gfs[big_i]['w']} over {gfs[big_i]['l']})")
        if top_i is not None:
            parts.append(f"high score {gfs[top_i]['wp']} ({gfs[top_i]['w']})")
        dek = " · ".join(parts)
        facts = {"type": "recap", "week": week, "label": wl, "playoff": playoff, "story": {"kind": kind, "game": story},
                 "games": [self._compact_game(f, week) for f in gfs], "standings_shift": shift,
                 "league_avg_this_week": fmt(info["wavg"])}
        cand = [t for f in gfs for t in ((f["_a"], f["_b"]) if f["mclass"] == "tie" else (f["_w"], f["_l"]))]
        return self._article(w, "recap", week, headline, dek, cand, ["recap", f"week-{week}"], facts)

    def _compact_game(self, f: dict, week: int) -> dict:
        if f["mclass"] == "tie":
            return {"result": "tie", "teams": [f["a"], f["b"]], "points_each": f["pts"], "shotguns": self._sg_names(week, [f["_a"], f["_b"]])}
        out = {k: f[k] for k in ("w", "l", "wp", "lp", "m", "mclass", "w_rec", "l_rec", "w_rank", "l_rank", "w_rank0", "l_rank0",
                                  "star", "spos", "spts", "sshare", "gname", "gpos", "gpts", "bench_left", "bench_total", "bench_name", "bench_pos", "bench_pts") if f.get(k)}
        out["shotguns"] = self._sg_names(week, [f["_w"], f["_l"]])
        return {("winner" if k == "w" else "loser" if k == "l" else "winner_score" if k == "wp" else "loser_score" if k == "lp"
                 else "margin" if k == "m" else k): v for k, v in out.items()}

    def _sg_names(self, week: int, rids: list[int]) -> list[dict]:
        out = []
        for rid in rids:
            its = self.sg_week(week, rid)
            if its:
                out.append({"owner": self.name(rid), "count": len(its), "why": self._sg_phrase(its)})
        return out

    # ======================================================================
    # Preview
    # ======================================================================
    def _pv(self, rid: int, S: dict) -> dict:
        t = self.teams[rid]
        po = (self.po.get("teams") or {}).get(rid) or {}
        ng = po.get("next_game") or {}
        return {"rid": rid, "name": self.name(rid), "team": self.tname(rid), "rec": S["teams"][rid]["record"],
                "avg": fmt1(t["avg"]), "avg_v": t["avg"], "std": t["std"], "rank": S["teams"][rid]["rank"],
                "pct": po.get("playoff_pct"), "if_win": ng.get("if_win"), "if_loss": ng.get("if_loss")}

    def _favorite(self, A: dict, B: dict) -> tuple[dict | None, dict | None, str | None]:
        if A["pct"] is not None and B["pct"] is not None and round(A["pct"] * 100) != round(B["pct"] * 100):
            fav, dog, why = (A, B, "playoff odds") if A["pct"] > B["pct"] else (B, A, "playoff odds")
        elif A["avg_v"] != B["avg_v"]:
            fav, dog, why = (A, B, "scoring average") if A["avg_v"] > B["avg_v"] else (B, A, "scoring average")
        else:
            return None, None, None
        return fav, dog, why

    def _swing(self, A: dict, B: dict) -> float:
        s = 0.0
        for x in (A, B):
            if x["if_win"] is not None and x["if_loss"] is not None:
                s += abs(x["if_win"] - x["if_loss"])
        return s

    def _trash(self, w: Writer, me: dict, opp: dict, games: list[dict], upto: int, h2h: bool = True,
               sig: bool = False) -> tuple[str, str | None]:
        """Pick a trash-talk quote for `me` aimed at `opp` that only claims what the data supports."""
        hh = self.h2h_games(me["rid"], opp["rid"], upto) if h2h else []
        wins = sum(1 for g in hh if g["winner"] == me["rid"])
        losses = sum(1 for g in hh if g["winner"] == opp["rid"])
        if wins > losses:
            sit, facts = "trash_h2h_lead", {"opp": opp["name"], "h2h": f"{wins}-{losses}"}
        elif losses > wins:
            sit, facts = "trash_h2h_trail", {"opp": opp["name"], "h2h": f"{wins}-{losses}"}
        elif me["rank"] < opp["rank"]:
            sit, facts = "trash_standings", {"opp": opp["name"], "rank": ordinal(me["rank"]), "opp_rank": ordinal(opp["rank"])}
        elif (me["pct"] is not None and opp["pct"] is not None and round(me["pct"] * 100) < round(opp["pct"] * 100)):
            sit, facts = "trash_underdog", {"opp": opp["name"]}    # "spoiler" talk only from the side with the worse odds
        else:
            sit, facts = "trash_even", {"opp": opp["name"]}
        return sit, w.quote(me["rid"], sit, facts, sig_ok=sig)

    def _exchange(self, w: Writer, A: dict, B: dict, upto: int, h2h: bool = True, sig: bool = False) -> list[str | None]:
        """A trash-talks B; B either denies (right after the trash) or trashes back."""
        sit, qa = self._trash(w, A, B, [], upto, h2h, sig)
        if qa is None:
            return []
        if w.rng.random() < 0.4:
            qb = w.quote(B["rid"], "deny_after_trash", {"opp": A["name"]}, sig_ok=sig)
        else:
            qb = self._trash(w, B, A, [], upto, h2h, sig)[1]
        return [qa, qb]

    def _h2h_line(self, w: Writer, A: dict, B: dict, upto: int) -> str | None:
        hh = self.h2h_games(A["rid"], B["rid"], upto)
        if not hh:
            return w.line("p.h2h_none", {"a": A["name"], "b": B["name"]}, repeat=True)
        wa = sum(1 for g in hh if g["winner"] == A["rid"])
        wb = sum(1 for g in hh if g["winner"] == B["rid"])
        ties = len(hh) - wa - wb
        tail = f"-{ties}" if ties else ""
        if wa == wb:
            return w.line("p.h2h_split", {"a": A["name"], "b": B["name"], "h2h_rec": f"{wa}-{wb}{tail}"}, repeat=True)
        lead, trail = (A, B) if wa > wb else (B, A)
        return w.line("p.h2h_lead", {"lead": lead["name"], "trail": trail["name"], "h2h_rec": f"{max(wa, wb)}-{min(wa, wb)}{tail}"}, repeat=True)

    def preview(self, week: int, voice) -> dict | None:
        games = self.st["schedule"].get(week) or []
        last = self.ctx["last_completed"]
        if not games or last < 1 or not (self.po.get("teams")):
            return None
        S = self.snap(last)
        wl = f"Week {week}"
        r = self.rng("preview", week, voice.id)
        w = Writer(self, voice, r, "preview", week)
        n_po = self.ctx["playoff_teams"]
        rows = []
        for g in games:
            A, B = self._pv(g["a"], S), self._pv(g["b"], S)
            fav, dog, why = self._favorite(A, B)
            rows.append({"g": g, "A": A, "B": B, "fav": fav, "dog": dog, "why": why, "swing": self._swing(A, B),
                         "rv": self.rivalry_between(g["a"], g["b"])})

        def gotw_key(x):
            pa, pb = x["A"]["pct"] or 0, x["B"]["pct"] or 0
            return (x["swing"], pa + pb)
        gotw = max(rows, key=gotw_key)
        order = [gotw] + [x for x in rows if x is not gotw]

        def gfacts(x: dict) -> dict:
            A, B = x["A"], x["B"]
            f = {"a": A["name"], "b": B["name"], "a_team": A["team"], "b_team": B["team"], "a_rec": A["rec"], "b_rec": B["rec"],
                 "a_avg": A["avg"], "b_avg": B["avg"], "wk": str(week), "wl": wl,
                 "a_odds": pct(A["pct"]), "b_odds": pct(B["pct"])}
            if x["swing"] > 0.5:
                f["swing"] = str(round(x["swing"] * 100))
            if A["if_win"] is not None and A["if_loss"] is not None:
                f.update(a_win=pct(A["if_win"]), a_loss=pct(A["if_loss"]))
            if B["if_win"] is not None and B["if_loss"] is not None:
                f.update(b_win=pct(B["if_win"]), b_loss=pct(B["if_loss"]))
            if x["fav"]:
                f.update(fav=x["fav"]["name"], dog=x["dog"]["name"], fav_odds=pct(x["fav"]["pct"]), dog_odds=pct(x["dog"]["pct"]),
                         fav_why=x["why"])
            return f

        gf = gfacts(gotw)
        gap = abs((gotw["A"]["pct"] or 0) - (gotw["B"]["pct"] or 0)) * 100
        if gotw["swing"] > 0.5:
            bucket, head_fav = "lev", None
        elif gotw["fav"] and gap >= 10:
            bucket, head_fav = "fav", gotw["fav"]["name"]
        else:
            bucket, head_fav = "even", None
        headline = w.head(f"h.p.{bucket}", gf)

        for k, x in enumerate(order):
            A, B = x["A"], x["B"]
            f = gfacts(x)
            meta = {"game": k, "teams": [A["name"], B["name"]], "favorite": x["fav"]["name"] if x["fav"] else None}
            s: list[str | None] = []
            if k == 0:
                s.append(w.line("p.lede", f, repeat=True))
            s.append(w.line("p.matchup", f, repeat=True))
            s.append(self._h2h_line(w, A, B, last))
            if k == 0:
                s.append(w.line("p.stakes", f))
                if x["swing"] > 0.5:
                    s.append(w.line("p.leverage", f))
            else:
                s.append(w.line("p.stakes", f) if r.random() < 0.5 else None)
            if x["fav"]:
                s.append(w.line("p.favorite", f, repeat=True))
            va, vb = A["std"], B["std"]
            if (k == 0 or r.random() < 0.4) and va and vb and va != vb:
                hi, lo = (A, B) if va > vb else (B, A)
                s.append(w.line("p.vol", {**f, "vol_n": hi["name"], "vol_std": fmt1(hi["std"]), "other": lo["name"], "other_std": fmt1(lo["std"])}))
            if x["rv"]:
                s.append(w.line("p.rivnote", {**f, "rv_name": x["rv"]["name"], "backstory": x["rv"]["backstory"].strip()}))
            if k == 0:
                s.extend(self._exchange(w, A, B, last, sig=True))
            else:   # every game gets at least one quote
                first, second = (A, B) if r.random() < 0.5 else (B, A)
                q = self._trash(w, first, second, [], last)[1] or self._trash(w, second, first, [], last)[1]
                s.append(q)
            if k == 0:
                s.append(w.line("p.close", f))
            w.add(s, meta)

        dek = f"{wl}: {plural(len(games), 'game')} · game of the week: {gotw['A']['name']} ({gotw['A']['rec']}) vs. {gotw['B']['name']} ({gotw['B']['rec']})"
        facts = {"type": "preview", "week": week, "favorite": gotw["fav"]["name"] if gotw["fav"] else None,
                 "headline_favorite": head_fav, "game_of_the_week": [gotw["A"]["name"], gotw["B"]["name"]],
                 "games": [{"teams": [x["A"]["name"], x["B"]["name"]], "records": [x["A"]["rec"], x["B"]["rec"]],
                            "avg_ppg": [x["A"]["avg"], x["B"]["avg"]],
                            "playoff_odds": [pct(x["A"]["pct"]), pct(x["B"]["pct"])],
                            "favorite": x["fav"]["name"] if x["fav"] else None, "favorite_basis": x["why"],
                            "swing_points": round(x["swing"] * 100), "rivalry": x["rv"]["name"] if x["rv"] else None}
                           for x in order]}
        cand = [t for x in order for t in (x["A"]["rid"], x["B"]["rid"])]
        return self._article(w, "preview", week, headline, dek, cand, ["preview", f"week-{week}"], facts)

    # ======================================================================
    # Rivalry hype
    # ======================================================================
    def rivalry_hype(self, week: int, g: dict, voice) -> dict | None:
        rv = self.rivalry_between(g["a"], g["b"])
        last = self.ctx["last_completed"]
        if not rv or last < 1:
            return None
        S = self.snap(last)
        a, b = rv["owners"]
        A, B = self._pv(a, S), self._pv(b, S)
        r = self.rng("rivalry", week, rv["name"])
        w = Writer(self, voice, r, "rivalry", week)
        f = {"a": A["name"], "b": B["name"], "rv_name": rv["name"], "backstory": rv["backstory"].strip(), "wk": str(week),
             "wl": f"Week {week}", "a_rec": A["rec"], "b_rec": B["rec"], "a_avg": A["avg"], "b_avg": B["avg"],
             "a_rank": ordinal(A["rank"]), "b_rank": ordinal(B["rank"])}
        headline = w.head("h.v", f)
        s1 = [w.line("v.lede", f, repeat=True), w.line("v.form", f, repeat=True)]
        w.add(s1, {"teams": [A["name"], B["name"]]})
        fav, dog, why = self._favorite(A, B)
        s2 = [self._h2h_line(w, A, B, last)]
        if fav:
            s2.append(w.line("p.favorite", {**f, "fav": fav["name"], "dog": dog["name"], "fav_odds": pct(fav["pct"]),
                                            "dog_odds": pct(dog["pct"]), "fav_why": why}))
        w.add(s2, {"teams": [A["name"], B["name"]]})
        w.add(self._exchange(w, A, B, last) + [w.line("v.close", f, repeat=True)], {"teams": [A["name"], B["name"]]})
        facts = {"type": "rivalry", "week": week, "rivalry": rv["name"], "backstory": rv["backstory"],
                 "teams": [A["name"], B["name"]], "records": [A["rec"], B["rec"]], "avg_ppg": [A["avg"], B["avg"]],
                 "favorite": fav["name"] if fav else None}
        return self._article(w, "rivalry", week, headline, rv["name"], [a, b], ["rivalry", f"week-{week}"], facts, key_teams=[a, b])
