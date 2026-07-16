/* VERIMEM — LIVE ENGINE ROOM (/ui/engine).
   External script by CSP design (script-src 'self': no inline JS, no eval).
   Streams /v1/events/flow (authed fetch-streaming; bearer in a header +
   sessionStorage, never in a URL) and animates the custody line with the
   REAL events of this tenant. Payloads are flow metadata only.

   v2 (2026-07-16): NO event queue. v1 played one event per 900 ms — under
   real traffic (tens of events/s) the pipeline ran MINUTES behind its own
   feed. Now every event lands the moment it arrives: counters move NOW,
   stages glow with a decaying HEAT (bursts stack, nothing waits), the feed
   flushes per animation frame, and a per-second rate chart shows the load.
   shadow.* events (phase-1 observation logs, not decisions) are counted in
   a discreet chip, never drawn as engine activity. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var counters = { adm: 0, quar: 0, ans: 0, abs: 0 };
  var shadowN = 0;
  var aborter = null;
  var gen = 0;                 // connection generation: a new connect
                               // invalidates the old stream's retry loop

  var KEY_SS = "verimem_api_key";
  $("key").value = sessionStorage.getItem(KEY_SS) || "";

  function setLive(on, tx) {
    $("live").classList.toggle("on", on);
    $("liveTx").textContent = tx;
  }

  /* ---- HEAT: stages glow while events flow, decay when they stop ---------*/
  var hot = {};                 // element id -> {until, cls}
  var sweepTimer = null;
  function heat(id, cls, ms) {
    var el = $(id);
    if (!el) { return; }
    cls.forEach(function (c) { el.classList.add(c); });
    hot[id] = { until: performance.now() + (ms || 900), cls: cls };
    if (!sweepTimer) { sweepTimer = setInterval(sweep, 150); }
  }
  function sweep() {
    var now = performance.now(), left = 0;
    Object.keys(hot).forEach(function (id) {
      if (hot[id].until <= now) {
        var el = $(id);
        if (el) {
          hot[id].cls.forEach(function (c) { el.classList.remove(c); });
        }
        delete hot[id];
      } else { left++; }
    });
    if (!left) { clearInterval(sweepTimer); sweepTimer = null; }
  }
  function stamp(id, text, cls) {
    var el = $(id);
    el.textContent = text;
    ["adm", "ref", "ans", "abs"].forEach(function (c) { el.classList.remove(c); });
    heat(id, ["on", cls], 2200);
  }

  /* ---- rate: events/min + a real-time per-second chart --------------------*/
  var tsW = [], tsR = [];
  var chart = $("ratechart");
  var chartCtx = chart ? chart.getContext("2d") : null;
  function drawRate() {
    var now = Date.now();
    while (tsW.length && now - tsW[0] > 60000) { tsW.shift(); }
    while (tsR.length && now - tsR[0] > 60000) { tsR.shift(); }
    $("rate").textContent = (tsW.length || tsR.length)
      ? tsW.length + " writes/min · " + tsR.length + " recalls/min"
      : "quiet";
    if (!chartCtx) { return; }
    var W = chart.width, H = chart.height, bins = 60, bw = W / bins;
    var bw2 = Math.max(1, bw - 1);
    var w = new Array(bins).fill(0), r = new Array(bins).fill(0);
    tsW.forEach(function (t) {
      var b = bins - 1 - Math.floor((now - t) / 1000);
      if (b >= 0) { w[b]++; }
    });
    tsR.forEach(function (t) {
      var b = bins - 1 - Math.floor((now - t) / 1000);
      if (b >= 0) { r[b]++; }
    });
    var max = 1;
    for (var i = 0; i < bins; i++) { max = Math.max(max, w[i] + r[i]); }
    var cs = getComputedStyle(document.documentElement);
    var cw = (cs.getPropertyValue("--verified") || "#2E6B4F").trim();
    var cr = (cs.getPropertyValue("--ink-2") || "#423B30").trim();
    chartCtx.clearRect(0, 0, W, H);
    for (i = 0; i < bins; i++) {
      var hw = (w[i] / max) * (H - 2), hr = (r[i] / max) * (H - 2);
      if (hw) {
        chartCtx.fillStyle = cw;
        chartCtx.fillRect(i * bw, H - hw, bw2, hw);
      }
      if (hr) {
        chartCtx.fillStyle = cr;
        chartCtx.fillRect(i * bw, H - hw - hr, bw2, hr);
      }
    }
  }
  setInterval(drawRate, 1000);

  /* ---- one event, NOW ------------------------------------------------------*/
  function onWrite(p) {
    tsW.push(Date.now());
    // quarantined IS written to the ledger but excluded from recall → red branch
    var ok = p.stored && p.status !== "quarantined";
    heat("n-ingest", ["pass"], 900);
    heat("w-in-l1", ["flow"], 900);
    if (ok) {
      counters.adm++;
      heat("n-l1", ["pass"], 900); heat("w-l1-l4", ["flow"], 900);
      heat("n-l4", ["pass"], 900); heat("w-l4-led", ["flow"], 900);
      stamp("st-led", "ADMITTED", "adm");
    } else {
      counters.quar++;
      heat("n-l1", ["fail"], 900);
      heat("w-l1-q", ["flow", "q"], 900);
      stamp("st-q", String(p.status || "REFUSED").toUpperCase(), "ref");
    }
  }
  function onRecall(p) {
    tsR.push(Date.now());
    var abst = !!p.abstained;
    heat("n-query", ["pass"], 900); heat("w-q-rec", ["flow"], 900);
    heat("n-rec", ["pass"], 900); heat("w-rec-fl", ["flow"], 900);
    if (abst) {
      counters.abs++;
      heat("n-fl", ["fail"], 900); heat("w-fl-v", ["flow", "q"], 900);
      heat("n-v", ["fail"], 900);
      $("vSub").textContent = "honest silence";
      stamp("st-v", "NO ANSWER", "abs");
    } else {
      counters.ans++;
      heat("n-fl", ["pass"], 900); heat("w-fl-v", ["flow"], 900);
      heat("n-v", ["pass"], 900);
      $("vSub").textContent = p.kind === "answer"
        ? (p.grounded ? "grounded answer" : "answer") : "answer + provenance";
      stamp("st-v", p.kind === "answer" && p.grounded ? "ANSWER ✓" : "ANSWER",
            "ans");
    }
  }
  function countersRender() {
    $("cAdm").textContent = counters.adm; $("cQuar").textContent = counters.quar;
    $("cAns").textContent = counters.ans; $("cAbs").textContent = counters.abs;
  }

  /* ---- feed: batched per animation frame ------------------------------------*/
  var pendingRows = [];
  function feedRow(evt) {
    var p = evt.payload || {};
    var d = new Date((evt.ts || 0) * 1000);
    var hh = ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2)
      + ":" + ("0" + d.getSeconds()).slice(-2);
    var row = document.createElement("div"); row.className = "evt";
    // build with createElement + textContent only — no innerHTML on event data
    var t = document.createElement("span"); t.className = "t"; t.textContent = hh;
    var tag = document.createElement("span");
    var detail;
    if (evt.name === "flow.write") {
      var ok = p.stored && p.status !== "quarantined";
      tag.className = ok ? "adm" : "ref";
      tag.textContent = ok ? "ADMITTED" : String(p.status || "refused").toUpperCase();
      detail = " · write · topic " + (p.topic || "—")
        + (p.fact_id ? " · id " + String(p.fact_id).slice(0, 8) : "");
    } else {
      var abst = !!p.abstained;
      tag.className = abst ? "abs" : "ans";
      var kind = p.kind || "recall";
      if (kind === "answer") {
        tag.textContent = abst ? "NO ANSWER" : "ANSWER";
        detail = " · answer" + (p.grounded != null
          ? (p.grounded ? " · grounded" : " · not grounded") : "")
          + (p.reason ? " · " + p.reason : "");
      } else {
        tag.textContent = abst ? "ABSTAIN" : "ANSWER";
        detail = " · " + kind
          + (p.n != null ? " · n=" + p.n : "")
          + (p.best != null ? " · best " + p.best : "");
      }
    }
    if (p.surface) {
      detail += " · via " + p.surface + (p.actor ? "/" + p.actor : "");
    }
    row.appendChild(t); row.appendChild(document.createTextNode(" "));
    row.appendChild(tag); row.appendChild(document.createTextNode(detail));
    return row;
  }
  function feedPush(evt) {
    pendingRows.push(evt);
    if (pendingRows.length === 1) { requestAnimationFrame(feedFlush); }
  }
  function feedFlush() {
    var f = $("feed");
    var batch = pendingRows; pendingRows = [];
    var frag = document.createDocumentFragment();
    // newest first: append in reverse so the youngest ends up on top
    for (var i = batch.length - 1; i >= 0; i--) {
      frag.appendChild(feedRow(batch[i]));
    }
    f.insertBefore(frag, f.firstChild);
    while (f.children.length > 50) { f.removeChild(f.lastChild); }
  }

  function handle(evt) {
    var name = evt.name || "";
    if (name.indexOf("shadow.") === 0) {
      // phase-1 observation logs — real, counted, but NOT engine decisions
      shadowN++;
      $("shadow").textContent = "shadow ×" + shadowN;
      return;
    }
    if (name === "flow.write") { onWrite(evt.payload || {}); }
    else if (name === "flow.recall") { onRecall(evt.payload || {}); }
    else { return; }           // flow.entity lives on the console's graph
    countersRender();
    feedPush(evt);
  }

  /* ---- the stream -----------------------------------------------------------*/
  async function connect() {
    var key = $("key").value.trim();
    var myGen = ++gen;
    $("err").textContent = "";
    // personal mode (`verimem console`, loopback): no key needed — an empty
    // field connects as the local tenant; a 401 explains when one IS needed.
    if (key) { sessionStorage.setItem(KEY_SS, key); }
    if (aborter) { aborter.abort(); }
    aborter = new AbortController();
    setLive(false, "connecting…");
    try {
      var hdrs = key ? { Authorization: "Bearer " + key } : {};
      var r = await fetch("/v1/events/flow?replay=20",
        { headers: hdrs, signal: aborter.signal });
      if (r.status === 401) {
        setLive(false, "disconnected");
        $("key").hidden = false; $("go").hidden = false;
        $("err").textContent = key ? "401 — invalid key"
          : "401 — this gateway needs an API key (personal mode not active)";
        return;
      }
      if (!r.ok || !r.body) { throw new Error("HTTP " + r.status); }
      setLive(true, "LIVE");
      if (!key) {               // personal mode: the form is noise — drop it
        $("key").hidden = true; $("go").hidden = true;
        $("streamHint").textContent =
          "personal store · loopback · no key needed";
      }
      var reader = r.body.getReader(), dec = new TextDecoder(), buf = "";
      for (;;) {
        var ch = await reader.read();
        if (ch.done) { break; }
        buf += dec.decode(ch.value, { stream: true });
        var idx;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          var chunk = buf.slice(0, idx); buf = buf.slice(idx + 2);
          if (chunk.indexOf("data: ") === 0) {
            try { handle(JSON.parse(chunk.slice(6))); }
            catch (e) { /* skip bad line */ }
          }
        }
      }
      throw new Error("stream closed");
    } catch (e) {
      if (e.name === "AbortError") { return; }
      // LIVE means live: a dropped stream (server restart, laptop sleep)
      // reconnects itself with backoff — a page that stays "disconnected"
      // until a human clicks is a screenshot, not a live map.
      if (myGen === gen) {
        setLive(false, "reconnecting…");
        setTimeout(function () { if (myGen === gen) { connect(); } }, 4000);
      }
    }
  }
  $("go").addEventListener("click", connect);
  $("key").addEventListener("keydown", function (e) { if (e.key === "Enter") { connect(); } });
  // AUTO-CONNECT on load, like the trust console: in personal mode the page
  // must just work with zero clicks; with a stored key it resumes it; only
  // a true 401 leaves the form waiting for the human.
  connect();
})();
