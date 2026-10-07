# Labrums

A fantasy football league site powered by the Sleeper API. It turns your league's raw scores into standings, playoff odds, a shotgun leaderboard, and a fake newsroom that writes about your friends.

## Features

- Standings, power rankings, luck (wins vs. all-play expected wins), lineup efficiency, league records.
- Playoff odds from a Monte Carlo simulation, including "if you win / if you lose" odds for next week.
- Shotgun leaderboard: every started player who scores zero or less (plus special rules) is a beer owed, with check-offs.
- Fake news: game recaps, matchup previews, rivalry hype, standings watch, trades, waivers, and feuds.
- Past seasons are discovered automatically through Sleeper's previous league chain.
- Demo mode with fake data, so you can try everything offline.

## Quick start

With [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Or with pip:

```bash
pip install -e .
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

Try it without a Sleeper league (no network needed):

```bash
LABRUMS_DEMO=1 uv run uvicorn app.main:app --reload
```

## Configuring your league

Everything lives in `config.yaml`. No code changes needed. Hit the refresh button on the site (or `POST /api/season/{season}/refresh`) to reload it.

**New season each year.** Add a line under `seasons` and bump `current_season`:

```yaml
current_season: "2027"
seasons:
  "2027": "1400000000000000000"
  "2026": "1312105961640448000"
```

Older seasons are also found by following `previous_league_id`, so the newest ID is the only one you strictly need.

**Owners** feed the articles. Use the Sleeper display name as the key. All fields are optional.

```yaml
owners:
  "Mike":
    nickname: "The Commish"
    bio: "Three-time runner-up, zero-time champion."
    traits: ["overpays for rookies", "never sets his lineup before Sunday"]
    catchphrase: "It's a marathon, not a sprint."
    hometown: "Philly"
```

**Rivalries** get hype pieces when the two owners meet:

```yaml
rivalries:
  - name: "The Brothers' War"
    owners: ["Mike", "Dan"]
    backstory: "Siblings. Loser hosts Thanksgiving."
```

**Special shotgun rules** are one-off extras on top of the zero-points rule:

```yaml
special_rules:
  - season: "2026"
    type: score_less_than_team     # owners owe a shotgun when they score less than target
    label: "Lost to Tyler on the scoreboard"
    owners: ["Mike", "Dan", "Jess"]
    target: "Tyler"
  - season: "2026"
    type: score_below              # owners owe a shotgun when they score under `points`
    label: "Under 80"
    owners: ["Ray"]
    points: 80
```

Other sections: `playoffs` (`teams`, `simulations`, `prior_games`), `shotguns` (below), and `reporters` (article bylines).

## Shotguns

A starter who scores `threshold` points or fewer (default 0) is a shotgun. Settings under `shotguns`:

- `threshold`: points at or below this count.
- `count_empty_slots`: an empty starting slot scores 0. Count it?
- `include_playoff_weeks`: count playoff and consolation weeks too?

Check-offs and manually added shotguns are stored in SQLite at `data/labrums.db` (`data/labrums-demo.db` in demo mode). Back up or mount that file to keep your history.

## Environment variables

| Variable | Purpose |
|---|---|
| `LABRUMS_DEMO` | `1` uses built-in fake league data instead of Sleeper. |
| `LABRUMS_DEMO_WEEK` | Current week in demo mode (default 7). |
| `LABRUMS_DEMO_DB` | `memory` keeps demo check-offs in memory (used by the tests). |
| `LABRUMS_ADMIN_PIN` | If set, write endpoints (check-offs, manual shotguns) need an `X-Admin-Pin` header with this value. |
| `LABRUMS_DATA_DIR` | Where the database and Sleeper cache live (default `./data`). |
| `LABRUMS_CONFIG` | Path to the config file (default `./config.yaml`). |
| `LABRUMS_MODEL_TTL` | Seconds to cache a built season before rebuilding (default 300). |

## How playoff odds work

Each team's weekly score is modeled as a normal distribution. Its mean and spread come from the team's own games, blended with the league average by `prior_games` games of weight so early-season odds do not overreact. The remaining regular-season games are simulated `simulations` times (default 5000). Seeds go by wins, then points for, and the top `teams` make the playoffs. The simulation uses a fixed random seed, so the numbers are stable between refreshes.

## Deploying

Docker:

```bash
docker build -t labrums .
docker run -p 8000:8000 -v labrums-data:/app/data labrums
```

Mount `/app/data` as a persistent volume or the check-offs disappear when the container is replaced. Set env vars with `-e`, for example `-e LABRUMS_ADMIN_PIN=secret`.

### Vercel (free Hobby plan)

The same app runs as a serverless function. SQLite and local files do not survive there, so check-offs and the Sleeper cache live in Upstash Redis (free).

1. Import the repo in Vercel. The first deploy happens automatically and runs in ephemeral mode (no Redis yet). The `app` object in `api/index.py` is detected as a FastAPI app, and the `/static` mount is served from the CDN. No build settings are needed. Python 3.12 or newer is required.
2. In the project, open Storage and create or connect an Upstash Redis database. Vercel injects `KV_REST_API_URL` and `KV_REST_API_TOKEN`. The app also reads `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` (the Upstash console names) and `LABRUMS_REDIS_URL` / `LABRUMS_REDIS_TOKEN`. Precedence when several pairs are set: `UPSTASH_*`, then `KV_*`, then `LABRUMS_*`.
3. Open Settings, then Environment Variables. Optional: set `LABRUMS_ADMIN_PIN` to protect check-offs and refresh, and `LABRUMS_REDIS_PREFIX` if several deployments share one database. Do **not** set `LABRUMS_DEMO`: demo mode never uses Redis and shows fake data.
4. Open Deployments and Redeploy. Environment changes only apply to new deployments.
5. For a custom domain, open Settings, then Domains, and add the CNAME or A record Vercel shows.

The first load after a deploy takes about 10 seconds while Sleeper is pulled, then pages load in under a second.

Without Redis on Vercel the app still works but writes to `/tmp`, which is wiped on cold starts. `meta.persistence` in `/api/season/<year>` reports `redis`, `sqlite` or `ephemeral`.

Free-tier limits that matter: Upstash allows 500K commands a month and 256 MB (about 90 Redis commands per cold build, 2 per warm page load, and warm instances reuse their built model for five minutes). Hobby functions can run up to 300 seconds; `vercel.json` sets 120. The first request after a cold start pulls from Sleeper if the Redis cache is empty, so it is slower. The players blob is stored zlib-compressed and stays well under 1 MB.

Other hosts that run the Docker image need a persistent volume at `/app/data`.

## Tests

```bash
uv run pytest
```

The tests use the built-in demo data and never touch the network.

## Project layout

```
app/
  main.py        FastAPI app and API endpoints
  sleeper.py     Sleeper API client with a pluggable (disk or Redis) cache
  loader.py      Assembles one season into a plain dict
  stats.py       Standings, records, luck, lineup efficiency
  playoffs.py    Monte Carlo playoff odds
  shotguns.py    Shotgun detection and leaderboard
  articles.py    Fake newsroom
  db.py          SQLite store for check-offs and manual shotguns
  redis_client.py  stdlib Upstash REST client
  storage.py     Redis store and Sleeper cache (used on Vercel)
  config.py      config.yaml loading
  demo.py        Deterministic fake league
static/          Vanilla JS frontend
tests/           pytest suite
config.yaml      League settings
Dockerfile
```
