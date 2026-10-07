"""Owner profile `name` (real first name) replaces the Sleeper handle everywhere a person is named."""
from __future__ import annotations

import copy

from app import articles, config, loader, playoffs, shotguns, stats
from app.demo import DemoClient

from .conftest import LEAGUE_ID

HANDLE = "zz_handle{}"
NAME = "Fname{}"


class HandleClient(DemoClient):
    """Demo league whose Sleeper handles are distinctive strings that can't appear by accident."""

    def users(self, league_id):
        out = copy.deepcopy(super().users(league_id))
        for i, u in enumerate(out):
            u["display_name"] = HANDLE.format(i)
        return out


def _build(cfg_over):
    cfg = copy.deepcopy(config.load_config())
    cfg.update(cfg_over)
    ctx = loader.load_season(HandleClient(current_week=7), cfg, LEAGUE_ID)
    st = stats.compute(ctx)
    po = playoffs.simulate(ctx, st)
    items = shotguns.detect(ctx, st)
    return ctx, st, po, items


def _owners(n=12):
    return {HANDLE.format(i): {"name": NAME.format(i)} for i in range(n)}


def test_name_defaults_to_handle_and_profile_name_wins():
    ctx, st, *_ = _build({"owners": {HANDLE.format(0): {"name": "  "}, HANDLE.format(1): {"name": "Nick"}}})
    by_handle = {t["display_name"]: t for t in ctx["teams"].values()}
    assert by_handle[HANDLE.format(0)]["name"] == HANDLE.format(0)  # blank name ignored
    assert by_handle[HANDLE.format(1)]["name"] == "Nick"
    assert by_handle[HANDLE.format(1)]["display_name"] == HANDLE.format(1)
    for rid, t in ctx["teams"].items():
        assert st["teams"][rid]["name"] == t["name"]  # carried through stats


def test_articles_use_name_not_handle():
    ctx, st, po, items = _build({"owners": _owners()})
    arts = articles.generate(ctx, st, po, items)
    assert arts
    text = "\n".join(" ".join([a["headline"], a["dek"], a["byline"], *a["body"]]) for a in arts)
    assert "zz_handle" not in text
    assert "Fname" in text
    nr = articles.Newsroom(ctx, st, po, items)
    for rid, t in st["teams"].items():
        assert nr.name(rid) == t["name"]


def test_leaderboard_rows_carry_name():
    ctx, st, po, items = _build({"owners": _owners()})
    for row in shotguns.leaderboard(ctx, items, {}):
        assert row["name"].startswith("Fname") and row["display_name"].startswith("zz_handle")


def test_rivalry_and_rule_resolve_by_profile_name_case_insensitive():
    ctx0, *_ = _build({"owners": _owners()})
    t = ctx0["teams"]
    uid = t[2]["owner_id"]
    refs = [["fname0", "FNAME1"], ["ZZ_HANDLE2", str(uid).upper().replace("U", "u")], ["3", t[5]["team_name"].upper()]]
    # fname0=roster 1, FNAME1=roster 2 ; ZZ_HANDLE2=roster 3, user_id of roster 2 ; roster_id 3 (=handle2), team_name of roster 5
    ctx, st, po, items = _build({"owners": _owners(), "rivalries": [
        {"name": f"R{i}", "owners": o} for i, o in enumerate(refs)]})
    nr = articles.Newsroom(ctx, st, po, items)
    assert [rv["owners"] for rv in nr.rivalries] == [[1, 2], [3, 2], [3, 5]]
    assert nr.rivalries[0]["owner_names"] == ["Fname0", "Fname1"]

    rule = {"season": "2026", "type": "score_less_than_team", "label": "x",
            "owners": ["fname0", "FNAME1", "Fname2"], "target": "fNaMe3"}
    ctx2, st2, _, items2 = _build({"owners": _owners(), "special_rules": [rule]})
    found = [i for i in items2 if i["reason"] == "rule"]
    expected = {(w, r) for r in (1, 2, 3) for w, mine in st2["teams"][r]["scores"].items()
                if mine < st2["teams"][4]["scores"][w]}
    assert {(i["week"], i["roster_id"]) for i in found} == expected
    assert found and all("Fname3" in i["detail"] and "zz_handle" not in i["detail"] for i in found)
