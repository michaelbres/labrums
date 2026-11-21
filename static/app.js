/* Labrums League HQ — single-page frontend. Talks to the FastAPI backend. */
(() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const app = $('#app');
  const state = { seasons: [], season: null, data: null, newsFilter: 'all', newsWeek: 'all', newsTeam: 'all', shotFilter: 'outstanding', shotGroup: 'owner' };

  // ---------- utils ----------
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n, d = 2) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
  const pct = (p) => p == null ? '—' : `${Math.round(p * 100)}%`;
  const signed = (n) => n == null ? '—' : (n > 0 ? '+' : '') + fmt(n, 2);
  const ordinal = (n) => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };
  const team = (rid) => state.data.teams[String(rid)];
  // Dashed cut line only when the seeded teams are exactly the top-N rows of the standings.
  const cutIndex = () => {
    const n = state.data.league.playoff_teams, order = state.data.standings;
    return order.slice(0, n).every((rid) => team(rid).current_seed != null)
      && order.slice(n).every((rid) => team(rid).current_seed == null) ? n - 1 : -1;
  };
  const seedCell = (rid) => `<td class="num">${team(rid).current_seed ?? ''}</td>`;
  const initials = (name) => (name || '?').split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
  const avatar = (t, cls = '') => t.avatar
    ? `<img class="avatar ${cls}" src="${esc(t.avatar)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'avatar ${cls}',textContent:'${esc(initials(t.name))}'}))">`
    : `<span class="avatar ${cls}">${esc(initials(t.name))}</span>`;
  const teamCell = (rid, { sub = 'team' } = {}) => {
    const t = team(rid);
    const subText = sub === 'team' ? t.team_name : sub === 'record' ? t.record : '';
    return `<a class="team-cell" href="#/teams/${rid}">${avatar(t)}<span class="names"><b>${esc(t.name)}</b><small>${esc(subText)}</small></span></a>`;
  };
  const POWER_CAPTION = 'Rating 1–99: 35% record · 40% all-play · 25% scoring';
  const powerTable = (d, { eff = true } = {}) => {
    const rows = d.power_rankings.map((rid, i) => {
      const t = team(rid), diff = t.rank - (i + 1);
      const rating = t.power_rating ?? Math.round((t.power_score || 0) * 100);
      const vs = diff > 0 ? `<span class="badge good">+${diff}</span>` : diff < 0 ? `<span class="badge bad">${diff}</span>` : '<span class="dim">—</span>';
      return `<tr><td class="pw-rank"><span class="rank ${i === 0 ? 'top' : ''}">${i + 1}</span></td><td class="pw-team">${teamCell(rid, { sub: 'record' })}</td>
        <td class="num pw-rating" data-label="Rating"><span class="pw-n">${rating}</span><span class="meter" aria-hidden="true"><i style="width:${rating}%"></i></span></td>
        <td class="num" data-label="Avg">${fmt(t.avg, 1)}</td><td class="num" data-label="All-play">${pct(t.all_play.pct)}</td>
        ${eff ? `<td class="num" data-label="Lineup">${pct(t.lineup_efficiency)}</td>` : ''}
        <td class="num pw-vs" title="vs. standings">${vs}</td></tr>`;
    }).join('');
    return `<div class="table-wrap power-wrap"><table class="power-table ${eff ? 'has-eff' : ''}"><thead><tr><th class="pw-rank">#</th><th>Team</th><th class="num">Rating</th><th class="num">Avg</th><th class="num">All-play %</th>${eff ? '<th class="num">Lineup eff.</th>' : ''}<th class="num">vs. standings</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  };
  const luckFmt = (n) => { const r = Math.round(Math.abs(n) * 10) / 10; return (n > 0 && r ? '+' : n < 0 && r ? '\u2212' : '') + r.toFixed(1); };
  const LUCK_EXPLAINER = "Expected wins come from the all-play record: every week, your score is compared with every other team's, as if you played all of them. Luck is actual wins minus expected wins: positive means the schedule gave you wins your scoring didn't earn; negative means you outscored most of the league and still lost.";
  const luckCard = (d) => {
    const ids = Object.keys(d.teams).map(Number).sort((a, b) => team(b).luck - team(a).luck || team(a).rank - team(b).rank);
    const maxAbs = Math.max(0.01, ...ids.map((rid) => Math.abs(team(rid).luck)));
    const rows = ids.map((rid, i) => {
      const t = team(rid), cls = t.luck > 0.75 ? 'good' : t.luck < -0.75 ? 'bad' : '';
      const w = (Math.abs(t.luck) / maxAbs) * 50;
      return `<tr><td class="lk-rank"><span class="rank ${i === 0 ? 'top' : ''}">${i + 1}</span></td><td class="lk-team">${teamCell(rid, { sub: 'record' })}</td>
        <td class="num" data-label="All-play">${esc(t.all_play_record)}</td><td class="num" data-label="Exp. W">${fmt(t.expected_wins, 1)}</td><td class="num" data-label="Actual">${t.wins}</td>
        <td class="num lk-luck ${cls}" data-label="Luck"><span class="lk-n">${luckFmt(t.luck)}</span><span class="lk-meter" aria-hidden="true"><i class="${t.luck < 0 ? 'neg' : 'pos'} ${cls}" style="width:${w}%"></i></span></td>
        <td class="num" data-label="Lucky">${t.lucky_wins}</td><td class="num" data-label="Unlucky">${t.unlucky_losses}</td></tr>`;
    }).join('');
    return `<div class="card power-card luck-card section"><div class="card-h"><h2>Luck</h2></div><p class="luck-explain">${esc(LUCK_EXPLAINER)}</p>
      <div class="table-wrap power-wrap"><table class="luck-table"><thead><tr><th class="lk-rank">#</th><th>Team</th><th class="num">All-play</th><th class="num">Expected wins</th><th class="num">Actual wins</th><th class="num">Luck</th><th class="num">Lucky wins</th><th class="num">Unlucky losses</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
  };
  const teamLink = (rid) => `<a href="#/teams/${rid}">${esc(team(rid).name)}</a>`;
  const meter = (p, cls = '') => `<div class="meter-row"><div class="meter ${cls}"><i style="width:${Math.max(0, Math.min(100, (p || 0) * 100))}%"></i></div><span class="pct">${pct(p)}</span></div>`;
  const pageHead = (eyebrow, title, lead = '', extra = '') => `<div class="page-h"><div class="eyebrow">${eyebrow}</div><h1>${title}</h1>${lead ? `<p class="lead">${lead}</p>` : ''}${extra ? `<div class="page-tools">${extra}</div>` : ''}</div>`;
  const toast = (msg) => { let el = $('.toast'); if (!el) { el = document.createElement('div'); el.className = 'toast'; document.body.appendChild(el); } el.textContent = msg; el.classList.add('show'); clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove('show'), 2200); };
  const streakBadge = (s) => { if (!s || s === '—') return '<span class="dim">—</span>'; const cls = s[0] === 'W' ? 'good' : s[0] === 'L' ? 'bad' : ''; return `<span class="badge ${cls}">${esc(s)}</span>`; };
  const statusBadge = (st) => st === 'clinched' ? '<span class="badge good">Clinched</span>' : st === 'eliminated' ? '<span class="badge bad">Eliminated</span>' : '';

  async function api(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    const pin = localStorage.getItem('labrums_pin');
    if (pin) headers['X-Admin-Pin'] = pin;
    const res = await fetch(path, { ...opts, headers });
    if (!res.ok) { let msg = res.statusText; try { msg = (await res.json()).detail || msg; } catch (_) { } throw new Error(msg); }
    return res.json();
  }

  // ---------- charts ----------
  function sparkline(scores, avg) {
    const weeks = Object.keys(scores).map(Number).sort((a, b) => a - b);
    if (weeks.length < 2) return '<span class="dim">—</span>';
    const vals = weeks.map((w) => scores[w]);
    const w = 110, h = 26, pad = 2;
    const min = Math.min(...vals, avg), max = Math.max(...vals, avg);
    const x = (i) => pad + (i / (vals.length - 1)) * (w - 2 * pad);
    const y = (v) => h - pad - ((v - min) / ((max - min) || 1)) * (h - 2 * pad);
    const d = vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" role="img" aria-label="Weekly scores"><title>${vals.map((v, i) => `Wk ${weeks[i]}: ${v}`).join(', ')}</title><line x1="0" x2="${w}" y1="${y(avg).toFixed(1)}" y2="${y(avg).toFixed(1)}"/><path d="${d}"/></svg>`;
  }

  function scoreChart(t, leagueAvg) {
    const weeks = Object.keys(t.scores).map(Number).sort((a, b) => a - b);
    if (!weeks.length) return '<div class="empty">No games played yet.</div>';
    const games = {};
    state.data.games.forEach((g) => { if (g.a === t.roster_id || g.b === t.roster_id) games[g.week] = g; });
    const W = 720, H = 220, padL = 40, padR = 10, padT = 14, padB = 28;
    const vals = weeks.map((w) => t.scores[w]);
    const max = Math.max(...vals, leagueAvg) * 1.08;
    const bw = (W - padL - padR) / weeks.length;
    const y = (v) => padT + (H - padT - padB) * (1 - v / max);
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(max * f));
    let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Weekly scores for ${esc(t.name)}">`;
    ticks.forEach((tv) => { s += `<line class="axis" x1="${padL}" x2="${W - padR}" y1="${y(tv)}" y2="${y(tv)}"/><text x="${padL - 6}" y="${y(tv) + 4}" text-anchor="end">${tv}</text>`; });
    weeks.forEach((w, i) => {
      const v = t.scores[w]; const g = games[w];
      const won = g ? g.winner === t.roster_id : null;
      const cls = won === null ? '' : won ? 'win' : 'loss';
      const x = padL + i * bw + bw * 0.18, bwid = bw * 0.64;
      const opp = g ? (g.a === t.roster_id ? g.b : g.a) : null;
      const tip = `Week ${w}: ${v}${g ? ` ${won ? 'W' : won === false ? 'L' : 'T'} vs ${team(opp).name} (${g.a === t.roster_id ? g.b_pts : g.a_pts})` : ''}`;
      s += `<rect class="bar ${cls}" x="${x.toFixed(1)}" y="${y(v).toFixed(1)}" width="${bwid.toFixed(1)}" height="${(H - padB - y(v)).toFixed(1)}" rx="0"><title>${esc(tip)}</title></rect>`;
      s += `<text x="${(x + bwid / 2).toFixed(1)}" y="${H - padB + 16}" text-anchor="middle">${w}</text>`;
    });
    s += `<line class="avg" x1="${padL}" x2="${W - padR}" y1="${y(leagueAvg)}" y2="${y(leagueAvg)}"/><text class="avg-label" x="${W - padR}" y="${y(leagueAvg) - 5}" text-anchor="end">lg avg ${leagueAvg}</text>`;
    s += '</svg>';
    s += `<div class="legend"><span><i style="background:var(--accent)"></i>Win</span><span><i style="background:var(--faint)"></i>Loss</span><span><i class="dash"></i>League average</span></div>`;
    return s;
  }

  // ---------- views ----------
  function viewHome() {
    const d = state.data, L = d.league, cutIdx = cutIndex();
    const top = team(d.standings[0]);
    const lb = d.shotguns.leaderboard;
    const owed = lb.reduce((a, r) => a + r.outstanding, 0);
    const rec = d.records || {};
    const hi = rec.high_score ? `${fmt(rec.high_score.points)} · ${team(rec.high_score.roster_id).name} (wk ${rec.high_score.week})` : '—';
    const headlines = pickHeadlines(d.articles.filter((a) => a.type !== 'beat'), 6);
    const po = d.playoffs.teams;
    const [tw, tl, tt] = String(top.record).split('-').map(Number);
    const bubble = d.standings.slice(1).map(team).filter((t) => po[t.roster_id] && po[t.roster_id].playoff_pct != null)
      .sort((a, b) => Math.abs(po[a.roster_id].playoff_pct - 0.5) - Math.abs(po[b.roster_id].playoff_pct - 0.5))[0];
    const unbeaten = d.standings.map(team).filter((t) => t.wins > 0 && !t.losses && !t.ties);
    const byLuck = Object.keys(d.teams).map(team).filter((t) => t.luck != null).sort((a, b) => b.luck - a.luck);
    const lucky = byLuck[0], unlucky = byLuck[byLuck.length - 1];
    const luckTiles = (lucky && lucky.luck >= 0.5 ? `<div class="tile"><div class="label">Luckiest</div><div class="value">${esc(lucky.name)}</div><div class="sub"><span class="good">${luckFmt(lucky.luck)}</span> wins vs. expected</div></div>` : '')
      + (unlucky && unlucky.luck <= -0.5 ? `<div class="tile"><div class="label">Unluckiest</div><div class="value">${esc(unlucky.name)}</div><div class="sub"><span class="bad">${luckFmt(unlucky.luck)}</span> wins vs. expected</div></div>` : '');
    const heroTitle = L.status === 'complete' ? `${esc(top.name)} finished ${esc(top.record)} and the rest of you have notes.`
      : L.last_completed === 0 ? `Week 1. Nobody has lost yet. Enjoy it while it lasts.`
      : unbeaten.length > 1 ? `${unbeaten.map((t) => esc(t.name)).join(' and ')} are ${esc(top.record)} and nobody is okay.`
      : unbeaten.length === 1 ? `${esc(top.name)} is ${esc(top.record)} and nobody is okay.`
      : `Week ${L.current_week}. ${esc(top.name)} leads.${bubble ? ` ${esc(bubble.name)} is sweating.` : ''}`;
    return `
      <section class="hero">
        <div class="eyebrow"><span class="dot"></span>${esc(L.season)} / ${esc(L.name || 'Labrums and Lagers')}</div>
        <h1>${heroTitle}</h1>
        <p class="lead">${L.status === 'complete' ? 'Season complete' : `Week ${L.current_week} · ${L.last_completed} week${L.last_completed === 1 ? '' : 's'} in the books`} · ${L.playoff_teams} playoff spots. ${L.last_completed > 0 ? `League average is ${fmt(d.league_avg, 1)} points per team-week and ${owed} shotgun${owed === 1 ? ' is' : 's are'} still owed.` : 'Lineups lock Sunday. The shotgun ledger opens after the first scores post.'}</p>
        <div class="actions"><a class="btn btn-primary" href="#/standings">Standings</a><a class="btn-link" href="#/news">Latest news <span aria-hidden="true">↗</span></a></div>
      </section>
      <div class="tiles section">
        <div class="tile"><div class="label">Leader</div><div class="value">${esc(top.name)}</div><div class="sub">${top.record} · ${fmt(top.pf, 1)} PF</div></div>
        <div class="tile"><div class="label">Top score</div><div class="value">${rec.high_score ? fmt(rec.high_score.points, 1) : '—'}</div><div class="sub">${rec.high_score ? `${esc(team(rec.high_score.roster_id).name)}, week ${rec.high_score.week}` : ''}</div></div>
        <div class="tile"><div class="label">League average</div><div class="value">${fmt(d.league_avg, 1)}</div><div class="sub">points per team-week</div></div>
        <div class="tile"><div class="label">Shotguns owed</div><div class="value">${owed}</div><div class="sub">${lb[0] && lb[0].total ? `${esc(lb[0].name)} leads with ${lb[0].total}` : 'nobody yet'}</div></div>
        ${luckTiles}
      </div>
      <div class="card power-card section"><div class="card-h"><h2>Power rankings</h2><small>${POWER_CAPTION}</small><a href="#/standings">Full standings →</a></div>${powerTable(d, { eff: false })}</div>
      <div class="grid grid-2 section">
        <div class="card"><div class="card-h"><h2>Headlines</h2><a href="#/news">All news →</a></div>
          <ul class="clean headlines">${headlines.map((a) => `<li><div class="kicker">${esc(a.type)} · week ${a.week}</div><a href="#/news/${esc(a.id)}">${esc(a.headline)}</a></li>`).join('') || '<li class="empty">Nothing yet.</li>'}</ul>
        </div>
        <div>
          <div class="card section"><div class="card-h"><h2>Standings</h2><a href="#/standings">Full table →</a></div>
            <div class="table-wrap"><table><thead><tr><th>#</th><th>Team</th><th class="num">W-L</th><th class="num">PF</th><th class="num">Odds</th></tr></thead><tbody>
            ${d.standings.map((rid, i) => { const t = team(rid); return `<tr class="${i === cutIdx ? 'cut-line' : ''}"><td><span class="rank ${i === 0 ? 'top' : ''}">${i + 1}</span></td><td>${teamCell(rid)}</td><td class="num">${t.record}</td><td class="num">${fmt(t.pf, 1)}</td><td class="num">${pct(po[rid]?.playoff_pct)}</td></tr>`; }).join('')}
            </tbody></table></div></div>
          <div class="card"><div class="card-h"><h2>Shotgun leaderboard</h2><a href="#/shotguns">Check them off →</a></div>
            ${lb.slice(0, 6).map((r) => `<div class="hbar"><span>${esc(r.name)}</span><div class="meter warn"><i style="width:${lb[0].total ? (r.total / lb[0].total) * 100 : 0}%"></i></div><span class="num">${r.total} <span class="dim">(${r.outstanding} owed)</span></span></div>`).join('')}
          </div>
        </div>
      </div>`;
  }

  function viewStandings() {
    const d = state.data, L = d.league, po = d.playoffs.teams;
    const cutIdx = cutIndex();
    const rows = d.standings.map((rid, i) => {
      const t = team(rid);
      return `<tr class="${i === cutIdx ? 'cut-line' : ''}">
        <td><span class="rank ${i === 0 ? 'top' : ''}">${i + 1}</span></td>${seedCell(rid)}<td>${teamCell(rid)}</td>
        <td class="num"><b>${t.record}</b></td><td class="num">${fmt(t.pf, 1)}</td><td class="num">${fmt(t.pa, 1)}</td><td class="num">${fmt(t.avg, 1)}</td>
        <td class="num">${fmt(t.high, 1)}</td><td class="num">${fmt(t.low, 1)}</td><td>${streakBadge(t.streak)}</td>
        <td class="num">${t.all_play.w}-${t.all_play.l}</td><td class="num ${t.luck > 0.75 ? 'good' : t.luck < -0.75 ? 'bad' : ''}">${signed(t.luck)}</td>
        <td class="num">${t.power_rank}</td><td class="num">${pct(po[rid]?.playoff_pct)}</td><td>${sparkline(t.scores, d.league_avg)}</td></tr>`;
    }).join('');
    const rec = d.records || {};
    const recCard = rec.high_score ? `<div class="card"><div class="card-h"><h2>Season records</h2></div><dl class="kv">
      <dt>Highest score</dt><dd>${fmt(rec.high_score.points)} · ${teamLink(rec.high_score.roster_id)} (week ${rec.high_score.week})</dd>
      <dt>Lowest score</dt><dd>${fmt(rec.low_score.points)} · ${teamLink(rec.low_score.roster_id)} (week ${rec.low_score.week})</dd>
      <dt>Biggest blowout</dt><dd>${teamLink(rec.biggest_blowout.winner)} by ${fmt(rec.biggest_blowout.margin)} over ${teamLink(rec.biggest_blowout.winner === rec.biggest_blowout.a ? rec.biggest_blowout.b : rec.biggest_blowout.a)} (week ${rec.biggest_blowout.week})</dd>
      ${rec.closest_game ? `<dt>Closest game</dt><dd>${teamLink(rec.closest_game.winner)} by ${fmt(rec.closest_game.margin)} over ${teamLink(rec.closest_game.winner === rec.closest_game.a ? rec.closest_game.b : rec.closest_game.a)} (week ${rec.closest_game.week})</dd>` : ''}
      <dt>Highest-scoring game</dt><dd>${teamLink(rec.highest_scoring_game.a)} ${fmt(rec.highest_scoring_game.a_pts)} – ${teamLink(rec.highest_scoring_game.b)} ${fmt(rec.highest_scoring_game.b_pts)} (week ${rec.highest_scoring_game.week})</dd>
    </dl></div>` : '';
    const divIds = Object.keys(d.divisions || {});
    const divCard = divIds.length ? `<div class="card section"><div class="card-h"><h2>Divisions</h2></div><div class="grid grid-2">${divIds.map((id) => `
      <div><h3 style="margin:0 0 6px">${esc(d.divisions[id])}</h3><table><thead><tr><th>Team</th><th class="num">Record</th><th class="num">Div</th></tr></thead><tbody>${(d.division_standings[id] || []).map((rid) => `<tr><td>${teamCell(rid)}${d.division_leaders[id] === rid ? ' <span class="badge good">Leader</span>' : ''}</td><td class="num"><b>${team(rid).record}</b></td><td class="num">${team(rid).division_record ?? '—'}</td></tr>`).join('')}</tbody></table></div>`).join('')}</div></div>` : '';
    return `
      ${pageHead('01 / Standings', 'Standings', `Sorted by wins, then points for, then points against. Seed = current playoff seed (division winners first). Dashed line = playoff cut when it falls cleanly after the top ${L.playoff_teams} rows. Luck = actual wins minus all-play expected wins.`)}
      ${divCard}
      <div class="card section"><div class="table-wrap"><table><thead><tr><th>#</th><th class="num">Seed</th><th>Team</th><th class="num">Record</th><th class="num">PF</th><th class="num">PA</th><th class="num">Avg</th><th class="num">High</th><th class="num">Low</th><th>Streak</th><th class="num">All-play</th><th class="num">Luck</th><th class="num">Power</th><th class="num">Playoff %</th><th>Trend</th></tr></thead><tbody>${rows}</tbody></table></div></div>
      <div class="grid grid-2 section">
        <div class="card power-card"><div class="card-h"><h2>Power rankings</h2><small>${POWER_CAPTION}</small></div>${powerTable(d)}</div>
        ${recCard}
      </div>
      ${luckCard(d)}`;
  }

  function viewTeams() {
    const d = state.data, po = d.playoffs.teams;
    const cards = d.standings.map((rid) => {
      const t = team(rid);
      return `<a class="card" href="#/teams/${rid}" style="color:inherit">
        <div class="team-cell" style="margin-bottom:8px">${avatar(t, 'lg')}<span class="names"><b style="font-size:1.05rem">${esc(t.team_name)}</b><small>${esc(t.name)} · <span class="handle">@${esc(t.display_name)}</span>${t.nickname ? ` · “${esc(t.nickname)}”` : ''}</small></span></div>
        <div class="kv"><dt>Record</dt><dd><b>${t.record}</b> (${ordinal(t.rank)})</dd><dt>Avg</dt><dd>${fmt(t.avg, 1)}</dd><dt>Streak</dt><dd>${streakBadge(t.streak)}</dd><dt>Playoffs</dt><dd>${pct(po[rid]?.playoff_pct)} ${statusBadge(po[rid]?.status)}</dd><dt>Top player</dt><dd>${t.top_player ? `${esc(t.top_player.name)} (${fmt(t.top_player.points, 1)})` : '—'}</dd></div>
        <div style="margin-top:8px">${sparkline(t.scores, d.league_avg)}</div></a>`;
    }).join('');
    return `${pageHead('02 / Teams', 'Teams', 'Click a team for the full breakdown.')}<div class="cards">${cards}</div>`;
  }

  function viewTeam(rid) {
    const d = state.data, t = team(rid);
    if (!t) return '<div class="error">Unknown team.</div>';
    const po = d.playoffs.teams[rid] || {};
    const log = d.games.filter((g) => g.a === t.roster_id || g.b === t.roster_id).map((g) => {
      const me = g.a === t.roster_id, opp = me ? g.b : g.a, mine = me ? g.a_pts : g.b_pts, theirs = me ? g.b_pts : g.a_pts;
      const res = g.winner === t.roster_id ? 'W' : g.winner == null ? 'T' : 'L';
      return `<tr><td>${g.week}${g.regular ? '' : ' <span class="badge">playoffs</span>'}</td><td>${teamCell(opp, { sub: 'record' })}</td><td><span class="badge ${res === 'W' ? 'good' : res === 'L' ? 'bad' : ''}">${res}</span></td><td class="num">${fmt(mine)}</td><td class="num">${fmt(theirs)}</td><td class="num">${signed(mine - theirs)}</td></tr>`;
    }).join('');
    const sched = Object.entries(d.schedule).flatMap(([w, gs]) => gs.filter((g) => g.a === t.roster_id || g.b === t.roster_id).map((g) => ({ week: Number(w), opp: g.a === t.roster_id ? g.b : g.a })));
    const posMax = Math.max(1, ...Object.values(t.pos_points));
    const posBars = Object.entries(t.pos_points).map(([p, v]) => `<div class="hbar"><span class="mono">${esc(p)}</span><div class="meter"><i style="width:${(v / posMax) * 100}%"></i></div><span class="num">${fmt(v, 1)}</span></div>`).join('');
    const roster = [...t.roster].sort((a, b) => (b.starter - a.starter) || (b.season_points - a.season_points)).map((p) => `<tr><td>${p.starter ? '<span class="badge accent">ST</span>' : '<span class="dim">BN</span>'}</td><td class="mono">${esc(p.position)}</td><td>${esc(p.name)}</td><td class="dim">${esc(p.team || '')}</td><td class="num">${fmt(p.season_points, 1)}</td></tr>`).join('');
    const h2h = Object.entries(t.h2h).filter(([, r]) => r.w + r.l + r.t > 0).map(([o, r]) => `<tr><td>${teamCell(o, { sub: 'record' })}</td><td class="num">${r.w}-${r.l}${r.t ? `-${r.t}` : ''}</td></tr>`).join('');
    const shots = d.shotguns.items.filter((s) => s.roster_id === t.roster_id);
    const teamArts = d.articles.filter((a) => a.teams.includes(t.roster_id));
    const arts = teamArts.filter((a) => a.type !== 'beat').slice(0, 8);
    const beatArts = teamArts.filter((a) => a.type === 'beat');
    const br = (d.beat_reporters || []).find((b) => b.team && b.team.roster_id === t.roster_id);
    const beatCard = br || beatArts.length ? `<div class="card section beat-card"><div class="card-h"><h2>Team beat</h2>${beatArts.length ? `<a href="#/news" data-beat-team="${esc(t.roster_id)}">All ${beatArts.length} reports →</a>` : ''}</div>
            ${br ? `<div class="m-name">${esc(br.name)}</div><div class="m-outlet">${esc(br.outlet)}</div><div class="m-bio">${esc(br.bio)}</div>` : ''}
            <ul class="clean headlines">${beatArts.slice(0, 4).map((a) => `<li><div class="kicker">week ${esc(a.week)}</div><a href="#/news/${esc(a.id)}">${esc(a.headline)}</a></li>`).join('') || '<li class="empty">No report yet.</li>'}</ul></div>` : '';
    const prof = t.profile || {};
    const seedDist = (po.seed_dist || []).map((p, i) => `<div class="hbar"><span>Seed ${i + 1}</span><div class="meter ${i < d.league.playoff_teams ? '' : 'bad'}"><i style="width:${p * 100}%"></i></div><span class="num">${pct(p)}</span></div>`).join('');
    return `
      <div class="page-h team-head">${avatar(t, 'lg')}<div><div class="eyebrow">02 / Teams / ${ordinal(t.rank)} place</div><h1>${esc(t.team_name)}</h1><div class="lead">${esc(t.name)} <small class="handle">@${esc(t.display_name)}</small>${t.division_name ? ` · ${esc(t.division_name)}` : ''}${t.nickname ? ` · “${esc(t.nickname)}”` : ''}${prof.hometown ? ` · ${esc(prof.hometown)}` : ''}</div></div>
        <div class="team-status">${statusBadge(po.status)}</div></div>
      <div class="tiles section">
        <div class="tile"><div class="label">Record</div><div class="value">${t.record}</div><div class="sub">${ordinal(t.rank)} place · power #${t.power_rank}</div></div>
        <div class="tile"><div class="label">Points for</div><div class="value">${fmt(t.pf, 1)}</div><div class="sub">${fmt(t.avg, 1)} avg · ±${fmt(t.std, 1)}</div></div>
        <div class="tile"><div class="label">Points against</div><div class="value">${fmt(t.pa, 1)}</div><div class="sub">${t.pa > t.pf ? 'outscored' : 'outscoring opponents'}</div></div>
        <div class="tile"><div class="label">Playoff odds</div><div class="value">${pct(po.playoff_pct)}</div><div class="sub">bye ${pct(po.bye_pct)} · proj ${fmt(po.proj_wins, 1)} wins</div></div>
        <div class="tile"><div class="label">Luck</div><div class="value">${signed(t.luck)}</div><div class="sub">all-play ${t.all_play.w}-${t.all_play.l} · ${fmt(t.expected_wins, 1)} xW</div></div>
        <div class="tile"><div class="label">Lineup efficiency</div><div class="value">${pct(t.lineup_efficiency)}</div><div class="sub">${fmt(t.bench_points_left, 1)} pts left on bench</div></div>
        <div class="tile"><div class="label">Shotguns</div><div class="value">${shots.length}</div><div class="sub">${shots.filter((s) => !s.completed).length} outstanding</div></div>
        <div class="tile"><div class="label">Streak</div><div class="value">${esc(t.streak)}</div><div class="sub">high ${fmt(t.high, 1)} · low ${fmt(t.low, 1)}</div></div>
      </div>
      <div class="card section"><div class="card-h"><h2>Weekly scores</h2><small>bars colored by result</small></div>${scoreChart(t, d.league_avg)}</div>
      <div class="grid grid-2 section">
        <div class="card"><div class="card-h"><h2>Game log</h2></div><div class="table-wrap"><table><thead><tr><th>Wk</th><th>Opponent</th><th>Res</th><th class="num">For</th><th class="num">Against</th><th class="num">Margin</th></tr></thead><tbody>${log || '<tr><td colspan="6" class="empty">No games yet.</td></tr>'}</tbody></table></div>
          ${sched.length ? `<h3 style="margin-top:14px">Upcoming</h3><ul class="clean">${sched.map((s) => `<li>Week ${s.week}: vs ${teamLink(s.opp)} (${team(s.opp).record})</li>`).join('')}</ul>` : ''}</div>
        <div>
          <div class="card section pos-bars"><div class="card-h"><h2>Points by position</h2><small>starters only</small></div>${posBars || '<div class="empty">—</div>'}</div>
          <div class="card"><div class="card-h"><h2>Seed distribution</h2><small>${d.playoffs.sims.toLocaleString()} sims</small></div>${seedDist}</div>
        </div>
      </div>
      <div class="grid grid-2 section">
        <div class="card"><div class="card-h"><h2>Roster</h2><small>season points as a starter</small></div><div class="table-wrap"><table><thead><tr><th></th><th>Pos</th><th>Player</th><th>NFL</th><th class="num">Pts</th></tr></thead><tbody>${roster}</tbody></table></div></div>
        <div>
          <div class="card section"><div class="card-h"><h2>Head to head</h2></div><div class="table-wrap"><table><tbody>${h2h || '<tr><td class="empty">—</td></tr>'}</tbody></table></div></div>
          <div class="card section"><div class="card-h"><h2>Shotgun ledger</h2><a href="#/shotguns">Manage →</a></div>${shots.length ? shots.map((s) => shotRow(s, false)).join('') : '<div class="empty">Clean sheet. Suspicious.</div>'}</div>
          ${beatCard}
          <div class="card"><div class="card-h"><h2>In the news</h2></div><ul class="clean headlines">${arts.map((a) => `<li><div class="kicker">${esc(a.type)} · week ${a.week}</div><a href="#/news/${esc(a.id)}">${esc(a.headline)}</a></li>`).join('') || '<li class="empty">No coverage yet.</li>'}</ul></div>
        </div>
      </div>`;
  }

  function viewPlayoffs() {
    const d = state.data, P = d.playoffs, L = d.league;
    const order = [...d.standings].sort((a, b) => (P.teams[b].playoff_pct - P.teams[a].playoff_pct) || (P.teams[a].avg_seed - P.teams[b].avg_seed));
    const rows = order.map((rid, i) => {
      const t = team(rid), p = P.teams[rid];
      const ng = p.next_game;
      return `<tr class="${i === L.playoff_teams - 1 ? 'cut-line' : ''}"><td>${teamCell(rid, { sub: 'record' })}</td>
        <td>${meter(p.playoff_pct, p.playoff_pct >= 0.75 ? 'good' : p.playoff_pct < 0.25 ? 'bad' : '')}</td>
        <td>${meter(p.bye_pct)}</td><td class="num">${pct(p.top_seed_pct)}</td><td class="num">${fmt(p.avg_seed, 1)}</td><td class="num">${fmt(p.proj_wins, 1)}</td><td class="num">${fmt(p.proj_pf, 0)}</td><td class="num">${p.games_left}</td>
        <td>${ng && ng.if_win != null ? `<span class="good">${pct(ng.if_win)}</span> / <span class="bad">${pct(ng.if_loss)}</span>` : '<span class="dim">—</span>'}</td><td>${statusBadge(p.status)}</td></tr>`;
    }).join('');
    const seeds = order.map((rid) => `<tr><td>${teamCell(rid, { sub: 'record' })}</td>${P.teams[rid].seed_dist.map((p, i) => `<td class="num" style="background:color-mix(in srgb, var(--accent) ${Math.round(p * 100)}%, transparent)">${p >= 0.005 ? pct(p) : '<span class="dim">·</span>'}</td>`).join('')}</tr>`).join('');
    const nseeds = order.length;
    return `
      ${pageHead('03 / Playoff odds', 'Playoff odds', `${P.sims.toLocaleString()} simulated seasons. Each team's weekly score ~ Normal(mean, sd), shrunk toward the league average (${fmt(P.league_mu, 1)} ± ${fmt(P.league_sd, 1)}). Seeding: ${esc(P.seeding_rule || 'by record, then points for')}. Top ${L.playoff_teams} make it${L.playoff_teams === 6 ? ', top 2 get a bye' : ''}.`)}
      <div class="card section"><div class="table-wrap"><table><thead><tr><th>Team</th><th>Make playoffs</th><th>First-round bye</th><th class="num">#1 seed</th><th class="num">Avg seed</th><th class="num">Proj W</th><th class="num">Proj PF</th><th class="num">Left</th><th>Next game: win / loss</th><th></th></tr></thead><tbody>${rows}</tbody></table></div></div>
      <div class="card section"><div class="card-h"><h2>Seed distribution</h2><small>probability of finishing at each seed</small></div><div class="table-wrap"><table><thead><tr><th>Team</th>${Array.from({ length: nseeds }, (_, i) => `<th class="num">${i + 1}</th>`).join('')}</tr></thead><tbody>${seeds}</tbody></table></div></div>`;
  }

  function shotRow(s, editable) {
    const reasonBadge = { zero: '<span class="badge warn">0 pts</span>', negative: '<span class="badge bad">negative</span>', low: '<span class="badge warn">low</span>', empty_slot: '<span class="badge">empty slot</span>', rule: '<span class="badge accent">rule</span>', manual: '<span class="badge">manual</span>' }[s.reason] || '';
    const what = s.reason === 'rule' || s.reason === 'manual' ? `<b>${esc(s.label)}</b><small>${esc(s.detail || '')}</small>` : `<b>${esc(s.player.name)}</b><small>${esc(s.player.position)}${s.player.team ? ` · ${esc(s.player.team)}` : ''} · started at ${esc(s.slot)} · ${fmt(s.points)} pts</small>`;
    const del = editable && s.reason === 'manual' ? `<button class="btn btn-sm btn-ghost btn-danger" data-del="${s.manual_id}" title="Remove">✕</button>` : '';
    return `<div class="shot-row ${s.completed ? 'done' : ''}" data-key="${esc(s.key)}">
      <input type="checkbox" ${s.completed ? 'checked' : ''} ${editable ? '' : 'disabled'} data-toggle="${esc(s.key)}" title="${s.completed ? `Completed ${esc(s.completed_at || '')}` : 'Mark as shotgunned'}">
      <span class="dim">Wk ${s.week}</span><span class="what">${what}</span>${reasonBadge}${del}</div>`;
  }

  function viewShotguns() {
    const d = state.data, S = d.shotguns, L = d.league;
    const lb = S.leaderboard, maxTotal = Math.max(1, ...lb.map((r) => r.total));
    const locked = d.meta.admin_locked && !localStorage.getItem('labrums_pin');
    const rows = lb.map((r) => `<tr><td><span class="rank ${r.rank === 1 && r.total ? 'top' : ''}">${r.rank}</span></td><td>${teamCell(r.roster_id)}</td><td class="num"><b>${r.total}</b></td><td class="num good">${r.completed}</td><td class="num ${r.outstanding ? 'bad' : ''}">${r.outstanding}</td><td><div class="meter-row"><div class="meter good" title="${r.completed} of ${r.total} done"><i style="width:${r.total ? (r.completed / r.total) * 100 : 0}%"></i></div><span class="pct">${r.total ? Math.round((r.completed / r.total) * 100) : 0}%</span></div></td><td class="dim">${Object.entries(r.by_reason).map(([k, v]) => `${v} ${k.replace('_', ' ')}`).join(', ') || '—'}</td><td class="dim">${r.worst_week ? `wk ${r.worst_week.week} (${r.worst_week.count})` : '—'}</td></tr>`).join('');
    let items = S.items;
    if (state.shotFilter === 'outstanding') items = items.filter((s) => !s.completed);
    if (state.shotFilter === 'completed') items = items.filter((s) => s.completed);
    let groups;
    if (state.shotGroup === 'owner') {
      groups = lb.map((r) => ({ key: r.roster_id, title: teamCell(r.roster_id), items: items.filter((s) => s.roster_id === r.roster_id), total: r.total, done: r.completed }));
    } else {
      const weeks = [...new Set(items.map((s) => s.week))].sort((a, b) => b - a);
      groups = weeks.map((w) => ({ key: w, title: `<b>Week ${w}</b>`, items: items.filter((s) => s.week === w) }));
    }
    const special = (S.rules.special || []).filter((r) => r.owners && r.owners.length);
    const ownerOpts = d.standings.map((rid) => `<option value="${rid}">${esc(team(rid).name)}</option>`).join('');
    const weekOpts = Array.from({ length: Math.max(1, L.last_completed) }, (_, i) => `<option value="${i + 1}">Week ${i + 1}</option>`).reverse().join('');
    return `
      ${pageHead('04 / Shotguns', 'Shotgun leaderboard 🍺', `Start a player who scores ${S.rules.threshold} or fewer, shotgun a beer.${S.rules.count_empty_slots ? ' Empty starting slots count.' : ''}${special.length ? ` Special rules: ${special.map((r) => `${esc(r.label)} (${r.owners.map(esc).join(', ')}${r.target ? ` vs ${esc(r.target)}` : ''})`).join('; ')}.` : ''}`,
        d.meta.admin_locked ? `<div class="form-row"><input class="input" id="pin" type="password" placeholder="Admin PIN" value="${esc(localStorage.getItem('labrums_pin') || '')}"><button class="btn btn-sm" id="pin-save">Unlock</button>${locked ? '<span class="lock-note">Check-offs are locked until you enter the PIN.</span>' : '<span class="lock-note">Unlocked.</span>'}</div>` : '')}
      <div class="card section"><div class="table-wrap"><table><thead><tr><th>#</th><th>Owner</th><th class="num">Total</th><th class="num">Done</th><th class="num">Owed</th><th>Progress</th><th>Breakdown</th><th>Worst week</th></tr></thead><tbody>${rows}</tbody></table></div></div>
      <div class="card section">
        <div class="card-h"><h2>The ledger</h2>
          <div class="chips">
            ${['outstanding', 'completed', 'all'].map((f) => `<span class="chip ${state.shotFilter === f ? 'active' : ''}" data-filter="${f}">${f}</span>`).join('')}
            <span style="width:8px"></span>
            ${['owner', 'week'].map((g) => `<span class="chip ${state.shotGroup === g ? 'active' : ''}" data-group="${g}">by ${g}</span>`).join('')}
          </div></div>
        ${groups.map((g) => g.items.length || state.shotGroup === 'owner' ? `<details class="owner-block" ${g.items.length ? 'open' : ''}><summary>${g.title}<div class="meter good" style="max-width:160px"><i style="width:${g.total ? (g.done / g.total) * 100 : 0}%"></i></div><span class="dim">${g.items.length} shown${g.total != null ? ` · ${g.done}/${g.total} done` : ''}</span></summary>${g.items.map((s) => shotRow(s, !locked)).join('') || '<div class="empty">Nothing here.</div>'}</details>` : '').join('') || '<div class="empty">No shotguns match that filter.</div>'}
      </div>
      <div class="card section"><div class="card-h"><h2>Add a manual shotgun</h2><small>for anything the automatic rules miss</small></div>
        <form class="form-row" id="manual-form"><select class="select" name="week">${weekOpts}</select><select class="select" name="roster_id">${ownerOpts}</select><input class="input" name="label" placeholder="Reason (e.g. lost a side bet)" required style="flex:1;min-width:200px"><input class="input" name="detail" placeholder="Details (optional)" style="flex:1;min-width:160px"><button class="btn btn-primary" type="submit" ${locked ? 'disabled' : ''}>Add</button></form></div>`;
  }

  // Home page: the freshest story of each kind, in a fixed order of importance, instead of the first N by date.
  function pickHeadlines(arts, n) {
    const order = ['preview', 'recap', 'standings', 'shotgun', 'rivalry', 'trade', 'waiver', 'feud', 'column', 'analytics', 'offseason'];
    const picked = [];
    for (const type of order) {
      const a = arts.find((x) => x.type === type);
      if (a) picked.push(a);
    }
    for (const a of arts) if (picked.length < n && !picked.includes(a)) picked.push(a);
    return picked.slice(0, n);
  }

  // Where check-offs live: Redis (durable), local SQLite (durable on this machine), or ephemeral /tmp (lost on restart).
  function storageBadge(p) {
    if (p === 'redis') return '<span class="storage">storage: redis</span>';
    if (p === 'sqlite') return '<span class="storage">storage: local</span>';
    if (p === 'ephemeral') return '<span class="storage warn">storage: temporary (check-offs won\'t persist)</span>';
    return `<span class="storage">storage: ${esc(p || 'unknown')}</span>`;
  }

  function bylineOf(a) {
    const r = a.reporter;
    return r ? `By ${esc(r.name)} · ${esc(r.outlet)}` : `By ${esc(a.byline)}`;
  }

  function mastheadCard() {
    const rs = state.data.reporters || [];
    const bs = state.data.beat_reporters || [];
    const staff = rs.length ? `<div class="card section masthead"><div class="card-h"><h2>Masthead</h2><small>${rs.length} reporters, no two alike</small></div>
      <ul class="clean masthead-list">${rs.map((r) => `<li><div class="m-name">${esc(r.name)}</div><div class="m-outlet">${esc(r.outlet)}</div><div class="m-bio">${esc(r.bio)}</div>${r.known_for ? `<div class="m-known"><span class="dim">Known for:</span> ${esc(r.known_for)}</div>` : ''}</li>`).join('')}</ul></div>` : '';
    const beat = bs.length ? `<div class="card section masthead"><div class="card-h"><h2>Team beat</h2><small>${bs.length} reporters, one per team, all of them tough on the owner</small></div>
      <ul class="clean masthead-list">${bs.map((r) => `<li><div class="m-name">${esc(r.name)}</div><div class="m-outlet">${esc(r.outlet)}</div><div class="m-bio">${esc(r.bio)}</div>${r.team ? `<div class="m-known"><span class="dim">Covers:</span> ${teamLink(r.team.roster_id)}</div>` : ''}</li>`).join('')}</ul></div>` : '';
    return staff + beat;
  }

  function articleCard(a, open = false) {
    return `<article class="card article type-${esc(a.type)} ${open ? 'open' : ''}" id="art-${esc(a.id)}">
      <div class="kicker"><span>${esc(a.type === 'beat' ? 'team beat' : a.type)}</span><span>·</span><span>Week ${a.week}</span>${a.source === 'desk' ? '<span class="desk-mark" title="Written by hand at the editorial desk">✎ Desk</span>' : ''}${a.tags.includes('rivalry') ? '<span class="badge bad">rivalry</span>' : ''}</div>
      <h3>${esc(a.headline)}</h3><div class="dek">${esc(a.dek)}</div><div class="byline">${bylineOf(a)} · ${a.teams.map((rid) => teamLink(rid)).join(', ')}</div>
      <div class="body">${a.body.map((p) => `<p>${esc(p)}</p>`).join('')}</div>
      <span class="more" data-more>${open ? 'Collapse' : 'Read more'}</span></article>`;
  }

  function viewNews(articleId) {
    const d = state.data;
    if (articleId) {
      const a = d.articles.find((x) => x.id === articleId);
      if (!a) return '<div class="error">Article not found.</div>';
      const related = d.articles.filter((x) => x.id !== a.id && x.teams.some((t) => a.teams.includes(t))).slice(0, 6);
      return `<div class="back"><a href="#/news">← All news</a></div>${articleCard(a, true)}<div class="card section"><div class="card-h"><h2>Related</h2></div><ul class="clean headlines">${related.map((x) => `<li><div class="kicker">${esc(x.type)} · week ${x.week}</div><a href="#/news/${esc(x.id)}">${esc(x.headline)}</a></li>`).join('') || '<li class="empty">—</li>'}</ul></div>`;
    }
    // The 10 weekly team reports are their own filter: they never crowd the other stories out of the main list.
    const beat = d.articles.filter((a) => a.type === 'beat'), main = d.articles.filter((a) => a.type !== 'beat');
    const inBeat = state.newsFilter === 'beat' && beat.length > 0;
    const types = ['all', ...new Set(main.map((a) => a.type)), ...(beat.length ? ['beat'] : [])];
    const weeks = ['all', ...new Set((inBeat ? beat : main).map((a) => a.week))];
    let arts = inBeat ? beat : state.newsFilter === 'all' || state.newsFilter === 'beat' ? main : main.filter((a) => a.type === state.newsFilter);
    if (state.newsWeek !== 'all') arts = arts.filter((a) => String(a.week) === String(state.newsWeek));
    if (inBeat && state.newsTeam !== 'all') arts = arts.filter((a) => a.teams.includes(Number(state.newsTeam)));
    const beatTeams = (d.beat_reporters || []).map((b) => b.team).filter(Boolean);
    const teamSelect = inBeat ? `<select class="select" id="news-team"><option value="all">All teams</option>${beatTeams.map((t) => `<option value="${esc(t.roster_id)}" ${String(state.newsTeam) === String(t.roster_id) ? 'selected' : ''}>${esc(t.name)}</option>`).join('')}</select>` : '';
    return `
      ${pageHead('05 / News', 'League News', 'All of it fake. Most of it accurate.',
        `<select class="select" id="news-week">${weeks.map((w) => `<option value="${esc(w)}" ${String(state.newsWeek) === String(w) ? 'selected' : ''}>${w === 'all' ? 'All weeks' : `Week ${esc(w)}`}</option>`).join('')}</select>${teamSelect}`)}
      <div class="chips section">${types.map((t) => `<span class="chip ${state.newsFilter === t ? 'active' : ''}" data-news="${esc(t)}">${t === 'beat' ? `team beat (${beat.length})` : esc(t)}</span>`).join('')}</div>
      ${inBeat ? '<p class="muted beat-note">One beat reporter per team, every week, and every one of them is hard on the owner.</p>' : ''}
      <div class="grid" style="gap:12px">${arts.map((a) => articleCard(a)).join('') || '<div class="empty">No stories match.</div>'}</div>
      ${mastheadCard()}`;
  }

  function viewRivalries() {
    const d = state.data;
    const cards = d.rivalries.map((rv) => {
      const [a, b] = rv.owners; const ta = team(a), tb = team(b);
      const h2h = ta.h2h[b] || { w: 0, l: 0, t: 0 };
      const meetings = d.games.filter((g) => (g.a === a && g.b === b) || (g.a === b && g.b === a));
      const next = Object.entries(d.schedule).flatMap(([w, gs]) => gs.filter((g) => (g.a === a && g.b === b) || (g.a === b && g.b === a)).map(() => Number(w)))[0];
      const arts = d.articles.filter((x) => x.teams.includes(a) && x.teams.includes(b)).slice(0, 5);
      return `<div class="card">
        <div class="card-h"><h2>${esc(rv.name)}</h2>${next ? `<span class="badge bad">Next: week ${next}</span>` : ''}</div>
        ${rv.backstory ? `<p class="muted" style="margin-top:0">${esc(rv.backstory)}</p>` : ''}
        <div class="grid grid-2" style="gap:10px;margin-bottom:10px">
          <div>${teamCell(a, { sub: 'record' })}<div class="dim" style="margin-top:4px">${ordinal(ta.rank)} · ${fmt(ta.avg, 1)} avg · ${pct(d.playoffs.teams[a].playoff_pct)} playoffs</div></div>
          <div>${teamCell(b, { sub: 'record' })}<div class="dim" style="margin-top:4px">${ordinal(tb.rank)} · ${fmt(tb.avg, 1)} avg · ${pct(d.playoffs.teams[b].playoff_pct)} playoffs</div></div>
        </div>
        <dl class="kv"><dt>Head to head</dt><dd><b>${esc(ta.name)} ${h2h.w}-${h2h.l}${h2h.t ? `-${h2h.t}` : ''}</b> this season</dd>
          ${meetings.map((g) => `<dt>Week ${g.week}</dt><dd>${g.winner == null ? 'Tie' : `${esc(team(g.winner).name)} won`} ${fmt(Math.max(g.a_pts, g.b_pts))}–${fmt(Math.min(g.a_pts, g.b_pts))}</dd>`).join('')}</dl>
        ${arts.length ? `<h3 style="margin-top:12px">Coverage</h3><ul class="clean headlines">${arts.map((x) => `<li><div class="kicker">${esc(x.type)} · week ${x.week}</div><a href="#/news/${esc(x.id)}">${esc(x.headline)}</a></li>`).join('')}</ul>` : ''}
      </div>`;
    }).join('');
    // Auto "heat" pairs: adjacent teams around the playoff cut.
    const cut = d.league.playoff_teams;
    const hot = [];
    for (let i = Math.max(0, cut - 3); i < Math.min(d.standings.length - 1, cut + 2); i++) hot.push([d.standings[i], d.standings[i + 1]]);
    const hotCards = hot.map(([a, b]) => `<div class="card"><div class="card-h"><h3>${esc(team(a).name)} vs. ${esc(team(b).name)}</h3><span class="badge warn">${ordinal(team(a).rank)} / ${ordinal(team(b).rank)}</span></div><div class="dim">${team(a).record} vs ${team(b).record} · ${fmt(Math.abs(team(a).pf - team(b).pf), 1)} PF apart · playoff odds ${pct(d.playoffs.teams[a].playoff_pct)} vs ${pct(d.playoffs.teams[b].playoff_pct)}</div></div>`).join('');
    return `
      ${pageHead('06 / Rivalries', 'Rivalries', 'The newsroom writes hype pieces when rivals meet.')}
      ${cards ? `<div class="grid grid-2 section">${cards}</div>` : '<div class="card section"><div class="empty">No rivalries configured yet. Add them to config.yaml, then hit ↻.</div></div>'}
      <div class="section-head"><div class="eyebrow">Heat</div><h2>Fighting for the cut line</h2><p class="lead">Teams stacked around the ${ordinal(cut)} seed, where every week is a grudge match whether they like it or not.</p></div>
      <div class="grid grid-3 section">${hotCards}</div>`;
  }

  // ---------- player network ----------
  // Lazy: /api/network is only fetched when #/network is opened. The graph is hand-rolled SVG with a small
  // force simulation (teams = big nodes, players = small nodes coloured by position) that stops once settled.
  const NET_POS = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF'];
  const netPos = (p) => NET_POS.includes(p) ? p : 'X';
  const netNet = () => state.net || (state.net = { data: null, loading: false, error: null, minTeams: 2, pos: 'all', q: '', sel: null, raf: 0 });
  const wkRange = (s) => s.brief ? 'Offseason / under a week' : s.start_week === s.end_week ? `Wk ${s.start_week}` : `Wk ${s.start_week}–${s.end_week}`;
  const VIA_LABEL = { draft: 'Drafted', trade: 'Trade', waiver: 'Waiver', free_agent: 'Free agent', kept: 'Kept', inherited: 'Inherited', unknown: 'Unknown' };

  function viewNetwork() {
    const n = netNet();
    const head = pageHead('07 / Network', 'Player network', 'Who has been on whose roster, across every season of the league. Big circles are teams, dots are players coloured by position; a line means the player has spent time on that team. Players on one team only are hidden by default.');
    if (!n.data) {
      if (n.error) return head + `<div class="error">Couldn't load the network: ${esc(n.error)} <button type="button" class="btn" data-net-retry>Retry</button></div>`;
      if (!n.loading) {
        n.loading = true;
        api('/api/network').then((d) => { n.data = d; }).catch((e) => { n.error = e.message || 'request failed'; })
          .finally(() => { n.loading = false; if (location.hash.startsWith('#/network')) route(); });
      }
      return head + '<div class="loading">Building the player network…</div>';
    }
    const d = n.data;
    const poss = NET_POS.filter((p) => d.players.some((x) => x.position === p));
    const opt = (v, label, cur) => `<option value="${esc(v)}" ${String(cur) === String(v) ? 'selected' : ''}>${esc(label)}</option>`;
    const skipped = (d.skipped || []).length ? `<p class="dim">Skipped seasons that failed to load: ${esc(d.skipped.map((x) => x.season).join(', '))}.</p>` : '';
    return `${head}
      <div class="card net-card section">
        <div class="net-controls">
          <label>Min teams <select class="select" id="net-min">${opt(2, '2+ teams', n.minTeams)}${opt(3, '3+ teams', n.minTeams)}${opt(4, '4+ teams', n.minTeams)}</select></label>
          <label>Position <select class="select" id="net-pos">${opt('all', 'All positions', n.pos)}${poss.map((p) => opt(p, p, n.pos)).join('')}</select></label>
          <label class="net-search">Player <input class="input" id="net-q" type="search" placeholder="Search name" value="${esc(n.q)}" autocomplete="off"></label>
        </div>
        <div class="net-legend">${poss.map((p) => `<span><i class="net-sw pos-${p}"></i>${esc(p)}</span>`).join('')}<span class="dim" id="net-count"></span></div>
        <div id="net-graph" class="net-graph"></div>
      </div>
      <div class="card net-card section" id="net-panel"></div>
      <div class="section-head"><div class="eyebrow">Most traveled</div><h2>Players who've seen the most teams</h2></div>
      <div class="card net-card section">${netTravelTable(d)}</div>
      <div class="section-head"><div class="eyebrow">Shared players</div><h2>Team by team</h2><p class="lead">Each cell counts the players who have been on both teams at some point.</p></div>
      <div class="card net-card section">${netMatrix(d)}</div>
      ${skipped}`;
  }

  function netTravelTable(d) {
    const top = d.players.slice(0, 15);
    const rows = top.map((p, i) => `<tr class="net-row" data-net-player="${esc(p.player_id)}" tabindex="0"><td class="num">${i + 1}</td><td><b>${esc(p.name)}</b></td><td><span class="badge">${esc(p.position)}</span></td><td class="num" data-label="Teams">${p.team_count}</td><td class="num" data-label="Weeks">${p.total_weeks}</td></tr>`).join('');
    return `<div class="table-wrap"><table class="net-table"><thead><tr><th class="num">#</th><th>Player</th><th>Pos</th><th class="num">Teams</th><th class="num">Weeks rostered</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function netMatrix(d) {
    const owners = {};
    d.edges.forEach((e) => { (owners[e.player_id] = owners[e.player_id] || []).push(e.owner_id); });
    const shared = {};
    Object.values(owners).forEach((os) => os.forEach((a) => os.forEach((b) => { if (a !== b) { shared[a + '|' + b] = (shared[a + '|' + b] || 0) + 1; } })));
    const max = Math.max(1, ...Object.values(shared));
    const ts = d.teams;
    const head = ts.map((t) => `<th class="num" title="${esc(t.owner)}">${esc(t.owner.slice(0, 4))}</th>`).join('');
    const rows = ts.map((a) => `<tr><th class="net-rowh">${esc(a.owner)}</th>${ts.map((b) => {
      if (a.owner_id === b.owner_id) return '<td class="num net-self">·</td>';
      const v = shared[a.owner_id + '|' + b.owner_id] || 0;
      return `<td class="num" style="background:color-mix(in srgb, var(--accent) ${Math.round((v / max) * 55)}%, transparent)" title="${esc(a.owner)} & ${esc(b.owner)}: ${v}">${v}</td>`;
    }).join('')}</tr>`).join('');
    return `<div class="table-wrap"><table class="net-matrix"><thead><tr><th></th>${head}</tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function netPanelHtml() {
    const n = netNet(), d = n.data, sel = n.sel;
    if (!sel) return '<div class="empty">Click a team or a player in the graph (or a row below) to see how they connect.</div>';
    if (sel.type === 'player') {
      const p = d.players.find((x) => x.player_id === sel.id);
      if (!p) return '<div class="empty">Unknown player.</div>';
      const st = d.stints.filter((s) => s.player_id === sel.id).sort((a, b) => a.season.localeCompare(b.season) || a.start_week - b.start_week || (b.brief ? 1 : 0) - (a.brief ? 1 : 0));
      const rows = st.map((s) => `<tr><td data-label="Season">${esc(s.season)}</td><td data-label="Weeks">${esc(wkRange(s))}${s.brief ? '' : ` <span class="dim">(${s.weeks})</span>`}</td><td data-label="Team"><b>${esc(s.owner)}</b> <small>${esc(s.team_name)}</small></td><td data-label="How"><span class="badge ${s.acquired_via === 'unknown' ? '' : 'accent'}">${esc(VIA_LABEL[s.acquired_via] || s.acquired_via)}</span></td></tr>`).join('');
      return `<div class="card-h"><h3>${esc(p.name)} <span class="badge">${esc(p.position)}</span></h3><span class="dim">${p.team_count} team${p.team_count === 1 ? '' : 's'} · ${p.total_weeks} weeks</span></div>
        <div class="table-wrap"><table class="net-table"><thead><tr><th>Season</th><th>Weeks</th><th>Team</th><th>Acquired</th></tr></thead><tbody>${rows}</tbody></table></div>`;
    }
    const t = d.teams.find((x) => x.owner_id === sel.id);
    if (!t) return '<div class="empty">Unknown team.</div>';
    const pl = netVisible().filter((p) => d.edges.some((e) => e.owner_id === t.owner_id && e.player_id === p.player_id)).sort((a, b) => b.team_count - a.team_count || a.name.localeCompare(b.name));
    const shown = pl.slice(0, 40);
    return `<div class="card-h"><h3>${esc(t.owner)} <small>${esc(t.team_name)}</small></h3><span class="dim">${esc(t.seasons.join(', '))} · ${t.players_count} players overall</span></div>
      <p class="dim">${pl.length} player${pl.length === 1 ? '' : 's'} in the current graph${pl.length > shown.length ? ` (first ${shown.length} shown)` : ''}. Click one for details.</p>
      <div class="net-pills">${shown.map((p) => `<button type="button" class="net-pill" data-net-player="${esc(p.player_id)}"><i class="net-sw pos-${netPos(p.position)}"></i>${esc(p.name)}</button>`).join('')}</div>`;
  }

  function netVisible() {
    const n = netNet(), q = n.q.trim().toLowerCase();
    return n.data.players.filter((p) => p.team_count >= n.minTeams && (n.pos === 'all' || p.position === n.pos) && (!q || p.name.toLowerCase().includes(q)));
  }

  function netMount() {
    const n = netNet(), d = n.data;
    if (!d) return;
    cancelAnimationFrame(n.raf);
    const host = $('#net-graph'), panel = $('#net-panel');
    if (!host || !panel) return;
    panel.innerHTML = netPanelHtml();
    const players = netVisible();
    $('#net-count').textContent = `${players.length} player${players.length === 1 ? '' : 's'} shown`;
    if (!players.length) { host.innerHTML = '<div class="empty">No players match these filters.</div>'; return; }
    const W = Math.max(300, Math.min(1100, host.clientWidth || 900)), H = W < 560 ? Math.round(W * 1.3) : Math.round(W * 0.62);
    const small = W < 560, R = small ? 14 : 19, PR = small ? 3.6 : 4.2;
    const keep = new Set(players.map((p) => p.player_id));
    const edges = d.edges.filter((e) => keep.has(e.player_id));
    const ids = new Set(edges.map((e) => e.owner_id));
    const teams = d.teams.map((t) => ({ ...t, kind: 'team' }));   // every team gets a node; it just sits idle if unconnected
    const idx = {}, nodes = [];
    const hash = (str) => { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967296; };
    teams.forEach((t, i) => {
      const a = (i / teams.length) * Math.PI * 2 - Math.PI / 2;
      t.hx = W / 2 + Math.cos(a) * (W / 2 - R * 2.6); t.hy = H / 2 + Math.sin(a) * (H / 2 - R * 2.8);
      t.x = t.hx; t.y = t.hy; t.vx = t.vy = 0; t.r = R; idx[t.owner_id] = nodes.length; nodes.push(t);
    });
    players.forEach((p) => {
      const q = { ...p, kind: 'player', r: PR, vx: 0, vy: 0, x: W / 2 + (hash(p.player_id) - 0.5) * W * 0.4, y: H / 2 + (hash(p.player_id + 'y') - 0.5) * H * 0.4 };
      idx[p.player_id] = nodes.length; nodes.push(q);
    });
    const links = edges.map((e) => ({ s: idx[e.player_id], t: idx[e.owner_id], e }));
    const pad = R + 6;
    let alpha = 1, ticks = 0;
    const tick = () => {
      const N = nodes.length;
      for (let i = 0; i < N; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < N; j++) {
          const b = nodes[j];
          let dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy;
          const min = (a.kind === 'team' || b.kind === 'team') ? (a.kind === b.kind ? 140 : 50) : 46;
          if (d2 > min * min * 4) continue;
          if (d2 < 0.01) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = 0.5; }
          const dist = Math.sqrt(d2), f = ((a.kind === b.kind && a.kind === 'team' ? 900 : 260) / d2) * alpha;
          const fx = (dx / dist) * f, fy = (dy / dist) * f;
          a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
        }
      }
      links.forEach((l) => {
        const a = nodes[l.s], b = nodes[l.t];
        const dx = b.x - a.x, dy = b.y - a.y, dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const rest = small ? 50 : 70, k = 0.03 * alpha * (dist - rest) / dist;
        a.vx += dx * k; a.vy += dy * k; b.vx -= dx * k * 0.08; b.vy -= dy * k * 0.08;
      });
      nodes.forEach((o) => {
        if (o.kind === 'team') { o.vx += (o.hx - o.x) * 0.08; o.vy += (o.hy - o.y) * 0.08; }
        else { o.vx += (W / 2 - o.x) * 0.002 * alpha; o.vy += (H / 2 - o.y) * 0.002 * alpha; }
        o.vx *= 0.82; o.vy *= 0.82;
        o.x = Math.max(pad, Math.min(W - pad, o.x + o.vx)); o.y = Math.max(pad, Math.min(H - pad, o.y + o.vy));
      });
      alpha *= 0.985; ticks++;
    };
    for (let i = 0; i < 160; i++) tick();   // settle most of the way before the first paint

    const teamSvg = nodes.filter((o) => o.kind === 'team').map((t) => `<g class="net-team${ids.has(t.owner_id) ? '' : ' idle'}" data-net-team="${esc(t.owner_id)}" tabindex="0" role="button" aria-label="${esc(t.owner)}"><title>${esc(t.owner)} · ${esc(t.team_name)} · ${t.players_count} players</title><circle r="${R}"/><text class="net-ini" dy="0.35em">${esc(initials(t.owner))}</text><text class="net-lab" dy="${R + 12}">${esc(t.owner)}</text></g>`).join('');
    const playerSvg = nodes.filter((o) => o.kind === 'player').map((p) => `<circle class="net-p pos-${netPos(p.position)}" data-net-player="${esc(p.player_id)}" r="${PR}"><title>${esc(p.name)} · ${esc(p.position)} · ${p.team_count} teams</title></circle>`).join('');
    const edgeSvg = links.map(() => '<line class="net-e"/>').join('');
    host.innerHTML = `<svg class="net-svg" viewBox="0 0 ${W} ${H}" role="group" aria-label="Player network graph"><g class="net-edges">${edgeSvg}</g><g class="net-players">${playerSvg}</g><g class="net-teams">${teamSvg}</g></svg>`;
    const svg = $('svg', host);
    const edgeEls = [...svg.querySelectorAll('.net-e')];
    const teamEls = {}, playerEls = {};
    svg.querySelectorAll('[data-net-team]').forEach((el) => { teamEls[el.dataset.netTeam] = el; });
    svg.querySelectorAll('[data-net-player]').forEach((el) => { playerEls[el.dataset.netPlayer] = el; });
    const draw = () => {
      links.forEach((l, i) => { const a = nodes[l.s], b = nodes[l.t], el = edgeEls[i]; el.setAttribute('x1', a.x.toFixed(1)); el.setAttribute('y1', a.y.toFixed(1)); el.setAttribute('x2', b.x.toFixed(1)); el.setAttribute('y2', b.y.toFixed(1)); });
      nodes.forEach((o) => {
        if (o.kind === 'team') teamEls[o.owner_id].setAttribute('transform', `translate(${o.x.toFixed(1)},${o.y.toFixed(1)})`);
        else { const el = playerEls[o.player_id]; el.setAttribute('cx', o.x.toFixed(1)); el.setAttribute('cy', o.y.toFixed(1)); }
      });
    };
    const highlight = () => {
      const sel = n.sel;
      let tOn = null, pOn = null, eOn = null;
      if (sel) {
        tOn = new Set(); pOn = new Set();
        if (sel.type === 'team') { tOn.add(sel.id); eOn = (e) => e.owner_id === sel.id; }
        else { pOn.add(sel.id); eOn = (e) => e.player_id === sel.id; }
        edges.forEach((e) => { if (eOn(e)) { tOn.add(e.owner_id); pOn.add(e.player_id); } });
      }
      svg.classList.toggle('has-sel', !!sel);
      Object.entries(teamEls).forEach(([id, el]) => el.classList.toggle('on', !!tOn && tOn.has(id)));
      Object.entries(playerEls).forEach(([id, el]) => el.classList.toggle('on', !!pOn && pOn.has(id)));
      links.forEach((l, i) => edgeEls[i].classList.toggle('on', !!sel && eOn(l.e)));
    };
    n.highlight = highlight;
    draw(); highlight();
    const step = () => {
      if (!document.body.contains(svg)) return;
      for (let i = 0; i < 3; i++) tick();
      draw();
      if (alpha > 0.03 && ticks < 420) n.raf = requestAnimationFrame(step);
    };
    n.raf = requestAnimationFrame(step);
  }

  function netSelect(type, id) {
    const n = netNet();
    n.sel = (n.sel && n.sel.type === type && n.sel.id === id) ? null : { type, id };
    const panel = $('#net-panel');
    if (panel) panel.innerHTML = netPanelHtml();
    if (n.highlight) n.highlight();
  }

  // Delegated handlers (the page is re-rendered by route(), so they live on #app once).
  app.addEventListener('click', (e) => {
    const n = state.net;
    if (n && e.target.closest('[data-net-retry]')) { n.error = null; route(); return; }
    if (!n || !$('#net-panel')) return;
    const t = e.target.closest('[data-net-team]'), p = e.target.closest('[data-net-player]');
    if (t) netSelect('team', t.dataset.netTeam);
    else if (p) { const was = n.sel; netSelect('player', p.dataset.netPlayer); if (n.sel && was && was.id === n.sel.id) return; if (p.closest('.net-table, .net-pills')) $('#net-panel').scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
  });
  app.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const el = e.target.closest('[data-net-team], tr[data-net-player]');
    if (el && state.net) { e.preventDefault(); el.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
  });
  app.addEventListener('input', (e) => {
    if (e.target.id !== 'net-q') return;
    const n = netNet(); n.q = e.target.value;
    clearTimeout(n.qt); n.qt = setTimeout(netMount, 180);
  });
  app.addEventListener('change', (e) => {
    const n = netNet();
    if (e.target.id === 'net-min') { n.minTeams = Number(e.target.value); netMount(); }
    if (e.target.id === 'net-pos') { n.pos = e.target.value; netMount(); }
  });

  // ---------- power rankings (our own player-value model) ----------
  // Lazy: /api/power-rankings is only fetched when #/power is opened; a failure shows Retry and is never retried
  // automatically. Tabs / team selection / filters re-render only their own container (no scroll jump).
  const POW_TABS = [['combined', 'Combined'], ['QB', 'QB'], ['RB', 'RB'], ['WR', 'WR'], ['TE', 'TE'], ['picks', 'Picks']];
  const POW_CHIPS = [['QB', 'QB'], ['RB', 'RB'], ['WR', 'WR'], ['TE', 'TE'], ['picks', 'Picks']];
  const powSt = () => state.pow || (state.pow = { data: null, loading: false, error: null, sort: 'combined', sel: null, pos: 'all', q: '', qt: 0 });
  const powRk = (r, n) => `<span class="rk ${r <= 3 ? 'rk-top' : r > n - 3 ? 'rk-low' : ''}">${esc(r)}</span>`;
  const powTeamCell = (t) => `<span class="team-cell">${avatar(t)}<span class="names"><b>${esc(t.name)}</b><small>${esc(t.team_name)}</small></span></span>`;

  function viewPower() {
    const p = powSt();
    const head = pageHead('08 / Power', 'Power rankings', 'Every team ranked by what its roster and its future rookie picks are worth in our own player-value model, not by record. Click a team to see its players and picks.');
    if (!p.data) {
      if (p.error) return head + `<div class="error">Couldn't load the power rankings: ${esc(p.error)} <button type="button" class="btn" data-pow-retry>Retry</button></div>`;
      if (!p.loading) {
        p.loading = true;
        api('/api/power-rankings').then((d) => { p.data = d; }).catch((e) => { p.error = e.message || 'request failed'; })
          .finally(() => { p.loading = false; if (location.hash.startsWith('#/power')) route(); });
      }
      return head + '<div class="loading">Valuing every player in the league…</div>';
    }
    const d = p.data, c = d.constants || {}, cv = d.curve.values || {};
    const opt = (v, label, cur) => `<option value="${esc(v)}" ${String(cur) === String(v) ? 'selected' : ''}>${esc(label)}</option>`;
    const skipped = (d.skipped || []).length ? `<p class="dim">Some data failed to load and was left out: ${esc(d.skipped.map((x) => x.what).join(', '))}.</p>` : '';
    const w = c.season_weights || [], rr = c.replacement_rank || {};
    const curveNote = d.curve.source === 'fit'
      ? `fitted to ${d.curve.samples} picks from this league's own past rookie drafts`
      : 'estimated from default values, because there is not enough rookie-draft history yet';
    return `${head}
      <div class="card pow-card section"><div id="pow-main">${powMainHtml()}</div></div>
      <div class="section-head"><div class="eyebrow">Players</div><h2>Player rankings</h2><p class="lead">The ${d.players.length} most valuable rostered players, from the same model. Filter by position or search by name.</p></div>
      <div class="card pow-card section">
        <div class="net-controls">
          <label>Position <select class="select" id="pow-pos">${opt('all', 'All positions', p.pos)}${['QB', 'RB', 'WR', 'TE'].map((x) => opt(x, x, p.pos)).join('')}</select></label>
          <label class="net-search">Player <input class="input" id="pow-q" type="search" placeholder="Search name" value="${esc(p.q)}" autocomplete="off"></label>
        </div>
        <div id="pow-players">${powPlayersHtml()}</div>
      </div>
      <div class="section-head"><div class="eyebrow">Method</div><h2>How this is calculated</h2></div>
      <div class="card pow-card pow-how section">
        <ol>
          <li><b>Production.</b> Each player's points per game, scored with this league's own scoring settings (TE premium, first-down bonuses, interception penalty and so on) from this season and the two before, weighted ${esc(w.map((x) => Math.round(x * 100) + '%').join(' / '))}. A season counts less the fewer games he played, and everyone is pulled a little toward a replacement-level player (worth about ${esc(c.prior_games)} games) so a hot week or two does not fool the model.</li>
          <li><b>Replacement level.</b> The points per game of a player you could pick up for free: the ${esc(rr.QB)}th best QB, ${esc(rr.RB)}th RB, ${esc(rr.WR)}th WR and ${esc(rr.TE)}th TE in the NFL (${esc(Object.entries(d.replacement || {}).map(([k, v]) => `${k} ${v}`).join(', '))} points per game right now). The QB bar is deeper because this is a superflex league where teams stash several QBs. Only the points above that level count.</li>
          <li><b>Age.</b> The current season always counts in full. Value is multiplied by how many good seasons are left over the next ${esc(c.longevity_years)} years: later seasons are discounted by age, and each year further out counting ${esc(Math.round((c.longevity_discount || 0) * 100))}% as much as the one before. Production holds until a prime age (RB ${esc((c.prime_end || {}).RB)}, WR ${esc((c.prime_end || {}).WR)}, TE ${esc((c.prime_end || {}).TE)}, QB ${esc((c.prime_end || {}).QB)}) and fades to nothing at ${esc((c.cliff || {}).RB)} / ${esc((c.cliff || {}).WR)} / ${esc((c.cliff || {}).TE)} / ${esc((c.cliff || {}).QB)}.</li>
          <li><b>Young players.</b> Rookies and second- and third-year players who were drafted in this league are blended with what their draft slot has been worth: the fewer games they have played, the more the draft slot counts. The blend can only raise a player's value, never lower it.</li>
          <li><b>Draft picks.</b> A pick is worth what a player taken at that slot has turned out to be worth (${esc(curveNote)}): about ${esc(cv['1'])} for the 1st overall pick, ${esc(cv['10'])} for the 10th, ${esc(cv['20'])} for the 20th and ${esc(cv['40'])} for the last pick of round 4. Next year's draft order assumes the worst teams pick first; later years use the middle of each round. Picks a year further away are worth ${esc(Math.round((c.pick_year_discount || 0) * 100))}% as much per year, and traded picks count for whoever owns them now.</li>
          <li><b>Teams.</b> A team's value at a position is the sum of its rostered players' values there (taxi and reserve included); players plus picks gives the combined number. Ranks run 1 (best) to ${d.teams.length}.</li>
        </ol>
      </div>
      ${skipped}`;
  }

  function powMainHtml() {
    const p = powSt(), d = p.data, n = d.teams.length;
    const key = p.sort;
    const ordered = d.teams.slice().sort((a, b) => (b.values[key] - a.values[key]) || (a.ranks.combined - b.ranks.combined));
    const posCol = ['QB', 'RB', 'WR', 'TE'].includes(key);
    const hl = (k) => (key === k ? ' sorted' : '');
    const rows = ordered.map((t, i) => `<tr class="pow-row ${p.sel === t.roster_id ? 'sel' : ''}" data-pow-team="${t.roster_id}" tabindex="0" aria-expanded="${p.sel === t.roster_id}">
        <td class="pw2-rank"><span class="rank ${i === 0 ? 'top' : ''}">${i + 1}</span></td>
        <td class="pw2-team">${powTeamCell(t)}</td>
        <td class="num pw2-comb${hl('combined')}" data-label="Combined">${fmt(t.values.combined, 1)}</td>
        <td class="num pw2-pl${hl('players')}" data-label="Players">${fmt(t.values.players, 1)}</td>
        <td class="num pw2-pk${hl('picks')}" data-label="Picks">${fmt(t.values.picks, 1)}</td>
        ${posCol ? `<td class="num pw2-x sorted" data-label="${esc(key)}">${fmt(t.values[key], 1)}</td>` : ''}
        ${POW_CHIPS.map(([k, l]) => `<td class="pw2-c${hl(k)}" data-label="${esc(l)}">${powRk(t.ranks[k], n)}</td>`).join('')}
      </tr>`).join('');
    const tabs = POW_TABS.map(([k, l]) => `<button type="button" class="pow-chip ${key === k ? 'active' : ''}" data-pow-sort="${k}" aria-pressed="${key === k}">${esc(l)}</button>`).join('');
    return `<div class="card-h"><h2>Team rankings</h2><small>Season ${esc(d.season)}</small></div>
      <div class="chips pow-tabs" role="group" aria-label="Sort teams by">${tabs}</div>
      <div class="table-wrap power-wrap"><table class="pow-table ${posCol ? 'has-x' : ''}"><thead><tr><th class="pw2-rank">#</th><th>Team</th><th class="num">Combined</th><th class="num">Players</th><th class="num">Picks</th>${posCol ? `<th class="num">${esc(key)}</th>` : ''}${POW_CHIPS.map(([k, l]) => `<th class="pw2-c">${esc(l)}<span class="pw2-sub"> rank</span></th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>
      <div id="pow-detail" class="pow-detail">${powDetailHtml()}</div>`;
  }

  function powDetailHtml() {
    const p = powSt(), d = p.data;
    const t = d.teams.find((x) => x.roster_id === p.sel);
    if (!t) return '<p class="dim pow-hint">Select a team above to see its top players at each position and every pick it owns.</p>';
    const mine = d.players.filter((x) => x.roster_id === t.roster_id);
    const blocks = ['QB', 'RB', 'WR', 'TE'].map((pos) => {
      const ps = mine.filter((x) => x.position === pos);
      const list = ps.slice(0, 6).map((x) => `<li><span class="pw-nm">${esc(x.name)}</span><span class="dim">${x.age == null ? '' : esc(x.age)}</span><b class="num">${fmt(x.value, 1)}</b></li>`).join('');
      return `<div class="pow-block"><div class="pow-bh"><b>${esc(pos)}</b><span class="dim">rank ${esc(t.ranks[pos])} · ${fmt(t.values[pos], 1)}</span></div>
        ${list ? `<ul>${list}</ul>` : '<div class="dim">No valued players</div>'}${ps.length > 6 ? `<div class="dim pow-more">+${ps.length - 6} more</div>` : ''}</div>`;
    }).join('');
    const picks = t.picks.map((x) => `<tr><td>${esc(x.season)}</td><td class="num">${esc(x.round)}</td><td>${esc(x.original)}${x.traded ? ' <span class="badge">via trade</span>' : ''}</td><td class="num">${fmt(x.slot, 1)}</td><td class="num">${fmt(x.value, 1)}</td></tr>`).join('');
    return `<div class="pow-dh"><h3>${esc(t.name)}<small>${esc(t.team_name)}</small></h3><span class="dim">players ${fmt(t.values.players, 1)} · picks ${fmt(t.values.picks, 1)} (${t.picks.length}) · combined ${fmt(t.values.combined, 1)}</span></div>
      <div class="pow-blocks">${blocks}</div>
      <div class="pow-bh pow-picks-h"><b>Pick inventory</b><span class="dim">rank ${esc(t.ranks.picks)} · ${t.picks.length} picks</span></div>
      <div class="table-wrap"><table class="pow-picks"><thead><tr><th>Draft</th><th class="num">Rd</th><th>Original team</th><th class="num">Proj. slot</th><th class="num">Value</th></tr></thead><tbody>${picks || '<tr><td colspan="5" class="dim">No picks</td></tr>'}</tbody></table></div>`;
  }

  function powPlayersHtml() {
    const p = powSt(), q = p.q.trim().toLowerCase();
    const list = p.data.players.filter((x) => (p.pos === 'all' || x.position === p.pos) && (!q || String(x.name).toLowerCase().includes(q))).slice(0, 50);
    if (!list.length) return '<p class="dim">No players match.</p>';
    const rows = list.map((x) => `<tr><td class="num">${x.rank}</td><td class="pw3-pl"><b>${esc(x.name)}</b><small>${esc([x.nfl_team, x.owner].filter(Boolean).join(' · '))}</small></td><td><span class="badge">${esc(x.position)}</span></td><td class="num">${x.age == null ? '—' : esc(x.age)}</td><td class="num">${fmt(x.value, 1)}</td><td class="num">${esc(x.position)}${x.pos_rank}</td></tr>`).join('');
    return `<div class="table-wrap"><table class="pow-players"><thead><tr><th class="num">#</th><th>Player</th><th>Pos</th><th class="num">Age</th><th class="num">Value</th><th class="num">Pos rank</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function powRerender(focusTeam) {
    const main = $('#pow-main');
    if (!main) return;
    main.innerHTML = powMainHtml();
    if (focusTeam != null) { const r = $(`[data-pow-team="${focusTeam}"]`); if (r) r.focus({ preventScroll: true }); }
  }

  app.addEventListener('click', (e) => {
    const p = state.pow;
    if (!p) return;
    if (e.target.closest('[data-pow-retry]')) { p.error = null; route(); return; }
    if (!p.data || !$('#pow-main')) return;
    const sort = e.target.closest('[data-pow-sort]');
    if (sort) { p.sort = sort.dataset.powSort; powRerender(); return; }
    const row = e.target.closest('[data-pow-team]');
    if (row) {
      const id = Number(row.dataset.powTeam);
      p.sel = p.sel === id ? null : id;
      powRerender(id);
      if (p.sel != null) { const det = $('#pow-detail'); if (det) det.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
    }
  });
  app.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const el = e.target.closest('tr[data-pow-team]');
    if (el && state.pow) { e.preventDefault(); el.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
  });
  app.addEventListener('input', (e) => {
    if (e.target.id !== 'pow-q' || !state.pow) return;
    const p = state.pow; p.q = e.target.value;
    clearTimeout(p.qt); p.qt = setTimeout(() => { const el = $('#pow-players'); if (el && p.data) el.innerHTML = powPlayersHtml(); }, 150);
  });
  app.addEventListener('change', (e) => {
    if (e.target.id !== 'pow-pos' || !state.pow) return;
    state.pow.pos = e.target.value;
    const el = $('#pow-players'); if (el && state.pow.data) el.innerHTML = powPlayersHtml();
  });

  // ---------- router ----------
  function route() {
    const hash = location.hash.replace(/^#\/?/, '');
    const [view, arg] = hash.split('/');
    document.querySelectorAll('#nav a').forEach((a) => a.classList.toggle('active', (a.dataset.view === (view || 'home'))));
    if (!state.data) return;
    let html;
    switch (view || 'home') {
      case 'standings': html = viewStandings(); break;
      case 'teams': html = arg ? viewTeam(arg) : viewTeams(); break;
      case 'playoffs': html = viewPlayoffs(); break;
      case 'shotguns': html = viewShotguns(); break;
      case 'news': html = viewNews(arg); break;
      case 'rivalries': html = viewRivalries(); break;
      case 'network': html = viewNetwork(); break;
      case 'power': html = viewPower(); break;
      default: html = viewHome();
    }
    if (state.net) { cancelAnimationFrame(state.net.raf); clearTimeout(state.net.qt); }
    if (state.pow) clearTimeout(state.pow.qt);
    app.innerHTML = html;
    if ((view || 'home') === 'network') netMount();
    window.scrollTo({ top: 0 });
  }

  // ---------- events ----------
  app.addEventListener('click', async (e) => {
    const more = e.target.closest('[data-more]');
    if (more) { const art = more.closest('.article'); art.classList.toggle('open'); more.textContent = art.classList.contains('open') ? 'Collapse' : 'Read more'; return; }
    const bt = e.target.closest('[data-beat-team]');
    if (bt) { state.newsFilter = 'beat'; state.newsTeam = bt.dataset.beatTeam; state.newsWeek = 'all'; }   // the link itself still navigates to #/news
    const chip = e.target.closest('.chip');
    if (chip) {
      if (chip.dataset.news) { state.newsFilter = chip.dataset.news; if (chip.dataset.news !== 'beat') state.newsTeam = 'all'; }
      if (chip.dataset.filter) state.shotFilter = chip.dataset.filter;
      if (chip.dataset.group) state.shotGroup = chip.dataset.group;
      route(); return;
    }
    if (e.target.id === 'pin-save') { localStorage.setItem('labrums_pin', $('#pin').value.trim()); toast('PIN saved'); route(); return; }
    const del = e.target.closest('[data-del]');
    if (del) {
      if (!confirm('Remove this manual shotgun?')) return;
      try { await api(`/api/season/${state.season}/shotguns/manual/${del.dataset.del}`, { method: 'DELETE' }); await loadSeason(state.season, true); toast('Removed'); }
      catch (err) { toast(`Error: ${err.message}`); }
    }
  });
  app.addEventListener('change', async (e) => {
    if (e.target.matches('[data-toggle]')) {
      const key = e.target.dataset.toggle; const box = e.target;
      box.disabled = true;
      try {
        const r = await api(`/api/season/${state.season}/shotguns/${encodeURIComponent(key)}/toggle`, { method: 'POST' });
        const item = state.data.shotguns.items.find((s) => s.key === key);
        if (item) { item.completed = r.completed; item.completed_at = r.completed_at; }
        const lb = state.data.shotguns.leaderboard.find((x) => x.roster_id === item?.roster_id);
        if (lb) { lb.completed += r.completed ? 1 : -1; lb.outstanding -= r.completed ? 1 : -1; }
        toast(r.completed ? 'Shotgun logged' : 'Un-logged');
        route();
      } catch (err) { box.checked = !box.checked; box.disabled = false; toast(`Error: ${err.message}`); }
    }
    if (e.target.id === 'news-week') { state.newsWeek = e.target.value; route(); }
    if (e.target.id === 'news-team') { state.newsTeam = e.target.value; route(); }
  });
  app.addEventListener('submit', async (e) => {
    if (e.target.id !== 'manual-form') return;
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api(`/api/season/${state.season}/shotguns/manual`, { method: 'POST', body: JSON.stringify({ week: Number(fd.get('week')), roster_id: Number(fd.get('roster_id')), label: fd.get('label'), detail: fd.get('detail') || null }) });
      await loadSeason(state.season, true); toast('Added');
    } catch (err) { toast(`Error: ${err.message}`); }
  });
  $('#season-select').addEventListener('change', (e) => loadSeason(e.target.value));
  $('#refresh-btn').addEventListener('click', async () => {
    $('#refresh-btn').disabled = true; toast('Refreshing from Sleeper…');
    try { await api(`/api/season/${state.season}/refresh`, { method: 'POST' }); state.pow = null; await loadSeason(state.season, true); toast('Refreshed'); }
    catch (err) { toast(`Error: ${err.message}`); }
    $('#refresh-btn').disabled = false;
  });
  window.addEventListener('hashchange', route);

  // ---------- boot ----------
  async function loadSeason(season, silent = false) {
    state.season = season;
    if (!silent) app.innerHTML = '<div class="loading">Loading league data…</div>';
    try {
      state.data = await api(`/api/season/${season}`);
      const L = state.data.league;
      $('#league-name').textContent = L.name || 'Labrums and Lagers';
      $('#league-sub').textContent = `/ ${L.season} · ${L.status === 'complete' ? 'Final' : `Week ${L.current_week}`}${state.data.meta.demo ? ' · Demo data' : ''}`;
      $('#foot-meta').innerHTML = `${esc(`Data via Sleeper · built ${new Date(state.data.meta.built_at * 1000).toLocaleString()} in ${state.data.meta.build_seconds}s · ${state.data.playoffs.sims.toLocaleString()} playoff sims${state.data.meta.demo ? ' · running on demo data' : ''}`)} · ${storageBadge(state.data.meta.persistence)}`;
      document.title = `${L.name || 'League HQ'} · ${L.season}`;
      route();
    } catch (err) {
      app.innerHTML = `<div class="error">Couldn't load season ${esc(season)}: ${esc(err.message)}</div>`;
    }
  }
  (async () => {
    try {
      const s = await api('/api/seasons');
      state.seasons = s.seasons;
      $('#season-select').innerHTML = s.seasons.map((x) => `<option value="${esc(x.season)}" ${x.season === s.current ? 'selected' : ''}>${esc(x.season)}${x.status === 'unavailable' ? ' (offline)' : ''}</option>`).join('');
      await loadSeason(s.current || (s.seasons[0] && s.seasons[0].season));
    } catch (err) { app.innerHTML = `<div class="error">Couldn't reach the server: ${esc(err.message)}</div>`; }
  })();
})();
