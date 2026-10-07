#!/usr/bin/env python3
"""Export the facts packets for the editorial desk.

    .venv/bin/python scripts/newsroom_facts.py --season 2026 --week 5
    .venv/bin/python scripts/newsroom_facts.py --season 2026 --all-pending

For every generated article of the week this writes: the stable key, the assigned reporter's voice card, the
facts dict, the beats in order, and the current template text (as a reference). Default output is
content/facts/{season}/week-{W}.json (gitignored); `--out -` prints to stdout. `--all-pending` exports every
week that has no content/articles/{season}/week-{W}.json yet.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.newsroom import tools  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--season", help="season (default: current_season from config.yaml)")
    ap.add_argument("--week", type=int, help="week to export")
    ap.add_argument("--all-pending", action="store_true", help="export every week without a desk file")
    ap.add_argument("--out", help="output path (single week only); '-' for stdout")
    args = ap.parse_args()
    if bool(args.week) == bool(args.all_pending):
        ap.error("give exactly one of --week N or --all-pending")
    if args.all_pending and args.out:
        ap.error("--out only applies to --week (pending weeks go to content/facts/{season}/week-{W}.json)")
    season, nr, arts = tools.build(args.season)
    weeks = tools.pending_weeks(season, arts) if args.all_pending else [args.week]
    if not weeks:
        print(f"no pending weeks for {season}", file=sys.stderr)
        return 0
    status = 0
    for wk in weeks:
        data = tools.export_week(season, nr, arts, wk)
        if not data["articles"]:
            print(f"week {wk}: no generated articles", file=sys.stderr)
            status = 1
            continue
        if args.out == "-":
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
            print()
            continue
        path = Path(args.out) if args.out else ROOT / "content" / "facts" / season / f"week-{wk}.json"
        tools.write_json(path, data)
        print(f"week {wk}: {len(data['articles'])} articles -> {path}", file=sys.stderr)
    return status


if __name__ == "__main__":
    sys.exit(main())
