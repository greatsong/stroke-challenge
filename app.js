// DS 건강검진센터 인턴 미션 · 순위판 (참가자 index.html · 진행자 host.html 공용)
// 설정은 config.js의 CHALLENGE_CONFIG(SUPABASE_URL · SUPABASE_KEY · EVENT)에서 읽는다.
// 공개 키는 표를 직접 읽지 못하고 함수(rpc)만 부른다. 마감·최종 공개 여부는 서버(event_info)가 정한다.
//
// 규칙
//   팀 점수 = 그 팀의 공개 F2 최고 기록. 같은 점수면 그 점수를 먼저 낸 팀이 앞선다(같은 순위 없음).
//   최종 순위 = 각 팀의 공개 최고 기록(같은 제출)의 최종 F2로 다시 매긴 순위.
//   지표는 서버가 준 sent·found와 event_info의 pos_public·pos_private로 브라우저에서 계산한다.
(function () {
  'use strict';
  var C = window.CHALLENGE_CONFIG || {};
  var URL_ = (C.SUPABASE_URL || '').replace(/\/$/, ''), KEY = C.SUPABASE_KEY || '', EVENT = C.EVENT || '';
  var HOST = window.CHALLENGE_MODE === 'host';
  var PASS_KEY = 'stroke_challenge_admin_pass';

  var $ = function (id) { return document.getElementById(id); };
  var state = {
    info: null, rows: [], roster: [], admin: false, pass: '',
    view: 'public', viewChosen: false, prevBest: {}, prevLeader: null, first: true, teams: []
  };

  // ── 작은 도구 ───────────────────────────────────────────
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmt(v, d) { return v == null || isNaN(v) ? '—' : Number(v).toFixed(d == null ? 4 : d); }
  function int(v) { return v == null ? '—' : Number(v).toLocaleString('ko-KR'); }
  function setText(id, t) { var el = $(id); if (el) el.textContent = t; }
  function clock(t) { return new Date(t).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  function store(k, v) {
    try { if (v == null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, v); } catch (e) { /* 저장소를 못 써도 화면은 동작한다 */ }
  }
  function load(k) { try { return sessionStorage.getItem(k) || ''; } catch (e) { return ''; } }

  // 정밀도·재현율·F1·F2. sent가 0이거나 P+R이 0이면 null
  function metrics(sent, found, pos) {
    if (sent == null || found == null) return { P: null, R: null, F1: null, F2: null };
    var P = sent > 0 ? found / sent : null, R = pos ? found / pos : null;
    var ok = P != null && R != null && P + R > 0;
    return { P: P, R: R, F1: ok ? 2 * P * R / (P + R) : null, F2: ok ? 5 * P * R / (4 * P + R) : null };
  }

  // ── 수파베이스 호출 ─────────────────────────────────────
  function rpc(name, args, method) {
    var url = URL_ + '/rest/v1/rpc/' + name, opt = { headers: { apikey: KEY, Authorization: 'Bearer ' + KEY } };
    if (method === 'GET') {
      url += '?' + Object.keys(args).map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(args[k]); }).join('&');
    } else {
      opt.method = 'POST';
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(args);
    }
    return fetch(url, opt).then(function (r) {
      return r.text().then(function (t) {
        var body = null;
        try { body = t ? JSON.parse(t) : null; } catch (e) { body = null; }
        if (!r.ok) {
          var err = new Error((body && body.message) || String(r.status));
          err.status = r.status;
          throw err;
        }
        return body;
      });
    });
  }

  // ── 팀별로 모아 순위를 매긴다 ─────────────────────────────
  // 참가자 화면은 event_info의 pos_private(공개 뒤에만 값)를, 진행자 화면은 admin_info의 pos_private(늘 값)를 쓴다
  function posPrivate() { return (state.info || {}).pos_private; }
  function finalVisible() { return !!(state.info && state.info.revealed) || state.admin; }

  function buildTeams() {
    var info = state.info || {}, posPub = info.pos_public, posPri = posPrivate();
    var map = {};
    state.rows.forEach(function (r) {
      r.pub = metrics(r.sent, r.found, posPub);
      r.pri = metrics(r.sent_private, r.found_private, posPri);
      var t = map[r.nickname] || (map[r.nickname] = { name: r.nickname, subs: 0, best: null, last: r.created_at, first: r.created_at });
      t.subs += 1;
      if (r.created_at > t.last) t.last = r.created_at;
      if (r.created_at < t.first) t.first = r.created_at;
      if (r.pub.F2 == null) return;                    // 계산할 수 없는 기록은 최고 기록이 되지 못한다
      if (!t.best || r.pub.F2 > t.best.pub.F2 || (r.pub.F2 === t.best.pub.F2 && r.created_at < t.best.created_at)) t.best = r;
    });
    if (state.admin) {                                   // 등록만 하고 제출하지 않은 팀도 진행자 화면에 보인다
      state.roster.forEach(function (p) {
        if (!map[p.nickname]) map[p.nickname] = { name: p.nickname, subs: 0, best: null, last: p.created_at, first: p.created_at };
      });
    }
    var list = Object.keys(map).map(function (k) { return map[k]; });
    var rosterBy = {};
    state.roster.forEach(function (p) { rosterBy[p.nickname] = p; });
    list.forEach(function (t) { t.person = rosterBy[t.name] || null; });

    function by(get) {
      return function (a, b) {
        var va = a.best ? get(a.best) : null, vb = b.best ? get(b.best) : null;
        if (va == null && vb == null) return a.first.localeCompare(b.first);
        if (va == null) return 1;
        if (vb == null) return -1;
        return (vb - va) || a.best.created_at.localeCompare(b.best.created_at);
      };
    }
    list.slice().sort(by(function (r) { return r.pub.F2; })).forEach(function (t, i) { t.pubRank = t.best ? i + 1 : null; });
    list.slice().sort(by(function (r) { return r.pri.F2; })).forEach(function (t, i) { t.priRank = t.best && t.best.pri.F2 != null ? i + 1 : null; });
    return list;
  }

  function isFinal() { return state.view === 'final' && finalVisible(); }
  function score(t) { return t.best ? (isFinal() ? t.best.pri.F2 : t.best.pub.F2) : null; }
  function rankOf(t) { return isFinal() ? t.priRank : t.pubRank; }
  function sorted(list) {
    return list.slice().sort(function (a, b) {
      var ra = rankOf(a), rb = rankOf(b);
      if (ra == null && rb == null) return a.first.localeCompare(b.first);
      if (ra == null) return 1;
      if (rb == null) return -1;
      return ra - rb;
    });
  }

  // ── 마감 ───────────────────────────────────────────────
  function deadlineText() {
    var d = state.info && state.info.deadline;
    if (!d) return '마감 없음';
    var ms = new Date(d) - new Date();
    if (ms <= 0) return '마감되었습니다';
    var m = Math.floor(ms / 60000), day = Math.floor(m / 1440), h = Math.floor(m % 1440 / 60), mi = m % 60;
    if (day > 0) return day + '일 ' + h + '시간 남음';
    if (h > 0) return h + '시간 ' + mi + '분 남음';
    var s = Math.floor(ms / 1000) % 60;
    return mi + '분 ' + s + '초 남음';
  }
  function deadlineAbs() {
    var d = state.info && state.info.deadline;
    return d ? new Date(d).toLocaleString('ko-KR', { month: 'long', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit' }) : '마감 없음';
  }
  function tick() {
    setText('deadlineChip', '⏱ ' + deadlineText());
    setText('kLeft', state.info ? deadlineText() : '—');
  }

  // ── 센터장 한마디(현재 1등 기록에 따라) ──────────────────
  function bossLine(list) {
    var top = list[0], info = state.info || {};
    if (!top || !top.best) {
      return state.rows.length
        ? '올라온 목록으로는 아직 점수를 계산할 수 없습니다. 전화를 걸 사람이 한 명 이상이고 그중 환자가 있어야 합니다.'
        : '아직 올라온 목록이 없습니다. 첫 목록을 기다리고 있습니다.';
    }
    var fin = isFinal(), b = top.best, m = fin ? b.pri : b.pub;
    var sent = fin ? b.sent_private : b.sent, n = fin ? info.n_private : info.n_public;
    var lead = fin && top.pubRank && top.pubRank !== 1 ? '최종 1등은 공개 순위 ' + top.pubRank + '위였던 팀입니다. ' : '';
    if (n && sent >= 0.4 * n) return lead + '안내 인원이 검진자의 40%를 넘습니다. 검진자 전원에게 전화를 걸던 작년과 비슷해 상담사가 감당하기 어렵습니다.';
    if (m.R != null && m.R < 0.5) return lead + '1등 목록도 환자의 절반 이상을 놓치고 있습니다. 위험이 높은 사람에게만 전화를 걸던 작년의 문제가 남아 있습니다.';
    if (m.P != null && m.P < 0.05) return lead + '전화 스무 통 가운데 환자는 한 명이 되지 않습니다. 환자는 많이 찾았지만 헛전화도 많습니다.';
    if (m.F2 != null && m.F2 >= 0.25) return lead + '상담팀이 감당할 만한 목록입니다. 이 설정이 왜 환자를 더 찾았는지 설명할 수 있는지 확인하십시오.';
    return lead + '정밀도와 재현율의 균형을 찾는 중입니다. 기준값을 바꾸면 두 값이 어떻게 움직이는지 살피십시오.';
  }

  // ── 그리기 ─────────────────────────────────────────────
  function drawPodium(list) {
    var medals = ['🥇', '🥈', '🥉'], leader = list[0] && list[0].best ? list[0].name : null;
    var html = [0, 1, 2].map(function (i) {
      var t = list[i], cls = 'pod p' + (i + 1) + (i === 0 ? ' first' : '');
      if (!t || !t.best || score(t) == null) {
        return '<div class="' + cls + ' empty"><div class="medal">' + medals[i] + '</div><div class="who">비어 있습니다</div><div class="big">—</div></div>';
      }
      var b = t.best, fin = isFinal(), sent = fin ? b.sent_private : b.sent, found = fin ? b.found_private : b.found;
      return '<div class="' + cls + '" data-team="' + esc(t.name) + '">' +
        '<div class="medal">' + medals[i] + '</div>' +
        '<div class="who">' + esc(t.name) + '</div>' +
        '<div class="big">' + fmt(score(t)) + '<span> ' + (fin ? '최종 F2' : 'F2') + '</span></div>' +
        '<div class="sub">안내 ' + int(sent) + '명 · 찾은 환자 ' + int(found) + '명' + (fin && t.pubRank ? ' · 공개 ' + t.pubRank + '위' : '') + '</div>' +
        '</div>';
    }).join('');
    $('podium').innerHTML = html;
    if (!state.first && leader && state.prevLeader && leader !== state.prevLeader) {
      var p1 = document.querySelector('#podium .p1');
      if (p1) { p1.classList.add('crown'); }
    }
    state.prevLeader = leader;
  }

  function settingText(s) {
    if (!s) return '';
    var parts = [];
    if (s.inputs) parts.push('입력 ' + s.inputs);
    if (s.depth != null && /트리/.test(s.model || '')) parts.push('질문 ' + s.depth + '번');   // 로지스틱 회귀에는 질문 횟수가 없다
    if (s.threshold != null) parts.push('기준값 ' + Number(s.threshold).toFixed(2));
    if (s.missing) parts.push('빈 값 ' + s.missing);
    if (s.validation_f2 != null) parts.push('검증 F2 ' + fmt(s.validation_f2));
    if (s.file) parts.push('파일 ' + s.file);
    return parts.join(' · ');
  }
  function modelName(r) {
    var m = r.model || (r.setting && r.setting.model);
    return m ? m : (r.source === 'csv' ? '외부 예측 파일' : '');
  }

  function drawTable(list) {
    var fin = isFinal(), H = state.admin;
    var fresh = {};
    list.forEach(function (t) {
      var key = t.name + (fin ? '#f' : '#p'), now = score(t), prev = state.prevBest[key];
      if (!state.first && now != null && (prev == null || now > prev) && prev !== undefined) fresh[t.name] = true;
      if (!state.first && now != null && prev === undefined && t.subs) fresh[t.name] = true;
      state.prevBest[key] = now;
    });

    var head = '<tr><th class="num">#</th>' + (fin ? '<th class="num">변동</th>' : '') + '<th>팀</th>' +
      '<th>' + (fin ? '최종 F2' : 'F2') + '</th>' +
      (fin ? '<th class="num hide">공개 F2</th>' : '') +
      '<th class="num hide">F1</th><th class="num hide">정밀도</th><th class="num hide">재현율</th>' +
      '<th class="num">안내</th><th class="num">찾은 환자</th><th class="num hide">제출</th>' +
      (H ? '<th>성명 · 소속 · 이메일</th><th>설정</th>' : '<th class="hide">모델</th>') +
      '<th class="num hide">최근 제출</th></tr>';
    $('thead').innerHTML = head;

    var cols = (fin ? 12 : 11) + (H ? 2 : 0);
    var body = list.map(function (t) {
      var b = t.best, m = b ? (fin ? b.pri : b.pub) : null, rank = rankOf(t), s = score(t);
      var medal = rank && rank <= 3 ? ['🥇', '🥈', '🥉'][rank - 1] : null;
      var width = s == null ? 0 : Math.min(100, Math.round(s / 0.5 * 100));   // 0.5를 막대 끝으로 둔다
      var move = '';
      if (fin) {
        if (t.pubRank && t.priRank) {
          var d = t.pubRank - t.priRank;
          move = d > 0 ? '<span class="up">▲' + d + '</span>' : d < 0 ? '<span class="down">▼' + (-d) + '</span>' : '<span class="same">‒</span>';
        } else move = '<span class="same">‒</span>';
      }
      var sent = b ? (fin ? b.sent_private : b.sent) : null, found = b ? (fin ? b.found_private : b.found) : null;
      var p = t.person || {};
      var src = b && b.source === 'csv' ? '<span class="tag csv">csv</span>' : '';
      var reason = !b && t.subs ? '<span class="detail">점수를 계산할 수 없는 목록만 있습니다</span>' : (!t.subs ? '<span class="detail">등록만 했습니다</span>' : '');
      return '<tr class="' + (fresh[t.name] ? 'fresh' : '') + '">' +
        '<td class="rank">' + (rank ? (medal || rank) : '—') + '</td>' +
        (fin ? '<td class="num">' + move + '</td>' : '') +
        '<td class="team"><b>' + esc(t.name) + '</b>' + src + reason + '</td>' +
        '<td><div class="bar"><i style="width:' + width + '%"></i><b>' + fmt(s) + '</b></div></td>' +
        (fin ? '<td class="num hide">' + fmt(b && b.pub.F2) + '</td>' : '') +
        '<td class="num hide">' + fmt(m && m.F1) + '</td>' +
        '<td class="num hide">' + fmt(m && m.P) + '</td>' +
        '<td class="num hide">' + fmt(m && m.R) + '</td>' +
        '<td class="num">' + int(sent) + '</td>' +
        '<td class="num">' + int(found) + '</td>' +
        '<td class="num hide">' + t.subs + '</td>' +
        (H ? '<td class="person">' + esc(p.name || '') + '<span class="detail">' + esc([p.org, p.email].filter(Boolean).join(' · ')) + '</span></td>' +
             '<td class="setting"><span class="detail" style="color:var(--text)">' + esc(b ? modelName(b) : '') +
             (b && b.n_called != null ? ' · 전체 ' + int(b.n_called) + '명에게 전화' : '') + '</span><span class="detail">' +
             esc(b ? settingText(b.setting) : '') + '</span></td>'
           : '<td class="hide"><span class="detail" style="color:var(--text)">' + esc(b ? modelName(b) : '') + '</span></td>') +
        '<td class="num hide">' + clock(t.last) + '</td></tr>';
    }).join('');
    $('tbody').innerHTML = body || '<tr><td colspan="' + cols + '" class="quiet" style="text-align:center;padding:1.4rem">아직 올라온 목록이 없습니다. 실습실에서 첫 목록을 제출하면 여기에 표시됩니다.</td></tr>';
  }

  // Plotly는 'Z'가 붙은 시각을 UTC로 그린다. 표와 같은 현지 시각 문자열로 바꿔 넘긴다
  function localTime(t) {
    var d = new Date(t), p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || undefined; }

  function drawPlot(list) {
    if (!window.Plotly || !$('plot')) return;
    var fin = isFinal(), leader = list[0] && list[0].best ? list[0].name : null;
    var pts = state.rows.filter(function (r) { return r.pub.F2 != null; });
    function trace(rows, name, color, size, sym) {
      return {
        x: rows.map(function (r) { return localTime(r.created_at); }),
        y: rows.map(function (r) { return r.pub.F2; }),
        text: rows.map(function (r) { return esc(r.nickname) + ' · 안내 ' + r.sent + '명 · 찾은 환자 ' + r.found + '명'; }),
        hovertemplate: '%{text}<br>공개 F2 %{y:.4f}<extra></extra>',
        mode: 'markers', type: 'scatter', name: name,
        marker: { size: size, color: color, opacity: .85, symbol: sym || 'circle', line: { width: 0 } }
      };
    }
    // 시간에 따른 전체 최고 기록(계단)
    var run = [], best = -1;
    pts.slice().sort(function (a, b) { return a.created_at.localeCompare(b.created_at); }).forEach(function (r) {
      if (r.pub.F2 > best) { best = r.pub.F2; run.push(r); }
    });
    var lastAt = state.rows.reduce(function (m, r) { return r.created_at > m ? r.created_at : m; }, '');
    if (run.length && lastAt > run[run.length - 1].created_at) run.push({ created_at: lastAt, pub: { F2: best } });   // 선을 마지막 제출 시각까지 잇는다
    var data = [
      { x: run.map(function (r) { return localTime(r.created_at); }), y: run.map(function (r) { return r.pub.F2; }),
        mode: 'lines', line: { shape: 'hv', color: css('--green'), width: 2, dash: 'dot' }, name: '그때까지의 최고', hoverinfo: 'skip' },
      trace(pts.filter(function (r) { return r.nickname !== leader; }), '제출한 목록', css('--muted'), 9),
      trace(pts.filter(function (r) { return r.nickname === leader; }), fin ? '최종 1등 팀' : '지금 1등 팀', css('--accent'), 12, 'diamond')
    ];
    Plotly.react('plot', data, {
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: css('--font'), color: css('--text-soft'), size: 12 },
      margin: { l: 48, r: 12, t: 8, b: 40 },
      xaxis: { title: { text: '제출 시각' }, gridcolor: css('--border-soft'), tickformat: '%H:%M', hoverformat: '%m월 %d일 %H:%M' },
      yaxis: { title: { text: '공개 F2' }, rangemode: 'tozero', gridcolor: css('--border-soft'), zeroline: false },
      legend: { orientation: 'h', y: 1.12, x: 0 },
      showlegend: true
    }, { displayModeBar: false, responsive: true });
  }

  function drawSummary(list) {
    var info = state.info || {};
    setText('kTeams', list.filter(function (t) { return t.subs; }).length + '팀');
    setText('kSubs', state.rows.length + '번');
    var top = list[0];
    setText('kBestLabel', isFinal() ? '최종 최고 F2' : '지금 최고 F2');
    setText('kBest', top && top.best ? fmt(score(top)) : '—');
    setText('bossSay', bossLine(list));
    var fc = $('finalChip'); if (fc) fc.hidden = !info.revealed;
    var seg = $('viewSeg'); if (seg) seg.hidden = !finalVisible();
    [].forEach.call(document.querySelectorAll('#viewSeg button'), function (b) { b.classList.toggle('on', b.dataset.v === state.view); });
    setText('boardLead', isFinal()
      ? '최종 순위입니다. 각 팀의 공개 최고 기록(같은 제출)을 최종 절반 ' + int(info.n_private) + '명으로 다시 채점했습니다. 변동은 공개 순위와 비교한 자리입니다.'
      : '공개 절반 ' + int(info.n_public) + '명으로 채점한 순위입니다. 팀마다 공개 F2 최고 기록이 점수이고, 같은 점수면 그 점수를 먼저 낸 팀이 앞섭니다.');
    // 미션 요약 칸(index.html에만 있다)
    setText('mPublic', int(info.n_public));
    setText('mPrivate', int(info.n_private));
    setText('mTest', info.n_public != null && info.n_private != null ? int(info.n_public + info.n_private) : '—');
    setText('mMaxSub', info.max_submissions != null ? info.max_submissions + '번' : '—');
    setText('mDeadline', deadlineAbs());
    if (info.title) { setText('eventTitle', info.title.replace(/^DS 건강검진센터\s*/, '') || info.title); }
    tick();
  }

  function draw() {
    var list = sorted(buildTeams());
    state.teams = list;
    drawSummary(list);
    drawPodium(list);
    drawTable(list);
    drawPlot(list);
    state.first = false;
  }

  // ── 읽기 ───────────────────────────────────────────────
  function status(ok, text) {
    var d = $('liveDot'); if (d) d.className = ok ? 'dot' : 'dot off';
    setText('liveText', text);
  }
  function notice(text) {
    var n = $('notice'); if (!n) return;
    n.hidden = !text; n.textContent = text || '';
  }

  function read() {
    if (!URL_ || !KEY) { status(false, '설정이 없어 순위판을 열 수 없습니다.'); notice('config.js에 SUPABASE_URL과 SUPABASE_KEY가 없습니다.'); return Promise.resolve(); }
    var jobs = [rpc('stroke_challenge_event_info', { event: EVENT }, 'GET'), rpc('stroke_challenge_board', { event: EVENT }, 'GET')];
    if (HOST && state.pass) {
      jobs.push(rpc('stroke_challenge_admin_board', { pass: state.pass, event: EVENT }, 'POST'));
      jobs.push(rpc('stroke_challenge_roster', { pass: state.pass, event: EVENT }, 'POST'));
      jobs.push(rpc('stroke_challenge_admin_info', { pass: state.pass, event: EVENT }, 'POST'));
    }
    return Promise.all(jobs).then(function (res) {
      var info = (res[0] || [])[0] || null;
      if (!info) {
        status(false, '행사를 찾지 못했습니다.');
        notice('행사 「' + EVENT + '」가 등록되어 있지 않습니다. 진행자가 행사를 등록하고 config.js의 EVENT를 맞추면 열립니다.');
        return;
      }
      var wasRevealed = state.info && state.info.revealed;
      state.info = info;
      var pub = res[1] || [];
      if (HOST && state.pass) {
        var adm = res[2] || [], ros = res[3] || [], ainfo = (res[4] || [])[0];
        if (!ainfo) {                                    // 암호가 틀리면 관리자 함수는 빈 배열을 돌려준다
          state.admin = false; state.roster = [];
          adminMsg('암호가 맞지 않습니다. 명단과 설정을 불러오지 못했습니다.', 'err');
        } else {
          if (!state.admin) adminMsg('명단 ' + ros.length + '팀과 제출 ' + adm.length + '건을 불러왔습니다.', 'ok');
          state.admin = true; state.roster = ros;
          state.info = info = ainfo;                     // 공개 전에도 pos_private가 들어 있다
          pub = adm;
        }
      }
      state.rows = pub;
      if (info.revealed && !wasRevealed && !state.viewChosen) state.view = 'final';
      if (!finalVisible()) state.view = 'public';
      notice('');
      status(true, '5초마다 새로 읽습니다 · ' + new Date().toLocaleTimeString('ko-KR'));
      draw();
    }).catch(function (e) {
      status(false, e.status === 404 ? '순위판이 아직 열리지 않았습니다.' : '읽지 못했습니다 (' + e.message + ')');
      if (e.status === 404) notice('순위판이 아직 열리지 않았습니다. 진행자가 schema.sql과 labels.sql을 실행하고 행사를 등록하면 열립니다.');
    });
  }

  // ── 진행자 기능 ─────────────────────────────────────────
  function adminMsg(t, kind) {
    var el = $('adminMsg'); if (!el) return;
    el.textContent = t || ''; el.className = 'msg' + (kind ? ' ' + kind : '');
  }
  function setEvent(args, okText) {
    if (!state.pass) { adminMsg('먼저 관리자 암호를 넣습니다.', 'err'); return; }
    var body = { pass: state.pass, event: EVENT };
    Object.keys(args).forEach(function (k) { body[k] = args[k]; });
    rpc('stroke_challenge_set_event', body, 'POST').then(function () {
      adminMsg(okText, 'ok'); return read();
    }).catch(function (e) {
      adminMsg(/bad_pass/.test(e.message) ? '암호가 맞지 않습니다.' : '바꾸지 못했습니다 (' + e.message + ')', 'err');
    });
  }
  function csvCell(v) {
    var s = v == null ? '' : String(v);
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;          // 팀명 같은 입력값이 스프레드시트 수식으로 실행되지 않게 한다
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function buildCsv() {
    var rows = [['팀명', '소속', '성명', '이메일', '공개 순위', '공개 F2', '최종 순위', '최종 F2', '안내 인원', '찾은 환자', '제출 횟수']];
    var byFinal = !!(state.info && state.info.revealed);   // 최종 점수를 공개했으면 최종 순위 순, 아니면 공개 순위 순
    state.teams.slice().sort(function (a, b) {
      var ra = byFinal ? a.priRank : a.pubRank, rb = byFinal ? b.priRank : b.pubRank;
      return (ra || 1e9) - (rb || 1e9) || a.first.localeCompare(b.first);
    }).forEach(function (t) {
      var b = t.best, p = t.person || {};
      rows.push([t.name, p.org, p.name, p.email, t.pubRank, b ? fmt(b.pub.F2) : '', t.priRank, b && b.pri.F2 != null ? fmt(b.pri.F2) : '',
                 b ? b.n_called : '', b && b.found_private != null ? b.found + b.found_private : '', t.subs]);
    });
    return '﻿' + rows.map(function (r) { return r.map(csvCell).join(','); }).join('\r\n') + '\r\n';
  }
  function boardUrl() { return location.href.replace(/[?#].*$/, '').replace(/host\.html$/, ''); }
  function mailHref() {
    var emails = state.roster.map(function (p) { return p.email; }).filter(Boolean);
    var subject = 'DS 건강검진센터 인턴 미션 최종 결과';
    var body = 'DS 건강검진센터 인턴 미션의 최종 결과가 순위판에 공개되었습니다.\n순위판: ' + boardUrl() + '\n\n참여해 주셔서 감사합니다.';
    return 'mailto:?bcc=' + emails.map(encodeURIComponent).join(',') +
      '&subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
  }
  window.__challenge = { buildCsv: buildCsv, mailHref: mailHref, state: state, read: read };   // 점검용

  function wireHost() {
    state.pass = load(PASS_KEY);
    if ($('passInput') && state.pass) $('passInput').value = state.pass;
    $('passForm').addEventListener('submit', function (e) {
      e.preventDefault();
      state.pass = $('passInput').value.trim(); state.admin = false; state.first = true;
      store(PASS_KEY, state.pass || null);
      adminMsg(state.pass ? '확인하는 중입니다.' : '', '');
      read();
    });
    $('passClear').addEventListener('click', function () {
      state.pass = ''; state.admin = false; state.roster = []; $('passInput').value = ''; store(PASS_KEY, null);
      adminMsg('이 브라우저에서 암호를 지웠습니다.', 'ok'); read();
    });
    $('btnReveal').addEventListener('click', function () {
      if (confirm('최종 점수를 참가자 순위판에 공개합니다. 계속할까요?')) setEvent({ revealed_: true }, '최종 점수를 공개했습니다.');
    });
    $('btnHide').addEventListener('click', function () { setEvent({ revealed_: false }, '최종 점수 공개를 취소했습니다.'); });
    $('btnDeadline').addEventListener('click', function () {
      var v = $('deadlineInput').value;
      if (!v) { adminMsg('마감 시각을 고릅니다.', 'err'); return; }
      setEvent({ deadline_: new Date(v).toISOString() }, '마감 시각을 바꿨습니다. ' + new Date(v).toLocaleString('ko-KR', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }));
    });
    $('btnClearDeadline').addEventListener('click', function () { setEvent({ clear_deadline: true }, '마감을 해제했습니다.'); });
    $('btnCsv').addEventListener('click', function () {
      if (!state.admin) { adminMsg('암호를 넣어 명단을 불러온 뒤 내려받습니다.', 'err'); return; }
      var blob = new Blob([buildCsv()], { type: 'text/csv;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = '인턴미션_최종결과_' + EVENT + '.csv';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    });
    $('mailLink').addEventListener('click', function (e) {
      if (!state.admin || !state.roster.length) { e.preventDefault(); adminMsg('암호를 넣어 명단을 불러온 뒤 메일을 씁니다.', 'err'); return; }
      this.href = mailHref();
    });
  }

  function wireCommon() {
    var seg = $('viewSeg');
    if (seg) seg.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      state.view = b.dataset.v; state.viewChosen = true; state.first = true;
      draw();
    });
  }

  wireCommon();
  if (HOST) wireHost();
  read();
  setInterval(read, 5000);
  setInterval(tick, 1000);
})();
