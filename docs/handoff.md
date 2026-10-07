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

## Live league facts (verified 2026-10-06)
- "Labrums and Lagers", 10 teams, divisions Chuds (1) and Chads (2), superflex + 3 flex, 6 playoff teams, playoffs start week 15. Dynasty: offseason trades carry future picks and are tagged week 1 by Sleeper (collapsed into one "offseason" article using the season start date; past seasons derive the date from their own week-2 transactions).
- Playoff weeks: playing teams have a matchup_id, idle teams null; consolation games get ids too. Matchup ids are per week, not bracket numbers.
- Seeding (Sleeper default, researched): division winners take the top seeds, then best record; tiebreaks wins > PF > PA. Implemented in the sim and in the standings seed column; `playoffs.division_winners_top_seeds: auto`. playoff_seed_type numeric meanings are UNVERIFIED; `auto` assumes 0 = default.
- rosters[].settings.ppts is Sleeper's potential points (undocumented); used for lineup efficiency when present.
- Prior seasons 2025/2024/2023 are discovered via previous_league_id; 2025 has no divisions.

## Design system (2026-10-07)
Modeled on davidsasser.com (brief saved during the session; the tokens live at the top of static/styles.css). Paper #f4f3ef, ink #171816, muted #656861, faint #6b6e67 (raised from the reference's #898c85 for 4.5:1 contrast), border #d9dbd5, accent #235c3f. Geist + Geist Mono from Google Fonts. No shadows, radius 0 except avatars. Numbered mono eyebrows ("01 / STANDINGS"), 3px accent-top data cards, dashed accent cut line. Dark variant kept (the reference has none) under both prefers-color-scheme and data-theme. Hero copy on home is data-driven (unbeaten leaders, tied leaders, week 1, season complete).

## Hosting (2026-10-07)
- Target: Vercel Hobby (free). FastAPI auto-detected from api/index.py; static mount promoted to the CDN; vercel.json only sets maxDuration 120. requirements.txt mirrors pyproject (no uvicorn needed on Vercel). Python pinned >=3.12 (Vercel has no 3.11).
- Persistence: Upstash Redis via Vercel Marketplace (KV_REST_API_URL/TOKEN; also accepts UPSTASH_REDIS_REST_* and LABRUMS_REDIS_URL/TOKEN). RedisStore (check-offs, manual shotguns) and RedisCache (zlib+base64 Sleeper responses; players blob ~410 KB). Store failures degrade to read-only pages with meta.store_error; writes return 503. No Redis on Vercel → /tmp fallback, meta.persistence "ephemeral".
- Cold build from empty cache ~11 s (live Sleeper pulls); warm ~0.2 s. ~90 Redis commands per cold build, 2 per warm page view; players blob memoized in-process for 24 h.
- davidsasser.com itself: Next.js (vinext) on Cloudflare; static, hence free. Rejected for us: Render free (sleeps), Fly/Railway (no free tier), Cloudflare Pages static rebuild (more refactor).
- UNVERIFIED until a real deploy: FastAPI detection, static promotion, pyproject vs requirements precedence, real Upstash SCAN/limits.

## Known assumptions / unverified
- Clinch/eliminate: exact counting rule while games remain (ties on wins count as "can still pass me"); final standings decide once the regular season is over.

## Waiting on the owner
- Sleeper display names of the 3 owners under the special rule and the target team → `special_rules` in config.yaml.
- Owner profiles (nickname, bio, traits, catchphrase) → `owners`.
- Rivalry pairs and backstories → `rivalries`.
- Whether empty starting slots should count as shotguns (currently yes).
