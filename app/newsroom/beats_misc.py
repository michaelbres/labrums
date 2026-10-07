"""Article builders: trade, waiver, Beer Report, standings, feud, offseason."""
from __future__ import annotations

from typing import Any

from ..loader import is_offseason
from .beats import Beats
from .engine import BUSY_RX, Writer
from .util import fmt, fmt1, join_and, mclass, num_word, ordinal, ord_word, pct, plural, pts, signed, times


WAIVER_HI = 15.0    # points since the claim: at or above, a good pickup
WAIVER_MID = 5.0    # at or above (and below HI), a middling one; below, a miss


def sg_words(n: int) -> str:
    return f"{num_word(n)} shotgun" + ("" if n == 1 else "s")


def short_side(players: list, picks: list, n_picks: int | None = None) -> str:
    n = len(picks) if n_picks is None else n_picks
    if len(players) == 1 and not n:
        return players[0]
    if n == 1 and not players:
        return picks[0]
    if n and not players and len(picks) == 1:
        return picks[0]       # one collapsed line: "two 2026 round 2 picks"
    parts = []
    if players:
        parts.append(plural(len(players), "player"))
    if n:
        parts.append(plural(n, "pick"))
    return " and ".join(parts)


class Beats2(Beats):
    # ======================================================================
    # Trades
    # ======================================================================
    def trade_info(self, tx: dict, week: int) -> dict | None:
        rids = [int(x) for x in tx.get("roster_ids") or [] if int(x) in self.teams]
        if len(rids) != 2:
            return None  # a 3-team deal is not summarized as a 2-team one
        a, b = rids
        got = self.tx_desc(tx)
        ga, gb = got.get(a), got.get(b)
        if not ga or not gb or not (ga["players"] or ga["picks"]) or not (gb["players"] or gb["picks"]):
            return None
        first = self.first_week_after(tx, week)   # a deal made before the week's games counts that week's points
        weeks = len(self.counted_weeks(first))
        since = {a: round(sum(self.points_from(p, first, a) for p in ga["pids"]), 2),
                 b: round(sum(self.points_from(p, first, b) for p in gb["pids"]), 2)}
        graded = bool(ga["players"] and gb["players"] and weeks >= 1 and since[a] != since[b])
        lead = trail = None
        if graded:
            lead, trail = (a, b) if since[a] > since[b] else (b, a)

        def plain(g: dict) -> str:
            names = [self.label(p)["name"] for p in g["pids"]]
            return join_and(names + g["picks"])
        return {"a": a, "b": b, "got": {a: ga, b: gb}, "text": {a: join_and(ga["players"] + ga["picks"]), b: join_and(gb["players"] + gb["picks"])},
                "plain": {a: plain(ga), b: plain(gb)}, "weeks": weeks, "since": since, "graded": graded,
                "lead": lead, "trail": trail, "week": week, "tx": tx.get("transaction_id"), "first": first, "raw": tx}

    def trade(self, tx: dict, week: int, voice) -> dict | None:
        T = self.trade_info(tx, week)
        if not T:
            return None
        a, b = T["a"], T["b"]
        r = self.rng("trade", week, T["tx"], voice.id)
        w = Writer(self, voice, r, "trade", week)
        nar = w.active(a, b)
        ga, gb = T["got"][a], T["got"][b]
        f = {"a": self.name(a), "b": self.name(b), "a_got": T["text"][a], "b_got": T["text"][b], "wk": str(week), "wl": f"Week {week}",
             "gave_s": short_side(gb["players"], gb["picks"], gb["n_picks"]), "got_s": short_side(ga["players"], ga["picks"], ga["n_picks"])}
        headline = w.head("h.t", f)
        w.add([w.line("t.sides", f, repeat=True)], {"trade": True})
        # early returns: only when both sides received a player and a week has passed
        if T["graded"]:
            lead, trail = T["lead"], T["trail"]
            ret = {**f, "a_pts": pts(T["since"][a]), "b_pts": pts(T["since"][b]), "lead": self.name(lead), "trail": self.name(trail),
                   "lead_pts": pts(T["since"][lead]), "trail_pts": pts(T["since"][trail]), "since_wk": plural(T["weeks"], "week")}
            ret["sample_note"] = "the sample is small" if T["weeks"] <= 3 else "the sample is growing"   # "small" only for 3 weeks or fewer
            s_ret = w.line("t.returns", ret, repeat=True)
        else:
            picks_only = [x for x in (a, b) if T["got"][x]["picks"] and not T["got"][x]["players"]]
            players_side = [x for x in (a, b) if T["got"][x]["players"]]
            if T["weeks"] >= 1 and len(picks_only) == 1 and len(players_side) == 1:
                pk, pl = picks_only[0], players_side[0]
                s_ret = w.line("t.pending", {"pk_side": self.name(pk), "pl_side": self.name(pl), "pk_got": T["text"][pk], "pl_got": T["text"][pl]}, repeat=True)
            else:
                s_ret = w.line("t.fresh", f, repeat=True)
        # league reaction, grounded in real counts and records
        counts = {x: self.moves_before(x, tx, week) for x in (a, b)}
        busy = max((a, b), key=lambda x: (counts[x]["trades"], counts[x]["trades"] + counts[x]["claims"]))
        s_cnt = None
        if counts[busy]["trades"] >= 1:
            total = counts[busy]["trades"] + counts[busy]["claims"]
            cf = {"n": self.name(busy), "nth": ord_word(counts[busy]["trades"])}
            if total > counts[busy]["trades"]:
                cf["moves"] = plural(total, "in-season move")
            s_cnt = w.line("t.count", cf, avoid=BUSY_RX if counts[busy]["trades"] < 3 else None)   # a first trade is not "busy"
        s_rec = None
        rw = self.records_week(tx, week)   # the standings "before the deal": through the week if it was already played
        if rw >= 1:
            S = self.snap(rw)
            if S["teams"][a]["games"] >= 1:
                s_rec = w.line("t.rec", {"a": f["a"], "b": f["b"], "a_rec": S["teams"][a]["record"], "b_rec": S["teams"][b]["record"],
                                         "a_rank": ordinal(S["teams"][a]["rank"]), "b_rank": ordinal(S["teams"][b]["rank"])})
        hy = None
        for x in (a, b):
            for pid in T["got"][x]["pids"]:
                hy = hy or w.hype(self.label(pid)["name"], f"changed hands in this trade, landing with {self.name(x)}")
        w.add([s_ret, s_cnt, s_rec, hy], {"trade": True})
        # quotes: the happy / defensive lines go to whoever actually has the better / worse early return
        qs: list[str | None] = []
        for x, y in ((a, b), (b, a)):
            qf = {"opp": self.name(y), "gave": T["plain"][y], "got": T["plain"][x]}
            if T["graded"]:
                sit = "trade_got_more" if x == T["lead"] else "trade_gave_more"
            else:
                sit = "trade_pending"
            qs.append(w.quote(x, sit, qf, sig_ok=True))
        if T["graded"] and r.random() < 0.5:
            qs = qs[:1] if T["lead"] == a else qs[1:]
        w.add(qs + [w.line("t.close", f, repeat=True)], {"trade": True})
        w.add_theme(nar)
        dek = f"{self.name(a)} receives {short_side(ga['players'], ga['picks'], ga['n_picks'])}; {self.name(b)} receives {short_side(gb['players'], gb['picks'], gb['n_picks'])}"
        facts = {"type": "trade", "week": week, "teams": [self.name(a), self.name(b)],
                 "received": {self.name(a): ga["players"] + ga["picks"], self.name(b): gb["players"] + gb["picks"]},
                 "points_since": {self.name(a): T["since"][a], self.name(b): T["since"][b]}, "weeks_since": T["weeks"],
                 "graded": T["graded"], "better_early_return": self.name(T["lead"]) if T["lead"] else None,
                 "trade_counts": {self.name(x): counts[x] for x in (a, b)}}
        art = self._article(w, "trade", week, headline, dek, [a, b], ["trade", f"week-{week}"], facts, key_teams=[a, b])
        art["_created"] = tx.get("created")   # generate() turns this into publish_on and removes it
        art["_txid"] = str(tx.get("transaction_id") or "")
        return art

    # ======================================================================
    # Waivers
    # ======================================================================
    def waiver_moves(self, week: int) -> list[dict]:
        moves = []
        for tx in self.live_txs(week):
            if tx.get("type") not in ("waiver", "free_agent"):
                continue
            rids = [int(x) for x in tx.get("roster_ids") or []]
            if not rids or rids[0] not in self.teams:
                continue
            bid = (tx.get("settings") or {}).get("waiver_bid")
            first = self.first_week_after(tx, week)
            n_weeks = len(self.counted_weeks(first))
            for pid, to in (tx.get("adds") or {}).items():
                if int(to) not in self.teams:
                    continue
                lab = self.label(pid)
                moves.append({"rid": int(to), "pid": pid, "name": lab["name"], "pos": lab["position"],
                              "bid": int(bid) if bid else 0, "since": self.points_from(pid, first, int(to)), "weeks": n_weeks})
        moves.sort(key=lambda m: (-m["bid"], -m["since"], m["name"]))
        return moves

    def waivers(self, week: int, voice) -> dict | None:
        moves = self.waiver_moves(week)
        if not moves:
            return None
        r = self.rng("waiver", week, voice.id)
        w = Writer(self, voice, r, "waiver", week)
        top = moves[0]
        nar = w.active(top["rid"])
        budget = float(self.ctx["settings"].get("waiver_budget") or 100)
        weeks = top["weeks"]
        f = {"n": self.name(top["rid"]), "player": top["name"], "pos": top["pos"], "wk": str(week), "wl": f"Week {week}"}
        if top["bid"]:
            f["bid"] = f"${top['bid']}"
            bucket = "big" if top["bid"] >= 0.2 * budget else "small"
            hs = f"h.w.{bucket}"
        else:
            hs = "h.w.free"
        headline = w.head_slanted(nar, "h.sl.any", {"n": f["n"], "wl": f["wl"], "wk": f["wk"]}) if nar else None
        if headline is None:
            headline = w.head(hs, f)
        s1 = [w.line("w.top_bid" if top["bid"] else "w.top_free", f, repeat=True)]
        if weeks >= 1:
            tier = "hi" if top["since"] >= WAIVER_HI else "mid" if top["since"] >= WAIVER_MID else "lo"
            s1.append(w.line("w.since", {**f, "spts": pts(top["since"]), "tier": tier, "since_wk": plural(weeks, "week")}))
        w.add(s1, {"waiver": True})
        others = moves[1:5]
        s2: list[str | None] = []
        if others:
            by_owner: dict[int, list[dict]] = {}
            for m in others:
                by_owner.setdefault(m["rid"], []).append(m)
            txt = join_and([f"{self.name(rid)} added " + join_and([f"{m['name']} ({m['pos']})" + (f" for ${m['bid']}" if m["bid"] else "") for m in ms])
                            for rid, ms in by_owner.items()])
            s2.append(w.line("w.others", {"others_text": txt, "n_other": str(len(others))}))
        s2.append(w.line("w.total", {**f, "total_n": plural(len(moves), "player"), "total_owners": plural(len({m['rid'] for m in moves}), "owner")}))
        for m in moves[:5]:   # a hype narrative: its player is one of the pickups
            who = self.name(m["rid"])
            s2.append(w.hype(m["name"], f"has scored {pts(m['since'])} for {who} since the claim" if m["weeks"] >= 1
                             else f"was one of the week's pickups, added by {who}"))
        t = self.teams[top["rid"]]
        if week == self.ctx["last_completed"] and t.get("waiver_budget_used") is not None:
            s2.append(w.line("w.budget", {"n": f["n"], "spent": f"${t['waiver_budget_used']}", "budget": f"${int(budget)}"}))
        w.add(s2, {"waiver": True})
        qf = {"player": top["name"], "pos": top["pos"]}
        if top["bid"]:
            qf["bid"] = f["bid"]
        # the quote must fit how the claim has actually gone: brag / shrug / defend / "too early"
        if weeks < 1:
            qsit = "waiver_pending"
        elif top["since"] >= WAIVER_HI:
            qsit = "waiver_brag"
        elif top["since"] >= WAIVER_MID:
            qsit = "waiver_neutral"
        else:
            qsit = "waiver_miss"
        if weeks >= 1:
            qf["spts"] = pts(top["since"])
        w.add([w.quote(top["rid"], qsit, qf), w.line("w.close", f, repeat=True)], {"waiver": True})
        w.add_theme(nar)
        dek = f"{plural(len(moves), 'add')} · top move: {f['n']} adds {top['name']} ({top['pos']})" + (f" for {f['bid']}" if top["bid"] else "")
        facts = {"type": "waiver", "week": week, "top": {"owner": f["n"], "player": top["name"], "pos": top["pos"], "bid": top["bid"] or None,
                                                       "points_since": top["since"] if weeks >= 1 else None},
                 "adds": [{"owner": self.name(m["rid"]), "player": m["name"], "pos": m["pos"], "bid": m["bid"] or None} for m in moves[:8]],
                 "total_adds": len(moves)}
        return self._article(w, "waiver", week, headline, dek, [m["rid"] for m in moves], ["waivers", f"week-{week}"], facts)

    # ======================================================================
    # Beer Report
    # ======================================================================
    def _sg_list(self, items: list[dict]) -> str:
        parts = []
        for s in items:
            if s["reason"] == "rule":
                d = s.get("detail", "")
                ref = self.rule_ref(s["label"])
                parts.append(f"{ref} ({d[:1].lower() + d[1:]})" if d else ref)
            elif s["reason"] == "empty_slot":
                parts.append(f"an empty {s['slot']} slot")
            else:
                parts.append(f"{s['player']['name']} ({s['player']['position']}, {fmt(s['points'])})")
        return join_and(parts)

    def beer_report(self, week: int, voice) -> dict | None:
        items = self.sg_week(week)
        if not items:
            return None
        r = self.rng("shotgun", week, voice.id)
        w = Writer(self, voice, r, "shotgun", week)
        per: dict[int, list[dict]] = {}
        for s in items:
            per.setdefault(s["roster_id"], []).append(s)
        ranked = sorted(per.items(), key=lambda kv: (-len(kv[1]), self.name(kv[0])))
        top_rid, top_items = ranked[0]
        nar = w.active(top_rid)
        f = {"total_n": plural(len(items), "shotgun"), "owners_n": plural(len(per), "owner"), "top": self.name(top_rid),
             "topn": plural(len(top_items), "shotgun"), "top_times": times(len(top_items)), "wk": str(week), "wl": f"Week {week}"}
        headline = w.head_slanted(nar, "h.sl.any", {"n": self.name(top_rid), "wl": f["wl"], "wk": f["wk"]}) if nar else None
        if headline is None:
            headline = w.head("h.s", f)
        w.add([w.line("s.total", f, repeat=True)], {"shotgun": True})
        lines = []
        for rid, its in ranked:
            lines.append(w.line("s.owner", {"n": self.name(rid), "sgn": plural(len(its), "shotgun"), "sgn_times": times(len(its)), "list": self._sg_list(its), "wk": str(week)}, repeat=True))
        w.add(lines, {"shotgun": True})
        extra: list[str | None] = []
        neg = [s for s in items if s["reason"] == "negative"]
        if neg:
            worst = min(neg, key=lambda s: s["points"])
            extra.append(w.line("s.low", {"n": self.name(worst["roster_id"]), "player": worst["player"]["name"], "pos": worst["player"]["position"],
                                          "pts": pts(worst["points"]), "wk": str(week)}))
        counts = self.sg_counts(week)
        order = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        leader = None
        if order and (len(order) == 1 or order[0][1] > order[1][1]):
            leader = order[0]
            extra.append(w.line("s.leader", {"leader": self.name(leader[0]), "ltotal": plural(leader[1], "shotgun"), "wk": str(week)}))
        w.add(extra, {"shotgun": True})
        # the quote must match what the speaker actually owes
        all_rule = all(s["reason"] == "rule" for s in top_items)
        qf: dict[str, Any] = {"sgn": sg_words(len(top_items))}
        if all_rule:
            qf["rule"] = self.rule_ref(top_items[0]["label"], "\u2018\u2019")[4:-5]
            sit = "rule_owed"
        else:
            sit = "shotgun_owed"
            if len(top_items) == 1 and top_items[0]["reason"] in ("negative", "zero", "low"):
                qf["player"] = top_items[0]["player"]["name"]
        w.add([w.quote(top_rid, sit, qf, multi=len(top_items) >= 2, sig_ok=True), w.line("s.close", f, repeat=True)], {"shotgun": True})
        w.add_theme(nar)
        dek = f"{plural(len(items), 'shotgun')} owed across {plural(len(per), 'owner')} · {self.name(top_rid)} leads with {len(top_items)}"
        facts = {"type": "shotgun", "week": week, "total": len(items),
                 "owners": [{"owner": self.name(rid), "count": len(its), "items": [{"reason": s["reason"], "player": s["player"]["name"], "pos": s["player"]["position"],
                                                                                    "points": s["points"], "label": s["label"]} for s in its]} for rid, its in ranked],
                 "season_leader": {"owner": self.name(leader[0]), "total": leader[1]} if leader else None}
        return self._article(w, "shotgun", week, headline, dek, [rid for rid, _ in ranked] + ([leader[0]] if leader else []),
                             ["shotguns", f"week-{week}"], facts)

    # ======================================================================
    # Standings
    # ======================================================================
    def standings_watch(self, week: int, voice) -> dict | None:
        if week < 1 or len(self.teams) < 4 or not self.po.get("teams"):
            return None
        final = self.regular_over()
        S = self.snap(self.final_reg_week if final else week)
        order = S["standings"]
        n_po = self.ctx["playoff_teams"]
        r = self.rng("standings", week, voice.id)
        w = Writer(self, voice, r, "standings", week)
        po = self.po["teams"]
        T = S["teams"]
        wl = f"Week {S['week']}"
        nm = self.name
        bottom = order[-1]
        lucky = max(order, key=lambda x: T[x]["luck"])
        unlucky = min(order, key=lambda x: T[x]["luck"])
        luck_f = None
        if T[lucky]["luck"] >= 1 and T[unlucky]["luck"] <= -1:
            luck_f = {"lucky": nm(lucky), "lucky_luck": signed(T[lucky]["luck"]), "unlucky": nm(unlucky), "unlucky_luck": signed(T[unlucky]["luck"])}
        effs = [(self.teams[x]["lineup_efficiency"], x) for x in order if self.teams[x].get("lineup_efficiency")]
        eff_f = None
        if len(effs) >= 2:
            hi, lo = max(effs), min(effs)
            eff_f = {"best_n": nm(hi[1]), "best_pct": f"{round(hi[0] * 100)}%", "worst_n": nm(lo[1]), "worst_pct": f"{round(lo[0] * 100)}%"}
        rec = self.st["records"] or {}
        rec_f = None
        if rec.get("high_score") and rec.get("biggest_blowout"):
            bb = rec["biggest_blowout"]
            bw = bb["winner"]
            if bw is not None:
                bl = bb["b"] if bw == bb["a"] else bb["a"]
                rec_f = {"hi_n": nm(rec["high_score"]["roster_id"]), "hi_pts": fmt(rec["high_score"]["points"]), "hi_wk": str(rec["high_score"]["week"]),
                         "blow_w": nm(bw), "blow_l": nm(bl), "blow_m": fmt(bb["margin"]), "blow_wk": str(bb["week"])}
        cands: list[int] = []
        if final:
            seeds = self.po.get("current_seeds") or {}
            seeded = sorted((x for x in order if seeds.get(x)), key=lambda x: seeds[x]) or order[:n_po]
            top = seeded[0]
            six = seeded[-1]
            rest = [x for x in order if x not in seeded]
            seven = rest[0] if rest else None
            f0 = {"top": nm(top), "six": nm(six), "seven": nm(seven) if seven else None, "bottom": nm(bottom), "wl": wl, "wk": str(S["week"])}
            if not seven:
                return None
            headline = w.head("h.nf", f0)
            pf_n = max(order, key=lambda x: T[x]["pf"]); low_n = min(order, key=lambda x: T[x]["pf"])
            w.add([w.line("n.ftop", {"top": nm(top), "top_rec": T[top]["record"], "top_pf": pts(T[top]["pf"])}, repeat=True),
                   w.line("n.fcut", {"six": nm(six), "six_rec": T[six]["record"], "seven": nm(seven), "seven_rec": T[seven]["record"]}, repeat=True),
                   w.line("n.fbottom", {"bottom": nm(bottom), "bottom_rec": T[bottom]["record"]}, repeat=True)], {"standings": True})
            w.add([w.line("n.fpts", {"pf_n": nm(pf_n), "pf_pts": pts(T[pf_n]["pf"]), "low_n": nm(low_n), "low_pts": pts(T[low_n]["pf"])}),
                   w.line("n.luck", luck_f) if luck_f else None, w.line("n.eff", eff_f) if eff_f else None,
                   w.line("n.records", rec_f) if rec_f else None], {"standings": True})
            qs = [w.quote(top, "clinched", {"rec": T[top]["record"]}), w.quote(seven, "eliminated", {"rec": T[seven]["record"]})]
            w.add(qs + [w.line("n.close", {"top": nm(top), "wl": wl}, repeat=True)], {"standings": True})
            dek = f"Final regular-season standings · {nm(top)} earns the top seed at {T[top]['record']} · {n_po} teams advance"
            cands = [top, six, seven, bottom, pf_n, low_n] + ([lucky, unlucky] if luck_f else []) + [x for x in order if eff_f and nm(x) in (eff_f["best_n"], eff_f["worst_n"])]
            facts = {"type": "standings", "final": True, "through_week": S["week"],
                     "table": [{"seed": seeds.get(x), "owner": nm(x), "record": T[x]["record"], "pf": T[x]["pf"], "pa": T[x]["pa"]} for x in order]}
        else:
            top = order[0]
            six = order[n_po - 1] if len(order) >= n_po else order[-1]
            seven = order[n_po] if len(order) > n_po else None
            if not seven:
                return None
            alive = [x for x in order if po[x]["playoff_pct"] > 0.05]
            f0 = {"top": nm(top), "six": nm(six), "bottom": nm(bottom), "alive": str(len(alive)), "spots": str(n_po), "wl": wl, "wk": str(week)}
            headline = w.head("h.n", f0)
            ft = {"top": nm(top), "top_rec": T[top]["record"], "wl": wl, "wk": str(week)}
            if po[top]["playoff_pct"] is not None:
                ft["top_odds"] = pct(po[top]["playoff_pct"])
            if po[top].get("bye_pct"):
                ft["bye"] = pct(po[top]["bye_pct"])
            fc = {"six": nm(six), "six_rec": T[six]["record"], "seven": nm(seven), "seven_rec": T[seven]["record"],
                  "six_odds": pct(po[six]["playoff_pct"]), "seven_odds": pct(po[seven]["playoff_pct"])}
            fb = {"bottom": nm(bottom), "bottom_rec": T[bottom]["record"], "bottom_odds": pct(po[bottom]["playoff_pct"])}
            w.add([w.line("n.top", ft, repeat=True), w.line("n.cut", fc, repeat=True), w.line("n.bottom", fb, repeat=True)], {"standings": True})
            clinched = [nm(x) for x in order if po[x]["status"] == "clinched"]
            elim = [nm(x) for x in order if po[x]["status"] == "eliminated"]
            w.add([w.line("n.luck", luck_f) if luck_f else None, w.line("n.eff", eff_f) if eff_f else None,
                   w.line("n.records", rec_f) if rec_f else None], {"standings": True})
            s3 = [w.line("n.clinch", {"names": join_and(clinched)}) if clinched else None,
                  w.line("n.elim", {"names": join_and(elim)}) if elim else None,
                  w.quote(six, "bubble", {"odds": pct(po[six]["playoff_pct"]), "rec": T[six]["record"]})]
            ex = [x for x in order if po[x]["status"] == "clinched"][:1]
            ey = [x for x in order if po[x]["status"] == "eliminated"][:1]
            if ex and r.random() < 0.5:
                s3.append(w.quote(ex[0], "clinched", {"rec": T[ex[0]]["record"]}))
            elif ey:
                s3.append(w.quote(ey[0], "eliminated", {"rec": T[ey[0]]["record"]}))
            s3.append(w.line("n.close", {"top": nm(top), "wl": wl}, repeat=True))
            w.add(s3, {"standings": True})
            dek = f"Through {wl}: {len(alive)} teams alive for {n_po} spots · {nm(top)} leads at {T[top]['record']}"
            cands = [top, six, seven, bottom] + ([lucky, unlucky] if luck_f else []) + [self.teams[x]["roster_id"] for x in order if (clinched and nm(x) in clinched) or (elim and nm(x) in elim)]
            if eff_f:
                cands += [x for x in order if nm(x) in (eff_f["best_n"], eff_f["worst_n"])]
            cands += ex + ey
            facts = {"type": "standings", "final": False, "through_week": S["week"],
                     "table": [{"owner": nm(x), "record": T[x]["record"], "pf": T[x]["pf"], "playoff_pct": po[x]["playoff_pct"],
                                "bye_pct": po[x].get("bye_pct"), "status": po[x]["status"]} for x in order]}
        return self._article(w, "standings", week, headline, dek, cands, ["standings", f"week-{week}"], facts)

    # ======================================================================
    # Feud
    # ======================================================================
    def feud_pair(self, week: int, used: set, r) -> tuple[int, int, dict | None] | None:
        games = [g for g in self.games_by_week.get(week, []) if g["a"] in self.teams and g["b"] in self.teams]
        if not games:
            return None
        scored = []
        for g in games:
            pair = frozenset((g["a"], g["b"]))
            sc = 0.0
            if self.rivalry_between(g["a"], g["b"]):
                sc += 5
            if g["margin"] >= 30 or 0 < g["margin"] < 7:
                sc += 2
            if pair in used:
                sc -= 6
            sc += r.random()
            scored.append((sc, g))
        g = max(scored, key=lambda x: x[0])[1]
        a, b = (g["winner"], g["b"] if g["winner"] == g["a"] else g["a"]) if g["winner"] is not None else (g["a"], g["b"])
        return a, b, self.rivalry_between(a, b)

    def feud(self, week: int, a: int, b: int, voice) -> dict | None:
        r = self.rng("feud", week, a, b, voice.id)
        w = Writer(self, voice, r, "feud", week)
        nar = w.active(a, b)
        S = self.snap(week)  # as-of (regular season through `week`)
        nm = self.name
        rv = self.rivalry_between(a, b)
        # Every incident below involves BOTH parties. A blowout by one of them over a third team is only ever
        # background (the `third` context sentence), never the lede, the dek or what the quotes answer.
        inc: dict[str, dict] = {}
        info: dict[str, Any] = {}
        hh = [g for g in self.h2h_games(a, b, week) if g["winner"] is not None]
        if hh:
            g = max(hh, key=lambda x: x["week"])
            ww = g["winner"]; ll = b if ww == a else a
            wp = g["a_pts"] if ww == g["a"] else g["b_pts"]; lp = g["b_pts"] if ww == g["a"] else g["a_pts"]
            mc = mclass(g["margin"])
            inc["h2h"] = {"w": nm(ww), "l": nm(ll), "wp": fmt(wp), "lp": fmt(lp), "m": fmt(g["margin"]), "gwk": str(g["week"]), "mclass": mc}
            wins = sum(1 for x in hh if x["winner"] == ww)
            info["h2h"] = {"w": ww, "l": ll, "mc": mc, "m": fmt(g["margin"]), "wp": fmt(wp), "lp": fmt(lp), "wk": g["week"],
                           "rec": {ww: (wins, len(hh) - wins), ll: (len(hh) - wins, wins)}}
        trades = []
        for wk in sorted(self.ctx["transactions"]):
            if wk > week:
                break
            for tx in self.live_txs(wk):
                if tx["type"] == "trade" and {int(x) for x in tx.get("roster_ids") or []} == {a, b}:
                    ti = self.trade_info(tx, wk)
                    if ti:
                        trades.append(ti)
        if trades:
            ti = trades[-1]
            inc["trade"] = {"a": nm(a), "b": nm(b), "a_got": ti["text"][a], "b_got": ti["text"][b], "twk": str(ti["week"])}
            info["trade"] = ti
        ra, rb = S["teams"][a]["rank"], S["teams"][b]["rank"]
        if abs(ra - rb) <= 2 and S["week"] >= 1:
            hi, lo = (a, b) if ra < rb else (b, a)
            gap = abs(S["teams"][a]["pf"] - S["teams"][b]["pf"])
            inc["adj"] = {"hi": nm(hi), "lo": nm(lo), "hi_rank": ordinal(S["teams"][hi]["rank"]), "lo_rank": ordinal(S["teams"][lo]["rank"]),
                          "hi_rec": S["teams"][hi]["record"], "lo_rec": S["teams"][lo]["record"], "pf_gap": pts(gap)}
        cnt = self.sg_counts(week)
        ca, cb = cnt.get(a, 0), cnt.get(b, 0)
        if ca != cb and ca + cb >= 2:
            inc["sg"] = {"a": nm(a), "b": nm(b), "a_sg": plural(ca, "shotgun") if ca else "no shotguns", "b_sg": plural(cb, "shotgun") if cb else "no shotguns"}
            info["sg"] = (a, ca, b, cb)
        if rv and rv["backstory"]:
            inc["story"] = {"rv_name": rv["name"], "backstory": rv["backstory"].strip(), "a": nm(a), "b": nm(b)}
        ta = [t.strip().rstrip(".") for t in self.profile(a).get("traits") or []]
        tb = [t.strip().rstrip(".") for t in self.profile(b).get("traits") or []]
        if ta and tb:
            inc["trait"] = {"a": nm(a), "b": nm(b), "a_trait": r.choice(ta), "b_trait": r.choice(tb)}
        # background only: one party's blowout over somebody else this season
        third = third_key = None
        blows = [g for g in self.st["games"] if g["week"] <= week and g["margin"] >= 30 and g["winner"] in (a, b)
                 and (g["b"] if g["winner"] == g["a"] else g["a"]) not in (a, b)
                 and (g["week"], g["a"], g["b"]) not in self.third_cited]   # one blowout is cited once per build, not in four feuds
        if blows:
            g = max(blows, key=lambda x: (x["margin"], x["week"]))
            ww = g["winner"]; ll = g["b"] if ww == g["a"] else g["a"]
            wp = g["a_pts"] if ww == g["a"] else g["b_pts"]; lp = g["b_pts"] if ww == g["a"] else g["a_pts"]
            third = {"w": nm(ww), "l": nm(ll), "m": fmt(g["margin"]), "gwk": str(g["week"]), "wp": fmt(wp), "lp": fmt(lp), "mclass": "blowout"}
            third_key = (g["week"], g["a"], g["b"])
        weights = {"h2h": 5, "trade": 4.5, "story": 3.5, "adj": 3, "sg": 2.5, "trait": 1}
        kinds = list(inc)
        if not kinds:
            return None
        primary = r.choices(kinds, weights=[weights[x] for x in kinds])[0]
        rest = [k for k in kinds if k != primary]
        second = None
        if rest or third:
            opts = rest + (["third"] if third else [])
            second = r.choices(opts, weights=[3 if k == "third" else weights[k] for k in opts])[0]
        f = {"a": nm(a), "b": nm(b)}
        headline = w.head_slanted(nar, "h.sl.any", {"n": nm(nar.rid), "wl": f"Week {week}", "wk": str(week)}) if nar else None
        if headline is None:
            headline = w.head("h.f", f)
        slot = {"h2h": "f.h2h", "trade": "f.trade", "adj": "f.adj", "sg": "f.sg", "story": "f.story", "trait": "f.trait"}
        paras = [[w.line(slot[primary], inc[primary], repeat=True)]]
        p2: list[str | None] = []
        if second == "third":
            # a third team may only appear in a sentence that says "over <third>"
            p2.append(w.line("f.blow", third, need="over {l}"))
            if p2[-1]:
                self.third_cited.add(third_key)
        elif second:
            p2.append(w.line(slot[second], inc[second], repeat=True))
        if S["week"] >= 1:
            p2.append(w.line("f.mid", {**f, "a_rec": S["teams"][a]["record"], "b_rec": S["teams"][b]["record"],
                                       "a_rank": ordinal(ra), "b_rank": ordinal(rb), "wk": str(S["week"])}))
        quotes = self._feud_quotes(w, primary, a, b, info, week, S)
        meta = {"feud": primary, "teams": [nm(a), nm(b)]}
        w.add(paras[0], meta)
        w.add(p2, meta)
        w.add(quotes + [w.line("f.close", f, repeat=True)], meta)
        w.add_theme(nar)
        dek = self._feud_dek(primary, inc[primary], a, b)
        shown = [k for k in (primary, second) if k and k != "third"]
        facts = {"type": "feud", "week": week, "teams": [nm(a), nm(b)], "incidents": {k: dict(inc[k]) for k in shown},
                 "primary": primary, "rivalry": rv["name"] if rv else None}
        if second == "third":
            facts["background"] = {"blowout_over_third_team": third}
        return self._article(w, "feud", week, headline, dek, [a, b], ["feud"] + (["rivalry"] if rv else []) + [f"week-{week}"], facts,
                             key_teams=[a, b])

    def _feud_dek(self, kind: str, d: dict, a: int, b: int) -> str:
        n = self.name
        if kind == "h2h":
            return f"Week {d['gwk']}: {d['w']} {d['wp']}, {d['l']} {d['lp']}"
        if kind == "trade":
            return f"{n(a)} and {n(b)} traded in Week {d['twk']}"
        if kind == "adj":
            return f"{d['hi']} ({d['hi_rec']}, {d['hi_rank']}) and {d['lo']} ({d['lo_rec']}, {d['lo_rank']}), {d['pf_gap']} apart"
        if kind == "sg":
            return f"Shotgun ledger: {d['a']} {d['a_sg']}, {d['b']} {d['b_sg']}"
        if kind == "story":
            return d["rv_name"]
        return f"{n(a)} vs. {n(b)}"

    def _feud_quotes(self, w: Writer, kind: str, a: int, b: int, info: dict, week: int, S: dict) -> list[str | None]:
        """Quotes that answer the chosen incident (never a game against a third team)."""
        nm = self.name
        pa, pb = self._pv(a, S), self._pv(b, S)
        if kind == "h2h":
            d = info["h2h"]
            ww, ll = d["w"], d["l"]
            big = d["mc"] in ("blowout", "comfortable")
            base = {"m": d["m"], "wp": d["wp"], "lp": d["lp"], "wk": str(d["wk"])}

            def sit_for(x: int, y: int, won: bool) -> tuple[str, dict]:
                if d["mc"] == "close":
                    return ("won_close" if won else "lost_close"), {**base, "opp": nm(y)}
                if big:
                    return ("won_big" if won else "lost_big"), {**base, "opp": nm(y)}
                x_w, x_l = d["rec"][x]
                rec = f"{x_w}-{x_l}"
                if x_w > x_l:
                    return "trash_h2h_lead", {"opp": nm(y), "h2h": rec}
                if x_l > x_w:
                    return "trash_h2h_trail", {"opp": nm(y), "h2h": rec}
                return "trash_even", {"opp": nm(y)}
            sit, qf = sit_for(ww, ll, True)
            boast = w.quote(ww, sit, qf, sig_ok=True)
            if boast is None:
                return []
            if w.rng.random() < 0.5:
                reply = w.quote(ll, "deny_after_trash", {"opp": nm(ww)}, sig_ok=True)
            else:
                sit2, qf2 = sit_for(ll, ww, False)
                reply = w.quote(ll, sit2, qf2, sig_ok=True)
            return [boast, reply]
        if kind == "trade":
            T = info["trade"]
            out = []
            for x, y in ((a, b), (b, a)):
                sit = "trade_pending" if not T["graded"] else ("trade_got_more" if x == T["lead"] else "trade_gave_more")
                out.append(w.quote(x, sit, {"opp": nm(y), "gave": T["plain"][y], "got": T["plain"][x]}, sig_ok=True))
            return out
        if kind == "sg":
            xa, ca, xb, cb = info["sg"]
            x, cx = (xa, ca) if ca > cb else (xb, cb)
            Y, X = (pb, pa) if x == a else (pa, pb)
            return [w.quote(x, "shotgun_owed", {"sgn": sg_words(cx)}, multi=cx >= 2, sig_ok=True), self._trash(w, Y, X, [], week, False, True)[1]]
        return self._exchange(w, pa, pb, week, False, True)

    # ======================================================================
    # Offseason
    # ======================================================================
    def offseason(self, txs: list[dict], voice) -> dict | None:
        trades = [t for t in txs if t.get("type") == "trade"]
        pickups = sum(len(t.get("adds") or {}) for t in txs if t.get("type") in ("waiver", "free_agent"))
        if not trades and not pickups:
            return None
        r = self.rng("offseason", voice.id)
        w = Writer(self, voice, r, "offseason", 1)
        counts: dict[int, int] = {}
        for t in trades:
            for x in t.get("roster_ids") or []:
                if int(x) in self.teams:
                    counts[int(x)] = counts.get(int(x), 0) + 1
        busy = sorted(counts, key=lambda x: (-counts[x], self.name(x).lower()))[:3]
        f = {"ntrades": plural(len(trades), "trade"), "npick": plural(pickups, "pickup")}
        headline = w.head("h.o", f)
        s1 = [w.line("o.lede", f, repeat=True)]
        if busy:
            s1.append(w.line("o.busy", {"busy_text": ", ".join(f"{self.name(x)} ({counts[x]})" for x in busy)}))
        w.add(s1, {"offseason": True})
        cands = list(busy)
        big = None
        for t in sorted(trades, key=lambda t: str(t.get("transaction_id"))):
            d = self.tx_desc(t)
            if len(d) == 2 and all(v["players"] or v["picks"] for v in d.values()):
                n = sum(len(v["players"]) + len(v["picks"]) for v in d.values())
                if big is None or n > big[0]:
                    big = (n, d)
        s2: list[str | None] = []
        if big:
            (ra, ga), (rb, gb) = list(big[1].items())
            s2.append(w.line("o.big", {"side_a": self.name(ra), "side_b": self.name(rb), "a_got": join_and(ga["players"] + ga["picks"]),
                                       "b_got": join_and(gb["players"] + gb["picks"])}))
            cands += [ra, rb]
        if busy:
            s2.append(w.line("o.close", {"busiest": self.name(busy[0])}))
        w.add(s2, {"offseason": True})
        facts = {"type": "offseason", "trades": len(trades), "pickups": pickups,
                 "busiest": [{"owner": self.name(x), "trades": counts[x]} for x in busy]}
        dek = f"{plural(len(trades), 'trade')} · {plural(pickups, 'pickup')}" + (f" · busiest: {self.name(busy[0])}" if busy else "")
        return self._article(w, "offseason", 1, headline, dek, cands, ["offseason", "trade", "week-1"], facts)
