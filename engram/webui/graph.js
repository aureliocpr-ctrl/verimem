/* VERIMEM — the knowledge graph, WHOLE and ALIVE (/ui).
   Rendering: sigma.js v2 (WebGL) on graphology, both vendored same-origin
   (see vendor/README.md) — CSP `script-src 'self'`, no CDN at runtime, no
   eval. Layout: ForceAtlas2 in a web worker (graphology-library FA2Layout),
   so the main thread never blocks — the 2026-07-16 lesson: the hand-rolled
   canvas physics froze the page the moment the REAL store (7.7k nodes / 78k
   edges) met REAL live traffic. Battle-tested library, worker layout,
   incremental live updates (no full refetch on node birth).

   API consumed by app.js:
     var g = new VerimemGraph(container, {onSelect, onLayout});
     g.load(compact)            -> {nodes, edges} actually drawn
     g.addLive(created, touched)-> int (nodes added incrementally)
     g.touch(ids, opts)         -> pulse nodes (live "firing"; opts.born)
     g.search(q)                -> first matching id | null (highlights all)
     g.focus(id) / g.fit()      -> camera
     g.setSelected(id|null)     -> persistent highlight
     g.name(id) / g.has(id) / g.counts()
     g.layout(ms) / g.stopLayout() / g.layoutRunning()
   `compact` is /v1/graph/full: {n:[[id,name,type],..], e:[[si,di,grounded],..]}. */
