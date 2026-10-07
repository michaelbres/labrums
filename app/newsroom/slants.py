"""Slanted template variants for narratives (see config.yaml `narratives`), one register per style family.

SLANTS[family][slot][slant] -> templates. A slanted variant frames the SAME facts differently (a hater credits the star
and not the owner, a homer reads a loss as bad luck): it may use only the placeholders listed in
families.SLANT_SLOTS, it carries no digits of its own, and it never states a fact the placeholders do not hold. The
engine picks `neg` / `pos` / `neutral` by the reporter's stance; the neutral families in styles/ are untouched.

Units: spts, gpts, wbench, wdpts, lspts and gpts carry their unit ("34.5 points"); wp, lp, m, thin, wluck, lluck,
labove are bare numbers; sshare is a percentage; over_half is the clause "more than the rest of the roster combined".
x.theme's {theme} is the owner-written thesis (no final period); x.hype's {ctx} is a verb phrase built from real facts.
"""
from __future__ import annotations

SLANTS: dict[str, dict[str, dict[str, list[str]]]] = {}

SLANTS["wire"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) scored {spts} for {w}. The credit belongs to the player, not to the decisions around him.",
            "{w} won with {spts} from {star} ({spos}); the box score does not credit the manager.",
            "{star} ({spos}) scored {spts}, {over_half}. The win was one player's work.",
        ],
        "pos": [
            "{star} ({spos}) scored {spts} for {w}, who had started him.",
            "{w}'s decision to start {star} ({spos}) returned {spts}.",
            "{w} received {spts} from {star} ({spos}), a return that supports the decision to start him.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} started {gname} ({gpos}) and received {gpts}. The decision is recorded without comment and without credit.",
            "{gname} ({gpos}) scored {gpts} in a slot {l} chose to fill with him.",
        ],
        "pos": [
            "{gname} ({gpos}) scored {gpts} for {l}, one slot that does not describe the rest of the roster.",
            "One starting slot fell short: {gname} ({gpos}) scored {gpts} for {l}.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} is {w_rec} ({w_rank}) and {l} is {l_rec} ({l_rank}); the records are listed here without endorsement.",
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). A record is not a recommendation.",
        ],
        "pos": [
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). Neither record is the final word.",
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}). Records are only part of the picture for either roster.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won, but a win is not the same as a good week, and the result should not be read as one.",
            "{w} beat {l}. How the win was achieved is a separate question, and the answer is not flattering.",
            "{w} won while leaving {wbench} on the bench, a margin of error a contender does not usually carry.",
            "{w} won while starting {wdud} ({wdpos}), who scored {wdpts}. The result got past the lineup; the lineup did not earn it.",
            "{w} ({w_rec}) is {wluck} wins ahead of what the all-play record says the team should have. The record is generous.",
            "{w} won by {thin} points, a margin that can go the other way on any other week.",
        ],
        "pos": [
            "{l} lost, but the result says less about {l} than the score does.",
            "{l} lost to {w}. The loss should not be read as a verdict on the roster.",
            "{l} lost, but {lstar} ({lspos}) did his part with {lspts}.",
            "{l} scored {lp}, above the league average of {labove} for the week, and still lost. That is bad luck, not bad rostering.",
            "{l} ({l_rec}) is {lluck} wins behind what the all-play record says the team has earned. The record is unkind.",
            "{l} lost by {thin} points, a margin that falls either way and fell the wrong way here.",
            "{l} lost with {gname} ({gpos}) scoring {gpts} in a starting slot. It is hard to win that way.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed.",
            "{n} insisted: “{qp}”",
            "“{qc}” {n} maintained, without further comment.",
        ],
        "pos": [
            "“{qc}” {n} said with confidence.",
            "{n} said plainly: “{qp}”",
            "“{qc}” {n} said, standing by the remark.",
        ],
    },
    "x.theme": {
        "neg": [
            "The position of this desk is unchanged: {theme}.",
            "The ledger has been consistent on one point: {theme}.",
            "For the record, as before: {theme}.",
        ],
        "pos": [
            "The position of this desk is unchanged: {theme}.",
            "The ledger has been consistent on one point, and states it again: {theme}.",
            "For the record, as before, and with confidence: {theme}.",
        ],
        "neutral": [
            "The qualification of this desk is unchanged: {theme}.",
            "The result stands. So does the caveat: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, whom {rep} has been recommending since August, {ctx}.",
            "{rep} has backed {player} since August. {player} {ctx}.",
            "On the record, {rep}'s pick {player} {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, to limited applause in {wl}", "{w} gets the win over {l} in {wl}; the questions remain"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the case for {w} grows in {wl}", "{w} earns the win over {l} in {wl}, as backers expected"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}, and the doubts return", "{l} falls to {w} in {wl}; the criticism stands"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}; the case for {l} stands", "{l} falls to {w} in {wl}, a result that flatters nobody and indicts nobody"],
    },
    "h.sl.any": {
        "neg": ["Questions remain about {n} in {wl}", "{n} makes the record in {wl}, to little acclaim", "Doubts persist around {n} as {wl} closes"],
        "pos": ["Case for {n} holds in {wl}", "{n} makes the record in {wl}, to deserved notice", "Backers of {n} note a solid {wl}"],
    },
}

SLANTS["hype"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) put up {spts} for {w}, and let's be honest: THAT is who won this game, not the guy who set the lineup!",
            "Give {star} ({spos}) ALL the credit for {spts}! {w} just happened to be the one holding the roster!",
            "{star} ({spos}) scored {spts}, {over_half}! That is ONE player's win, folks!",
        ],
        "pos": [
            "{star} ({spos}) put up {spts} for {w}, and {w} started him! THAT'S how you build a winner!",
            "{w} trusted {star} ({spos}) and got {spts} back! Respect the call!",
            "{spts} from {star} ({spos}), and {w} had the guts to start him! Stand up and clap!",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} started {gname} ({gpos}) and got {gpts}! POINTS! IN THE STARTING SLOT! You cannot make this up!",
            "{gname} ({gpos}) gave {l} {gpts}, and {l} PUT HIM IN THE LINEUP! Unbelievable!",
        ],
        "pos": [
            "One slot let {l} down: {gname} ({gpos}), {gpts}! That is on the SLOT, not on the team!",
            "Don't blame {l}! Blame {gname} ({gpos}) and {gpts}! One bad spot doesn't define a roster!",
        ],
    },
    "g.record": {
        "neg": [
            "{w} is {w_rec} ({w_rank}), {l} is {l_rec} ({l_rank}), and I'm not buying EITHER number!",
            "The table says {w} {w_rec} ({w_rank}) and {l} {l_rec} ({l_rank}). Records LIE, people!",
        ],
        "pos": [
            "{w} is {w_rec} ({w_rank}), {l} is {l_rec} ({l_rank}), and the best is STILL ahead!",
            "The table says {w} {w_rec} ({w_rank}) and {l} {l_rec} ({l_rank}). Believe in this league!",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won! But a win is NOT a good week, folks, and everybody knows it!",
            "{w} beat {l}, sure! But HOW? Let's not pretend that was pretty!",
            "{w} won while leaving {wbench} on the bench! On the BENCH! A contender does not do that!",
            "{w} won while starting {wdud} ({wdpos}), who scored {wdpts}! The win got past that lineup! Barely deserved!",
            "{w} ({w_rec}) is {wluck} wins ahead of what the all-play record says! LUCKY! There, I said it!",
            "{w} won by just {thin} points! That goes the OTHER way on any other Sunday!",
        ],
        "pos": [
            "{l} lost! But that score does NOT tell the story, folks!",
            "{l} lost to {w}, and I refuse to call it a verdict on {l}!",
            "{l} lost, but {lstar} ({lspos}) showed up with {lspts}! Respect the effort!",
            "{l} scored {lp}, ABOVE the {labove} league average, and STILL lost! That's bad luck, not bad rostering!",
            "{l} ({l_rec}) is {lluck} wins behind what the all-play record says! UNLUCKY! Somebody give {l} a break!",
            "{l} lost by just {thin} points! A coin flip that landed the wrong way!",
            "{l} lost with {gname} ({gpos}) giving {gpts} in a starting slot! Nobody wins like that!",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} CLAIMED!",
            "{n} INSISTED: “{qp}”",
            "“{qc}” {n} said, with a straight face!",
        ],
        "pos": [
            "“{qc}” {n} said, and I believe every word!",
            "{n} said it LOUD and proud: “{qp}”",
            "“{qc}” {n} said with total conviction!",
        ],
    },
    "x.theme": {
        "neg": [
            "And I will say it again, LOUDER: {theme}!",
            "Write it down, folks, because I keep saying it: {theme}!",
            "My position has not changed one bit: {theme}!",
        ],
        "pos": [
            "And I will say it again, LOUDER: {theme}!",
            "Write it down, folks, because I keep saying it: {theme}! I believe in it!",
            "My position has not changed one bit: {theme}!",
        ],
        "neutral": [
            "Great, fine, but here's my catch: {theme}!",
            "Yes, but, folks: {theme}!",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, who {rep} has been telling you about since August, {ctx}!",
            "{rep} has been on {player} since August, and {player} {ctx}! Remember the name!",
            "You heard it from {rep} first, and he has not stopped: {player} {ctx}!",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, but nobody is clapping in {wl}!", "{w} wins in {wl}, and the doubts are still LOUD!"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the believers were RIGHT in {wl}!", "{w} wins in {wl}, and the hype is REAL!"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}, and the doubts get LOUDER!", "{l} falls in {wl}, and nobody is shocked!"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}, but don't you DARE panic!", "{l} falls in {wl}, but the believers are not going anywhere!"],
    },
    "h.sl.any": {
        "neg": ["More questions than answers for {n} in {wl}!", "{n} is back in the headlines in {wl}, and nobody's thrilled!", "Doubts are LOUD around {n} in {wl}!"],
        "pos": ["{n} is making the case in {wl}!", "Believe in {n}! {wl} says so!", "{n} keeps the believers happy in {wl}!"],
    },
}

