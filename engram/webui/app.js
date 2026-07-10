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

  /* ---- graph engine v3: Obsidian-feel ------------------------------------
   * inertial physics (velocity + damping + soft collision, no hard walls),
   * persistent focus, search with highlight, label LOD, fit-to-view. */
  var svg = $("graph");
  var G = { nodes: [], edges: [], byId: {}, edgeEls: [], nodeEls: {},
            alpha: 0, vb: null, running: false, drag: null, litKeys: {},
            focus: null, query: "", degree: {} };

  function edgeKey(e) { return e.src + "|" + e.dst + "|" + e.predicate; }

  function simStep() {
    var nodes = G.nodes, K = G.K, i, j;
    for (i = 0; i < nodes.length; i++) { nodes[i].ax = 0; nodes[i].ay = 0; }
    for (i = 0; i < nodes.length; i++) {
      var a = nodes[i];
      for (j = i + 1; j < nodes.length; j++) {
        var b = nodes[j];
        var dx = a.x - b.x, dy = a.y - b.y;
        var d2 = dx * dx + dy * dy || 0.01, d = Math.sqrt(d2);
        var rep = (K * K) / d2 * 9;            // repulsion falls with d²
        var pad = (a.r || 8) + (b.r || 8) + 8; // soft collision shell
        if (d < pad) { rep += (pad - d) * 1.4; }
        var ux = dx / d, uy = dy / d;
        a.ax += ux * rep; a.ay += uy * rep;
        b.ax -= ux * rep; b.ay -= uy * rep;
      }
      a.ax += (G.w / 2 - a.x) * 0.012;         // gentle center gravity
      a.ay += (G.h / 2 - a.y) * 0.012;
    }
    G.edges.forEach(function (e) {
      var s = G.byId[e.src], t = G.byId[e.dst];
      if (!s || !t) { return; }
      var dx = t.x - s.x, dy = t.y - s.y;
      var d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      var f = (d - K) * 0.045;                 // spring toward rest length K
      var ux = dx / d, uy = dy / d;
      s.ax += ux * f; s.ay += uy * f; t.ax -= ux * f; t.ay -= uy * f;
    });
    nodes.forEach(function (n) {
      if (n.pinned) { n.vx = 0; n.vy = 0; return; }
      // inertia: forces accumulate into velocity, damping bleeds it off —
      // the graph breathes and settles instead of snapping (no hard walls;
      // gravity keeps it together, `fit` brings it back into view)
      n.vx = (n.vx + n.ax * 0.06 * G.alpha) * 0.86;
      n.vy = (n.vy + n.ay * 0.06 * G.alpha) * 0.86;
      n.x += n.vx; n.y += n.vy;
    });
  }

  function draw() {
    G.edgeEls.forEach(function (r) {
      var s = G.byId[r.e.src], t = G.byId[r.e.dst];
      if (!s || !t) { return; }
      r.line.setAttribute("x1", s.x); r.line.setAttribute("y1", s.y);
      r.line.setAttribute("x2", t.x); r.line.setAttribute("y2", t.y);
      if (r.flow) {
        r.flow.setAttribute("x1", s.x); r.flow.setAttribute("y1", s.y);
        r.flow.setAttribute("x2", t.x); r.flow.setAttribute("y2", t.y);
      }
      r.label.setAttribute("x", (s.x + t.x) / 2);
      r.label.setAttribute("y", (s.y + t.y) / 2 - 4);
    });
    G.nodes.forEach(function (n) {
      var g = G.nodeEls[n.id];
      if (g) { g.setAttribute("transform", "translate(" + n.x + "," + n.y + ")"); }
    });
  }

  function loop() {
    if (!G.running) { return; }
    if (G.alpha > 0.006 && !document.hidden) {
      simStep(); draw();
      G.alpha *= 0.985;                        // slow cool = visible breathe
      requestAnimationFrame(loop);
    } else { G.running = false; draw(); }
  }
  function reheat(a) {
    G.alpha = Math.max(G.alpha, a);
    if (!G.running) { G.running = true; requestAnimationFrame(loop); }
  }

  function zoomScale() { return G.vb ? (G.w / G.vb.w) : 1; }

  /* ONE emphasis pass — priority: search query > sticky focus > hover.
   * Lit (chain-of-custody) elements are never faded. Label LOD lives here:
   * a label shows when its node is emphasized, is a hub, or the view is
   * zoomed in / small enough to afford it. */
  function updateEmphasis(hoverId) {
    var mode = G.query ? "query" : (G.focus ? "focus"
               : (hoverId ? "hover" : "none"));
    var keep = {};
    if (mode === "query") {
      G.nodes.forEach(function (n) {
        if (n.name.toLowerCase().indexOf(G.query) >= 0) { keep[n.id] = 1; }
      });
    } else if (mode !== "none") {
      var id = mode === "focus" ? G.focus : hoverId;
      keep[id] = 1;
      G.edges.forEach(function (e) {
        if (e.src === id || e.dst === id) { keep[e.src] = 1; keep[e.dst] = 1; }
      });
    }
    var manyEdges = G.edges.length > 40;
    var zoomed = zoomScale() >= 1.45 || G.nodes.length <= 30;
    G.edgeEls.forEach(function (r) {
      var lit = !!G.litKeys[r.key];
      var on = mode === "none" ? false
        : (mode === "query" ? (keep[r.e.src] && keep[r.e.dst])
           : (keep[r.e.src] && keep[r.e.dst] &&
              (r.e.src === (G.focus || hoverId) ||
               r.e.dst === (G.focus || hoverId))));
      r.line.classList.toggle("hl", !!on || lit);
      r.line.classList.toggle("faded", mode !== "none" && !on && !lit);
      r.label.classList.toggle("faded", mode !== "none" && !on && !lit);
      r.label.classList.toggle("show", (!manyEdges || !!on || lit) && zoomed
                                        || !!on || lit);
    });
    G.nodes.forEach(function (n) {
      var g = G.nodeEls[n.id];
      var emph = mode === "none" || keep[n.id];
      g.classList.toggle("faded", !emph);
      var hub = (G.degree[n.id] || 0) >= 3 || (n.r || 0) >= 11;
      g.classList.toggle("nolabel",
        !(zoomed || hub || keep[n.id] || g.classList.contains("sel") ||
          g.classList.contains("lit")));
    });
  }

  function fitView() {
    if (!G.nodes.length || !G.vb) { return; }
    var xs = G.nodes.map(function (n) { return n.x; });
    var ys = G.nodes.map(function (n) { return n.y; });
    var pad = 70;
    var x0 = Math.min.apply(null, xs) - pad, x1 = Math.max.apply(null, xs) + pad;
    var y0 = Math.min.apply(null, ys) - pad, y1 = Math.max.apply(null, ys) + pad;
    var w = Math.max(120, x1 - x0), h = Math.max(120, y1 - y0);
    var ratio = G.w / G.h;                     // preserve aspect
    if (w / h > ratio) { h = w / ratio; } else { w = h * ratio; }
    G.vb = { x: (x0 + x1) / 2 - w / 2, y: (y0 + y1) / 2 - h / 2, w: w, h: h };
    applyVB(); updateEmphasis(null);
  }

  function centerOn(n) {
    if (!G.vb) { return; }
    G.vb.x = n.x - G.vb.w / 2; G.vb.y = n.y - G.vb.h / 2;
    applyVB();
  }

  function renderGraph(data) {
    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    G.nodes = data.nodes || []; G.edges = data.edges || [];
    G.byId = {}; G.edgeEls = []; G.nodeEls = {}; G.litKeys = {};
    $("graph-empty").hidden = G.nodes.length > 0;
    if (!G.nodes.length) { return; }
    G.w = svg.clientWidth || 860; G.h = svg.clientHeight || 540;
    G.vb = { x: 0, y: 0, w: G.w, h: G.h };
    svg.setAttribute("viewBox", "0 0 " + G.w + " " + G.h);
    G.K = Math.sqrt((G.w * G.h) / Math.max(1, G.nodes.length)) * 0.62;
    G.nodes.forEach(function (n, i) {
      var ang = (i / G.nodes.length) * 2 * Math.PI;
      n.x = G.w / 2 + (G.w / 3.4) * Math.cos(ang);
      n.y = G.h / 2 + (G.h / 3.4) * Math.sin(ang);
      n.vx = 0; n.vy = 0; G.byId[n.id] = n;
    });
    G.degree = {};
    G.edges.forEach(function (e) {
      G.degree[e.src] = (G.degree[e.src] || 0) + 1;
      G.degree[e.dst] = (G.degree[e.dst] || 0) + 1;
    });
    G.focus = null;
    var showLabels = G.edges.length <= 40;

    var gEdges = el("g", {}), gFlows = el("g", {}), gNodes = el("g", {});
    svg.appendChild(gEdges); svg.appendChild(gFlows); svg.appendChild(gNodes);

    G.edges.forEach(function (e) {
      var line = el("line", { "class": "edge " +
        (e.grounded ? "grounded" : "ungrounded") });
      line.appendChild(el("title", {})).textContent = e.predicate +
        (e.source_fact_id ? " — source: " + e.source_fact_id : " — NO SOURCE");
      gEdges.appendChild(line);
      var flow = el("line", { "class": "flow" });
      gFlows.appendChild(flow);
      var label = el("text", { "class": "edge-label" +
        (showLabels ? " show" : ""), "text-anchor": "middle" });
      label.textContent = e.predicate;
      gEdges.appendChild(label);
      G.edgeEls.push({ e: e, line: line, flow: flow, label: label,
                       key: edgeKey(e) });
    });

    G.nodes.forEach(function (n) {
      var g = el("g", { "class": "node",
                        "data-type": String(n.type || "").toLowerCase() });
      n.r = 7 + Math.min(7, (G.degree[n.id] || 0) * 1.4);
      g.appendChild(el("circle", { r: n.r }));
      var t = el("text", { x: n.r + 4, y: 4 });
      t.textContent = n.name;
      g.appendChild(t);
      g.addEventListener("click", function (ev) {
        if (G.dragMoved) { return; }
        ev.stopPropagation(); selectNode(n, g);
      });
      g.addEventListener("pointerdown", function (ev) {
        ev.preventDefault(); ev.stopPropagation();
        G.drag = n; G.dragMoved = false; n.pinned = true;
        svg.setPointerCapture(ev.pointerId);
      });
      g.addEventListener("mouseenter", function () {
        if (!G.focus && !G.query) { updateEmphasis(n.id); }
      });
      g.addEventListener("mouseleave", function () {
        if (!G.focus && !G.query) { updateEmphasis(null); }
      });
      gNodes.appendChild(g);
      G.nodeEls[n.id] = g;
    });

    reheat(REDUCED ? 0.9 : 1);
    if (REDUCED) {   // settle instantly, no animation frames visible
      for (var k = 0; k < 300; k++) { simStep(); G.alpha *= 0.985; }
      G.alpha = 0; draw();
    }
    updateEmphasis(null);
  }

  /* pan / zoom on the svg canvas */
  function applyVB() {
    svg.setAttribute("viewBox",
      G.vb.x + " " + G.vb.y + " " + G.vb.w + " " + G.vb.h);
  }
  svg.addEventListener("wheel", function (ev) {
    if (!G.vb) { return; }
    ev.preventDefault();
    var f = ev.deltaY > 0 ? 1.12 : 0.9;
    var mx = G.vb.x + (ev.offsetX / svg.clientWidth) * G.vb.w;
    var my = G.vb.y + (ev.offsetY / svg.clientHeight) * G.vb.h;
    G.vb.w *= f; G.vb.h *= f;
    G.vb.x = mx - (ev.offsetX / svg.clientWidth) * G.vb.w;
    G.vb.y = my - (ev.offsetY / svg.clientHeight) * G.vb.h;
    applyVB();
    updateEmphasis(null);                      // zoom drives the label LOD
  }, { passive: false });
  svg.addEventListener("pointerdown", function (ev) {
    if (G.drag || !G.vb) { return; }
    G.pan = { x: ev.clientX, y: ev.clientY, vx: G.vb.x, vy: G.vb.y,
              moved: false };
    svg.classList.add("panning");
    svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener("pointermove", function (ev) {
    if (G.drag) {
      if (!G.dragStart) { G.dragStart = { x: ev.clientX, y: ev.clientY }; }
      // 4px threshold: a twitchy click still SELECTS instead of dragging
      if (Math.abs(ev.clientX - G.dragStart.x) +
          Math.abs(ev.clientY - G.dragStart.y) > 4) { G.dragMoved = true; }
      var pt = svg.createSVGPoint();
      pt.x = ev.clientX; pt.y = ev.clientY;
      var p = pt.matrixTransform(svg.getScreenCTM().inverse());
      G.drag.x = p.x; G.drag.y = p.y;
      G.drag.vx = 0; G.drag.vy = 0;
      reheat(0.35);
    } else if (G.pan) {
      var sx = G.vb.w / svg.clientWidth, sy = G.vb.h / svg.clientHeight;
      G.vb.x = G.pan.vx - (ev.clientX - G.pan.x) * sx;
      G.vb.y = G.pan.vy - (ev.clientY - G.pan.y) * sy;
      applyVB();
    }
  });
  function endPointer(ev) {
    if (G.drag) { G.drag.pinned = false; G.drag = null; reheat(0.25); }
    else if (G.pan && ev && Math.abs(ev.clientX - G.pan.x) +
             Math.abs(ev.clientY - G.pan.y) < 4) {
      // background CLICK (not a pan): release focus, unlight the chain
      G.focus = null; clearLit();
      Array.prototype.forEach.call(svg.querySelectorAll(".node.sel"),
        function (x) { x.classList.remove("sel"); });
      updateEmphasis(null);
    }
    G.dragStart = null;
    G.pan = null; svg.classList.remove("panning");
    setTimeout(function () { G.dragMoved = false; }, 0);
  }
  svg.addEventListener("pointerup", endPointer);
  svg.addEventListener("pointercancel", endPointer);
  svg.addEventListener("dblclick", function () { fitView(); });
  $("graph-fit").addEventListener("click", fitView);

  /* search: live highlight; Enter selects & centers the first match */
  var searchBox = $("graph-search");
  searchBox.addEventListener("input", function () {
    G.query = searchBox.value.trim().toLowerCase();
    updateEmphasis(null);
  });
  searchBox.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      searchBox.value = ""; G.query = ""; updateEmphasis(null);
      searchBox.blur();
    }
    if (ev.key === "Enter") {
      ev.preventDefault();
      var hit = null;
      G.nodes.forEach(function (n) {
        if (!hit && G.query &&
            n.name.toLowerCase().indexOf(G.query) >= 0) { hit = n; }
      });
      if (hit) {
        centerOn(hit);
        selectNode(hit, G.nodeEls[hit.id]);
      }
    }
  });

  /* ---- dossier + chain lighting --------------------------------------------*/
  function clearLit() {
    G.litKeys = {};
    G.edgeEls.forEach(function (r) {
      r.line.classList.remove("hl"); r.flow.classList.remove("run");
      r.label.classList.remove("lit");
    });
    G.nodes.forEach(function (n) { G.nodeEls[n.id].classList.remove("lit"); });
  }

  function lightChain(derivation) {
    clearLit();
    (derivation || []).forEach(function (hop, i) {
      var key = hop.src_entity + "|" + hop.dst_entity + "|" + hop.predicate;
      var rec = null;
      G.edgeEls.forEach(function (r) { if (r.key === key) { rec = r; } });
      setTimeout(function () {
        if (rec) {
          G.litKeys[key] = 1;
          rec.line.classList.add("hl");
          rec.label.classList.add("lit", "show");
          if (!REDUCED) { rec.flow.classList.add("run"); }
        }
        [hop.src_entity, hop.dst_entity].forEach(function (nid) {
          var g = G.nodeEls[nid];
          if (g) { g.classList.add("lit"); }
        });
      }, REDUCED ? 0 : i * 260);
    });
  }

  function selectNode(n, g) {
    Array.prototype.forEach.call(svg.querySelectorAll(".node"),
      function (x) { x.classList.remove("sel"); });
    g.classList.add("sel");
    clearLit();
    G.focus = n.id;                            // sticky focus (Obsidian-like)
    updateEmphasis(null);
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
  function loadGraph() {
    api("/v1/graph?max_nodes=300&max_edges=600")
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

  $("keyform").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var v = $("key").value.trim();
    if (v) {
      sessionStorage.setItem(STORE, v); $("key").value = "";
      sseGen++; sseActive = false;         // re-auth the live stream
      loadLive(); loadGraph();
    }
  });
  $("graph-refresh").addEventListener("click", loadGraph);

  setInterval(loadLive, 30000);
  loadLive(); loadGraph();
})();
