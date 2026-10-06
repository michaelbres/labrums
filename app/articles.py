"""Fake newsroom. Template-driven, seeded per (season, week, type) so a story
reads the same on every refresh. Owner profiles and rivalries from config.yaml
flavor the quotes and the feuds.
"""
from __future__ import annotations

import random
from typing import Any

from .loader import is_offseason
from .sleeper import player_label

# --------------------------------------------------------------------------
# Quote banks. {me} = speaker, {them} = other owner, {team} = other team name.
# --------------------------------------------------------------------------
Q_WIN = [
    "Honestly, I never doubted it. The lineup set itself.",
    "Tell {them} the check's in the mail. Oh wait, there's no check. Just the L.",
    "We play the games for a reason, and the reason is so I can do this to {them}.",
    "I'd like to thank my waiver wire, my group chat, and nobody else.",
    "Was it ever close? I didn't look. I don't look at scores, I look at results.",
    "That's a professional operation over here. Film study. Nutrition. Vibes.",
]
Q_LOSS = [
    "The scoring system is rigged and I will be filing a formal complaint with the commissioner.",
    "No comment. Actually, one comment: my kicker should be in jail.",
    "If my guys had scored more points, I think we win that game.",
    "I'm not making excuses, but I had three guys on bye and a fourth who I'm pretty sure retired mid-game.",
    "We'll regroup. We'll reload. We'll probably lose again, but we'll do it with dignity.",
    "I set my lineup from a bar at 12:58. That's on me. Mostly on the bar.",
]
Q_TRADE_HAPPY = [
    "This is the move that puts us over the top. Book the parade.",
    "I fleeced him and he thanked me for it. That's the business.",
    "When {them} texted me that offer I had to check it wasn't a wrong number.",
    "People will say I overpaid. People said that about the Louisiana Purchase.",
]
Q_TRADE_DEFENSIVE = [
    "It's a win-win. Mostly a win for me, but still.",
    "Every analyst in the group chat is wrong and I'll remember every name.",
    "I'm playing chess. {them} is playing with blocks.",
]
Q_TRASH = [
    "{them} runs a team like a lemonade stand. Cute, but it's not a business.",
    "I've seen {them}'s bench. It's a hospice.",
    "If {them} makes the playoffs I'll shotgun a beer for every week of the season.",
    "{them} drafted a kicker in the eighth round. I rest my case.",
    "I don't have a rivalry with {them}. A rivalry implies they win sometimes.",
    "My lineup could beat {them}'s lineup with my phone on airplane mode.",
]
Q_DENY = [
    "I never said that. And if I did, it was taken out of context. And if it wasn't, I was right.",
    "This is a league of gentlemen, and also {them}.",
    "I'm focused on my team. I'm not focused on {them}. Why would I be focused on {them}? Who told you that?",
]
Q_WAIVER = [
    "Saw him on the wire at 2 a.m. and knew. Sometimes you just know.",
    "Everyone was asleep. I was not. That's the edge.",
    "I bid what I bid. My FAAB is my business.",
    "This is a depth move. A depth move that's starting in my flex this week.",
]
Q_SHOTGUN = [
    "The beer was cold, the kicker was colder.",
    "I'd like to appeal. On what grounds? On the grounds that I don't want to do it.",
    "Rules are rules. I made the rule. I regret the rule.",
    "Two shotguns before noon on a Tuesday. This league is a cry for help.",
    "He had the bye. I knew he had the bye. I started him anyway. There's no defense.",
]

FEUD_INCIDENTS = [
    ("{a} accused {b} of 'lineup tampering' after {b} liked a photo of {a}'s injured running back",
     "The post has since been deleted, though screenshots are, as always, forever."),
    ("{a} and {b} were reportedly not on speaking terms at a league dinner after a dispute over who 'really' won the 2019 draft",
     "Witnesses say {a} ordered for the table without asking. {b} paid, but 'aggressively.'"),
    ("{a} has filed a grievance with the commissioner alleging {b} 'vetoes trades with his eyes'",
     "The commissioner's office responded with a thumbs-up emoji and no further comment."),
    ("{a} left the group chat for 41 minutes on Sunday after {b} posted a GIF of a clown",
     "{a} returned with a single message: 'scoreboard.' The scoreboard, at that moment, did not support this."),
    ("{a} was overheard calling {b}'s team 'a collection of handcuffs and prayers'",
     "{b} responded by changing their team name to 'Handcuffs and Prayers' for the remainder of the week."),
    ("{b} offered {a} a trade of three kickers for a first-round pick 'as a joke,' which {a} did not find funny",
     "{a} countered with a block. Sources say the block lasted a full day."),
    ("{a} reportedly set a calendar reminder to trash-talk {b} every Tuesday at 9 a.m.",
     "The reminder is titled 'Reminder.' {b} has seen it. Everyone has seen it."),
    ("{a} and {b} disagreed on whether a 0.5 PPR league is 'real football'",
     "The debate lasted four hours and resolved nothing, like most things in this league."),
    ("{b} brought a printed spreadsheet to a casual hangout to prove {a} is 'the luckiest owner alive'",
     "The spreadsheet had three tabs. {a} did not read any of them."),
]