SLANTS["nerd"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) posted {spts} for {w} (a single-game outlier, which regresses), so credit the variance before crediting the manager.",
            "{w} won with {spts} from {star} ({spos}); one player's score is a sample of one, and it should not be mistaken for a plan.",
            "{star} ({spos}) scored {spts}, {over_half} (a concentration of risk, not a strategy).",
        ],
        "pos": [
            "{star} ({spos}) posted {spts} for {w} (and {w} did start him, which the model counts in {w}'s favor).",
            "{w} started {star} ({spos}) and received {spts}, a return consistent with a sound lineup decision.",
            "{spts} from {star} ({spos}): the process that put him in the lineup deserves a little credit for the outcome.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} started {gname} ({gpos}), who scored {gpts} (a small cost, but a self-inflicted one).",
            "{gname} ({gpos}) returned {gpts} in a slot {l} chose to fill with him, which the efficiency column will remember.",
        ],
        "pos": [
            "{gname} ({gpos}) returned {gpts} for {l} (one slot, one draw from the distribution; it says little about the roster).",
            "A single starter missed: {gname} ({gpos}), {gpts}. That is variance, not a verdict on {l}.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} is {w_rec} ({w_rank}) and {l} is {l_rec} ({l_rank}), though a record is a noisy estimate of a roster's strength.",
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}); treat the order with the suspicion it has earned.",
        ],
        "pos": [
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}); the sample is still being collected, and neither side has been fully measured.",
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}); a record is a partial estimate, and for some rosters it is a modest one.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won (but a win is a single draw, and a single draw is a weak argument about the roster behind it).",
            "{w} beat {l}; whether the process behind the win holds up is a separate question the box score does not flatter.",
            "{w} won while leaving {wbench} on the bench (an efficiency loss the final score happened to hide).",
            "{w} won while starting {wdud} ({wdpos}), who scored {wdpts} (the result tolerated the decision; the model does not).",
            "{w} ({w_rec}) is {wluck} wins ahead of the all-play expectation (which is what luck looks like on a spreadsheet).",
            "{w} won by {thin} points (a margin well inside the noise, which could have gone the other way).",
        ],
        "pos": [
            "{l} lost (a single draw, and a poor one from the distribution, which says little about the roster).",
            "{l} lost to {w}; the process behind the lineup is better than the outcome suggests.",
            "{l} lost, but {lstar} ({lspos}) returned {lspts} (the lineup decision was sound; the result was not).",
            "{l} scored {lp}, above the week's league average of {labove}, and still lost (a bad outcome from a good draw).",
            "{l} ({l_rec}) is {lluck} wins behind the all-play expectation (bad variance, not bad rostering).",
            "{l} lost by {thin} points (a margin well inside the noise, which could have gone either way).",
            "{l} lost with {gname} ({gpos}) returning {gpts} in a starting slot (a drag no lineup can fully absorb).",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed (unverified).",
            "{n} insisted, evidence unspecified: “{qp}”",
            "“{qc}” {n} maintained, a claim worth checking.",
        ],
        "pos": [
            "“{qc}” {n} said (a defensible position).",
            "{n} said, with justified confidence: “{qp}”",
            "“{qc}” {n} said, and the claim is at least testable.",
        ],
    },
    "x.theme": {
        "neg": [
            "The working hypothesis of this desk has not changed: {theme}.",
            "A standing hypothesis, offered here once more: {theme}.",
            "This desk's working hypothesis, stated again: {theme}.",
        ],
        "pos": [
            "The working hypothesis of this desk has not changed: {theme}.",
            "A standing hypothesis, offered here once more: {theme}.",
            "This desk's working hypothesis, held with some confidence: {theme}.",
        ],
        "neutral": [
            "The caveat of this desk (the sample is small, and it applies here): {theme}.",
            "Yes, but (and the confidence interval is wide): {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, whom {rep} has been flagging since August (an early-sample signal, in {rep}'s defense), {ctx}.",
            "{rep} has been on {player} since August; the data now has {player} {ctx}.",
            "A note for {rep}'s file on {player}: he {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, though the sample is one game in {wl}", "{w} wins in {wl}; the model remains unconvinced"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the process looks sound in {wl}", "{w} wins in {wl}; the model is mildly impressed"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, and the model sees a pattern in {wl}", "{l} falls in {wl}; the efficiency column objects"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}; variance, not process", "{l} falls in {wl}, a result the model attributes to noise"],
    },
    "h.sl.any": {
        "neg": ["The numbers on {n} do not reassure in {wl}", "{n} in {wl}: the model has concerns", "A skeptical read on {n} as {wl} closes"],
        "pos": ["The numbers on {n} hold up in {wl}", "{n} in {wl}: the model approves, cautiously", "A generous read on {n} as {wl} closes"],
    },
}

