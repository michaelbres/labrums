"""Redis-backed persistence: RedisStore (shotgun check-offs) and RedisCache (Sleeper responses).

Both share one UpstashRedis client and keep no mutable state, so they are thread-safe.
"""
from __future__ import annotations

import base64
import json
import logging
import zlib
from datetime import datetime, timezone
from typing import Any, Callable

from .redis_client import RedisError, UpstashRedis, key_prefix

log = logging.getLogger("labrums.storage")

# Keys outlive the longest ttl (7 days for finished weeks) by a day; freshness is judged by fetched_at.
CACHE_EXPIRE_SECONDS = 8 * 24 * 3600
MAX_BLOB_BYTES = 1_000_000  # keep every cached value under 1 MB after compression


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pairs(flat: list | dict | None) -> dict[str, str]:
    """HGETALL comes back as a flat [field, value, ...] list (or a dict with RESP3)."""
    if not flat:
        return {}
    if isinstance(flat, dict):
        return {str(k): v for k, v in flat.items()}
    return {str(flat[i]): flat[i + 1] for i in range(0, len(flat) - 1, 2)}


class RedisStore:
    """Same interface as db.Store."""

    def __init__(self, redis: UpstashRedis, prefix: str | None = None):
        self.r = redis
        self.p = key_prefix(prefix)

    def _comp(self, season: str) -> str:
        return f"{self.p}completions:{season}"

    def _man(self, season: str) -> str:
        return f"{self.p}manual:{season}"

    def completed(self, season: str) -> dict[str, dict]:
        out = {}
        for key, raw in _pairs(self.r.cmd("HGETALL", self._comp(season))).items():
            try:
                v = json.loads(raw)
            except (TypeError, ValueError):
                v = {}
            out[key] = {"completed_at": v.get("completed_at"), "note": v.get("note")}
        return out

    def set_completed(self, season: str, key: str, done: bool, note: str | None = None) -> bool:
        if done:
            self.r.cmd("HSET", self._comp(season), key, json.dumps({"completed_at": _now(), "note": note}))
        else:
            self.r.cmd("HDEL", self._comp(season), key)
        return done

    def toggle(self, season: str, key: str) -> bool:
        # HSETNX is atomic: it only writes when the field is absent, so two racing toggles cannot both "complete".
        added = self.r.cmd("HSETNX", self._comp(season), key, json.dumps({"completed_at": _now(), "note": None}))
        if added:
            return True
        self.r.cmd("HDEL", self._comp(season), key)
        return False

    def manual(self, season: str) -> list[dict]:
        rows = []
        for raw in _pairs(self.r.cmd("HGETALL", self._man(season))).values():
            try:
                rows.append(json.loads(raw))
            except (TypeError, ValueError):
                continue
        rows.sort(key=lambda r: (r.get("week", 0), r.get("roster_id", 0), r.get("id", 0)))
        return rows

    def add_manual(self, season: str, week: int, roster_id: int, label: str, detail: str | None = None) -> dict:
        mid = int(self.r.cmd("INCR", f"{self.p}manual:seq"))
        row = {"id": mid, "season": season, "week": int(week), "roster_id": int(roster_id), "label": label,
               "detail": detail, "created_at": _now()}
        self.r.cmd("HSET", self._man(season), str(mid), json.dumps(row))
        return {"id": mid, "season": season, "week": week, "roster_id": roster_id, "label": label, "detail": detail}

    def delete_manual(self, season: str, manual_id: int) -> None:
        self.r.pipeline([["HDEL", self._man(season), str(manual_id)],
                         ["HDEL", self._comp(season), f"{season}:manual:{manual_id}"]])


class RedisCache:
    """Sleeper response cache: one key per API path, zlib-compressed JSON, base64 text."""

    def __init__(self, redis: UpstashRedis, prefix: str | None = None, expire: int = CACHE_EXPIRE_SECONDS):
        self.r = redis
        self.p = f"{key_prefix(prefix)}cache:"
        self.expire = expire

    def _key(self, path: str) -> str:
        return self.p + path.strip("/")

    @staticmethod
    def encode(data: Any, fetched_at: float) -> str:
        raw = json.dumps({"fetched_at": fetched_at, "data": data}, separators=(",", ":")).encode("utf-8")
        return base64.b64encode(zlib.compress(raw, 9)).decode("ascii")

    @staticmethod
    def decode(text: str) -> tuple[Any, float]:
        blob = json.loads(zlib.decompress(base64.b64decode(text)).decode("utf-8"))
        return blob["data"], blob["fetched_at"]

    def read(self, path: str) -> tuple[Any, float] | None:
        try:
            text = self.r.cmd("GET", self._key(path))
            return None if text is None else self.decode(text)
        except RedisError as e:
            log.warning("redis cache read failed for %s: %s", path, e)
        except Exception:  # corrupt value: treat as a miss
            log.warning("corrupt redis cache entry for %s", path)
        return None

    def write(self, path: str, data: Any, fetched_at: float) -> None:
        text = self.encode(data, fetched_at)
        if len(text) > MAX_BLOB_BYTES:
            log.warning("not caching %s: %d bytes compressed exceeds %d", path, len(text), MAX_BLOB_BYTES)
            return
        log.debug("redis cache write %s (%d bytes)", path, len(text))
        try:
            self.r.cmd("SET", self._key(path), text, "EX", self.expire)
        except RedisError as e:
            log.warning("redis cache write failed for %s: %s", path, e)

    def delete_matching(self, predicate: Callable[[str], bool]) -> None:
        cursor, keys = "0", []
        try:
            while True:
                cursor, batch = self.r.cmd("SCAN", cursor, "MATCH", self.p + "*", "COUNT", 500)
                keys.extend(batch)
                if str(cursor) == "0":
                    break
            doomed = [k for k in keys if predicate(k[len(self.p):])]
            for i in range(0, len(doomed), 100):
                self.r.cmd("DEL", *doomed[i:i + 100])
        except RedisError as e:
            log.warning("redis cache clear failed: %s", e)
