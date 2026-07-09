/* Verimem trust console.
 * All data arrives via authenticated fetch (bearer from sessionStorage);
 * this file ships static — no tenant data is ever baked in. */
(function () {
  "use strict";
  var STORE = "verimem_bearer";                 // same key as /dashboard
  var $ = function (id) { return document.getElementById(id); };
  var err = $("err"), board = $("board");

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
    board.hidden = true;
    err.textContent = e.message; err.hidden = false;
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

  /* ---- odometer + layers ------------------------------------------------ */
  function rows(el, obj, empty) {
    var keys = Object.keys(obj || {}).sort();
    if (!keys.length) {
      el.innerHTML = '<div class="row muted">' + empty + "</div>"; return;
    }
    el.innerHTML = keys.map(function (k) {
      return '<div class="row"><span>' + esc(k) + "</span><span>" +
             esc(String(obj[k])) + "</span></div>";
    }).join("");
  }

  function renderStats(d) {
    var led = (d.trust || {}).ledger || {};
    ["admitted", "quarantined", "rejected", "abstained"].forEach(function (a) {
      $("n-" + a).textContent = led[a] || 0;
    });
    rows($("layers"), (d.trust || {}).by_layer, "no gate layer has fired yet");
    rows($("store"), (d.trust || {}).store, "empty store");
    var failures = (d.trust || {}).ledger_write_failures || 0;
    $("meta").innerHTML = "tenant: " + esc(d.tenant) +
      " &middot; refreshed " + new Date().toLocaleTimeString() +
      " &middot; auto-refresh 30s" +
      (failures ? ' &middot; <span class="warn">' + failures +
                  " ledger write failures</span>" : "");
  }

  /* ---- blocked claims ---------------------------------------------------- */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;",
               '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function renderBlocked(items) {
    var body = $("blocked-rows");
    $("blocked-empty").hidden = items.length > 0;
    body.innerHTML = items.map(function (it) {
      var when = new Date(it.created_at * 1000);
      return "<tr><td class='when'>" + when.toLocaleDateString() + " " +
        when.toLocaleTimeString() + "</td><td class='claim'>" +
        esc(it.proposition) + "</td><td class='topic'>" +
        esc(it.topic || "") + "</td></tr>";
    }).join("");
  }

  /* ---- graph: tiny force layout, no dependencies ------------------------- */
  var SVG = "http://www.w3.org/2000/svg";
  var sel = null;

  function el(tag, attrs) {
    var e = document.createElementNS(SVG, tag);
    Object.keys(attrs || {}).forEach(function (k) {
      e.setAttribute(k, attrs[k]);
    });
    return e;
  }

  function layout(nodes, edges, w, h, done) {
    // spring-electric: repulsion between all pairs, springs along edges,
    // slight gravity to the center; ~240 cooled iterations offline, then draw.
    var idx = {}, i;
    nodes.forEach(function (n, j) {
      idx[n.id] = j;
      var a = (j / nodes.length) * 2 * Math.PI;      // deterministic seed
      n.x = w / 2 + (w / 3.2) * Math.cos(a);
      n.y = h / 2 + (h / 3.2) * Math.sin(a);
      n.vx = 0; n.vy = 0;
    });
    var K = Math.sqrt((w * h) / Math.max(1, nodes.length)) * 0.72;
    for (var it = 0; it < 240; it++) {
      var t = 1 - it / 240, step = 12 * t * t + 0.4;
      for (i = 0; i < nodes.length; i++) {
        var a1 = nodes[i], fx = 0, fy = 0, j2, dx, dy, d2, d;
        for (j2 = 0; j2 < nodes.length; j2++) {
          if (i === j2) { continue; }
          dx = a1.x - nodes[j2].x; dy = a1.y - nodes[j2].y;
          d2 = dx * dx + dy * dy || 0.01; d = Math.sqrt(d2);
          fx += (dx / d) * (K * K / d); fy += (dy / d) * (K * K / d);
        }
        fx += (w / 2 - a1.x) * 0.02; fy += (h / 2 - a1.y) * 0.02;
        a1.vx = fx; a1.vy = fy;
      }
      edges.forEach(function (e2) {
        var s = nodes[idx[e2.src]], d3 = nodes[idx[e2.dst]];
        if (!s || !d3) { return; }
        var dx2 = d3.x - s.x, dy2 = d3.y - s.y;
        var dist = Math.sqrt(dx2 * dx2 + dy2 * dy2) || 0.01;
        var f = (dist - K) / dist * 0.5;
        s.vx += dx2 * f; s.vy += dy2 * f;
        d3.vx -= dx2 * f; d3.vy -= dy2 * f;
      });
      for (i = 0; i < nodes.length; i++) {
        var n2 = nodes[i];
        var vlen = Math.sqrt(n2.vx * n2.vx + n2.vy * n2.vy) || 1;
        n2.x += (n2.vx / vlen) * Math.min(vlen, step);
        n2.y += (n2.vy / vlen) * Math.min(vlen, step);
        n2.x = Math.max(28, Math.min(w - 28, n2.x));
        n2.y = Math.max(22, Math.min(h - 22, n2.y));
      }
    }
    done();
  }

  function renderGraph(data) {
    var svg = $("graph"), empty = $("graph-empty");
    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    var nodes = data.nodes || [], edges = data.edges || [];
    empty.hidden = nodes.length > 0;
    if (!nodes.length) { return; }
    var w = svg.clientWidth || 800, h = svg.clientHeight || 520;
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    layout(nodes, edges, w, h, function () {
      var byId = {};
      nodes.forEach(function (n) { byId[n.id] = n; });
      edges.forEach(function (e2) {
        var s = byId[e2.src], d = byId[e2.dst];
        if (!s || !d) { return; }
        var line = el("line", {
          x1: s.x, y1: s.y, x2: d.x, y2: d.y,
          "class": "edge " + (e2.grounded ? "grounded" : "ungrounded")
        });
        line.appendChild(el("title", {})).textContent =
          e2.predicate + (e2.source_fact_id
            ? " — source: " + e2.source_fact_id : " — NO SOURCE");
        svg.appendChild(line);
        var lbl = el("text", {
          x: (s.x + d.x) / 2, y: (s.y + d.y) / 2 - 3,
          "class": "edge-label", "text-anchor": "middle"
        });
        lbl.textContent = e2.predicate;
        svg.appendChild(lbl);
      });
      nodes.forEach(function (n) {
        var g = el("g", { "class": "node", transform:
                          "translate(" + n.x + "," + n.y + ")" });
        g.appendChild(el("circle", { r: 9 }));
        var t = el("text", { x: 12, y: 4 });
        t.textContent = n.name;
        g.appendChild(t);
        g.addEventListener("click", function () { selectNode(n, g); });
        svg.appendChild(g);
      });
    });
  }

  function selectNode(n, g) {
    var svg = $("graph");
    Array.prototype.forEach.call(svg.querySelectorAll(".node"),
      function (x) { x.classList.remove("sel"); });
    g.classList.add("sel");
    sel = n.id;
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
        box.classList.toggle("open");
      });
      ds.length === 1 && box.classList.add("open");
      host.appendChild(box);
    });
  }

  /* ---- load ------------------------------------------------------------- */
  function loadLive() {                       // cheap, auto-refreshed
    if (!token()) { return; }
    Promise.all([api("/v1/stats"), api("/v1/quarantine?limit=100")])
      .then(function (res) {
        board.hidden = false; err.hidden = true;
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