SLANTS["columnist"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) scored {spts} for {w}, and a fellow ought to give the player his due before he gives the manager any.",
            "I will say this for {w}: {star} ({spos}) did the work, with {spts}, and it was not the manager's doing.",
            "{star} ({spos}) put up {spts}, {over_half}, which is a man carrying a team on his back and the manager taking the bow.",
        ],
        "pos": [
            "{star} ({spos}) scored {spts} for {w}, and {w} had the good sense to start him; there is something to be said for good sense.",
            "I tip my hat to {w}: he started {star} ({spos}), and {spts} came back, as it should.",
            "{spts} from {star} ({spos}), and the man who set the lineup earned the bow he took.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} started {gname} ({gpos}) and got {gpts}, which is the kind of decision a fellow makes once and remembers.",
            "{gname} ({gpos}) gave {l} {gpts}, and {l} had chosen him for the job, God help him.",
        ],
        "pos": [
            "{gname} ({gpos}) gave {l} {gpts}, but one bad slot has never been the whole story, and I would not make it one here.",
            "A single starter let {l} down: {gname} ({gpos}), {gpts}. It happens to the best of men.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} is {w_rec} ({w_rank}) and {l} is {l_rec} ({l_rank}), and I have learned not to trust a record to tell the truth.",
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), and the table, as ever, flatters somebody.",
        ],
        "pos": [
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), and a record never tells you everything about a man.",
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}), and I have a soft spot for a team that has more to it than its record.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won, and I would not call it much more than that; a win and a good week are cousins, not twins.",
            "{w} beat {l}, and I have been asking myself since how, and I am not satisfied with the answers.",
            "{w} won while leaving {wbench} sitting on the bench, which my father would have called carelessness.",
            "{w} won while starting {wdud} ({wdpos}), who gave {wdpts}, and a win like that should embarrass a careful man.",
            "{w} ({w_rec}) is {wluck} wins ahead of what the all-play record says, and luck, I have found, always sends a bill.",
            "{w} won by {thin} points, a margin that can slip away on any ordinary afternoon.",
        ],
        "pos": [
            "{l} lost, and I will not pretend it was anything but a loss, but the score is not the whole of the man.",
            "{l} lost to {w}, and that is no kind of verdict, whatever the table says.",
            "{l} lost, but {lstar} ({lspos}) did honest work with {lspts}, and that deserves a line.",
            "{l} scored {lp}, above the league average of {labove} for the week, and still lost, which is just bad luck, and no fault of the manager's.",
            "{l} ({l_rec}) is {lluck} wins behind what the all-play record says, which is the sort of luck I would not wish on anybody.",
            "{l} lost by {thin} points, a coin that came down the wrong way.",
            "{l} lost with {gname} ({gpos}) giving {gpts} in a starting slot, and a man cannot win that way, however well he plans.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed, as men do.",
            "{n} insisted, with some heat: “{qp}”",
            "“{qc}” {n} maintained, and I wrote it down so I could remember it later.",
        ],
        "pos": [
            "“{qc}” {n} said quietly, and I was inclined to believe him.",
            "{n} said, and meant it: “{qp}”",
            "“{qc}” {n} said, with the calm of a man who knows his business.",
        ],
    },
    "x.theme": {
        "neg": [
            "I have said it before, and I will say it again, because it has not stopped being true: {theme}.",
            "A fellow develops views over the years, and this is mine: {theme}.",
            "Call me stubborn; I will still say it: {theme}.",
        ],
        "pos": [
            "I have said it before, and I will say it again, because it has not stopped being true: {theme}.",
            "A fellow develops views over the years, and this one has only grown: {theme}.",
            "Call me loyal; I will still say it: {theme}.",
        ],
        "neutral": [
            "I will grant the result, and then add what I always add: {theme}.",
            "Fine, but a fellow has his reservations: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, whom {rep} has been going on about since August, {ctx}, and I record it for whatever it is worth.",
            "{rep} told anybody who would listen about {player} since August, and {player} {ctx}.",
            "I will give {rep} this much: he has been consistent on {player}, who {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, and I remain unpersuaded in {wl}", "{w} wins in {wl}, though it is hardly a cause for singing"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the faithful were right in {wl}", "{w} wins in {wl}, and a good week it was"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}, and I was not surprised", "{l} falls in {wl}, as I rather expected"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}, but I would not count the man out", "{l} falls in {wl}, but the faithful keep the faith"],
    },
    "h.sl.any": {
        "neg": ["A word of doubt about {n} in {wl}", "{n}, once more, in {wl}, and I have my reservations", "I remain unconvinced by {n} as {wl} closes"],
        "pos": ["A word in favor of {n} in {wl}", "{n}, once more, in {wl}, and I am rather fond of the view", "I remain a believer in {n} as {wl} closes"],
    },
}

SLANTS["tabloid"] = {
    "g.star": {
        "neg": [
            "Don't give {w} the credit, darlings: {star} ({spos}) did the work with {spts}, and the manager just stood next to the trophy.",
            "{star} ({spos}) scored {spts} for {w}, and we all know who really won it, and it was not the manager.",
            "{star} ({spos}) put up {spts}, {over_half}, which is a carry job and a half. Cute that {w} took the bow.",
        ],
        "pos": [
            "{star} ({spos}) scored {spts} for {w}, who started him, and we simply adore a manager with taste.",
            "{w} backed {star} ({spos}), and {spts} came back. Hats off, darlings.",
            "{spts} from {star} ({spos}), and {w} gets a little credit for the casting call.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} started {gname} ({gpos}) and got {gpts}. Started him! On purpose! Spill!",
            "{gname} ({gpos}) gave {l} {gpts}, and {l} put him in the lineup, darling. Voluntarily.",
        ],
        "pos": [
            "{gname} ({gpos}) gave {l} {gpts}, but one bad slot isn't a scandal about {l}, no matter what the group chat says.",
            "A single starter flopped: {gname} ({gpos}), {gpts}. Don't blame {l}, darlings.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} is {w_rec} ({w_rank}) and {l} is {l_rec} ({l_rank}), and a little bird says the table is lying.",
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). Don't believe a word of it.",
        ],
        "pos": [
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), and we hear the best is still coming.",
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}). There's more to this story, darling.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won! But a win is not a good week, and everyone in the group chat knows it.",
            "{w} beat {l}, and the whispers about how are LOUD.",
            "{w} won while leaving {wbench} on the bench! Allegedly a contender, darling.",
            "{w} won while starting {wdud} ({wdpos}), who scored {wdpts}. The win barely noticed the lineup, and neither did we.",
            "{w} ({w_rec}) is {wluck} wins ahead of what the all-play record says. Lucky, lucky, lucky. We said it.",
            "{w} won by just {thin} points. One bounce the other way, and what a headline THAT would have been.",
        ],
        "pos": [
            "{l} lost! But the score is hiding the real story, darling.",
            "{l} lost to {w}, and we refuse to call it a verdict.",
            "{l} lost, but {lstar} ({lspos}) turned up with {lspts}. Somebody was working, darling.",
            "{l} scored {lp}, above the league's {labove} average for the week, and still lost. Cursed, we tell you.",
            "{l} ({l_rec}) is {lluck} wins behind what the all-play record says. Unlucky, and very, very unfair.",
            "{l} lost by just {thin} points. A coin flip that landed the wrong way, and the poor dear.",
            "{l} lost with {gname} ({gpos}) giving {gpts} in a starting slot. Nobody could win like that, darling.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed, with a straight face.",
            "{n} insisted, darlings: “{qp}”",
            "“{qc}” {n} maintained. Sure, honey.",
        ],
        "pos": [
            "“{qc}” {n} said, and we believe every word.",
            "{n} said, glowing: “{qp}”",
            "“{qc}” {n} purred.",
        ],
    },
    "x.theme": {
        "neg": [
            "You heard it here first, and you'll hear it again: {theme}.",
            "Our sources have said it all season, and we will say it again: {theme}.",
            "The tea has not changed one bit: {theme}.",
        ],
        "pos": [
            "You heard it here first, and you'll hear it again: {theme}.",
            "Our sources have loved it all season, and we will say so again: {theme}.",
            "The tea is sweet and has not changed one bit: {theme}.",
        ],
        "neutral": [
            "Lovely win, darlings, but here's the tea: {theme}.",
            "Congratulations, we suppose, but: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, whom {rep} has been gushing about since August, {ctx}. Spill, {rep}!",
            "{rep} has been dishing on {player} since August, and {player} {ctx}, darlings.",
            "You read it from {rep} first: {player} {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, but the whispers continue in {wl}", "{w} wins in {wl}, and nobody is buying it"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the haters have gone quiet in {wl}", "{w} wins in {wl}, and we adore it"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}, and the group chat pounces", "{l} falls in {wl}, and the whispers return"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}, but don't count {l} out, darlings", "{l} falls in {wl}, and we love {l} anyway"],
    },
    "h.sl.any": {
        "neg": ["Whispers about {n} get louder in {wl}", "{n} is the talk of the group chat in {wl}, and not kindly", "What is going on with {n} in {wl}?"],
        "pos": ["Everyone is talking about {n} in {wl}, and kindly", "{n} is the toast of the group chat in {wl}", "Why we still adore {n} in {wl}"],
    },
}

