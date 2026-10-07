"""Helpers behind scripts/newsroom_facts.py and scripts/newsroom_lint.py (the editorial desk's tooling)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import desk, families
from .voices import BY_ID

WORDS = {"recap": (180, 320), "preview": (180, 320)}   # everything else: 120-220
DEFAULT_WORDS = (120, 220)


def build(season: str | None = None):
    """(season, newsroom, template articles) for the configured league, exactly as the site builds them but
    without desk overrides (the template text is the reference a writer starts from)."""
    from .. import main
    from . import Newsroom
    st = main.state
    season = str(season or st.cfg.get("current_season"))
    m = st.base_model(season)
    nr = Newsroom(m["ctx"], m["stats"], m["playoffs"], m["shotgun_items"])
    return season, nr, nr.generate(use_desk=False)


def voice_card(reporter: dict) -> dict:
    v = BY_ID.get(reporter.get("id"))
    card = {k: reporter.get(k) for k in ("name", "outlet", "bio", "family")}
    if v is None:
        return card
    fam = families.get(v.family)
    card.update(family_label=fam.label, family_description=fam.desc, sentence_rhythm=fam.rhythm, formality=fam.formality,
                metaphor_domain=fam.metaphors, numbers=fam.numbers, signature_openers=list(v.openers),
                signature_closers=list(v.closers), verbal_tics=list(v.tics), beats=sorted(v.beats))
    return card


def word_target(kind: str) -> tuple[int, int]:
    return WORDS.get(kind, DEFAULT_WORDS)


def export_week(season: str, nr, arts: list[dict], week: int) -> dict:
    """Everything a writer needs for one week: per article the key, assigned reporter's voice card, the facts
    packet, the beats in order, and the current template text."""
    out = []
    for a in sorted((x for x in arts if x["week"] == week), key=lambda x: (x["publish_on"], x["type"], x["key"])):
        facts = dict(a["facts"])
        beats = facts.pop("beats", [])
        facts.pop("paras", None)   # per-paragraph bookkeeping for the template lint, not for writers
        lo, hi = word_target(a["type"])
        out.append({"key": a["key"], "type": a["type"], "week": a["week"], "publish_on": a["publish_on"],
                    "teams": [nr.name(r) for r in a["teams"]], "reporter": voice_card(a["reporter"]),
                    "target_words": {"min": lo, "max": hi}, "facts": facts, "beats": beats,
                    "template": {"headline": a["headline"], "dek": a["dek"], "body": a["body"]}})
    owners = []
    for rid, t in sorted(nr.teams.items()):
        prof = t.get("profile") or {}
        owners.append({"roster_id": rid, "name": nr.name(rid), "team_name": nr.tname(rid), "nickname": prof.get("nickname"),
                       "traits": prof.get("traits") or [], "catchphrase": prof.get("catchphrase")})
    return {"season": season, "week": week, "format": "see docs/newsroom.md", "owners": owners, "articles": out}


def weeks_with_articles(arts: list[dict]) -> list[int]:
    return sorted({a["week"] for a in arts})


def pending_weeks(season: str, arts: list[dict]) -> list[int]:
    done = desk.weeks_with_files(season)
    return [w for w in weeks_with_articles(arts) if w not in done]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def season_of(path: Path, default: str) -> str:
    """content/articles/2026/week-4.json -> "2026"; anything else falls back to `default`."""
    return path.resolve().parent.name if re.fullmatch(r"\d{4}", path.resolve().parent.name) else default


def check_file(path: Path, arts: list[dict], book) -> list[dict]:
    """One row per desk entry: {index, key, ok, problems, warnings}. A file that cannot be parsed is one failed row."""
    data, err = desk.read_file(path)
    if err:
        return [{"index": 0, "key": None, "ok": False, "problems": [err], "warnings": []}]
    by_key = {a["key"]: a for a in arts}
    rows, seen = [], set()
    for i, e in enumerate(data["articles"]):
        e = e if isinstance(e, dict) else {}
        key = e.get("key")
        probs: list[str] = []
        warns: list[str] = []
        a = by_key.get(key)
        if a is None:
            probs.append(f"unknown key {key!r} (run scripts/newsroom_facts.py to see the valid keys)")
        else:
            probs += desk.check(a, e, book)
            if key in seen:
                warns.append("duplicate key in this file: the later entry wins")
            if data.get("week") is not None and a["week"] != data["week"]:
                warns.append(f"article belongs to week {a['week']} but the file says week {data['week']}")
            body = e.get("body")
            if isinstance(body, list) and all(isinstance(p, str) for p in body):
                n = len(" ".join(body).split())
                lo, hi = word_target(a["type"])
                if not lo <= n <= hi:
                    warns.append(f"{n} words; target for a {a['type']} is {lo}-{hi}")
        seen.add(key)
        rows.append({"index": i, "key": key, "ok": not probs, "problems": probs, "warnings": warns})
    return rows
