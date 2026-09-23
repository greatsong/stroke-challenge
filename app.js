// 뇌졸중 예측 챌린지 순위판 — 수파베이스에서 읽어 시상대·순위·이력을 그린다.
// 설정은 config.js(CHALLENGE_CONFIG)에서 읽는다. 공개용 키만 들어 있다.
//
// 규칙: 겨루는 동안은 F1로 순위를 매긴다(공개 순위). 마감 뒤 같은 기록(팀의 F1 최고 기록)을
// F2(재현율을 정밀도의 두 배로 치는 식)로 다시 매겨 최종 순위를 낸다. 점수가 같으면 먼저 올린 팀이 앞선다.
(function () {
  var 설정 = window.CHALLENGE_CONFIG || {};
  var 주소 = 설정.SUPABASE_URL, 키 = 설정.SUPABASE_KEY;
  var 표이름 = 설정.TABLE || 'stroke_challenge_log', 행사 = 설정.EVENT || '';
  var 교사용 = (window.CHALLENGE_MODE === 'teacher');   // 진행자용(host.html)에서만 설정과 확인 결과를 보여 준다
  var 공개됨 = 교사용 || 설정.REVEAL === true;          // 최종(F2) 순위를 볼 수 있는가
  var 모드 = 'F1', 지난최고 = {}, 첫판 = true;
  var $ = function (id) { return document.getElementById(id); };

  // ── 올라온 기록이 실제로 나올 수 있는 값인지 정답표와 대조한다 ──────────
  var 속성번호 = { '나이': 0, '평균 혈당': 1, '체질량지수': 2, '고혈압': 3, '심장병': 4,
                   '결혼 여부': 5, '현재 흡연': 6, '자영업': 7, '남성': 8 };

  function 열쇠(r) {
    var 번호 = r.inputs.split(' · ').map(function (x) { return 속성번호[x.trim()]; });
    if (번호.some(function (n) { return n === undefined; })) return null;
    번호.sort(function (a, b) { return a - b; });
    var 이름 = r.model || '';
    var 모델 = (이름.indexOf('로지스틱') >= 0 || 이름.indexOf('확률') >= 0) ? 'L' : 'T';
    return (r.missing === '지운다' ? '1' : '0') + (r.weighted ? '1' : '0') +
           번호.join('') + 모델 + (모델 === 'T' ? String(r.depth) : '');
  }

  function 확인(r) {
    var K = window.CHALLENGE_KEY;
    if (!K) return null;                                 // 정답표가 없으면 판정하지 않는다
    var k = 열쇠(r);
    var 줄 = k && K.key[k];
    if (!줄) return false;
    var 자리 = Math.round(Number(r.threshold) / 0.05) - 1;   // 기준값 0.05~0.95가 차례로 들어 있다
    var 정답 = 줄[자리];
    return !!(정답 && 정답[0] === r.sent && 정답[1] === r.found);
  }

  function 지표값(r, 이름) {                           // 올라온 값 대신 안내 인원·찾아낸 환자로 다시 계산한다
    var K = window.CHALLENGE_KEY, 머리 = K && K.head[r.missing === '지운다' ? '1' : '0'];
    if (!머리) {
      if (이름 === 'F2') return null;
      return r[{ '정확도': 'accuracy', '재현율': 'recall', '정밀도': 'precision', 'F1': 'f1' }[이름]];
    }
    var TP = r.found, FP = r.sent - r.found, FN = 머리.pos - r.found, TN = 머리.n - 머리.pos - FP;
    var P = r.sent ? TP / r.sent : null, R = TP / 머리.pos;
    if (이름 === '정확도') return (TP + TN) / 머리.n;
    if (이름 === '재현율') return R;
    if (이름 === '정밀도') return P;
    if (P == null || P + R === 0) return null;
    if (이름 === 'F2') return 5 * P * R / (4 * P + R);
    return 2 * P * R / (P + R);
  }

  function 값(v) { return v == null ? -1 : v; }
  function 소수(v) { return v == null ? '—' : Number(v).toFixed(4); }
  function 글자(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function 시각(t) {
    return new Date(t).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  }
  function 설정글(r) {
    return r.inputs + ' · 질문 ' + r.depth + '번 · 기준값 ' + Number(r.threshold).toFixed(2) +
           (r.missing === '지운다' ? ' · 빈 값 지움' : ' · 빈 값 채움');
  }
  function 모델글(r) { return 교사용 ? (r.model + ' · ' + 설정글(r)) : (r.model || ''); }

  // ── 팀별로 모은다. 최고 = F1이 가장 높은 기록(같으면 먼저 올린 것). 그 기록의 F2가 최종 점수다 ──
  function 사람별(줄들) {
    var 표 = {};
    줄들.forEach(function (r) {
      var it = 표[r.nickname] || (표[r.nickname] = { 팀명: r.nickname, 시도: 0, 의심: 0,
                                                     최고: null, F2최고: null, 마지막: r.created_at });
      it.시도 += 1;
      if (r.created_at > it.마지막) it.마지막 = r.created_at;
      if (r.확인 === false) { it.의심 += 1; return; }   // 맞지 않는 기록은 최고로 치지 않는다
      if (!it.최고 || r.F1 > it.최고.F1) it.최고 = r;
      if (!it.F2최고 || r.F2 > it.F2최고.F2) it.F2최고 = r;
    });
    var 목록 = Object.values(표);
    if (!교사용) {                                      // 참가자 화면에서는 맞지 않는 기록만 낸 팀을 아예 뺀다
      목록 = 목록.filter(function (it) { return it.최고 || it.의심 === 0; });
    }
    function 정렬(이름) {
      return function (a, b) {
        if (!a.최고 || !b.최고) return (b.최고 ? 1 : 0) - (a.최고 ? 1 : 0) || a.마지막.localeCompare(b.마지막);
        return (값(b.최고[이름]) - 값(a.최고[이름])) || a.최고.created_at.localeCompare(b.최고.created_at);
      };
    }
    목록.slice().sort(정렬('F1')).forEach(function (it, i) { it.공개순위 = it.최고 ? i + 1 : null; });
    목록.slice().sort(정렬('F2')).forEach(function (it, i) { it.최종순위 = it.최고 ? i + 1 : null; });
    return 목록.sort(정렬(모드));
  }

  function 점수(it) { return it.최고 ? it.최고[모드] : null; }
  function 순위(it) { return 모드 === 'F1' ? it.공개순위 : it.최종순위; }

  function 시상대그리기(목록) {
    var 메달표 = ['🥇', '🥈', '🥉'];
    $('시상대').innerHTML = [0, 1, 2].map(function (i) {
      var it = 목록[i];
      if (!it || !it.최고) {
        return '<div class="pod empty"><div class="medal">' + 메달표[i] + '</div>' +
               '<div class="who">비어 있습니다</div><div class="big">—</div></div>';
      }
      var b = it.최고;
      return '<div class="pod' + (i === 0 ? ' first' : '') + '">' +
        '<div class="medal">' + 메달표[i] + '</div>' +
        '<div class="who">' + 글자(it.팀명) + '</div>' +
        '<div class="cls">시도 ' + it.시도 + '번' +
          (모드 === 'F2' ? ' · 공개 ' + it.공개순위 + '위' : '') + '</div>' +
        '<div class="big">' + 소수(점수(it)) + '<span> ' + 모드 + '</span></div>' +
        '<div class="set">찾아낸 환자 ' + b.found + '명 · 안내 ' + b.sent.toLocaleString() + '명</div>' +
        '<div class="set">정밀도 ' + 소수(b.정밀도) + ' · 재현율 ' + 소수(b.재현율) +
          (모드 === 'F2' ? ' · F1 ' + 소수(b.F1) : '') + '</div>' +
        '<div class="set">' + 글자(모델글(b)) + '</div></div>';
    }).join('');
  }

  function 순위그리기(목록) {
    var 새로움 = {};
    목록.forEach(function (it) {
      var 지난 = 지난최고[it.팀명];
      if (!첫판 && it.최고 && 지난 && 값(점수(it)) > 값(지난)) 새로움[it.팀명] = true;
      지난최고[it.팀명] = 점수(it);
    });
    첫판 = false;

    var 최종 = 모드 === 'F2';
    $('표머리').innerHTML = '<tr>' +
      '<th class="rank">#</th>' + (최종 ? '<th class="num">변동</th>' : '') +
      '<th>팀명</th><th>' + 모드 + '</th>' + (최종 ? '<th class="num">F1</th>' : '') +
      '<th class="num">찾아낸 환자</th><th class="num">안내</th>' +
      '<th class="num hide">정밀도</th><th class="num hide">재현율</th>' +
      '<th class="hide">' + (교사용 ? '설정' : '모델') + '</th><th class="num">시도</th><th class="num hide">마지막</th></tr>';

    $('순위').innerHTML = 목록.map(function (it) {
      var b = it.최고, 등수 = 순위(it);
      var 폭 = b ? Math.min(100, Math.round(값(점수(it)) / 0.5 * 100)) : 0;   // 0.5를 막대 끝으로 둔다
      var 메달 = 등수 ? ['🥇', '🥈', '🥉'][등수 - 1] : null;
      var 변동 = '';
      if (최종 && b) {
        var d = it.공개순위 - it.최종순위;
        변동 = d > 0 ? '<span class="up">▲' + d + '</span>' : d < 0 ? '<span class="down">▼' + (-d) + '</span>' : '<span class="same">—</span>';
      }
      var 딴기록 = (최종 && b && it.F2최고 && it.F2최고 !== b && 값(it.F2최고.F2) > 값(b.F2))
        ? '<div class="set2">이 팀이 올린 기록 중 F2 최고는 ' + 소수(it.F2최고.F2) + ' (찾아낸 환자 ' + it.F2최고.found + '명)</div>' : '';
      return '<tr class="' + (새로움[it.팀명] ? 'fresh' : '') + '">' +
        '<td class="rank' + (메달 ? ' m' : '') + '">' + (b ? (메달 || 등수) : '—') + '</td>' +
        (최종 ? '<td class="num">' + 변동 + '</td>' : '') +
        '<td class="nick">' + 글자(it.팀명) +
          (교사용 && it.의심 ? '<span class="badge3">확인 필요 ' + it.의심 + '건</span>' : '') + 딴기록 + '</td>' +
        '<td><div class="bar"><i style="width:' + 폭 + '%"></i><b>' + (b ? 소수(점수(it)) : (it.의심 ? '확인 필요' : '—')) + '</b></div></td>' +
        (최종 ? '<td class="num">' + (b ? 소수(b.F1) : '—') + '</td>' : '') +
        '<td class="num">' + (b ? b.found + '명' : '—') + '</td>' +
        '<td class="num">' + (b ? b.sent.toLocaleString() + '명' : '—') + '</td>' +
        '<td class="num hide">' + (b ? 소수(b.정밀도) : '—') + '</td>' +
        '<td class="num hide">' + (b ? 소수(b.재현율) : '—') + '</td>' +
        '<td class="hide set2">' + (b ? 글자(모델글(b)) : '—') + '</td>' +
        '<td class="num">' + it.시도 + '</td>' +
        '<td class="num hide">' + 시각(it.마지막) + '</td></tr>';
    }).join('') || '<tr><td colspan="12" class="quiet">아직 올라온 기록이 없습니다. 실습실에서 첫 기록을 올려 보세요.</td></tr>';
  }

  function 이력그리기(대상) {
    function 점(줄, 이름, 색, 투명, 크기) {
      return { x: 줄.map(function (r) { return r.created_at; }),
               y: 줄.map(function (r) { return r[모드]; }),
               text: 줄.map(function (r) { return r.nickname + ' · 찾아낸 환자 ' + r.found + '명 · 안내 ' + r.sent + '명'; }),
               hovertemplate: '%{text}<br>' + 모드 + ' %{y:.4f}<extra></extra>',
               mode: 'markers', type: 'scatter', name: 이름,
               marker: { size: 크기, color: 색, opacity: 투명, line: { width: 0 } } };
    }
    Plotly.react('plot', [
      점(대상.filter(function (r) { return r.확인 !== false; }), '올린 기록', '#e8930c', 0.8, 10),
      점(교사용 ? 대상.filter(function (r) { return r.확인 === false; }) : [], '확인 필요', '#e45756', 0.8, 11)
    ], {
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: 'Apple SD Gothic Neo, sans-serif', color: '#6b5836', size: 12 },
      margin: { l: 52, r: 16, t: 10, b: 44 },
      xaxis: { title: '올린 시각', gridcolor: '#f7edcf', tickformat: '%H:%M', hoverformat: '%H:%M' },
      yaxis: { title: 모드, rangemode: 'tozero', gridcolor: '#f7edcf' },
      legend: { orientation: 'h', y: 1.15, x: 0 }
    }, { displayModeBar: false, responsive: true });
  }

  function 그리기(전체) {
    전체.forEach(function (r) {
      r.확인 = 확인(r);
      r.F1 = 지표값(r, 'F1'); r.F2 = 지표값(r, 'F2');
      r.정밀도 = 지표값(r, '정밀도'); r.재현율 = 지표값(r, '재현율');
    });
    var 목록 = 사람별(전체);
    시상대그리기(목록);
    $('s인원').textContent = 목록.length + '팀';
    $('s시도').textContent = 전체.length + '번';
    $('s최고').textContent = (목록[0] && 목록[0].최고) ? 소수(점수(목록[0])) : '—';
    $('s최고제목').textContent = 모드 === 'F1' ? '지금 최고 F1' : '최종 최고 F2';
    var 의심칸 = $('s의심');
    if (의심칸) {
      var 의심 = 전체.filter(function (r) { return r.확인 === false; }).length;
      의심칸.textContent = 의심 + '건';
      의심칸.style.color = 의심 ? 'var(--red)' : '';
    }
    순위그리기(목록);
    이력그리기(전체);
  }

  function 읽기() {
    if (!주소 || !키) { $('상태').textContent = '설정이 없어 순위판을 열 수 없습니다.'; $('불').className = 'dot off'; return; }
    fetch(주소 + '/rest/v1/' + 표이름 + '?select=*&order=created_at.asc&limit=3000' +
          (행사 ? '&event_id=eq.' + encodeURIComponent(행사) : ''),
          { headers: { apikey: 키, Authorization: 'Bearer ' + 키 } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (줄들) {
        $('불').className = 'dot';
        $('상태').textContent = '5초마다 새로 읽습니다 · ' + new Date().toLocaleTimeString('ko-KR');
        그리기(줄들);
      })
      .catch(function (e) {
        $('불').className = 'dot off';
        $('상태').textContent = (e.message === '404')
          ? '순위판이 아직 열리지 않았습니다. 진행자가 schema.sql을 수파베이스에서 한 번 실행하면 열립니다.'
          : '읽지 못했습니다 (' + e.message + ')';
      });
  }

  var 모드칸 = $('모드');
  if (!공개됨) 모드칸.style.display = 'none';            // 마감 전 참가자 화면에는 F1 순위판만 있다
  모드칸.addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    [].forEach.call(this.querySelectorAll('button'), function (x) { x.classList.remove('on'); });
    b.classList.add('on'); 모드 = b.dataset.v; 첫판 = true; 지난최고 = {};
    $('설명').textContent = 모드 === 'F1'
      ? '겨루는 동안의 순위입니다. F1이 높을수록 앞서고, 같으면 그 점수를 먼저 올린 팀이 앞섭니다.'
      : '최종 순위입니다. 각 팀의 F1 최고 기록을 F2(재현율을 정밀도의 두 배로 치는 식)로 다시 매겼습니다. 변동은 공개 순위와 비교한 자리입니다.';
    읽기();
  });
  읽기();
  setInterval(읽기, 5000);
})();