SLANTS["deadpan"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) scored {spts} for {w}. The player did that. Not the manager.",
            "{w} won. {star} ({spos}) scored {spts}. Credit goes there.",
            "{star} ({spos}) scored {spts}, {over_half}. One player did it.",
        ],
        "pos": [
            "{star} ({spos}) scored {spts} for {w}. {w} started him. Good call.",
            "{w} started {star} ({spos}). {spts} came back. Fine work.",
            "{spts} from {star} ({spos}). {w} chose him. It paid off.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} started {gname} ({gpos}). He scored {gpts}. It was a choice.",
            "{gname} ({gpos}) gave {l} {gpts}. {l} put him there.",
        ],
        "pos": [
            "{gname} ({gpos}) scored {gpts} for {l}. One slot. Not the whole roster.",
            "One starter missed. {gname} ({gpos}), {gpts}. It happens.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} is {w_rec} ({w_rank}). {l} is {l_rec} ({l_rank}). Make of that what you will.",
            "After {wl}: {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). Records are not praise.",
        ],
        "pos": [
            "After {wl}: {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). It is not the whole story.",
            "{w} is {w_rec} ({w_rank}). {l} is {l_rec} ({l_rank}). There is more to both.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won. A win is not a good week. They are different.",
            "{w} beat {l}. How is another matter. It was not pretty.",
            "{w} left {wbench} on the bench. And won anyway. Noted.",
            "{w} started {wdud} ({wdpos}). He scored {wdpts}. {w} won anyway.",
            "{w} ({w_rec}) is {wluck} wins ahead of the all-play record. That is luck.",
            "{w} won by {thin} points. It could go the other way.",
        ],
        "pos": [
            "{l} lost. The score is not the whole story.",
            "{l} lost to {w}. It is not a verdict.",
            "{l} lost. {lstar} ({lspos}) scored {lspts}. He did his part.",
            "{l} scored {lp}. The league average was {labove}. {l} lost anyway. Bad luck.",
            "{l} ({l_rec}) is {lluck} wins behind the all-play record. That is bad luck.",
            "{l} lost by {thin} points. It could go either way. It did not.",
            "{l} lost. {gname} ({gpos}) scored {gpts} in a starting slot. That is hard to win with.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed.",
            "{n} insisted. “{qp}”",
            "“{qc}” {n} maintained. Sure.",
        ],
        "pos": [
            "“{qc}” {n} said. Calmly.",
            "{n} said it plainly. “{qp}”",
            "“{qc}” {n} said. Seems right.",
        ],
    },
    "x.theme": {
        "neg": [
            "The view has not changed. {theme}.",
            "Same as before. {theme}.",
            "Still true, apparently. {theme}.",
        ],
        "pos": [
            "The view has not changed. {theme}.",
            "Same as before, and meant. {theme}.",
            "Still true, apparently. {theme}.",
        ],
        "neutral": [
            "Fine. But. {theme}.",
            "A win. With a caveat. {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player} {ctx}. {rep} has been on him since August.",
            "{rep} has said it since August. {player} {ctx}.",
            "{player} {ctx}. {rep} has been watching him since August.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}. Nobody cheers. {wl}", "{w} wins in {wl}. It is fine"],
        "pos": ["{w} beats {l}, {wp}-{lp}. Deserved. {wl}", "{w} wins in {wl}. Good work"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}. {wl}. Not shocking", "{l} falls in {wl}. As expected"],
        "pos": ["{l} loses to {w}, {wp}-{lp}. {wl}. Not the whole story", "{l} falls in {wl}. It is not the end"],
    },
    "h.sl.any": {
        "neg": ["Doubts about {n}. {wl}", "{n} in {wl}. Questions remain", "Nothing reassuring about {n} in {wl}"],
        "pos": ["A case for {n}. {wl}", "{n} in {wl}. Holding up", "Something reassuring about {n} in {wl}"],
    },
}

SLANTS["noir"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) put up {spts} for {w}. The player did the job. The manager took the credit. I've seen that before.",
            "The week had a name, and it wasn't {w}. It was {star} ({spos}), {spts}, doing the heavy lifting.",
            "{star} ({spos}) went for {spts}, {over_half}. One man, one job, and somebody else on the receipt.",
        ],
        "pos": [
            "{star} ({spos}) went for {spts} for {w}, and {w} had put him there. Good instinct in a bad town.",
            "{w} made the call on {star} ({spos}), and {spts} walked in the door. Sometimes the hunch pays.",
            "{spts} from {star} ({spos}), and {w} was the one who called the number. I respect that.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} started {gname} ({gpos}) and got {gpts}. He picked that. I wrote it down.",
            "{gname} ({gpos}) gave {l} {gpts}. {l} put him in the lineup. That's a confession, if you ask me.",
        ],
        "pos": [
            "{gname} ({gpos}) gave {l} {gpts}. One bad slot. It doesn't make a case against the rest of the roster.",
            "A single starter went cold: {gname} ({gpos}), {gpts}. It happens in the best families.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} is {w_rec} ({w_rank}). {l} is {l_rec} ({l_rank}). Don't trust a record in this town. It lies for a living.",
            "After {wl}, the ledger read {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). A rap sheet, not a reference.",
        ],
        "pos": [
            "After {wl}, the ledger read {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). A record doesn't tell you what a man is made of.",
            "{w} is {w_rec} ({w_rank}). {l} is {l_rec} ({l_rank}). There's more under the coat than the ledger lets on.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won. A win is a win. A good week is something else, and that's the case I'm building.",
            "{w} beat {l}. I wanted to see how. I didn't like what I saw.",
            "{w} left {wbench} on the bench and still got the win. Careless, the way a man is careless when he's lucky.",
            "{w} started {wdud} ({wdpos}). He scored {wdpts}. {w} won anyway. The city looks after fools.",
            "{w} ({w_rec}) is {wluck} wins ahead of the all-play record. That's what luck looks like in this town.",
            "{w} won by {thin} points. A margin you could slip a knife through.",
        ],
        "pos": [
            "{l} lost. The score didn't tell the whole story. It never does.",
            "{l} lost to {w}. It's no kind of verdict. I've seen verdicts. This wasn't one.",
            "{l} lost, but {lstar} ({lspos}) put up {lspts}. Somebody was working the case.",
            "{l} scored {lp}, above the week's {labove} average, and still lost. Bad luck, nothing more.",
            "{l} ({l_rec}) is {lluck} wins behind the all-play record. The kind of luck nobody orders.",
            "{l} lost by {thin} points. A coin in a dark alley, and it landed the wrong way.",
            "{l} lost with {gname} ({gpos}) giving {gpts} in a starting slot. Nobody wins like that.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed. I've heard better lies in a worse bar.",
            "{n} insisted: “{qp}”",
            "“{qc}” {n} maintained, the way a man does when the lights are on him.",
        ],
        "pos": [
            "“{qc}” {n} said, and I was inclined to believe it.",
            "{n} said, steady as a streetlamp: “{qp}”",
            "“{qc}” {n} said. It rang true, which is rarer than you think.",
        ],
    },
    "x.theme": {
        "neg": [
            "I've been telling anybody who'd listen, and I'll keep telling them: {theme}.",
            "The case file hasn't changed: {theme}.",
            "It's the same story every week, and I keep writing it down: {theme}.",
        ],
        "pos": [
            "I've been telling anybody who'd listen, and I'll keep telling them: {theme}.",
            "The case file hasn't changed, and I wouldn't want it to: {theme}.",
            "It's the same story every week, and it's a good one: {theme}.",
        ],
        "neutral": [
            "A win, sure. But the file has a note in it: {theme}.",
            "It happened. I still have my doubts: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}. {rep} had his name in August. Now {player} {ctx}.",
            "{rep} has been on about {player} since August. {player} {ctx}.",
            "{rep} had the tip on {player} early, and {player} {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, but nobody should be fooled in {wl}", "{w} wins in {wl}, and the city still has questions"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the faithful were right in {wl}", "{w} wins in {wl}, and for once the town smiled"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}, and the doubts come back like rain", "{l} falls in {wl}, the way the file said it would"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}, but the story isn't over", "{l} falls in {wl}, but the case for {l} isn't closed"],
    },
    "h.sl.any": {
        "neg": ["Something doesn't add up about {n} in {wl}", "{n}, again, in {wl}, and the file gets thicker", "The shadow around {n} lengthens in {wl}"],
        "pos": ["Something does add up about {n} in {wl}", "{n}, once more, in {wl}, and the file looks good", "The light finds {n} in {wl}"],
    },
}

