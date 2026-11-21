"""The beat reporters: one per team, a roster SEPARATE from the 50 staff voices (voices.py).

A beat reporter covers exactly one team and writes exactly one article type (`beat`, the weekly team report); the
staff Assigner never sees them and they never write another beat. They are bound to a team by OWNER identity, the
same key config.yaml `owners` uses (the Sleeper display name, or the Sleeper user_id), never by roster id or team name.

config.yaml `reporters.beat` renames or re-outlets any of them, keyed by owner:

    reporters:
      beat:
        PatrickHanrahan: {name: "Laurel Hanrahan", outlet: "...", bio: "..."}   # outlet and bio are optional

Built-in placeholders (invented names) cover everyone else. A league whose owners are not in the built-in table
(demo mode, an old season, a new owner) still gets one reporter per team: the unclaimed placeholders are dealt out
deterministically (by a hash of the owner key, so the same owners always get the same reporters).
"""
from __future__ import annotations

import dataclasses
import hashlib
import logging
from dataclasses import dataclass

log = logging.getLogger("labrums.newsroom")

STRUCTURES = ("verdict", "grade", "notebook", "questions", "ledger")


@dataclass(frozen=True)
class BeatReporter:
    id: str
    name: str
    outlet: str
    bio: str
    owner: str            # the owner this placeholder covers by default (lowercased Sleeper display name), "" = none
    column: str           # the name of this reporter's regular notebook
    favs: tuple           # the two article structures this reporter reaches for most often
    openers: tuple
    closers: tuple
    tics: tuple
    known_for: str = ""   # "Covers <team>", set once the reporter is attached to a team

    def card(self) -> dict:
        return {"id": self.id, "name": self.name, "outlet": self.outlet, "bio": self.bio, "family": "beat",
                "known_for": self.known_for}


def _b(id, owner, name, outlet, bio, column, favs, openers, closers, tics) -> BeatReporter:
    assert set(favs) <= set(STRUCTURES)
    return BeatReporter(id, name, outlet, bio, owner.casefold(), column, tuple(favs), tuple(openers), tuple(closers), tuple(tics))


# Names and outlets are invented. Openers/closers/tics never state a fact about the league.
BEAT_VOICES: list[BeatReporter] = [
    _b("beat-brindlemoor", "michaelbreslow", "Odessa Brindlemoor", "The Sentinel-Ledger",
       "Treats every lineup decision as a line item and every owner as an audit.", "Brindlemoor's Ledger", ("ledger", "grade"),
       ["From the beat desk:", "For the record, and the record is unkind:"],
       ["The ledger will be updated next week, whether or not the owner is.", "Filed from the press box, which has the best view of the bench."],
       ["Receipts available on request.", "Make of that what you will; I did."]),
    _b("beat-pennywhistle", "JimmyWoods10", "Walt Pennywhistle", "Northside Courier-Post",
       "Has covered one team since before the waiver wire had a deadline and holds a grudge about all of it.", "The Pennywhistle Report", ("verdict", "notebook"),
       ["Pull up a chair, folks.", "Well, here we are again."],
       ["That's the beat, and I'm stuck with it.", "See you next week, same bad time, same bad channel."],
       ["Mark my words.", "I've seen this movie."]),
    _b("beat-okafor-lund", "colonbuns", "Tamsin Okafor-Lund", "The Harbor Standard",
       "Quantifies disappointment to two decimal places and still finds it understated.", "Standard Deviations", ("ledger", "questions"),
       ["The data, such as it is:", "Run the numbers and weep:"],
       ["Sample size noted. Sympathy not included.", "The model has been consulted. The model declined to comment."],
       ["(Methodology: watching.)", "Variance is not an alibi."]),
    _b("beat-vossberg", "cianmahoney", "Ignatius Vossberg", "The Meridian Telegraph",
       "Files from wherever the owner last was, which is rarely the lineup page.", "Vossberg Abroad", ("notebook", "questions"),
       ["Dateline: the group chat.", "Reporting from the front lines of a lineup:"],
       ["More from the field as the situation deteriorates.", "I will file again when I am able."],
       ["I have seen the lineup. I am not able to say more.", "The situation remains fluid, and not in a good way."]),
    _b("beat-quillfeather", "PatrickHanrahan", "Dale Quillfeather", "The Daily Gazette-Herald",
       "A sports-page lifer who only has one team to cover and plenty to say about it.", "Quillfeather's Corner", ("verdict", "grade"),
       ["Hot off the beat:", "Stop the presses:"],
       ["Thirty. (That is how we used to end a story.)", "That's the story. Go read the standings."],
       ["In this reporter's long experience, this does not get better.", "Write that down."]),
    _b("beat-fenwick-hart", "trottner", "Marisol Fenwick-Hart", "The Lakeview Dispatch",
       "Live-blogs every Sunday and has never once been pleased.", "The Fenwick-Hart Wire", ("questions", "verdict"),
       ["UPDATE:", "Breaking, in the sense that it broke:"],
       ["Refresh for more disappointment.", "We will keep you posted, whether you like it or not."],
       ["(More as it develops.)", "Stay tuned. Nobody asked you to, but stay tuned."]),
    _b("beat-abernathy-pike", "styerech", "Cornelius Abernathy-Pike", "The Metro Daily Bulletin",
       "Writes headlines first and finds the facts that fit.", "Pike's Peek", ("grade", "notebook"),
       ["Exclusive:", "Developing:"],
       ["You read it here first, unfortunately.", "No further questions."],
       ["Shocking, yes. Surprising, no.", "Draw your own conclusions; I drew mine."]),
    _b("beat-calloway-strand", "bowieshreiber", "Beatrix Calloway-Strand", "The Evening Beacon",
       "A literary columnist serving a sentence on the fantasy desk.", "Strand Notes", ("notebook", "verdict"),
       ["There is a particular sadness to this beat:", "Some weeks write themselves. This one filed a complaint."],
       ["Next week, hope. It is a small word.", "And so the season goes on, as seasons do."],
       ["One does not choose the beat; the beat chooses.", "I have been asked to be fair. I am trying."]),
    _b("beat-linwood", "asinagra25", "Hobart Linwood", "The Valley Courier",
       "A professional optimist who has been forced to find new material.", "Linwood Looks Up", ("questions", "ledger"),
       ["Look, I want to be positive.", "I came in with an open mind."],
       ["I will remain optimistic, professionally.", "Better days ahead, or at least different ones."],
       ["(I tried to find a bright side. I am still looking.)", "To be fair, and I am trying to be fair:"]),
    _b("beat-strathmore", "ncarney7502", "Imelda Strathmore", "The County Docket",
       "Covers the beat like a prosecutor: the evidence first, the verdict after.", "The Strathmore Docket", ("grade", "ledger"),
       ["The court has reviewed the tape.", "Exhibit A is the box score."],
       ["The court is adjourned. The owner is not acquitted.", "Appeal denied."],
       ["Objection overruled.", "The evidence speaks for itself, and it is loud."]),
]


