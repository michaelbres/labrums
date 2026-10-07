"""Reporter overrides and narratives (config.yaml: `reporters.overrides`, `narratives`).

A narrative is a reporter's take on an owner (hater / homer / skeptic) or a player (hype). It only ever changes how
facts are framed and which of them get picked; every number, score and name still comes from the data.
"""
from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass

from typing import TYPE_CHECKING

from .. import shotguns

if TYPE_CHECKING:   # voices.py imports this module at its end, so it must not import voices at load time
    from .voices import Voice

log = logging.getLogger("labrums.newsroom")

_WARNED: set[str] = set()


def _warn_once(msg: str, *args) -> None:
    """The site rebuilds its newsroom often (and demo mode never resolves the real owners): say it once per process."""
    text = msg % args
    if text not in _WARNED:
        _WARNED.add(text)
        log.warning("%s", text)
HONORIFICS = {"dr.", "sir", "hon.", "mr.", "mrs.", "ms.", "prof."}


@dataclass(frozen=True)
class Narrative:
    voice_id: str
    stance: str                  # hater | homer | skeptic | hype
    theme: str                   # one-line thesis ("" when none)
    kind: str                    # "owner" | "player"
    label: str                   # what articles call the target ("Patrick", "Quentin Johnston")
    rid: int | None = None       # owner narratives: the target's roster id
    player: str | None = None    # hype narratives: the player's name


def apply_overrides(cfg: dict) -> list[Voice]:
    """The 50 staff voices with config `reporters.overrides` applied (unknown voice ids are ignored with a warning)."""
    from .voices import BASE_VOICES
    rep = (cfg or {}).get("reporters")
    ov = (rep.get("overrides") if isinstance(rep, dict) else None) or {}
    ids = {v.id for v in BASE_VOICES}
    for vid in ov:
        if vid not in ids:
            _warn_once("config: reporters.overrides.%s is not a voice id; ignored", vid)
    out = []
    for v in BASE_VOICES:
        fields = {k: str(x) for k, x in (ov.get(v.id) or {}).items() if k in ("name", "outlet", "bio") and str(x).strip()}
        out.append(dataclasses.replace(v, **fields) if fields else v)
    names = [v.name.casefold() for v in out]
    if len(set(names)) != len(names):
        _warn_once("config: two reporters share a name after reporters.overrides; narratives may pick the wrong one")
    return out


def find_voice(voices: list[Voice], key: str) -> Voice | None:
    k = " ".join(str(key or "").split()).casefold()
    for v in voices:
        if k in (v.id.casefold(), v.name.casefold()):
            return v
    return None


def _owner_from_config(cfg: dict, about: str) -> str | None:
    """The label for an owner named in the config (display name / user id key, or the profile name), else None."""
    k = about.casefold()
    for key, prof in (cfg.get("owners") or {}).items():
        label = str((prof or {}).get("name") or key)
        if k in (str(key).casefold(), label.casefold()):
            return label
    return None


def resolve(cfg: dict, voices: list[Voice], teams: dict | None = None, *, warn: bool = True) -> list[Narrative]:
    """Narratives whose reporter and owner exist. `teams` (roster id -> team) resolves owners against the league;
    without it, owners are checked against the config's `owners` block (enough for the masthead)."""
    out: list[Narrative] = []
    for n in (cfg or {}).get("narratives") or []:
        v = find_voice(voices, n.get("reporter"))
        if v is None:
            if warn:
                _warn_once("narrative ignored: unknown reporter %r", n.get("reporter"))
            continue
        stance, theme = n["stance"], n.get("theme") or ""
        if n.get("player"):
            out.append(Narrative(v.id, stance, theme, "player", str(n["player"]), None, str(n["player"])))
            continue
        about = str(n.get("about") or "")
        if teams is not None:
            rid = shotguns.team_by_name({"teams": teams}, about)
            label = (str(teams[rid].get("name") or teams[rid]["display_name"]).strip()) if rid is not None else None
        else:
            rid, label = None, _owner_from_config(cfg, about)
        if label is None:
            if warn:
                _warn_once("narrative ignored: unknown owner %r", about)
            continue
        out.append(Narrative(v.id, stance, theme, "owner", label, rid))
    return out


def known_for(n: Narrative) -> str:
    """The masthead line for a narrative reporter (shown after 'Known for:')."""
    if n.theme:
        return n.theme
    return {"hater": f"a well-documented grudge against {n.label}",
            "homer": f"unwavering faith in {n.label}",
            "skeptic": f"a standing doubt about {n.label}",
            "hype": f"a long campaign on behalf of {n.label}"}[n.stance]


def with_known_for(voices: list[Voice], narrs: list[Narrative]) -> list[Voice]:
    by: dict[str, list[str]] = {}
    for n in narrs:
        by.setdefault(n.voice_id, []).append(known_for(n))
    return [dataclasses.replace(v, known_for="; ".join(by[v.id])) if v.id in by else v for v in voices]


def staff(cfg: dict, teams: dict | None = None, *, warn: bool = True) -> tuple[list[Voice], list[Narrative]]:
    """(voices with overrides and `known_for`, resolved narratives) for a config."""
    voices = apply_overrides(cfg)
    narrs = resolve(cfg, voices, teams, warn=warn)
    return with_known_for(voices, narrs), narrs
