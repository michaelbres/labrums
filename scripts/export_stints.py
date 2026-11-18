#!/usr/bin/env python3
"""Write the player stints table (who was rostered by whom, when) as CSV.

Usage: uv run python scripts/export_stints.py [out.csv]   (default data/stints.csv)
Honors LABRUMS_DEMO=1 like the app.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import DATA_DIR, load_config  # noqa: E402
from app.loader import discover_seasons, load_draft_picks, load_season  # noqa: E402
from app.network import build_stints  # noqa: E402
from app.sleeper import SleeperClient  # noqa: E402

COLUMNS = ["player_id", "player", "position", "owner_id", "owner", "team_name", "season",
           "start_week", "end_week", "weeks", "acquired_via"]


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else DATA_DIR / "stints.csv"
    cfg = load_config()
    if os.environ.get("LABRUMS_DEMO", "").lower() in ("1", "true", "yes"):
        from app.demo import DemoClient
        client = DemoClient(current_week=int(os.environ.get("LABRUMS_DEMO_WEEK", 7)))
        cfg["seasons"] = {"2026": "demo2026"}
        cfg["current_season"] = "2026"
    else:
        client = SleeperClient(DATA_DIR / "cache")
    loaded, drafts = [], {}
    for info in sorted(discover_seasons(client, cfg), key=lambda s: s["season"]):
        try:
            s = load_season(client, cfg, info["league_id"])
        except Exception as e:
            print(f"skipping {info['season']}: {e}", file=sys.stderr)
            continue
        loaded.append(s)
        drafts[s["season"]] = load_draft_picks(client, info["league_id"])
    stints = build_stints(loaded, drafts)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(stints)
    print(f"wrote {len(stints)} stints from {len(loaded)} seasons to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
