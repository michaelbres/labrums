"""Fake newsroom entry point. The writing lives in app/newsroom (50 reporters, 14 style families);
this module keeps the public API main.py and the tests rely on."""
from __future__ import annotations

from .newsroom import Newsroom, generate  # noqa: F401
from .newsroom.voices import VOICES


def reporters() -> list[dict]:
    """The masthead: every staff reporter (id, name, outlet, bio, family)."""
    return [v.card() for v in VOICES]
