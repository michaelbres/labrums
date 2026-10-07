"""Load and normalize config.yaml."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("labrums.config")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("LABRUMS_CONFIG", ROOT / "config.yaml"))
DATA_DIR = Path(os.environ.get("LABRUMS_DATA_DIR", ROOT / "data"))

DEFAULTS: dict[str, Any] = {
    "current_season": None,
    "seasons": {},
    "playoffs": {"teams": None, "simulations": 5000, "prior_games": 3, "division_winners_top_seeds": "auto"},
    "shotguns": {"threshold": 0, "count_empty_slots": True, "include_playoff_weeks": True},
    "special_rules": [],
    "owners": {},
    "rivalries": [],
    "reporters": {"overrides": {}},   # per-voice name/outlet/bio overrides; the 50 staff reporters live in app/newsroom/voices.py
    "narratives": [],         # reporter grudges / crushes: see config.yaml and docs/newsroom.md
    "commissioner": None,     # Sleeper display name of the commissioner (only they may say "I made the rule")
}

UNSET_CATCHPHRASES = {"...", "…", ".", "-", "—"}
STANCES = ("hater", "homer", "skeptic", "hype")
REPORTER_FIELDS = ("name", "outlet", "bio")


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        elif v is not None:
            out[k] = v
    return out


def clean_profile(prof: dict | None) -> dict:
    """Drop unset owner-profile fields: None, empty/blank strings, empty lists."""
    out = {}
    for k, v in (prof or {}).items():
        if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, (list, tuple, dict)) and not v):
            continue
        if k == "catchphrase" and str(v).strip() in UNSET_CATCHPHRASES:
            continue  # "..." means "no catchphrase", not a quote to print
        out[k] = v
    return out


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or CONFIG_PATH
    raw: dict = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    cfg = _merge(DEFAULTS, raw)
    # Normalize season keys to strings and league ids to strings.
    cfg["seasons"] = {str(k): str(v) for k, v in (cfg.get("seasons") or {}).items()}
    if cfg.get("current_season") is not None:
        cfg["current_season"] = str(cfg["current_season"])
    elif cfg["seasons"]:
        cfg["current_season"] = max(cfg["seasons"])
    cfg["commissioner"] = str(cfg["commissioner"]).strip() if cfg.get("commissioner") else None
    cfg["owners"] = {str(k): clean_profile(v) for k, v in (cfg.get("owners") or {}).items()}
    cfg["rivalries"] = [r for r in (cfg.get("rivalries") or []) if r and r.get("owners")]
    rules = []
    for r in cfg.get("special_rules") or []:
        if not r:
            continue
        r = dict(r)
        r["season"] = str(r.get("season", "")) if r.get("season") is not None else ""
        r["owners"] = [str(o) for o in (r.get("owners") or []) if str(o).strip()]
        rules.append(r)
    cfg["special_rules"] = rules
    cfg["reporters"] = {"overrides": normalize_overrides(cfg.get("reporters"))}
    cfg["narratives"] = normalize_narratives(cfg.get("narratives"))
    return cfg


def normalize_overrides(raw: Any) -> dict[str, dict[str, str]]:
    """reporters.overrides -> {voice_id: {name|outlet|bio: non-empty str}}; anything malformed is dropped."""
    block = raw.get("overrides") if isinstance(raw, dict) else None
    out: dict[str, dict[str, str]] = {}
    for vid, fields in (block or {}).items():
        if not isinstance(fields, dict):
            log.warning("config: reporters.overrides.%s must be a mapping; ignored", vid)
            continue
        clean = {k: " ".join(str(v).split()) for k, v in fields.items() if k in REPORTER_FIELDS and v is not None and str(v).strip()}
        if clean:
            out[str(vid)] = clean
    return out


def normalize_narratives(raw: Any) -> list[dict[str, str]]:
    """narratives -> [{reporter, about | player, stance, theme}]; entries that cannot work are dropped with a warning."""
    out: list[dict[str, str]] = []
    for i, n in enumerate(raw if isinstance(raw, list) else []):
        if not isinstance(n, dict):
            continue
        rep = " ".join(str(n.get("reporter") or "").split())
        about = " ".join(str(n.get("about") or "").split())
        player = " ".join(str(n.get("player") or "").split())
        stance = str(n.get("stance") or "").strip().lower()
        if not rep or bool(about) == bool(player) or stance not in STANCES:
            log.warning("config: narratives[%d] needs a reporter, exactly one of about/player and a stance in %s; ignored", i, STANCES)
            continue
        if (stance == "hype") != bool(player):
            log.warning("config: narratives[%d]: 'hype' goes with player:, the other stances with about:; ignored", i)
            continue
        out.append({"reporter": rep, **({"about": about} if about else {"player": player}), "stance": stance,
                    "theme": " ".join(str(n.get("theme") or "").split()).rstrip(".")})
    return out


# ---- storage backend selection ------------------------------------------------
REDIS_ENV_PAIRS = (
    ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"),  # Upstash console
    ("KV_REST_API_URL", "KV_REST_API_TOKEN"),                # Vercel Marketplace integration
    ("LABRUMS_REDIS_URL", "LABRUMS_REDIS_TOKEN"),            # manual override
)


def redis_settings() -> tuple[str, str] | None:
    """(url, token) from the first env var pair where both are non-empty, else None."""
    for url_var, token_var in REDIS_ENV_PAIRS:
        url, token = os.environ.get(url_var, "").strip(), os.environ.get(token_var, "").strip()
        if url and not token:
            log.warning("%s is set but %s is empty; Redis not configured from this pair", url_var, token_var)
            continue
        if url and token:
            if not url.lower().startswith(("http://", "https://")):
                log.warning("%s must start with http:// or https://; Redis not configured from this pair", url_var)
                continue
            return url, token
    return None


def on_vercel() -> bool:
    return bool(os.environ.get("VERCEL"))
