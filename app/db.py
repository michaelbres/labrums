"""SQLite persistence for shotgun check-offs and manually added shotguns."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS shotgun_completions (
    key TEXT PRIMARY KEY,
    season TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    note TEXT
);
CREATE TABLE IF NOT EXISTS manual_shotguns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season TEXT NOT NULL,
    week INTEGER NOT NULL,
    roster_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(SCHEMA)

    def completed(self, season: str) -> dict[str, dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key, completed_at, note FROM shotgun_completions WHERE season = ?", (season,)).fetchall()
        return {r["key"]: {"completed_at": r["completed_at"], "note": r["note"]} for r in rows}

    def set_completed(self, season: str, key: str, done: bool, note: str | None = None) -> bool:
        with self._lock, self._conn:
            if done:
                self._conn.execute(
                    "INSERT OR REPLACE INTO shotgun_completions(key, season, completed_at, note) VALUES (?,?,?,?)",
                    (key, season, _now(), note))
            else:
                self._conn.execute("DELETE FROM shotgun_completions WHERE key = ?", (key,))
        return done

    def toggle(self, season: str, key: str) -> bool:
        with self._lock:
            row = self._conn.execute("SELECT 1 FROM shotgun_completions WHERE key = ?", (key,)).fetchone()
        return self.set_completed(season, key, row is None)

    def manual(self, season: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM manual_shotguns WHERE season = ? ORDER BY week, roster_id, id", (season,)).fetchall()
        return [dict(r) for r in rows]

    def add_manual(self, season: str, week: int, roster_id: int, label: str, detail: str | None = None) -> dict:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO manual_shotguns(season, week, roster_id, label, detail, created_at) VALUES (?,?,?,?,?,?)",
                (season, int(week), int(roster_id), label, detail, _now()))
            mid = cur.lastrowid
        return {"id": mid, "season": season, "week": week, "roster_id": roster_id, "label": label, "detail": detail}

    def delete_manual(self, season: str, manual_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM manual_shotguns WHERE id = ? AND season = ?", (manual_id, season))
            self._conn.execute("DELETE FROM shotgun_completions WHERE key = ? AND season = ?",
                               (f"{season}:manual:{manual_id}", season))


def manual_to_items(season: str, rows: list[dict]) -> list[dict]:
    return [{
        "key": f"{season}:manual:{r['id']}", "season": season, "week": r["week"], "roster_id": r["roster_id"],
        "slot": "MANUAL", "player": {"player_id": None, "name": r["label"], "position": "MANUAL", "team": None},
        "points": None, "reason": "manual", "label": r["label"], "detail": r.get("detail"), "manual_id": r["id"],
    } for r in rows]
