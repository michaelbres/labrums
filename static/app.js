/* Labrums League HQ — single-page frontend. Talks to the FastAPI backend. */
(() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const app = $('#app');
  const state = { seasons: [], season: null, data: null, newsFilter: 'all', newsWeek: 'all', shotFilter: 'outstanding', shotGroup: 'owner' };

  // ---------- utils ----------
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n, d = 2) => (n == null || isNaN(n)) ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
  const pct = (p) => p == null ? '—' : `${Math.round(p * 100)}%`;
  const signed = (n) => n == null ? '—' : (n > 0 ? '+' : '') + fmt(n, 2);
  const ordinal = (n) => { const s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };
  const team = (rid) => state.data.teams[String(rid)];
  const initials = (name) => (name || '?').split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
  const avatar = (t, cls = '') => t.avatar
    ? `<img class="avatar ${cls}" src="${esc(t.avatar)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'avatar ${cls}',textContent:'${esc(initials(t.display_name))}'}))">`
    : `<span class="avatar ${cls}">${esc(initials(t.display_name))}</span>`;
  const teamCell = (rid, { sub = 'team' } = {}) => {
    const t = team(rid);
    const subText = sub === 'team' ? t.team_name : sub === 'record' ? t.record : '';
    return `<a class="team-cell" href="#/teams/${rid}">${avatar(t)}<span class="names"><b>${esc(t.display_name)}</b><small>${esc(subText)}</small></span></a>`;
  };
  const teamLink = (rid) => `<a href="#/teams/${rid}">${esc(team(rid).display_name)}</a>`;
  const meter = (p, cls = '') => `<div class="meter-row"><div class="meter ${cls}"><i style="width:${Math.max(0, Math.min(100, (p || 0) * 100))}%"></i></div><span class="pct">${pct(p)}</span></div>`;
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
    let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Weekly scores for ${esc(t.display_name)}">`;
    ticks.forEach((tv) => { s += `<line class="axis" x1="${padL}" x2="${W - padR}" y1="${y(tv)}" y2="${y(tv)}"/><text x="${padL - 6}" y="${y(tv) + 4}" text-anchor="end">${tv}</text>`; });
    weeks.forEach((w, i) => {
      const v = t.scores[w]; const g = games[w];
      const won = g ? g.winner === t.roster_id : null;
      const cls = won === null ? '' : won ? 'win' : 'loss';
      const x = padL + i * bw + bw * 0.18, bwid = bw * 0.64;
      const opp = g ? (g.a === t.roster_id ? g.b : g.a) : null;
      const tip = `Week ${w}: ${v}${g ? ` ${won ? 'W' : won === false ? 'L' : 'T'} vs ${team(opp).display_name} (${g.a === t.roster_id ? g.b_pts : g.a_pts})` : ''}`;
      s += `<rect class="bar ${cls}" x="${x.toFixed(1)}" y="${y(v).toFixed(1)}" width="${bwid.toFixed(1)}" height="${(H - padB - y(v)).toFixed(1)}" rx="3"><title>${esc(tip)}</title></rect>`;
      s += `<text x="${(x + bwid / 2).toFixed(1)}" y="${H - padB + 16}" text-anchor="middle">${w}</text>`;
    });
    s += `<line class="avg" x1="${padL}" x2="${W - padR}" y1="${y(leagueAvg)}" y2="${y(leagueAvg)}"/><text x="${W - padR}" y="${y(leagueAvg) - 4}" text-anchor="end">lg avg ${leagueAvg}</text>`;
    s += '</svg>';
    s += `<div class="legend"><span><i style="background:var(--series-1)"></i>Win</span><span><i style="background:var(--series-2)"></i>Loss</span><span><i style="background:var(--text-3)"></i>League average</span></div>`;
    return s;
  }

  // ---------- views ----------
  function viewHome() {
    const d = state.data, L = d.league;
    const top = team(d.standings[0]);
    const lb = d.shotguns.leaderboard;
    const owed = lb.reduce((a, r) => a + r.outstanding, 0);
    const rec = d.records || {};
    const hi = rec.high_score ? `${fmt(rec.high_score.points)} · ${team(rec.high_score.roster_id).display_name} (wk ${rec.high_score.week})` : '—';
    const headlines = d.articles.slice(0, 8);
    const po = d.playoffs.teams;
    return `
      <div class="page-h"><div><h1>${esc(L.name)}</h1><p>${L.status === 'complete' ? 'Season complete' : `Week ${L.current_week} · ${L.last_completed} week${L.last_completed === 1 ? '' : 's'} in the books`} · ${L.playoff_teams} playoff spots</p></div></div>
      <div class="tiles section">
        <div class="tile"><div class="label">Leader</div><div class="value">${esc(top.display_name)}</div><div class="sub">${top.record} · ${fmt(top.pf, 1)} PF</div></div>
        <div class="tile"><div class="label">Top score</div><div class="value">${rec.high_score ? fmt(rec.high_score.points, 1) : '—'}</div><div class="sub">${rec.high_score ? `${esc(team(rec.high_score.roster_id).display_name)}, week ${rec.high_score.week}` : ''}</div></div>
        <div class="tile"><div class="label">League average</div><div class="value">${fmt(d.league_avg, 1)}</div><div class="sub">points per team-week</div></div>
        <div class="tile"><div class="label">Shotguns owed</div><div class="value">${owed} <span class="beer">🍺</span></div><div class="sub">${lb[0] && lb[0].total ? `${esc(lb[0].display_name)} leads with ${lb[0].total}` : 'nobody yet'}</div></div>
      </div>
      <div class="grid grid-2 section">
        <div class="card"><div class="card-h"><h2>Headlines</h2><a href="#/news">All news →</a></div>
          <ul class="clean headlines">${headlines.map((a) => `<li><div class="kicker">${esc(a.type)} · week ${a.week}</div><a href="#/news/${esc(a.id)}">${esc(a.headline)}</a></li>`).join('') || '<li class="empty">Nothing yet.</li>'}</ul>
        </div>
        <div>
          <div class="card section"><div class="card-h"><h2>Standings</h2><a href="#/standings">Full table →</a></div>
            <div class="table-wrap"><table><thead><tr><th>#</th><th>Team</th><th class="num">W-L</th><th class="num">PF</th><th class="num">Odds</th></tr></thead><tbody>
            ${d.standings.map((rid, i) => { const t = team(rid); return `<tr class="${i === L.playoff_teams - 1 ? 'cut-line' : ''}"><td><span class="rank-pill ${i === 0 ? 'top' : ''}">${i + 1}</span></td><td>${teamCell(rid)}</td><td class="num">${t.record}</td><td class="num">${fmt(t.pf, 1)}</td><td class="num">${pct(po[rid]?.playoff_pct)}</td></tr>`; }).join('')}
            </tbody></table></div></div>
          <div class="card"><div class="card-h"><h2>Shotgun leaderboard</h2><a href="#/shotguns">Check them off →</a></div>
            ${lb.slice(0, 6).map((r) => `<div class="hbar"><span>${esc(r.display_name)}</span><div class="meter warn"><i style="width:${lb[0].total ? (r.total / lb[0].total) * 100 : 0}%"></i></div><span class="num">${r.total} <span class="dim">(${r.outstanding} owed)</span></span></div>`).join('')}
          </div>
        </div>
      </div>`;
  }

  function viewStandings() {
    const d = state.data, L = d.league, po = d.playoffs.teams;
    const rows = d.standings.map((rid, i) => {
      const t = team(rid);
      return `<tr class="${i === L.playoff_teams - 1 ? 'cut-line' : ''}">
        <td><span class="rank-pill ${i === 0 ? 'top' : ''}">${i + 1}</span></td><td>${teamCell(rid)}</td>
        <td class="num"><b>${t.record}</b></td><td class="num">${fmt(t.pf, 1)}</td><td class="num">${fmt(t.pa, 1)}</td><td class="num">${fmt(t.avg, 1)}</td>
        <td class="num">${fmt(t.high, 1)}</td><td class="num">${fmt(t.low, 1)}</td><td>${streakBadge(t.streak)}</td>
        <td class="num">${t.all_play.w}-${t.all_play.l}</td><td class="num ${t.luck > 0.75 ? 'good' : t.luck < -0.75 ? 'bad' : ''}">${signed(t.luck)}</td>
        <td class="num">${t.power_rank}</td><td class="num">${pct(po[rid]?.playoff_pct)}</td><td>${sparkline(t.scores, d.league_avg)}</td></tr>`;
    }).join('');
    const power = d.power_rankings.map((rid, i) => { const t = team(rid); return `<tr><td><span class="rank-pill ${i === 0 ? 'top' : ''}">${i + 1}</span></td><td>${teamCell(rid, { sub: 'record' })}</td><td class="num">${fmt(t.power_score * 100, 1)}</td><td class="num">${fmt(t.avg, 1)}</td><td class="num">${pct(t.all_play.pct)}</td><td class="num">${t.weeks_top}</td><td class="num">${t.weeks_bottom}</td><td class="num">${pct(t.lineup_efficiency)}</td><td class="num">${t.rank - (i + 1) > 0 ? `<span class="badge good">+${t.rank - (i + 1)}</span>` : t.rank - (i + 1) < 0 ? `<span class="badge bad">${t.rank - (i + 1)}</span>` : '<span class="dim">—</span>'}</td></tr>`; }).join('');
    const rec = d.records || {};
    const recCard = rec.high_score ? `<div class="card"><div class="card-h"><h2>Season records</h2></div><dl class="kv">
      <dt>Highest score</dt><dd>${fmt(rec.high_score.points)} · ${teamLink(rec.high_score.roster_id)} (week ${rec.high_score.week})</dd>
      <dt>Lowest score</dt><dd>${fmt(rec.low_score.points)} · ${teamLink(rec.low_score.roster_id)} (week ${rec.low_score.week})</dd>
      <dt>Biggest blowout</dt><dd>${teamLink(rec.biggest_blowout.winner)} by ${fmt(rec.biggest_blowout.margin)} over ${teamLink(rec.biggest_blowout.winner === rec.biggest_blowout.a ? rec.biggest_blowout.b : rec.biggest_blowout.a)} (week ${rec.biggest_blowout.week})</dd>
      ${rec.closest_game ? `<dt>Closest game</dt><dd>${teamLink(rec.closest_game.winner)} by ${fmt(rec.closest_game.margin)} over ${teamLink(rec.closest_game.winner === rec.closest_game.a ? rec.closest_game.b : rec.closest_game.a)} (week ${rec.closest_game.week})</dd>` : ''}
      <dt>Highest-scoring game</dt><dd>${teamLink(rec.highest_scoring_game.a)} ${fmt(rec.highest_scoring_game.a_pts)} – ${teamLink(rec.highest_scoring_game.b)} ${fmt(rec.highest_scoring_game.b_pts)} (week ${rec.highest_scoring_game.week})</dd>
    </dl></div>` : '';
    return `
      <div class="page-h"><div><h1>Standings</h1><p>Sorted by wins, then points for. Dashed line = playoff cut (top ${L.playoff_teams}). Luck = actual wins minus all-play expected wins.</p></div></div>
      <div class="card section"><div class="table-wrap"><table><thead><tr><th>#</th><th>Team</th><th class="num">Record</th><th class="num">PF</th><th class="num">PA</th><th class="num">Avg</th><th class="num">High</th><th class="num">Low</th><th>Streak</th><th class="num">All-play</th><th class="num">Luck</th><th class="num">Power</th><th class="num">Playoff %</th><th>Trend</th></tr></thead><tbody>${rows}</tbody></table></div></div>
      <div class="grid grid-2 section">
        <div class="card"><div class="card-h"><h2>Power rankings</h2><small>35% record · 40% all-play · 25% scoring</small></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Team</th><th class="num">Score</th><th class="num">Avg</th><th class="num">All-play</th><th class="num">Wk high</th><th class="num">Wk low</th><th class="num">Lineup eff.</th><th class="num">vs. standings</th></tr></thead><tbody>${power}</tbody></table></div></div>
        ${recCard}
      </div>`;
  }

  function viewTeams() {
    const d = state.data, po = d.playoffs.teams;
    const cards = d.standings.map((rid) => {
      const t = team(rid);
      return `<a class="card" href="#/teams/${rid}" style="color:inherit">
        <div class="team-cell" style="margin-bottom:8px">${avatar(t, 'lg')}<span class="names"><b style="font-size:1.05rem">${esc(t.team_name)}</b><small>${esc(t.display_name)}${t.nickname ? ` · “${esc(t.nickname)}”` : ''}</small></span></div>
        <div class="kv"><dt>Record</dt><dd><b>${t.record}</b> (${ordinal(t.rank)})</dd><dt>Avg</dt><dd>${fmt(t.avg, 1)}</dd><dt>Streak</dt><dd>${streakBadge(t.streak)}</dd><dt>Playoffs</dt><dd>${pct(po[rid]?.playoff_pct)} ${statusBadge(po[rid]?.status)}</dd><dt>Top player</dt><dd>${t.top_player ? `${esc(t.top_player.name)} (${fmt(t.top_player.points, 1)})` : '—'}</dd></div>
        <div style="margin-top:8px">${sparkline(t.scores, d.league_avg)}</div></a>`;
    }).join('');
    return `<div class="page-h"><div><h1>Teams</h1><p>Click a team for the full breakdown.</p></div></div><div class="cards">${cards}</div>`;
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
    const arts = d.articles.filter((a) => a.teams.includes(t.roster_id)).slice(0, 8);
    const prof = t.profile || {};
    const seedDist = (po.seed_dist || []).map((p, i) => `<div class="hbar"><span>Seed ${i + 1}</span><div class="meter ${i < d.league.playoff_teams ? '' : 'bad'}"><i style="width:${p * 100}%"></i></div><span class="num">${pct(p)}</span></div>`).join('');
    return `
      <div class="team-head">${avatar(t, 'lg')}<div><h1>${esc(t.team_name)}</h1><div class="muted">${esc(t.display_name)}${t.nickname ? ` · “${esc(t.nickname)}”` : ''}${prof.hometown ? ` · ${esc(prof.hometown)}` : ''}</div>${prof.bio ? `<div class="muted" style="margin-top:4px">${esc(prof.bio)}</div>` : ''}</div>
        <div style="margin-left:auto">${statusBadge(po.status)}</div></div>
      <div class="tiles section">
        <div class="tile"><div class="label">Record</div><div class="value">${t.record}</div><div class="sub">${ordinal(t.rank)} place · power #${t.power_rank}</div></div>
        <div class="tile"><div class="label">Points for</div><div class="value">${fmt(t.pf, 1)}</div><div class="sub">${fmt(t.avg, 1)} avg · ±${fmt(t.std, 1)}</div></div>
        <div class="tile"><div class="label">Points against</div><div class="value">${fmt(t.pa, 1)}</div><div class="sub">${t.pa > t.pf ? 'outscored' : 'outscoring opponents'}</div></div>
        <div class="tile"><div class="label">Playoff odds</div><div class="value">${pct(po.playoff_pct)}</div><div class="sub">bye ${pct(po.bye_pct)} · proj ${fmt(po.proj_wins, 1)} wins</div></div>
        <div class="tile"><div class="label">Luck</div><div class="value">${signed(t.luck)}</div><div class="sub">all-play ${t.all_play.w}-${t.all_play.l} · ${fmt(t.expected_wins, 1)} xW</div></div>
        <div class="tile"><div class="label">Lineup efficiency</div><div class="value">${pct(t.lineup_efficiency)}</div><div class="sub">${fmt(t.bench_points_left, 1)} pts left on bench</div></div>
        <div class="tile"><div class="label">Shotguns</div><div class="value">${shots.length} 🍺</div><div class="sub">${shots.filter((s) => !s.completed).length} outstanding</div></div>
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
    const seeds = order.map((rid) => `<tr><td>${teamCell(rid, { sub: 'record' })}</td>${P.teams[rid].seed_dist.map((p, i) => `<td class="num" style="background:color-mix(in srgb, var(--series-1) ${Math.round(p * 100)}%, transparent)">${p >= 0.005 ? pct(p) : '<span class="dim">·</span>'}</td>`).join('')}</tr>`).join('');
    const nseeds = order.length;
    return `
      <div class="page-h"><div><h1>Playoff odds</h1><p>${P.sims.toLocaleString()} simulated seasons. Each team's weekly score ~ Normal(mean, sd), shrunk toward the league average (${fmt(P.league_mu, 1)} ± ${fmt(P.league_sd, 1)}). Seeds by wins, then points for. Top ${L.playoff_teams} make it${L.playoff_teams === 6 ? ', top 2 get a bye' : ''}.</p></div></div>
      <div class="card section"><div class="table-wrap"><table><thead><tr><th>Team</th><th>Make playoffs</th><th>First-round bye</th><th class="num">#1 seed</th><th class="num">Avg seed</th><th class="num">Proj W</th><th class="num">Proj PF</th><th class="num">Left</th><th>Next game: win / loss</th><th></th></tr></thead><tbody>${rows}</tbody></table></div></div>
      <div class="card section"><div class="card-h"><h2>Seed distribution</h2><small>probability of finishing at each seed</small></div><div class="table-wrap"><table><thead><tr><th>Team</th>${Array.from({ length: nseeds }, (_, i) => `<th class="num">${i + 1}</th>`).join('')}</tr></thead><tbody>${seeds}</tbody></table></div></div>`;
  }

  function shotRow(s, editable) {
    const reasonBadge = { zero: '<span class="badge warn">0 pts</span>', negative: '<span class="badge bad">negative</span>', empty_slot: '<span class="badge">empty slot</span>', rule: '<span class="badge accent">rule</span>', manual: '<span class="badge">manual</span>' }[s.reason] || '';
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
    const rows = lb.map((r) => `<tr><td><span class="rank-pill ${r.rank === 1 && r.total ? 'top' : ''}">${r.rank}</span></td><td>${teamCell(r.roster_id)}</td><td class="num"><b>${r.total}</b></td><td class="num good">${r.completed}</td><td class="num ${r.outstanding ? 'bad' : ''}">${r.outstanding}</td><td><div class="meter-row"><div class="meter good" title="${r.completed} of ${r.total} done"><i style="width:${r.total ? (r.completed / r.total) * 100 : 0}%"></i></div><span class="pct">${r.total ? Math.round((r.completed / r.total) * 100) : 0}%</span></div></td><td class="dim">${Object.entries(r.by_reason).map(([k, v]) => `${v} ${k.replace('_', ' ')}`).join(', ') || '—'}</td><td class="dim">${r.worst_week ? `wk ${r.worst_week.week} (${r.worst_week.count})` : '—'}</td></tr>`).join('');
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
    const ownerOpts = d.standings.map((rid) => `<option value="${rid}">${esc(team(rid).display_name)}</option>`).join('');
    const weekOpts = Array.from({ length: Math.max(1, L.last_completed) }, (_, i) => `<option value="${i + 1}">Week ${i + 1}</option>`).reverse().join('');
    return `
      <div class="page-h"><div><h1>Shotgun leaderboard 🍺</h1><p>Start a player who scores ${S.rules.threshold} or fewer, shotgun a beer.${S.rules.count_empty_slots ? ' Empty starting slots count.' : ''}${special.length ? ` Special rules: ${special.map((r) => `${esc(r.label)} (${r.owners.map(esc).join(', ')}${r.target ? ` vs ${esc(r.target)}` : ''})`).join('; ')}.` : ''}</p></div>
        ${d.meta.admin_locked ? `<div class="form-row"><input class="input" id="pin" type="password" placeholder="Admin PIN" value="${esc(localStorage.getItem('labrums_pin') || '')}"><button class="btn btn-sm" id="pin-save">Unlock</button>${locked ? '<span class="lock-note">Check-offs are locked until you enter the PIN.</span>' : '<span class="lock-note">Unlocked.</span>'}</div>` : ''}</div>
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

  function articleCard(a, open = false) {
    return `<article class="card article type-${esc(a.type)} ${open ? 'open' : ''}" id="art-${esc(a.id)}">
      <div class="kicker"><span>${esc(a.type)}</span><span>·</span><span>Week ${a.week}</span>${a.tags.includes('rivalry') ? '<span class="badge bad">rivalry</span>' : ''}</div>
      <h3>${esc(a.headline)}</h3><div class="dek">${esc(a.dek)}</div><div class="byline">By ${esc(a.byline)} · ${a.teams.map((rid) => teamLink(rid)).join(', ')}</div>
      <div class="body">${a.body.map((p) => `<p>${esc(p)}</p>`).join('')}</div>
      <span class="more" data-more>${open ? 'Collapse' : 'Read more'}</span></article>`;
  }

  function viewNews(articleId) {
    const d = state.data;
    if (articleId) {
      const a = d.articles.find((x) => x.id === articleId);
      if (!a) return '<div class="error">Article not found.</div>';
      const related = d.articles.filter((x) => x.id !== a.id && x.teams.some((t) => a.teams.includes(t))).slice(0, 6);
      return `<div class="page-h"><div><a href="#/news">← All news</a></div></div>${articleCard(a, true)}<div class="card section"><div class="card-h"><h2>Related</h2></div><ul class="clean headlines">${related.map((x) => `<li><div class="kicker">${esc(x.type)} · week ${x.week}</div><a href="#/news/${esc(x.id)}">${esc(x.headline)}</a></li>`).join('') || '<li class="empty">—</li>'}</ul></div>`;
    }
    const types = ['all', ...new Set(d.articles.map((a) => a.type))];
    const weeks = ['all', ...new Set(d.articles.map((a) => a.week))];
    let arts = d.articles;
    if (state.newsFilter !== 'all') arts = arts.filter((a) => a.type === state.newsFilter);
    if (state.newsWeek !== 'all') arts = arts.filter((a) => String(a.week) === String(state.newsWeek));
    return `
      <div class="page-h"><div><h1>League News</h1><p>All of it fake. Most of it accurate.</p></div>
        <select class="select" id="news-week">${weeks.map((w) => `<option value="${w}" ${String(state.newsWeek) === String(w) ? 'selected' : ''}>${w === 'all' ? 'All weeks' : `Week ${w}`}</option>`).join('')}</select></div>
      <div class="chips section">${types.map((t) => `<span class="chip ${state.newsFilter === t ? 'active' : ''}" data-news="${t}">${t}</span>`).join('')}</div>
      <div class="grid" style="gap:12px">${arts.map((a) => articleCard(a)).join('') || '<div class="empty">No stories match.</div>'}</div>`;
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
        <dl class="kv"><dt>Head to head</dt><dd><b>${esc(ta.display_name)} ${h2h.w}-${h2h.l}${h2h.t ? `-${h2h.t}` : ''}</b> this season</dd>
          ${meetings.map((g) => `<dt>Week ${g.week}</dt><dd>${g.winner == null ? 'Tie' : `${esc(team(g.winner).display_name)} won`} ${fmt(Math.max(g.a_pts, g.b_pts))}–${fmt(Math.min(g.a_pts, g.b_pts))}</dd>`).join('')}</dl>
        ${arts.length ? `<h3 style="margin-top:12px">Coverage</h3><ul class="clean headlines">${arts.map((x) => `<li><div class="kicker">${esc(x.type)} · week ${x.week}</div><a href="#/news/${esc(x.id)}">${esc(x.headline)}</a></li>`).join('')}</ul>` : ''}
      </div>`;
    }).join('');
    // Auto "heat" pairs: adjacent teams around the playoff cut.
    const cut = d.league.playoff_teams;
    const hot = [];
    for (let i = Math.max(0, cut - 3); i < Math.min(d.standings.length - 1, cut + 2); i++) hot.push([d.standings[i], d.standings[i + 1]]);
    const hotCards = hot.map(([a, b]) => `<div class="card"><div class="card-h"><h3>${esc(team(a).display_name)} vs. ${esc(team(b).display_name)}</h3><span class="badge warn">${ordinal(team(a).rank)} / ${ordinal(team(b).rank)}</span></div><div class="dim">${team(a).record} vs ${team(b).record} · ${fmt(Math.abs(team(a).pf - team(b).pf), 1)} PF apart · playoff odds ${pct(d.playoffs.teams[a].playoff_pct)} vs ${pct(d.playoffs.teams[b].playoff_pct)}</div></div>`).join('');
    return `
      <div class="page-h"><div><h1>Rivalries</h1><p>Configured in <code>config.yaml</code> under <code>rivalries</code>. The newsroom writes hype pieces when rivals meet.</p></div></div>
      ${cards ? `<div class="grid grid-2 section">${cards}</div>` : '<div class="card section"><div class="empty">No rivalries configured yet. Add them to config.yaml, then hit ↻.</div></div>'}
      <h2>Fighting for the cut line</h2><p class="muted">Teams stacked around the ${ordinal(cut)} seed, where every week is a grudge match whether they like it or not.</p>
      <div class="grid grid-3 section">${hotCards}</div>`;
  }

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
      default: html = viewHome();
    }
    app.innerHTML = html;
    window.scrollTo({ top: 0 });
  }

  // ---------- events ----------
  app.addEventListener('click', async (e) => {
    const more = e.target.closest('[data-more]');
    if (more) { const art = more.closest('.article'); art.classList.toggle('open'); more.textContent = art.classList.contains('open') ? 'Collapse' : 'Read more'; return; }
    const chip = e.target.closest('.chip');
    if (chip) {
      if (chip.dataset.news) state.newsFilter = chip.dataset.news;
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
        toast(r.completed ? '🍺 Shotgun logged' : 'Un-logged');
        route();
      } catch (err) { box.checked = !box.checked; box.disabled = false; toast(`Error: ${err.message}`); }
    }
    if (e.target.id === 'news-week') { state.newsWeek = e.target.value; route(); }
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
    try { await api(`/api/season/${state.season}/refresh`, { method: 'POST' }); await loadSeason(state.season, true); toast('Refreshed'); }
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
      $('#league-name').textContent = L.name || 'League HQ';
      $('#league-sub').textContent = `${L.season} season · ${L.status === 'complete' ? 'final' : `week ${L.current_week}`}${state.data.meta.demo ? ' · DEMO DATA' : ''}`;
      $('#foot-meta').textContent = `Data via Sleeper · built ${new Date(state.data.meta.built_at * 1000).toLocaleString()} in ${state.data.meta.build_seconds}s · ${state.data.playoffs.sims.toLocaleString()} playoff sims${state.data.meta.demo ? ' · running on demo data' : ''}`;
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