(function () {
  "use strict";

  var REDUCED = window.matchMedia
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* palette resolved from the console's CSS variables so the graph follows
     the light/dark theme; re-read on theme change (recolor, not rebuild). */
  function readPalette() {
    var cs = getComputedStyle(document.documentElement);
    function v(name, fb) {
      var x = cs.getPropertyValue(name).trim();
      return x || fb;
    }
    return {
      node: v("--graph-node", "#8A7E66"),
      hub: v("--graph-hub", "#5F543F"),
      iso: v("--graph-iso", "rgba(138,126,102,.38)"),
      lit: v("--graph-lit", "#2E6B4F"),
      ink: v("--graph-ink", "#17140E"),
      edge: v("--graph-edge", "rgba(46,107,79,.30)"),
      edgeUn: v("--graph-edge-un", "rgba(166,51,31,.28)"),
      born: v("--ok", "#2E6B4F"),
      person: v("--node-person", "#5B7A93"),
      org: v("--node-org", "#4C8A6B"),
      place: v("--node-place", "#B08A3E")
    };
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
    this.hot = new Map();          // id -> {t0, until, born}
    this.query = "";
    this._matches = 0;
    this.sel = null;
    this._pulseRaf = null;
    this._fa2 = null;
    this._fa2Timer = null;
    this._onLayout = opts.onLayout || function () {};
    this._onSelect = opts.onSelect || function () {};

    function nodeColor(type, deg) {
      var p = self.pal;
      if (deg === 0) { return p.iso; }
      if (type === "person") { return p.person; }
      if (type === "org") { return p.org; }
      if (type === "place") { return p.place; }
      return deg >= 30 ? p.hub : p.node;
    }
    this._nodeColor = nodeColor;

    /* the reducer stays LEAN — it runs per node per refresh. Static looks
       (type color, degree size) are baked into attributes at add-time; the
       reducer only overlays the DYNAMIC states: pulse / search / selection. */
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
        var h = self.hot.get(node);
        if (h) {
          var k = Math.max(0, (h.until - performance.now()) / (h.until - h.t0));
          out = Object.assign({}, data, {
            color: h.born ? self.pal.born : self.pal.lit,
            size: data.size * (1 + (h.born ? 1.2 : 0.9) * k) + 1.2
          });
          if (k <= 0) { self.hot.delete(node); }
        }
        if (self.query) {
          var match = data.fname && data.fname.indexOf(self.query) >= 0;
          if (!match) {
            // search shows the matches, full stop: dimming 7.7k overlapping
            // nodes turned the stage into paste (seen live 2026-07-16)
            out = Object.assign({}, out, { hidden: true });
          } else if (self._matches <= 40) {
            out = Object.assign({}, out, { forceLabel: true });
          }
        }
        if (self.sel === node) {
          out = Object.assign({}, out, { highlighted: true });
        }
        return out;
      }
    });
    this.r = renderer;

    /* interactions: click -> dossier; double-click stage -> fit; drag node */
    renderer.on("clickNode", function (e) {
      var a = self.g.getNodeAttributes(e.node);
      self.setSelected(e.node);
      self._onSelect({ id: e.node, name: a.rawname || a.label });
    });
    renderer.on("clickStage", function () { self.setSelected(null); });
    renderer.on("doubleClickStage", function (e) {
      if (e && e.preventSigmaDefault) { e.preventSigmaDefault(); }
      self.fit();
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

    /* live theme: recolor baked attributes + labels, single refresh */
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      var onTheme = function () {
        self.pal = readPalette();
        renderer.setSetting("labelColor", { color: self.pal.ink });
        self.g.forEachNode(function (n, a) {
          self.g.setNodeAttribute(n, "color", nodeColor(a.t, a.deg));
        });
        self.g.forEachEdge(function (ed, a) {
          self.g.setEdgeAttribute(ed, "color",
            a.grounded ? self.pal.edge : self.pal.edgeUn);
        });
        renderer.refresh();
      };
      if (mq.addEventListener) { mq.addEventListener("change", onTheme); }
    }
  }

  /* ---- load: the WHOLE store ---------------------------------------------
     Seed = degree-sorted phyllotaxis (hubs central, dust outer) so FA2 starts
     near its destiny; isolated nodes seed on an outer ring — with plain (non
     strong-gravity) FA2 they stay a quiet belt instead of flooding the core. */
  VerimemGraph.prototype.load = function (data) {
    var g = this.g, i;
    this.stopLayout();
    g.clear();
    this.hot.clear();
    var n = data.n || [], e = data.e || [];

    var deg = new Array(n.length).fill(0);
    for (i = 0; i < e.length; i++) { deg[e[i][0]]++; deg[e[i][1]]++; }

    var order = n.map(function (_, ix) { return ix; })
      .sort(function (a, b) { return deg[b] - deg[a]; });
    var nCon = 0;
    for (i = 0; i < order.length; i++) { if (deg[order[i]] > 0) { nCon++; } }
    var GA = Math.PI * (3 - Math.sqrt(5)),
        STEP = 24,
        RCON = Math.sqrt(Math.max(nCon, 1)) * STEP,   // connected disc radius
        nIso = order.length - nCon,
        rank = 0, iso = 0;
    for (i = 0; i < order.length; i++) {
      var ix = order[i], row = n[ix], d = deg[ix], x, y, th;
      if (d > 0) {
        th = rank * GA;
        var rr = STEP * Math.sqrt(rank + 0.5);
        x = Math.cos(th) * rr; y = Math.sin(th) * rr;
        rank++;
      } else {                                // the belt: real, quiet, outside
        th = iso * GA * 1.618;
        var br = RCON * 1.25 + STEP * 2 * (((iso / Math.max(nIso, 1)) * 6) | 0);
        x = Math.cos(th) * br; y = Math.sin(th) * br;
        iso++;
      }
      var name = String(row[1] == null ? row[0] : row[1]);
      g.addNode(row[0], {
        label: name.length > 30 ? name.slice(0, 29) + "…" : name,
        rawname: name, fname: name.toLowerCase(),
        t: row[2] || "", deg: d,
        size: d === 0 ? 1.6 : Math.min(2 + Math.log2(1 + d) * 1.35, 13),
        color: this._nodeColor(row[2] || "", d),
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
          grounded: grounded, size: 0.6,
          color: grounded ? this.pal.edge : this.pal.edgeUn
        });
      }
    }
    this.r.setCustomBBox(null);
    this.r.refresh();
    this.layout(nCon > 3000 ? 26000 : 9000);
    this.fit();
    return { nodes: g.order, edges: g.size };
  };

  /* ---- FA2 in a worker ----------------------------------------------------
     sigma computes the scene extent ONCE (first render): while the layout
     expands the graph past it, nodes would leave the stage. The follow
     timer re-bakes the bbox as the layout breathes; stopLayout() seals the
     final extent and re-fits the camera. */
  VerimemGraph.prototype._followBBox = function () {
    try { this.r.setCustomBBox(this.r.getBBox()); }
    catch (e) { /* renderer mid-teardown */ }
  };
  VerimemGraph.prototype.layout = function (ms, quiet) {
    var self = this, lib = window.graphologyLibrary;
    this.stopLayout();
    if (this.g.order < 2) { return; }
    var settings = lib.layoutForceAtlas2.inferSettings(this.g);
    settings.strongGravityMode = false;   // belt stays a belt (see load())
    settings.gravity = 0.06;
    // hubs share their attraction with their degree (LinLog-ish): the dense
    // co-occurrence core breathes into clusters instead of one solid ball
    settings.outboundAttractionDistribution = true;
    settings.scalingRatio = (settings.scalingRatio || 10) * 1.8;
    this._quiet = !!quiet;   // live kick: never yank the viewer's camera
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
      if (!this._quiet) { this._followBBox(); this.fit(); }
      this._onLayout(false);
    }
  };
  VerimemGraph.prototype.layoutRunning = function () {
    return !!(this._fa2 && this._fa2.isRunning && this._fa2.isRunning());
  };

  /* ---- LIVE: birth without refetch -----------------------------------------
     flow.entity gives us everything: created [{id,name,type}] + touched (the
     fact's full entity list = its co-occurrence clique, capped at 8 by the
     engine). New nodes spawn beside their clique-mates; edges merge in. */
  VerimemGraph.prototype.addLive = function (created, touched) {
    var g = this.g, self = this, added = 0, i, j;
    (created || []).forEach(function (c) {
      if (!c || !c.id || g.hasNode(c.id)) { return; }
      var sx = 0, sy = 0, k = 0;
      (touched || []).forEach(function (tid) {
        if (tid !== c.id && g.hasNode(tid)) {
          sx += g.getNodeAttribute(tid, "x");
          sy += g.getNodeAttribute(tid, "y"); k++;
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
        t: c.type || "", deg: 0, size: 1.6,
        color: self._nodeColor(c.type || "", 0), x: x, y: y
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
                    { grounded: 1, size: 0.6, color: this.pal.edge });
        }
      }
    }
    // re-bake degree-driven looks for the clique that just changed
    head.forEach(function (id) {
      var d = g.degree(id);
      g.mergeNodeAttributes(id, {
        deg: d,
        size: d === 0 ? 1.6 : Math.min(2 + Math.log2(1 + d) * 1.35, 13),
        color: self._nodeColor(g.getNodeAttribute(id, "t"), d)
      });
    });
    if (added && !this.layoutRunning()) { this.layout(1500, true); }
    return added;
  };

  /* ---- pulse: a node the engine just used ----------------------------------
     Driven by a rAF loop that runs ONLY while something is hot (idle = 0 CPU);
     the decay curve lives in the nodeReducer. */
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
    if (this.hot.size && !this._pulseRaf) {
      var step = function () {
        self.r.refresh();
        if (self.hot.size) { self._pulseRaf = requestAnimationFrame(step); }
        else { self._pulseRaf = null; }
      };
      this._pulseRaf = requestAnimationFrame(step);
    }
  };

  /* ---- search / camera / selection -----------------------------------------*/
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
      // moderate zoom: 0.05 dove the camera INTO the dense core and the
      // stage became unreadable — keep the neighborhood in frame instead
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
    if (this._pulseRaf) { cancelAnimationFrame(this._pulseRaf); }
    this.r.kill();
  };

  window.VerimemGraph = VerimemGraph;
})();
