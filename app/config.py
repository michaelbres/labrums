"""Load and normalize config.yaml."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

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
    "reporters": ["The Beat Writer", "Anonymous League Source"],
}


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
    return cfg
