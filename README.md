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

- **Render:** new Web Service, runtime Docker, add a disk mounted at `/app/data`.
- **Fly.io:** `fly launch`, then `fly volumes create data` and mount it at `/app/data`.
- **Railway:** deploy from the repo (it detects the Dockerfile) and attach a volume at `/app/data`.

## Tests

```bash
uv run pytest
```

The tests use the built-in demo data and never touch the network.

## Project layout

```
app/
  main.py        FastAPI app and API endpoints
  sleeper.py     Sleeper API client with a disk cache
  loader.py      Assembles one season into a plain dict
  stats.py       Standings, records, luck, lineup efficiency
  playoffs.py    Monte Carlo playoff odds
  shotguns.py    Shotgun detection and leaderboard
  articles.py    Fake newsroom
  db.py          SQLite store for check-offs and manual shotguns
  config.py      config.yaml loading
  demo.py        Deterministic fake league
static/          Vanilla JS frontend
tests/           pytest suite
config.yaml      League settings
Dockerfile
```
