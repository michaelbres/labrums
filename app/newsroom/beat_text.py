"""Line pools for the weekly team report (beat reporters). Pure text: every {placeholder} is filled from facts computed
in beats_team.py, and a pool is only used when the facts behind its placeholders exist. Tone keys: W (the owner won),
L (the owner lost), A (either). A tie reads from A, then L.

House rules: critical of the OWNER (the lineup-setter), never of the players; a win gets backhanded credit, a loss gets
the blame; no pronouns for the owner (their gender is not on file), no slurs, nothing about health, family tragedy or
protected characteristics. "Blowout"-class words only appear in the pools used for margins of 30 or more, and
"edged"-class words only in the pools used for margins under 7.
"""
from __future__ import annotations

# ---------------------------------------------------------------- the result itself
CORE = {
    "W": [
        "{o} beat {opp} {mine} to {theirs} in {wl}, and the most surprising part is how little of it looks like management.",
        "The scoreboard says {o} {mine}, {opp} {theirs}. The scoreboard is not a character reference.",
        "{o} took {wl} from {opp}, {mine}-{theirs}, and will describe it as a plan. It was a result.",
        "Credit where it is due, and not a point more: {o} won {mine}-{theirs} over {opp}.",
        "{o} got past {opp}, {mine} to {theirs}. A win is a win, even when it shows up by accident.",
        "{wl} went to {o}, {mine}-{theirs} over {opp}, and the group chat will be hearing about it for days.",
        "{o} won {mine}-{theirs}. {opp} lost. The distance between those two facts is narrower than {o} will admit.",
        "It took {mine} points for {o} to beat {opp}'s {theirs}, and every one of them came from a player rather than a decision.",
        "{o} beat {opp}, {mine}-{theirs}. It will be called a statement win by people who were not paying attention.",
        "{opp} came in with {theirs} and left a loser to {o}'s {mine}, a sentence the owner has already started rehearsing.",
        "Somehow, {o} beat {opp} {mine} to {theirs} in {wl}. Somehow is doing a lot of work in that sentence.",
        "{o} won {mine}-{theirs} over {opp}. Exactly how much of that belongs to the owner is a question the box score declines to answer.",
    ],
    "L": [
        "{o} lost to {opp} {theirs}-{mine} in {wl}, and the person who set the lineup is the person to blame.",
        "Final: {opp} {theirs}, {o} {mine}. The owner's fingerprints are all over it.",
        "{o} fell to {opp}, {mine} to {theirs}, in a result that surprised nobody who has been watching the lineup moves.",
        "There is a version of {wl} where {o} beats {opp}. It requires someone else running the team. The real version ended {mine}-{theirs}, a loss.",
        "{o} dropped {wl} to {opp}, {mine} to {theirs}, and has already started drafting the explanation.",
        "The loss to {opp}, {mine}-{theirs}, was not bad luck. Bad luck needs help, and {o} did this alone.",
        "{opp} beat {o} {theirs}-{mine}. The players played. The owner owned the outcome.",
        "{o} lost {mine}-{theirs} to {opp}, and the post-mortem should begin and end with the front office.",
        "{opp} took {wl} from {o}, {theirs}-{mine}, and the blame belongs to {o}.",
        "{o}'s team lost to {opp}, {mine}-{theirs}. It is the owner's team, so it is the owner's loss.",
        "{o} came up short against {opp}, {mine} to {theirs}, and the shortfall began long before kickoff, in the lineup.",
        "{opp} handed {o} a {margin}-point loss, {theirs}-{mine}, and the only thing {o} offered in return was a lineup full of questions.",
    ],
    "T": [
        "{o} and {opp} tied at {mine} in {wl}, a result that satisfies nobody and indicts everybody, starting with the owner.",
        "{wl} ended {mine}-{theirs} against {opp}, a tie, which is the scoreboard's way of saying {o} could not manage to win or lose properly.",
        "A tie with {opp}, {mine} apiece. {o} will call it a moral victory. It is a clerical event.",
    ],
}

# ---------------------------------------------------------------- the margin
MARGIN = {
    "blow_w": [
        "A {margin}-point margin is the sort of thing an owner frames and hangs up. The credit belongs to the players; the framing belongs to {o}.",
        "{margin} points. A blowout, and a blowout the roster delivered on its own.",
        "The margin was {margin}, a blowout that {o} will take personally and the players earned professionally.",
        "A blowout by {margin}. When the roster is this far ahead, the owner's best contribution is staying out of the way.",
        "{margin} points ahead. Even a lineup page that tried to get in the way could not stop it.",
    ],
    "blow_l": [
        "{margin} points is not a loss, it is a verdict, and {o} is the defendant.",
        "A {margin}-point blowout is a lot of points to lose by when the lineup could have been fixed all week.",
        "The margin was {margin}, a blowout, and a blowout takes more than one bad decision. {o} made several.",
        "Down by {margin} at the final whistle, a blowout, and the lineup was settled days before. The owner had every chance to make it closer.",
        "A blowout of {margin} points does not happen to a team with a sound plan. It happened to {o}.",
    ],
    "close_w": [
        "The margin was {margin}. That is not dominance, it is a clerical error that happened to land on {o}'s side.",
        "{margin} points separated the teams, which means one decision the other way and this is a different article.",
        "A {margin}-point win. {o} edged it, and edging is not the same as earning.",
        "{margin} points is the width of a bad start-sit decision, and the owner stood on the right side of it by luck.",
        "The final margin was {margin}. That is a win by a hair, and the hair was not the owner's.",
    ],
    "close_l": [
        "The margin was {margin} points: one better lineup call and this is a different article. It is this article.",
        "{margin} points. {o} lost a close one, and a close one is exactly the kind of game the owner is supposed to be there for.",
        "A {margin}-point loss is a decision somewhere, and the decision-maker is not hard to find.",
        "It came down to {margin} points, which is one swap, one waiver pickup, or one different week of attention from the owner.",
        "Lost by {margin}. Close games are decided at the margins, and the margins are where {o} does the least work.",
    ],
}

