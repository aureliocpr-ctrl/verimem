/* VERIMEM — the knowledge graph, WHOLE and ALIVE (/ui).
   Rendering: sigma.js v2 (WebGL) on graphology, vendored same-origin
   (vendor/README.md) — CSP `script-src 'self'`, no CDN, no eval. Layout:
   ForceAtlas2 (LinLog) in a Web Worker.

   v2.1 — FORM and SMOOTHNESS (Aurelio 2026-07-16: "qualità Obsidian,
   basta giocattoli"):
   - Louvain communities (vendored bundle) give the hairball its SHAPE:
     cluster colors + legend, like Obsidian groups.
   - Edge BACKBONE: by default only each node's strongest ties are drawn
     (rank ≤ k against both endpoints' neighbor lists); a slider goes to
     100%. Declared in the UI, never silent.
   - Hover lights the NEIGHBORHOOD and fades the rest — the one gesture
     that makes a graph feel premium.
   - Double-click a node → LOCAL graph (2 hops); breadcrumb exits.
   - The 26s layout with a full re-render per tick was the perceived lag:
     now LinLog runs ~9s with edges HIDDEN while it settles (nodes-only
     renders are cheap; edges snap in when the shape is ready).
   - The live pulse used to force a FULL refresh per animation frame —
     under real traffic that was permanent lag. Now it decays in 140ms
     steps (≈7 refresh/s only while something is hot; idle = zero).

   API consumed by app.js:
     var g = new VerimemGraph(container, {onSelect, onLayout, onLocal});
     g.load(compact)            -> {nodes, edges} totals
     g.addLive(created, touched)-> int
     g.touch(ids, opts)         -> pulse (opts.born)
     g.search(q)                -> first matching id | null
     g.focus(id) / g.fit() / g.setSelected(id|null)
     g.setBackbone(k)           -> edges shown  (k=9 → ALL)
     g.clusters()               -> [{id,color,size,label}] top clusters
     g.setClusterFilter(id|null)
     g.localEnter(id) / g.localExit()
     g.layout(ms) / g.stopLayout() / g.layoutRunning()
     g.name(id) / g.has(id) / g.counts() / g.shownEdges()
   `compact` is /v1/graph/full: {n:[[id,name,type],..], e:[[si,di,grounded],..]}. */