SLANTS["nature"] = {
    "g.star": {
        "neg": [
            "Observe {star} ({spos}): {spts} for {w}. It is the animal that hunts, and not the keeper who takes the credit.",
            "{w} prevails, but it is {star} ({spos}), with {spts}, who did the hunting. The keeper merely watched.",
            "{star} ({spos}) gathered {spts}, {over_half}. One creature fed the whole pride, and the keeper did not.",
        ],
        "pos": [
            "Observe {star} ({spos}): {spts} for {w}, a creature {w} had chosen well, and a choice worth noting.",
            "{w} selected {star} ({spos}) for the hunt, and {spts} came home. A wise keeper, as these things go.",
            "{spts} from {star} ({spos}), and {w}, who made the selection, deserves a little of the credit.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} sent out {gname} ({gpos}) and received {gpts}, a poor return from a creature {l} chose himself.",
            "{gname} ({gpos}) returned {gpts} to {l}, and the keeper had selected him. Nature is not kind to that mistake.",
        ],
        "pos": [
            "{gname} ({gpos}) returned only {gpts} to {l}. One weak creature does not make a weak herd.",
            "A single hunter came back empty: {gname} ({gpos}), {gpts}. It happens to every pride.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}); in the wild, a good season can be a lucky one.",
            "After {wl}, the herd stands {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). One does not trust the order of the herd until the drought has passed.",
        ],
        "pos": [
            "After {wl}, the herd stands {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). The order does not tell the whole of a creature.",
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}). There is more to the creature than its place in the herd.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} prevails. But surviving a week is not the same as thriving, and the observer is not yet convinced.",
            "{w} defeated {l}. How the creature managed it is a separate question, and not a flattering one.",
            "{w} prevailed while leaving {wbench} on the bench, unused, like prey left uneaten. The pride was fortunate.",
            "{w} prevailed with {wdud} ({wdpos}) in a starting slot, a creature that returned only {wdpts}. Fortune protects the careless.",
            "{w} ({w_rec}) is {wluck} wins ahead of what the all-play record predicts. In nature we call that luck.",
            "{w} prevailed by only {thin} points, a margin the next season may reverse.",
        ],
        "pos": [
            "{l} was beaten. But a single contest is not the measure of a pride.",
            "{l} lost to {w}. It is not a verdict on the creature.",
            "{l} lost, yet {lstar} ({lspos}) hunted well, with {lspts}. The pride was not idle.",
            "{l} gathered {lp}, above the week's average of {labove}, and still lost. A cruel stroke of nature.",
            "{l} ({l_rec}) is {lluck} wins behind what the all-play record predicts. Nature has been unkind.",
            "{l} lost by only {thin} points, a margin that falls either way, and fell the wrong way here.",
            "{l} lost with {gname} ({gpos}) returning {gpts} in a starting slot. No pride thrives on that.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed, as the creature does.",
            "{n} insisted, unconvincingly: “{qp}”",
            "“{qc}” {n} maintained, from the safety of the blind.",
        ],
        "pos": [
            "“{qc}” {n} said, with the calm of a creature at ease.",
            "{n} said, and the herd listened: “{qp}”",
            "“{qc}” {n} said, steadily.",
        ],
    },
    "x.theme": {
        "neg": [
            "And so the observer returns, as he always does, to one conclusion: {theme}.",
            "The finding of this long study has not changed: {theme}.",
            "One truth recurs, season after season: {theme}.",
        ],
        "pos": [
            "And so the observer returns, as he always does, to one conclusion: {theme}.",
            "The finding of this long study, happily, has not changed: {theme}.",
            "One truth recurs, season after season, and a welcome one: {theme}.",
        ],
        "neutral": [
            "A fine hunt, and yet the observer notes: {theme}.",
            "Remarkable, and yet: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, a creature {rep} has watched since August, {ctx}. Observe.",
            "{rep} pointed the observers toward {player} in August, and now {player} {ctx}.",
            "In August, {rep} marked {player} as one to watch, and {player} {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} prevails over {l}, {wp}-{lp}, though the observer is unmoved in {wl}", "{w} gets through {wl}, with the credit going elsewhere"],
        "pos": ["{w} prevails over {l}, {wp}-{lp}, and the herd takes note in {wl}", "{w} thrives in {wl}"],
    },
    "h.sl.loss": {
        "neg": ["{l} falls to {w}, {wp}-{lp}, in {wl}, as the weak do", "{l} stumbles in {wl}, and the herd moves on"],
        "pos": ["{l} falls to {w}, {wp}-{lp}, in {wl}, but the pride endures", "{l} stumbles in {wl}, and the observer is not worried"],
    },
    "h.sl.any": {
        "neg": ["The observer grows wary of {n} in {wl}", "{n} wanders into the open in {wl}, unprepared", "Signs of weakness around {n} in {wl}"],
        "pos": ["The observer grows fond of {n} in {wl}", "{n} strides into the open in {wl}, assured", "Signs of strength around {n} in {wl}"],
    },
}

SLANTS["wrestling"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) put up {spts} for {w}, and THAT is the guy who won the match, folks, not the manager in the corner!",
            "{w} gets the pin, but {star} ({spos}) did the work with {spts}! The manager just held the towel!",
            "{star} ({spos}) hit {spts}, {over_half}! That is a one-man show! And the manager is taking the belt!",
        ],
        "pos": [
            "{star} ({spos}) put up {spts} for {w}, and {w} sent him in! Smartest booking in the building!",
            "{w} called the number of {star} ({spos}), and {spts} came crashing down! What a call from the corner!",
            "{spts} from {star} ({spos}), and {w} made the call! Give that manager his flowers!",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} sent in {gname} ({gpos}) and got {gpts}! He PICKED that guy! Ladies and gentlemen, he picked him!",
            "{gname} ({gpos}) gave {l} {gpts}, and {l} booked him in the lineup! The referee should have stopped it!",
        ],
        "pos": [
            "{gname} ({gpos}) gave {l} {gpts}, but one bad spot does not lose a title for a champion!",
            "One wrestler botched the spot: {gname} ({gpos}), {gpts}! That's not on {l}, folks!",
        ],
    },
    "g.record": {
        "neg": [
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}), and don't you trust either record for a second!",
            "After {wl}, the card reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), and the referee missed more than a few things!",
        ],
        "pos": [
            "After {wl}, the card reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), and the best matches are STILL to come!",
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}), and a record never shows you the heart of a champion!",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} got the pin, but a pin is not a clinic, folks, and everybody in this building knows it!",
            "{w} beat {l}, sure! But HOW? That was not a technical masterpiece!",
            "{w} got the pin while leaving {wbench} on the BENCH! A real champion never does that!",
            "{w} got the pin with {wdud} ({wdpos}) in the starting spot, scoring {wdpts}! The referee should have been counting!",
            "{w} ({w_rec}) is {wluck} wins ahead of the all-play record! That is a LUCKY punch, folks!",
            "{w} won by just {thin} points! That could be a three-count the other way!",
        ],
        "pos": [
            "{l} lost! But the three-count does not tell the story, folks!",
            "{l} lost to {w}, and I refuse to call it a verdict!",
            "{l} lost, but {lstar} ({lspos}) came to fight with {lspts}! Respect!",
            "{l} scored {lp}, ABOVE the {labove} league average, and STILL lost! The referee missed something!",
            "{l} ({l_rec}) is {lluck} wins behind the all-play record! ROBBED, I tell you!",
            "{l} lost by just {thin} points! A shoulder up at the two-count in any other match!",
            "{l} lost with {gname} ({gpos}) giving {gpts} in a starting spot! Nobody wins from that corner!",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} CLAIMED from the ropes!",
            "{n} INSISTED: “{qp}”",
            "“{qc}” {n} maintained, with a straight face and a folding chair behind his back!",
        ],
        "pos": [
            "“{qc}” {n} said, belt held high!",
            "{n} roared it to the crowd: “{qp}”",
            "“{qc}” {n} said with the confidence of a champion!",
        ],
    },
    "x.theme": {
        "neg": [
            "And I will say it from the top rope until they throw me out: {theme}!",
            "Write it on the turnbuckle, folks: {theme}!",
            "My position has NOT changed one bit: {theme}!",
        ],
        "pos": [
            "And I will say it from the top rope until they throw me out: {theme}!",
            "Write it on the championship belt, folks: {theme}!",
            "My faith has NOT changed one bit: {theme}!",
        ],
        "neutral": [
            "A fair pin, folks, but here is my catch: {theme}!",
            "Yes, but, folks: {theme}!",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, the man {rep} has been calling a future champion since August, {ctx}!",
            "{rep} booked {player} for big things in August, and {player} {ctx}!",
            "{rep} has had {player} on the card since August, and {player} {ctx}!",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, but nobody is cheering in {wl}!", "{w} gets the pin in {wl}, and the doubters are LOUD!"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the believers were RIGHT in {wl}!", "{w} gets the pin in {wl}, and the crowd goes WILD!"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}, and the boos rain down!", "{l} is pinned in {wl}, and nobody is shocked!"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}, but the champion is not done!", "{l} is pinned in {wl}, but the belt is not gone!"],
    },
    "h.sl.any": {
        "neg": ["Trouble in the corner of {n} in {wl}!", "{n} steps into the ring in {wl}, and the crowd is not impressed!", "The heat is on {n} in {wl}!"],
        "pos": ["The crowd is behind {n} in {wl}!", "{n} steps into the ring in {wl}, and the building ROARS!", "{n} is the people's champion in {wl}!"],
    },
}

