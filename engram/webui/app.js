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

  function api(path) {
    return fetch(path, { headers: { Authorization: "Bearer " + token() } })
      .then(function (r) {
        if (r.status === 401) {
          sessionStorage.removeItem(STORE);
          throw new Error("invalid key — paste it again");
        }
        if (!r.ok) { throw new Error("gateway error " + r.status); }
        return r.json();
      });
  }

  function fail(e) {
    board.hidden = true; $("live").hidden = true;
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

  /* ---- graph: living force sim, drag, pan/zoom, chain lighting -------------*/
  var svg = $("graph");
  var G = { nodes: [], edges: [], byId: {}, edgeEls: [], nodeEls: {},
            alpha: 0, vb: null, running: false, drag: null, litKeys: {} };

  function edgeKey(e) { return e.src + "|" + e.dst + "|" + e.predicate; }

  function simStep() {
    var nodes = G.nodes, edges = G.edges, K = G.K, i, j;
    var step = 10 * G.alpha + 0.25;
    for (i = 0; i < nodes.length; i++) {
      var a = nodes[i], fx = 0, fy = 0;
      for (j = 0; j < nodes.length; j++) {
        if (i === j) { continue; }
        var dx = a.x - nodes[j].x, dy = a.y - nodes[j].y;
        var d2 = dx * dx + dy * dy || 0.01, d = Math.sqrt(d2);
        fx += (dx / d) * (K * K / d); fy += (dy / d) * (K * K / d);
      }
      fx += (G.w / 2 - a.x) * 0.02; fy += (G.h / 2 - a.y) * 0.02;
      a.vx = fx; a.vy = fy;
    }
    edges.forEach(function (e) {
      var s = G.byId[e.src], t = G.byId[e.dst];
      if (!s || !t) { return; }
      var dx = t.x - s.x, dy = t.y - s.y;
      var dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      var f = (dist - K) / dist * 0.5;
      s.vx += dx * f; s.vy += dy * f; t.vx -= dx * f; t.vy -= dy * f;
    });
    nodes.forEach(function (n) {
      if (n.fixed) { return; }
      var v = Math.sqrt(n.vx * n.vx + n.vy * n.vy) || 1;
      n.x += (n.vx / v) * Math.min(v, step);
      n.y += (n.vy / v) * Math.min(v, step);
      n.x = Math.max(26, Math.min(G.w - 26, n.x));
      n.y = Math.max(20, Math.min(G.h - 20, n.y));
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
    if (G.alpha > 0.015 && !document.hidden) {
      simStep(); draw();
      G.alpha *= 0.97;
      requestAnimationFrame(loop);
    } else { G.running = false; draw(); }
  }
  function reheat(a) {
    G.alpha = Math.max(G.alpha, a);
    if (!G.running) { G.running = true; requestAnimationFrame(loop); }
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
    var degree = {};
    G.edges.forEach(function (e) {
      degree[e.src] = (degree[e.src] || 0) + 1;
      degree[e.dst] = (degree[e.dst] || 0) + 1;
    });
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
      var r = 7 + Math.min(6, (degree[n.id] || 0) * 1.4);
      g.appendChild(el("circle", { r: r }));
      var t = el("text", { x: r + 4, y: 4 });
      t.textContent = n.name;
      g.appendChild(t);
      g.addEventListener("click", function (ev) {
        if (G.dragMoved) { return; }
        ev.stopPropagation(); selectNode(n, g);
      });
      g.addEventListener("pointerdown", function (ev) {
        ev.preventDefault(); ev.stopPropagation();
        G.drag = n; G.dragMoved = false; n.fixed = true;
        svg.setPointerCapture(ev.pointerId);
      });
      g.addEventListener("mouseenter", function () { hover(n.id, true); });
      g.addEventListener("mouseleave", function () { hover(null, false); });
      gNodes.appendChild(g);
      G.nodeEls[n.id] = g;
    });

    reheat(REDUCED ? 0.9 : 1);
    if (REDUCED) {   // settle instantly, no animation frames visible
      for (var k = 0; k < 240; k++) { simStep(); G.alpha *= 0.985; }
      G.alpha = 0; draw();
    }
  }

  function hover(id, on) {
    var neigh = {};
    if (on && id) {
      neigh[id] = 1;
      G.edges.forEach(function (e) {
        if (e.src === id || e.dst === id) { neigh[e.src] = 1; neigh[e.dst] = 1; }
      });
    }
    G.edgeEls.forEach(function (r) {
      var lit = G.litKeys[r.key];
      var connected = on && (neigh[r.e.src] && neigh[r.e.dst] &&
        (r.e.src === id || r.e.dst === id));
      r.line.classList.toggle("hl", !!connected || !!lit);
      r.line.classList.toggle("faded", on && !connected && !lit);
      r.label.classList.toggle("faded", on && !connected && !lit);
      r.label.classList.toggle("show",
        (G.edges.length <= 40 || !!connected || !!lit));
    });
    G.nodes.forEach(function (n) {
      G.nodeEls[n.id].classList.toggle("faded", on && !neigh[n.id]);
    });
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
  }, { passive: false });
  svg.addEventListener("pointerdown", function (ev) {
    if (G.drag || !G.vb) { return; }
    G.pan = { x: ev.clientX, y: ev.clientY, vx: G.vb.x, vy: G.vb.y };
    svg.classList.add("panning");
    svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener("pointermove", function (ev) {
    if (G.drag) {
      G.dragMoved = true;
      var pt = svg.createSVGPoint();
      pt.x = ev.clientX; pt.y = ev.clientY;
      var p = pt.matrixTransform(svg.getScreenCTM().inverse());
      G.drag.x = p.x; G.drag.y = p.y;
      reheat(0.35);
    } else if (G.pan) {
      var sx = G.vb.w / svg.clientWidth, sy = G.vb.h / svg.clientHeight;
      G.vb.x = G.pan.vx - (ev.clientX - G.pan.x) * sx;
      G.vb.y = G.pan.vy - (ev.clientY - G.pan.y) * sy;
      applyVB();
    }
  });
  function endPointer() {
    if (G.drag) { G.drag.fixed = false; G.drag = null; reheat(0.25); }
    G.pan = null; svg.classList.remove("panning");
    setTimeout(function () { G.dragMoved = false; }, 0);
  }
  svg.addEventListener("pointerup", endPointer);
  svg.addEventListener("pointercancel", endPointer);

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
    if (!token()) { return; }
    Promise.all([api("/v1/stats"), api("/v1/quarantine?limit=100")])
      .then(function (res) {
        board.hidden = false; err.hidden = true; $("live").hidden = false;
        renderStats(res[0]);
        renderBlocked(res[1].items || []);
      })
      .catch(fail);
  }
  function loadGraph() {
    if (!token()) { return; }
    api("/v1/graph?max_nodes=300&max_edges=600")
      .then(renderGraph).catch(fail);
  }

  $("keyform").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var v = $("key").value.trim();
    if (v) {
      sessionStorage.setItem(STORE, v); $("key").value = "";
      loadLive(); loadGraph();
    }
  });
  $("graph-refresh").addEventListener("click", loadGraph);

  setInterval(loadLive, 30000);
  loadLive(); loadGraph();
})();
