"""Redis/Upstash persistence and the Vercel serverless path. No network: a fake Upstash server stands in."""
from __future__ import annotations

import importlib
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import config, db, demo, sleeper
from app.redis_client import RedisError, UpstashRedis, key_prefix
from app.storage import MAX_BLOB_BYTES, RedisCache, RedisStore
from tests.fake_upstash import FakeUpstash

REDIS_VARS = ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN", "KV_REST_API_URL", "KV_REST_API_TOKEN",
              "LABRUMS_REDIS_URL", "LABRUMS_REDIS_TOKEN", "LABRUMS_REDIS_PREFIX")


@pytest.fixture
def fake(monkeypatch):
    for v in REDIS_VARS:
        monkeypatch.delenv(v, raising=False)
    f = FakeUpstash().start()
    yield f
    f.stop()


@pytest.fixture
def redis(fake):
    return UpstashRedis(fake.url, fake.token)


# ---- client ---------------------------------------------------------------
def test_cmd_and_pipeline(redis, fake):
    assert redis.cmd("SET", "k", 5) == "OK"  # non-string args are stringified
    assert redis.cmd("GET", "k") == "5"
    assert redis.pipeline([["INCR", "n"], ["INCR", "n"], ["GET", "n"]]) == [1, 2, "2"]
    assert redis.pipeline([]) == []


def test_errors_raise_without_leaking_token(fake):
    bad = UpstashRedis(fake.url, "secret-token-xyz")
    with pytest.raises(RedisError) as e:
        bad.cmd("GET", "k")
    assert "secret-token-xyz" not in str(e.value) and "WRONGPASS" in str(e.value)
    ok = UpstashRedis(fake.url, fake.token)
    with pytest.raises(RedisError):
        ok.cmd("NOPE", "k")                      # error body on a 400
    with pytest.raises(RedisError):
        ok.pipeline([["GET", "a"], ["NOPE"]])    # error entry inside a 200 pipeline reply
    with pytest.raises(RedisError):
        UpstashRedis("http://127.0.0.1:1", "t", timeout=1).cmd("GET", "k")  # connection refused
    with pytest.raises(RedisError):
        UpstashRedis("file:///etc/passwd", "t")


def test_key_prefix(monkeypatch):
    monkeypatch.delenv("LABRUMS_REDIS_PREFIX", raising=False)
    assert key_prefix() == "labrums:"
    monkeypatch.setenv("LABRUMS_REDIS_PREFIX", "prod")
    assert key_prefix() == "labrums:prod:"


def test_redis_settings_precedence(monkeypatch):
    for v in REDIS_VARS:
        monkeypatch.delenv(v, raising=False)
    assert config.redis_settings() is None
    monkeypatch.setenv("LABRUMS_REDIS_URL", "http://c"); monkeypatch.setenv("LABRUMS_REDIS_TOKEN", "c")
    assert config.redis_settings() == ("http://c", "c")
    monkeypatch.setenv("KV_REST_API_URL", "http://b"); monkeypatch.setenv("KV_REST_API_TOKEN", "b")
    assert config.redis_settings() == ("http://b", "b")
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "http://a")  # token missing -> pair ignored
    assert config.redis_settings() == ("http://b", "b")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "a")
    assert config.redis_settings() == ("http://a", "a")


# ---- RedisStore -----------------------------------------------------------
def test_store_completions(redis, fake):
    s = RedisStore(redis)
    assert s.completed("2026") == {}
    assert s.toggle("2026", "2026:1:a") is True
    assert set(s.completed("2026")) == {"2026:1:a"}
    assert s.completed("2026")["2026:1:a"]["completed_at"]
    assert s.completed("2025") == {}
    assert s.toggle("2026", "2026:1:a") is False
    assert s.completed("2026") == {}
    assert s.set_completed("2026", "k", True, note="hi") is True
    assert s.completed("2026")["k"]["note"] == "hi"
    s.set_completed("2026", "k", False)
    assert s.completed("2026") == {}
    assert all(k.startswith("labrums:") for k in fake.data)