# ---------------------------------------------------------------- facts (one line each, chosen by what is notable)
FACTS = {
    "bench": {
        "W": [
            "And that was with {left} sitting on the bench. The optimal lineup was right there; {o} walked past it.",
            "Credit the players: {o} left {left} on the bench and won anyway, a sentence that sounds like praise and is not.",
            "The best possible lineup would have scored {opt}, which is {left} more than {o} managed. Winning with that on the table is a habit, not a strategy.",
            "The bench held {left} that never made it into the lineup. {o} won in spite of the bench, which is a theme.",
            "Even in a win, {o} left {left} on the bench. Imagine what a proper lineup might have done to the final score.",
            "The win came with {left} unused on the bench. A tighter lineup would have padded it, and a tighter owner would have noticed.",
        ],
        "L": [
            "The loss came with {left} stranded on the bench, points that were available and unused.",
            "{o} left {left} on the bench. The optimal lineup would have scored {opt}. The actual lineup scored {mine}.",
            "Somewhere on {o}'s bench sat {left} of production that never made the lineup. {o} had the keys.",
            "The bench held {left} that {o} chose not to start. It is hard to call the result a surprise.",
            "A better lineup, from the same roster, scores {opt}. {o} set the one that scored {mine}.",
            "{left} on the bench, unused. That number belongs on a sign outside {o}'s house.",
        ],
    },
    "bench_n": {
        "W": [
            "{bench_name} ({bench_pos}) scored {bench_pts} on the bench for {o}. The team won anyway, which {o} will use as evidence the bench was fine.",
            "On the bench: {bench_name} ({bench_pos}), {bench_pts}. In the lineup: whatever {o} was thinking. {o} won, so nobody is asking questions yet.",
            "{bench_name} ({bench_pos}) put up {bench_pts} from {o}'s bench, which is the kind of detail a winning owner gets to ignore.",
            "Not in the lineup, and not for lack of points: {bench_name} ({bench_pos}) scored {bench_pts} for {o} from the bench in a week the team won.",
            "{o} won while {bench_name} ({bench_pos}) sat on the bench with {bench_pts}. The bench is a place for players the owner does not trust, and that player did not deserve it.",
        ],
        "L": [
            "{bench_name} ({bench_pos}) put up {bench_pts} on {o}'s bench, which is the kind of detail that makes the loss feel authored.",
            "While {o} lost, {bench_name} ({bench_pos}) sat on the bench and scored {bench_pts}. Somebody made that seating chart.",
            "{bench_name} ({bench_pos}) scored {bench_pts} from the bench, and the bench is where {o} put it.",
            "Unused and unforgiven: {bench_name} ({bench_pos}) put up {bench_pts} on {o}'s bench in a loss.",
            "The loss has a footnote: {bench_name} ({bench_pos}), {bench_pts}, bench. {o} wrote that footnote.",
        ],
    },
    "bench_nr": {   # a bench player in the best legal lineup, with the starter he should have replaced
        "W": [
            "{bench_name} ({bench_pos}) scored {bench_pts} on {o}'s bench while {rep_name} ({rep_pos}) started and scored {rep_pts}. The team won anyway, which {o} will call vindication.",
            "{o} started {rep_name} ({rep_pos}) for {rep_pts} and benched {bench_name} ({bench_pos}), who scored {bench_pts}. A win covers a lot of start-sit sins.",
            "The slot that went to {rep_name} ({rep_pos}), {rep_pts}, was available to {bench_name} ({bench_pos}), {bench_pts}. {o} won and will not be revisiting the choice.",
            "In a winning week, {o} chose {rep_name} ({rep_pos}) over {bench_name} ({bench_pos}) and got {rep_pts} instead of {bench_pts}. A win is a good place to hide that.",
        ],
        "L": [
            "{o} started {rep_name} ({rep_pos}), who scored {rep_pts}, and left {bench_name} ({bench_pos}) on the bench for {bench_pts}. That is a decision, and a loss followed it.",
            "{bench_name} ({bench_pos}) put up {bench_pts} on the bench, in a slot {rep_name} ({rep_pos}) filled for {rep_pts}. {o} picked the wrong one.",
            "The start-sit that mattered: {rep_name} ({rep_pos}), {rep_pts}, in the lineup; {bench_name} ({bench_pos}), {bench_pts}, on the bench. The loss has {o}'s signature on it.",
            "{o} lost with {bench_name} ({bench_pos}) holding {bench_pts} on the bench and {rep_name} ({rep_pos}) taking the slot for {rep_pts}. Whose idea was that?",
            "Swap {rep_name} ({rep_pos}), {rep_pts}, for {bench_name} ({bench_pos}), {bench_pts}, and the week reads differently. {o} did not swap.",
        ],
    },
    "bench_gt": {
        "L": [
            "The {left} left on the bench is more than the {margin}-point margin, which turns the loss from a fate into a decision.",
            "{o} lost by {margin} and left {left} on the bench. That is not bad luck. That is arithmetic.",
            "Do the subtraction: a {margin}-point loss, {left} sitting on the bench. {o} owns the difference.",
            "The margin was {margin}. The bench held {left}. There is no version of this story in which the owner is not the main character.",
            "{left} on the bench and a {margin}-point margin: the loss was available to be avoided, and {o} had the lineup page open.",
        ],
    },
    "dud": {
        "A": [
            "Someone made the call to start {dud} ({dpos}), who produced {dpts}. {o} made the call.",
            "{dud} ({dpos}) scored {dpts} in a starting slot, a spot {o} filled on purpose.",
            "Start-sit report: {dud} ({dpos}), starter, {dpts}. Responsible party: {o}.",
            "{dpts} from {dud} ({dpos}) in a starting slot is the kind of number a person has to work at. {o} worked at it.",
            "The starting lineup included {dud} ({dpos}), who scored {dpts}. The starting lineup was set by {o}.",
            "{dud} ({dpos}) started and delivered {dpts}. Choosing who starts is the one part of the job that cannot be delegated.",
        ],
        "W": ["The win happened with {dud} ({dpos}) in the lineup for {dpts}, which was generous of the other starters."],
        "L": ["Part of the loss is {dud} ({dpos}), who started for {o} and returned {dpts}."],
    },
    "shotgun": {
        "A": [
            "The week also cost {o} {nsg}, for {sg_phrase}, which is a lot of damage for one lineup page.",
            "{o} earned {nsg} this week, for {sg_phrase}: the kind of week that makes the shotgun rule feel less like a punishment and more like a performance review.",
            "Then there is the shotgun count: {nsg} for {o}, for {sg_phrase}. It is the beat's job to report it and the owner's job to drink it.",
            "{o} picked up {nsg} in {wl} for {sg_phrase}. The rule exists for weeks like this one.",
        ],
    },
    "star": {
        "W": [
            "{star} ({spos}) put up {spts}, a performance {o} will take credit for and nobody else will.",
            "Credit {star} ({spos}), {spts}. {o}'s contribution was clicking the starter button.",
            "The top scorer was {star} ({spos}) with {spts}. That was the roster's doing, and the owner is welcome to the rest.",
        ],
        "L": [
            "{star} ({spos}) scored {spts} and still could not carry the weight of {o}'s other decisions.",
            "{star} ({spos}) put up {spts} in a losing cause, and it is worth asking what the rest of the lineup was for.",
            "{spts} from {star} ({spos}) deserved a better lineup around it.",
        ],
    },
    "luckywin": {
        "W": [
            "{o} scored {mine}, which ranked {wr_ord} of {n} in the league this week. The win came from the matchup, not the management.",
            "In {wl}, {k_teams} outscored {o}. {o} still won, which is a credit to the draw of the opponent and not to the owner.",
            "A {wr_ord}-best score and a win: that is what happens when the schedule hands over an opponent having a worse week. {o} thanks the schedule, presumably.",
            "{mine} was only {wr_ord}-best in a {n}-team league. The win is real. The case for the owner is not.",
        ],
    },
    "unlucky": {
        "L": [
            "{o} scored {mine}, the {wr_ord}-best total in the league, and still lost. Hard to do. Harder to do on purpose, though some days it looks intentional.",
            "A {wr_ord}-best score and a loss to {opp}. {o} will call it bad luck, and for once the luck argument is not nothing, but a dominant owner does not need the schedule's permission.",
            "{mine} was the {wr_ord}-highest score in the league. {o} lost anyway. That is the schedule's fault, and the owner will make sure everyone hears it.",
            "The one defense {o} has this week is that {mine} ranked {wr_ord} in the league. It is a good defense, and it is the only one.",
        ],
    },
    "lowscore": {
        "L": [
            "{mine} was the lowest score in the league this week. Not near the bottom of the league; the bottom.",
            "Of the {n} teams in the league, {o} scored the fewest points this week, {mine}. That is a distinction.",
            "Nobody in the league scored fewer than {o}'s {mine} this week. It is a record of sorts, and the beat is obliged to report it.",
            "The league's lowest score of the week, {mine}, belongs to {o}. Wear it.",
        ],
    },
    "highscore": {
        "W": [
            "{mine} was the league's high score in {wl}, a week of good work by the players that {o} is already treating as personal expertise.",
            "The league's best score of the week, {mine}, belongs to {o}. Savor it; the beat does not expect to be saying this often.",
            "{o} had the high score of the week at {mine}. That is a roster talking, and the owner is allowed to listen.",
            "Top score in the league, {mine}. {o} will credit the process. The process, as far as this reporter can tell, is the players.",
        ],
    },
    "avgweek_up": {
        "A": [
            "The league averaged {lavg} in {wl}. {o} scored {mine}, {diff} above it, which is not much credit for a lot of points.",
            "{o} cleared the week's league average of {lavg} by {diff}. Clearing an average is the minimum.",
            "At {mine}, {o} finished {diff} above the league's {lavg} average. Being above average is something an owner can do by accident, and sometimes does.",
            "Above average by {diff}: {mine} against a league mean of {lavg}. Do not throw a parade.",
        ],
    },
    "avgweek_dn": {
        "A": [
            "The league averaged {lavg} in {wl}. {o} scored {mine}, {diff} below it. Below average is a choice, and the lineup was the choice.",
            "{mine} for {o}, against a league average of {lavg}: {diff} short, and the shortfall begins in the lineup.",
            "{o} finished {diff} below the week's league average of {lavg}, with a full roster and a full week to prepare.",
            "Below the league average by {diff}, {mine} against {lavg}. The average team did not do this.",
        ],
    },
    "standing": {
        "W": [
            "At {rec}, {o} sits {rank_ord} in the standings, {line} the playoff line, a position the owner will call earned.",
            "{o} is {rec}, {rank_ord} overall and {line} the playoff line. Do not ask how.",
            "The record stands at {rec} for {o}, good for {rank_ord}, {line} the playoff line, thanks in large part to the players on it.",
            "{rec} and {rank_ord} place, {line} the playoff line: that is where {o} finds the team after {wl}.",
        ],
        "L": [
            "At {rec}, {o} sits {rank_ord} in the standings, {line} the playoff line, and the lineup is not helping.",
            "{o} is {rec}, {rank_ord} overall and {line} the playoff line. It reads like a team with no one at the controls.",
            "The record stands at {rec} for {o}, {rank_ord} in the league, {line} the playoff line, and the trend is the owner's to explain.",
            "{rec} and {rank_ord} place, {line} the playoff line: that is the state of {o}'s team after {wl}.",
        ],
    },
    "leader": {
        "W": [
            "{o} leads the league at {rec}, and the league is entitled to ask how.",
            "First place, {rec}, and still the owner is getting more credit than the roster.",
            "{o}'s team sits atop the standings at {rec}. The owner will take the credit; the schedule and the players are owed some of it.",
        ],
        "L": [
            "Even in first place at {rec}, {o} is losing games in ways a leader should not.",
            "{o}'s team still leads the league at {rec}. The standings have not caught up with the lineup.",
            "{o} remains first at {rec}, which is a credit to the roster and a coincidence for the owner.",
        ],
    },
    "cellar": {
        "W": [
            "Even with the win, {o} is last at {rec}. The win is a rounding error in a larger story.",
            "{o} sits at the bottom of the standings at {rec}, win and all.",
            "{rec}, and still last. A win is nice. The owner needs a lot more of them.",
        ],
        "L": [
            "{o} is last at {rec}, a place that requires effort.",
            "{rec}, dead last. The bottom of the standings is {o}'s now, rent-free.",
            "At the bottom of the league at {rec}, the team is a long way from anything and {o} is the one driving.",
        ],
    },
    "up": {
        "A": [
            "{o} climbed {k} spots to {rank_ord}, which will be mentioned in the group chat more times than it deserves.",
            "Climbing from {prev_ord} to {rank_ord} is the least the owner could do.",
            "{o} rose from {prev_ord} to {rank_ord}, and has been acting like it was a plan ever since.",
            "From {prev_ord} to {rank_ord}: a climb the players made and the owner is claiming.",
        ],
    },
    "down": {
        "A": [
            "{o} slid from {prev_ord} to {rank_ord}, a drop of {k} places that the lineup has been working toward.",
            "{k} places is how far {o} fell, from {prev_ord} to {rank_ord}, and it did not happen by accident.",
            "{o}'s team dropped from {prev_ord} to {rank_ord}. Gravity works on owners too.",
            "Down to {rank_ord} from {prev_ord}: {k} spots lost in one week, which takes talent.",
        ],
    },
    "streak": {
        "W": [
            "That is {k} straight wins for {o}, a streak that has made the owner insufferable and has not yet made the owner good.",
            "{o} has won {k} in a row. Streaks are what happen when the schedule and the players cooperate; the owner just stands near them.",
            "{k_cap} straight wins now. {o} is going to call it momentum. It is called a schedule.",
            "{o}'s team has run off {k} straight wins, and {o} has handled the success the way the owner handles everything: loudly.",
        ],
        "L": [
            "{o} has now lost {k} straight, and at some point a streak is just the team.",
            "{k_cap} straight losses for {o}, and each one has the same signature on it.",
            "{o}'s team has lost {k} in a row. At this point it is a trend line, and the trend is {o}.",
            "{k_cap} games, {k} losses, one owner. This reporter does the math so nobody has to.",
        ],
    },
    "streak_end": {
        "L": [
            "That ends a {k}-game winning streak for {o}, one the owner treated as a skill.",
            "The {k}-game winning streak is over. {o} will blame the loss on the matchup; the lineup was due.",
            "A {k}-game winning streak ended in {wl}. It lasted exactly as long as the owner's luck.",
        ],
    },
    "snap": {
        "W": [
            "{o} snapped a {k}-game losing streak, which is the minimum the situation required.",
            "The {k}-game losing streak is over. {o} is expected to take credit.",
            "A win ends a {k}-game skid for {o}. It is the sort of progress that gets a press release in some leagues.",
        ],
    },
    "luck_pos": {
        "A": [
            "By the all-play math, {o} should be {exp_rec}. The record says {rec}. Someone is getting a lot of help from the schedule.",
            "{o}'s {rec} is flattered by luck: the all-play numbers put the team nearer {exp_rec}.",
            "The record is {rec}; the all-play record says {exp_rec}. The difference is the schedule's and not the owner's.",
        ],
    },
    "luck_neg": {
        "A": [
            "Unlucky, sure: the all-play record says {o} should be {exp_rec}, not {rec}. But a good team beats the schedule, not just the numbers.",
            "{o} is {rec} where the all-play math says {exp_rec}. Bad luck explains some of it. Lineup decisions explain what bad luck does not.",
            "The all-play numbers say {exp_rec}. The record says {rec}. {o} will blame the schedule. The schedule is only part of it.",
        ],
    },
    "subpar": {
        "A": [
            "{o} has landed below the league median in {c} of {m} weeks. A record can hide that. The scoring cannot.",
            "In {c} of {m} weeks, more than half the league outscored {o}. That is not a bad stretch, that is the profile.",
            "Below the median in {c} of {m} weeks: the owner's results are better than the owner's play, and that gap is luck.",
        ],
    },
    "bottom": {
        "A": [
            "{o} has had the league's lowest score of the week {k_times} this season. Some owners hold records. This owner holds a floor.",
            "The league's lowest score of the week has belonged to {o} {k_times} so far. The bottom has a regular.",
            "{k_times_cap} this season, {o} has posted the week's lowest score. It is no longer a fluke.",
        ],
    },
    "top": {
        "W": [
            "{o} has had the league's high score {k_times} this season. It is the one statistic that makes the rest of the record harder to explain.",
            "The week's high score has been {o}'s {k_times}, which is evidence of a good roster and not necessarily a good owner.",
            "High score of the week, {k_times}. A roster that talented should be winning more arguments than the owner is.",
        ],
    },
    "trade_pending": {
        "A": [
            "{o} made a trade with {partner}, taking {got} and sending {gave}. Trades are what {o} does when {o} has a feeling, and feelings are not a roster strategy.",
            "The week's transaction: {o} sent {gave} to {partner} for {got}. The verdict will come in. The owner will not like it.",
            "{o} traded {gave} to {partner} for {got}, a deal that has not yet been graded and is already being defended.",
            "Newest addition to {o}'s roster: {got}, from {partner}, for {gave}. The beat reserves judgment, which is a courtesy.",
        ],
    },
    "trade_lead": {
        "A": [
            "{o} traded with {partner} and, so far, is ahead: {got} produced {my_pts} against {their_pts} for {gave}. Note the phrase so far.",
            "Early returns on the {partner} trade favor {o}, {split}. It is good news and probably an accident.",
            "{o}'s side of the {partner} trade is ahead, {split}. Enjoy it. The sample is only as big as it is.",
        ],
    },
    "trade_trail": {
        "A": [
            "{o}'s side of the trade with {partner} is behind, {split}. That is what is known in the business as a bad trade.",
            "Early returns on the {partner} trade: {my_pts} for {o}, {their_pts} for {partner}. The owner made the deal and now owns the number.",
            "Getting {got} for {gave} returned {my_pts} to {o}; {gave} returned {their_pts} to {partner}. {o} lost this one on the merits.",
        ],
    },
    "waiver_bid": {
        "A": [
            "On the waiver wire, {o} paid {bid} for {player} ({pos}). Whether that is a bargain or a confession depends on the next few weeks.",
            "{o} bid {bid} on {player} ({pos}), the kind of move that looks like activity and often is only that.",
            "{o} spent {bid} of the waiver budget on {player} ({pos}). A budget is a plan only if there is a plan.",
            "{bid} for {player} ({pos}). The waiver budget is finite, and {o} is spending it like it is not.",
        ],
    },
    "waiver_free": {
        "A": [
            "{o} added {player} ({pos}) off the wire for free. The price is right; the plan is not clear.",
            "{o} picked up {player} ({pos}) off the wire, which is the owner's way of looking busy.",
            "The waiver move of the week for {o}: {player} ({pos}), at no cost. You get what you pay for, and so does {o}.",
            "{player} ({pos}) came off the wire to {o} for nothing. That is the right price for an unexplained roster move.",
        ],
    },
    "waiver_multi": {
        "A": [
            "{o} made {n_adds} adds this week, led by {player} ({pos}). That is a lot of motion, and the standings are the measure of it.",
            "{n_adds_cap} waiver adds from {o} in {wl}, headlined by {player} ({pos}). Activity is not the same as improvement.",
            "{o} worked the wire {n_adds} times this week, with {player} ({pos}) the headliner. The roster is a revolving door and the owner is the one pushing it.",
        ],
    },
    "waiver_low": {
        "A": [
            "{player} ({pos}) has produced {since_pts} for {o} since the claim. The claim was a mistake with a transaction ID.",
            "{since_pts} from {player} ({pos}) since {o} added the player. That is not a pickup, that is a donation.",
            "{o} claimed {player} ({pos}) and has {since_pts} to show for it. The wire is not a lottery, though the owner plays it like one.",
            "Since the claim, {player} ({pos}) has returned {since_pts} to {o}'s team. Somebody saw something in that. It was not the numbers.",
            "The pickup of {player} ({pos}) has been worth {since_pts} so far, which is what unplanned activity looks like on a stat sheet.",
        ],
    },
    "waiver_mid": {
        "A": [
            "{player} ({pos}) has given {o} {since_pts} since the claim, an unremarkable return on a move that was treated as remarkable.",
            "{o}'s waiver add, {player} ({pos}), has returned {since_pts} so far. Fine. Nobody is going to build a statue.",
            "{player} ({pos}) has put up {since_pts} for {o} since the add. Serviceable, which is a high bar for this owner's waiver record.",
            "Since being claimed, {player} ({pos}) has given {o}'s team {since_pts}. It is neither the move of the year nor the mistake of it.",
            "{since_pts} from {player} ({pos}) since {o} added the player: a fine return that will be described as genius in the group chat.",
        ],
    },
    "waiver_hi": {
        "A": [
            "{player} ({pos}) has returned {since_pts} since {o} picked up the player. Mark the date; it will not come up again.",
            "{o} got a good one in {player} ({pos}), {since_pts} since the claim. A broken clock, and so on.",
            "The add of {player} ({pos}) is working: {since_pts} since the claim. Even this owner gets one by accident now and then.",
            "{since_pts} for {o}'s team from {player} ({pos}) since the pickup. Good for the roster; the owner will take the credit anyway.",
            "{player} ({pos}) has put up {since_pts} since {o} claimed the player. Credit the eye; question the process.",
        ],
    },
    "eff": {
        "A": [
            "Across the season, {o} has left {season_left} on the bench, a lineup efficiency of {eff_pct} that ranks {eff_rank_ord} of {n} in the league.",
            "Lineup efficiency, season to date: {eff_pct}, {eff_rank_ord} of {n} teams. The roster has points. The lineup page is where they go to sit down.",
            "{season_left} stranded on the bench this season is not a rounding error. It is {eff_pct} lineup efficiency, {eff_rank_ord} in a {n}-team league.",
            "By lineup efficiency, {o} is {eff_rank_ord} of {n} at {eff_pct}, with {season_left} of available points left sitting down.",
        ],
    },
    "odds_low": {
        "A": [
            "The simulations give {o} a {odds} shot at the playoffs. Small number, large ambition.",
            "Playoff odds for {o}'s team stand at {odds}, and the owner's plan for improving them is not on file.",
        ],
    },
    "odds_mid": {
        "A": [
            "Playoff odds sit at {odds} for {o}, which is a coin flip, which is also how some of the lineup decisions look.",
            "The model puts {o}'s team at {odds} to make the playoffs. That is about as certain as the lineup choices.",
        ],
    },
    "odds_high": {
        "A": [
            "At {odds} to make the playoffs, {o} is in good shape, a position the owner will treat as personal achievement and the schedule has a share in.",
            "The model likes {o}'s team, {odds} to reach the playoffs. The model has not looked closely at the lineup page.",
        ],
    },
    "odds_clinched": {
        "A": ["{o} has clinched a playoff spot, which is the point of the whole exercise and now the owner is on the clock to do something with it."],
    },
    "odds_out": {
        "A": ["{o} has been mathematically eliminated from the playoffs, which took real commitment."],
    },
    "avg_up": {
        "A": [
            "{o} averages {avg} a week, {diff_s} above the league's {lavg_s}. The roster is strong; ask why that has not been enough to dominate.",
            "{avg} a week for {o}, {diff_s} better than the league's {lavg_s}. A roster that good makes the owner's mistakes more expensive, not less.",
            "{o}'s team averages {avg}, against a league average of {lavg_s}. Credit the roster; the owner is only on the invoice.",
        ],
    },
    "avg_dn": {
        "A": [
            "{o} averages {avg} a week against a league average of {lavg_s}. That is {diff_s} short, and the shortfall begins at the front office.",
            "{avg} a week is {diff_s} below the league's {lavg_s}. The team has been below average for long enough that it is the plan.",
            "{o}'s team scores {avg} a week, {diff_s} below the {lavg_s} league average. This is not variance. This is a profile.",
        ],
    },
    "consol": {   # a game in the consolation bracket: never claims the team is in the playoffs
        "A": [
            "{o} finished the regular season {rec}, {rank_ord}. The title is not on the line in {wl}, which is a bad setting for a lineup that was already not on the line.",
            "This was a consolation game, nothing riding on it but pride and a draft slot, and {o}'s lineup treated it with the seriousness it deserved.",
            "A {rec} record and a {rank_ord}-place finish put {o} here, in a game that decides nothing. It is the right game for this owner.",
            "Nothing in {wl} counts toward a title. {o} spent the week finding out whether that is also the lineup's philosophy.",
            "{o} is {rec} and {rank_ord} on the year, and the season's last games are being played for position. The beat is not sure {o} knows the difference.",
            "There is no title in {wl} for {o}, and there is no excuse for the lineup either.",
        ],
    },
    "finish": {
        "A": [
            "{o} came into the postseason at {rec}, {rank_ord} after the regular season. The regular season record is the owner's best argument and it is not a great one.",
            "Regular season: {rec}, {rank_ord}. That is what {o} brought to {wl}, and this is what happened.",
            "{o}'s team finished the regular season {rec}, {rank_ord}. It was enough to get here. It was not enough to make anyone confident.",
        ],
    },
}

