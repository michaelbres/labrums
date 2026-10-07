"""Thin Sleeper API client with a pluggable cache (disk by default, Redis on Vercel).

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


class DiskCache:
    """One JSON file per API path under `cache_dir`. The directory is created on first write."""

    def __init__(self, cache_dir: Path | str):
        self.cache_dir = Path(cache_dir)

    def path_for(self, path: str) -> Path:
        safe = path.strip("/").replace("/", "__")
        return self.cache_dir / f"{safe}.json"

    def read(self, path: str) -> tuple[Any, float] | None:
        p = self.path_for(path)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as fh:
                blob = json.load(fh)
            return blob["data"], blob["fetched_at"]
        except Exception:  # corrupt cache: ignore it
            return None

    def write(self, path: str, data: Any, fetched_at: float) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        p = self.path_for(path)
        tmp = p.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"fetched_at": fetched_at, "data": data}, fh)
        tmp.replace(p)

    def delete_matching(self, predicate) -> None:
        if not self.cache_dir.is_dir():
            return
        for p in self.cache_dir.glob("*.json"):
            if not predicate(p.stem.replace("__", "/")):
                continue
            try:
                p.unlink()
            except OSError as e:
                log.warning("could not delete cache file %s: %s", p, e)


class SleeperClient:
    def __init__(self, cache: Any, timeout: float = 20.0):
        """`cache` is a backend with read/write/delete_matching, or a directory (-> DiskCache)."""
        self.cache = cache if hasattr(cache, "delete_matching") else DiskCache(cache)
        self.timeout = timeout
        self._players: tuple[float, dict] | None = None  # in-process memo of the trimmed players dict

    # ---- low level -------------------------------------------------------
    def _cache_path(self, path: str) -> Path:
        return self.cache.path_for(path)  # disk backend only

    def _read_cache(self, path: str) -> tuple[Any, float] | None:
        return self.cache.read(path)

    def _write_cache(self, path: str, data: Any) -> None:
        self.cache.write(path, data, time.time())

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

    def clear_cache(self, keep_players: bool = True, league_id: str | None = None) -> None:
        """Delete cached API responses so the next build re-pulls from Sleeper.

        With `league_id`, only that league's entries (plus the NFL state) are removed,
        so other seasons keep their offline fallback. The players blob is kept by default.
        """
        prefix = f"league/{league_id}" if league_id else None

        def doomed(path: str) -> bool:
            if keep_players and path == "players/nfl":
                return False
            if prefix and not (path == prefix or path.startswith(prefix + "/") or path.startswith("state/")):
                return False
            return True

        self.cache.delete_matching(doomed)

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
        memo = self._players
        if memo is not None and time.time() - memo[0] < PLAYERS_TTL:
            return memo[1]
        out = self.get("players/nfl", PLAYERS_TTL, transform=trim) or {}
        if out:
            self._players = (time.time(), out)
        return out


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
