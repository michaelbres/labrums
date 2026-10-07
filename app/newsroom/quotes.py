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
        "Put {wp} on the board and left the rest to {opp}. {opp} did not take the hint.",
        "I'm not saying {opp} gave up, but I didn't see a fight. {m} points is a statement.",
        "A {m}-point win is a lot of points. I'm choosing to enjoy every one of them.",
        "Week {wk} was my week, and {opp} just happened to be in it.",
        "If you need me, I'll be refreshing my phone and not feeling sorry for {opp}.",
        "I've seen better teams lose by less than {opp} did, so take that however you like.",
        "Scored {wp}, took the week, and I'm still deciding whether to be humble about it.",
        "{opp} brought a plan. I brought {wp} points. Guess which one traveled farther.",
        "The way {opp} lost by {m} is the way you lose when the other side is having fun.",
        "{m} points of daylight. I'll bring sunglasses to the next group chat.",
        "Nobody check the margin, {m}. Actually, everybody check the margin, {m}.",
        "{m} points is not a margin, it's a message, and {opp} got it.",
        "I'd say it was close, but I don't lie in public. {m} points.",
        "{wp} points. I'll let {opp} do the math on that one.",
        "{opp} had a plan, I had a lineup, and the lineup won by {m}.",
        "Week {wk} felt like a victory lap with the lights on. {m} points.",
        "I don't want to gloat about beating {opp} by {m}, but I've cleared my afternoon for it.",
    ],
    "won_close": [
        "{m} points. That's a win, that's a win, and nobody gets to ask how.",
        "I'll be honest: I stopped watching and started praying, and the prayer cleared by {m}.",
        "Beat {opp} by {m} and I'm not going to pretend I earned all of it.",
        "Close games are won by sound lineup management. Privately I'd call it a coin flip I happened to call right.",
        "Put {m} points in the bank and don't ask what happened in the fourth quarter.",
        "If you'd told me on Thursday that I'd win by {m}, I'd have asked what I was doing wrong.",
        "{opp} had me sweating through my shirt. The scoreboard says {m}, and the scoreboard is the only thing I answer to.",
        "I won by {m} and I'm calling it a masterclass, because the alternative is calling it luck.",
        "{m} points. I've had longer commutes with more margin for error.",
        "That one was closer than I'd like and exactly as close as I needed.",
        "I'd tell you it was strategy. It was {m} points of pure panic.",
        "{opp} made me earn it. I'll give {opp} that much, and nothing else.",
        "I want everyone to know I never doubted it, and I want everyone to forget the middle of the game.",
        "Won by {m} and aged six years. Worth it.",
        "Close wins count the same as big wins. I looked it up in my head.",
        "{opp} was one starter away from a different week. I was lucky it wasn't a different week.",
        "If this keeps up I'll need a cardiologist and a better lineup, in that order.",
        "I'll accept the {m}-point win and I'll send {opp} a thank-you note, unsigned.",
    ],
    "lost_big": [
        "{m} points. I'd like to see the tape, but I'd like even more not to.",
        "{opp} was great and I was absent, which is a hard combination to beat.",
        "I'm not going to make excuses. I'll make a couple of observations about my quarterback and then I'm done.",
        "Down {m} points. I'm calling it a data point. Every season has one.",
        "I'm putting Week {wk} in a drawer, and I'm putting the drawer in a lake.",
        "Nobody gets hurt by a {m}-point loss. Except me. Mostly me.",
        "Tell {opp} congratulations. Tell {opp} it won't happen again. Don't tell {opp} I said either.",
        "I'd call it an off week, but I'd need a few more of the good kind to compare.",
        "{m} points is a lot of points to lose by. I'm going to have to sit with that.",
        "{opp} played well. I played the whole game with my coat on.",
        "Give {opp} credit. Then give me my {m} points back, if anybody finds them.",
        "Some weeks the lineup works and some weeks it files a grievance. Week {wk} was the latter.",
        "I'd like a recount, a referee, and a new quarterback, in that order.",
        "That was a masterclass. {opp} gave it and I took notes, which I am now burning.",
        "{m} points. I'm not mad, I'm fascinated.",
        "I'll let the lineup speak for itself. It said {m} points' worth, none of it good.",
        "Week {wk} will be remembered. I'd just prefer it weren't.",
        "I'm going to blame the schedule maker, the weather, and the group chat, in that order.",
    ],
    "lost_close": [
        "{m} points. That's one good tight end away from a different story.",
        "I lost by {m}, which means I did most things right and one thing wrong, and I'd like to know which.",
        "I'll be thinking about {m} points at my own funeral.",
        "Fantasy is cruel. {m} points. I've done the math four times and it comes out the same.",
        "I'd call it a moral victory, but I don't think {opp} would let me.",
        "Down {m} at the end, and I'll be replaying every lineup decision until Thursday.",
        "A game like that doesn't need a quote. It needs a hug.",
        "{m} points. I can almost feel the ones I left on the bench.",
        "I lost by {m}. Somewhere, a player I benched is feeling very good about it.",
        "A loss by {m} is worse than a big loss because I have to think about it.",
        "I'll take the moral victory over {opp}. It's the only one on offer.",
        "Down by {m} and still sure I outplayed {opp}. The scoreboard disagrees.",
        "{m} points. I've lost bets by more and slept better.",
        "You could fit my regret in a {m}-point gap and still have room for the bench.",
        "I'm going to be fine by Thursday. That's my official statement on {opp}.",
        "It came down to {m}. It always comes down to something. This time it came down to me.",
        "I lost to {opp} by {m} and I'd like to speak to whoever drew up the schedule.",
        "Close games build character. I'm fully built at this point.",
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
        "It's early, and {got} will have a say before this is over.",
        "I'm not worried about the numbers. {got} is a long-term piece, and so am I.",
        "Judge me in December. {got} hasn't peaked, and neither have I.",
        "I'd do the trade again, and I'd tell {opp} to enjoy {gave} while it lasts.",
        "Nobody wins a trade in the first few weeks. I'll wait for the other kind of week.",
        "Sure, {opp} is ahead for now. {got} didn't ask to be graded this early.",
        "I can read a scoreboard. I can also read a calendar, and the calendar says there's a lot of season left.",
    ],
    "trade_got_more": [
        "I'd like to thank {opp} for {got}, which is already paying me back.",
        "I'd do that one again tomorrow. {got} has been the best part of my roster.",
        "I don't want to say {opp} got fleeced. I'll let the box scores say it.",
        "When {opp} said yes to my offer I checked the number twice. Then I took {got} and ran.",
        "Everyone said I overpaid. {got} says otherwise.",
        "{opp} will tell you it's a long game. It is. I'm also winning the short part.",
        "This one's going in the scrapbook, in the section called Things I Got Right.",
        "{got} for {gave} looks better every week, and I'm not going to pretend I'm surprised.",
        "{opp} sent me {got} and I sent a thank-you note, which is only fair.",
        "I'd say I'm humble about it, but {got} has been doing the talking.",
        "People asked what I was thinking. I was thinking {got}.",
        "The box scores don't care about anybody's feelings, {opp}'s included.",
        "{got} is paying off, and I'm collecting.",
        "I made the offer, {opp} said yes, and I've been happy ever since.",
    ],
    "trade_pending": [
        "We'll know who won this when the picks turn into players, and not before.",
        "I like {got}. {opp} likes {gave}. Somebody's going to be wrong and we'll both find out slowly.",
        "Ask me again in a month. That's the honest answer and the only answer.",
        "Both of us got what we wanted, and one of us is wrong about that.",
        "No comment on who won. I'll have a comment once the games are played.",
        "{opp} and I talked it through and it's still too early to say. That's what I'm telling people.",
        "I got {got}. {opp} got {gave}. That's all I have until the box scores come in.",
        "It's too early to say, and anyone who says otherwise is selling something.",
        "I got {got}. {opp} got {gave}. Ask me again when there's a box score to argue about.",
        "Nobody wins a trade in the first week. That's why I'm still talking.",
        "We shook hands, and the results are going to take a few Sundays.",
        "I like {got}. {opp} likes {gave}. One of us will look smarter later.",
        "Let's give it a few weeks before anybody writes a victory speech.",
        "The only thing I know for sure is that I got {got}.",
        "No verdict from me. The scoreboard hasn't ruled, and neither will I.",
    ],
    # Waiver quotes are keyed by how the claim has actually gone: 15+ points since the claim brags, 5 to 15 shrugs,
    # under 5 (or negative) defends, and before any game has been played it is "too early".
    "waiver_brag": [
        "{player} was sitting there. I just had the nerve.",
        "I put in the claim for {player} at 3 a.m. and woke up a genius.",
        "{spts} from {player} since the claim. I'd call it a bargain, but I don't want the league bidding against me next week.",
        "Everybody's going to say they saw {player} coming. I actually did.",
        "{player} is a {pos} on my roster now, and with {spts} in the bank my roster has never been happier.",
        "I don't chase. I stalk. That was {player}, and the box scores agree.",
        "Some people read scouting reports. I read the free-agent list in bed. {player} is the proof.",
        "{bid} for {player} and I'd pay it twice. {spts} says I should.",
        "A {bid} bid on {player} looked bold on Tuesday. {spts} later it looks like a bargain.",
        "{player} has {spts} since the claim. I'd tell you I planned it, and for once that's almost true.",
        "I'd like to thank the waiver wire, the 3 a.m. alarm, and {player}, in that order.",
        "Somebody had to claim {player}. The fact that it was me, with {spts} to show for it, is just how the system works.",
        "{spts} from a pickup is a good week for anyone. {player} is a great week for me.",
        "I scouted {player} for exactly as long as it took to click the button, and {spts} says that was long enough.",
    ],
    "waiver_neutral": [
        "{player} is doing what a {pos} is supposed to do, and I'm not going to oversell it.",
        "{spts} from {player} so far. Not a headline, but not a mistake either.",
        "I'd call {player} a solid pickup and leave the adjectives to somebody else.",
        "Nobody writes songs about {player}, but the claim is paying its own way.",
        "{player} is fine. Fine is underrated.",
        "I wanted a {pos} and I got a {pos}. I'm calling that a win on a technicality.",
        "It's a depth move. {player} has given me {spts}, which is about what depth is for.",
        "Ask me when {player} has a big week. Until then it's a steady claim.",
        "{bid} for {player} is a fair price for {spts}, no more and no less.",
        "I'll take {spts} and a spot on my roster. That's the whole story of {player}.",
        "{player} hasn't changed my season. He hasn't hurt it either, and I'll sign for that.",
        "Some claims are home runs and some are singles. {player} is a single, and singles score runs.",
        "Not every pickup has to be a story. {player} is just a useful {pos}.",
        "{spts} out of {player} is about what I paid for, which makes it the most honest transaction I've made this year.",
    ],
    "waiver_miss": [
        "In my defense, the claim for {player} looked a lot better on Tuesday.",
        "I'm not saying the claim for {player} was a mistake. I'm saying I'd like to see the tape.",
        "{spts} from {player}. I'm told that's what the experts call a learning experience.",
        "If {player} turns it around, I'll take full credit. Until then, no comment.",
        "It was a swing, and swings miss. {player} is a {pos} who hasn't shown up yet.",
        "I'd defend the claim for {player}, but the box score is making it difficult.",
        "{bid} on {player} was my decision and I'll own it, quietly.",
        "Next time I'll let somebody else find the {pos}.",
        "{player} hasn't done much yet. I'm giving him time, and not much more than that.",
        "Some claims age like milk. {player} is still in the carton.",
        "I'd call {player} a work in progress, but that implies somebody is working.",
        "The data on {player} is early and unflattering, and I've decided to focus on the early part.",
        "Every waiver pickup is a bet, and {player} is the one that didn't pay. I'm on to the next one.",
        "I'm keeping {player} out of respect for the {spts}. Respect for the {spts} is not high.",
    ],
    "waiver_pending": [
        "It's too early to judge {player}. Check back after the games.",
        "I put in the claim for {player} and I'm not saying a word until he plays.",
        "Ask me in a week. {player} has to play a game before I can be right or wrong.",
        "{player} is a {pos} on my roster now. Whether that's good news is a question for Sunday.",
        "No verdict on {player} yet. I've learned not to give one early.",
        "The claim's in. The results aren't. That's all I've got on {player}.",
        "{bid} for {player} and the games haven't been played. I'll take a victory lap or an apology next week.",
        "I'm optimistic about {player}, which is what you say before the games are played.",
        "I don't have {player} numbers yet, only a feeling, and the feeling is cautiously good.",
        "Come back when {player} has a box score. Until then I'm just a person with a claim.",
    ],
    "shotgun_owed": [
        "[single] One shotgun, one beer, no complaints. The rule's the rule.",
        "[single] A single shotgun. I've done worse before noon.",
        "[single] I'll pay my {sgn} with dignity. With a beer, but with dignity.",
        "[single] Put it on the ledger: {sgn}. I'll honor it before the next waiver run.",
        "[single] {player} is the reason and {player} knows it.",
        "[single] It's only one. I've made bigger mistakes at tailgates.",
        "[multi] {sgn} owed. That's not a lineup, that's a drinking game with a lineup attached.",
        "[multi] {sgn}. I'd like to say I learned something. I'd like to say a lot of things.",
        "[multi] {sgn} owed and I'll pay every one. The only question is the order.",
        "[multi] Somebody tell my liver. {sgn}.",
        "[multi] I'm counting {sgn} and I'm not driving anywhere.",
        "[multi] {sgn}. My only regret is the rule, and the rule has no regrets about me.",
        "[single] One shotgun, and I know exactly which lineup decision earned it.",
        "[single] I'll take one shotgun and a long look at my bench.",
        "[single] One. I've had worse Mondays, but not many.",
        "[single] The rule says one, and the rule is correct, which is the annoying part.",
        "[single] {sgn}. I'll pay it before anyone asks twice.",
        "[single] One shotgun is a reminder, not a punishment. That's what I'm telling myself.",
        "[multi] {sgn}. I'd like to dispute it, but I don't have the stomach for it.",
        "[multi] I owe {sgn}, and I'd like it noted that I'm taking it well.",
        "[multi] {sgn} is a lot of beer for one lineup. It was also a lot of lineup.",
        "[multi] I'll be paying this one in installments: {sgn}, spread across the week.",
        "[multi] Put me down for {sgn}, and put the cooler next to me.",
        "[multi] {sgn} on the board. I'll be calling in sick to my own Sunday.",
    ],
    "rule_owed": [
        "{rule}. That's a sentence I never wanted attached to my name.",
        "I scored less than {target}. I'd like that struck from the record, and also from my memory.",
        "The rule is the rule, and now I'm in the rule.",
        "{sgn} for the {rule} rule. If I'd known it was coming, I'd have scored more.",
        "Fine. Pour it. I knew what I signed up for when I agreed to the {rule} rule.",
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
        "{rank} and {opp_rank}. I'm not saying it's over, but I'm not saying it isn't.",
        "The standings say {rank} versus {opp_rank}, and I take standings personally.",
        "{opp} can enjoy {opp_rank}. I'll be busy enjoying {rank}.",
        "I'm {rank}. {opp} is {opp_rank}. Everything else is commentary.",
        "{rank} to {opp_rank}: the table made the argument, and I'm just repeating it.",
        "Somebody's got to be {rank}, and I volunteer. {opp} can keep {opp_rank}.",
        "If the standings are right, and they usually are, {rank} beats {opp_rank}.",
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
    "trash_even": [
        "I'm not going to say much about {opp}. Sunday will do the talking.",
        "{opp} is a fine team. I'm planning to be a better one this week.",
        "No predictions on {opp}. Just a lineup and some hope.",
        "{opp} and I are both going to show up. Only one of us will be happy about it.",
        "I respect {opp}. I also plan to beat {opp}, and those two things can coexist.",
        "It's a coin flip on paper, and I like a coin flip.",
        "{opp} has a lineup. I have a lineup. Let's see whose shows up.",
        "I'm taking {opp} seriously, which is more than I can say for my own bench.",
        "Nothing to say about {opp} that Sunday won't say louder.",
        "I'm not making a prediction on {opp}. I'm making a lineup.",
        "{opp} is going to try. I'm going to try. That's the whole preview.",
        "It could go either way, which is why they play the games.",
        "I've got a good feeling about {opp}'s lineup, which is the nicest thing I'll say all week.",
    ],
    "deny_after_trash": [
        "{opp} can say whatever {opp} wants. I'll be busy winning.",
        "I heard what {opp} said. I wasn't listening, but I heard.",
        "That's {opp}'s opinion, and {opp}'s opinion has been wrong before.",
        "No comment on {opp}. I'm saying that as a favor.",
        "I'd answer {opp}, but I try not to reward noise.",
        "I'd love to hear {opp} say that to my face on Sunday, which is when it will matter.",
        "Respectfully, {opp} should check the schedule and then check the mirror.",
        "I'll answer {opp} on Sunday, in the only language {opp} respects.",
        "Funny, {opp} wasn't this chatty when the lineups were set.",
        "{opp} is entitled to an opinion. I'm entitled to the result.",
        "I heard {opp}. Then I heard the final score in my head, and it sounded better.",
        "Let {opp} talk. I've got a lineup to set.",
        "If {opp} wants a response, the box score will send one.",
        "I've read what {opp} said. I've also read my roster, and I feel fine.",
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


def _render(text: str, facts: dict[str, str]) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(facts[m.group(1)]), text)


def pick(situation: str, facts: dict[str, str], rng: random.Random, used: set, *,
         multi: bool = False, commish: bool = False, counts=None, scorer=None) -> str | None:
    """A quote for the situation. `used` keeps one article from repeating a line; `counts` (a Counter shared
    by a whole build) and `scorer` (how many times a rendering's sentences were already written this build)
    steer every article toward lines that have been used least so far."""
    cands = candidates(situation, facts, multi=multi, commish=commish)
    fresh = [c for c in cands if (situation, c[0]) not in used]
    pool = fresh or cands
    if not pool:
        return None
    if counts is not None or scorer is not None:
        def key(c):
            return (scorer(_render(c[1], facts)) if scorer else 0, counts[(situation, c[0])] if counts is not None else 0)
        low = min(key(c) for c in pool)
        pool = [c for c in pool if key(c) == low]
    i, text = pool[rng.randrange(len(pool))]
    used.add((situation, i))
    if counts is not None:
        counts[(situation, i)] += 1
    return _render(text, facts)
