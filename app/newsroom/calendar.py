"""Daily release calendar: every article posts at 6:00 am America/New_York on a fixed weekday.

Week W's "Tuesday" is the Tuesday after that week's games: week 1's Tuesday is the first Tuesday after the
season start date, week W's is that + 7*(W-1) days. Calendar by type (offset from Tuesday of the article's week):

    Tue  recap (roundup), shotgun (Beer Report)        +0
    Wed  waiver, trade                                 +1   (a trade made after Tuesday posts the day after it was made)
    Thu  preview, rivalry hype (about week W+1)        +2 from the PRIOR week's Tuesday
    Fri  feud                                          +3
    Sat  standings                                     +4
    Sun  column (trash-talk)                           +5
    Mon  analytics                                     +6
    offseason                                          the season start date

If the season start is unknown every article is dated `today`.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

RELEASE_HOUR = 6   # local (America/New_York) hour at which a day's articles go live

OFFSETS = {"recap": 0, "shotgun": 0, "waiver": 1, "trade": 1, "feud": 3, "standings": 4, "column": 5, "analytics": 6}
PRIOR_WEEK_OFFSETS = {"preview": 2, "rivalry": 2}   # relative to the Tuesday of week-1 (the games just played)


def _nth_sunday(year: int, month: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(days=7 * (n - 1))


def _et_fixed(utc_now: datetime) -> datetime:
    """America/New_York without tzdata: EDT from the 2nd Sunday of March 07:00Z to the 1st Sunday of Nov 06:00Z."""
    y = utc_now.year
    start = datetime.combine(_nth_sunday(y, 3, 2), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=7)
    end = datetime.combine(_nth_sunday(y, 11, 1), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6)
    off = -4 if start <= utc_now < end else -5
    return utc_now.astimezone(timezone(timedelta(hours=off)))


def now_et() -> datetime:
    """The current time in America/New_York. LABRUMS_NOW (ISO, e.g. 2026-10-09T05:59:00-04:00) freezes it."""
    frozen = os.environ.get("LABRUMS_NOW")
    if frozen:
        dt = datetime.fromisoformat(frozen)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone(timedelta(hours=-4)))
    utc_now = datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return utc_now.astimezone(ZoneInfo("America/New_York"))
    except Exception:  # no tz database on this host
        return _et_fixed(utc_now)


def effective_today(now: datetime | None = None) -> date:
    """The newest calendar date whose 6:00 am release has happened (before 6 am it is still yesterday's edition)."""
    now = now or now_et()
    return now.date() if now.hour >= RELEASE_HOUR else now.date() - timedelta(days=1)


def season_start(ctx: dict) -> date | None:
    ms = ctx.get("season_start_ms")
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).date()


def week_tuesday(start: date, week: int) -> date:
    """The Tuesday after week `week`'s games (strictly after the start date for week 1)."""
    first = start + timedelta(days=(1 - start.weekday()) % 7 or 7)
    return first + timedelta(days=7 * (week - 1))


def _to_et(ms: int | float) -> datetime:
    utc = datetime.fromtimestamp(float(ms) / 1000, tz=timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        return _et_fixed(utc)


def publish_on(kind: str, week: int, start: date | None, *, today: date | None = None, tx_created_ms: int | None = None) -> str:
    """ISO date on which an article of this type and week posts (6:00 am ET)."""
    if start is None:
        return (today or effective_today()).isoformat()
    if kind == "offseason":
        return start.isoformat()
    if kind in PRIOR_WEEK_OFFSETS:
        return (week_tuesday(start, week - 1) + timedelta(days=PRIOR_WEEK_OFFSETS[kind])).isoformat()
    d = week_tuesday(start, week) + timedelta(days=OFFSETS.get(kind, 0))
    if kind == "trade" and tx_created_ms:
        d = max(d, _to_et(tx_created_ms).date() + timedelta(days=1))
    return d.isoformat()


def is_visible(pub: str | None, today: date) -> bool:
    if not pub:
        return True
    try:
        return date.fromisoformat(pub) <= today
    except ValueError:
        return True
