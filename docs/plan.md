# Plan / status board

## Right now
- v0.1 complete on demo data, two adversarial review rounds applied, 58 tests green, pushed to `claude/magical-edison-g0t0m1`.
- Blocked on the owner: real config details (see handoff "Waiting on the owner") and a first live run against Sleeper from a machine that can reach it.

## Next
- Fill `config.yaml` with the owner's real details (special rule owners/target, owner profiles, rivalries).
- First run against the live league ID on a machine that can reach api.sleeper.app; check real-data edge cases (co-owners, orphan rosters, divisions).
- Possible: optional LLM-written articles, draft recap, trade grades over time, light/dark toggle.
- Idea (owner asked 2026-10-06, NOT started): "Adam Schefter" bot in the league iMessage group. Options: always-on Mac + BlueBubbles (two-way), iPhone Shortcuts scheduled posts (one-way), or a Discord/GroupMe bot. Would use the site API + Claude API for the persona. Waiting on: spare device? two-way or scheduled?

## Completed
- 2026-10-06 (later): test suite, README, Dockerfile; refuter round 1 (17 findings fixed) and round 2 (4 leftovers fixed).
- 2026-10-06: project scaffold, Sleeper client + cache, demo fixture, stats, playoff Monte Carlo, shotgun detection + SQLite check-offs + manual adds, article generator, FastAPI API, SPA frontend (home/standings/teams/team detail/playoffs/shotguns/news/rivalries), CLAUDE.md orchestration rules, agent role files.

## Dead ends
- Fetching Sleeper from the Claude sandbox: blocked by the environment's network policy (api.sleeper.app). Use demo mode here, live mode locally.
