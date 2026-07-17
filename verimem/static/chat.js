(function () {
  "use strict";
  const conv = document.getElementById('conversation');
  const status = document.getElementById('status');
  const runBtn = document.getElementById('run');
  const planBtn = document.getElementById('plan');
  const stopBtn = document.getElementById('stop');
  const sleepBtn = document.getElementById('sleep');
  const clearBtn = document.getElementById('clear');
  const taskBox = document.getElementById('task');
  const llmBadge = document.getElementById('active-llm');

  const HISTORY_KEY = 'engram-chat-history';
  let abortCtrl = null;

  function renderMarkdown(text, parent) {
    if (!text) { parent.appendChild(document.createTextNode('')); return; }
    const lines = text.split('\n');
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const fenceMatch = line.match(/^```(\w*)\s*$/);
      if (fenceMatch) {
        const lang = fenceMatch[1] || '';
        const codeLines = [];
        i++;
        while (i < lines.length && !lines[i].match(/^```\s*$/)) {
          codeLines.push(lines[i]); i++;
        }
        i++;
        const pre = document.createElement('pre');
        pre.style.background = '#0a0d12';
        pre.style.padding = '10px';
        pre.style.borderRadius = '4px';
        pre.style.overflowX = 'auto';
        pre.style.border = '1px solid #21262d';
        if (lang) {
          const tag = document.createElement('div');
          tag.textContent = lang;
          tag.style.color = 'var(--dim)';
          tag.style.fontSize = '11px';
          tag.style.marginBottom = '4px';
          pre.appendChild(tag);
        }
        const codeNode = document.createElement('code');
        codeNode.textContent = codeLines.join('\n');
        pre.appendChild(codeNode);
        parent.appendChild(pre);
        continue;
      }
      const p = document.createElement('div');
      p.style.whiteSpace = 'pre-wrap';
      const re = /`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*/g;
      let last = 0; let m;
      while ((m = re.exec(line))) {
        if (m.index > last) p.appendChild(document.createTextNode(line.slice(last, m.index)));
        if (m[1] !== undefined) {
          const c = document.createElement('code');
          c.textContent = m[1];
          c.style.background = '#0a0d12';
          c.style.padding = '1px 5px';
          c.style.borderRadius = '3px';
          c.style.fontSize = '12px';
          p.appendChild(c);
        } else if (m[2] !== undefined) {
          const b = document.createElement('strong');
          b.textContent = m[2];
          p.appendChild(b);
        } else if (m[3] !== undefined) {
          const it = document.createElement('em');
          it.textContent = m[3];
          p.appendChild(it);
        }
        last = m.index + m[0].length;
      }
      if (last < line.length) p.appendChild(document.createTextNode(line.slice(last)));
      parent.appendChild(p);
      i++;
    }
  }

  function loadActiveLLM() {
    fetch('/api/settings/active').then(r => r.json()).then(d => {
      llmBadge.textContent = (d.provider || '?') + ' · ' + (d.executor_model || 'default');
      llmBadge.style.borderColor = d.configured ? 'var(--ok)' : 'var(--bad)';
    }).catch(() => { llmBadge.textContent = '?'; });
  }

  function loadHistory() {
    try {
      const items = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
      conv.textContent = '';
      items.forEach(item => {
        if (item.kind === 'turn') renderTurn(item.task, item.data, item.ms);
        else if (item.kind === 'sleep') renderSleep(item.data);
      });
    } catch (e) {/*ignore*/}
  }

  function saveHistory(item) {
    try {
      const items = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
      items.push(item);
      while (items.length > 30) items.shift();
      localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
    } catch (e) {/*ignore*/}
  }

  // FORGIA #191 — XSS hardening:
  //  - dangerous attribute keys (innerHTML, outerHTML, etc.) are refused
  //  - href values matching `javascript:` / `data:` schemes are refused
  //  - children are always wrapped in createTextNode (no HTML reinterpretation)
  const _DANGEROUS_ATTRS = new Set([
    'innerHTML', 'outerHTML', 'insertAdjacentHTML', 'srcdoc',
    'onload', 'onclick', 'onerror', 'onfocus', 'onmouseover',
  ]);
  const _UNSAFE_URL_RE = /^\s*(javascript|data|vbscript):/i;

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (_DANGEROUS_ATTRS.has(k)) continue;  // silently drop XSS sinks
        if (k === 'style') Object.assign(n.style, attrs[k]);
        else if (k === 'class') n.className = attrs[k];
        else if (k === 'href') {
          const v = String(attrs[k] || '');
          if (_UNSAFE_URL_RE.test(v)) continue;  // refuse javascript:/data:
          n.setAttribute('href', v);
        }
        else n.setAttribute(k, attrs[k]);  // setAttribute, not assignment
      }
    }
    for (const k of kids) {
      if (k == null) continue;
      // Always treat strings as text — never as HTML.
      n.appendChild(typeof k === 'string' ? document.createTextNode(k) : k);
    }
    return n;
  }

  function tag(text, href) {
    const a = el('a', {class: 'tag'}, text);
    if (href) a.setAttribute('href', href);
    return a;
  }

  function prepend(card) {
    conv.insertBefore(card, conv.firstChild);
  }

  function renderTurn(task, data, ms) {
    const card = el('div', {class: 'card'});
    card.appendChild(el('div', {style: {color: 'var(--dim)', fontSize: '12px'}}, 'YOU'));
    const youText = el('div', {style: {margin: '4px 0 12px 0', whiteSpace: 'pre-wrap'}}, task);
    card.appendChild(youText);

    const meta = el('div', {style: {color: 'var(--dim)', fontSize: '12px'}}, 'AGENT ');
    const oc = el('span', {class: data.outcome}, '[' + data.outcome + ']');
    meta.appendChild(oc);
    meta.appendChild(document.createTextNode(
      ' — ' + data.steps + ' steps, ' + data.tokens + ' tokens, ' + ms + 'ms — '));
    meta.appendChild(el('a', {href: '/episodes/' + data.episode_id}, 'replay full trajectory →'));
    card.appendChild(meta);

    const ansBox = el('div', {style: {marginTop: '8px'}});
    renderMarkdown(data.answer || '(no answer)', ansBox);
    card.appendChild(ansBox);

    const skillsRow = el('div', {style: {marginTop: '6px'}});
    skillsRow.appendChild(el('b', {style: {color: 'var(--dim)', fontSize: '12px'}}, 'Skills applied: '));
    if (data.skills_used && data.skills_used.length) {
      data.skills_used.forEach(s => {
        skillsRow.appendChild(tag(
          s.name + ' (f=' + s.fitness.toFixed(2) + ')',
          '/skills/' + s.id
        ));
        skillsRow.appendChild(document.createTextNode(' '));
      });
    } else {
      skillsRow.appendChild(el('span', {class: 'tag'}, 'no skills retrieved'));
    }
    card.appendChild(skillsRow);

    // Feedback bar — user signal feeds the same Bayesian fitness machinery.
    // Up-vote = +1 success trial on each applied skill; down-vote = +1 failure
    // (and flips episode outcome → failure if it was originally a success).
    const fbRow = el('div', {style: {marginTop: '10px',
      display: 'flex', gap: '6px', alignItems: 'center'}});
    fbRow.appendChild(el('span', {style: {color: 'var(--dim)', fontSize: '12px'}},
                           'Was this useful?'));
    const fbStatus = el('span', {style: {color: 'var(--dim)', fontSize: '12px',
                                         marginLeft: '6px'}}, '');
    function sendFb(kind) {
      fetch('/api/feedback', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({episode_id: data.episode_id, kind: kind}),
      }).then(r => r.json()).then(j => {
        if (j.error) {
          fbStatus.textContent = 'error: ' + j.error;
          fbStatus.style.color = 'var(--bad)';
        } else {
          fbStatus.textContent = (kind === 'up' ? '👍 ' : '👎 ') +
            'recorded · ' + j.skills_updated + ' skill(s) updated';
          fbStatus.style.color = (kind === 'up' ? 'var(--ok)' : 'var(--bad)');
          upBtn.disabled = true; downBtn.disabled = true;
          upBtn.style.opacity = '0.4'; downBtn.style.opacity = '0.4';
        }
      }).catch(e => {
        fbStatus.textContent = 'network error';
        fbStatus.style.color = 'var(--bad)';
      });
    }
    const upBtn = el('button',
      {style: {background: '#21262d', color: 'var(--ok)',
                border: '1px solid #30363d', padding: '4px 10px',
                borderRadius: '4px', cursor: 'pointer', fontSize: '13px'},
       title: 'Boost fitness on the skills used here'},
      '👍 useful');
    upBtn.onclick = () => sendFb('up');
    const downBtn = el('button',
      {style: {background: '#21262d', color: 'var(--bad)',
                border: '1px solid #30363d', padding: '4px 10px',
                borderRadius: '4px', cursor: 'pointer', fontSize: '13px'},
       title: 'Penalise fitness on the skills used here (reverses success)'},
      '👎 not useful');
    downBtn.onclick = () => sendFb('down');
    fbRow.appendChild(upBtn);
    fbRow.appendChild(downBtn);
    fbRow.appendChild(fbStatus);
    card.appendChild(fbRow);
    prepend(card);
  }

  function renderError(msg) {
    const card = el('div', {class: 'card'});
    card.appendChild(el('div', {style: {color: 'var(--bad)'}}, 'Error: ' + msg));
    prepend(card);
  }

  function renderSleep(data) {
    const card = el('div', {class: 'card'});
    const hd = el('div', {style: {color: '#a78bfa', fontWeight: '700'}}, '\u{1F319} SLEEP CYCLE');
    const wrap = el('div', {style: {borderLeft: '3px solid #7c3aed', paddingLeft: '10px'}}, hd);
    const tbl = el('table', {style: {marginTop: '8px'}});
    function row(k, v) {
      const tr = el('tr', null,
        el('th', null, k),
        el('td', null, String(v)));
      tbl.appendChild(tr);
    }
    row('replayed episodes', data.n_episodes_replayed);
    row('clusters', data.n_clusters);
    row('NREM skills (new)', data.n_nrem_skills);
    row('REM hybrids (new)', data.n_rem_skills);
    row('semantic facts', data.n_facts);
    row('promoted', (data.promoted || []).length);
    row('retired', (data.retired || []).length);
    row('merged', (data.merged || []).length);
    row('duration', data.duration_s.toFixed(1) + 's · ' + data.tokens_used + ' tokens');
    wrap.appendChild(tbl);
    const links = el('div', {style: {marginTop: '8px'}});
    links.appendChild(el('a', {href: '/skills'}, 'view skills →'));
    links.appendChild(document.createTextNode(' · '));
    links.appendChild(el('a', {href: '/lineage'}, 'view lineage →'));
    wrap.appendChild(links);
    card.appendChild(wrap);
    prepend(card);
  }

  async function runTask() {
    const task = taskBox.value.trim();
    if (!task) return;
    runBtn.disabled = true;
    stopBtn.style.display = 'inline-block';
    abortCtrl = new AbortController();
    status.textContent = 'Thinking… (real LLM call, can take 5-30s)';
    const t0 = performance.now();
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task}),
        signal: abortCtrl.signal,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
      const ms = Math.round(performance.now() - t0);
      renderTurn(task, data, ms);
      saveHistory({kind: 'turn', task: task, data: data, ms: ms});
      status.textContent = 'Done in ' + ms + 'ms';
      taskBox.value = '';
      loadActiveLLM();
    } catch (e) {
      if (e.name === 'AbortError') {
        status.textContent = 'Stopped by user.';
      } else {
        renderError(String(e && e.message || e));
        status.textContent = 'Error';
      }
    } finally {
      runBtn.disabled = false;
      stopBtn.style.display = 'none';
      abortCtrl = null;
    }
  }

  async function runSleep() {
    status.textContent = 'Running sleep consolidation cycle…';
    const t0 = performance.now();
    try {
      const r = await fetch('/api/sleep', {method: 'POST'});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
      const ms = Math.round(performance.now() - t0);
      renderSleep(data);
      status.textContent = 'Sleep complete in ' + ms + 'ms';
    } catch (e) {
      renderError('sleep: ' + String(e && e.message || e));
      status.textContent = 'Error';
    }
  }

  async function runSleepWithSave() {
    await runSleep();
    // sleep already renders; we still want to persist the history entry.
    // (Simpler approach: re-fetch last conversation card and skip persistence here.)
  }

  function renderPlan(task, plan, model) {
    const card = el('div', {class: 'card'});
    card.style.borderLeft = '3px solid #0891b2';
    card.appendChild(el('div', {style: {color: '#67e8f9', fontSize: '12px', fontWeight: '700'}},
      '📋 PROPOSED PLAN  · ' + (model || '')));
    const youText = el('div', {style: {margin: '4px 0 12px 0', whiteSpace: 'pre-wrap',
      color: 'var(--dim)', fontSize: '13px'}}, 'Task: ' + task);
    card.appendChild(youText);
    const planBox = el('div', {style: {marginTop: '4px'}});
    renderMarkdown(plan, planBox);
    card.appendChild(planBox);
    const btnRow = el('div', {style: {marginTop: '12px', display: 'flex', gap: '8px'}});
    const approveBtn = el('button', {style: {
      background: 'var(--ok)', color: '#0e1116', border: '0',
      padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: '700',
    }}, '✓ Approve & execute');
    approveBtn.addEventListener('click', () => {
      taskBox.value = task + '\n\n[Approved plan]\n' + plan;
      runTask();
      btnRow.textContent = '';
      btnRow.appendChild(el('span', {style: {color: 'var(--dim)'}}, 'executing approved plan…'));
    });
    const rejectBtn = el('button', {style: {
      background: '#21262d', color: 'var(--text)', border: '1px solid #30363d',
      padding: '8px 16px', borderRadius: '4px', cursor: 'pointer',
    }}, '✗ Reject');
    rejectBtn.addEventListener('click', () => {
      btnRow.textContent = '';
      btnRow.appendChild(el('span', {style: {color: 'var(--dim)'}}, 'plan rejected'));
    });
    btnRow.appendChild(approveBtn);
    btnRow.appendChild(rejectBtn);
    card.appendChild(btnRow);
    prepend(card);
  }

  async function runPlan() {
    const task = taskBox.value.trim();
    if (!task) return;
    planBtn.disabled = true;
    status.textContent = 'Planning…';
    try {
      const r = await fetch('/api/plan', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task}),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
      renderPlan(task, data.plan, data.model);
      status.textContent = 'Plan ready · review and approve';
    } catch (e) {
      renderError('plan: ' + (e.message || e));
      status.textContent = 'Error';
    } finally {
      planBtn.disabled = false;
    }
  }

  runBtn.addEventListener('click', runTask);
  planBtn.addEventListener('click', runPlan);
  sleepBtn.addEventListener('click', runSleep);
  stopBtn.addEventListener('click', () => { if (abortCtrl) abortCtrl.abort(); });
  clearBtn.addEventListener('click', () => {
    if (!confirm('Clear local conversation history? Episodes in the database remain.')) return;
    localStorage.removeItem(HISTORY_KEY);
    conv.textContent = '';
    status.textContent = 'history cleared';
  });
  taskBox.addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); runTask(); }
  });

  loadActiveLLM();
  loadHistory();
  // Refresh active LLM badge every few seconds in case user switches in /settings
  setInterval(loadActiveLLM, 5000);
})();