HEAD_BLOWOUT = [
    "{w} Obliterates {l} in {m}-Point Massacre",
    "Mercy Rule Requested: {w} Hangs {wp} on {l}",
    "{l} Formally Requests to Forfeit Next Week After {w} Rout",
    "{w} Treats {l} Like a Bye Week",
]
HEAD_CLOSE = [
    "{w} Escapes {l} by {m} in Monday Night Heart Attack",
    "{l} Loses by {m}, Immediately Blames the Scoring System",
    "Coin Flip Goes {w}'s Way in {m}-Point Thriller",
    "{w} Survives {l}; Both Owners Need a Nap",
]
HEAD_NORMAL = [
    "{w} Handles {l}, {wp}-{lp}",
    "{w} Takes Care of Business Against {l}",
    "{l} Falls to {w} in Game Nobody Will Remember by Thursday",
    "{w} Over {l}: Fine. Just Fine.",
]
HEAD_UPSET = [
    "UPSET: {w} Stuns {l} and the Entire Group Chat",
    "{l}'s Hot Start Hits a Wall Named {w}",
    "Nobody Saw It Coming: {w} Topples {l}",
]
HEAD_PREVIEW = [
    "Week {wk} Preview: {a} vs. {b}",
    "{a} and {b} Collide With Playoff Math on the Line",
    "Can {b} Slow Down {a}? Probably Not, But Let's Discuss",
    "{a}-{b}: Everything You Need to Know (and Several Things You Don't)",
]
HEAD_TRADE = [
    "BLOCKBUSTER: {a} and {b} Swap {n} Players in Deal That Shakes the League",
    "{a} Sends {pa} to {b} in Trade the Group Chat Is Already Vetoing",
    "Trade Alert: {a} and {b} Agree to Terms; Analysts Divided, Loudly",
    "{b} Acquires {pb} From {a}; 'Robbery,' Says Everyone Not Involved",
]
HEAD_WAIVER = [
    "Waiver Wire Report: {top} Breaks the Bank for {p}",
    "{top} Wins the Week's Waiver Battle; {n} Other {moves} Made",
    "FAAB Frenzy: {p} Lands With {top}",
]
HEAD_SHOTGUN = [
    "Beer Report, Week {wk}: {n} Shotguns Owed Across the League",
    "{top} Leads a Brutal Week {wk} With {topn} Shotguns",
    "Week {wk} Shotgun Ledger: Somebody Check on {top}",
    "A Moment of Silence for the Livers: {n} Shotguns in Week {wk}",
]
HEAD_FEUD = [
    "Sources: Tension Between {a} and {b} 'At an All-Time High'",
    "{a} vs. {b}: The Feud Nobody Asked For Continues",
    "League Insiders Worried About {a}-{b} Beef Ahead of Draft Dinner",
    "Exclusive: Inside the Cold War Between {a} and {b}",
]
HEAD_RIVALRY = [
    "RIVALRY WEEK: {a} vs. {b} Is Here",
    "{name}: {a} and {b} Renew Hostilities in Week {wk}",
    "Bragging Rights on the Line as {a} Hosts {b}",
]
HEAD_STANDINGS = [
    "Playoff Picture, Week {wk}: {bubble} Clings to the Final Spot",
    "Standings Check: {top} on Top, {bubble} on the Bubble, {bottom} on the Couch",
    "{spots} Spots, {alive} Contenders: The Week {wk} Playoff Race",
]

ORDINALS = {1: "1st", 2: "2nd", 3: "3rd"}


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return ORDINALS.get(n % 10, f"{n}th") if n % 10 in ORDINALS else f"{n}th"


def _fill(text: str, **kw: str) -> str:
    """Plain {key} replacement. Never str.format: user text may contain braces."""
    for k, v in kw.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def pct(p: float | None) -> str:
    return "—" if p is None else f"{round(p * 100):d}%"