def test_store_manual(redis):
    s = RedisStore(redis)
    a = s.add_manual("2026", 5, 2, "late", "detail")
    b = s.add_manual("2026", 3, 7, "early")
    assert (a["id"], b["id"]) == (1, 2)
    assert set(a) == {"id", "season", "week", "roster_id", "label", "detail"}
    rows = s.manual("2026")
    assert [r["label"] for r in rows] == ["early", "late"]  # ordered by week
    assert rows[1]["detail"] == "detail" and rows[1]["id"] == 1
    assert s.manual("2025") == []
    s.set_completed("2026", "2026:manual:1", True)
    s.delete_manual("2026", 1)
    assert [r["label"] for r in s.manual("2026")] == ["early"]
    assert s.completed("2026") == {}
    assert s.add_manual("2026", 1, 1, "x")["id"] == 3  # ids never reused


def test_store_prefix_isolation(redis):
    a, b = RedisStore(redis, prefix="a"), RedisStore(redis, prefix="b")
    a.toggle("2026", "k")
    assert b.completed("2026") == {}


def test_store_matches_sqlite_semantics(redis):
    """Same call sequence gives the same observable results as db.Store."""
    for s in (db.Store(":memory:"), RedisStore(redis)):
        s.add_manual("2026", 2, 1, "m")
        assert s.toggle("2026", "2026:manual:1") is True
        assert list(s.completed("2026")) == ["2026:manual:1"]
        assert s.manual("2026")[0]["label"] == "m"
        s.delete_manual("2026", 1)
        assert s.manual("2026") == [] and s.completed("2026") == {}


# ---- RedisCache -----------------------------------------------------------
def test_cache_roundtrip_players_blob_under_1mb(redis, fake):
    players = demo.DemoClient(current_week=7).players()
    cache = RedisCache(redis)
    t = time.time()
    cache.write("players/nfl", players, t)
    key = "labrums:cache:players/nfl"
    assert fake.ttls[key] == 8 * 24 * 3600
    stored = fake.data[key]
    assert len(stored) < MAX_BLOB_BYTES
    assert cache.read("players/nfl") == (players, t)
    assert cache.read("nope") is None


def test_cache_oversize_value_is_skipped(redis, fake):
    import os
    cache = RedisCache(redis)
    cache.write("big", {"x": os.urandom(1_200_000).hex()}, 1.0)  # incompressible > 1 MB
    assert cache.read("big") is None and not fake.data


def test_cache_corrupt_value_is_a_miss(redis, fake):
    fake.data["labrums:cache:bad"] = "not-base64-zlib!!"
    assert RedisCache(redis).read("bad") is None


def test_cache_survives_redis_outage():
    cache = RedisCache(UpstashRedis("http://127.0.0.1:1", "t", timeout=1))
    assert cache.read("x") is None
    cache.write("x", {"a": 1}, 1.0)       # must not raise
    cache.delete_matching(lambda p: True)  # must not raise


def test_clear_cache_over_redis(redis, fake):
    client = sleeper.SleeperClient(RedisCache(redis))
    for i in range(120):  # more keys than one SCAN page
        client._write_cache(f"league/L1/matchups/{i}", [i])
    client._write_cache("league/L1", {"a": 1})
    client._write_cache("league/L10/rosters", [])  # different league whose id shares a prefix
    client._write_cache("league/L2", {"b": 2})
    client._write_cache("state/nfl", {"week": 1})
    client._write_cache("players/nfl", {"p": 1})
    client.clear_cache(keep_players=True, league_id="L1")
    assert client._read_cache("league/L1") is None and client._read_cache("league/L1/matchups/99") is None
    assert client._read_cache("state/nfl") is None
    assert client._read_cache("league/L2") is not None and client._read_cache("league/L10/rosters") is not None
    assert client._read_cache("players/nfl") is not None
    client.clear_cache(keep_players=False)
    assert not [k for k in fake.data if k.startswith("labrums:cache:")]


def test_sleeper_client_uses_redis_cache(redis, monkeypatch):
    client = sleeper.SleeperClient(RedisCache(redis))
    calls = []

    def fake_fetch(path):
        calls.append(path)
        return [{"roster_id": 1, "points": 10}]
    monkeypatch.setattr(client, "_fetch", fake_fetch)
    assert client.matchups("L", 1, final=True) == [{"roster_id": 1, "points": 10}]
    assert client.matchups("L", 1, final=True) == [{"roster_id": 1, "points": 10}]
    assert calls == ["league/L/matchups/1"]
    # a second client (a new serverless instance) sees the shared cache
    other = sleeper.SleeperClient(RedisCache(redis))
    monkeypatch.setattr(other, "_fetch", lambda p: pytest.fail("should hit the cache"))
    assert other.matchups("L", 1, final=True)
    # stale entries refetch; if Sleeper is down the stale entry is served
    client._write_cache("league/L/rosters", [1])
    data, _ = client.cache.read("league/L/rosters")
    client.cache.write("league/L/rosters", data, time.time() - sleeper.LIVE_TTL - 5)
    monkeypatch.setattr(client, "_fetch", lambda p: (_ for _ in ()).throw(sleeper.SleeperError("down")))
    assert client.rosters("L") == [1]


