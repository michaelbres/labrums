"""Minimal Upstash Redis REST client (stdlib only).

Upstash speaks Redis over HTTPS: POST a JSON array of command arguments to the base URL and
get back {"result": ...} or {"error": ...}. POST an array of such arrays to {url}/pipeline
for several commands in one round trip. The client holds no mutable state, so it is safe to
share between threads.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Sequence

TIMEOUT = 10.0


class RedisError(RuntimeError):
    pass


def key_prefix(prefix: str | None = None) -> str:
    """`labrums:` or `labrums:<LABRUMS_REDIS_PREFIX>:` so several deployments can share one database."""
    extra = (os.environ.get("LABRUMS_REDIS_PREFIX", "") if prefix is None else prefix).strip().strip(":")
    return f"labrums:{extra}:" if extra else "labrums:"


class UpstashRedis:
    def __init__(self, url: str, token: str, timeout: float = TIMEOUT):
        url = (url or "").strip().rstrip("/")
        if not url.lower().startswith(("http://", "https://")):
            raise RedisError("Redis REST URL must start with http:// or https://")
        self.url = url
        self._token = token
        self.timeout = timeout

    def _post(self, url: str, payload: Any) -> Any:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json",
                     "User-Agent": "labrums/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status != 200:
                    raise RedisError(f"Redis REST returned HTTP {resp.status}")
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = (json.loads(e.read().decode("utf-8")).get("error") or "")
            except Exception:
                pass
            raise RedisError(f"Redis REST HTTP {e.code}: {detail}".rstrip(": ")) from e
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            raise RedisError(f"Redis REST request failed: {e}") from e

    @staticmethod
    def _args(args: Sequence[Any]) -> list[str]:
        return [a if isinstance(a, str) else str(a) for a in args]

    def cmd(self, *args: Any) -> Any:
        body = self._post(self.url, self._args(args))
        if not isinstance(body, dict):
            raise RedisError("unexpected Redis REST response")
        if body.get("error"):
            raise RedisError(str(body["error"]))
        return body.get("result")

    def pipeline(self, cmds: Sequence[Sequence[Any]]) -> list[Any]:
        if not cmds:
            return []
        body = self._post(f"{self.url}/pipeline", [self._args(c) for c in cmds])
        if not isinstance(body, list) or len(body) != len(cmds):
            raise RedisError("unexpected Redis REST pipeline response")
        out = []
        for item in body:
            if isinstance(item, dict) and item.get("error"):
                raise RedisError(str(item["error"]))
            out.append(item.get("result") if isinstance(item, dict) else item)
        return out
