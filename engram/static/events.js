(function () {
  "use strict";
  const tbody = document.getElementById('evt-tbody');
  const status = document.getElementById('evt-status');
  const filterInput = document.getElementById('evt-filter');
  const clearBtn = document.getElementById('evt-clear');
  const pauseBtn = document.getElementById('evt-pause');
  let paused = false;
  let filterText = '';

  function pad2(n) { return String(n).padStart(2, '0'); }
  function fmtTime(ts) {
    const d = new Date(ts * 1000);
    return pad2(d.getHours())+':'+pad2(d.getMinutes())+':'+pad2(d.getSeconds());
  }

  function matchesFilter(name, payloadStr) {
    if (!filterText) return true;
    const f = filterText.toLowerCase();
    return name.toLowerCase().includes(f) || payloadStr.toLowerCase().includes(f);
  }

  function addEvent(evt) {
    if (paused) return;
    const payloadStr = JSON.stringify(evt.payload);
    if (!matchesFilter(evt.name, payloadStr)) return;
    const tr = document.createElement('tr');
    const tdTime = document.createElement('td');
    tdTime.textContent = fmtTime(evt.ts);
    tdTime.style.color = 'var(--dim)';
    tdTime.style.whiteSpace = 'nowrap';
    const tdName = document.createElement('td');
    const b = document.createElement('b'); b.textContent = evt.name;
    tdName.appendChild(b);
    const tdP = document.createElement('td');
    const c = document.createElement('code');
    c.textContent = payloadStr.slice(0, 300);
    c.style.fontSize = '12px';
    tdP.appendChild(c);
    tr.appendChild(tdTime); tr.appendChild(tdName); tr.appendChild(tdP);
    tbody.insertBefore(tr, tbody.firstChild);
    while (tbody.children.length > 500) tbody.removeChild(tbody.lastChild);
  }

  function connect() {
    fetch('/api/events/recent').then(r => r.json()).then(d => {
      d.events.slice().reverse().forEach(addEvent);
    });
    const es = new EventSource('/api/events/stream');
    es.onmessage = e => {
      try { addEvent(JSON.parse(e.data)); } catch (_) {/*skip*/}
    };
    es.onerror = () => {
      status.textContent = '● disconnected';
      status.style.color = 'var(--bad)';
      status.style.borderColor = 'var(--bad)';
      setTimeout(() => { es.close(); connect(); }, 3000);
    };
    es.onopen = () => {
      status.textContent = '● live';
      status.style.color = 'var(--ok)';
      status.style.borderColor = 'var(--ok)';
    };
  }

  filterInput.addEventListener('input', () => { filterText = filterInput.value; });
  clearBtn.addEventListener('click', () => { tbody.textContent = ''; });
  pauseBtn.addEventListener('click', () => {
    paused = !paused;
    pauseBtn.textContent = paused ? 'Resume' : 'Pause';
    pauseBtn.style.background = paused ? 'var(--warn)' : '#21262d';
    pauseBtn.style.color = paused ? '#0e1116' : 'var(--text)';
  });

  connect();
})();