def test_disk_cache_default_is_lazy(tmp_path):
    d = tmp_path / "a" / "b"
    client = sleeper.SleeperClient(d)
    assert not d.exists()
    client._write_cache("league/L", {"x": 1})
    assert client._read_cache("league/L")[0] == {"x": 1}


# ---- app wiring -----------------------------------------------------------
def _reload_main(monkeypatch, **env):
    for v in REDIS_VARS + ("VERCEL", "LABRUMS_DEMO", "LABRUMS_DEMO_DB", "LABRUMS_ADMIN_PIN"):
        monkeypatch.delenv(v, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import app.main as main
    return importlib.reload(main)


def test_vercel_entrypoint_without_redis(monkeypatch):
    main = _reload_main(monkeypatch, VERCEL="1", LABRUMS_DEMO="1", LABRUMS_DEMO_DB="memory")
    import api.index
    idx = importlib.reload(api.index)
    assert idx.app is main.app
    with TestClient(idx.app) as c:
        assert c.get("/api/health").json() == {"ok": True, "demo": True}
        body = c.get("/api/season/2026").json()
        assert body["meta"]["persistence"] == "ephemeral"
        key = body["shotguns"]["items"][0]["key"]
        assert c.post(f"/api/season/2026/shotguns/{key}/toggle").json()["completed"] is True
        after = c.get("/api/season/2026").json()["shotguns"]["items"]
        assert [i["completed"] for i in after if i["key"] == key] == [True]  # persisted within the process
    _reload_main(monkeypatch, LABRUMS_DEMO="1", LABRUMS_DEMO_DB="memory")


def test_local_default_is_sqlite(monkeypatch):
    main = _reload_main(monkeypatch, LABRUMS_DEMO="1", LABRUMS_DEMO_DB="memory")
    assert main.state.persistence == "sqlite" and isinstance(main.state.store, db.Store)


def test_app_end_to_end_with_fake_upstash(monkeypatch, fake):
    """Non-demo wiring: Redis env selects RedisStore + RedisCache; the model builds from cached Sleeper data."""
    monkeypatch.setattr(sleeper, "SleeperClient", lambda cache, *a, **k: _Capture(cache))
    main = _reload_main(monkeypatch, UPSTASH_REDIS_REST_URL=fake.url, UPSTASH_REDIS_REST_TOKEN=fake.token)
    assert main.state.persistence == "redis" and isinstance(main.state.store, RedisStore)
    assert isinstance(main.state.client.cache, RedisCache)
    main.state.client = demo.DemoClient(current_week=7)
    main.state.cfg["seasons"] = {"2026": "demo2026"}
    main.state.cfg["current_season"] = "2026"
    with TestClient(main.app) as c:
        body = c.get("/api/season/2026").json()
        assert body["meta"]["persistence"] == "redis"
        key = body["shotguns"]["items"][0]["key"]
        assert c.post(f"/api/season/2026/shotguns/{key}/toggle").json()["completed"] is True
        mid = c.post("/api/season/2026/shotguns/manual", json={"label": "m", "week": 2, "roster_id": 1}).json()["id"]
    # a brand-new State (another serverless instance) sees the same Redis data
    main2 = _reload_main(monkeypatch, UPSTASH_REDIS_REST_URL=fake.url, UPSTASH_REDIS_REST_TOKEN=fake.token)
    assert key in main2.state.store.completed("2026")
    assert [r["id"] for r in main2.state.store.manual("2026")] == [mid]
    _reload_main(monkeypatch, LABRUMS_DEMO="1", LABRUMS_DEMO_DB="memory")


class _Capture:
    """Stand-in for SleeperClient that only records the cache backend State chose."""

    def __init__(self, cache):
        self.cache = cache
