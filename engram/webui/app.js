/* Verimem trust console v2 — living instrument.
 * All data arrives via authenticated fetch (bearer from sessionStorage);
 * this file ships static — no tenant data is ever baked in.
 * Every interpolated string goes through esc() (XSS-safe by construction). */
(function () {
  "use strict";
  var STORE = "verimem_bearer";
  var $ = function (id) { return document.getElementById(id); };
  var err = $("err"), board = $("board");
  var REDUCED = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function token() { return sessionStorage.getItem(STORE); }

  function authHeaders() {
    var t = token();
    return t ? { Authorization: "Bearer " + t } : {};
  }

  function api(path) {
    var had = !!token();
    return fetch(path, { headers: authHeaders() })
      .then(function (r) {
        if (r.status === 401) {
          sessionStorage.removeItem(STORE);
          // personal (no-key) mode not available AND no key yet: stay on
          // the neutral form, no scary error
          var e = new Error(had ? "invalid key — paste it again"
                                : "__nokey__");
          e.nokey = !had;
          throw e;
        }
        if (!r.ok) { throw new Error("gateway error " + r.status); }
        return r.json();
      });
  }

  function fail(e) {
    board.hidden = true; $("live").hidden = true;
    if (e && e.nokey) { err.hidden = true; return; }
    err.textContent = e.message; err.hidden = false;
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;",
               '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---- tabs ------------------------------------------------------------ */
  Array.prototype.forEach.call(document.querySelectorAll(".tab-btn"),
    function (btn) {
      btn.addEventListener("click", function () {
        Array.prototype.forEach.call(document.querySelectorAll(".tab-btn"),
          function (b) { b.classList.toggle("on", b === btn); });
        Array.prototype.forEach.call(document.querySelectorAll(".tab"),
          function (t) {
            t.classList.toggle("on", t.id === "tab-" + btn.dataset.tab);
          });
      });
    });

  /* ---- count-up numerals -------------------------------------------------*/
  var prevN = {};
  function countUp(id, target) {
    var el = $(id), from = prevN[id] || 0;
    prevN[id] = target;
    if (from !== target && from > 0) {      // an event landed: flash the card
      var card = el.closest ? el.closest(".card") : null;
      if (card) {
        card.classList.remove("tick");
        void card.offsetWidth;              // restart the animation
        card.classList.add("tick");
      }
    }
    if (REDUCED || from === target) { el.textContent = target; return; }
    var t0 = null, DUR = 700;
    function tick(ts) {
      if (!t0) { t0 = ts; }
      var p = Math.min(1, (ts - t0) / DUR);
      p = 1 - Math.pow(1 - p, 3);                      // easeOutCubic
      el.textContent = Math.round(from + (target - from) * p);
      if (p < 1) { requestAnimationFrame(tick); }
    }
    requestAnimationFrame(tick);
  }

  /* ---- trust ring ---------------------------------------------------------
   * three arcs stacked on one circle: admitted (green) then quarantined,
   * then rejected. C = 2πr with r=84. */
  var RING_C = 2 * Math.PI * 84;
  function setArc(cls, fromFrac, frac) {
    var el = document.querySelector(".arc-" + cls);
    el.style.strokeDasharray = (frac * RING_C) + " " + RING_C;
    el.style.strokeDashoffset = String(-fromFrac * RING_C);
  }
  function renderRing(led) {
    var a = led.admitted || 0, q = led.quarantined || 0, r = led.rejected || 0;
    var tot = a + q + r;
    if (!tot) {
      $("ring-pct").textContent = "—";
      $("ring-foot").textContent = "no gate activity yet";
      setArc("admitted", 0, 0); setArc("quarantined", 0, 0); setArc("rejected", 0, 0);
      return;
    }
    var fa = a / tot, fq = q / tot, fr = r / tot;
    setArc("admitted", 0, fa);
    setArc("quarantined", fa, fq);
    setArc("rejected", fa + fq, fr);
    $("ring-pct").textContent = Math.round(fa * 100) + "%";
    $("ring-foot").textContent = tot + " writes screened";
  }

  /* ---- sparklines (14-day real series from the ledger) --------------------*/
  var SVG = "http://www.w3.org/2000/svg";
  function el(tag, attrs) {
    var e = document.createElementNS(SVG, tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  function spark(id, series) {
    var svg = $(id);
    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    if (!series.length) { return; }
    var W = 120, H = 26, PAD = 3;
    var max = Math.max.apply(null, series.concat([1]));
    var pts = series.map(function (v, i) {
      var x = series.length === 1 ? W - PAD
        : PAD + (i / (series.length - 1)) * (W - 2 * PAD);
      var y = H - PAD - (v / max) * (H - 2 * PAD);
      return [x, y];
    });
    var flat = pts.map(function (p) { return p[0] + "," + p[1]; }).join(" ");
    svg.appendChild(el("polygon", {
      points: PAD + "," + (H - PAD) + " " + flat + " " +
              pts[pts.length - 1][0] + "," + (H - PAD) }));
    svg.appendChild(el("polyline", { points: flat }));
    var last = pts[pts.length - 1];
    svg.appendChild(el("circle", { cx: last[0], cy: last[1], r: 2.2 }));
  }

  /* ---- odometer -----------------------------------------------------------*/
  function rows(elx, obj, empty) {
    var keys = Object.keys(obj || {}).sort();
    if (!keys.length) {
      elx.innerHTML = '<div class="row muted">' + empty + "</div>"; return;
    }
    elx.innerHTML = keys.map(function (k) {
      return '<div class="row"><span>' + esc(k) + "</span><span>" +
             esc(String(obj[k])) + "</span></div>";
    }).join("");
  }

  function renderStats(d) {
    var trust = d.trust || {}, led = trust.ledger || {};
    var daily = trust.daily || [];
    var todayKey = new Date().toISOString().slice(0, 10);
    ["admitted", "quarantined", "rejected", "abstained"].forEach(function (a) {
      countUp("n-" + a, led[a] || 0);
      spark("s-" + a, daily.map(function (b) { return b[a] || 0; }));
      var today = daily.length && daily[daily.length - 1].day === todayKey
        ? daily[daily.length - 1][a] || 0 : 0;
      var dl = $("d-" + a);
      dl.textContent = today ? "+" + today + " today" : "";
      dl.classList.toggle("up", !!today);
    });
    renderRing(led);
    rows($("layers"), trust.by_layer, "no gate layer has fired yet");
    rows($("store"), trust.store, "empty store");
    var failures = trust.ledger_write_failures || 0;
    $("meta").innerHTML = "tenant: " + esc(d.tenant) +
      " &middot; refreshed " + new Date().toLocaleTimeString() +
      " &middot; auto-refresh 30s" +
      (failures ? ' &middot; <span class="warn">' + failures +
                  " ledger write failures</span>" : "");
  }

  /* ---- blocked claims ------------------------------------------------------*/
  var seenBlocked = {};
  function relTime(ts) {
    var s = (Date.now() / 1000) - ts;
    if (s < 60) { return "just now"; }
    if (s < 3600) { return Math.floor(s / 60) + "m ago"; }
    if (s < 86400) { return Math.floor(s / 3600) + "h ago"; }
    return new Date(ts * 1000).toLocaleDateString();
  }
  function renderBlocked(items) {
    var body = $("blocked-rows");
    $("blocked-empty").hidden = items.length > 0;
    body.innerHTML = items.map(function (it) {
      var fresh = !seenBlocked[it.id];
      return "<tr" + (fresh && Object.keys(seenBlocked).length
                      ? ' class="rise"' : "") + ">" +
        "<td class='when' title='" +
        esc(new Date(it.created_at * 1000).toLocaleString()) + "'>" +
        esc(relTime(it.created_at)) + "</td>" +
        "<td class='claim'>" + esc(it.proposition) + "</td>" +
        "<td class='topic'>" + esc(it.topic || "") + "</td></tr>";
    }).join("");
    items.forEach(function (it) { seenBlocked[it.id] = 1; });
  }

  /* ---- graph: the REAL one -----------------------------------------------
   * The whole store on a canvas (Barnes-Hut O(n log n)) instead of an SVG
   * sample: engram/webui/graph.js. This wrapper keeps the console's own
   * behaviour — dossier on click, search, fit/refresh, live pulses. */
  var GG = null;                                   // VerimemGraph instance
  var graphStats = $("graph-stats");

  function renderGraph(data) {
    var host = $("graph");
    $("graph-empty").hidden = (data.n || []).length > 0;
    if (!GG) {
      GG = new VerimemGraph(host, { onSelect: function (n) { selectNode(n); } });
    }
    var t0 = performance.now();
    var tot = GG.load(data);
    var ms = Math.round(performance.now() - t0);
    if (graphStats) {
      graphStats.textContent = tot.entities.toLocaleString() + " entities · "
        + tot.edges.toLocaleString() + " edges"
        + (tot.truncated ? " (capped)" : "") + " · " + ms + " ms";
    }
  }

  function centerOn(n) {
    if (!GG) { return; }
    GG.view.x = n.x; GG.view.y = n.y;
    GG.view.s = Math.max(GG.view.s, 1.2);
    GG.dirty = true; GG.loop();
  }

  /* search: live highlight; Enter selects & centers the first match */
  var searchBox = $("graph-search");
  searchBox.addEventListener("input", function () {
    if (GG) { GG.search(searchBox.value.trim()); }
  });
  searchBox.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      searchBox.value = "";
      if (GG) { GG.search(""); }
      searchBox.blur();
    }
    if (ev.key === "Enter") {
      ev.preventDefault();
      if (!GG || !GG.query) { return; }
      var hit = null;
      GG.nodes.forEach(function (n) {
        if (!hit && n.name.toLowerCase().indexOf(GG.query) >= 0) { hit = n; }
      });
      if (hit) { centerOn(hit); selectNode(hit); }
    }
  });
  $("graph-fit").addEventListener("click", function () { if (GG) { GG.fit(); } });

  /* ---- dossier + chain lighting --------------------------------------------*/
  /* On canvas the chain of custody lights by PULSING its hops in order —
     same story as the old SVG glow (hop by hop, 260 ms apart), told with the
     renderer's own live vocabulary instead of per-element CSS classes. */
  function lightChain(derivation) {
    if (!GG) { return; }
    (derivation || []).forEach(function (hop, i) {
      setTimeout(function () {
        GG.touch([hop.src_entity, hop.dst_entity]);
      }, REDUCED ? 0 : i * 260);
    });
  }

  function selectNode(n) {
    if (GG) { GG.sel = n.id; GG.dirty = true; GG.loop(); }
    $("dossier-body").innerHTML =
      '<span class="muted">deriving from &ldquo;' + esc(n.name) +
      "&rdquo;&hellip;</span>";
    api("/v1/graph/dossier?src=" + encodeURIComponent(n.id) + "&max_hops=3")
      .then(function (out) { renderDossier(n, out.dossiers || []); })
      .catch(fail);
  }

  function renderDossier(n, ds) {
    var host = $("dossier-body");
    if (!ds.length) {
      host.innerHTML = '<span class="muted">&ldquo;' + esc(n.name) +
        "&rdquo; reaches nothing within 3 hops.</span>";
      return;
    }
    host.innerHTML = "";
    ds.forEach(function (d) {
      var box = document.createElement("div");
      box.className = "d-target" + (d.abstained ? " abst" : "");
      var head = document.createElement("button");
      head.type = "button";
      head.innerHTML = "<span>" + (d.abstained ? "&#9888; " : "&#10003; ") +
        esc(d.answer || d.target_name || d.target) + "</span>" +
        (d.min_weight != null
          ? '<span class="w">trust ' + Number(d.min_weight).toFixed(2) +
            "</span>" : "");
      box.appendChild(head);
      var chain = document.createElement("div");
      chain.className = "d-chain";
      if (d.abstained) {
        chain.innerHTML = '<div class="d-reason">abstained: ' +
          esc(d.reason || "ungrounded path") + "</div>";
      } else {
        (d.derivation || []).forEach(function (hop) {
          var hv = document.createElement("div");
          hv.className = "hop";
          hv.innerHTML = esc(hop.from_entity) +
            ' <span class="rel">&mdash;' + esc(hop.predicate) +
            "&rarr;</span> " + esc(hop.to_entity) +
            '<span class="prop">&ldquo;' + esc(hop.proposition) +
            '&rdquo;</span><span class="fid">fact ' +
            esc(hop.source_fact_id) + " &middot; w " +
            Number(hop.weight).toFixed(2) + "</span>";
          chain.appendChild(hv);
        });
      }
      box.appendChild(chain);
      head.addEventListener("click", function () {
        var opening = !box.classList.contains("open");
        Array.prototype.forEach.call(host.querySelectorAll(".d-target"),
          function (x) { x.classList.remove("open"); });
        if (opening) {
          box.classList.add("open");
          if (!d.abstained) { lightChain(d.derivation); } else { clearLit(); }
        } else { clearLit(); }
      });
      host.appendChild(box);
      if (ds.length === 1 && !d.abstained) {
        box.classList.add("open"); lightChain(d.derivation);
      }
    });
  }

  /* ---- load -----------------------------------------------------------------*/
  function loadLive() {
    // no token guard: in personal mode (`verimem console`) the loopback
    // gateway answers WITHOUT a key — the page just works
    Promise.all([api("/v1/stats"), api("/v1/quarantine?limit=100")])
      .then(function (res) {
        board.hidden = false; err.hidden = true; $("live").hidden = false;
        renderStats(res[0]);
        renderBlocked(res[1].items || []);
        startEvents();
      })
      .catch(fail);
  }
  // the WHOLE graph, compact (nodes array + edges by index): 7753 nodes /
  // 78 725 edges = 1.6 MB on the real store, vs 5.7 MB verbose. The old
  // /v1/graph?max_nodes=300 window was a 0.76% fossil of the oldest edges.
  var GRAPH_URL = "/v1/graph/full";
  function loadGraph() {
    api(GRAPH_URL)
      .then(renderGraph).catch(function (e) {
        if (!(e && e.nokey)) { fail(e); }
      });
  }

  /* ---- SSE: the memory WORKING, live ------------------------------------------
   * fetch-streaming (not EventSource) so the bearer key travels in a header,
   * never in a URL. One generation at a time; reconnect with backoff. */
  var sseGen = 0, sseActive = false;
  function startEvents() {
    if (sseActive) { return; }              // one live connection at a time
    sseActive = true;
    var gen = ++sseGen;
    fetch("/v1/events", { headers: authHeaders() })
      .then(function (r) {
        if (!r.ok || !r.body) { throw new Error("events " + r.status); }
        var reader = r.body.getReader();
        var dec = new TextDecoder(), buf = "";
        function pump() {
          return reader.read().then(function (step) {
            if (gen !== sseGen) { reader.cancel(); return; }
            if (step.done) { throw new Error("stream ended"); }
            buf += dec.decode(step.value, { stream: true });
            var lines = buf.split("\n");
            buf = lines.pop();
            lines.forEach(function (line) {
              if (line.indexOf("data: ") !== 0) { return; }
              var led;
              try { led = JSON.parse(line.slice(6)).ledger; }
              catch (ex) { return; }
              var changed = ["admitted", "quarantined", "rejected",
                             "abstained"].some(function (a) {
                return (prevN["n-" + a] || 0) !== (led[a] || 0);
              });
              if (changed) { loadLive(); }   // full refresh: sparks, ring, feed
            });
            return pump();
          });
        }
        return pump();
      })
      .catch(function () {
        sseActive = false;
        if (gen === sseGen) { setTimeout(startEvents, 5000); }
      });
  }

  /* ---- the GRAPH, alive ------------------------------------------------------
   * Second stream, /v1/events/flow: the engine announces its graph's life —
   * `flow.entity` carries the nodes just BORN (created) and the ones a fact
   * just lit up (touched). A node that appears grows in place; a node that is
   * touched pulses. No polling, no full re-render: the map you are looking at
   * IS the store, right now. (Aurelio 2026-07-15: "voglio vedere
   * l'attivazione dei nodi live e quando se ne crea uno nuovo".) */
  var flowGen = 0, flowActive = false, bornTimer = null, bornIds = [];

  function onEntityEvent(p) {
    // touched nodes fire right away — no fetch, the renderer already has them
    if (GG && (p.touched || []).length) { GG.touch(p.touched); }
    if (!(p.created || []).length) { return; }
    // a node was BORN: it isn't in the canvas yet, so re-fetch the graph and
    // pulse the newcomers. Debounced: a burst of writes must not storm the
    // endpoint (the full graph is 1.6 MB).
    bornIds = bornIds.concat(p.created.map(function (c) { return c.id; }));
    if (bornTimer) { clearTimeout(bornTimer); }
    bornTimer = setTimeout(function () {
      var justBorn = bornIds; bornIds = []; bornTimer = null;
      api(GRAPH_URL).then(function (d) {
        renderGraph(d);
        if (GG) { GG.touch(justBorn); }
      }).catch(function () { /* the map keeps what it has */ });
    }, 900);
  }
  function startFlow() {
    if (flowActive) { return; }
    flowActive = true;
    var gen = ++flowGen;
    fetch("/v1/events/flow?replay=0", { headers: authHeaders() })
      .then(function (r) {
        if (!r.ok || !r.body) { throw new Error("flow " + r.status); }
        var reader = r.body.getReader(), dec = new TextDecoder(), buf = "";
        function pump() {
          return reader.read().then(function (step) {
            if (gen !== flowGen) { reader.cancel(); return; }
            if (step.done) { throw new Error("flow ended"); }
            buf += dec.decode(step.value, { stream: true });
            var lines = buf.split("\n");
            buf = lines.pop();
            lines.forEach(function (line) {
              if (line.indexOf("data: ") !== 0) { return; }
              var evt;
              try { evt = JSON.parse(line.slice(6)); } catch (ex) { return; }
              if (evt.name === "flow.entity") { onEntityEvent(evt.payload || {}); }
            });
            return pump();
          });
        }
        return pump();
      })
      .catch(function () {
        flowActive = false;
        if (gen === flowGen) { setTimeout(startFlow, 5000); }
      });
  }

  $("keyform").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var v = $("key").value.trim();
    if (v) {
      sessionStorage.setItem(STORE, v); $("key").value = "";
      sseGen++; sseActive = false;         // re-auth the live streams
      flowGen++; flowActive = false;
      loadLive(); loadGraph(); startFlow();
    }
  });
  $("graph-refresh").addEventListener("click", loadGraph);

  setInterval(loadLive, 30000);
  loadLive(); loadGraph(); startFlow();
})();
