/* Verimem trust console v2 — living instrument.
 * All data arrives via authenticated fetch (bearer from sessionStorage);
 * this file ships static — no tenant data is ever baked in.
 * Every interpolated string goes through esc() (XSS-safe by construction).
 *
 * LIVE DISCIPLINE (2026-07-16, learned the hard way): this page sits on a
 * store that other agents write CONTINUOUSLY. One fetch per event is a
 * self-inflicted DDoS (ERR_INSUFFICIENT_RESOURCES took the whole console
 * down). Rules: counters update from the event payload itself; full
 * refreshes are throttled; the graph grows INCREMENTALLY from flow.entity
 * (never a 1.6 MB refetch per node birth); a failed fetch degrades to a
 * banner + retry, never to a dead page. */
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

  /* a fetch that fails must NOT kill the console: if the board is already
     live, keep showing it (stale data beats a blank page), banner + retry. */
  var failTimer = null;
  function fail(e) {
    if (e && e.nokey) {
      board.hidden = true; $("live").hidden = true; err.hidden = true;
      return;
    }
    $("live").hidden = true;
    err.textContent = e.message + " — retrying…";
    err.hidden = false;
    if (!failTimer) {
      failTimer = setTimeout(function () { failTimer = null; loadLive(); },
                             6000);
    }
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
        if (btn.dataset.tab === "graph" && GG) {
          requestAnimationFrame(function () { GG.r.resize(); });
        }
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
      " &middot; live stream + 30s failsafe" +
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

  /* ---- graph: the REAL one, on sigma.js (WebGL) -----------------------------
   * graph.js wraps sigma + graphology + FA2-in-a-worker (vendored). This
   * section owns console behaviour: dossier on click, search, fit/layout/
   * refresh, live pulses, INCREMENTAL births. */
  var GG = null;                                   // VerimemGraph instance
  var graphStats = $("graph-stats");
  var graphTotals = { nodes: 0, edges: 0 };
  var liveBorn = 0;
  var lastLoadMs = 0;

  /* honest FPS: measured on the page, shown in the stats bar — "smooth"
     is a number here, not an adjective (Aurelio 2026-07-16). */
  var fpsNow = 0;
  (function fpsMeter() {
    var frames = 0, t0 = performance.now();
    function loop(ts) {
      frames++;
      if (ts - t0 >= 1000) {
        fpsNow = Math.round(frames * 1000 / (ts - t0));
        frames = 0; t0 = ts;
        statsLine();
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  })();

  function statsLine(suffix) {
    if (!graphStats) { return; }
    var c = GG ? GG.counts() : graphTotals;
    var shown = GG ? GG.shownEdges() : 0;
    graphStats.textContent = c.nodes.toLocaleString() + " entities · "
      + (shown < c.edges
         ? shown.toLocaleString() + "/" + c.edges.toLocaleString() + " edges"
         : c.edges.toLocaleString() + " edges")
      + (liveBorn ? " · +" + liveBorn + " born live" : "")
      + (lastLoadMs ? " · " + lastLoadMs + " ms" : "")
      + (fpsNow ? " · " + fpsNow + " fps" : "")
      + (suffix ? " · " + suffix : "");
  }

  function renderClusters() {
    var host = $("graph-clusters");
    if (!host || !GG) { return; }
    var cs = GG.clusters();
    host.innerHTML = "";
    var active = null;
    cs.forEach(function (cl) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "cluster-chip";
      var dot = document.createElement("i");
      dot.style.background = cl.color;
      b.appendChild(dot);
      b.appendChild(document.createTextNode(
        (cl.label.length > 18 ? cl.label.slice(0, 17) + "…" : cl.label)
        + " " + cl.size));
      b.title = "community around “" + cl.label + "” — " + cl.size
        + " entities. Click to isolate, click again to release.";
      b.addEventListener("click", function () {
        var on = active === cl.id ? null : cl.id;
        active = on;
        GG.setClusterFilter(on);
        Array.prototype.forEach.call(host.children, function (x) {
          x.classList.toggle("on", on !== null && x === b);
        });
      });
      host.appendChild(b);
    });
  }

  function renderGraph(data) {
    var host = $("graph");
    $("graph-empty").hidden = (data.n || []).length > 0;
    if (!GG) {
      GG = new window.VerimemGraph(host, {
        onSelect: function (n) { selectNode(n); },
        onLayout: function (running) {
          var b = $("graph-layout");
          if (b) { b.textContent = running ? "stop layout" : "re-layout"; }
          statsLine(running ? "layout running" : "");
        },
        onLocal: function (name, size) {
          var bar = $("graph-local");
          if (!bar) { return; }
          if (name) {
            $("graph-local-label").textContent =
              "local · " + name + " · 2 hops · " + size + " nodes";
            bar.hidden = false;
          } else { bar.hidden = true; }
        }
      });
      $("graph-local-exit").addEventListener("click", function () {
        GG.localExit();
      });
      var slider = $("graph-density");
      slider.addEventListener("input", function () {
        GG.setBackbone(+slider.value);
        statsLine();
      });
    }
    var t0 = performance.now();
    graphTotals = GG.load(data);
    lastLoadMs = Math.round(performance.now() - t0);
    renderClusters();
    statsLine("layout running");
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
      if (!GG) { return; }
      var hit = GG.search(searchBox.value.trim());
      if (hit) {
        GG.focus(hit);
        selectNode({ id: hit, name: GG.name(hit) });
      }
    }
  });
  $("graph-fit").addEventListener("click", function () { if (GG) { GG.fit(); } });
  $("graph-layout").addEventListener("click", function () {
    if (!GG) { return; }
    if (GG.layoutRunning()) { GG.stopLayout(); } else { GG.layout(9000); }
  });

  /* ---- dossier + chain lighting --------------------------------------------*/
  function lightChain(derivation) {
    if (!GG) { return; }
    (derivation || []).forEach(function (hop, i) {
      setTimeout(function () {
        GG.touch([hop.src_entity, hop.dst_entity]);
      }, REDUCED ? 0 : i * 260);
    });
  }

  function selectNode(n) {
    if (GG) { GG.setSelected(n.id); }
    $("dossier-body").innerHTML =
      '<span class="muted">deriving from &ldquo;' + esc(n.name) +
      "&rdquo;&hellip;</span>";
    api("/v1/graph/dossier?src=" + encodeURIComponent(n.id) + "&max_hops=3")
      .then(function (out) { renderDossier(n, out.dossiers || []); })
      .catch(function (e) {
        if (!(e && e.nokey)) {
          $("dossier-body").innerHTML =
            '<span class="muted">dossier unavailable: ' + esc(e.message) +
            "</span>";
        }
      });
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
          if (!d.abstained) { lightChain(d.derivation); }
        }
      });
      host.appendChild(box);
      if (ds.length === 1 && !d.abstained) {
        box.classList.add("open"); lightChain(d.derivation);
      }
    });
  }

  /* ---- memory search (provenance-first) --------------------------------------
   * /v1/search hits carry per-fact provenance (asserted_at, created_at,
   * source episode, verified_by — case-B wire 2026-07-16): show it. Trust
   * you can SEE per fact, not just per aggregate. */
  function provBadges(it) {
    var b = [];
    b.push('<span class="badge st-' + esc(it.status || "model_claim") + '">'
      + esc(it.status || "model_claim") + "</span>");
    if (it.verified_by && it.verified_by.length) {
      b.push('<span class="badge vby" title="' +
        esc(it.verified_by.join(", ")) + '">verified ×' +
        it.verified_by.length + "</span>");
    }
    if (it.grounding_score != null) {
      b.push('<span class="badge gs">grounding ' +
        esc(String(it.grounding_score)) + "</span>");
    }
    if (it.asserted_at) {
      b.push('<span class="badge t" title="event time">asserted ' +
        esc(relTime(it.asserted_at)) + "</span>");
    }
    if (it.created_at) {
      b.push('<span class="badge t" title="transaction time">written ' +
        esc(relTime(it.created_at)) + "</span>");
    }
    if (it.source) {
      b.push('<span class="badge src" title="' + esc(it.source) +
        '">ep ' + esc(String(it.source).slice(0, 8)) + "</span>");
    }
    return b.join("");
  }

  function renderMem(hits) {
    var host = $("mem-results");
    if (!hits.length) {
      host.innerHTML = '<div class="empty">no fact matches — the memory ' +
        "does not pretend otherwise.</div>";
      return;
    }
    host.innerHTML = hits.map(function (it) {
      var sc = Number(it.score || 0);
      return '<div class="mem-hit">' +
        '<div class="mh-score" title="similarity">' +
        (sc > 0 ? sc.toFixed(2) : "—") + "</div>" +
        '<div class="mh-main"><div class="mh-text">' + esc(it.text) + "</div>" +
        '<div class="mh-meta">' + provBadges(it) +
        (it.topic ? '<span class="badge tp">' + esc(it.topic) + "</span>" : "") +
        "</div></div></div>";
    }).join("");
  }

  $("mem-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = $("mem-q").value.trim();
    if (!q) { return; }
    $("mem-results").innerHTML = '<div class="muted pad">searching…</div>';
    api("/v1/search?q=" + encodeURIComponent(q) + "&k=12")
      .then(function (res) { renderMem(res.hits || []); })
      .catch(function (e) {
        $("mem-results").innerHTML =
          '<div class="empty">' + esc(e.nokey
            ? "connect first (API key above)" : e.message) + "</div>";
      });
  });

  /* ---- ask: grounding-verified answering --------------------------------------
   * GET /v1/answer (2026-07-16). Needs a server-side llm: the personal
   * console does NOT have one and answers 400 — show that honestly instead
   * of a dead spinner. */
  $("ask-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = $("ask-q").value.trim();
    if (!q) { return; }
    var host = $("ask-out");
    host.innerHTML = '<div class="muted pad">asking — retrieval + grounding check…</div>';
    fetch("/v1/answer?q=" + encodeURIComponent(q) + "&k=8",
          { headers: authHeaders() })
      .then(function (r) {
        if (r.status === 400) {
          return r.json().then(function (j) {
            var e = new Error(j.detail ||
              "answering unavailable on this gateway");
            e.noLlm = true; throw e;
          });
        }
        if (r.status === 401) { throw new Error("invalid or missing key"); }
        if (!r.ok) { throw new Error("gateway error " + r.status); }
        return r.json();
      })
      .then(function (out) {
        var abst = out.answer === "NO ANSWER";
        host.innerHTML =
          '<div class="ask-verdict ' + (abst ? "abst" : "ok") + '">' +
          (abst ? "NO ANSWER — honest abstention" : esc(out.answer)) +
          "</div>" +
          '<div class="mh-meta">' +
          '<span class="badge ' + (out.grounded ? "vby" : "st-quarantined") +
          '">' + (out.grounded ? "grounded" : "not grounded") + "</span>" +
          (out.support_score != null
            ? '<span class="badge gs">support ' + esc(String(out.support_score))
              + "</span>" : "") +
          '<span class="badge t">' + esc(out.reason || "") + "</span></div>" +
          (out.support_fact
            ? '<div class="ask-support">&ldquo;' + esc(out.support_fact) +
              "&rdquo;</div>" : "") +
          (abst && out.raw_answer
            ? '<div class="ask-support raw">model said: &ldquo;' +
              esc(out.raw_answer) + "&rdquo; — refused: no retrieved fact " +
              "supports it.</div>" : "");
      })
      .catch(function (e) {
        host.innerHTML = '<div class="empty">' + esc(e.message) +
          (e.noLlm ? " — the personal console runs WITHOUT an LLM by design; " +
            "search &amp; explain above work fully." : "") + "</div>";
      });
  });

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
        startFlow();
      })
      .catch(fail);
  }

  /* full refresh throttle: the ledger stream may fire MANY times a second
     under real traffic; counters update inline, the heavy refresh (sparks,
     deltas, blocked table) coalesces to once per 5s. */
  var liveTimer = null;
  function loadLiveSoon() {
    if (liveTimer) { return; }
    liveTimer = setTimeout(function () { liveTimer = null; loadLive(); }, 5000);
  }

  // the WHOLE graph, compact (nodes array + edges by index): 7.7k nodes /
  // 78k edges ≈ 1.6 MB on the real store. Fetched ONCE at boot, then it
  // grows incrementally from flow.entity events; refetch only on manual
  // refresh or stream resync.
  var GRAPH_URL = "/v1/graph/full";
  var graphRetry = null;
  function loadGraph() {
    api(GRAPH_URL)
      .then(function (d) { liveBorn = 0; renderGraph(d); })
      .catch(function (e) {
        if (e && e.nokey) { return; }
        statsLine("graph fetch failed — retrying");
        if (!graphRetry) {
          graphRetry = setTimeout(function () {
            graphRetry = null; loadGraph();
          }, 8000);
        }
      });
  }
  var lastResync = 0;
  function graphResync() {          // stream dropped: events were missed
    var now = Date.now();
    if (now - lastResync < 30000) { return; }
    lastResync = now;
    loadGraph();
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
              if (!led) { return; }
              var changed = ["admitted", "quarantined", "rejected",
                             "abstained"].some(function (a) {
                return (prevN["n-" + a] || 0) !== (led[a] || 0);
              });
              if (changed) {
                // counters + ring move NOW, from the event itself (no fetch);
                // sparks/deltas/blocked follow, throttled.
                ["admitted", "quarantined", "rejected", "abstained"]
                  .forEach(function (a) { countUp("n-" + a, led[a] || 0); });
                renderRing(led);
                loadLiveSoon();
              }
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

  /* ---- the GRAPH, alive -------------------------------------------------------
   * Second stream, /v1/events/flow: `flow.entity` carries the nodes just
   * BORN (created: id+name+type) and the ones a fact just lit up (touched =
   * the fact's co-occurrence clique). Births are added INCREMENTALLY — the
   * event already has everything; no refetch, no re-layout of the world. */
  var flowGen = 0, flowActive = false, flowWasLost = false;

  function onEntityEvent(p) {
    if (!GG) { return; }
    var created = p.created || [], touched = p.touched || [];
    if (created.length) {
      liveBorn += GG.addLive(created, touched);
      GG.touch(created.map(function (c) { return c.id; }), { born: true });
      statsLine();
    }
    if (touched.length) { GG.touch(touched); }
  }

  function startFlow() {
    if (flowActive) { return; }
    flowActive = true;
    var gen = ++flowGen;
    fetch("/v1/events/flow?replay=0", { headers: authHeaders() })
      .then(function (r) {
        if (!r.ok || !r.body) { throw new Error("flow " + r.status); }
        if (flowWasLost) { flowWasLost = false; graphResync(); }
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
        flowActive = false; flowWasLost = true;
        if (gen === flowGen) { setTimeout(startFlow, 5000); }
      });
  }

  /* ---- boot ----------------------------------------------------------------*/
  $("keyform").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var v = $("key").value.trim();
    if (v) {
      sessionStorage.setItem(STORE, v); $("key").value = "";
      sseGen++; sseActive = false;         // re-auth the live streams
      flowGen++; flowActive = false;
      loadLive(); loadGraph();
    }
  });
  $("graph-refresh").addEventListener("click", loadGraph);

  setInterval(loadLive, 30000);            // failsafe if both streams die
  loadLive(); loadGraph();
})();