SLANTS["memo"] = {
    "g.star": {
        "neg": [
            "Please note that {star} ({spos}) delivered {spts} for {w}; attribution of this outcome to lineup management is not supported at this time.",
            "{w} achieved the target, with {spts} from {star} ({spos}); the contributing factor was the player, not the process.",
            "{star} ({spos}) contributed {spts}, {over_half}, a concentration risk we recommend flagging.",
        ],
        "pos": [
            "Please note that {star} ({spos}) delivered {spts} for {w}, confirming the lineup decision to start him.",
            "{w} selected {star} ({spos}) and realized {spts}, a favorable variance against expectations.",
            "{spts} from {star} ({spos}) reflects well on the process that put him there.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} elected to start {gname} ({gpos}), who delivered {gpts}. The decision has been logged.",
            "{gname} ({gpos}) delivered {gpts} against a lineup slot {l} assigned to him. We recommend a review.",
        ],
        "pos": [
            "{gname} ({gpos}) delivered {gpts} for {l}; this is a single-slot variance and not a roster-wide finding.",
            "One slot underperformed: {gname} ({gpos}), {gpts}. No action is required for {l}.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} is {w_rec} ({w_rank}) and {l} is {l_rec} ({l_rank}); we note that records are a lagging indicator.",
            "As of {wl}: {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). This is not an endorsement.",
        ],
        "pos": [
            "As of {wl}: {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). Records are a lagging indicator, and trend lines may differ.",
            "{w} is {w_rec} ({w_rank}) and {l} is {l_rec} ({l_rank}); the underlying fundamentals warrant a closer look.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} met its target, but meeting a target is not the same as a successful week; we recommend caution.",
            "{w} beat {l}; the quality of the process behind the result has been flagged for review.",
            "{w} met its target while leaving {wbench} on the bench, a gap against the optimal lineup we recommend addressing.",
            "{w} met its target while starting {wdud} ({wdpos}), who delivered {wdpts}. The variance is unfavorable, and the outcome masked it.",
            "{w} ({w_rec}) is {wluck} wins ahead of the all-play benchmark; we attribute the variance to luck.",
            "{w} won by {thin} points, a margin within tolerance for reversal.",
        ],
        "pos": [
            "{l} missed its target, but a single miss is not a pattern; no escalation is recommended.",
            "{l} lost to {w}; the result should not be read as a performance finding.",
            "{l} missed its target, though {lstar} ({lspos}) delivered {lspts} against expectations.",
            "{l} delivered {lp}, above the week's {labove} league benchmark, and still lost; an unfavorable variance.",
            "{l} ({l_rec}) is {lluck} wins behind the all-play benchmark; the shortfall is attributed to variance.",
            "{l} lost by {thin} points, a margin within the tolerance for either outcome.",
            "{l} lost with {gname} ({gpos}) delivering {gpts} in a starting slot, a headwind for any roster.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed in a message to the group.",
            "{n} insisted, per the thread: “{qp}”",
            "“{qc}” {n} maintained, per the group thread.",
        ],
        "pos": [
            "“{qc}” {n} confirmed in a message to the group.",
            "{n} wrote, with confidence: “{qp}”",
            "“{qc}” {n} stated, and we see no cause for concern.",
        ],
    },
    "x.theme": {
        "neg": [
            "Per our standing assessment, which remains unchanged: {theme}.",
            "Action item: none. Position unchanged: {theme}.",
            "For visibility, going forward: {theme}.",
        ],
        "pos": [
            "Per our standing assessment, which remains unchanged and favorable: {theme}.",
            "Action item: none. Position unchanged: {theme}.",
            "For visibility, with enthusiasm, going forward: {theme}.",
        ],
        "neutral": [
            "A positive result, with one open item: {theme}.",
            "Noted, with a caveat for follow-up: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "Following up on {rep}'s August recommendation: {player} {ctx}.",
            "{rep} flagged {player} as a priority in August, and {player} {ctx}.",
            "Per {rep}'s earlier note, {player} {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} meets target against {l}, {wp}-{lp}; concerns remain in {wl}", "{w} reports a win in {wl}; underlying process under review"],
        "pos": ["{w} exceeds target against {l}, {wp}-{lp}, in {wl}", "{w} reports a strong result in {wl}; process validated"],
    },
    "h.sl.loss": {
        "neg": ["{l} misses target against {w}, {wp}-{lp}; concerns escalate in {wl}", "{l} reports a loss in {wl}; review recommended"],
        "pos": ["{l} misses target against {w}, {wp}-{lp}; no escalation required in {wl}", "{l} reports a loss in {wl}; fundamentals intact"],
    },
    "h.sl.any": {
        "neg": ["Concerns flagged for {n} in {wl}", "{n}: {wl} update, with open questions", "Risk review recommended for {n} in {wl}"],
        "pos": ["Confidence reaffirmed for {n} in {wl}", "{n}: {wl} update, with good news", "Positive outlook maintained for {n} in {wl}"],
    },
}

SLANTS["british"] = {
    "g.star": {
        "neg": [
            "And it's {star} ({spos}) who does the business, {spts} for {w}, while the gaffer takes the credit from the dugout!",
            "{w} win it, but make no mistake, it was {star} ({spos}) with {spts}, and not a tactical masterclass from the dugout!",
            "{star} ({spos}) pops up with {spts}, {over_half}! A one-man team, and the gaffer taking the bow!",
        ],
        "pos": [
            "And it's {star} ({spos}) who does the business, {spts} for {w}, and {w} sent him out there, so full marks for the gaffer!",
            "{w} backed {star} ({spos}), and {spts} came back! That's why they pay the gaffer, or would, if anyone did!",
            "{spts} from {star} ({spos}), and what a call from the dugout by {w}!",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} start {gname} ({gpos}) and get {gpts}! He picked him! Proper schoolboy stuff!",
            "{gname} ({gpos}) gives {l} {gpts}, and {l} named him in the side! You couldn't write it!",
        ],
        "pos": [
            "{gname} ({gpos}) gives {l} {gpts}, but one off-day doesn't lose a manager the dressing room!",
            "One lad has an off-day: {gname} ({gpos}), {gpts}! That's not on {l}!",
        ],
    },
    "g.record": {
        "neg": [
            "{w} are {w_rec} ({w_rank}) and {l} are {l_rec} ({l_rank}), and I wouldn't trust the table as far as I could throw it!",
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), and the table has been known to flatter!",
        ],
        "pos": [
            "After {wl}, the table reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), and the table doesn't show you the half of it!",
            "{w} are {w_rec} ({w_rank}) and {l} are {l_rec} ({l_rank}), and there's more to both sides than the table lets on!",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} win, but a win isn't a performance, and everyone in the ground knows it!",
            "{w} beat {l}, and I'll be honest, I've seen prettier!",
            "{w} win while leaving {wbench} on the bench, on the bench! Not the work of a title side!",
            "{w} win with {wdud} ({wdpos}) in the starting side, and he got {wdpts}! They got away with one there!",
            "{w} ({w_rec}) are {wluck} wins ahead of the all-play record! Lucky, I'm afraid, and there's no other word!",
            "{w} won by just {thin} points! That goes the other way on another day!",
        ],
        "pos": [
            "{l} lose, but the scoreline doesn't tell the story, and I won't have it said!",
            "{l} lost to {w}, and it's no kind of verdict on the side!",
            "{l} lose, but {lstar} ({lspos}) gave his all, {lspts}! Proper effort!",
            "{l} scored {lp}, above the week's {labove} average, and still lost! Bad luck, and nothing else!",
            "{l} ({l_rec}) are {lluck} wins behind the all-play record! Robbed, I say, robbed!",
            "{l} lost by just {thin} points! A coin toss that fell the wrong way!",
            "{l} lost with {gname} ({gpos}) giving {gpts} in a starting slot! No side wins from there!",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed, with a straight face!",
            "{n} insisted: “{qp}”",
            "“{qc}” {n} maintained, which is what they all say!",
        ],
        "pos": [
            "“{qc}” {n} said, and fair play to him!",
            "{n} said, with real conviction: “{qp}”",
            "“{qc}” {n} said, quite rightly!",
        ],
    },
    "x.theme": {
        "neg": [
            "And I'll say it again, as I have all season: {theme}!",
            "I'll say it as often as I'm allowed: {theme}!",
            "Mark it down, and mark it twice: {theme}!",
        ],
        "pos": [
            "And I'll say it again, as I have all season: {theme}!",
            "I'll say it as often as I'm allowed, and with pleasure: {theme}!",
            "Mark it down, and mark it twice, because it's lovely: {theme}!",
        ],
        "neutral": [
            "Well played, mind, but I have my reservations: {theme}!",
            "Fair enough, but: {theme}!",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, whom {rep} has been banging the drum about since August, {ctx}!",
            "{rep} has been on about {player} since August, and {player} {ctx}!",
            "You heard it from {rep} first: {player} {ctx}!",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beat {l}, {wp}-{lp}, but nobody's singing in {wl}!", "{w} win in {wl}, and the doubters remain!"],
        "pos": ["{w} beat {l}, {wp}-{lp}, and the faithful were right in {wl}!", "{w} win in {wl}, and the terraces sing!"],
    },
    "h.sl.loss": {
        "neg": ["{l} lose to {w}, {wp}-{lp}, in {wl}, and the doubts return!", "{l} fall in {wl}, and nobody's surprised!"],
        "pos": ["{l} lose to {w}, {wp}-{lp}, in {wl}, but it isn't over!", "{l} fall in {wl}, but the faithful stay loyal!"],
    },
    "h.sl.any": {
        "neg": ["More questions than answers for {n} in {wl}!", "{n} back in the headlines in {wl}, and the pundits are circling!", "Doubts grow around {n} in {wl}!"],
        "pos": ["{n} makes the case in {wl}!", "{n} back in the headlines in {wl}, and for the right reasons!", "Hope grows around {n} in {wl}!"],
    },
}