# ---------------------------------------------------------------- jabs from the owner profile (and generic ones for when there is none)
TRAIT = {
    "A": [
        "This is, after all, the owner who {trait}. {o} is consistent, if nothing else.",
        "Nobody should be shocked. {o} {trait}.",
        "Context matters, and the context is that {o} {trait}.",
        "It helps to remember that {o} {trait}.",
        "A word on the owner: {o} {trait}. Draw the conclusions.",
        "Everything about {wl} makes more sense once you accept that {o} {trait}.",
        "Say what you want about the lineup, but {o} {trait}, and that explains a lot.",
        "For the record, and this is relevant: {o} {trait}.",
    ],
    "W": [
        "The win is real. So, unfortunately, is the fact that {o} {trait}.",
        "Enjoy it while it lasts, since {o} {trait} and the schedule will not stay this kind.",
        "Before the owner takes a victory lap, a reminder: {o} {trait}.",
        "A win cannot hide it. {o} {trait}.",
    ],
    "L": [
        "The loss reads like a character reference: {o} {trait}.",
        "The result surprised no one who knows that {o} {trait}.",
        "The loss makes sense in the light of one fact: {o} {trait}.",
        "If you want to know how {wl} went wrong, start with the part where {o} {trait}.",
    ],
}
NICK = {   # the nickname only ever appears as: <name>, “<nick>” to the group chat, <lowercase verb ...>
    "A": [
        "{o}, “{nick}” to the group chat, has earned that name the hard way, one lineup at a time.",
        "{o}, “{nick}” to the group chat, will blame the matchup, the injuries, the weather or the schedule. It was the lineup.",
        "{o}, “{nick}” to the group chat, would like it noted that {wl} was not the plan. The beat would like it noted that there was no plan.",
    ],
    "W": ["{o}, “{nick}” to the group chat, is already calling the win part of a plan. There was no plan."],
    "L": ["{o}, “{nick}” to the group chat, has an explanation ready. It will not hold up against the box score."],
}
HOME = {
    "A": [
        "Back in {home}, somebody is reading this and quietly closing the tab.",
        "{home} has been through worse. Not much worse, but worse.",
        "{home} sent the league {o}, and the league is still processing it.",
    ],
    "W": ["Somewhere in {home}, {o} is describing this win as expertise."],
    "L": ["Somewhere in {home}, the people who love {o} are reading this and nodding."],
}
CATCH = {
    "A": [
        "{o} has a line for every occasion: {q} The standings have a line too, and it is a number.",
        "Asked to sum it up, {o} could always fall back on the classic, {q} It has aged poorly.",
    ],
}
GENERIC = {
    "A": [
        "Nothing here is the players' fault. Players do what they are given to do; the owner chooses what they are given.",
        "The common factor in every one of {o}'s results this season is {o}.",
        "The roster did its best. The owner did what the owner does.",
        "If this team is ever to turn this around, the first move is a different owner, and that is not on the table.",
        "{o} has had every tool this week: a lineup page, a bench, a waiver wire. What was done with the tools is another story.",
    ],
    "W": ["A win like this is almost always the players' doing. The owner will take it anyway."],
    "L": ["The players showed up. The decisions showed up too, which was the problem."],
}

