"""Small formatting helpers shared by the newsroom modules."""
from __future__ import annotations

import re

_ORD = {1: "1st", 2: "2nd", 3: "3rd"}
_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
_ORD_WORDS = ["zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]


def ordinal(n: int) -> str:
    n = int(n)
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return _ORD.get(n % 10, f"{n}th") if n % 10 in _ORD else f"{n}th"


def ord_word(n: int) -> str:
    return _ORD_WORDS[n] if 0 <= n < len(_ORD_WORDS) else ordinal(n)


def num_word(n: int) -> str:
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


def fmt(x: float) -> str:
    """Score-style number: two decimals, integers bare. 139.9 -> 139.90, 12.0 -> 12."""
    v = round(float(x), 2)
    if v == 0:
        return "0"
    s = f"{v:.2f}"
    return s[:-3] if s.endswith(".00") else s


def fmt1(x: float) -> str:
    return f"{float(x):.1f}"


def pts(x: float) -> str:
    """'1 point' / '12.4 points' / '0 points' / '-2.1 points'."""
    return "1 point" if round(float(x), 2) == 1 else f"{fmt(x)} points"


def pct(p: float | None) -> str | None:
    return None if p is None else f"{round(p * 100):d}%"


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one}" if n == 1 else f"{n} {many or one + 's'}"


def join_and(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def mclass(margin: float) -> str:
    if margin <= 0:
        return "tie"
    if margin >= 30:
        return "blowout"
    if margin >= 15:
        return "comfortable"
    if margin < 7:
        return "close"
    return "normal"


def signed(x: float) -> str:
    return f"{x:+.1f}"


_PLACE = re.compile(r"\{(\w+)\}")


def placeholders(tpl: str) -> set[str]:
    return set(_PLACE.findall(tpl))


def fill(tpl: str, vals: dict[str, str]) -> str:
    """Plain {key} replacement (never str.format: team names may contain braces)."""
    return _PLACE.sub(lambda m: vals[m.group(1)], tpl)


def split_sentences(text: str) -> list[str]:
    """Rough sentence splitter used by lint and the diversity tests."""
    text = text.replace("“", '"').replace("”", '"')
    parts = re.split(r'(?<=[.!?])"?\s+(?=["A-Z0-9(])', text)
    return [p.strip() for p in parts if p.strip()]
