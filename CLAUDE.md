# Labrums

Fantasy football league site: Sleeper data → standings, playoff odds (Monte Carlo), shotgun leaderboard, fake newsroom.
Stack: Python 3.11+ / FastAPI / numpy / SQLite, vanilla JS frontend in `static/`. Run: `LABRUMS_DEMO=1 uv run uvicorn app.main:app --reload` (demo) or without the env var for live Sleeper data. Tests: `uv run pytest`.

## Orchestration (user-directed 2026-09-10 — how Claude works here)

Fable is the orchestrator, not the worker: plans, writes specs, spawns agents, reads their reports, makes judgment calls, integrates. Roles are defined in `.claude/agents/` and must be used by name:

| agent | model | job |
|---|---|---|
| scout | haiku | find files/symbols/call sites; reports locations, never whole files |
| researcher | sonnet | reads docs/source/data, reports facts; unverifiable → UNVERIFIED |
| builder | sonnet | implements a clear spec, runs tests; changes only files in scope |
| refuter | opus | reviews the diff, reruns tests itself, tries to break it; "done" is not evidence |
| debugger | opus | hard root-cause only; reproduce → bisect data/code/env |

Rules:

- Fable does not read large amounts of code, do bulk refactors, write docs or do work a cheaper model can do. A one-line fix or single grep: Fable just does it — no agent for tiny things.
- Every sub-agent gets marching orders: specific goal; exact files/URLs in scope; what it may change; what to verify; what NOT to do; required output format; short output cap; what is already known.
- Reports come back short. Anything large goes to a scratch file and the next agent reads the file — no code dumps into Fable's context.
- Default coding loop: Fable → builder → refuter → Fable. Builders build, refuters verify; never the same agent for both.
- Read-only research/reviews may run in parallel. Never two agents editing the same files at once. Batch related fixes so big files are read once.
- Ultracode stays OFF unless the user asks for a larger workflow; when on, cap the agent count.
- Decisions and progress go into `docs/handoff.md` so a new session picks up from the file, not from rebuilt context. `docs/plan.md` is the short status board (right now / next / completed / dead ends) — update it at the end of every session (user-directed 2026-09-24).
- Keep Fable's replies and agent reports short unless more detail is actually needed. If an agent goes off track, stop it.