SLANTS["courtroom"] = {
    "g.star": {
        "neg": [
            "The record reflects that {star} ({spos}) produced {spts} for {w}. The court declines to credit the manager for the testimony of the player.",
            "{w} prevailed, on the strength of {spts} from {star} ({spos}); the credit, in the view of this court, belongs to the witness.",
            "{star} ({spos}) produced {spts}, {over_half}; the prosecution submits that this was one player's case.",
        ],
        "pos": [
            "The record reflects that {star} ({spos}) produced {spts} for {w}, who had selected him. The selection is entered in {w}'s favor.",
            "{w} called {star} ({spos}) to the stand, and {spts} was the testimony. The defense rests.",
            "{spts} from {star} ({spos}), and the court notes that {w} made the call.",
        ],
    },
    "g.goat": {
        "neg": [
            "The record reflects that {l} started {gname} ({gpos}), who produced {gpts}. The selection is entered against {l}.",
            "{gname} ({gpos}) produced {gpts} in a slot {l} elected to fill with him. Exhibit B for the prosecution.",
        ],
        "pos": [
            "{gname} ({gpos}) produced {gpts} for {l}. The court finds one slot, and not a pattern, and so rules.",
            "One witness failed: {gname} ({gpos}), {gpts}. The defense moves that this not be held against {l}.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}); the court notes that a record is not a character reference.",
            "After {wl}, the docket reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), entered over the objection of this reporter.",
        ],
        "pos": [
            "After {wl}, the docket reads {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}); the defense reminds the court that a record is not the whole case.",
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}); the court is invited to look beyond the docket.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won; the prosecution submits that a win is not the same as a good week, and asks the court to note the distinction.",
            "{w} beat {l}. The method is not in evidence in {w}'s favor.",
            "{w} won while leaving {wbench} on the bench, a fact the prosecution enters as Exhibit A.",
            "{w} won while starting {wdud} ({wdpos}), who produced {wdpts}. The court finds the result lucky and the lineup careless.",
            "{w} ({w_rec}) is {wluck} wins ahead of the all-play expectation; the prosecution calls this luck, and the record supports the term.",
            "{w} won by {thin} points, a margin the prosecution submits could be reversed on appeal.",
        ],
        "pos": [
            "{l} lost; the defense submits that a loss is not the same as a poor week, and asks the court to note the distinction.",
            "{l} lost to {w}. The defense moves that the verdict not be read as a judgment on {l}.",
            "{l} lost, though {lstar} ({lspos}) gave testimony of {lspts} in {l}'s defense.",
            "{l} produced {lp}, above the week's {labove} league average, and still lost. The defense calls this bad luck.",
            "{l} ({l_rec}) is {lluck} wins behind the all-play expectation; the defense calls this misfortune, and the record supports the term.",
            "{l} lost by {thin} points, a margin the defense submits should be appealed.",
            "{l} lost with {gname} ({gpos}) producing {gpts} in a starting slot. The defense submits that no roster wins that case.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed, under no oath.",
            "{n} insisted, for the record: “{qp}”",
            "“{qc}” {n} maintained, over the objection of this court.",
        ],
        "pos": [
            "“{qc}” {n} testified, and the court found it credible.",
            "{n} stated, for the record: “{qp}”",
            "“{qc}” {n} said, in a voice the court found steady.",
        ],
    },
    "x.theme": {
        "neg": [
            "The finding of this court has not changed: {theme}.",
            "The prosecution restates its case: {theme}.",
            "Let the record show, once again: {theme}.",
        ],
        "pos": [
            "The finding of this court has not changed: {theme}.",
            "The defense restates its case, with confidence: {theme}.",
            "Let the record show, once again, and with approval: {theme}.",
        ],
        "neutral": [
            "The ruling stands, with a note in the margin: {theme}.",
            "Granted, but the court reserves a caveat: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, whom {rep} has argued for since August, {ctx}. The record is noted.",
            "{rep} entered {player} into evidence in August, and {player} {ctx}.",
            "Let the record show that {rep} backed {player} early, and {player} {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, and the prosecution is unmoved in {wl}", "{w} wins in {wl}; the court has reservations"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the defense rests in {wl}", "{w} wins in {wl}; the court is satisfied"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}; the prosecution rests", "{l} falls in {wl}, and the verdict surprises nobody"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}; the defense appeals", "{l} falls in {wl}, but the case is not closed"],
    },
    "h.sl.any": {
        "neg": ["The case against {n} grows in {wl}", "{n} before the court in {wl}, and the prosecution is ready", "Charges of doubt stand against {n} in {wl}"],
        "pos": ["The case for {n} grows in {wl}", "{n} before the court in {wl}, and the defense is ready", "The court looks kindly on {n} in {wl}"],
    },
}

