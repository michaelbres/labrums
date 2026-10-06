"""Shared fixtures. Everything runs against the offline DemoClient (no network)."""
from __future__ import annotations

import copy

import pytest

from app import articles, config, loader, playoffs, shotguns, stats
from app.demo import DemoClient

SEASON = "2026"
LEAGUE_ID = "demo2026"


@pytest.fixture(scope="session")
def client():
    return DemoClient(current_week=7)


@pytest.fixture(scope="session")
def cfg():
    return config.load_config()


@pytest.fixture(scope="session")
def ctx(client, cfg):
    return loader.load_season(client, cfg, LEAGUE_ID)


@pytest.fixture(scope="session")
def st(ctx):
    return stats.compute(ctx)


@pytest.fixture(scope="session")
def po(ctx, st):
    return playoffs.simulate(ctx, st)


@pytest.fixture(scope="session")
def items(ctx, st):
    return shotguns.detect(ctx, st)


@pytest.fixture(scope="session")
def arts(ctx, st, po, items):
    return articles.generate(ctx, st, po, items)


@pytest.fixture
def make_ctx(client, cfg):
    """Build a fresh ctx from a modified deep copy of the config."""

    def _make(**overrides):
        c = copy.deepcopy(cfg)
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(c.get(key), dict):
                c[key].update(value)
            else:
                c[key] = value
        return loader.load_season(client, c, LEAGUE_ID)

    return _make


def rid_by_name(ctx, name):
    for rid, t in ctx["teams"].items():
        if t["display_name"] == name:
            return rid
    raise KeyError(name)
