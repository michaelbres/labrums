#!/usr/bin/env python3
"""Validate a desk file against the generated articles.

    .venv/bin/python scripts/newsroom_lint.py content/articles/2026/week-5.json [--season 2026]

Prints PASS/FAIL per article (key, coherence-lint rules, required fields) and WARN lines for soft rules such as
word counts. Exit code 1 if any article fails. The season comes from the parent folder name (content/articles/2026/)
or --season (default: current_season from config.yaml).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.newsroom import tools  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("--season")
    args = ap.parse_args()
    if not args.file.is_file():
        print(f"FAIL {args.file}: no such file")
        return 1
    from app.config import load_config
    default = str(load_config().get("current_season"))
    season, nr, arts = tools.build(args.season or tools.season_of(args.file, default))
    rows = tools.check_file(args.file, arts, nr)
    failed = 0
    for r in rows:
        label = r["key"] or f"article #{r['index']}"
        if r["ok"]:
            print(f"PASS {label}")
        else:
            failed += 1
            print(f"FAIL {label}")
            for p in r["problems"]:
                print(f"     - {p}")
        for w in r["warnings"]:
            print(f"     WARN {w}")
    print(f"{len(rows) - failed}/{len(rows)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