# ---------------------------------------------------------------- structure glue
VERDICT = {
    "W": [
        "Verdict: a win, which {o} did not earn so much as receive.",
        "Verdict: {o} won and will be insufferable until the next loss.",
        "Final grade on the owner's contribution: participation.",
        "Verdict: the team is better than its owner, a gap that grew this week.",
        "Verdict: congratulations to the players; condolences to anyone who has to hear {o}'s version.",
        "Verdict: {o} won, and everyone around the team is hoping nobody looks closely at how.",
        "Verdict: a win that reflects well on the roster and the schedule and leaves the owner's name out of it.",
        "Verdict: the win stands, the explanation does not.",
    ],
    "L": [
        "Verdict: a loss, and the owner is the lead suspect.",
        "Verdict: the players have been cleared. The owner has not.",
        "Verdict: {o} lost this one and will spend the week writing the explanation, which will not be the lineup.",
        "Verdict: self-inflicted.",
        "Verdict: {o}'s team lost, and the file is on {o}'s desk.",
        "Verdict: no mystery here, just a series of decisions.",
        "Verdict: the blame is where it always is, and it has a username.",
        "Verdict: the box score has the result; the owner has the responsibility.",
    ],
    "T": [
        "Verdict: a tie, which is what happens when the owner is neither good enough to win nor bad enough to lose.",
        "Verdict: nobody won, which is the closest {o} has come to a clean sheet.",
    ],
}
GRADE_INTRO = [
    "Report card for {o}, {wl}: {grade}.",
    "The beat grades {o}'s {wl}: {grade}.",
    "This week's grade for {o}: {grade}.",
    "Grade for {o}'s management of {wl}: {grade}.",
]
GRADE_CASE = [
    "The case for the grade:",
    "How the grade was reached:",
    "Reasons for the {grade}:",
    "The comments on the report card:",
]
HOMEWORK = {
    "bench": ["Homework for {o}: start the players who score the points.", "Homework for {o}: read the bench before the games, not after.", "Assignment for {o}: the best lineup is the one with the points in it."],
    "dud": ["Homework for {o}: find out who is actually playing before starting them.", "Homework for {o}: check the starter list for names that have stopped scoring.", "Assignment for {o}: look at the zero before it happens."],
    "shotgun": ["Homework for {o}: a lineup that does not cost a shotgun.", "Assignment for {o}: one week with no one owing a beer.", "Homework for {o}: make the shotgun rule feel unnecessary."],
    "trade": ["Homework for {o}: leave the trade button alone for a week.", "Assignment for {o}: reread the last trade before proposing the next.", "Homework for {o}: keep the roster, for once."],
    "streak": ["Homework for {o}: understand why the streak is happening before it ends.", "Assignment for {o}: explain the streak without using the word momentum.", "Homework for {o}: take the streak seriously, in either direction."],
    "waiver": ["Homework for {o}: spend the budget on a plan.", "Assignment for {o}: one claim a week, with a reason.", "Homework for {o}: explain the add before making it."],
    "wk": ["Homework for {o}: win with a better score.", "Assignment for {o}: score more than the schedule allows.", "Homework for {o}: do something with the lineup that the scoreboard notices."],
    "eff": ["Homework for {o}: raise the lineup efficiency above the floor.", "Assignment for {o}: stop leaving points on the sideline.", "Homework for {o}: a lineup that uses the whole roster, not part of it."],
    "default": ["Homework for {o}: anything.", "Assignment for {o}: a plan.", "Homework for {o}: show the work."],
}
LEDGER_INTRO = ["{column}, {wl}: the numbers on {o}.", "From {column}, {wl}:", "The ledger on {o} for {wl}:"]
NOTE_LABEL = ["Note {i}:", "Item {i}:", "{i}."]
NOTE_INTRO = ["{column}, {wl}: notes on {o} and the team.", "Notes on {o}'s team, {wl}.", "{column}: {wl}, one note at a time."]
Q_INTRO = ["Three questions for {o} after {wl}.", "Questions the beat would like answered by {o}.", "{wl} leaves {o} with questions to answer."]
Q_OUTRO = [
    "Answers are expected by next week's kickoff. They are not expected to be good.",
    "The beat will wait by the group chat.",
    "Responses may be sent to the lineup page, which is where the problem started.",
]
Q_DEFAULT = ["What, exactly, is the plan?", "Who is running this team?", "Is this the version of the lineup {o} meant to set?"]
QUESTIONS = {
    "bench": ["Why were {left} left on the bench?", "What did the bench do to deserve {left} of points left unused?"],
    "bench_n": ["Why was {bench_name} ({bench_pos}) on the bench for {bench_pts}?", "Who made the seating chart that put {bench_name} on the bench?"],
    "bench_nr": ["Why did {rep_name} ({rep_pos}) start over {bench_name} ({bench_pos})?", "What did {o} see in {rep_name} ({rep_pos}) that {bench_name} ({bench_pos}) was missing?"],
    "consol": ["Does {o} even know which bracket this is?", "What is the plan for {wl}, other than a better draft slot?"],
    "bench_gt": ["Why did {left} sit on the bench in a {margin}-point loss?", "With {left} on the bench and a {margin}-point margin, whose fault is it?"],
    "dud": ["Why was {dud} ({dpos}) in the lineup for {dpts}?", "What did {o} see in {dud} ({dpos}) that the {dpts} says was not there?"],
    "shotgun": ["How does one lineup end up costing {nsg}?", "Is there any version of the shotgun rule that {o} has not already tested this week?"],
    "star": ["With {spts} from {star} ({spos}), what was the rest of the lineup for?", "Who deserves the credit for {star} ({spos})? Not the owner."],
    "luckywin": ["How much of this win was {o} and how much was the schedule?", "Does a {wr_ord}-best score deserve a win?"],
    "unlucky": ["Does {o} still call it bad luck when {mine} is the {wr_ord}-best score in the league?", "Is bad luck a plan?"],
    "lowscore": ["How does a team score the fewest points in the league?", "Does {o} know the lineup page has a submit button?"],
    "highscore": ["Was the league's high score the owner's doing or the roster's?", "What does {o} plan to credit this time?"],
    "avgweek_up": ["Is clearing a {lavg} average something to put on a banner?", "How much credit does {o} think a {diff} edge deserves?"],
    "avgweek_dn": ["How does a team finish {diff} below the league average?", "What happened between the roster and the lineup?"],
    "standing": ["Is {rank_ord} where {o} wanted to be at {rec}?", "What is {o}'s plan for a record of {rec}?"],
    "leader": ["How does a leader at {rec} still find things to get wrong?", "Is first place the roster's doing or the owner's?"],
    "cellar": ["How long can {o} afford last place at {rec}?", "Is the bottom of the standings a destination or a stop?"],
    "up": ["What does {o} think moved the team from {prev_ord} to {rank_ord}?", "Is the climb to {rank_ord} the owner's or the players'?"],
    "down": ["What moved the team from {prev_ord} to {rank_ord}?", "How does {o} explain a drop of {k} places?"],
    "streak": ["Does {o} understand why the streak is {k} games, and is {o} sure?", "At what point does a streak become a plan?"],
    "streak_end": ["What ended the {k}-game winning streak, besides the lineup?", "Was the winning streak ever the owner's?"],
    "snap": ["What changed to end the {k}-game skid?", "Why did the skid last {k} games?"],
    "luck_pos": ["Is {rec} a record or a rumor, given the all-play numbers?", "How long does {o} expect the schedule to keep helping?"],
    "luck_neg": ["Is the schedule really to blame for {rec} when the all-play record says {exp_rec}?", "What does {o} plan to do about the part of the record the schedule did not cause?"],
    "subpar": ["Why has more than half the league outscored {o} in {c} of {m} weeks?", "What is {o}'s answer to {c} sub-median weeks?"],
    "bottom": ["How many more times will the lowest score of the week belong to {o}?", "Is the floor of the league {o}'s permanent address?"],
    "top": ["If the roster can top the league {k_times}, why is the record not better?", "What does {o} do differently in the weeks the roster does not top the league?"],
    "trade_pending": ["What was {o} thinking, trading {gave} to {partner} for {got}?", "Why trade with {partner} at all?"],
    "trade_lead": ["Does {o} understand that {split} is an early read and not a verdict?", "Will {o} trade again out of confidence?"],
    "trade_trail": ["Why did {o} trade {gave} for {got}, with {my_pts} to show for it?", "Is the {partner} trade the lesson {o} needed?"],
    "waiver_bid": ["What was {bid} on {player} ({pos}) supposed to fix?", "Who talked {o} into spending {bid}?"],
    "waiver_free": ["What did {player} ({pos}) do to earn the roster spot?", "Is {player} ({pos}) a plan or a placeholder?"],
    "waiver_multi": ["What is {o} doing with {n_adds} adds in a week?", "Is activity a strategy?"],
    "waiver_low": ["Why did {o} claim {player} ({pos}) for {since_pts}?", "Is {player} ({pos}) the move or the mistake?"],
    "waiver_mid": ["What did {o} expect of {player} ({pos}) beyond {since_pts}?", "Is {since_pts} what the claim was supposed to return?"],
    "waiver_hi": ["Is {player} ({pos}) the exception or the rule for {o}?", "Does {o} know how to find a second one like it?"],
    "eff": ["How does {o} explain {season_left} left on the bench this season?", "Is {eff_pct} lineup efficiency a choice?"],
    "odds_low": ["What would it take to move a {odds} playoff chance?", "Does {o} have a plan or a hope?"],
    "odds_mid": ["Is {odds} a good place for {o} to be, or just the place the schedule left the team?", "Will {o} spend the next week fixing the lineup or explaining it?"],
    "odds_high": ["With {odds} playoff odds, what is {o} going to do to ruin them?", "Is the owner ready for this to go well?"],
    "odds_clinched": ["Now that the team is in, is there a plan?", "What does {o} do with a clinched spot?"],
    "odds_out": ["What does {o} plan to say about being mathematically out?", "Is next year's plan any different?"],
    "avg_up": ["With {avg} a week, why is the record not better?", "Is {o} using the roster or just standing near it?"],
    "avg_dn": ["What is the plan for averaging {avg} against a league {lavg_s}?", "Is {avg} a week the roster's ceiling or the owner's?"],
    "finish": ["Was {rank_ord} the plan?", "Is a record of {rec} enough for {o}?"],
}

