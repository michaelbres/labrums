"""Style families: each is a COMPLETE template set (every beat slot, >= 3 variants) written in one register.

A template is a string with {key} placeholders. It may only use keys named for its slot in SLOTS (plus the
lexicon keys verb/noun/tier, which the engine fills from the family lexicon). A template whose keys are
missing from the facts is skipped, so a template can never print something the data does not contain.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from .util import placeholders

FAMILY_IDS = ["wire", "hype", "nerd", "columnist", "tabloid", "deadpan", "noir",
              "nature", "wrestling", "memo", "british", "courtroom", "weather", "finance"]

# slot -> (min variants, guaranteed keys, optional keys)
G_RES = "w l wp lp m w_team l_team w_nick l_nick wl wk verb noun"
G_TIE = "a b pts a_team b_team wl wk"
SLOTS: dict[str, tuple[int, str, str]] = {
    # ---- weekly roundup ("recap") ----
    "h.r.blow": (3, G_RES, ""),
    "h.r.upset": (3, G_RES + " w_rank0 l_rank0", ""),
    "h.r.close": (3, G_RES, ""),
    "h.r.top": (3, G_RES + " wavg", ""),
    "h.r.tie": (3, G_TIE, ""),
    "r.lede.blow": (3, G_RES, ""),
    "r.lede.upset": (3, G_RES + " w_rank0 l_rank0", ""),
    "r.lede.close": (3, G_RES, ""),
    "r.lede.top": (3, G_RES + " wavg", ""),
    "r.lede.tie": (3, G_TIE, ""),
    "g.result": (10, G_RES, ""),
    "g.tie": (3, G_TIE, ""),
    "g.star": (3, "w l wp lp star spos spts sshare wl wk", ""),
    "g.goat": (3, "w l gname gpos gpts wl wk", ""),
    "g.bench": (3, "w l bench_left bench_name bench_pos bench_pts wl wk", ""),
    "g.streak_w": (3, "w k w_rec w_rank wl wk", ""),
    "g.streak_l": (3, "l k l_rec l_rank wl wk", ""),
    "g.record": (3, "w l w_rec l_rec w_rank l_rank wl wk", ""),
    "g.top": (3, "w wp wavg wl wk", ""),
    "g.low": (3, "l lp wavg wl wk", ""),
    "g.luck_up": (3, "n luck n_rec wl wk", ""),
    "g.luck_down": (3, "n luck n_rec wl wk", ""),
    "g.upset": (3, "w l w_rank0 l_rank0 wl wk", ""),
    "g.shotgun": (3, "n sgn why wl wk", ""),
    "g.aside": (3, "n trait event wl wk", ""),
    "r.close_shift": (3, "in_names out_names leader leader_rec wl wk", ""),
    "r.close_table": (3, "leader leader_rec cut cut_rec wl wk", ""),
    "r.close_po": (3, "top_w top_pts big_w big_l big_m ngames wl wk", ""),
    # ---- preview ----
    "h.p.fav": (3, "fav dog fav_odds dog_odds a b wk wl", ""),
    "h.p.even": (3, "a b a_odds b_odds wk wl", ""),
    "h.p.lev": (3, "a b swing wk wl", ""),
    "p.lede": (3, "a b a_team b_team wk wl", "swing fav dog"),
    "p.matchup": (4, "a b a_team b_team a_rec b_rec a_avg b_avg wk wl", ""),
    "p.h2h_split": (3, "a b h2h_rec", ""),
    "p.h2h_lead": (3, "lead trail h2h_rec", ""),
    "p.h2h_none": (3, "a b", ""),
    "p.stakes": (3, "a b a_win a_loss b_win b_loss", ""),
    "p.leverage": (3, "a b swing", ""),
    "p.favorite": (3, "fav dog fav_odds dog_odds fav_why", ""),
    "p.vol": (3, "vol_n vol_std other other_std", ""),
    "p.rivnote": (3, "rv_name backstory a b", ""),
    "p.close": (3, "a b wk wl", ""),
    # ---- trade ----
    "h.t": (4, "a b gave_s got_s wk", ""),
    "t.sides": (4, "a b a_got b_got wk wl", ""),
    "t.returns": (3, "a b a_pts b_pts lead trail lead_pts trail_pts since_wk", ""),
    "t.pending": (3, "pk_side pl_side pk_got pl_got", ""),
    "t.fresh": (3, "a b", ""),
    "t.count": (3, "n nth", "moves"),
    "t.rec": (3, "a b a_rec b_rec a_rank b_rank", ""),
    "t.close": (3, "a b", ""),
    # ---- waiver ----
    "h.w.big": (3, "n player pos bid wk", ""),
    "h.w.small": (3, "n player pos bid wk", ""),
    "h.w.free": (3, "n player pos wk", ""),
    "w.top_bid": (3, "n player pos bid wk wl", ""),
    "w.top_free": (3, "n player pos wk wl", ""),
    "w.since": (3, "n player spts tier since_wk", ""),
    "w.others": (3, "others_text n_other", ""),
    "w.total": (3, "total_n total_owners wk wl", ""),
    "w.budget": (3, "n spent budget", ""),
    "w.close": (3, "n player", ""),
    # ---- beer report ----
    "h.s": (4, "total_n top topn wk", ""),
    "s.total": (3, "total_n owners_n wk wl", ""),
    "s.owner": (4, "n sgn list wk", ""),
    "s.low": (3, "n player pos pts wk", ""),
    "s.leader": (3, "leader ltotal wk", ""),
    "s.close": (3, "top wk", ""),
    # ---- standings ----
    "h.n": (4, "top six bottom alive spots wl wk", ""),
    "h.nf": (4, "top six seven bottom", ""),
    "n.top": (3, "top top_rec wl wk", "top_odds bye"),
    "n.cut": (3, "six six_rec seven seven_rec", "six_odds seven_odds"),
    "n.luck": (3, "lucky lucky_luck unlucky unlucky_luck", ""),
    "n.clinch": (3, "names", ""),
    "n.elim": (3, "names", ""),
    "n.bottom": (3, "bottom bottom_rec", "bottom_odds"),
    "n.eff": (3, "best_n best_pct worst_n worst_pct", ""),
    "n.records": (3, "hi_n hi_pts hi_wk blow_w blow_l blow_m blow_wk", ""),
    "n.ftop": (3, "top top_rec top_pf", ""),
    "n.fcut": (3, "six six_rec seven seven_rec", ""),
    "n.fpts": (3, "pf_n pf_pts low_n low_pts", ""),
    "n.fbottom": (3, "bottom bottom_rec", ""),
    "n.close": (3, "top wl", ""),
    # ---- feud ----
    "h.f": (4, "a b", ""),
    "f.h2h": (3, "w l wp lp m gwk verb noun", ""),
    "f.trade": (3, "a b a_got b_got twk", ""),
    "f.adj": (3, "hi lo hi_rank lo_rank hi_rec lo_rec pf_gap", ""),
    "f.blow": (3, "w l m gwk wp lp verb noun", ""),
    "f.sg": (3, "a b a_sg b_sg", ""),
    "f.story": (3, "rv_name backstory a b", ""),
    "f.trait": (3, "a b a_trait b_trait", ""),
    "f.mid": (3, "a b a_rec b_rec a_rank b_rank wk", ""),
    "f.close": (3, "a b", ""),
    # ---- rivalry hype ----
    "h.v": (4, "a b rv_name wk", ""),
    "v.lede": (3, "rv_name backstory a b wk wl", ""),
    "v.form": (3, "a b a_rec b_rec a_avg b_avg a_rank b_rank", ""),
    "v.close": (3, "a b wk", ""),
    # ---- offseason ----
    "h.o": (3, "ntrades npick", ""),
    "o.lede": (3, "ntrades npick", ""),
    "o.busy": (3, "busy_text", ""),
    "o.big": (3, "side_a side_b a_got b_got", ""),
    "o.close": (3, "busiest", ""),
    # ---- shared ----
    "x.sig": (3, "n catch", ""),
    "x.attr": (4, "n qc qp", ""),
}
LEX_KEYS = {"verb", "noun", "tier"}
COMMON = {"wk", "wl"}
MCLASSES = ("blowout", "comfortable", "normal", "close")
TIERS = ("hi", "mid", "lo")


def allowed_keys(slot: str) -> set[str]:
    _, g, o = SLOTS[slot]
    return set(g.split()) | set(o.split()) | COMMON


def guaranteed_keys(slot: str) -> set[str]:
    return set(SLOTS[slot][1].split()) | COMMON


@dataclass
class Family:
    id: str
    label: str
    desc: str
    rhythm: str
    formality: str
    metaphors: str
    numbers: str
    lex: dict
    T: dict[str, list[str]]
    extra: dict = field(default_factory=dict)

    def templates(self, slot: str) -> list[str]:
        return self.T[slot]


_CACHE: dict[str, Family] = {}


def get(fid: str) -> Family:
    if fid not in _CACHE:
        mod = importlib.import_module(f"{__package__}.styles.{fid}")
        d = dict(mod.FAMILY)
        _CACHE[fid] = Family(id=d.pop("id"), label=d.pop("label"), desc=d.pop("desc"), rhythm=d.pop("rhythm"),
                             formality=d.pop("formality"), metaphors=d.pop("metaphors"), numbers=d.pop("numbers"),
                             lex=d.pop("lex"), T=d.pop("T"), extra=d)
    return _CACHE[fid]


def all_families() -> list[Family]:
    return [get(f) for f in FAMILY_IDS]


def validate(fam: Family) -> list[str]:
    """Problems with a family's template set (empty list = valid)."""
    bad: list[str] = []
    for slot, (n_min, _, _) in SLOTS.items():
        tpls = fam.T.get(slot)
        if not tpls or len(tpls) < n_min:
            bad.append(f"{fam.id}:{slot}: needs >= {n_min} variants, has {len(tpls or [])}")
            continue
        ok = allowed_keys(slot) | LEX_KEYS
        always = guaranteed_keys(slot) | LEX_KEYS
        usable = 0
        for t in tpls:
            ph = placeholders(t)
            if ph - ok:
                bad.append(f"{fam.id}:{slot}: unknown keys {sorted(ph - ok)} in {t!r}")
            if not (ph - always):
                usable += 1
            if "  " in t or t != t.strip():
                bad.append(f"{fam.id}:{slot}: spacing in {t!r}")
        if usable < 3:
            bad.append(f"{fam.id}:{slot}: only {usable} templates always usable")
    names_w = ("{w}", "{w_nick}")
    for slot in fam.T:
        if slot in ("g.result",) or slot.startswith("r.lede.") and not slot.endswith(".tie"):
            for t in fam.T[slot]:
                if not any(k in t for k in names_w) or "{l}" not in t and "{l_nick}" not in t:
                    bad.append(f"{fam.id}:{slot}: must name both owners ({{w}} and {{l}}): {t!r}")
        if slot == "r.lede.tie" or slot == "g.tie":
            for t in fam.T[slot]:
                if "{a}" not in t or "{b}" not in t:
                    bad.append(f"{fam.id}:{slot}: must name both owners ({{a}} and {{b}}): {t!r}")
    for slot in fam.T:
        if slot not in SLOTS:
            bad.append(f"{fam.id}:{slot}: unknown slot")
    for cls in MCLASSES:
        for kind in ("verb", "noun"):
            if len(fam.lex.get(kind, {}).get(cls, [])) < 3:
                bad.append(f"{fam.id}: lex {kind}/{cls} needs >= 3")
    for tier in TIERS:
        if len(fam.lex.get("tier", {}).get(tier, [])) < 3:
            bad.append(f"{fam.id}: lex tier/{tier} needs >= 3")
    return bad
