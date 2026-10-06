"""FastAPI app: JSON API + static frontend."""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import articles, playoffs, shotguns, stats
from .config import DATA_DIR, ROOT, load_config
from .db import Store, manual_to_items
from .loader import LeagueNotFound, discover_seasons, load_season
from .sleeper import SleeperClient, SleeperError

log = logging.getLogger("labrums")
logging.basicConfig(level=os.environ.get("LABRUMS_LOG", "INFO"))

MODEL_TTL = int(os.environ.get("LABRUMS_MODEL_TTL", 5 * 60))
STATIC_DIR = ROOT / "static"


class State:
    def __init__(self):
        self.cfg = load_config()
        self.demo = os.environ.get("LABRUMS_DEMO", "").lower() in ("1", "true", "yes")
        if self.demo:
            from .demo import DemoClient
            self.client = DemoClient(current_week=int(os.environ.get("LABRUMS_DEMO_WEEK", 7)))
            self.cfg["seasons"] = {"2026": "demo2026"}
            self.cfg["current_season"] = "2026"
            db_path = ":memory:" if os.environ.get("LABRUMS_DEMO_DB", "") == "memory" else DATA_DIR / "labrums-demo.db"
        else:
            self.client = SleeperClient(DATA_DIR / "cache")
            db_path = DATA_DIR / "labrums.db"
        self.store = Store(db_path)
        self.admin_pin = os.environ.get("LABRUMS_ADMIN_PIN") or None
        self._lock = threading.Lock()
        self._models: dict[str, tuple[float, dict]] = {}
        self._seasons: tuple[float, list[dict]] | None = None

    def reload_config(self):
        self.cfg = load_config()
        if self.demo:
            self.cfg["seasons"] = {"2026": "demo2026"}
            self.cfg["current_season"] = "2026"
        self._models.clear(); self._seasons = None

    def seasons(self) -> list[dict]:
        with self._lock:
            if self._seasons and time.time() - self._seasons[0] < MODEL_TTL * 2:
                return self._seasons[1]
        seasons = discover_seasons(self.client, self.cfg)
        with self._lock:
            self._seasons = (time.time(), seasons)
        return seasons

    def league_id_for(self, season: str) -> str:
        for s in self.seasons():
            if s["season"] == season:
                return s["league_id"]
        if season in self.cfg["seasons"]:
            return self.cfg["seasons"][season]
        raise HTTPException(404, f"Unknown season {season}")

    def base_model(self, season: str, force: bool = False) -> dict:
        with self._lock:
            hit = self._models.get(season)
            if hit and not force and time.time() - hit[0] < MODEL_TTL:
                return hit[1]
        league_id = self.league_id_for(season)
        t0 = time.time()
        try:
            ctx = load_season(self.client, self.cfg, league_id)
        except SleeperError as e:
            raise HTTPException(503, f"Sleeper API unavailable: {e}") from e
        except LeagueNotFound as e:
            raise HTTPException(404, str(e)) from e
        st = stats.compute(ctx)
        po = playoffs.simulate(ctx, st)
        items = shotguns.detect(ctx, st)
        arts = articles.generate(ctx, st, po, items)
        model = {"ctx": ctx, "stats": st, "playoffs": po, "shotgun_items": items, "articles": arts,
                 "built_at": time.time(), "build_seconds": round(time.time() - t0, 2)}
        with self._lock:
            self._models[season] = (time.time(), model)
        log.info("built model for %s in %.2fs", season, model["build_seconds"])
        return model


state = State()
app = FastAPI(title="Labrums", version="0.1.0")


def require_admin(x_admin_pin: str | None = Header(default=None)):
    if state.admin_pin and x_admin_pin != state.admin_pin:
        raise HTTPException(401, "Admin PIN required")


def serialize(season: str, m: dict) -> dict[str, Any]:
    ctx, st = m["ctx"], m["stats"]
    completed = state.store.completed(season)
    items = [dict(i) for i in m["shotgun_items"]] + manual_to_items(season, state.store.manual(season))
    board = shotguns.leaderboard(ctx, items, completed)
    league = ctx["league"]
    return {
        "season": season,
        "league": {"league_id": ctx["league_id"], "name": league.get("name"), "status": league.get("status"),
                   "season": ctx["season"], "total_rosters": league.get("total_rosters"),
                   "roster_positions": ctx["roster_positions"], "scoring": league.get("scoring_settings"),
                   "playoff_teams": ctx["playoff_teams"], "playoff_start": ctx["playoff_start"],
                   "regular_weeks": ctx["regular_weeks"], "last_completed": ctx["last_completed"],
                   "current_week": ctx["current_week"], "avatar": league.get("avatar")},
        "teams": {str(rid): t for rid, t in st["teams"].items()},
        "standings": st["standings"],
        "power_rankings": st["power_rankings"],
        "games": st["games"],
        "schedule": {str(w): g for w, g in st["schedule"].items()},
        "league_avg": st["league_avg"],
        "records": st["records"],
        "playoffs": m["playoffs"],
        "shotguns": {"items": items, "leaderboard": board,
                     "rules": {**ctx["config"]["shotguns"],
                               "special": [r for r in ctx["config"].get("special_rules", []) if not r.get("season") or r["season"] == season]}},
        "articles": m["articles"],
        "rivalries": articles.Newsroom(ctx, st, m["playoffs"], m["shotgun_items"]).rivalries,
        "meta": {"demo": state.demo, "built_at": m["built_at"], "build_seconds": m["build_seconds"],
                 "admin_locked": bool(state.admin_pin)},
    }


@app.get("/api/health")
def health():
    return {"ok": True, "demo": state.demo}


@app.get("/api/seasons")
def seasons():
    return {"seasons": state.seasons(), "current": state.cfg.get("current_season")}


@app.get("/api/season/{season}")
def season(season: str):
    return serialize(season, state.base_model(season))


@app.post("/api/season/{season}/refresh", dependencies=[Depends(require_admin)])
def refresh(season: str):
    state.reload_config()
    state.client.clear_cache(keep_players=True, league_id=state.league_id_for(season))
    m = state.base_model(season, force=True)
    return {"ok": True, "build_seconds": m["build_seconds"]}


@app.post("/api/season/{season}/shotguns/{key}/toggle", dependencies=[Depends(require_admin)])
def toggle_shotgun(season: str, key: str):
    m = state.base_model(season)
    valid = {i["key"] for i in m["shotgun_items"]} | {i["key"] for i in manual_to_items(season, state.store.manual(season))}
    if key not in valid:
        raise HTTPException(404, f"Unknown shotgun {key}")
    done = state.store.toggle(season, key)
    return {"key": key, "completed": done, "completed_at": state.store.completed(season).get(key, {}).get("completed_at")}


class ManualShotgun(BaseModel):
    week: int
    roster_id: int
    label: str
    detail: str | None = None


@app.post("/api/season/{season}/shotguns/manual", dependencies=[Depends(require_admin)])
def add_manual(season: str, body: ManualShotgun):
    ctx = state.base_model(season)["ctx"]
    if not 1 <= body.week <= 18:
        raise HTTPException(400, "week must be between 1 and 18")
    if body.roster_id not in ctx["teams"]:
        raise HTTPException(400, f"Unknown roster_id {body.roster_id}")
    return state.store.add_manual(season, body.week, body.roster_id, body.label.strip() or "Manual shotgun", body.detail)


@app.delete("/api/season/{season}/shotguns/manual/{manual_id}", dependencies=[Depends(require_admin)])
def delete_manual(season: str, manual_id: int):
    state.store.delete_manual(season, manual_id)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
