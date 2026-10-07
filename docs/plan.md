# Plan / status board

## Right now
- Running against the real league (Labrums and Lagers, 10 teams, 2 divisions, dynasty). Verified vs Sleeper: 10/10 records, 14/14 shotguns, 2025 playoff field. 78 tests green. Pushed to `claude/magical-edison-g0t0m1`.
- Config is filled: 10 owner profiles with real names, 5 rivalry bowls, the Nick rule (Michael/Patrick/Bowie owe a shotgun any week they score less than Nick). Division seeding confirmed by the owner. Articles and pages use real first names; Sleeper handles shown as secondary. 82 tests green.
- Restyled to match davidsasser.com (paper/ink/green, Geist + Geist Mono, hairlines, square, mono eyebrows, data-driven hero). Refuter-verified: all interactions, dark mode, mobile. His site: Next.js (vinext) on Cloudflare.
- Vercel (free Hobby) deployment is ready: api/index.py + vercel.json; Upstash Redis for check-offs and the Sleeper cache; SQLite/disk stay the local defaults. 105 tests. UNVERIFIED on real Vercel until the owner imports the repo.
- Next for the owner: import the repo in Vercel, add Upstash Redis from Storage, set LABRUMS_ADMIN_PIN, redeploy (steps in README). Then report back the URL so the next session can smoke-test it.

## Next
- Fill `config.yaml` with the owner's real details (special rule owners/target, owner profiles, rivalries).
- First run against the live league ID on a machine that can reach api.sleeper.app; check real-data edge cases (co-owners, orphan rosters, divisions).
- Possible: optional LLM-written articles, draft recap, trade grades over time, light/dark toggle.
- Idea (owner asked 2026-10-06, NOT started): "Adam Schefter" bot in the league iMessage group. Options: always-on Mac + BlueBubbles (two-way), iPhone Shortcuts scheduled posts (one-way), or a Discord/GroupMe bot. Would use the site API + Claude API for the persona. Waiting on: spare device? two-way or scheduled?

## Completed
- 2026-10-06 (live): network allowlist opened; rounds 3-4 on real data (divisions + Sleeper seeding/tiebreaks, offseason roundup, regular-season schedule, ppts efficiency, per-season start date, seed column).
- 2026-10-06 (later): test suite, README, Dockerfile; refuter round 1 (17 findings fixed) and round 2 (4 leftovers fixed).
- 2026-10-06: project scaffold, Sleeper client + cache, demo fixture, stats, playoff Monte Carlo, shotgun detection + SQLite check-offs + manual adds, article generator, FastAPI API, SPA frontend (home/standings/teams/team detail/playoffs/shotguns/news/rivalries), CLAUDE.md orchestration rules, agent role files.

## Dead ends
- (Resolved) Sleeper was blocked from the sandbox until the owner added api.sleeper.app to the environment's allowed domains. Headless Chromium still can't load sleepercdn.com avatars here; that's a sandbox limit.
