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