# ---------------------------------------------------------------- headlines
HEAD = {
    "W": [
        "{o} Beats {opp}, and Takes More Credit Than the Box Score Allows",
        "{o} Wins {mine}-{theirs}; the Owner Gets the Credit Anyway",
        "{o} Wins {wl}, to Everyone's Mild Surprise",
        "Beat Report: {o} Wins, Which Settles Nothing",
        "{o} Beats {opp} {mine}-{theirs} and Calls It Strategy",
        "A Win for {o}, and Someone Will Say It Was the Plan",
        "{o} Gets the Win; the Roster Gets the Credit",
        "{t}: A Win, and the Owner Has Already Taken the Credit",
        "{o} Gets Past {opp}, and Takes Most of the Credit",
    ],
    "L": [
        "{o} Loses to {opp}, and the Lineup Page Has Questions",
        "{o} Falls {mine}-{theirs}; the Owner Is the Lead Suspect",
        "{o}'s {wl}: A Loss, Self-Authored",
        "Beat Report: {o} Loses to {opp}, and It Is on {o}",
        "{opp} Beats {o} {theirs}-{mine}, and the Blame Has a Name",
        "{o} Drops {wl} and Looks for Someone Else to Blame",
        "Another Loss to Explain for {o}",
        "{o} Falls to {opp}; the Owner Owns It",
        "{t}: {o} Loses, and the Lineup Page Is the Lead Suspect",
    ],
    "T": [
        "{o} and {opp} Tie at {mine}, and the Owner Fails to Win Even That",
        "A Tie for {o}, a Small Achievement in Mediocrity",
    ],
    "bench": {"W": ["{o} Wins While Leaving {left} on the Bench", "{o} Wins, and {left} Sat Unused on the Bench"],
              "L": ["{o} Loses With {left} on the Bench", "{o} Leaves {left} on the Bench and Loses Anyway"]},
    "bench_gt": {"L": ["{o} Loses by {margin} With {left} on the Bench", "{left} on the Bench, a {margin}-Point Loss, and One Obvious Suspect"]},
    "dud": {"A": ["{o} Starts {dud}, Gets {dpts}", "{dud} Scores {dpts}, and {o} Started the Player Anyway", "{dpts} From {dud}: A Start-Sit Disaster by {o}"]},
    "streak": {"W": ["{o} Has Won {k} Straight, and Has Opinions About It"], "L": ["{o} Has Lost {k} Straight, and the Beat Is Counting"]},
    "shotgun": {"A": ["{o} Earns {nsg}, and the Lineup Was the Culprit", "{nsg} for {o}: The Lineup Page Strikes Again", "{o} Owes {nsg} and Has Only the Lineup to Blame"]},
    "trade_pending": {"A": ["{o} Makes a Deal With {partner}; the Beat Has Concerns", "{o} Trades With {partner}, and the Beat Reserves Judgment", "A Trade With {partner}, and {o} Has a Feeling About It"]},
    "luckywin": {"W": ["{o} Wins With the League's {wr_ord}-Best Score and Calls It Management", "A {wr_ord}-Best Score and a Win: {o} Thanks the Schedule"]},
    "unlucky": {"L": ["{o} Scores {mine}, the League's {wr_ord}-Best, and Loses Anyway", "A {wr_ord}-Best Score Is Not Enough for {o}"]},
    "lowscore": {"L": ["{o} Posts the League's Lowest Score of {wl}", "Nobody Scored Less Than {o} in {wl}"]},
    "highscore": {"W": ["{o} Posts the League's High Score and Credits the Owner", "High Score of the Week Goes to {o}; the Credit Goes to the Wrong Place"]},
    "blow_w": {"W": ["{o} Wins by {margin}, and the Owner Has Alerted the Press", "{o} Rolls to a {margin}-Point Win, Owner Barely Involved"]},
    "blow_l": {"L": ["{o} Loses by {margin}; There Is Nothing to Discuss but the Owner", "A {margin}-Point Loss for {o}, and the Evidence Is Overwhelming"]},
    "close_w": {"W": ["{o} Wins by {margin}, a Clerical Error in the Owner's Favor", "{o} Edges {opp} by {margin} and Calls It Skill"]},
    "close_l": {"L": ["{o} Loses by {margin}, and the Bench Was Right There", "{margin} Points Short: {o} Loses a Close One"]},
}
