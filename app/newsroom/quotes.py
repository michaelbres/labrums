"""Owner quotes, keyed by SITUATION (never by role). Every line needs only the concrete facts named in
its placeholders; a line whose placeholders are missing is never used.

Markers at the start of a line: [multi] only when the owner owes 2+ shotguns, [single] only for exactly 1,
[commish] only when the speaker is the configured commissioner.
No kicker/defense jokes: this league has neither (and quotes must hold in any roster setup).
"""
from __future__ import annotations

import random
import re

from .util import placeholders

BANK: dict[str, list[str]] = {
    "won_big": [
        "{m} points. I'd say I feel bad for {opp}, but I checked and I don't.",
        "It was over after the first Sunday window. {opp} can have the highlights. I'll keep the {wp}.",
        "Scoring {wp} in Week {wk} is a lifestyle, {opp}. Come back when you've got one.",
        "I looked at the final twice, because {m} points seemed like too many even for me.",
        "Somebody tell {opp} it's only fantasy. Tell {opp} after I screenshot this.",
        "Great win, great team, great margin: {m}. I'll be at the bar if anyone wants the receipts.",
        "{opp} played the {lp} game {opp} was always going to play, and I played the {wp} game I was always going to play.",
    ],
    "won_close": [
        "{m} points. That's a win, that's a win, and nobody gets to ask how.",
        "I'll be honest: I stopped watching and started praying, and the prayer cleared by {m}.",
        "Beat {opp} by {m} and I'm not going to pretend I earned all of it.",
        "Close games are won by sound lineup management. Privately I'd call it a coin flip I happened to call right.",
        "Put {m} points in the bank and don't ask what happened in the fourth quarter.",
        "If you'd told me on Thursday that I'd win by {m}, I'd have asked what I was doing wrong.",
        "{opp} had me sweating through my shirt. The scoreboard says {m}, and the scoreboard is the only thing I answer to.",
    ],
    "lost_big": [
        "{m} points. I'd like to see the tape, but I'd like even more not to.",
        "{opp} was great and I was absent, which is a hard combination to beat.",
        "I'm not going to make excuses. I'll make a couple of observations about my quarterback and then I'm done.",
        "Down {m}. I'm calling it a data point. Every season has one.",
        "I'm putting Week {wk} in a drawer, and I'm putting the drawer in a lake.",
        "Nobody gets hurt by a {m}-point loss. Except me. Mostly me.",
        "Tell {opp} congratulations. Tell {opp} it won't happen again. Don't tell {opp} I said either.",
    ],
    "lost_close": [
        "{m} points. That's one good tight end away from a different story.",
        "I lost by {m}, which means I did most things right and one thing wrong, and I'd like to know which.",
        "I'll be thinking about {m} points at my own funeral.",
        "Fantasy is cruel. {m} points. I've done the math four times and it comes out the same.",
        "I'd call it a moral victory, but I don't think {opp} would let me.",
        "Down {m} at the end, and I'll be replaying every lineup decision until Thursday.",
        "A game like that doesn't need a quote. It needs a hug.",
    ],
    "tied": [
        "We both scored {pts}. I didn't know the league could do this, and I'm not sure it should.",
        "I don't know what a tie is for. I do know I'm not doing it again.",
        "Nobody won. That's not a result, that's a hostage situation.",
        "Half a win each. {opp} gets the half I deserved.",
        "I've been refreshing the stat corrections since Tuesday and neither of us has moved.",
        "{pts} apiece is the most boring chaos I've ever been part of.",
        "Call it a draw with {opp}, call it a push, call it anything. I call it unfinished business.",
    ],
    "trade_gave_more": [
        "I sent out {gave} and got {got}. It's a long season, and I'm in it for the long part.",
        "Early returns aren't returns. Call me when {got} has played a full season.",
        "I'll take {got}. I'm not apologizing for it.",
        "Everyone's looking at what {opp} got. I'm looking at what I got: {got}. Different list.",
        "Maybe it's not fair on the scoreboard this month, but I never sold on a month.",
        "I'm sorry I'm not sorry about {got}. Check back when it matters.",
        "Dynasty is a marathon and I'm at the water station, enjoying {got}.",
    ],
    "trade_got_more": [
        "I'd like to thank {opp} for {got}, which is already paying me back.",
        "I'd do that one again tomorrow. {got} has been the best part of my roster.",
        "I don't want to say {opp} got fleeced. I'll let the box scores say it.",
        "When {opp} said yes to my offer I checked the number twice. Then I took {got} and ran.",
        "Everyone said I overpaid. {got} says otherwise.",
        "{opp} will tell you it's a long game. It is. I'm also winning the short part.",
        "This one's going in the scrapbook, under 'Things I Got Right.'",
    ],
    "trade_pending": [
        "We'll know who won this when the picks turn into players, and not before.",
        "I like {got}. {opp} likes {gave}. Somebody's going to be wrong and we'll both find out slowly.",
        "Ask me again in a month. That's the honest answer and the only answer.",
        "Both of us got what we wanted, and one of us is wrong about that.",
        "No comment on who won. I'll have a comment once the games are played.",
        "{opp} and I talked it through and it's still too early to say. That's what I'm telling people.",
        "I got {got}. {opp} got {gave}. That's all I have until the box scores come in.",
    ],
    "waiver_win": [
        "{player} was sitting there. I just had the nerve.",
        "Everybody's going to say they saw {player} coming. Nobody saw {player} coming. I saw {player} coming.",
        "I put in the claim for {player} at 3 a.m. and woke up a genius.",
        "{player} is a {pos} on my roster now, and my roster has never been happier.",
        "I don't chase. I stalk. That was {player}.",
        "Some people read scouting reports. I read the free-agent list in bed. {player} is the proof.",
        "If {player} works out, I'm a visionary. If not, I was never here.",
        "{bid} for {player} and I'd pay it twice.",
        "A {bid} bid on {player}. I'd call that a bargain, but I'm not the one doing the pricing.",
    ],
    "shotgun_owed": [
        "[single] One shotgun, one beer, no complaints. The rule's the rule.",
        "[single] A single shotgun. I've done worse before noon.",
        "[single] I'll pay my {sgn} with dignity. With a beer, but with dignity.",
        "[single] Put it on the ledger: {sgn}. I'll honor it before the next waiver run.",
        "[single] {player} is the reason and {player} knows it.",
        "[single] It's only one. I've made bigger mistakes at tailgates.",
        "[multi] {sgn} in one week. That's not a lineup, that's a drinking game with a lineup attached.",
        "[multi] {sgn}. I'd like to say I learned something. I'd like to say a lot of things.",
        "[multi] {sgn} owed and I'll pay every one. The only question is the order.",
        "[multi] Somebody tell my liver. {sgn}.",
        "[multi] I'm counting {sgn} and I'm not driving anywhere.",
        "[multi] {sgn}. My only regret is the rule, and the rule has no regrets about me.",
    ],
    "rule_owed": [
        "{rule}. That's a sentence I never wanted attached to my name.",
        "I scored less than {target}. I'd like that struck from the record, and also from my memory.",
        "The rule is the rule, and now I'm in the rule.",
        "{sgn} for '{rule}.' If I'd known it was coming, I'd have scored more.",
        "Fine. Pour it. I knew what I signed up for when I agreed to '{rule}.'",
        "I read the rule. I understood the rule. I did the thing the rule says not to do.",
        "[commish] I wrote this rule with a straight face and I'm paying it with a straight face.",
        "[commish] I made the rule. I regret the rule. I'm paying the rule.",
    ],
    "bubble": [
        "{odds}. I'm not sure what that number means, but it's less than 100 and more than zero, which is where I like to live.",
        "I can see the playoffs from here, but I've been able to see the playoffs from a lot of places.",
        "At {rec}, I'm on the bubble, and I've never been so comfortable being uncomfortable.",
        "Every week is a playoff game now. Every week was supposed to be a playoff game.",
        "{odds} is a real number. You can have the odds. I'll take the rest.",
        "I've done the tiebreaker math four times and I'm stopping before it tells me something.",
        "On the bubble means one win from comfortable and one loss from a vacation.",
    ],
    "clinched": [
        "At {rec}, I'm in. I'd like to thank the schedule and, in a smaller way, myself.",
        "Clinched. That's a word I plan to say out loud in public.",
        "I'm in the playoffs and I didn't need anyone's help. I needed a lot of people's help, but I didn't ask.",
        "{rec} gets you a ticket. What you do with the ticket is a question for the playoffs.",
        "Pour one out for everybody still doing math.",
        "I'm not going to say I knew. I'm going to say I'm in, and you're welcome to the rest.",
        "That's the work. Now it's the fun part.",
    ],
    "eliminated": [
        "At {rec}, I'm officially a spectator. I've got excellent seats.",
        "I'll be rooting for chaos from now on. It's the only team left that I own.",
        "Eliminated is just another word for focused on next year.",
        "I'd like to thank everybody who helped me get to {rec}. You know who you are. You were my own lineup.",
        "I'm going to be the most dangerous spoiler this league has ever seen, mostly by accident.",
        "Next year. I say that every year, and every year I mean it more specifically.",
        "The math says no. The math doesn't have to live with me.",
    ],
    "trash_h2h_lead": [
        "I'm {h2h} against {opp} this year. It's not a rivalry when one side keeps winning, it's a subscription.",
        "{h2h} on the season against {opp}, and I haven't even started trying.",
        "I've beaten {opp} this year and I plan on doing it again, so whatever {opp} is working on, work on it harder.",
        "Look at the head-to-head: {h2h}. Look at me. Look at the head-to-head.",
        "{opp} has seen my lineup before. {opp} lost to my lineup before. It's {h2h} for a reason.",
        "I don't need a pep talk against {opp}. I need a scoreboard, and the scoreboard says {h2h}.",
        "{h2h}. That's not trash talk, that's a citation.",
    ],
    "trash_h2h_trail": [
        "I'm {h2h} against {opp} this season, which is why this one is personal.",
        "{opp} has me {h2h} this year. A person can only be owned for so long.",
        "I've lost to {opp} already and I'm not doing it twice. That's not a prediction, it's a rule I just made.",
        "Sure, {opp} is ahead of me, {h2h}. That's how the first half of a comeback story starts.",
        "{h2h}. I've got a lot of notes on how {opp} did it, and I'm going to use every one.",
        "{opp} thinks the {h2h} means something. It means I've seen the plays.",
        "Revenge is a dish best served in the middle of a regular season, against {opp}, for no extra points.",
    ],
    "trash_standings": [
        "I'm {rank} in the standings and {opp} is {opp_rank}. I didn't make that up and I couldn't if I tried.",
        "{rank} versus {opp_rank}. That's not a matchup, that's a field trip for {opp}.",
        "Somebody has to be {rank}, and it's been me. {opp} can have {opp_rank} and the view.",
        "The table doesn't lie. {rank} and {opp_rank}. I'd be worried too.",
        "Being {rank} is a lot of work, and I'm not about to lose it to a team sitting {opp_rank}.",
        "I'd tell {opp} to enjoy {opp_rank}, but I want {opp} to have some fun this week and that's it.",
        "{opp} is {opp_rank}. I'm {rank}. We can skip the rest of this call.",
    ],
    "trash_underdog": [
        "Nobody's picking me this week. That's fine. I play better when everyone's wrong.",
        "{opp} is the favorite on paper. I'd like to remind everybody that paper doesn't score points.",
        "I'm the underdog against {opp} and I've never felt more dangerous.",
        "I've got nothing to lose against {opp} except this game, and honestly I've lost things before.",
        "Say what you want about my team. It's a team, and it's going to play {opp}.",
        "If {opp} wants to talk about favorites, I'd like to talk about Sunday.",
        "I'm going to play the spoiler, the villain, and the fan who refuses to leave early.",
    ],
    "deny_after_trash": [
        "{opp} can say whatever {opp} wants. I'll be busy winning.",
        "I heard what {opp} said. I wasn't listening, but I heard.",
        "That's {opp}'s opinion, and {opp}'s opinion has been wrong before.",
        "No comment on {opp}. I'm saying that as a favor.",
        "I'd answer {opp}, but I try not to reward noise.",
        "I'd love to hear {opp} say that to my face on Sunday, which is when it will matter.",
        "Respectfully, {opp} should check the schedule and then check the mirror.",
    ],
}

_MARK = re.compile(r"^\[(multi|single|commish)\]\s*")


def parse(line: str) -> tuple[str | None, str]:
    m = _MARK.match(line)
    return (m.group(1), line[m.end():]) if m else (None, line)


def candidates(situation: str, facts: dict[str, str], *, multi: bool = False, commish: bool = False) -> list[tuple[int, str]]:
    out = []
    for i, raw in enumerate(BANK[situation]):
        tag, text = parse(raw)
        if tag == "multi" and not multi:
            continue
        if tag == "single" and multi:
            continue
        if tag == "commish" and not commish:
            continue
        if any(not facts.get(k) for k in placeholders(text)):
            continue
        out.append((i, text))
    return out


def pick(situation: str, facts: dict[str, str], rng: random.Random, used: set, *,
         multi: bool = False, commish: bool = False) -> str | None:
    cands = candidates(situation, facts, multi=multi, commish=commish)
    fresh = [c for c in cands if (situation, c[0]) not in used]
    pool = fresh or cands
    if not pool:
        return None
    i, text = pool[rng.randrange(len(pool))]
    used.add((situation, i))
    return re.sub(r"\{(\w+)\}", lambda m: str(facts[m.group(1)]), text)
