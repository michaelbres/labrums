"""The editorial desk: hand-written articles that override template articles by stable key.

Files live in content/articles/{season}/week-{W}.json:

    {"week": W, "articles": [{"key": "...", "headline": "...", "dek": "...", "body": ["...", ...],
                              "reporter": {"name", "outlet", "bio"}, "tags": [...], "publish_on": "YYYY-MM-DD"}]}

`key`, `headline` and `body` are required; the rest are optional (default: the assigned reporter, the template
dek/tags/publish_on). A desk article replaces headline/dek/body/reporter/byline in place and is marked
source == "desk" (every other article is source == "template"). Unknown keys are logged and ignored; an article
that fails validation or the coherence lint is skipped with a warning and the template stays.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

from ..config import ROOT
from . import lint

log = logging.getLogger("labrums.newsroom.desk")

CONTENT_DIR = ROOT / "content" / "articles"

_cache: dict[tuple[str, str], tuple[tuple, list[dict]]] = {}


def clear_cache() -> None:
    _cache.clear()


def season_dir(season: str) -> Path:
    return Path(CONTENT_DIR) / str(season)


def desk_files(season: str) -> list[Path]:
    d = season_dir(season)
    return sorted(d.glob("week-*.json")) if d.is_dir() else []


def _week_of(path: Path) -> int | None:
    m = re.fullmatch(r"week-(\d+)\.json", path.name)
    return int(m.group(1)) if m else None


def read_file(path: Path) -> tuple[dict | None, str | None]:
    """(parsed file, error). The shape is checked here; per-article validation happens in `check`."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"cannot read {path}: {e}"
    if not isinstance(data, dict) or not isinstance(data.get("articles"), list):
        return None, f"{path}: expected an object with an 'articles' list"
    return data, None


def load(season: str) -> list[dict]:
    """Every desk entry for the season (flat list, each tagged with its file's week). Cached per process while
    the files are unchanged; `clear_cache()` (called on refresh) forces a re-read."""
    files = desk_files(season)
    sig = tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in files)
    hit = _cache.get((str(CONTENT_DIR), str(season)))
    if hit and hit[0] == sig:
        return hit[1]
    out: list[dict] = []
    for f in files:
        data, err = read_file(f)
        if err:
            log.warning("desk: %s", err)
            continue
        for i, e in enumerate(data["articles"]):
            if isinstance(e, dict):
                out.append({**e, "_file": f.name, "_week": data.get("week", _week_of(f)), "_idx": i})
            else:
                log.warning("desk: %s article %d is not an object", f.name, i)
    _cache[(str(CONTENT_DIR), str(season))] = (sig, out)
    return out


def weeks_with_files(season: str) -> set[int]:
    return {w for w in (_week_of(f) for f in desk_files(season)) if w is not None}


# ---------------------------------------------------------------- validation
def validate_entry(e: dict) -> list[str]:
    """Structural problems with one desk entry (empty list = fine)."""
    bad: list[str] = []
    if not isinstance(e.get("key"), str) or not e["key"].strip():
        bad.append("missing 'key'")
    if not isinstance(e.get("headline"), str) or not e["headline"].strip():
        bad.append("empty headline")
    body = e.get("body")
    if not isinstance(body, list) or not body or not all(isinstance(p, str) and p.strip() for p in body):
        bad.append("body must be a non-empty list of non-empty strings")
    if "dek" in e and (not isinstance(e["dek"], str) or not e["dek"].strip()):
        bad.append("dek, if present, must be a non-empty string")
    texts = [e.get("headline"), e.get("dek"), *(body if isinstance(body, list) else [])]
    if any(isinstance(t, str) and ("{" in t or "}" in t) for t in texts):
        bad.append("contains '{' or '}'")
    r = e.get("reporter")
    if r is not None and not (isinstance(r, dict) and all(isinstance(r.get(k), str) and r[k].strip() for k in ("name", "outlet", "bio"))):
        bad.append("reporter needs name, outlet and bio")
    tags = e.get("tags")
    if tags is not None and not (isinstance(tags, list) and all(isinstance(t, str) for t in tags)):
        bad.append("tags must be a list of strings")
    po = e.get("publish_on")
    if po is not None:
        try:
            date.fromisoformat(str(po))
        except ValueError:
            bad.append("publish_on must be an ISO date")
    return bad


def _reporter_card(r: dict) -> dict:
    from .voices import VOICES
    for v in VOICES:
        if v.name == r["name"]:
            return {**v.card(), "outlet": r["outlet"], "bio": r["bio"]}
    slug = re.sub(r"[^a-z0-9]+", "-", r["name"].lower()).strip("-") or "guest"
    return {"id": f"guest-{slug}", "name": r["name"], "outlet": r["outlet"], "bio": r["bio"], "family": "guest"}


def _candidate(a: dict, e: dict) -> dict:
    """The article as it would read with the desk text, for the coherence lint. The template's per-paragraph
    game metadata no longer lines up with a hand-written body, so it is dropped (headline class checks stay)."""
    c = dict(a)
    c.update(headline=e["headline"].strip(), dek=(e.get("dek") or a["dek"]).strip(), body=[p.strip() for p in e["body"]])
    facts = dict(a.get("facts") or {})
    facts["paras"] = []
    facts["headline_favorite"] = None
    c["facts"] = facts
    return c


def check(a: dict, e: dict, book=None) -> list[str]:
    """All problems that would keep desk entry `e` from replacing article `a` (empty list = it will be used)."""
    bad = validate_entry(e)
    if bad:
        return bad
    probs = lint.check(_candidate(a, e), book)
    return [p.split(": ", 1)[-1] for p in probs]


def _replace(a: dict, e: dict) -> None:
    a["headline"] = e["headline"].strip()
    if e.get("dek"):
        a["dek"] = e["dek"].strip()
    a["body"] = [p.strip() for p in e["body"]]
    if e.get("reporter"):
        a["reporter"] = _reporter_card(e["reporter"])
        a["byline"] = f"{a['reporter']['name']}, {a['reporter']['outlet']}"
    if e.get("tags"):
        a["tags"] = list(e["tags"])
    if e.get("publish_on"):
        a["publish_on"] = str(e["publish_on"])
    facts = dict(a.get("facts") or {})
    facts["paras"] = [{} for _ in a["body"]]
    a["facts"] = facts
    a["source"] = "desk"


def apply(arts: list[dict], season: str, book=None) -> list[dict]:
    """Replace template articles with their desk versions (in place). Returns one report row per desk entry."""
    by_key = {a["key"]: a for a in arts if a.get("key")}
    report: list[dict] = []
    for e in load(season):
        key = e.get("key")
        row = {"file": e["_file"], "key": key, "ok": False, "problems": []}
        report.append(row)
        a = by_key.get(key)
        if a is None:
            row["problems"] = ["unknown key (no generated article has it)"]
            log.warning("desk: %s: unknown key %r ignored", e["_file"], key)
            continue
        probs = check(a, e, book)
        if probs:
            row["problems"] = probs
            log.warning("desk: %s: skipped %s: %s", e["_file"], key, "; ".join(probs))
            continue
        _replace(a, e)
        row["ok"] = True
    return report
