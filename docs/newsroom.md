# Newsroom writer's guide (the editorial desk)

The site writes every article from templates, in the voice of one of 50 invented reporters. The **editorial desk**
lets a person (or an agent) replace any of those template articles with a hand-written one. Desk articles live in
the repo, override the template article with the same **key**, and post on the same release calendar. Nothing about
the desk needs an API key or a server: it is JSON files in `content/articles/`.

## Release calendar

Articles post at **6:00 am America/New_York**. Week W's "Tuesday" is the Tuesday after that week's games (week 1's is
the first Tuesday after the season start date; each later week is +7 days).

| Day | Type | Notes |
|---|---|---|
| Tue | `recap` (weekly roundup), `shotgun` (Beer Report) | |
| Wed | `waiver`, `trade` | a trade made after Tuesday posts the day after it was made |
| Thu | `preview`, `rivalry` | about week W+1; filed under week W+1 |
| Fri | `feud` | |
| Sat | `standings` | |
| Sun | `column` | trash-talk column: h2h, standings gaps, recent margins, rivalry backstory |
| Mon | `analytics` | luck index, lineup efficiency, bench points, weekly-rank consistency, trade early returns |
| season start | `offseason` | |

Every article carries `publish_on` (ISO date). The site hides articles whose `publish_on` is after today's edition
(before 6 am Eastern it is still yesterday's edition), lists them in `meta.desk.upcoming`, and shows everything for past
seasons. The admin can see unreleased articles with `GET /api/season/2026?preview=1` and the `X-Admin-Pin` header.
A desk article may override its date with `"publish_on": "YYYY-MM-DD"`.

## Stable keys

Every article has `key = "{season}:{type}:{week}:{teams}"`, for example `2026:recap:4:all` or `2026:feud:4:5-7`.
One-per-week pieces (recap, preview, shotgun, waiver, standings, analytics, offseason) use `all`; pair pieces
(trade, feud, column, rivalry) use the sorted roster ids joined by `-` (two trades between the same pair in one week
get `#2` by transaction id). Keys depend only on the data, never on which reporter was assigned or on build order.

## The weekly routine

1. `git pull`.
2. Export the facts for the week that just finished and for the upcoming week (its preview and rivalry piece):

   ```bash
   .venv/bin/python scripts/newsroom_facts.py --season 2026 --week 5
   .venv/bin/python scripts/newsroom_facts.py --season 2026 --week 6
   ```

   Each writes `content/facts/2026/week-N.json` (gitignored). `--all-pending` exports every week that has no desk
   file yet; `--out -` prints to stdout. The export holds, per article: `key`, `type`, `publish_on`, `teams`, the
   assigned reporter's voice card, `target_words`, the `facts` packet, the `beats` in order, and the current `template`
   text as a reference. `owners` lists every owner's name, team name, nickname, traits and catchphrase.
3. Write the articles you want to replace, in each article's assigned reporter's voice (or sign your own
   `reporter`). You do not have to write every article: whatever is not in the desk file stays template text.
4. Check the file:

   ```bash
   .venv/bin/python scripts/newsroom_lint.py content/articles/2026/week-5.json
   ```

   It prints PASS or FAIL per article (and WARN for soft rules such as length) and exits 1 on any failure.
5. Commit and push. The site picks the file up on the next rebuild (immediately after the refresh button).

   ```bash
   git add content/articles/2026/week-5.json && git commit -m "Desk: week 5" && git push
   ```

## File format

`content/articles/{season}/week-{W}.json`, filed under the week the article belongs to (a preview for week 6 goes in
`week-6.json` even though it runs on Thursday of week 5):

```json
{
  "week": 5,
  "articles": [
    {
      "key": "2026:recap:5:all",
      "headline": "Required",
      "dek": "Optional; defaults to the template dek",
      "body": ["Required: a list of paragraphs", "Second paragraph"],
      "reporter": {"name": "Optional", "outlet": "Optional", "bio": "Optional: all three or none"},
      "tags": ["optional"],
      "publish_on": "2026-10-13"
    }
  ]
}
```

A desk article replaces headline, dek, body, reporter and byline in place and is marked `source: "desk"` (the front end
shows "✎ Desk"). Everything else is `"template"`. An unknown key is logged and ignored. An entry that fails validation
or the coherence lint is skipped with a warning and the template article stays.

## Hard rules

- **Facts only.** Use only what the `facts` packet states: scores, margins, records, ranks, odds, players, trades, bids,
  shotguns, h2h, rivalry backstory and owner traits from config. No invented events, injuries, quotes about real-world
  news or players' real lives. Keep every number exactly as given.
- **Names.** Refer to owners by the `name` given (nickname at most once per article, and never mix a name and its
  nickname for the same person). Every team the article covers (`teams` in the export) must be named in the body.
- **Lengths.** 180-320 words for the weekly roundup and the weekly preview; 120-220 for everything else. The lint
  warns outside the range; it does not fail.
- **One catchphrase at most**, and only an owner who is a party to the story. No quotes that need the commissioner
  unless the speaker is the commissioner.
- **Voice.** Write in the assigned reporter's register: the family description, sentence rhythm, metaphor domain,
  signature opener/closer and at most one verbal tic. Don't copy the template's sentences.
- **PG-13.** Fun, not cruel. No slurs. Never call anyone a LARPer, in any spelling (the lint rejects "LARP").
- **Margin words.** "Blowout", "massacre" and the like only for a margin of 30 or more; "thriller", "escape" and the like
  only for a margin under 7. Playoff weeks are "playoff week N" with no standings shift.
- No `{` or `}` characters, no double spaces, no `..` or ` ,`, no "None", "nan" or "1 points".

## Under the hood

`app/newsroom/desk.py` loads and applies the files; `app/newsroom/calendar.py` computes `publish_on`;
`app/newsroom/tools.py` backs the two scripts. The desk re-reads a file when it changes on disk, and the refresh
button clears its cache.