def _norm(s) -> str:
    return " ".join(str(s or "").split()).casefold()


def _hash(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def _owner_keys(t: dict) -> list[str]:
    return [k for k in (_norm(t.get("display_name")), _norm(t.get("owner_id"))) if k]


def _team_for(teams: dict, key: str) -> int | None:
    """The roster whose owner a config key names: Sleeper display name or user_id first, then the profile / team name."""
    k = _norm(key)
    if not k:
        return None
    for rid in sorted(teams):
        if k in _owner_keys(teams[rid]):
            return rid
    for rid in sorted(teams):
        t = teams[rid]
        if k in (_norm(t.get("name")), _norm(t.get("team_name")), _norm(t.get("profile", {}).get("name") if isinstance(t.get("profile"), dict) else "")):
            return rid
    return None


def assign(cfg: dict | None, teams: dict) -> dict[int, BeatReporter]:
    """roster id -> the beat reporter covering that team, with config `reporters.beat` applied."""
    from ..config import normalize_beat
    rep = (cfg or {}).get("reporters")
    over = normalize_beat(rep.get("beat") if isinstance(rep, dict) else None)
    out: dict[int, BeatReporter] = {}
    taken: set[str] = set()
    for rid in sorted(teams):                       # 1. the built-in owner bindings
        keys = _owner_keys(teams[rid])
        for v in BEAT_VOICES:
            if v.owner and v.owner in keys and v.id not in taken:
                out[rid] = v
                taken.add(v.id)
                break
    free = [v for v in BEAT_VOICES if v.id not in taken]
    rest = sorted((r for r in teams if r not in out),
                  key=lambda r: (_hash(next(iter(_owner_keys(teams[r])), str(r))), r))
    for i, rid in enumerate(rest):                  # 2. everyone else: unclaimed placeholders, dealt out deterministically
        out[rid] = free[i] if i < len(free) else BEAT_VOICES[i % len(BEAT_VOICES)]
    for key, fields in over.items():                # 3. config renames
        rid = _team_for(teams, key)
        if rid is None:
            log.debug("config: reporters.beat.%s matches no owner in this league", key)
            continue
        out[rid] = dataclasses.replace(out[rid], **fields)
    for rid, v in out.items():
        t = teams[rid]
        label = str(t.get("name") or t.get("display_name") or "").strip()
        tn = " ".join(str(t.get("team_name") or "").split())
        out[rid] = dataclasses.replace(v, known_for=f"Covers {tn} ({label})" if tn else f"Covers {label}")
    return out
