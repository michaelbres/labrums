# Handoff

Living record of decisions and context. A new session should read this and `docs/plan.md` before touching code.

## What this is
Fantasy football league site for a Sleeper league. League ID changes each year (2026: `1312105961640448000`), so IDs live in `config.yaml` under `seasons`, and older seasons are auto-discovered through Sleeper's `previous_league_id` chain.

## Architecture decisions (2026-10-06)
- **Stack:** FastAPI + numpy + SQLite backend, vanilla JS frontend served from `static/`. Chosen because the owner codes Python for data analysis and is new to app building; one process, one command, no build step.
- **Sleeper client** (`app/sleeper.py`): stdlib urllib, disk cache in `data/cache/`. Completed weeks cached forever, live data 5 min, players blob 24h and trimmed to a few fields. Falls back to stale cache when offline.
- **Demo mode** (`app/demo.py`, `LABRUMS_DEMO=1`): deterministic Sleeper-shaped fixture. Needed because `api.sleeper.app` is blocked from the Claude cloud sandbox. All tests run on it.
- **Completed-week cutoff** (`app/loader.py`): week is final if `< state.week`, or league status complete, or state season newer than league season.
- **Stats** (`app/stats.py`): standings = wins, then PF. Luck = wins minus all-play expected wins. Power = 35% win pct + 40% all-play pct + 25% scoring z. Optimal lineup is greedy by fixed slots then flex slots.
- **Playoff odds** (`app/playoffs.py`): Monte Carlo, Normal per-team scores shrunk toward league mean with `prior_games` (3) weight, seeds by wins then PF, top-N make it, top-2 bye when N=6. Also returns conditional odds for next week's game (used in previews). Divisions are NOT modeled.
- **Shotguns** (`app/shotguns.py`): any starter with points <= threshold (0) on a completed week; empty slots count (configurable); special rules `score_less_than_team` and `score_below` from config. Keys are `season:week:roster:player:slotindex`, so check-offs survive rebuilds. Check-offs and manual shotguns in SQLite (`data/labrums.db`). Optional `LABRUMS_ADMIN_PIN` gates writes.
- **Articles** (`app/articles.py`): template bank with seeded RNG per (season, week, type, ids), so stories are stable across refreshes. Owner profiles and rivalries from config flavor quotes and feuds. No LLM calls; could add an optional Claude-generated mode later.
- **Model cache**: full season model rebuilt at most every `LABRUMS_MODEL_TTL` (300s) or on the ↻ button, which also reloads config.yaml.

## Orchestration
Custom agent roles live in `.claude/agents/` (scout/researcher/builder/refuter/debugger). They were created this session and were not yet registered as agent types, so this session used general-purpose agents with matching models.

## Known assumptions / unverified
- Live Sleeper playoff weeks: the code assumes teams that play in a playoff week have a `matchup_id` and idle teams have `null`. Verified only against the demo fixture (UNVERIFIED on live data). If live playoff rows come back with null ids, `include_playoff_weeks` has no effect; check `data/cache/league__<id>__matchups__15.json` after the first live run.
- Divisions are ignored for seeding.
- Clinch/eliminate: exact counting rule while games remain (ties on wins count as "can still pass me"); final standings decide once the regular season is over.

## Waiting on the owner
- Sleeper display names of the 3 owners under the special rule and the target team → `special_rules` in config.yaml.
- Owner profiles (nickname, bio, traits, catchphrase) → `owners`.
- Rivalry pairs and backstories → `rivalries`.
- Whether empty starting slots should count as shotguns (currently yes).
