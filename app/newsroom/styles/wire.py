"""Wire-service straight news: past tense, exact numbers, attribution, no adjectives that cannot be sourced."""
FAMILY = {
    "id": "wire",
    "label": "Wire-service straight news",
    "desc": "Inverted pyramid. Past tense, plain verbs, every number exact, no metaphor, no opinion. Attributes everything to the box score or the league ledger.",
    "rhythm": "mixed, mostly medium sentences",
    "formality": "high",
    "metaphors": "none",
    "numbers": "exact",
    "lex": {
        "verb": {
            "blowout": ["routed", "overpowered", "overwhelmed"],
            "comfortable": ["defeated", "beat", "outscored"],
            "normal": ["defeated", "beat", "topped"],
            "close": ["narrowly defeated", "edged", "narrowly beat"],
        },
        "noun": {
            "blowout": ["a rout", "a lopsided result", "a one-sided result"],
            "comfortable": ["a comfortable win", "a clear win", "a two-score win"],
            "normal": ["a solid win", "a standard win", "a straightforward win"],
            "close": ["a one-score game", "a narrow win", "a close finish"],
        },
        "tier": {
            "hi": ["a strong return on the bid", "well above what the bid suggested", "a return that justified the claim"],
            "mid": ["a moderate return", "a respectable return", "a steady return"],
            "lo": ["a small return so far", "little production to date", "a modest return so far"],
        },
    },
    "T": {
        # ---------------- headlines: roundup ----------------
        "h.r.blow": [
            "{w} {verb} {l}, {wp}-{lp}, in {wl}",
            "{w} wins by {m} points over {l} in {wl}",
            "{w_team} wins {wp}-{lp} over {l_team}, the week's widest margin",
        ],
        "h.r.upset": [
            "{w}, {w_rank0} in the standings, beats {l}, {l_rank0}, {wp}-{lp}",
            "Upset: {w} ({w_rank0}) defeats {l} ({l_rank0}) in {wl}",
            "{w} defeats higher-ranked {l} in {wl}",
        ],
        "h.r.close": [
            "{w} {verb} {l} by {m} in {wl}",
            "{w} wins {wp}-{lp} over {l}, the week's closest game",
            "{l} falls to {w} by {m} points in {wl}",
        ],
        "h.r.top": [
            "{w} posts the week's high score, {wp}, in win over {l}",
            "{w} leads {wl} scoring with {wp} points",
            "{wl}: {w} scores {wp}, the week's best, against {l}",
        ],
        "h.r.tie": [
            "{a} and {b} tie at {pts} in {wl}",
            "{a}, {b} finish level at {pts} points",
            "Tie game: {a} and {b} each score {pts}",
        ],
        # ---------------- lede ----------------
        "r.lede.blow": [
            "{w} {verb} {l}, {wp} to {lp}, in {wl}. The {m}-point margin was the largest of the week.",
            "{w_team}, managed by {w}, beat {l_team} ({l}) by {m} points in {wl}, the widest margin on the schedule.",
            "The largest margin of {wl} belonged to {w}, who {verb} {l}, {wp}-{lp}.",
        ],
        "r.lede.upset": [
            "{w}, ranked {w_rank0} in the standings entering {wl}, {verb} {l}, who was ranked {l_rank0}, {wp} to {lp}. By standings position it was the week's biggest upset.",
            "{l}, {l_rank0} in the standings before {wl}, lost to {w}, {w_rank0}, {lp}-{wp}. No other result of the week crossed more places in the table.",
            "Entering {wl}, {w} stood {w_rank0} and {l} stood {l_rank0}. {w} won, {wp} to {lp}.",
        ],
        "r.lede.close": [
            "{w} {verb} {l}, {wp} to {lp}, in {wl}. The {m}-point margin was the closest of the week.",
            "{l_team} ({l}) lost to {w_team} ({w}) by {m} points in {wl}, the narrowest margin on the schedule: {lp}-{wp}.",
            "The closest game of {wl} ended {wp}-{lp} in favor of {w} over {l}, a difference of {m} points.",
        ],
        "r.lede.top": [
            "{w} scored {wp} in {wl}, the highest total of the week, and {verb} {l}, who scored {lp}. The league average was {wavg}.",
            "The top score of {wl} was {w}'s {wp}, against {l}'s {lp}. The average score across the league was {wavg}.",
            "{w_team} ({w}) led all teams with {wp} points in {wl}. {l} scored {lp} in the loss.",
        ],
        "r.lede.tie": [
            "{a_team} ({a}) and {b_team} ({b}) tied at {pts} points each in {wl}.",
            "{a} and {b} finished {wl} level at {pts} points, an unusual result.",
            "Neither {a} nor {b} won in {wl}: both scored {pts}.",
        ],
        # ---------------- per-game sentences ----------------
        "g.result": [
            "{w_team} ({w}) {verb} {l_team} ({l}), {wp}-{lp}.",
            "{w} defeated {l}, {wp} to {lp}.",
            "In {wl}, {w_nick} {verb} {l}, {wp}-{lp}.",
            "{l_team} ({l_nick}) fell to {w_team} ({w}), {lp} to {wp}.",
            "{w} won by {m} points, {wp}-{lp}, against {l}.",
            "{w} won {wp}-{lp} against {l} in {wl}, a margin of {m}.",
            "{l} lost {lp}-{wp} to {w}.",
            "{w} came out ahead of {l}, {wp} to {lp}.",
            "The {wl} meeting of {w} and {l} ended {wp}-{lp}.",
            "{l} scored {lp}; {w} scored {wp} and won by {m}.",
        ],
        "g.tie": [
            "{a} and {b} tied at {pts} points each.",
            "{a_team} ({a}) and {b_team} ({b}) finished level at {pts}.",
            "Neither {a} nor {b} could separate: {pts} each.",
        ],
        "g.star": [
            "{star} ({spos}) led {w}'s starters with {spts}, {sshare} of the team's {wp}.",
            "The top individual scorer for {w} was {star} ({spos}), who recorded {spts}.",
            "{star}, a {spos}, accounted for {spts} of {w}'s {wp}.",
        ],
        "g.goat": [
            "{l}'s lowest-scoring starter was {gname} ({gpos}), who produced {gpts}.",
            "{gname} ({gpos}) gave {l} {gpts} from the starting lineup.",
            "{l} received {gpts} from {gname} ({gpos}) in a starting slot.",
        ],
        "g.bench": [
            "{l} left {bench_left} on the bench; {bench_name} ({bench_pos}) scored {bench_pts} while not starting.",
            "{bench_name} ({bench_pos}) scored {bench_pts} on {l}'s bench. The best possible lineup would have added {bench_left}.",
            "A better lineup would have given {l} {bench_left} more, including {bench_pts} from {bench_name} ({bench_pos}), who did not start.",
        ],
        "g.streak_w": [
            "{w} has won {k} consecutive games and stands {w_rank} at {w_rec}.",
            "The win was {w}'s {k}th in a row; the team is {w_rec}, {w_rank} in the standings.",
            "{w} is {w_rec} and has won {k} straight, which places it {w_rank}.",
        ],
        "g.streak_l": [
            "{l} has lost {k} consecutive games and stands {l_rank} at {l_rec}.",
            "The loss was {l}'s {k}th in a row; the team is {l_rec}, {l_rank} in the standings.",
            "{l} is {l_rec} and has lost {k} straight, which places it {l_rank}.",
        ],
        "g.record": [
            "{w} improved to {w_rec} ({w_rank}); {l} fell to {l_rec} ({l_rank}).",
            "After {wl}, {w} is {w_rec} and {w_rank} in the standings; {l} is {l_rec} and {l_rank}.",
            "The result left {w} at {w_rec} and {l} at {l_rec}.",
        ],
        "g.top": [
            "{w}'s {wp} was the highest score of {wl}; the league average was {wavg}.",
            "No team scored more than {w}'s {wp} in {wl}. The league average was {wavg}.",
            "{wp} points made {w} the week's top scorer, against a league average of {wavg}.",
        ],
        "g.low": [
            "{l}'s {lp} was the lowest score of {wl}; the league average was {wavg}.",
            "No team scored less than {l}'s {lp} in {wl}. The league average was {wavg}.",
            "{lp} points made {l} the week's lowest scorer, against a league average of {wavg}.",
        ],
        "g.luck_up": [
            "{n} ({n_rec}) has {luck} wins relative to what its all-play record predicts.",
            "By all-play expectation, {n} is {luck} wins to the good at {n_rec}.",
            "{n}'s {n_rec} record is {luck} wins better than its weekly scoring suggests.",
        ],
        "g.luck_down": [
            "{n} ({n_rec}) has {luck} wins relative to what its all-play record predicts.",
            "By all-play expectation, {n} is {luck} wins behind at {n_rec}.",
            "{n}'s {n_rec} record is {luck} wins worse than its weekly scoring suggests.",
        ],
        "g.upset": [
            "{w} entered {wl} {w_rank0} in the standings; {l} was {l_rank0}.",
            "Before the game, {l} stood {l_rank0} and {w} stood {w_rank0}.",
            "{l} ranked {l_rank0} to {w}'s {w_rank0} at kickoff of {wl}.",
        ],
        "g.shotgun": [
            "{n} owes {sgn} for {why}.",
            "The ledger lists {sgn} against {n}: {why}.",
            "{n} incurred {sgn} in {wl}, for {why}.",
        ],
        "g.aside": [
            "{n}, who {trait}, absorbed {event}.",
            "Of note: {n}, who {trait}, finished {wl} with {event}.",
            "{n}, who {trait}, now has {event} on the record.",
        ],
        "r.close_shift": [
            "{in_names} moved into the top six after {wl}; {out_names} dropped out. {leader} leads the standings at {leader_rec}.",
            "In the standings, {in_names} climbed into the playoff positions and {out_names} fell out of them. {leader} is first at {leader_rec}.",
            "After {wl}, the top six changed: {in_names} in, {out_names} out. {leader} remains the leader at {leader_rec}.",
        ],
        "r.close_table": [
            "{leader} leads the standings at {leader_rec} after {wl}. {cut} holds the final playoff position at {cut_rec}.",
            "After {wl}, {leader} is first at {leader_rec}; the sixth and last playoff spot belongs to {cut} at {cut_rec}.",
            "The standings after {wl} show {leader} on top ({leader_rec}) and {cut} sixth ({cut_rec}).",
        ],
        "r.close_po": [
            "{wl} produced {ngames}. The largest margin was {big_m} points ({big_w} over {big_l}), and the highest score was {top_pts}, by {top_w}.",
            "Results from {wl}: {ngames} played; the widest margin was {big_m} points, {big_w} over {big_l}; the top score was {top_w}'s {top_pts}.",
            "In {wl}, {big_w} won by the largest margin, {big_m} points over {big_l}, and {top_w} posted the top score, {top_pts}.",
        ],
        # ---------------- preview ----------------
        "h.p.fav": [
            "{fav} favored over {dog} in {wl}",
            "{wl}: {fav} ({fav_odds}) holds the edge over {dog} ({dog_odds})",
            "{fav} is the favorite against {dog} in {wl}",
        ],
        "h.p.even": [
            "{a} and {b} meet in {wl} with similar playoff odds ({a_odds}, {b_odds})",
            "{wl}: {a} vs. {b} is close to a toss-up",
            "{a}, {b} face off in {wl} with no clear favorite",
        ],
        "h.p.lev": [
            "{wl}: {a} and {b} meet with the most playoff leverage on the slate",
            "{a} vs. {b} could move playoff odds by {swing} points in {wl}",
            "{wl} preview: {a}, {b} play with playoff position at stake",
        ],
        "p.lede": [
            "{a_team} ({a}) plays {b_team} ({b}) in {wl}, the featured game of the week.",
            "The featured game of {wl} is {a} against {b}.",
            "In {wl}, the featured matchup pairs {a_team} with {b_team}, the teams of {a} and {b}.",
            "{a} and {b} meet in {wl} with {swing} points of combined playoff-odds swing at stake.",
        ],
        "p.matchup": [
            "{a_team} ({a}, {a_rec}, {a_avg} points per game) plays {b_team} ({b}, {b_rec}, {b_avg}) in {wl}.",
            "{a} ({a_rec}) meets {b} ({b_rec}) in {wl}. {a} averages {a_avg} points per game; {b} averages {b_avg}.",
            "In {wl}, {b_team} ({b}, {b_rec}, {b_avg} per game) faces {a_team} ({a}, {a_rec}, {a_avg} per game).",
            "{a} is {a_rec} and scores {a_avg} per game. {b} is {b_rec} and scores {b_avg}. They play in {wl}.",
        ],
        "p.h2h_split": [
            "{a} and {b} have split their meetings this season, {h2h_rec}.",
            "The season series between {a} and {b} is level at {h2h_rec}.",
            "{a} and {b} have met this season and are even, {h2h_rec}.",
        ],
        "p.h2h_lead": [
            "{lead} leads {trail} {h2h_rec} in games between the two this season.",
            "{lead} holds a {h2h_rec} edge over {trail} in the season series.",
            "{trail} trails {lead} {h2h_rec} in meetings this season.",
        ],
        "p.h2h_none": [
            "{a} and {b} have not met this season.",
            "The game is the first meeting of the season between {a} and {b}.",
            "{a} and {b} have yet to play each other this season.",
        ],
        "p.stakes": [
            "A win would raise {a}'s playoff odds to {a_win}; a loss would lower them to {a_loss}. For {b} the figures are {b_win} and {b_loss}.",
            "If {a} wins, the playoff odds are {a_win}; if {a} loses, they are {a_loss}. For {b}: {b_win} with a win, {b_loss} with a loss.",
            "The simulations give {a} {a_win} with a win and {a_loss} with a loss, and {b} {b_win} with a win and {b_loss} with a loss.",
        ],
        "p.leverage": [
            "The result could move the two teams' combined playoff odds by {swing} points, the largest swing on the slate.",
            "{a} and {b} have the most at stake this week: {swing} points of combined playoff-odds swing.",
            "No game on the slate carries more playoff leverage than {a} against {b}, at {swing} points of swing.",
        ],
        "p.favorite": [
            "{fav} is the favorite on {fav_why}: {fav_odds} to make the playoffs against {dog}'s {dog_odds}.",
            "By {fav_why}, {fav} ({fav_odds}) is ahead of {dog} ({dog_odds}).",
            "{dog} is the underdog at {dog_odds}; {fav} is at {fav_odds}.",
        ],
        "p.vol": [
            "{vol_n}'s scoring has been the more volatile, with a standard deviation of {vol_std} points a week against {other_std} for {other}.",
            "Weekly scoring varies more for {vol_n} ({vol_std} points) than for {other} ({other_std}).",
            "{other} has been steadier, with a {other_std}-point standard deviation to {vol_n}'s {vol_std}.",
        ],
        "p.rivnote": [
            "The game is part of {rv_name}. {backstory}",
            "The two owners have a recorded rivalry, {rv_name}. {backstory}",
            "League records list the pairing as {rv_name}. {backstory}",
        ],
        "p.close": [
            "Both teams play in {wl}; lineups lock at kickoff.",
            "{a} and {b} are among the matchups scheduled for {wl}.",
            "The game is scheduled for {wl}.",
        ],
        # ---------------- trade ----------------
        "h.t": [
            "{a} sends {gave_s} to {b} for {got_s}",
            "{a} trades {gave_s} to {b} in exchange for {got_s}",
            "{b} acquires {gave_s} from {a} for {got_s}",
            "{a} and {b} complete trade: {gave_s} for {got_s}",
        ],
        "t.sides": [
            "{a} and {b} completed a trade in {wl}. {a} received {a_got}; {b} received {b_got}.",
            "The league's transaction log shows a {wl} trade between {a} and {b}. {a} acquired {a_got}. {b} acquired {b_got}.",
            "In {wl}, {a} gave up {b_got} and received {a_got} from {b}.",
            "{b} received {b_got} from {a} in {wl}, and sent {a_got} the other way.",
        ],
        "t.returns": [
            "In the {since_wk} since, the players {a} received have scored {a_pts} for {a}; those {b} received have scored {b_pts} for {b}. {lead} leads the early comparison.",
            "Since the trade, {lead}'s incoming players have produced {lead_pts}, to {trail_pts} for {trail}'s, over {since_wk}.",
            "Over {since_wk}, {a}'s new players scored {a_pts} and {b}'s scored {b_pts}. The early advantage belongs to {lead}.",
        ],
        "t.pending": [
            "{pk_side} received {pk_got}; {pl_side} received {pl_got}. A deal of picks for players cannot be graded on points yet.",
            "The trade sent {pk_got} to {pk_side} and {pl_got} to {pl_side}. Because one side received only picks, there is no production to compare.",
            "{pl_side} took {pl_got}, and {pk_side} took {pk_got}. Picks have not played a game, so the deal cannot be graded.",
        ],
        "t.fresh": [
            "The trade cannot be graded on production yet.",
            "Not enough games have been played to grade the trade.",
            "There is no production to compare yet.",
        ],
        "t.count": [
            "It is {n}'s {nth} trade of the season.",
            "{n} has now made the {nth} trade of the season.",
            "The deal was the {nth} of the season for {n}.",
        ],
        "t.rec": [
            "Before the trade, {a} was {a_rec} ({a_rank}) and {b} was {b_rec} ({b_rank}).",
            "Entering that week, {a} stood {a_rank} at {a_rec}; {b} stood {b_rank} at {b_rec}.",
            "At the time, the standings had {a} {a_rank} ({a_rec}) and {b} {b_rank} ({b_rec}).",
        ],
        "t.close": [
            "The league's transaction log lists the deal as complete.",
            "The transaction was processed by the league without incident.",
            "The deal appears in the league log as completed.",
        ],
        # ---------------- waiver ----------------
        "h.w.big": [
            "{n} spends {bid} to add {player}",
            "{player} ({pos}) costs {n} {bid} in Week {wk} waivers",
            "{n} wins {player} with a {bid} bid",
        ],
        "h.w.small": [
            "{n} adds {player} for {bid}",
            "{n} claims {player} ({pos}) with a {bid} bid",
            "{player} goes to {n} for {bid}",
        ],
        "h.w.free": [
            "{n} picks up free agent {player}",
            "{n} adds {player} ({pos}) in Week {wk}",
            "{player} lands with {n} in Week {wk}",
        ],
        "w.top_bid": [
            "{n} added {player} ({pos}) for {bid} in {wl}, the largest bid of the week.",
            "The week's largest waiver bid was {bid}, from {n}, for {player} ({pos}).",
            "{n} paid {bid} for {player} ({pos}), the top bid of {wl}.",
        ],
        "w.top_free": [
            "{n} added {player} ({pos}) in {wl}.",
            "{player} ({pos}) was added by {n} in {wl}.",
            "The notable pickup of {wl} was {player} ({pos}), by {n}.",
        ],
        "w.since": [
            "{player} has scored {spts} in the {since_wk} since, {tier}.",
            "In the {since_wk} since, {player} has produced {spts} for {n}: {tier}.",
            "{n} has received {spts} from {player} over {since_wk}, {tier}.",
        ],
        "w.others": [
            "Other adds: {others_text}.",
            "Also added that week: {others_text}.",
            "Elsewhere on the wire: {others_text}.",
        ],
        "w.total": [
            "{total_n} changed hands across {total_owners} in {wl}.",
            "The league recorded {total_n} added by {total_owners} in {wl}.",
            "In all, {total_owners} added {total_n} in {wl}.",
        ],
        "w.budget": [
            "{n} has spent {spent} of a {budget} FAAB budget this season.",
            "{n}'s FAAB spending this season stands at {spent} of {budget}.",
            "Of the {budget} FAAB budget, {n} has used {spent}.",
        ],
        "w.close": [
            "The league log shows {player} on {n}'s roster.",
            "{player} is now on {n}'s roster.",
            "The claim for {player} was processed by the league.",
        ],
        # ---------------- beer report ----------------
        "h.s": [
            "Beer Report, Week {wk}: {total_n} owed",
            "{top} owes the most shotguns in Week {wk}: {topn}",
            "Week {wk} shotgun ledger lists {total_n}",
            "Beer Report: {top} heads the Week {wk} list with {topn}",
        ],
        "s.total": [
            "The Week {wk} shotgun ledger lists {total_n} across {owners_n}.",
            "{owners_n} owe a combined {total_n} for Week {wk}.",
            "League records show {total_n} owed from Week {wk}, spread over {owners_n}.",
        ],
        "s.owner": [
            "{n} owes {sgn}: {list}.",
            "{n}: {sgn}, for {list}.",
            "The ledger lists {sgn} for {n}: {list}.",
            "{n} incurred {sgn} ({list}).",
        ],
        "s.low": [
            "The lowest score among the week's shotgun starters was {pts}, from {player} ({pos}) in {n}'s lineup.",
            "{player} ({pos}) of {n}'s lineup scored {pts}, the week's lowest figure on the ledger.",
            "{n} started {player} ({pos}), who scored {pts}, the lowest mark of the week.",
        ],
        "s.leader": [
            "{leader} leads the season ledger with {ltotal} through Week {wk}.",
            "Through Week {wk}, {leader} has the most shotguns on the season, {ltotal}.",
            "The season total is highest for {leader}: {ltotal}.",
        ],
        "s.close": [
            "{top} is listed first on the Week {wk} ledger.",
            "Shotguns are settled under league rules; {top} leads the Week {wk} list.",
            "The Week {wk} ledger is listed in order, beginning with {top}.",
        ],
        # ---------------- standings ----------------
        "h.n": [
            "Standings through {wl}: {top} leads, {six} holds sixth",
            "{alive} teams hold better than a 5% chance at {spots} playoff spots through {wl}",
            "{top} on top, {bottom} last: standings through {wl}",
            "Through {wl}: {six} holds the last playoff spot",
        ],
        "h.nf": [
            "Final standings: {top} earns the top seed",
            "{top} finishes first; {six} takes the last playoff seed and {seven} misses out",
            "Regular season final: {top} first, {bottom} last",
            "{six} claims the sixth seed, {seven} just misses: final standings",
        ],
        "n.top": [
            "Through {wl}, {top} leads the standings at {top_rec}.",
            "{top} is first at {top_rec} through {wl}.",
            "Through {wl}: {top} leads at {top_rec}.",
            "{top} is first at {top_rec} through {wl}, with {top_odds} playoff odds.",
            "Through {wl}: {top} leads at {top_rec}. The team has a {bye} chance of a first-round bye.",
        ],
        "n.cut": [
            "{six} ({six_rec}) holds the sixth and final playoff spot, one place ahead of {seven} ({seven_rec}).",
            "The playoff line falls between {six} ({six_rec}) and {seven} ({seven_rec}).",
            "{seven} ({seven_rec}) sits just outside the playoff positions, behind {six} ({six_rec}).",
        ],
        "n.luck": [
            "{lucky} has the league's best luck at {lucky_luck} wins above all-play expectation; {unlucky} is at {unlucky_luck}.",
            "By all-play expectation, {lucky} is {lucky_luck} wins to the good and {unlucky} is {unlucky_luck}.",
            "The luck index is highest for {lucky} ({lucky_luck}) and lowest for {unlucky} ({unlucky_luck}).",
        ],
        "n.clinch": [
            "Clinched a playoff spot: {names}.",
            "Teams that have clinched: {names}.",
            "Playoff spots secured by {names}.",
        ],
        "n.elim": [
            "Mathematically eliminated: {names}.",
            "Teams that can no longer reach the playoffs: {names}.",
            "Out of playoff contention: {names}.",
        ],
        "n.bottom": [
            "{bottom} is last at {bottom_rec}.",
            "The bottom of the standings belongs to {bottom} ({bottom_rec}).",
            "{bottom} ({bottom_rec}) holds the last place.",
        ],
        "n.eff": [
            "{best_n} has the league's best lineup efficiency at {best_pct} of the maximum possible score; {worst_n} is lowest at {worst_pct}.",
            "Lineup efficiency is highest for {best_n} ({best_pct}) and lowest for {worst_n} ({worst_pct}).",
            "Measured against the best possible lineups, {best_n} scored {best_pct} of the maximum and {worst_n} scored {worst_pct}.",
        ],
        "n.records": [
            "The season-high score is {hi_pts}, set by {hi_n} in Week {hi_wk}. The largest margin is {blow_m}, by {blow_w} over {blow_l} in Week {blow_wk}.",
            "League records: highest score, {hi_pts} ({hi_n}, Week {hi_wk}); biggest blowout, {blow_m} points ({blow_w} over {blow_l}, Week {blow_wk}).",
            "{hi_n} holds the scoring record at {hi_pts} (Week {hi_wk}). The widest win was {blow_w}'s over {blow_l}, by {blow_m} in Week {blow_wk}.",
        ],
        "n.ftop": [
            "{top} finished the regular season first at {top_rec}, with {top_pf} scored.",
            "The top seed went to {top}, at {top_rec} and {top_pf}.",
            "{top} ended the regular season on top: {top_rec}, {top_pf}.",
        ],
        "n.fcut": [
            "{six} took the sixth and final playoff seed at {six_rec}; {seven} finished seventh at {seven_rec}.",
            "The playoff line fell between {six} ({six_rec}) and {seven} ({seven_rec}).",
            "{seven} ({seven_rec}) missed the playoffs; {six} ({six_rec}) took the last spot.",
        ],
        "n.fpts": [
            "{pf_n} scored the most points in the regular season ({pf_pts}); {low_n} scored the fewest ({low_pts}).",
            "Regular-season scoring was highest for {pf_n} ({pf_pts}) and lowest for {low_n} ({low_pts}).",
            "{pf_n} led the league in points at {pf_pts}. {low_n} had the fewest, at {low_pts}.",
        ],
        "n.fbottom": [
            "{bottom} finished last at {bottom_rec}.",
            "The last-place team was {bottom} ({bottom_rec}).",
            "{bottom} ended the season at {bottom_rec}, the league's worst record.",
        ],
        "n.close": [
            "Through {wl}, {top} remains first.",
            "The standings are current through {wl}; {top} leads.",
            "{top} sits at the top of the table through {wl}.",
        ],
        # ---------------- feud ----------------
        "h.f": [
            "{a}, {b}: the case file",
            "What the record shows about {a} and {b}",
            "{a} and {b}: tension, by the numbers",
            "A look at the history of {a} and {b}",
        ],
        "f.h2h": [
            "{w} {verb} {l}, {wp}-{lp}, in Week {gwk}. The margin was {m} points.",
            "The most recent meeting, in Week {gwk}, went to {w}, {wp} to {lp}, a margin of {m} points.",
            "{l} lost to {w} in Week {gwk}, {lp}-{wp}, by {m} points.",
        ],
        "f.trade": [
            "{a} and {b} traded in Week {twk}: {a} received {a_got}, and {b} received {b_got}.",
            "In Week {twk}, the two owners made a trade. {a} took {a_got}; {b} took {b_got}.",
            "The transaction log shows a Week {twk} deal between {a} and {b}, with {b_got} going to {b} and {a_got} to {a}.",
        ],
        "f.adj": [
            "{hi} ({hi_rec}, {hi_rank}) sits just ahead of {lo} ({lo_rec}, {lo_rank}); {pf_gap} separate them in points scored.",
            "In the standings, {hi} is {hi_rank} and {lo} is {lo_rank}, with {pf_gap} between them in points scored.",
            "{lo} ({lo_rec}) trails {hi} ({hi_rec}) by {pf_gap} in points scored, {lo_rank} to {hi_rank} in the table.",
        ],
        "f.blow": [
            "{w} beat {l} by {m} points in Week {gwk}, {wp}-{lp}, the sort of margin a league remembers.",
            "In Week {gwk}, {w} {verb} {l}, {wp} to {lp}, by {m} points.",
            "The {m}-point margin in Week {gwk}, {w} over {l}, is among the largest of the season.",
        ],
        "f.sg": [
            "{a} has {a_sg} on the season ledger; {b} has {b_sg}.",
            "On the shotgun ledger, {a} stands at {a_sg} and {b} at {b_sg}.",
            "The season ledger lists {a_sg} for {a} and {b_sg} for {b}.",
        ],
        "f.story": [
            "League records list the pairing as {rv_name}. {backstory}",
            "The two owners are the subject of a recorded rivalry, {rv_name}. {backstory}",
            "{rv_name} is the league's name for it. {backstory}",
        ],
        "f.trait": [
            "{a} {a_trait}; {b} {b_trait}.",
            "Owner profiles note that {a} {a_trait} and that {b} {b_trait}.",
            "On the record, {a} {a_trait}, while {b} {b_trait}.",
        ],
        "f.mid": [
            "Through Week {wk}, {a} is {a_rec} ({a_rank}) and {b} is {b_rec} ({b_rank}).",
            "The standings through Week {wk} show {a} {a_rank} at {a_rec} and {b} {b_rank} at {b_rec}.",
            "{a} stands {a_rank} ({a_rec}) and {b} stands {b_rank} ({b_rec}) through Week {wk}.",
        ],
        "f.close": [
            "The figures are from the league's official records.",
            "The dispute is documented in the standings, the scoreboard and the transaction log.",
            "Both teams' records are public.",
        ],
        # ---------------- rivalry ----------------
        "h.v": [
            "{rv_name}: {a} meets {b} in Week {wk}",
            "{a}-{b} rivalry returns in Week {wk}",
            "Week {wk} preview: {rv_name}",
            "{a} and {b} renew {rv_name} in Week {wk}",
        ],
        "v.lede": [
            "{rv_name} returns in {wl}, with {a} playing {b}. {backstory}",
            "{a} and {b} meet in {wl} in the game the league calls {rv_name}. {backstory}",
            "The league's recorded rivalry, {rv_name}, is on the schedule in {wl}. {backstory}",
        ],
        "v.form": [
            "{a} is {a_rec} ({a_rank}) and averages {a_avg} points per game; {b} is {b_rec} ({b_rank}) and averages {b_avg}.",
            "{a}: {a_rec}, {a_rank}, {a_avg} per game. {b}: {b_rec}, {b_rank}, {b_avg} per game.",
            "Coming in, {b} stands {b_rank} at {b_rec} ({b_avg} per game), and {a} stands {a_rank} at {a_rec} ({a_avg} per game).",
        ],
        "v.close": [
            "{a} and {b} play in Week {wk}.",
            "The game is scheduled for Week {wk}.",
            "Week {wk} will decide the next entry in the {a}-{b} record.",
        ],
        # ---------------- offseason ----------------
        "h.o": [
            "Offseason report: {ntrades} and {npick} recorded",
            "League logs {ntrades}, {npick} before the season",
            "{ntrades} and {npick}: the offseason in review",
        ],
        "o.lede": [
            "The league recorded {ntrades} and {npick} before the season began.",
            "Before the first game, the league's transaction log showed {ntrades} and {npick}.",
            "Offseason activity totaled {ntrades} and {npick}.",
        ],
        "o.busy": [
            "The busiest traders were {busy_text}.",
            "Most active in trades: {busy_text}.",
            "By number of trades, the leaders were {busy_text}.",
        ],
        "o.big": [
            "The largest trade was between {side_a} and {side_b}: {side_a} received {a_got}, and {side_b} received {b_got}.",
            "By players and picks moved, the biggest deal sent {b_got} to {side_b} and {a_got} to {side_a}.",
            "The offseason's largest deal: {side_a} got {a_got}; {side_b} got {b_got}.",
        ],
        "o.close": [
            "{busiest} made the most trades.",
            "{busiest} led the league in offseason trades.",
            "The trade count was highest for {busiest}.",
        ],
        # ---------------- Sunday column ----------------
        "h.c": [
            "{a} and {b} exchange pointed remarks; the record stands through {wl}",
            "{a}, {b} at odds, according to each other",
            "Remarks traded between {a} and {b}",
            "{a} and {b}: what each said about the other",
        ],
        "h.c.rv": [
            "{rv_name}: {a} and {b} exchange remarks",
            "{a} and {b} on the record about {rv_name}",
            "Statements issued in {rv_name} by {a} and {b}",
        ],
        "h.c.next": [
            "{a} and {b} meet in Week {nwk}; both made statements",
            "Week {nwk}: {a} to play {b}, remarks exchanged",
            "Remarks traded before {a} plays {b} in Week {nwk}",
        ],
        "c.lede": [
            "Through {wl}, {a} is {a_rec} and ranked {a_rank}. {b} is {b_rec} and ranked {b_rank}.",
            "{a} ({a_rec}) is {a_rank} in the standings through {wl}. {b} ({b_rec}) is {b_rank}.",
            "The standings through {wl} list {a} {a_rank} at {a_rec} and {b} {b_rank} at {b_rec}.",
        ],
        "c.next": [
            "They are scheduled to play each other in Week {nwk}.",
            "{a} and {b} meet in Week {nwk}.",
            "The two play in Week {nwk}, according to the schedule.",
        ],
        "c.recent": [
            "In recent games, {a} {a_form}. {b} {b_form}.",
            "Over their most recent games, {a} {a_form}, and {b} {b_form}.",
            "Recent margins: {a} {a_form}; {b} {b_form}.",
        ],
        "c.gap": [
            "{hi} ({hi_rank}, {hi_rec}) is ahead of {lo} ({lo_rank}, {lo_rec}) in the standings. In points scored, the gap is {pf_gap}.",
            "In points scored, {hi} and {lo} are {pf_gap} apart, {hi_rank} and {lo_rank} in the table.",
            "The standings place {hi} {hi_rank} at {hi_rec} and {lo} {lo_rank} at {lo_rec}, with {pf_gap} between them in points scored.",
        ],
        "c.pick": [
            "On {fav_why}, {fav} is the favorite over {dog}.",
            "{fav} is the pick on {fav_why}; {dog} is not.",
            "The numbers favor {fav} over {dog}, based on {fav_why}.",
        ],
        "c.close": [
            "Neither {a} nor {b} has withdrawn a statement.",
            "No further statements were issued by {a} or {b}.",
            "{a} and {b} did not agree on anything else.",
        ],
        # ---------------- Monday analytics ----------------
        "h.a.luck": [
            "{lucky} is {lucky_luck} wins above expectation; {unlucky} is {unlucky_luck}",
            "Luck index: {lucky} leads at {lucky_luck}, {unlucky} trails at {unlucky_luck}",
            "{unlucky} trails the league in luck at {unlucky_luck}; {lucky} leads at {lucky_luck}",
        ],
        "h.a.eff": [
            "{best_n} leads lineup efficiency at {best_pct}; {worst_n} is last at {worst_pct}",
            "Lineup efficiency: {best_n} {best_pct}, {worst_n} {worst_pct}",
            "{worst_n} scored {worst_pct} of its possible points; {best_n} scored {best_pct}",
        ],
        "h.a.bench": [
            "{bench_n} left {bench_pts} on the bench through {wl}",
            "Bench report: {bench_n} leads with {bench_pts} unused",
            "{bench_pts} left on {bench_n}'s bench, the most in the league",
        ],
        "h.a.steady": [
            "{steady_n} was the steadiest weekly scorer; {wild_n} the least steady",
            "Weekly rank consistency: {steady_n} most stable, {wild_n} least",
            "{wild_n} varies most from week to week; {steady_n} varies least",
        ],
        "a.lede": [
            "The following figures run through {wl}, after {gp} for each team.",
            "All figures below cover {gp} per team, through {wl}.",
            "This report uses results through {wl}, {gp} per team.",
        ],
        "a.luck": [
            "{lucky} is {lucky_rec} against an expected {lucky_exp} wins, a luck index of {lucky_luck}. {unlucky} is {unlucky_rec} against an expected {unlucky_exp}, an index of {unlucky_luck}.",
            "By all-play expectation, {lucky} should have {lucky_exp} wins and has a record of {lucky_rec} ({lucky_luck}). {unlucky} should have {unlucky_exp} and has a record of {unlucky_rec} ({unlucky_luck}).",
            "Luck index leader: {lucky}, {lucky_luck} ({lucky_rec}, expected {lucky_exp} wins). Last: {unlucky}, {unlucky_luck} ({unlucky_rec}, expected {unlucky_exp} wins).",
        ],
        "a.eff": [
            "Lineup efficiency is points scored divided by the points of the best possible lineup. {best_n} stands at {best_pct}. {worst_n} stands at {worst_pct}. The league as a whole is at {lg_pct}.",
            "Across the league, lineups captured {lg_pct} of the available points. {best_n} led at {best_pct}; {worst_n} trailed at {worst_pct}.",
            "{best_n}: {best_pct} efficiency. {worst_n}: {worst_pct}. League: {lg_pct}.",
        ],
        "a.bench": [
            "Points left on the bench, measured against each team's best possible lineup, were highest for {bench_n} at {bench_pts} and lowest for {bench_low_n} at {bench_low_pts}.",
            "{bench_n} left {bench_pts} on the bench through the period. {bench_low_n} left {bench_low_pts}.",
            "Bench points unused: {bench_n}, {bench_pts}; {bench_low_n}, {bench_low_pts}.",
        ],
        "a.blunder": [
            "The largest single-week bench loss was {bl_n}'s in Week {bl_wk}: {bl_pts} below the best possible lineup. The top score on that bench was {bl_player} ({bl_pos}), {bl_player_pts}.",
            "In Week {bl_wk}, {bl_n} finished {bl_pts} short of the best possible lineup. {bl_player} ({bl_pos}) scored {bl_player_pts} on the bench.",
            "{bl_n} recorded the largest weekly bench loss so far, {bl_pts}, in Week {bl_wk}. The best bench score was {bl_player_pts}, by {bl_player} ({bl_pos}).",
        ],
        "a.steady": [
            "By weekly scoring rank, {steady_n} was the most consistent, averaging {steady_avg} and ranging from {steady_band}. {wild_n} was the least consistent, ranging from {wild_band}.",
            "{steady_n} averaged a weekly rank of {steady_avg}, ranging from {steady_band}. {wild_n} ranged from {wild_band}.",
            "Weekly rank spread: {steady_n} was narrowest (from {steady_band}, average {steady_avg}); {wild_n} was widest (from {wild_band}).",
        ],
        "a.trade": [
            "In the Week {twk} trade between {lead} and {trail}, the players {lead} received have scored {lead_pts} in the {since_wk} since. The players {trail} received have scored {trail_pts}.",
            "Since the Week {twk} trade, the players {lead} received have outscored those {trail} received, {lead_pts} to {trail_pts}, over {since_wk}.",
            "Early returns on the Week {twk} trade favor {lead}: {lead_pts} from the players received, against {trail_pts} for {trail}, over {since_wk}.",
        ],
        "a.close": [
            "Figures run through {wl}.",
            "Next Monday's report will cover the following week.",
            "All figures were computed from official scores.",
        ],
        # ---------------- shared ----------------
        "x.sig": [
            "{n} then added the line the league knows: “{catch}”",
            "{n} closed with a familiar line: “{catch}”",
            "Asked for a final word, {n} offered the usual: “{catch}”",
        ],
        "x.attr": [
            "“{qc}” {n} said.",
            "{n} said: “{qp}”",
            "“{qc}” said {n}.",
            "{n} told the league: “{qp}”",
            "“{qc}” {n} told reporters.",
        ],
    },
}
