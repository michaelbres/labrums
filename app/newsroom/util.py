"""Small formatting helpers shared by the newsroom modules."""
from __future__ import annotations

import re

_ORD_SUFFIX = {1: "st", 2: "nd", 3: "rd"}
_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
_ORD_WORDS = ["zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
              "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth",
              "nineteenth", "twentieth"]


def ordinal(n: int) -> str:
    """1st, 2nd, 3rd, 4th ... 11th, 12th, 13th, 21st, 22nd, 23rd, 101st, 111th."""
    n = int(n)
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{_ORD_SUFFIX.get(n % 10, 'th')}"


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
    return f"{fmt(x)} point" if abs(round(float(x), 2)) == 1 else f"{fmt(x)} points"


def pct(p: float | None) -> str | None:
    return None if p is None else f"{round(p * 100):d}%"


def plural(n: int, one: str, many: str | None = None) -> str:
    """'1 owner' / '2 owners'."""
    return f"{n} {one}" if n == 1 else f"{n} {many or one + 's'}"


def verb(n: int, singular: str, plural_form: str) -> str:
    """Agreement for a counted subject: verb(1, 'owes', 'owe') -> 'owes'."""
    return singular if n == 1 else plural_form


_AN_WORD = re.compile(r"^(?:[aeiou]|hour|honest|honou?r|heir)", re.I)
_A_WORD = re.compile(r"^(?:uni|use|usu|one|eu|ubiq)", re.I)


def _number_takes_an(d: str) -> bool:
    """True when the integer part `d` is read starting with a vowel sound: 8, 11, 18, 80-89, 800s, 8000s."""
    if len(d) in (1, 2, 3, 4) and d.startswith("8"):
        return True
    return d in ("11", "18") or (len(d) == 4 and d.startswith(("11", "18")))


def a_an(phrase: str) -> str:
    """'83.21-point' -> 'an 83.21-point'; '12.5-point' -> 'a 12.5-point'; 'umpire' -> 'an umpire'; 'one' -> 'a one'."""
    p = phrase.strip()
    m = re.match(r"^(\d+)", p)
    if m:
        return f"{'an' if _number_takes_an(m.group(1)) else 'a'} {p}"
    return f"{'an' if _AN_WORD.match(p) and not _A_WORD.match(p) else 'a'} {p}"


def sentence_case(text: str) -> str:
    """Capitalize the first letter of `text`."""
    return text[:1].upper() + text[1:]


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


_ABBR = re.compile(r"\b(Dr|Mr|Mrs|Ms|Hon|vs|St|Jr|Sr|Esq|ret)\.")


def split_sentences(text: str) -> list[str]:
    """Rough sentence splitter used by the repetition memory, lint and tests."""
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = _ABBR.sub(lambda m: m.group(1) + "\x00", text)
    parts = re.split(r'(?<=[.!?])"?\s+(?=["A-Z0-9(])', text)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


_NO_CAP_BEFORE = re.compile(r"(?:\b(?:vs|v|e\.g|i\.e|etc|approx|no|nos|st|jr|sr|dr|mr|mrs|ms|esq|ret|hon)\.)$", re.I)
_AN_FIX = re.compile(r"\b([Aa]n?) (\d[\d,]*)(?=[A-Za-z.\d%\-\s]|$)")


def _fix_article(m: re.Match) -> str:
    art, num = m.group(1), m.group(2).replace(",", "")
    want = "an" if _number_takes_an(num) else "a"
    return (want.capitalize() if art[0] == "A" else want) + " " + m.group(2)


def polish(text: str, protect: "re.Pattern | None" = None) -> str:
    """The final pass over every rendered paragraph: collapse double spaces, close up ' ,' and ' .', start a
    sentence with a capital (never touching a team or player name that is spelled lowercase), and use 'an' before
    numbers read with a vowel sound ('an 83.21-point win', 'a 12-point win')."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,;])", r"\1", text)
    text = re.sub(r"\s+\.(?!\d)", ".", text)
    text = _AN_FIX.sub(_fix_article, text)

    def cap(m: re.Match) -> str:
        head, ch = m.group(1), m.group(2)
        if "\u201d" in head:      # '!" said Colin': an attribution, not a new sentence
            return m.group(0)
        if _NO_CAP_BEFORE.search(text[: m.start(1) + 1]):
            return m.group(0)
        if protect is not None:
            hit = protect.match(text, m.start(2))
            if hit:
                return m.group(0)
        return head + ch.upper()
    return re.sub(r"([.!?][\"\u201d)]*\s+)([a-z])", cap, text)
