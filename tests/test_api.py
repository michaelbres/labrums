"""API tests. app.main builds global state at import time, so env vars are set first and the module reloaded."""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


def _load_app(monkeypatch, pin=None):
    monkeypatch.setenv("LABRUMS_DEMO", "1")
    monkeypatch.setenv("LABRUMS_DEMO_DB", "memory")
    monkeypatch.delenv("LABRUMS_DEMO_WEEK", raising=False)
    if pin is None:
        monkeypatch.delenv("LABRUMS_ADMIN_PIN", raising=False)
    else:
        monkeypatch.setenv("LABRUMS_ADMIN_PIN", pin)
    import app.main as main
    return importlib.reload(main)


@pytest.fixture
def api(monkeypatch):
    main = _load_app(monkeypatch)
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def locked_api(monkeypatch):
    main = _load_app(monkeypatch, pin="secret")
    with TestClient(main.app) as c:
        yield c


def test_health(api):
    r = api.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "demo": True}


def test_seasons(api):
    data = api.get("/api/seasons").json()
    assert data["current"] == "2026"
    assert {s["season"] for s in data["seasons"]} == {"2026", "2025"}
    assert [s["season"] for s in data["seasons"] if s["is_current"]] == ["2026"]


def test_season_payload(api):
    r = api.get("/api/season/2026")
    assert r.status_code == 200
    data = r.json()
    for key in ("league", "teams", "standings", "playoffs", "shotguns", "articles"):
        assert key in data
    assert len(data["teams"]) == 12
    assert len(data["standings"]) == 12
    assert data["articles"]
    assert data["league"]["last_completed"] == 6


def _outstanding(data):
    return sum(r["outstanding"] for r in data["shotguns"]["leaderboard"])


def test_toggle_shotgun(api):
    before = api.get("/api/season/2026").json()
    key = before["shotguns"]["items"][0]["key"]
    r = api.post(f"/api/season/2026/shotguns/{key}/toggle")
    assert r.status_code == 200
    assert r.json()["completed"] is True

    mid = api.get("/api/season/2026").json()
    assert _outstanding(mid) == _outstanding(before) - 1
    assert next(i for i in mid["shotguns"]["items"] if i["key"] == key)["completed"] is True

    assert api.post(f"/api/season/2026/shotguns/{key}/toggle").json()["completed"] is False
    assert _outstanding(api.get("/api/season/2026").json()) == _outstanding(before)


def test_manual_round_trip(api):
    base = api.get("/api/season/2026").json()
    n_items = len(base["shotguns"]["items"])
    r = api.post("/api/season/2026/shotguns/manual",
                 json={"week": 2, "roster_id": 1, "label": "Missed kickoff", "detail": "Snoozed"})
    assert r.status_code == 200
    mid = r.json()["id"]

    after = api.get("/api/season/2026").json()
    assert len(after["shotguns"]["items"]) == n_items + 1
    assert any(i["key"] == f"2026:manual:{mid}" for i in after["shotguns"]["items"])
    assert _outstanding(after) == _outstanding(base) + 1

    assert api.delete(f"/api/season/2026/shotguns/manual/{mid}").status_code == 200
    final = api.get("/api/season/2026").json()
    assert len(final["shotguns"]["items"]) == n_items
    assert not any(i["key"] == f"2026:manual:{mid}" for i in final["shotguns"]["items"])


def test_index_html(api):
    r = api.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_unknown_season_404(api):
    assert api.get("/api/season/1999").status_code == 404


def test_admin_pin_required(locked_api):
    c = locked_api
    key = c.get("/api/season/2026").json()["shotguns"]["items"][0]["key"]
    url = f"/api/season/2026/shotguns/{key}/toggle"
    assert c.post(url).status_code == 401
    assert c.post(url, headers={"X-Admin-Pin": "wrong"}).status_code == 401
    assert c.post(url, headers={"X-Admin-Pin": "secret"}).status_code == 200
    assert c.get("/api/season/2026").json()["meta"]["admin_locked"] is True
    # Reads stay open.
    assert c.get("/api/health").status_code == 200


def test_network_demo(api):
    r = api.get("/api/network")
    assert r.status_code == 200
    data = r.json()
    assert data["skipped"] == [] and data["seasons"] == ["2025", "2026"]
    assert len(data["teams"]) == 12 and data["players"] and data["edges"] and data["stints"]
    pid = data["edges"][0]["player_id"]
    assert any(p["player_id"] == pid for p in data["players"])
    assert {s["acquired_via"] for s in data["stints"]} >= {"draft", "kept"}


def test_network_total_failure_is_503_and_not_cached(api, monkeypatch):
    import app.main as main
    from app.sleeper import SleeperError
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise SleeperError("no season could be loaded")
    monkeypatch.setattr(main, "load_network", boom)
    assert api.get("/api/network").status_code == 503
    assert api.get("/api/network").status_code == 503
    assert len(calls) == 2


def test_network_partial_result_not_cached_but_full_is_and_loads_are_single_flight(api, monkeypatch):
    import threading
    import time as _t
    import app.main as main
    calls = []

    def partial(*a, **k):
        calls.append(1)
        return {"teams": [], "players": [], "edges": [], "stints": [], "seasons": ["2026"],
                "skipped": [{"season": "2025", "league_id": "x", "error": "boom"}]}
    monkeypatch.setattr(main, "load_network", partial)
    r = api.get("/api/network")
    assert r.status_code == 200 and r.json()["skipped"][0]["season"] == "2025"
    api.get("/api/network")
    assert len(calls) == 2  # partial result was not cached

    calls.clear()

    def full(*a, **k):
        calls.append(1)
        _t.sleep(0.2)
        return {"teams": [], "players": [], "edges": [], "stints": [], "seasons": ["2025", "2026"], "skipped": []}
    monkeypatch.setattr(main, "load_network", full)
    res = []
    ths = [threading.Thread(target=lambda: res.append(api.get("/api/network").status_code)) for _ in range(4)]
    [t.start() for t in ths]; [t.join() for t in ths]
    assert res == [200] * 4 and len(calls) == 1
