(function () {
  "use strict";

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (k === 'style') Object.assign(n.style, attrs[k]);
        else if (k === 'class') n.className = attrs[k];
        else if (k === 'href') n.setAttribute('href', attrs[k]);
        else if (k === 'onclick') n.addEventListener('click', attrs[k]);
        else n[k] = attrs[k];
      }
    }
    for (const k of kids) {
      if (k == null) continue;
      n.appendChild(typeof k === 'string' ? document.createTextNode(k) : k);
    }
    return n;
  }

  const $ = id => document.getElementById(id);
  const status = $('status');

  async function loadActive() {
    const r = await fetch('/api/settings/active');
    const d = await r.json();
    const summary = $('active-summary');
    summary.textContent = '';
    summary.appendChild(el('div', null,
      'provider: ', el('b', null, d.provider || '(none)'),
      '   |   configured: ', el('b', {style: {color: d.configured ? 'var(--ok)' : 'var(--bad)'}},
        d.configured ? 'yes' : 'no')));
    summary.appendChild(el('div', null,
      'executor: ', d.executor_model || '(default)',
      '   |   dreamer: ', d.dreamer_model || '(default)',
      '   |   critic: ', d.critic_model || '(default)'));
  }

  async function loadProviders() {
    const r = await fetch('/api/settings/providers');
    const d = await r.json();
    const sel = $('provider');
    sel.textContent = '';
    sel.appendChild(el('option', {value: ''}, '(autodetect)'));
    d.providers.forEach(p => {
      const tag = p.configured ? '✓ ' : '  ';
      sel.appendChild(el('option', {value: p.name}, tag + p.name + ' — ' + (p.env || 'local')));
    });
    if (d.current_settings && d.current_settings.provider) sel.value = d.current_settings.provider;

    // populate static fields
    const s = d.current_settings || {};
    $('base_url').value = s.base_url || '';
    $('model_text').value = s.model || '';
    $('model_executor').value = s.model_executor || '';
    $('model_dreamer').value = s.model_dreamer || '';
    $('model_critic').value = s.model_critic || '';

    // table
    const tbl = el('table');
    tbl.appendChild(el('tr', null,
      el('th', null, 'name'), el('th', null, 'env'), el('th', null, 'default model'),
      el('th', null, 'status'), el('th', null, 'aliases'), el('th', null, '')));
    d.providers.forEach(p => {
      const row = el('tr', null,
        el('td', null, p.name),
        el('td', null, el('code', null, p.env || '—')),
        el('td', null, p.default_model || ''),
        el('td', {class: p.configured ? 'success' : 'failure'},
          p.configured ? 'configured' : 'not set'),
        el('td', {style: {color: 'var(--dim)'}}, (p.aliases || []).join(', ') || '—'),
        el('td', null,
          el('button', {
            style: {background: '#21262d', color: 'var(--text)', border: '1px solid #30363d',
                    padding: '4px 10px', borderRadius: '3px', cursor: 'pointer'},
            onclick: () => { sel.value = p.name; window.scrollTo(0, 0); }
          }, 'use →')));
      tbl.appendChild(row);
    });
    const wrap = $('providers-table');
    wrap.textContent = '';
    wrap.appendChild(tbl);
  }

  async function discover() {
    const provider = $('provider').value;
    if (!provider) { status.textContent = 'Pick a provider first'; return; }
    status.textContent = 'Discovering models for ' + provider + '…';
    try {
      const r = await fetch('/api/settings/models?provider=' + encodeURIComponent(provider));
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
      const sel = $('model_select');
      sel.textContent = '';
      sel.appendChild(el('option', {value: ''}, '(provider default)'));
      d.models.forEach(m => sel.appendChild(el('option', {value: m.id}, m.id)));
      status.textContent = 'Found ' + d.models.length + ' models';
    } catch (e) {
      status.textContent = 'Discovery failed: ' + (e.message || e);
    }
  }

  async function testConn() {
    const body = collect();
    status.textContent = 'Testing connection…';
    try {
      const r = await fetch('/api/settings/test', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok || !d.ok) {
        status.textContent = '✗ ' + (d.error || ('HTTP ' + r.status));
      } else {
        status.textContent = '✓ ' + (d.message || 'OK') + ' (' + d.latency_ms + 'ms)';
      }
    } catch (e) {
      status.textContent = '✗ ' + (e.message || e);
    }
  }

  function collect() {
    return {
      provider: $('provider').value,
      base_url: $('base_url').value.trim(),
      api_key: $('api_key').value,
      model: ($('model_text').value || $('model_select').value).trim(),
      model_executor: $('model_executor').value.trim(),
      model_dreamer: $('model_dreamer').value.trim(),
      model_critic: $('model_critic').value.trim(),
    };
  }

  async function save() {
    const body = collect();
    status.textContent = 'Saving…';
    try {
      const r = await fetch('/api/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || ('HTTP ' + r.status));
      $('api_key').value = '';
      status.textContent = '✓ Saved. Provider is now ' + (d.provider || '(autodetect)');
      await loadActive();
    } catch (e) {
      status.textContent = '✗ ' + (e.message || e);
    }
  }

  $('discover').addEventListener('click', discover);
  $('test').addEventListener('click', testConn);
  $('save').addEventListener('click', save);

  // ---- Permissions ----
  const PERMS = [
    {key: 'perm_filesystem', label: 'Filesystem',
     type: 'select', options: ['strict','home','full'],
     hint: 'strict=data/ only · home=user dir · full=anywhere'},
    {key: 'perm_computer_use', label: 'Computer use',
     type: 'bool', hint: 'screenshot, click, type, key (pyautogui)'},
    {key: 'perm_webcam', label: 'Webcam', type: 'bool',
     hint: 'capture frames + describe via vision'},
    {key: 'perm_shell', label: 'Shell terminal', type: 'bool',
     hint: 'arbitrary cmd.exe / /bin/sh commands'},
    {key: 'perm_web', label: 'Web fetch & search', type: 'bool',
     hint: 'web_fetch, web_search (DuckDuckGo)'},
    {key: 'perm_vision', label: 'Vision (image describe)', type: 'bool',
     hint: 'multimodal LLM image description'},
  ];

  async function loadPerms() {
    const r = await fetch('/api/permissions');
    const d = await r.json();
    const grid = $('perm-grid');
    grid.textContent = '';
    $('sandbox_enabled').checked = !!d.sandbox_enabled;
    updateSandboxStatus(d.sandbox_enabled);
    PERMS.forEach(p => {
      grid.appendChild(el('label', null, p.label));
      const row = el('div', {style: {display: 'flex', alignItems: 'center', gap: '12px'}});
      if (p.type === 'bool') {
        const wrap = el('label', {class: 'switch'});
        const cb = el('input', {type: 'checkbox', id: 'perm_' + p.key});
        cb.checked = !!d[p.key];
        wrap.appendChild(cb);
        wrap.appendChild(el('span', {class: 'slider'}));
        row.appendChild(wrap);
      } else if (p.type === 'select') {
        const sel = el('select', {id: 'perm_' + p.key,
          style: {background:'#0a0d12', color:'var(--text)',
                  border:'1px solid #30363d', borderRadius:'4px', padding:'4px 8px'}});
        p.options.forEach(o => sel.appendChild(el('option', {value: o}, o)));
        sel.value = d[p.key] || p.options[0];
        row.appendChild(sel);
      }
      row.appendChild(el('span', {style: {color:'var(--dim)', fontSize:'12px'}}, p.hint));
      grid.appendChild(row);
    });
  }

  function updateSandboxStatus(on) {
    $('sandbox-status').textContent = on
      ? 'sandbox ON — granular toggles below apply'
      : 'sandbox OFF — all capabilities unrestricted (DANGER)';
    $('sandbox-status').style.color = on ? 'var(--ok)' : 'var(--bad)';
  }

  async function savePerms() {
    const body = {sandbox_enabled: $('sandbox_enabled').checked};
    PERMS.forEach(p => {
      const w = $('perm_' + p.key);
      if (!w) return;
      body[p.key] = p.type === 'bool' ? w.checked : w.value;
    });
    $('perm-status').textContent = 'saving…';
    const r = await fetch('/api/permissions', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    const d = await r.json();
    if (r.ok) {
      $('perm-status').textContent = '✓ saved';
      updateSandboxStatus(d.sandbox_enabled);
    } else {
      $('perm-status').textContent = '✗ ' + (d.error || 'failed');
    }
  }

  $('sandbox_enabled').addEventListener('change', e => updateSandboxStatus(e.target.checked));
  $('perm-save').addEventListener('click', savePerms);
  $('perm-unleash').addEventListener('click', async () => {
    if (!confirm('Disable sandbox and grant ALL permissions to the agent?\\n\\n' +
                 'The model can read/write files anywhere, run shell commands, ' +
                 'control mouse/keyboard, capture webcam, and access the web. ' +
                 'Only do this if you trust the model.')) return;
    $('sandbox_enabled').checked = false;
    PERMS.forEach(p => { const w = $('perm_'+p.key);
      if (p.type === 'bool') w.checked = true;
      else if (p.type === 'select') w.value = p.options[p.options.length - 1]; });
    await savePerms();
  });
  $('perm-lockdown').addEventListener('click', async () => {
    $('sandbox_enabled').checked = true;
    PERMS.forEach(p => { const w = $('perm_'+p.key);
      if (p.type === 'bool') w.checked = (p.key === 'perm_web' || p.key === 'perm_vision');
      else if (p.type === 'select') w.value = 'strict'; });
    await savePerms();
  });

  // ---- Quick model presets ----
  async function loadPresets() {
    const r = await fetch('/api/presets');
    const d = await r.json();
    const wrap = $('presets');
    wrap.textContent = '';
    d.presets.forEach(p => {
      const btn = el('button', {
        style: {
          background: p.active ? 'var(--accent)' : '#21262d',
          color: p.active ? '#0e1116' : 'var(--text)',
          border: '1px solid ' + (p.active ? 'var(--accent)' : '#30363d'),
          padding: '8px 12px', borderRadius: '4px', cursor: 'pointer',
          fontSize: '13px', fontWeight: p.active ? '700' : '400',
        },
      });
      btn.appendChild(el('div', null, p.label));
      btn.appendChild(el('div', {style: {fontSize: '11px', opacity: '0.7'}},
        p.provider + (p.tier ? ' · ' + p.tier : '')));
      btn.addEventListener('click', async () => {
        $('perm-status').textContent = 'switching to ' + p.label + '…';
        const rr = await fetch('/api/presets/apply', {method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({preset_id: p.id})});
        const dd = await rr.json();
        if (rr.ok) {
          $('perm-status').textContent = '✓ active: ' + p.label;
          loadActive();
          loadPresets();
        } else {
          $('perm-status').textContent = '✗ ' + (dd.error || 'failed');
        }
      });
      wrap.appendChild(btn);
    });
  }

  // ---- Fallback chain ----
  let fallbackChain = [];
  async function loadFallback() {
    const r = await fetch('/api/fallback');
    const d = await r.json();
    fallbackChain = d.fallback_providers || [];
    renderFallbackChain();
    // Populate the "add" dropdown with all known providers minus what's already in chain
    const provR = await fetch('/api/settings/providers');
    const provD = await provR.json();
    const sel = $('fallback-add');
    sel.textContent = '';
    sel.appendChild(el('option', {value: ''}, '(pick one)'));
    provD.providers.forEach(p => {
      if (fallbackChain.includes(p.name)) return;
      const tag = p.configured ? '✓ ' : '  ';
      sel.appendChild(el('option', {value: p.name}, tag + p.name));
    });
  }
  function renderFallbackChain() {
    const wrap = $('fallback-chain');
    wrap.textContent = '';
    if (!fallbackChain.length) {
      wrap.appendChild(el('span', {style: {color: 'var(--dim)', fontSize: '13px'}},
        '(empty — no fallback configured)'));
      return;
    }
    fallbackChain.forEach((p, idx) => {
      const chip = el('span', {style: {
        background:'#21262d', color: 'var(--text)', padding:'4px 10px',
        borderRadius: '12px', fontSize: '13px', display:'inline-flex',
        alignItems: 'center', gap: '6px'
      }});
      chip.appendChild(document.createTextNode((idx + 1) + '. ' + p));
      const x = el('a', {href: '#', style: {color: 'var(--bad)', cursor: 'pointer'}}, ' ✕');
      x.addEventListener('click', e => {
        e.preventDefault();
        fallbackChain = fallbackChain.filter((_, i) => i !== idx);
        renderFallbackChain();
      });
      chip.appendChild(x);
      wrap.appendChild(chip);
    });
  }
  $('fallback-add-btn').addEventListener('click', () => {
    const v = $('fallback-add').value;
    if (!v) return;
    if (!fallbackChain.includes(v)) fallbackChain.push(v);
    renderFallbackChain();
    loadFallback();
  });
  $('fallback-save').addEventListener('click', async () => {
    $('fallback-status').textContent = 'saving…';
    const r = await fetch('/api/fallback', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({fallback_providers: fallbackChain})});
    const d = await r.json();
    $('fallback-status').textContent = r.ok ? '✓ saved' : '✗ ' + (d.error || 'failed');
  });

  loadActive();
  loadProviders();
  loadPerms();
  loadPresets();
  loadFallback();
})();
