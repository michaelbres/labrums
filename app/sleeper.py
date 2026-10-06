"""Thin Sleeper API client with a disk cache.

The Sleeper API is public and read-only (no auth). Completed weeks never change,
so they're cached permanently; live data is cached for a few minutes. When the
network is down we fall back to whatever is on disk.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

log = logging.getLogger("labrums.sleeper")

BASE = "https://api.sleeper.app/v1"
AVATAR_BASE = "https://sleepercdn.com/avatars/thumbs"

LIVE_TTL = 5 * 60          # league / rosters / users / state / current week
PLAYERS_TTL = 24 * 3600    # the big players blob
FINAL_TTL = 7 * 24 * 3600  # finished weeks: re-pull weekly to pick up stat corrections

PLAYER_FIELDS = ("full_name", "first_name", "last_name", "position", "team",
                 "fantasy_positions", "number", "injury_status", "status", "age")


class SleeperError(RuntimeError):
    pass


class SleeperClient:
    def __init__(self, cache_dir: Path, timeout: float = 20.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    # ---- low level -------------------------------------------------------
    def _cache_path(self, path: str) -> Path:
        safe = path.strip("/").replace("/", "__")
        return self.cache_dir / f"{safe}.json"

    def _read_cache(self, path: str) -> tuple[Any, float] | None:
        p = self._cache_path(path)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as fh:
                blob = json.load(fh)
            return blob["data"], blob["fetched_at"]
        except Exception:  # corrupt cache: ignore it
            return None

    def _write_cache(self, path: str, data: Any) -> None:
        p = self._cache_path(path)
        tmp = p.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"fetched_at": time.time(), "data": data}, fh)
        tmp.replace(p)

    def _fetch(self, path: str) -> Any:
        url = f"{BASE}/{path.strip('/')}"
        req = urllib.request.Request(url, headers={"User-Agent": "labrums/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise SleeperError(f"HTTP {e.code} for {url}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise SleeperError(f"network error for {url}: {e}") from e

    def get(self, path: str, ttl: float = LIVE_TTL, transform=None, ttl_for=None) -> Any:
        """`ttl_for(data) -> seconds` may shorten the ttl based on what was cached."""
        cached = self._read_cache(path)
        if cached is not None:
            data, fetched_at = cached
            eff = ttl_for(data) if ttl_for is not None else ttl
            if time.time() - fetched_at < eff:
                return data
        try:
            data = self._fetch(path)
        except SleeperError as e:
            if cached is not None:
                log.warning("Sleeper unreachable (%s); serving stale cache for %s", e, path)
                return cached[0]
            raise
        if transform is not None:
            data = transform(data)
        self._write_cache(path, data)
        return data

    def clear_cache(self, keep_players: bool = True) -> None:
        """Delete cached API responses (the big players blob is kept by default)."""
        for p in self.cache_dir.glob("*.json"):
            if keep_players and p.name == self._cache_path("players/nfl").name:
                continue
            try:
                p.unlink()
            except OSError as e:
                log.warning("could not delete cache file %s: %s", p, e)

    # ---- endpoints -------------------------------------------------------
    def state(self) -> dict:
        return self.get("state/nfl", LIVE_TTL) or {}

    def league(self, league_id: str) -> dict | None:
        return self.get(f"league/{league_id}", LIVE_TTL)

    def rosters(self, league_id: str) -> list[dict]:
        return self.get(f"league/{league_id}/rosters", LIVE_TTL) or []

    def users(self, league_id: str) -> list[dict]:
        return self.get(f"league/{league_id}/users", LIVE_TTL) or []

    def matchups(self, league_id: str, week: int, final: bool) -> list[dict]:
        ttl = FINAL_TTL if final else LIVE_TTL
        # A week where every row is 0 points hasn't been scored yet: never cache it as final.
        return self.get(f"league/{league_id}/matchups/{week}", ttl,
                        ttl_for=lambda rows: ttl if any(float((r or {}).get("points") or 0) != 0
                                                        for r in rows or []) else LIVE_TTL) or []

    def transactions(self, league_id: str, week: int, final: bool) -> list[dict]:
        return self.get(f"league/{league_id}/transactions/{week}", FINAL_TTL if final else LIVE_TTL) or []

    def winners_bracket(self, league_id: str) -> list[dict]:
        return self.get(f"league/{league_id}/winners_bracket", LIVE_TTL) or []

    def players(self) -> dict[str, dict]:
        """All NFL players, trimmed to the fields we use (the raw blob is ~5MB)."""
        def trim(raw: dict) -> dict:
            out = {}
            for pid, p in (raw or {}).items():
                if not isinstance(p, dict):
                    continue
                out[str(pid)] = {k: p.get(k) for k in PLAYER_FIELDS if p.get(k) is not None}
            return out
        return self.get("players/nfl", PLAYERS_TTL, transform=trim) or {}


def avatar_url(avatar_id: str | None) -> str | None:
    return f"{AVATAR_BASE}/{avatar_id}" if avatar_id else None


def player_label(players: dict[str, dict], pid: str) -> dict:
    """Name / position / team for a player id, with sane fallbacks."""
    if pid in (None, "", "0"):
        return {"player_id": "0", "name": "Empty slot", "position": "—", "team": None}
    p = players.get(str(pid)) or {}
    name = p.get("full_name") or " ".join(x for x in (p.get("first_name"), p.get("last_name")) if x)
    pos = p.get("position") or ((p.get("fantasy_positions") or [None])[0])
    if not name:
        # Team defenses are keyed by team abbreviation.
        name = f"{pid} D/ST" if (pos == "DEF" or (isinstance(pid, str) and pid.isalpha())) else f"Player {pid}"
        pos = pos or "DEF"
    return {"player_id": str(pid), "name": name, "position": pos or "?", "team": p.get("team")}