(function () {
  "use strict";

  var REDUCED = window.matchMedia
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var DARK = window.matchMedia
    && window.matchMedia("(prefers-color-scheme: dark)");

  function readPalette() {
    var cs = getComputedStyle(document.documentElement);
    function v(name, fb) {
      var x = cs.getPropertyValue(name).trim();
      return x || fb;
    }
    return {
      node: v("--graph-node", "#8A7E66"),
      iso: v("--graph-iso", "rgba(138,126,102,.38)"),
      lit: v("--graph-lit", "#2E6B4F"),
      ink: v("--graph-ink", "#17140E"),
      edge: v("--graph-edge", "rgba(46,107,79,.30)"),
      edgeUn: v("--graph-edge-un", "rgba(166,51,31,.28)"),
      born: v("--ok", "#2E6B4F"),
      // fade = a solid tone near the background: alpha stacking on 7k
      // overlapping nodes turned the stage into paste (2026-07-16)
      faded: (DARK && DARK.matches) ? "#2A2418" : "#DED5C2",
      fadedEdge: (DARK && DARK.matches) ? "#221D12" : "#E6DECB"
    };
  }

  /* cluster palette: golden-angle hues, saturation/lightness by theme */
  function clusterColor(i, dark) {
    var hue = (i * 137.508) % 360;
    return "hsl(" + hue.toFixed(0) + " " + (dark ? "42%" : "45%") + " "
      + (dark ? "62%" : "42%") + ")";
  }

  function VerimemGraph(container, opts) {
    if (!(this instanceof VerimemGraph)) { return new VerimemGraph(container, opts); }
    var self = this;
    opts = opts || {};

    var GraphCtor = window.graphology && (window.graphology.Graph || window.graphology);
    var lib = window.graphologyLibrary;
    if (!GraphCtor || !window.Sigma || !lib) {
      throw new Error("graph vendor bundles missing");
    }

    this.pal = readPalette();
    this.g = new GraphCtor({ type: "undirected", multi: false,
                             allowSelfLoops: false });
    this.adj = new Map();          // id -> Set(neighbor ids)
    this.hot = new Map();          // id -> {t0, until, born}
    this.query = "";
    this._matches = 0;
    this.sel = null;
    this.hover = null;
    this._clusters = [];           // [{id,color,size,label}] big → small
    this._clusterOf = new Map();   // community id -> palette index
    this._clusterFilter = null;
    this._local = null;            // {root, keep:Set} when in local mode
    this._backboneK = 3;
    this._shownEdges = 0;
    this._layoutHot = false;       // edges hidden while the big layout runs
    this._pulseTimer = null;
    this._fa2 = null;
    this._fa2Timer = null;
    this._followTimer = null;
    this._onLayout = opts.onLayout || function () {};
    this._onSelect = opts.onSelect || function () {};
    this._onLocal = opts.onLocal || function () {};

    var HIDDEN_EDGE = { hidden: true };   // constant: zero alloc in reducers

    var renderer = new window.Sigma(this.g, container, {
      allowInvalidContainer: true,
      renderLabels: true,
      labelRenderedSizeThreshold: 5.5,
      labelDensity: 0.36,
      labelGridCellSize: 90,
      labelFont: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
      labelSize: 11,
      labelColor: { color: this.pal.ink },
      defaultEdgeType: "line",
      hideEdgesOnMove: true,
      hideLabelsOnMove: true,
      zIndex: false,
      stagePadding: 24,
      minCameraRatio: 0.008,
      maxCameraRatio: 14,
      nodeReducer: function (node, data) {
        var out = data;
        // local mode: outside the kept set nothing exists
        if (self._local && !self._local.keep.has(node)) {
          return Object.assign({}, data, { hidden: true });
        }
        if (self._clusterFilter !== null && data.c !== self._clusterFilter
            && self.hover !== node && self.sel !== node) {
          out = Object.assign({}, out, { color: self.pal.faded, label: null });
        }
        var h = self.hot.get(node);
        if (h) {
          var k = Math.max(0, (h.until - performance.now()) / (h.until - h.t0));
          out = Object.assign({}, out === data ? data : out, {
            color: h.born ? self.pal.born : self.pal.lit,
            size: data.size * (1 + (h.born ? 1.2 : 0.9) * k) + 1.2
          });
          if (k <= 0) { self.hot.delete(node); }
        }
        if (self.hover && self.hover !== node) {
          var nb = self.adj.get(self.hover);
          if (!(nb && nb.has(node))) {
            out = Object.assign({}, out === data ? data : out,
                                { color: self.pal.faded, label: null });
          }
        }
        if (self.query) {
          var match = data.fname && data.fname.indexOf(self.query) >= 0;
          if (!match) {
            out = Object.assign({}, out === data ? data : out, { hidden: true });
          } else if (self._matches <= 40) {
            out = Object.assign({}, out === data ? data : out, { forceLabel: true });
          }
        }
        if (self.sel === node || self.hover === node) {
          out = Object.assign({}, out === data ? data : out,
                              { highlighted: true, forceLabel: true });
        }
        return out;
      },
      edgeReducer: function (edge, data, ctx) {
        // big layout settling: nodes-only frames are cheap; edges snap in
        // at the end. (26s of full re-renders WAS the lag.)
        if (self._layoutHot) { return HIDDEN_EDGE; }
        var s = self.g.source(edge), t = self.g.target(edge);
        if (self._local) {
          return (self._local.keep.has(s) && self._local.keep.has(t))
            ? data : HIDDEN_EDGE;   // local shows ALL its own edges
        }
        if (data.bb > self._backboneK) { return HIDDEN_EDGE; }
        if (self.hover) {
          if (s !== self.hover && t !== self.hover) {
            return Object.assign({}, data, { color: self.pal.fadedEdge });
          }
          return Object.assign({}, data, { size: 1.4 });
        }
        return data;
      }
    });
    this.r = renderer;

    renderer.on("clickNode", function (e) {
      var a = self.g.getNodeAttributes(e.node);
      self.setSelected(e.node);
      self._onSelect({ id: e.node, name: a.rawname || a.label });
    });
    renderer.on("doubleClickNode", function (e) {
      if (e && e.preventSigmaDefault) { e.preventSigmaDefault(); }
      self.localEnter(e.node);
    });
    renderer.on("clickStage", function () { self.setSelected(null); });
    renderer.on("doubleClickStage", function (e) {
      if (e && e.preventSigmaDefault) { e.preventSigmaDefault(); }
      if (self._local) { self.localExit(); } else { self.fit(); }
    });
    renderer.on("enterNode", function (e) {
      self.hover = e.node; container.style.cursor = "pointer";
      self.r.refresh();
    });
    renderer.on("leaveNode", function () {
      self.hover = null; container.style.cursor = "grab";
      self.r.refresh();
    });
    var dragging = null;
    renderer.on("downNode", function (e) {
      dragging = e.node;
      if (!renderer.getCustomBBox()) { renderer.setCustomBBox(renderer.getBBox()); }
    });
    renderer.getMouseCaptor().on("mousemovebody", function (e) {
      if (!dragging) { return; }
      var pos = renderer.viewportToGraph(e);
      self.g.setNodeAttribute(dragging, "x", pos.x);
      self.g.setNodeAttribute(dragging, "y", pos.y);
      e.preventSigmaDefault();
      e.original.preventDefault(); e.original.stopPropagation();
    });
    renderer.getMouseCaptor().on("mouseup", function () { dragging = null; });

    if (DARK && DARK.addEventListener) {
      DARK.addEventListener("change", function () {
        self.pal = readPalette();
        renderer.setSetting("labelColor", { color: self.pal.ink });
        self._recolor();
        renderer.refresh();
      });
    }
  }

  /* ---- colors: community first, belt stays quiet ---------------------------*/
  VerimemGraph.prototype._nodeColorFor = function (c, deg) {
    if (deg === 0) { return this.pal.iso; }
    var ix = this._clusterOf.get(c);
    return ix === undefined ? this.pal.node
      : clusterColor(ix, DARK && DARK.matches);
  };
  VerimemGraph.prototype._recolor = function () {
    var self = this;
    this.g.forEachNode(function (n, a) {
      self.g.setNodeAttribute(n, "color", self._nodeColorFor(a.c, a.deg));
    });
    this.g.forEachEdge(function (ed, a) {
      self.g.setEdgeAttribute(ed, "color",
        a.grounded ? self.pal.edge : self.pal.edgeUn);
    });
    this._clusters.forEach(function (cl, i) {
      cl.color = clusterColor(i, DARK && DARK.matches);
    });
  };

  /* ---- load: the WHOLE store ------------------------------------------------*/
  VerimemGraph.prototype.load = function (data) {
    var g = this.g, self = this, i;
    this.stopLayout();
    g.clear();
    this.adj.clear();
    this.hot.clear();
    this._local = null;
    this._clusterFilter = null;
    var n = data.n || [], e = data.e || [];

    var deg = new Array(n.length).fill(0);
    for (i = 0; i < e.length; i++) { deg[e[i][0]]++; deg[e[i][1]]++; }

    var order = n.map(function (_, ix) { return ix; })
      .sort(function (a, b) { return deg[b] - deg[a]; });
    var nCon = 0;
    for (i = 0; i < order.length; i++) { if (deg[order[i]] > 0) { nCon++; } }
    var GA = Math.PI * (3 - Math.sqrt(5)),
        STEP = 24,
        RCON = Math.sqrt(Math.max(nCon, 1)) * STEP,
        nIso = order.length - nCon,
        rank = 0, iso = 0;
    for (i = 0; i < order.length; i++) {
      var ix = order[i], row = n[ix], d = deg[ix], x, y, th;
      if (d > 0) {
        th = rank * GA;
        var rr = STEP * Math.sqrt(rank + 0.5);
        x = Math.cos(th) * rr; y = Math.sin(th) * rr;
        rank++;
      } else {
        th = iso * GA * 1.618;
        var br = RCON * 1.25 + STEP * 2 * (((iso / Math.max(nIso, 1)) * 6) | 0);
        x = Math.cos(th) * br; y = Math.sin(th) * br;
        iso++;
      }
      var name = String(row[1] == null ? row[0] : row[1]);
      g.addNode(row[0], {
        label: name.length > 30 ? name.slice(0, 29) + "…" : name,
        rawname: name, fname: name.toLowerCase(),
        t: row[2] || "", deg: d, c: -1,
        size: d === 0 ? 1.6 : Math.min(2 + Math.log2(1 + d) * 1.35, 13),
        color: this.pal.node,
        x: x, y: y
      });
    }
    for (i = 0; i < e.length; i++) {
      var a = n[e[i][0]], b = n[e[i][1]];
      if (!a || !b || a[0] === b[0]) { continue; }
      var grounded = e[i][2] ? 1 : 0;
      if (g.hasEdge(a[0], b[0])) {
        if (grounded && !g.getEdgeAttribute(a[0], b[0], "grounded")) {
          g.setEdgeAttribute(a[0], b[0], "grounded", 1);
          g.setEdgeAttribute(a[0], b[0], "color", this.pal.edge);
        }
      } else {
        g.addEdge(a[0], b[0], {
          grounded: grounded, size: 0.6, bb: 99,
          color: grounded ? this.pal.edge : this.pal.edgeUn
        });
        var sa = this.adj.get(a[0]); if (!sa) { this.adj.set(a[0], sa = new Set()); }
        var sb = this.adj.get(b[0]); if (!sb) { this.adj.set(b[0], sb = new Set()); }
        sa.add(b[0]); sb.add(a[0]);
      }
    }

    /* communities (Louvain, vendored): the SHAPE of the hairball.
       louvain(graph) -> {node: communityId} is the stable signature. */
    try {
      var louv = window.graphologyLibrary.communitiesLouvain;
      var communities = louv(g);
      g.forEachNode(function (node) {
        g.setNodeAttribute(node, "c", communities[node]);
      });
      var sizes = new Map();
      g.forEachNode(function (node, at) {
        if (at.deg > 0) { sizes.set(at.c, (sizes.get(at.c) || 0) + 1); }
      });
      var top = Array.from(sizes.entries())
        .sort(function (p, q) { return q[1] - p[1]; }).slice(0, 12);
      this._clusterOf.clear();
      this._clusters = top.map(function (pair, iy) {
        self._clusterOf.set(pair[0], iy);
        return { id: pair[0], size: pair[1],
                 color: clusterColor(iy, DARK && DARK.matches), label: "" };
      });
      // name each cluster after its highest-degree member
      var bestDeg = new Map();
      g.forEachNode(function (node, at) {
        var ixc = self._clusterOf.get(at.c);
        if (ixc !== undefined && (bestDeg.get(ixc) || -1) < at.deg) {
          bestDeg.set(ixc, at.deg);
          self._clusters[ixc].label = at.rawname;
        }
      });
    } catch (err) { this._clusters = []; }
    this._recolor();

    /* edge backbone rank: an edge is structural at k if it is among the
       top-k strongest ties of AT LEAST one endpoint (ties = neighbor degree,
       the signal we have; weights are clique counts, all ~equal). */
    var rankOf = new Map();
    this.adj.forEach(function (set, node) {
      var arr = Array.from(set);
      arr.sort(function (p, q) { return g.getNodeAttribute(q, "deg")
                                      - g.getNodeAttribute(p, "deg"); });
      var m = new Map();
      for (var j = 0; j < arr.length; j++) { m.set(arr[j], j + 1); }
      rankOf.set(node, m);
    });
    g.forEachEdge(function (ed, at, s, t) {
      var rs = rankOf.get(s), rt = rankOf.get(t);
      var rr = Math.min(rs ? (rs.get(t) || 99) : 99, rt ? (rt.get(s) || 99) : 99);
      g.setEdgeAttribute(ed, "bb", rr);
    });
    this.setBackbone(this._backboneK);

    this.r.setCustomBBox(null);
    this.r.refresh();
    this.layout(nCon > 3000 ? 9000 : 5000);
    this.fit();
    return { nodes: g.order, edges: g.size };
  };

  /* ---- backbone slider -------------------------------------------------------*/
  VerimemGraph.prototype.setBackbone = function (k) {
    this._backboneK = k >= 9 ? 99 : k;
    var shown = 0, self = this;
    this.g.forEachEdge(function (ed, at) {
      if (at.bb <= self._backboneK) { shown++; }
    });
    this._shownEdges = shown;
    this.r.refresh();
    return shown;
  };
  VerimemGraph.prototype.shownEdges = function () { return this._shownEdges; };

  /* ---- clusters ---------------------------------------------------------------*/
  VerimemGraph.prototype.clusters = function () { return this._clusters; };
  VerimemGraph.prototype.setClusterFilter = function (id) {
    this._clusterFilter = (id === null || id === undefined) ? null : id;
    this.r.refresh();
  };

  /* ---- local graph (2 hops) ----------------------------------------------------*/
  VerimemGraph.prototype.localEnter = function (id) {
    if (!this.g.hasNode(id)) { return; }
    var keep = new Set([id]);
    var n1 = this.adj.get(id) || new Set();
    n1.forEach(function (a) { keep.add(a); });
    var self = this;
    n1.forEach(function (a) {
      (self.adj.get(a) || new Set()).forEach(function (b) { keep.add(b); });
    });
    this._local = { root: id, keep: keep };
    this._onLocal(this.name(id), keep.size);
    this.r.refresh();
    this.fit();
  };
  VerimemGraph.prototype.localExit = function () {
    this._local = null;
    this._onLocal(null, 0);
    this.r.refresh();
    this.fit();
  };

  /* ---- FA2 (LinLog) in a worker -------------------------------------------------*/
  VerimemGraph.prototype._followBBox = function () {
    try { this.r.setCustomBBox(this.r.getBBox()); }
    catch (e) { /* renderer mid-teardown */ }
  };
  VerimemGraph.prototype.layout = function (ms, quiet) {
    var self = this, lib = window.graphologyLibrary;
    this.stopLayout();
    if (this.g.order < 2) { return; }
    var settings = lib.layoutForceAtlas2.inferSettings(this.g);
    settings.strongGravityMode = false;
    settings.gravity = 0.06;
    settings.linLogMode = true;            // clusters, not one solid ball
    settings.outboundAttractionDistribution = true;
    settings.scalingRatio = (settings.scalingRatio || 10) * 1.8;
    this._quiet = !!quiet;
    this._layoutHot = !quiet;              // big layout: nodes-only frames
    this._fa2 = new lib.FA2Layout(this.g, { settings: settings });
    this._fa2.start();
    this._onLayout(true);
    if (!this._quiet) {
      this._followTimer = setInterval(function () { self._followBBox(); }, 1200);
    }
    this._fa2Timer = setTimeout(function () { self.stopLayout(); }, ms || 9000);
  };
  VerimemGraph.prototype.stopLayout = function () {
    if (this._fa2Timer) { clearTimeout(this._fa2Timer); this._fa2Timer = null; }
    if (this._followTimer) {
      clearInterval(this._followTimer); this._followTimer = null;
    }
    if (this._fa2) {
      try { this._fa2.kill(); } catch (e) { /* already dead */ }
      this._fa2 = null;
      this._layoutHot = false;             // edges snap in, shape revealed
      if (!this._quiet) { this._followBBox(); this.fit(); }
      this.r.refresh();
      this._onLayout(false);
    }
  };
  VerimemGraph.prototype.layoutRunning = function () {
    return !!(this._fa2 && this._fa2.isRunning && this._fa2.isRunning());
  };

  /* ---- LIVE: birth without refetch ------------------------------------------------*/
  VerimemGraph.prototype.addLive = function (created, touched) {
    var g = this.g, self = this, added = 0, i, j;
    (created || []).forEach(function (c) {
      if (!c || !c.id || g.hasNode(c.id)) { return; }
      var sx = 0, sy = 0, k = 0, inheritC = -1;
      (touched || []).forEach(function (tid) {
        if (tid !== c.id && g.hasNode(tid)) {
          sx += g.getNodeAttribute(tid, "x");
          sy += g.getNodeAttribute(tid, "y"); k++;
          if (inheritC < 0) { inheritC = g.getNodeAttribute(tid, "c"); }
        }
      });
      var x, y;
      if (k) {
        x = sx / k + (Math.random() - 0.5) * 30;
        y = sy / k + (Math.random() - 0.5) * 30;
      } else {
        var th = Math.random() * Math.PI * 2;
        x = Math.cos(th) * 60; y = Math.sin(th) * 60;
      }
      var name = String(c.name || c.id);
      g.addNode(c.id, {
        label: name.length > 30 ? name.slice(0, 29) + "…" : name,
        rawname: name, fname: name.toLowerCase(),
        t: c.type || "", deg: 0, c: inheritC, size: 1.6,
        color: self.pal.iso, x: x, y: y
      });
      added++;
    });
    var head = (touched || []).slice(0, 8).filter(function (id) {
      return g.hasNode(id);
    });
    for (i = 0; i < head.length; i++) {
      for (j = i + 1; j < head.length; j++) {
        if (!g.hasEdge(head[i], head[j])) {
          g.addEdge(head[i], head[j],
                    { grounded: 1, size: 0.6, bb: 1,   // live ties are fresh news
                      color: this.pal.edge });
          var sa = this.adj.get(head[i]);
          if (!sa) { this.adj.set(head[i], sa = new Set()); }
          var sb = this.adj.get(head[j]);
          if (!sb) { this.adj.set(head[j], sb = new Set()); }
          sa.add(head[j]); sb.add(head[i]);
        }
      }
    }
    head.forEach(function (id) {
      var d = g.degree(id);
      g.mergeNodeAttributes(id, {
        deg: d,
        size: d === 0 ? 1.6 : Math.min(2 + Math.log2(1 + d) * 1.35, 13),
        color: self._nodeColorFor(g.getNodeAttribute(id, "c"), d)
      });
    });
    if (added) { this._shownEdges = this.setBackbone(this._backboneK); }
    if (added && !this.layoutRunning()) { this.layout(1500, true); }
    return added;
  };

  /* ---- pulse: stepped decay (never a full refresh per frame) -------------------*/
  VerimemGraph.prototype.touch = function (ids, opts) {
    var self = this;
    opts = opts || {};
    var now = performance.now();
    var dur = REDUCED ? 350 : (opts.born ? 2400 : 1200);
    (ids || []).forEach(function (id) {
      if (self.g.hasNode(id)) {
        self.hot.set(id, { t0: now, until: now + dur, born: !!opts.born });
      }
    });
    if (this.hot.size && !this._pulseTimer) {
      this._pulseTimer = setInterval(function () {
        self.r.refresh();
        if (!self.hot.size) {
          clearInterval(self._pulseTimer); self._pulseTimer = null;
        }
      }, 140);
      this.r.refresh();
    }
  };

  /* ---- search / camera / selection ----------------------------------------------*/
  VerimemGraph.prototype.search = function (q) {
    this.query = (q || "").toLowerCase();
    var first = null, self = this, m = 0;
    if (this.query) {
      this.g.forEachNode(function (n, a) {
        if (a.fname && a.fname.indexOf(self.query) >= 0) {
          m++; if (!first) { first = n; }
        }
      });
    }
    this._matches = m;
    this.r.refresh();
    return first;
  };
  VerimemGraph.prototype.focus = function (id) {
    if (!this.g.hasNode(id)) { return; }
    var d = this.r.getNodeDisplayData(id);
    if (d) {
      this.r.getCamera().animate({ x: d.x, y: d.y, ratio: 0.3 },
                                 { duration: REDUCED ? 0 : 500 });
    }
  };
  VerimemGraph.prototype.fit = function () {
    this.r.getCamera().animatedReset({ duration: REDUCED ? 0 : 450 });
  };
  VerimemGraph.prototype.setSelected = function (id) {
    this.sel = id || null;
    this.r.refresh();
  };
  VerimemGraph.prototype.name = function (id) {
    return this.g.hasNode(id)
      ? (this.g.getNodeAttribute(id, "rawname") || id) : id;
  };
  VerimemGraph.prototype.has = function (id) { return this.g.hasNode(id); };
  VerimemGraph.prototype.counts = function () {
    return { nodes: this.g.order, edges: this.g.size };
  };
  VerimemGraph.prototype.destroy = function () {
    this.stopLayout();
    if (this._pulseTimer) { clearInterval(this._pulseTimer); }
    this.r.kill();
  };

  window.VerimemGraph = VerimemGraph;
})();