class Newsroom:
    def __init__(self, ctx: dict, st: dict, po: dict, shotgun_items: list[dict]):
        self.ctx, self.st, self.po = ctx, st, po
        self.shotguns = shotgun_items
        self.cfg = ctx["config"]
        self.teams = st["teams"]
        self.reporters = list(self.cfg.get("reporters") or ["The Beat Writer"])
        self.rivalries = self._resolve_rivalries()
        self._id = 0

    # ---- helpers ---------------------------------------------------------
    def rng(self, *parts) -> random.Random:
        return random.Random(":".join(str(p) for p in (self.ctx["season"], *parts)))

    def name(self, rid: int) -> str:
        return self.teams[rid]["display_name"]

    def nick(self, rid: int, r: random.Random | None = None) -> str:
        t = self.teams[rid]
        if t.get("nickname") and (r is None or r.random() < 0.5):
            return t["nickname"]
        return t["display_name"]

    def tname(self, rid: int) -> str:
        return self.teams[rid]["team_name"]

    def profile(self, rid: int) -> dict:
        return self.teams[rid].get("profile") or {}

    def quote(self, rid: int, bank: list[str], r: random.Random, them: int | None = None) -> str:
        prof = self.profile(rid)
        if prof.get("catchphrase") and r.random() < 0.3:
            q = prof["catchphrase"]
        else:
            q = r.choice(bank)
        q = _fill(q, me=self.name(rid), them=self.name(them) if them else "them",
                  team=self.tname(them) if them else "that team")
        q = q.strip()
        if q.endswith("..."):
            q = q[:-3] + "…"
        if q.endswith("."):
            q = q[:-1]
        if q[-1:] not in ("!", "?"):
            q += ","  # “…,” said Name.   (a trailing ! or ? stays as is)
        return f"“{q}” said {self.name(rid)}."

    def trait_line(self, rid: int, r: random.Random) -> str | None:
        traits = self.profile(rid).get("traits") or []
        if not traits:
            return None
        return f"{self.name(rid)}, known around the league for being someone who {r.choice(traits)}, "

    def _resolve_rivalries(self) -> list[dict]:
        out = []
        by_name = {t["display_name"].lower(): rid for rid, t in self.teams.items()}
        by_name.update({str(t.get("owner_id")).lower(): rid for rid, t in self.teams.items()})
        for rv in self.cfg.get("rivalries") or []:
            owners = [by_name.get(str(o).lower()) for o in rv.get("owners") or []]
            owners = [o for o in owners if o is not None]
            if len(owners) >= 2:
                out.append({"name": rv.get("name") or f"{self.name(owners[0])} vs. {self.name(owners[1])}",
                            "owners": owners[:2], "backstory": rv.get("backstory") or ""})
        return out

    def rivalry_between(self, a: int, b: int) -> dict | None:
        for rv in self.rivalries:
            if set(rv["owners"]) == {a, b}:
                return rv
        return None

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
            pts = float(sp[i]) if i < len(sp) else float(pp.get(pid, 0) or 0)
            out.append({**player_label(self.ctx["players"], pid), "points": round(pts, 2)})
        return out

    def best_starter(self, week: int, rid: int) -> dict | None:
        s = [x for x in self.starters_with_points(week, rid) if x["player_id"] != "0"]
        return max(s, key=lambda x: x["points"]) if s else None

    def worst_starter(self, week: int, rid: int) -> dict | None:
        s = self.starters_with_points(week, rid)
        return min(s, key=lambda x: x["points"]) if s else None

    def points_since(self, pid: str, after_week: int, rid: int) -> float:
        total = 0.0
        for w, rows in self.ctx["matchups"].items():
            if w <= after_week or w > self.ctx["last_completed"]:
                continue
            for r in rows:
                if int(r["roster_id"]) == rid:
                    total += float((r.get("players_points") or {}).get(pid, 0) or 0)
        return round(total, 2)

    def article(self, kind: str, week: int, headline: str, dek: str, body: list[str],
                teams: list[int], r: random.Random, tags: list[str] | None = None) -> dict:
        self._id += 1
        return {"id": f"{self.ctx['season']}-{kind}-{week}-{self._id}", "type": kind, "week": week,
                "headline": headline, "dek": dek, "byline": r.choice(self.reporters), "body": body,
                "teams": teams, "tags": tags or []}

    # ---- generators ------------------------------------------------------
    def recap(self, g: dict) -> dict:
        week = g["week"]
        r = self.rng("recap", week, g["a"], g["b"])
        if g["winner"] is None:
            return self.recap_tie(g, r)
        w = g["winner"]; l = g["b"] if w == g["a"] else g["a"]
        wp = g["a_pts"] if w == g["a"] else g["b_pts"]
        lp = g["b_pts"] if w == g["a"] else g["a_pts"]
        m = g["margin"]
        tw, tl = self.teams[w], self.teams[l]
        # Was it an upset? Loser was higher in power rankings at the time (approx: season power rank).
        upset = tl["power_rank"] < tw["power_rank"] - 3
        bank = HEAD_BLOWOUT if m >= 30 else HEAD_CLOSE if m < 7 else HEAD_UPSET if upset else HEAD_NORMAL
        head = r.choice(bank).format(w=self.name(w), l=self.name(l), m=f"{m:g}", wp=f"{wp:g}", lp=f"{lp:g}")
        star = self.best_starter(week, w)
        goat = self.worst_starter(week, l)
        wk_shotguns = [s for s in self.shotguns if s["week"] == week and s["roster_id"] == l and s["reason"] != "rule"]
        body = []
        body.append(r.choice([
            f"{self.tname(w)} ({tw['record']}) took down {self.tname(l)} ({tl['record']}) in Week {week}, {wp:g} to {lp:g}.",
            f"Week {week} belonged to {self.nick(w, r)}, who beat {self.name(l)} {wp:g}-{lp:g} and moved to {tw['record']}.",
            f"Final from Week {week}: {self.name(w)} {wp:g}, {self.name(l)} {lp:g}. {self.name(l)} drops to {tl['record']}.",
        ]))
        if star:
            body.append(r.choice([
                f"{star['name']} ({star['position']}) led the way with {star['points']:g} points, which is {star['points'] / max(wp, 1) * 100:.0f}% of the winning total and roughly 100% of the trash talk material.",
                f"The star of the show was {star['name']}, whose {star['points']:g} points were more than enough to keep {self.name(l)} at arm's length.",
            ]))
        if goat and goat["points"] <= 2:
            body.append(r.choice([
                f"On the other side, {goat['name']} ({goat['position']}) posted {goat['points']:g} points in {self.name(l)}'s lineup. The bench, as always, watched in silence.",
                f"{self.name(l)} got {goat['points']:g} points out of {goat['name']}, which is not a typo, and is also not great.",
            ]))
        if wk_shotguns:
            names = ", ".join(s["player"]["name"] for s in wk_shotguns)
            body.append(f"Per league bylaws, {self.name(l)} now owes {len(wk_shotguns)} shotgun{'s' if len(wk_shotguns) > 1 else ''} for starting {names}. The commissioner's office has been notified.")
        if m >= 30:
            body.append(f"The {m:g}-point margin is the kind of score that gets screenshotted and sent to people who didn't ask.")
        elif m < 7:
            body.append(f"A {m:g}-point margin means this one came down to the Monday night game, the stat corrections, and whatever {self.name(l)} is going to blame in the group chat.")
        streak = tw["streak"]
        if streak.startswith("W") and int(streak[1:]) >= 3:
            body.append(f"{self.name(w)} has now won {streak[1:]} straight and sits {ordinal(tw['rank'])} in the standings.")
        if tl["streak"].startswith("L") and int(tl["streak"][1:]) >= 3:
            body.append(f"{self.name(l)} has lost {tl['streak'][1:]} in a row. Sources close to the team describe the mood as 'fine, why, who's asking.'")
        if abs(tl["luck"]) >= 1.2 and tl["luck"] > 0:
            body.append(f"Still, {self.name(l)} remains one of the luckier teams in the league by the all-play numbers (+{tl['luck']:g} wins over expectation), so spare the sympathy.")
        tl_line = self.trait_line(l, r)
        body.append(self.quote(w, Q_WIN, r, l))
        if tl_line:
            body.append(tl_line + "offered this: " + self.quote(l, Q_LOSS, r, w).rsplit(" said ", 1)[0].replace(",\u201d", ".\u201d"))
        else:
            body.append(self.quote(l, Q_LOSS, r, w))
        dek = f"{self.name(w)} {wp:g}, {self.name(l)} {lp:g}"
        return self.article("recap", week, head, dek, body, [w, l], r, ["recap", f"week-{week}"])

    def recap_tie(self, g: dict, r: random.Random) -> dict:
        week, a, b = g["week"], g["a"], g["b"]
        pts = g["a_pts"]
        ta, tb = self.teams[a], self.teams[b]
        head = f"{self.name(a)} and {self.name(b)} Tie at {pts:g}, Nobody Happy"
        body = [
            f"{self.tname(a)} ({ta['record']}) and {self.tname(b)} ({tb['record']}) finished Week {week} dead even at {pts:g} points apiece.",
            "The league office confirmed the final score twice. Neither owner has accepted it.",
            r.choice([
                "Sources say both owners spent Monday night refreshing the stat corrections, hoping for one more tenth of a point.",
                "A tie counts as half a win for both sides, which is exactly as satisfying as it sounds.",
            ]),
            self.quote(a, Q_LOSS, r, b),
            self.quote(b, Q_LOSS, r, a),
        ]
        dek = f"{self.name(a)} {pts:g}, {self.name(b)} {pts:g}"
        return self.article("recap", week, head, dek, body, [a, b], r, ["recap", f"week-{week}"])

    def preview(self, g: dict) -> dict:
        week = g["week"]
        a, b = g["a"], g["b"]
        r = self.rng("preview", week, a, b)
        ta, tb = self.teams[a], self.teams[b]
        pa, pb = self.po["teams"].get(a, {}), self.po["teams"].get(b, {})
        rv = self.rivalry_between(a, b)
        head = r.choice(HEAD_PREVIEW).format(wk=week, a=self.name(a), b=self.name(b))
        if rv:
            head = f"RIVALRY WEEK: {head}"
        body = [
            f"{self.tname(a)} ({ta['record']}, {ta['avg']:g} ppg) meets {self.tname(b)} ({tb['record']}, {tb['avg']:g} ppg) in Week {week}.",
        ]
        h2h = ta["h2h"].get(b)
        if h2h and (h2h["w"] + h2h["l"] + h2h["t"]) > 0:
            tail = f"-{h2h['t']}" if h2h["t"] else ""
            if h2h["w"] == h2h["l"]:
                body.append(f"Head to head this season: {self.name(a)} and {self.name(b)} split {h2h['w']}-{h2h['l']}{tail}.")
            elif h2h["w"] > h2h["l"]:
                body.append(f"Head to head this season: {self.name(a)} leads {h2h['w']}-{h2h['l']}{tail}.")
            else:
                body.append(f"Head to head this season: {self.name(b)} leads {h2h['l']}-{h2h['w']}{tail}.")
        if pa and pb:
            body.append(f"The playoff math: {self.name(a)} sits at {pct(pa['playoff_pct'])} to make the top {self.po['playoff_teams']}, {self.name(b)} at {pct(pb['playoff_pct'])}.")
            ng_a, ng_b = pa.get("next_game") or {}, pb.get("next_game") or {}
            if ng_a.get("if_win") is not None:
                body.append(f"A win pushes {self.name(a)} to {pct(ng_a['if_win'])}; a loss drops them to {pct(ng_a['if_loss'])}. For {self.name(b)} it's {pct(ng_b['if_win'])} with a win and {pct(ng_b['if_loss'])} without one.")
            swing = abs((ng_a.get("if_win") or 0) - (ng_a.get("if_loss") or 0)) + abs((ng_b.get("if_win") or 0) - (ng_b.get("if_loss") or 0))
            if swing > 0.5:
                body.append("That is as much leverage as any game on the slate this week. Set your lineups early, or at least set them.")
        fav = a if ta["avg"] >= tb["avg"] else b
        dog = b if fav == a else a
        body.append(r.choice([
            f"{self.name(fav)} is the paper favorite on scoring average, but {self.name(dog)}'s {self.teams[dog]['std']:g}-point weekly swing means anything is possible, including something stupid.",
            f"On paper this is {self.name(fav)}'s game. On the field it's whoever remembers that two of their starters are on bye.",
            f"{self.name(fav)} should win. {self.name(fav)} should have won several games this year, which is why we check the standings and not the vibes.",
        ]))
        if rv:
            body.append(f"Then there's {rv['name']}. {rv['backstory']}".strip() + " Expect the group chat to be unusable from Thursday night through Tuesday morning.")
        body.append(self.quote(a, Q_TRASH, r, b))
        body.append(self.quote(b, Q_DENY if r.random() < 0.4 else Q_TRASH, r, a))
        dek = f"{ta['record']} vs. {tb['record']} · Playoff odds {pct(pa.get('playoff_pct'))} / {pct(pb.get('playoff_pct'))}"
        return self.article("preview", week, head, dek, body, [a, b], r, ["preview", f"week-{week}"] + (["rivalry"] if rv else []))

    def trade(self, tx: dict, week: int) -> dict | None:
        rids = [int(x) for x in tx.get("roster_ids") or []]
        rids = [x for x in rids if x in self.teams]
        if len(rids) < 2:
            return None
        a, b = rids[0], rids[1]
        r = self.rng("trade", week, tx.get("transaction_id"))
        adds = tx.get("adds") or {}
        got = {rid: [pid for pid, to in adds.items() if int(to) == rid] for rid in rids}
        picks = tx.get("draft_picks") or []
        pick_to = {}
        for p in picks:
            if p.get("owner_id") is None:
                continue
            pick_to.setdefault(int(p.get("owner_id", 0)), []).append(f"a {p.get('season')} round {p.get('round')} pick")

        def desc(pids: list[str], rid: int) -> str:
            parts = [f"{player_label(self.ctx['players'], pid)['name']} ({player_label(self.ctx['players'], pid)['position']})" for pid in pids]
            parts += pick_to.get(rid, [])
            if not parts:
                return "nothing of note"
            return ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]
        n = sum(len(v) for v in got.values())
        pa = desc(got[a], a) if got[a] else "assets"
        pb = desc(got[b], b) if got[b] else "assets"
        head = r.choice(HEAD_TRADE).format(a=self.name(a), b=self.name(b), n=n or len(picks),
                                           pa=pa.split(",")[0].split(" and ")[0], pb=pb.split(",")[0].split(" and ")[0])
        body = [
            f"{self.name(a)} and {self.name(b)} agreed to a Week {week} trade. {self.name(a)} receives {desc(got[a], a)}. {self.name(b)} receives {desc(got[b], b)}.",
        ]
        # Scoreboard since the trade.
        since_a = sum(self.points_since(pid, week, a) for pid in got[a])
        since_b = sum(self.points_since(pid, week, b) for pid in got[b])
        weeks_since = self.ctx["last_completed"] - week
        if weeks_since > 0 and (got[a] or got[b]):
            lead = a if since_a >= since_b else b
            body.append(f"Since the deal, the pieces {self.name(a)} acquired have produced {since_a:g} points; {self.name(b)}'s haul has produced {since_b:g}. Early returns favor {self.name(lead)}, though 'early' is doing a lot of work in that sentence.")
        else:
            body.append("It's too early to grade this one, which has not stopped anyone from grading it.")
        body.append(r.choice([
            f"League reaction was swift. Three owners called it 'a robbery' without agreeing on who got robbed.",
            f"The trade cleared without a veto, which in this league counts as a standing ovation.",
            f"Analysts note that {self.name(a)} has now made {self.teams[a].get('total_moves') or 'several'} transactions this season, most of them at hours that suggest a problem.",
        ]))
        body.append(self.quote(a, Q_TRADE_HAPPY, r, b))
        body.append(self.quote(b, Q_TRADE_DEFENSIVE, r, a))
        third = r.choice([x for x in self.teams if x not in (a, b)]) if len(self.teams) > 2 else None
        if third:
            body.append(self.quote(third, Q_TRASH, r, r.choice([a, b])))
        dek = f"{self.name(a)} ⇄ {self.name(b)}"
        return self.article("trade", week, head, dek, body, [a, b], r, ["trade", f"week-{week}"])

    def _live_txs(self, txs: list[dict]) -> list[dict]:
        """Completed, non-commissioner transactions only."""
        return [t for t in txs if t.get("type") != "commissioner" and t.get("status") == "complete"]

    def offseason(self, txs: list[dict]) -> dict | None:
        """One roundup article for everything that happened before the season started."""
        trades = [t for t in txs if t.get("type") == "trade"]
        pickups = sum(len(t.get("adds") or {}) for t in txs if t.get("type") in ("waiver", "free_agent"))
        if not trades and not pickups:
            return None
        r = self.rng("offseason")
        players = self.ctx["players"]

        def assets(tx: dict) -> dict[int, list[str]]:
            out: dict[int, list[str]] = {int(x): [] for x in tx.get("roster_ids") or [] if int(x) in self.teams}
            for pid, to in (tx.get("adds") or {}).items():
                if int(to) in out:
                    lab = player_label(players, pid)
                    out[int(to)].append(f"{lab['name']} ({lab['position']})")
            for p in tx.get("draft_picks") or []:
                if p.get("owner_id") is not None and int(p["owner_id"]) in out:
                    out[int(p["owner_id"])].append(f"a {p.get('season')} round {p.get('round')} pick")
            return out

        def join(parts: list[str]) -> str:
            if not parts:
                return "nothing of note"
            return ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]

        counts: dict[int, int] = {}
        for t in trades:
            for x in t.get("roster_ids") or []:
                if int(x) in self.teams:
                    counts[int(x)] = counts.get(int(x), 0) + 1
        busiest = sorted(counts, key=lambda x: (-counts[x], self.name(x).lower()))[:3]
        head = f"Offseason Report: {len(trades)} Trades, {pickups} Pickups, and Several Questionable Decisions"
        body = [f"Before a single snap of the season, the league logged {len(trades)} trades and {pickups} waiver and free-agent "
                f"pickups. Nobody has been able to explain what most of them were for."]
        if busiest:
            lines = ", ".join(f"{self.name(x)} ({counts[x]})" for x in busiest)
            body.append(f"The busiest traders of the offseason: {lines}. The league's phone companies thank them for their service.")
        biggest = None
        if trades:
            biggest = max(trades, key=lambda t: (sum(len(v) for v in assets(t).values()), str(t.get("transaction_id"))))
            sides = assets(biggest)
            parts = [f"{self.name(x)} receives {join(v)}" for x, v in sides.items()]
            body.append("The largest deal of the offseason: " + "; ".join(parts) + ". Dynasty leagues reward patience; this was not that.")
        body.append("Offseason waiver and free-agent activity is not listed individually, out of respect for the people involved.")
        speaker = busiest[0] if busiest else r.choice(sorted(self.teams))
        body.append(self.quote(speaker, Q_TRADE_HAPPY, r))
        involved = sorted(set(busiest) | (set(assets(biggest)) if biggest else set()))
        dek = f"{len(trades)} trades · {pickups} pickups" + (f" · Busiest: {self.name(busiest[0])}" if busiest else "")
        return self.article("offseason", 1, head, dek, body, involved, r, ["offseason", "trade", "week-1"])

    def waivers(self, txs: list[dict], week: int) -> dict | None:
        moves = []
        for tx in txs:
            if tx.get("type") not in ("waiver", "free_agent") or tx.get("status") != "complete":
                continue
            if is_offseason(tx, self.ctx.get("season_start_ms")):
                continue
            rids = [int(x) for x in tx.get("roster_ids") or []]
            if not rids or rids[0] not in self.teams:
                continue
            for pid, to in (tx.get("adds") or {}).items():
                bid = (tx.get("settings") or {}).get("waiver_bid")
                lab = player_label(self.ctx["players"], pid)
                moves.append({"rid": int(to), "pid": pid, "name": lab["name"], "pos": lab["position"],
                              "bid": bid, "type": tx["type"], "since": self.points_since(pid, week, int(to))})
        if not moves:
            return None
        r = self.rng("waiver", week)
        moves.sort(key=lambda m: (-(m["bid"] or 0), -m["since"]))
        top = moves[0]
        head = r.choice(HEAD_WAIVER).format(top=self.name(top["rid"]), p=top["name"], n=len(moves) - 1,
                                            moves="Move" if len(moves) - 1 == 1 else "Moves")
        body = []
        bid_txt = f" for ${top['bid']} of FAAB" if top["bid"] else ""
        body.append(f"The biggest splash on the Week {week} wire was {self.name(top['rid'])} landing {top['name']} ({top['pos']}){bid_txt}.")
        if top["since"] and self.ctx["last_completed"] > week:
            body.append(f"{top['name']} has scored {top['since']:g} points since, which makes the bid look " +
                        ("genius." if top["since"] > 25 else "fine." if top["since"] > 10 else "like a cry for help."))
        others = moves[1:5]
        if others:
            lines = "; ".join(f"{self.name(m['rid'])} added {m['name']} ({m['pos']})" + (f" for ${m['bid']}" if m["bid"] else "") for m in others)
            body.append(f"Elsewhere: {lines}.")
        body.append(f"In total, {len(moves)} players changed hands via waivers and free agency this week. Most of them will be dropped by Week {week + 3}.")
        body.append(self.quote(top["rid"], Q_WAIVER, r))
        dek = f"{len(moves)} adds · Top bid: {self.name(top['rid'])}" + (f" (${top['bid']})" if top["bid"] else "")
        return self.article("waiver", week, head, dek, body, sorted({m["rid"] for m in moves}), r, ["waivers", f"week-{week}"])

    def beer_report(self, week: int) -> dict | None:
        items = [s for s in self.shotguns if s["week"] == week]
        if not items:
            return None
        r = self.rng("shotgun", week)
        per: dict[int, list[dict]] = {}
        for s in items:
            per.setdefault(s["roster_id"], []).append(s)
        ranked = sorted(per.items(), key=lambda kv: -len(kv[1]))
        top_rid, top_items = ranked[0]
        head = r.choice(HEAD_SHOTGUN).format(wk=week, n=len(items), top=self.name(top_rid), topn=len(top_items))
        body = [f"The Week {week} ledger is in: {len(items)} shotgun{'s' if len(items) != 1 else ''} owed across {len(per)} owner{'s' if len(per) != 1 else ''}."]
        for rid, its in ranked:
            parts = []
            for s in its:
                if s["reason"] == "rule":
                    parts.append(f"{s['label'].lower()} ({s.get('detail', '')})")
                elif s["reason"] == "empty_slot":
                    parts.append(f"an empty {s['slot']} slot")
                else:
                    parts.append(f"{s['player']['name']} ({s['player']['position']}, {s['points']:g})")
            body.append(f"{self.name(rid)}: {len(its)} — " + "; ".join(parts) + ".")
        neg = [s for s in items if s["reason"] == "negative"]
        if neg:
            worst = min(neg, key=lambda s: s["points"])
            body.append(f"Lowlight of the week goes to {self.name(worst['roster_id'])}, whose {worst['player']['name']} managed {worst['points']:g} points, which is less than zero, which is less than nothing.")
        body.append(self.quote(top_rid, Q_SHOTGUN, r))
        dek = f"{len(items)} shotguns · {self.name(top_rid)} leads with {len(top_items)}"
        return self.article("shotgun", week, head, dek, body, [rid for rid, _ in ranked], r, ["shotguns", f"week-{week}"])

    def feud(self, week: int) -> dict:
        r = self.rng("feud", week)
        pair = None
        if self.rivalries and r.random() < 0.5:
            rv = r.choice(self.rivalries)
            pair = tuple(rv["owners"])
        else:
            # Owners adjacent in the standings fight the most.
            standings = self.st["standings"]
            i = r.randrange(len(standings) - 1) if len(standings) > 1 else 0
            pair = (standings[i], standings[i + 1]) if len(standings) > 1 else (standings[0], standings[0])
        a, b = pair
        if r.random() < 0.5:
            a, b = b, a
        head = r.choice(HEAD_FEUD).format(a=self.name(a), b=self.name(b))
        inc1, inc2 = r.choice(FEUD_INCIDENTS)
        ta, tb = self.teams[a], self.teams[b]
        body = [
            inc1.format(a=self.name(a), b=self.name(b)) + ", according to multiple sources who asked not to be named because they are in the group chat.",
            inc2.format(a=self.name(a), b=self.name(b)),
            f"The standings do not help: {self.name(a)} sits {ordinal(ta['rank'])} at {ta['record']}, {self.name(b)} {ordinal(tb['rank'])} at {tb['record']}, close enough that every week feels personal.",
        ]
        ta_line = self.trait_line(a, r)
        if ta_line:
            body.append(ta_line + "declined to comment, then commented for eleven minutes.")
        rv = self.rivalry_between(a, b)
        if rv and rv["backstory"]:
            body.append(f"Longtime observers point to the history: {rv['backstory']}")
        body.append(self.quote(a, Q_TRASH, r, b))
        body.append(self.quote(b, Q_DENY, r, a))
        body.append("The commissioner has declined to intervene, citing 'entertainment value.'")
        dek = f"{self.name(a)} vs. {self.name(b)}"
        return self.article("feud", week, head, dek, body, [a, b], r, ["feud"] + (["rivalry"] if rv else []))

    def rivalry_hype(self, week: int, games: list[dict]) -> list[dict]:
        out = []
        for g in games:
            rv = self.rivalry_between(g["a"], g["b"])
            if not rv:
                continue
            a, b = rv["owners"]
            r = self.rng("rivalry", week, a, b)
            head = r.choice(HEAD_RIVALRY).format(a=self.name(a), b=self.name(b), name=rv["name"], wk=week)
            ta, tb = self.teams[a], self.teams[b]
            h2h = ta["h2h"].get(b, {"w": 0, "l": 0, "t": 0})
            body = [
                f"{rv['name']} is back on the schedule. {rv['backstory']}".strip(),
                f"This season: {self.name(a)} {ta['record']}, {self.name(b)} {tb['record']}. Head to head: " + (f"split {h2h['w']}-{h2h['l']}" if h2h['w'] == h2h['l'] else f"{h2h['w']}-{h2h['l']}") + (f"-{h2h['t']}" if h2h['t'] else "") + ("." if h2h['w'] == h2h['l'] else f" in favor of {self.name(a) if h2h['w'] > h2h['l'] else self.name(b)}."),
                f"Scoring says {self.name(a if ta['avg'] >= tb['avg'] else b)} ({max(ta['avg'], tb['avg']):g} ppg). History says nothing about this game will go the way the scoring says.",
                self.quote(a, Q_TRASH, r, b),
                self.quote(b, Q_TRASH, r, a),
            ]
            out.append(self.article("rivalry", week, head, rv["name"], body, [a, b], r, ["rivalry", f"week-{week}"]))
        return out

    def standings_watch(self, week: int) -> dict | None:
        standings = self.st["standings"]
        if len(standings) < 3 or not self.po.get("teams"):
            return None
        r = self.rng("standings", week)
        n_po = self.po["playoff_teams"]
        top = standings[0]
        bubble = standings[min(n_po - 1, len(standings) - 1)]
        first_out = standings[n_po] if len(standings) > n_po else None
        bottom = standings[-1]
        alive = sum(1 for rid in standings if self.po["teams"][rid]["playoff_pct"] > 0.05)
        head = r.choice(HEAD_STANDINGS).format(wk=week, top=self.name(top), bubble=self.name(bubble),
                                               bottom=self.name(bottom), alive=alive, spots=n_po)
        po = self.po["teams"]
        body = [
            f"Through Week {week}, {self.name(top)} leads the league at {self.teams[top]['record']} with {pct(po[top]['playoff_pct'])} playoff odds and a {pct(po[top]['bye_pct'])} shot at a first-round bye."
            if po[top]["bye_pct"] else f"Through Week {week}, {self.name(top)} leads the league at {self.teams[top]['record']} with {pct(po[top]['playoff_pct'])} playoff odds.",
            f"The {ordinal(n_po)} and final spot currently belongs to {self.name(bubble)} ({self.teams[bubble]['record']}, {pct(po[bubble]['playoff_pct'])})" +
            (f", with {self.name(first_out)} ({self.teams[first_out]['record']}, {pct(po[first_out]['playoff_pct'])}) one spot back and well within shouting distance. Literal shouting." if first_out else "."),
        ]
        lucky = max(standings, key=lambda rid: self.teams[rid]["luck"])
        unlucky = min(standings, key=lambda rid: self.teams[rid]["luck"])
        if self.teams[lucky]["luck"] >= 1:
            body.append(f"Luck index: {self.name(lucky)} has {self.teams[lucky]['luck']:+g} wins over what the all-play record says they deserve. {self.name(unlucky)} is at {self.teams[unlucky]['luck']:+g} and would like a word with the schedule maker.")
        clinched = [rid for rid in standings if po[rid]["status"] == "clinched"]
        elim = [rid for rid in standings if po[rid]["status"] == "eliminated"]
        if clinched:
            body.append("Clinched: " + ", ".join(self.name(x) for x in clinched) + ".")
        if elim:
            body.append("Eliminated, mathematically: " + ", ".join(self.name(x) for x in elim) + ".")
        body.append(f"{self.name(bottom)} sits last at {self.teams[bottom]['record']}. " + r.choice([
            "Sources say the rebuild is 'on schedule,' which is what every rebuild says.",
            "The silver lining is draft position. The cloud is everything else.",
            "They have, however, been very active on the waiver wire, which is like rearranging deck chairs but with more FAAB.",
        ]))
        body.append(self.quote(bubble, Q_WIN if self.teams[bubble]["streak"].startswith("W") else Q_LOSS, r, first_out))
        dek = f"{alive} teams alive for {n_po} spots"
        return self.article("standings", week, head, dek, body, [top, bubble] + ([first_out] if first_out else []), r, ["standings", f"week-{week}"])

    # ---- entry point -----------------------------------------------------
    def generate(self) -> list[dict]:
        out: list[dict] = []
        last = self.ctx["last_completed"]
        games_by_week: dict[int, list[dict]] = {}
        for g in self.st["games"]:
            games_by_week.setdefault(g["week"], []).append(g)
        for week in sorted(games_by_week):
            if week > last:
                continue
            for g in games_by_week[week]:
                out.append(self.recap(g))
            br = self.beer_report(week)
            if br:
                out.append(br)
            txs = [t for t in self._live_txs(self.ctx["transactions"].get(week, []))
                   if not is_offseason(t, self.ctx.get("season_start_ms"))]
            for tx in txs:
                if tx.get("type") == "trade":
                    a = self.trade(tx, week)
                    if a:
                        out.append(a)
            wv = self.waivers(txs, week)
            if wv:
                out.append(wv)
            out.append(self.feud(week))
        off = [t for w in sorted(self.ctx["transactions"]) for t in self._live_txs(self.ctx["transactions"][w])
               if is_offseason(t, self.ctx.get("season_start_ms"))]
        oa = self.offseason(off)
        if oa:
            out.append(oa)
        if last >= 1:
            sw = self.standings_watch(last)
            if sw:
                out.append(sw)
        nxt = self.po.get("next_week")
        if nxt and nxt in self.st["schedule"]:
            games = self.st["schedule"][nxt]
            out.extend(self.rivalry_hype(nxt, games))
            for g in games:
                out.append(self.preview(g))
        # Newest first; previews and standings on top of their week.
        order = {"preview": 0, "rivalry": 0, "standings": 1, "shotgun": 2, "offseason": 3, "trade": 3, "waiver": 4, "feud": 5, "recap": 6}
        out.sort(key=lambda a: (-a["week"], order.get(a["type"], 9), a["id"]))
        return out


def generate(ctx: dict, st: dict, po: dict, shotgun_items: list[dict]) -> list[dict]:
    return Newsroom(ctx, st, po, shotgun_items).generate()