SLANTS["weather"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) put up {spts} for {w}, a warm front the manager had nothing to do with, so don't hand him the umbrella.",
            "{w} gets the sunny result, but it was {star} ({spos}) generating the heat, {spts} of it. The forecaster in the dugout just stood under the awning.",
            "{star} ({spos}) logged {spts}, {over_half}, a one-system week and the manager taking credit for the weather.",
        ],
        "pos": [
            "{star} ({spos}) put up {spts} for {w}, who sent him out in the first place, so credit the forecaster.",
            "{w} read the radar right on {star} ({spos}), and {spts} rolled in. Nicely forecast.",
            "{spts} from {star} ({spos}), and {w} called the front before it arrived.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} started {gname} ({gpos}), and the reading was {gpts}. A forecast {l} made all by himself.",
            "{gname} ({gpos}) delivered {gpts} to {l}, and {l} picked the spot. Bad call on the radar.",
        ],
        "pos": [
            "{gname} ({gpos}) delivered {gpts} to {l}, a single cold spot in an otherwise decent system.",
            "One slot came in low: {gname} ({gpos}), {gpts}. A passing cloud, nothing more for {l}.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}), and the readings have been known to run warm.",
            "After {wl}, the readings show {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}); don't trust a thermometer that flatters.",
        ],
        "pos": [
            "After {wl}, the readings show {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}), and the long-range outlook is better than the numbers let on.",
            "{w} stands {w_rec} ({w_rank}) and {l} stands {l_rec} ({l_rank}); one reading never describes the whole climate.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} won, but a sunny result isn't the same as a good week, and the reporter is not fooled.",
            "{w} beat {l}, but the conditions were not what they appear on the scoreboard.",
            "{w} won while leaving {wbench} on the bench, unused, like a perfectly good umbrella left at home.",
            "{w} won with {wdud} ({wdpos}) in a starting slot, a reading of just {wdpts}. A lucky break in the clouds.",
            "{w} ({w_rec}) is {wluck} wins ahead of the all-play reading, which is luck by any instrument.",
            "{w} won by just {thin} points, a margin the next front can wipe away.",
        ],
        "pos": [
            "{l} lost, but the scoreboard is a single reading, not the whole climate.",
            "{l} lost to {w}, and that reading says little about {l}.",
            "{l} lost, but {lstar} ({lspos}) put up {lspts}, a warm spot in a cold afternoon.",
            "{l} logged {lp}, above the week's {labove} league average, and still lost, an unlucky draw from the weather.",
            "{l} ({l_rec}) is {lluck} wins behind the all-play reading, which is plain bad luck.",
            "{l} lost by just {thin} points, a margin that could have gone either way, and went the wrong way.",
            "{l} lost with {gname} ({gpos}) reading {gpts} in a starting slot. No forecast holds up against that.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed.",
            "{n} insisted: “{qp}”",
            "“{qc}” {n} maintained, with all the certainty of a bad forecast.",
        ],
        "pos": [
            "“{qc}” {n} said with confidence.",
            "{n} said, steady as high pressure: “{qp}”",
            "“{qc}” {n} said calmly.",
        ],
    },
    "x.theme": {
        "neg": [
            "And the long-range view has not changed: {theme}.",
            "My position remains unchanged: {theme}.",
            "I'll say it again, rain or shine: {theme}.",
        ],
        "pos": [
            "And the long-range view has not changed, and it is a good one: {theme}.",
            "My position remains unchanged: {theme}.",
            "I'll say it again, with pleasure: {theme}.",
        ],
        "neutral": [
            "A good result, though I'll add a caveat: {theme}.",
            "Fine, but the long-range view has a note on it: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, whom {rep} has been calling a breakout since August, {ctx}.",
            "{rep} saw {player} coming in August, and now {player} {ctx}.",
            "{rep} called {player} early, and {player} {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, but the skies stay doubtful in {wl}", "{w} wins in {wl}, and the doubters stay under cover"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and the forecast looks bright in {wl}", "{w} wins in {wl}, and the believers get their sunshine"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}, and the clouds gather", "{l} falls in {wl}, and the doubters said it would"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}, but a clearing is on the way", "{l} falls in {wl}, but the long-range view is bright"],
    },
    "h.sl.any": {
        "neg": ["More questions than answers for {n} in {wl}", "Doubts are building around {n} in {wl}", "A cold stretch for {n} in {wl}"],
        "pos": ["{n} makes the case in {wl}", "Hope is building around {n} in {wl}", "A warm stretch for {n} in {wl}"],
    },
}

SLANTS["finance"] = {
    "g.star": {
        "neg": [
            "{star} ({spos}) delivered {spts} for {w}; attribute the alpha to the player, not the portfolio manager.",
            "{w} posted the result, but {star} ({spos}) generated the return, {spts} of it. The manager is merely the custodian.",
            "{star} ({spos}) returned {spts}, {over_half}, which is concentration risk with a good quarter.",
        ],
        "pos": [
            "{star} ({spos}) delivered {spts} for {w}, who held the position, and the thesis is rewarded.",
            "{w} was long on {star} ({spos}), and {spts} came in. A well-timed position.",
            "{spts} from {star} ({spos}), and {w} gets credit for owning it.",
        ],
    },
    "g.goat": {
        "neg": [
            "{l} was long on {gname} ({gpos}), and the return was {gpts}. A self-inflicted write-down.",
            "{gname} ({gpos}) returned {gpts} on a position {l} chose to hold. Downgrade.",
        ],
        "pos": [
            "{gname} ({gpos}) returned {gpts} for {l}, a single position that does not describe the rest of the book.",
            "One holding underperformed: {gname} ({gpos}), {gpts}. A rounding error on {l}'s portfolio.",
        ],
    },
    "g.record": {
        "neg": [
            "{w} closes at {w_rec} ({w_rank}) and {l} at {l_rec} ({l_rank}), and past returns flatter the book.",
            "After {wl}, the ledger shows {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). Rating: suspect.",
        ],
        "pos": [
            "After {wl}, the ledger shows {w} {w_rec} ({w_rank}), {l} {l_rec} ({l_rank}). Rating: more upside than the price implies.",
            "{w} closes at {w_rec} ({w_rank}) and {l} at {l_rec} ({l_rank}); the book is worth more than its last close.",
        ],
    },
    "g.weak": {
        "neg": [
            "{w} posted the win, but a win is not a good quarter, and this desk is not upgrading the stock.",
            "{w} beat {l}; the quality of earnings behind the result is, to put it kindly, thin.",
            "{w} won while leaving {wbench} on the bench, uninvested capital a serious fund does not carry.",
            "{w} won while holding {wdud} ({wdpos}), who returned {wdpts}. The result masked the weak position.",
            "{w} ({w_rec}) is {wluck} wins ahead of the all-play benchmark, a lucky return and not a repeatable one.",
            "{w} won by just {thin} points, a margin with real downside risk.",
        ],
        "pos": [
            "{l} took the loss, but a single bad close is not a trend, and the stock remains a hold.",
            "{l} lost to {w}, and that result misprices {l}.",
            "{l} lost, though {lstar} ({lspos}) returned {lspts}, a bright spot in a down week.",
            "{l} posted {lp}, above the week's {labove} league average, and still lost. That is volatility, not weakness.",
            "{l} ({l_rec}) is {lluck} wins behind the all-play benchmark, a shortfall that is variance and not skill.",
            "{l} lost by just {thin} points, a margin that could have broken either way.",
            "{l} lost holding {gname} ({gpos}), who returned {gpts} in a starting slot. No portfolio outperforms with that.",
        ],
    },
    "x.attr": {
        "neg": [
            "“{qc}” {n} claimed.",
            "{n} insisted, without guidance: “{qp}”",
            "“{qc}” {n} maintained, a statement we are marking as unverified.",
        ],
        "pos": [
            "“{qc}” {n} said with confidence.",
            "{n} said, with conviction: “{qp}”",
            "“{qc}” {n} stated, reaffirming guidance.",
        ],
    },
    "x.theme": {
        "neg": [
            "Our rating on this has not changed: {theme}.",
            "Position unchanged, and still short: {theme}.",
            "Our thesis, restated for the record: {theme}.",
        ],
        "pos": [
            "Our rating on this has not changed: {theme}.",
            "Position unchanged, and still long: {theme}.",
            "Our thesis, restated for the record, with conviction: {theme}.",
        ],
        "neutral": [
            "A beat on the quarter, but with a caveat: {theme}.",
            "Hold rating, and here is why: {theme}.",
        ],
    },
    "x.hype": {
        "pos": [
            "{player}, a position {rep} has been long on since August, {ctx}. Position noted.",
            "{rep} flagged {player} as a buy in August, and {player} {ctx}.",
            "{rep} was early on {player}, and {player} {ctx}.",
        ],
    },
    "h.sl.win": {
        "neg": ["{w} beats {l}, {wp}-{lp}, but analysts stay cautious in {wl}", "{w} posts a win in {wl}; rating unchanged"],
        "pos": ["{w} beats {l}, {wp}-{lp}, and analysts upgrade in {wl}", "{w} posts a win in {wl}; rating raised"],
    },
    "h.sl.loss": {
        "neg": ["{l} loses to {w}, {wp}-{lp}, in {wl}, and analysts downgrade", "{l} posts a loss in {wl}; rating cut"],
        "pos": ["{l} loses to {w}, {wp}-{lp}, in {wl}, but analysts see a buying opportunity", "{l} posts a loss in {wl}; rating held"],
    },
    "h.sl.any": {
        "neg": ["Analysts cut their view on {n} in {wl}", "{n} faces more downside risk in {wl}", "Downgrade watch on {n} in {wl}"],
        "pos": ["Analysts raise their view on {n} in {wl}", "{n} shows more upside in {wl}", "Upgrade watch on {n} in {wl}"],
    },
}
