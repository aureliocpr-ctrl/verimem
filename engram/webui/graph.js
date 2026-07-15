/* VERIMEM — the REAL graph: every entity, every edge, live.
 *
 * Why this file exists (Aurelio, 2026-07-15): "sto grafo reale con tutte le
 * entità ed archi lo facciamo? io vedo che tutti lo hanno ed è super
 * performante". The old map drew SVG with an O(n²) force loop, so it could
 * only ever afford a 300-node sample — and that sample was the OLDEST 0.76%
 * of the store: a fossil. The store is 7753 nodes / 78 725 edges.
 *
 * What everyone else does, and what this does:
 *   - CANVAS, not SVG. 7753 SVG groups = 7753 DOM nodes = death. One canvas,
 *     one path for all edges, batched arcs for nodes.
 *   - BARNES-HUT quadtree: repulsion in O(n log n) instead of O(n²) —
 *     60M ops/frame becomes ~100k. This is the whole difference.
 *   - The layout SETTLES and then the canvas is static: 0 CPU at rest, and
 *     redraws only on pan/zoom/live-event.
 *   - Viewport culling + label LOD: you never pay for what is off-screen or
 *     too small to read.
 *
 * No dependencies, no CDN: the gateway's CSP is script-src 'self', and a
 * trust product does not pull a graph library from someone else's server.
 */
(function (global) {
  "use strict";

  var REDUCED = global.matchMedia
    && global.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- Barnes-Hut quadtree ------------------------------------------------
   * A node far away is approximated by the centre of mass of its whole
   * quadrant (θ criterion). That is what turns n² into n log n. */
  //: Hard depth ceiling. Bodies at (nearly) the same coordinates — and
  //: co-occurring entities DO land on top of each other — make a quadtree
  //: subdivide forever chasing a separation that never comes: measured as
  //: "Maximum call stack size exceeded" on the real graph, thrown inside
  //: requestAnimationFrame where nobody sees it, leaving a blank canvas.
  //: Below this depth a quadrant stops splitting and just accumulates mass:
  //: 2^22 of spread is far more resolution than any layout needs, and the
  //: recursion is now bounded BY CONSTRUCTION rather than by hoping the
  //: geometry cooperates.
  var MAX_DEPTH = 22;

  function Quad(x0, y0, x1, y1, depth) {
    this.x0 = x0; this.y0 = y0; this.x1 = x1; this.y1 = y1;
    this.depth = depth || 0;
    this.cx = 0; this.cy = 0; this.mass = 0;
    this.leaf = true; this.body = null; this.kids = null;
  }
  Quad.prototype.insert = function (p) {
    if (!isFinite(p.x) || !isFinite(p.y)) { return; }
    if (this.mass === 0) { this.body = p; this.mass = 1; this.cx = p.x; this.cy = p.y; return; }
    if (this.leaf) {
      if (this.depth >= MAX_DEPTH) {        // floor: pile up, never split
        this.cx = (this.cx * this.mass + p.x) / (this.mass + 1);
        this.cy = (this.cy * this.mass + p.y) / (this.mass + 1);
        this.mass += 1;
        return;
      }
      var b = this.body;
      this.split();
      this.push(b);
      this.body = null; this.leaf = false;
    }
    this.push(p);
    this.cx = (this.cx * this.mass + p.x) / (this.mass + 1);
    this.cy = (this.cy * this.mass + p.y) / (this.mass + 1);
    this.mass += 1;
  };
  Quad.prototype.split = function () {
    var mx = (this.x0 + this.x1) / 2, my = (this.y0 + this.y1) / 2, d = this.depth + 1;
    this.kids = [new Quad(this.x0, this.y0, mx, my, d), new Quad(mx, this.y0, this.x1, my, d),
                 new Quad(this.x0, my, mx, this.y1, d), new Quad(mx, my, this.x1, this.y1, d)];
    this.leaf = false;
  };
  Quad.prototype.push = function (p) {
    if (!this.kids) { this.split(); }
    var mx = (this.x0 + this.x1) / 2, my = (this.y0 + this.y1) / 2;
    var i = (p.x >= mx ? 1 : 0) + (p.y >= my ? 2 : 0);
    this.kids[i].insert(p);
  };
  Quad.prototype.force = function (p, theta, k2, out) {
    if (this.mass === 0 || this.body === p) { return; }
    var dx = p.x - this.cx, dy = p.y - this.cy;
    var d2 = dx * dx + dy * dy;
    if (d2 < 1e-6) { d2 = 1e-6; dx = (Math.random() - 0.5) * 0.01; dy = (Math.random() - 0.5) * 0.01; }
    var w = this.x1 - this.x0;
    if (this.leaf || (w * w) / d2 < theta * theta) {
      var f = (k2 * this.mass) / d2;          // repulsion ~ k²·m / d²
      out.x += dx * f; out.y += dy * f;
      return;
    }
    for (var i = 0; i < 4; i++) { this.kids[i].force(p, theta, k2, out); }
  };

  /* ---- the graph ---------------------------------------------------------*/
  function Graph(canvas, opts) {
    this.cv = canvas;
    this.ctx = canvas.getContext("2d", { alpha: true });
    this.opts = opts || {};
    this.nodes = []; this.edges = [];
    this.view = { x: 0, y: 0, s: 1 };
    this.running = false; this.alpha = 0;
    this.fired = {};                      // id -> t0 of the live pulse
    this.sel = null; this.hover = null; this.query = "";
    this._bind();
  }

  Graph.prototype.load = function (data) {
    var n = data.n || [], e = data.e || [];
    var deg = new Int32Array(n.length);
    for (var i = 0; i < e.length; i++) { deg[e[i][0]]++; deg[e[i][1]]++; }
    // Seed on a phyllotaxis spiral: uniform, no symmetry for the force to
    // fight (a ring seed leaves detached nodes parked on the ring forever).
    // R scales with sqrt(n) — the layout needs AREA per node, and 7753 nodes
    // squeezed into a small field can only ever be an even cloud.
    var R = Math.sqrt(n.length) * 34;
    this.nodes = n.map(function (row, i) {
      var a = i * 2.399963;                 // golden angle
      var r = R * Math.sqrt(i / Math.max(1, n.length));
      // the tiny jitter guarantees no two nodes share a coordinate — the
      // quadtree has a floor now, but a degenerate seed is still a bad seed
      return { id: row[0], name: row[1], type: row[2] || "", deg: deg[i],
               x: Math.cos(a) * r + (Math.random() - 0.5) * 0.5,
               y: Math.sin(a) * r + (Math.random() - 0.5) * 0.5,
               vx: 0, vy: 0, idx: i, born: 0 };
    });
    this.edges = e;
    this.byId = {};
    for (var j = 0; j < this.nodes.length; j++) { this.byId[this.nodes[j].id] = this.nodes[j]; }
    // hub threshold: only the top ~14 by degree keep a permanent label,
    // otherwise 7753 names collide into mush
    var ds = Array.prototype.slice.call(deg).sort(function (a, b) { return b - a; });
    this.hubMin = ds.length > 30 ? Math.max(2, ds[Math.min(13, ds.length - 1)] + 1) : 1;
    this.total = { entities: data.total_entities || n.length,
                   edges: data.total_edges || e.length,
                   truncated: !!data.truncated };
    // K = the rest length of an edge = the natural distance between two
    // related nodes. Derived from the seeded area so that repulsion and
    // springs are balanced at ANY store size (the old constant was tuned for
    // 300 nodes and made 7753 collapse into fog).
    this.K = Math.max(18, (2 * R) / Math.sqrt(Math.max(1, n.length)) * 2.2);
    // WARM UP before the first paint: fitting the seed spiral and letting the
    // viewer watch 7753 nodes untangle from a dot is not a graph, it's a
    // loading screen. ~120 Barnes-Hut passes settle the shape in well under a
    // second; then we fit what the layout actually IS.
    // The layout is computed FRAME BY FRAME, not in one blocking burst: 120
    // Barnes-Hut passes over 7753 nodes took 4.6 s of frozen tab. Now you
    // watch it organise itself (and the view keeps re-fitting while it does),
    // which is both honest and what every good graph tool shows you.
    this.settling = true;
    this.fit();
    this.reheat(1);
    return this.total;
  };

  Graph.prototype.step = function () {
    var ns = this.nodes, i, n;
    if (!ns.length) { return; }
    var minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    for (i = 0; i < ns.length; i++) {
      n = ns[i];
      if (n.x < minx) { minx = n.x; } if (n.x > maxx) { maxx = n.x; }
      if (n.y < miny) { miny = n.y; } if (n.y > maxy) { maxy = n.y; }
    }
    var pad = 10;
    var q = new Quad(minx - pad, miny - pad, maxx + pad, maxy + pad);
    for (i = 0; i < ns.length; i++) { q.insert(ns[i]); }

    // SPEED LIMIT (the "temperature" of Fruchterman-Reingold). Barnes-Hut
    // repulsion is k²·mass/d², and at the root that mass is every node in the
    // store: without a cap a few nodes reach escape velocity in one pass —
    // measured on the real graph, x ran to 631 000 058 while the median sat
    // at 46, so `fit` zoomed to 0.02 and the whole map vanished into a dot.
    // No node may cross more than one K per pass.
    var k2 = this.K * this.K, out = { x: 0, y: 0 };
    var vmax = this.K, vmax2 = vmax * vmax;
    for (i = 0; i < ns.length; i++) {
      n = ns[i];
      out.x = 0; out.y = 0;
      q.force(n, 0.9, k2, out);            // repulsion, O(log n) per node
      n.vx = (n.vx + out.x * 0.02 * this.alpha) * 0.82;
      n.vy = (n.vy + out.y * 0.02 * this.alpha) * 0.82;
      n.vx -= n.x * 0.0015 * this.alpha;   // gravity toward origin
      n.vy -= n.y * 0.0015 * this.alpha;
    }
    // springs, O(m). Strong enough to actually PULL clusters together —
    // with repulsion this wide, a timid spring leaves an even cloud where a
    // graph should have lumps. Damped by degree so a 97-edge hub doesn't
    // drag the whole map onto itself.
    var es = this.edges, K = this.K;
    for (i = 0; i < es.length; i++) {
      var a = ns[es[i][0]], b = ns[es[i][1]];
      if (!a || !b) { continue; }
      var dx = b.x - a.x, dy = b.y - a.y;
      var d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      var f = (d - K) * 0.09 * this.alpha
              / (1 + Math.log(1 + Math.min(a.deg, b.deg)));
      var ux = dx / d * f, uy = dy / d * f;
      a.vx += ux; a.vy += uy; b.vx -= ux; b.vy -= uy;
    }
    // integrate — and clamp HERE, after every force has had its say. Capping
    // before the springs (as I first did) is no cap at all: each edge then
    // adds velocity uncontested, a 97-edge hub accumulates 97 pushes, and
    // the layout blows up — measured, x reached 1e32 while the median sat at
    // -111, so `fit` zoomed to 0.02 and the canvas rendered nothing.
    // No node crosses more than one K per pass. Ever.
    for (i = 0; i < ns.length; i++) {
      n = ns[i];
      if (n === this.drag) { n.vx = 0; n.vy = 0; continue; }
      var sv2 = n.vx * n.vx + n.vy * n.vy;
      if (!isFinite(sv2)) { n.vx = 0; n.vy = 0; continue; }
      if (sv2 > vmax2) {
        var sc = vmax / Math.sqrt(sv2);
        n.vx *= sc; n.vy *= sc;
      }
      n.x += n.vx; n.y += n.vy;
      if (!isFinite(n.x) || !isFinite(n.y)) {   // last line of defence
        n.x = (Math.random() - 0.5) * this.K * 10;
        n.y = (Math.random() - 0.5) * this.K * 10;
        n.vx = 0; n.vy = 0;
      }
    }
  };

  Graph.prototype.draw = function () {
    var ctx = this.ctx, cv = this.cv;
    var dpr = global.devicePixelRatio || 1;
    var W = cv.clientWidth, H = cv.clientHeight;
    if (cv.width !== W * dpr || cv.height !== H * dpr) {
      cv.width = W * dpr; cv.height = H * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    var v = this.view, s = v.s;
    var css = getComputedStyle(document.documentElement);
    var C = {
      edge: css.getPropertyValue("--graph-edge").trim() || "rgba(120,180,150,.22)",
      edgeUn: css.getPropertyValue("--graph-edge-un").trim() || "rgba(190,90,60,.22)",
      node: css.getPropertyValue("--graph-node").trim() || "#b9ae95",
      hub: css.getPropertyValue("--graph-hub").trim() || "#d8cdb4",
      iso: css.getPropertyValue("--graph-iso").trim() || "rgba(150,140,120,.45)",
      lit: css.getPropertyValue("--graph-lit").trim() || "#4C9E78",
      ink: css.getPropertyValue("--graph-ink").trim() || "#e6ede9",
      bg: css.getPropertyValue("--graph-bg").trim() || "#17140E"
    };
    function px(n) { return (n.x - v.x) * s + W / 2; }
    function py(n) { return (n.y - v.y) * s + H / 2; }

    // edges: two paths (grounded / ungrounded) — 78k lineTo in 2 strokes.
    // Opacity scales with DENSITY: 78 725 edges at the 0.3 alpha that suits a
    // 600-edge map paint a solid green slab. Ink is a budget — spread it over
    // however many lines there are, and the structure shows as tone instead
    // of a wall (this is what a dense graph looks like when it's honest).
    var ns = this.nodes, es = this.edges, i;
    if (s > 0.06) {
      var ink = Math.max(0.06, Math.min(0.5, 4200 / Math.max(1, es.length)));
      ctx.globalAlpha = ink;
      ctx.lineWidth = Math.max(0.5, 0.8 * Math.min(1.4, s));
      var g0 = new Path2D(), g1 = new Path2D();
      for (i = 0; i < es.length; i++) {
        var a = ns[es[i][0]], b = ns[es[i][1]];
        if (!a || !b) { continue; }
        var ax = px(a), ay = py(a), bx = px(b), by = py(b);
        if ((ax < 0 && bx < 0) || (ax > W && bx > W)
            || (ay < 0 && by < 0) || (ay > H && by > H)) { continue; }  // cull
        var p = es[i][2] ? g0 : g1;
        p.moveTo(ax, ay); p.lineTo(bx, by);
      }
      ctx.strokeStyle = C.edge; ctx.stroke(g0);
      ctx.strokeStyle = C.edgeUn; ctx.setLineDash([3, 3]); ctx.stroke(g1);
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    // nodes: batched by class, one path each
    var now = performance.now();
    var pNorm = new Path2D(), pHub = new Path2D(), pIso = new Path2D();
    var labels = [];
    for (i = 0; i < ns.length; i++) {
      var n = ns[i];
      var x = px(n), y = py(n);
      if (x < -20 || x > W + 20 || y < -20 || y > H + 20) { continue; }   // cull
      var r = (n.deg === 0 ? 1.6 : 2 + Math.min(6, Math.sqrt(n.deg) * 1.1)) * Math.max(.5, Math.min(1.6, s));
      var t = this.fired[n.id];
      if (t !== undefined) {
        var age = (now - t) / 1100;
        if (age >= 1) { delete this.fired[n.id]; }
        else {
          var pulse = Math.sin(age * Math.PI);
          ctx.beginPath();
          ctx.arc(x, y, r + 14 * pulse, 0, 6.283);
          ctx.strokeStyle = C.lit; ctx.lineWidth = 2 * (1 - age); ctx.stroke();
          ctx.beginPath(); ctx.arc(x, y, r * (1 + pulse), 0, 6.283);
          ctx.fillStyle = C.lit; ctx.fill();
          if (s > 0.25) { labels.push([n, x, y, r, true]); }
          continue;
        }
      }
      var p = n.deg === 0 ? pIso : (n.deg >= this.hubMin ? pHub : pNorm);
      p.moveTo(x + r, y); p.arc(x, y, r, 0, 6.283);
      var lit = this.sel === n.id || this.hover === n.id
        || (this.query && n.name.toLowerCase().indexOf(this.query) >= 0);
      if (lit || (n.deg >= this.hubMin && s > 0.5) || s > 1.9) {
        labels.push([n, x, y, r, lit]);
      }
    }
    ctx.fillStyle = C.iso; ctx.fill(pIso);
    ctx.fillStyle = C.node; ctx.fill(pNorm);
    ctx.fillStyle = C.hub; ctx.fill(pHub);

    if (labels.length && labels.length < 400) {
      ctx.font = "11px ui-monospace, 'IBM Plex Mono', Consolas, monospace";
      ctx.textBaseline = "middle";
      ctx.lineWidth = 3; ctx.strokeStyle = C.bg;
      for (i = 0; i < labels.length; i++) {
        var L = labels[i];
        ctx.globalAlpha = L[4] ? 1 : 0.85;
        ctx.strokeText(L[0].name, L[1] + L[3] + 4, L[2]);
        ctx.fillStyle = L[4] ? C.lit : C.ink;
        ctx.fillText(L[0].name, L[1] + L[3] + 4, L[2]);
      }
      ctx.globalAlpha = 1;
    }
  };

  Graph.prototype.loop = function () {
    var self = this;
    if (this.running) { return; }
    this.running = true;
    function frame() {
      var busy = self.alpha > 0.008 && !document.hidden;
      if (busy) {
        // several passes per frame while settling: the layout converges in a
        // couple of seconds of ANIMATION instead of one frozen burst
        var passes = self.settling ? 3 : 1;
        for (var i = 0; i < passes; i++) { self.step(); self.alpha *= 0.99; }
        if (self.settling) {
          self.fit();                        // follow the shape as it opens
          if (self.alpha < 0.35) { self.settling = false; }
        }
      }
      self.draw();
      var pulsing = Object.keys(self.fired).length > 0;
      if (busy || pulsing || self.dirty) {
        self.dirty = false;
        requestAnimationFrame(frame);
      } else { self.running = false; }        // settled: 0 CPU at rest
    }
    requestAnimationFrame(frame);
  };
  Graph.prototype.reheat = function (a) {
    this.alpha = Math.max(this.alpha, a === undefined ? 0.9 : a);
    if (REDUCED) {                             // settle without animating
      for (var i = 0; i < 260; i++) { this.step(); this.alpha *= 0.985; }
      this.alpha = 0;
    }
    this.loop();
  };
  Graph.prototype.touch = function (ids) {     // live: the engine fired these
    var t = performance.now(), hit = 0;
    for (var i = 0; i < ids.length; i++) {
      if (this.byId[ids[i]]) { this.fired[ids[i]] = t; hit++; }
    }
    if (hit) { this.dirty = true; this.loop(); }
    return hit;
  };
  Graph.prototype.fit = function () {
    var ns = this.nodes;
    if (!ns.length) { return; }
    var minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    for (var i = 0; i < ns.length; i++) {
      var n = ns[i];
      if (n.x < minx) { minx = n.x; } if (n.x > maxx) { maxx = n.x; }
      if (n.y < miny) { miny = n.y; } if (n.y > maxy) { maxy = n.y; }
    }
    var W = this.cv.clientWidth || 800, H = this.cv.clientHeight || 520;
    this.view.x = (minx + maxx) / 2; this.view.y = (miny + maxy) / 2;
    var sx = W / Math.max(1, maxx - minx + 60), sy = H / Math.max(1, maxy - miny + 60);
    this.view.s = Math.max(0.02, Math.min(sx, sy, 2));
    this.dirty = true; this.loop();
  };
  Graph.prototype.at = function (mx, my) {
    var v = this.view, s = v.s;
    var W = this.cv.clientWidth, H = this.cv.clientHeight;
    var best = null, bd = 18 * 18;
    for (var i = 0; i < this.nodes.length; i++) {
      var n = this.nodes[i];
      var dx = (n.x - v.x) * s + W / 2 - mx, dy = (n.y - v.y) * s + H / 2 - my;
      var d = dx * dx + dy * dy;
      if (d < bd) { bd = d; best = n; }
    }
    return best;
  };
  Graph.prototype._bind = function () {
    var self = this, cv = this.cv, drag = null, pan = null;
    cv.addEventListener("pointerdown", function (ev) {
      var n = self.at(ev.offsetX, ev.offsetY);
      if (n) { drag = n; self.drag = n; }
      else { pan = { x: ev.offsetX, y: ev.offsetY, vx: self.view.x, vy: self.view.y }; }
      cv.setPointerCapture(ev.pointerId);
    });
    cv.addEventListener("pointermove", function (ev) {
      if (drag) {
        drag.x = self.view.x + (ev.offsetX - cv.clientWidth / 2) / self.view.s;
        drag.y = self.view.y + (ev.offsetY - cv.clientHeight / 2) / self.view.s;
        drag.vx = 0; drag.vy = 0; self.reheat(0.35); return;
      }
      if (pan) {
        self.view.x = pan.vx - (ev.offsetX - pan.x) / self.view.s;
        self.view.y = pan.vy - (ev.offsetY - pan.y) / self.view.s;
        self.dirty = true; self.loop(); return;
      }
      var h = self.at(ev.offsetX, ev.offsetY);
      var id = h ? h.id : null;
      if (id !== self.hover) { self.hover = id; self.dirty = true; self.loop(); }
      cv.style.cursor = h ? "pointer" : "grab";
    });
    cv.addEventListener("pointerup", function (ev) {
      if (drag && self.opts.onSelect) {
        var moved = false;
        self.sel = drag.id; self.opts.onSelect(drag);
      }
      drag = null; self.drag = null; pan = null;
      try { cv.releasePointerCapture(ev.pointerId); } catch (e) { /* ignore */ }
      self.dirty = true; self.loop();
    });
    cv.addEventListener("wheel", function (ev) {
      ev.preventDefault();
      var f = Math.exp(-ev.deltaY * 0.0016);
      var W = cv.clientWidth, H = cv.clientHeight;
      var wx = self.view.x + (ev.offsetX - W / 2) / self.view.s;
      var wy = self.view.y + (ev.offsetY - H / 2) / self.view.s;
      self.view.s = Math.max(0.02, Math.min(8, self.view.s * f));
      self.view.x = wx - (ev.offsetX - W / 2) / self.view.s;
      self.view.y = wy - (ev.offsetY - H / 2) / self.view.s;
      self.dirty = true; self.loop();
    }, { passive: false });
    cv.addEventListener("dblclick", function () { self.fit(); });
  };
  Graph.prototype.search = function (q) {
    this.query = (q || "").toLowerCase();
    this.dirty = true; this.loop();
    if (!this.query) { return 0; }
    var hits = this.nodes.filter(function (n) {
      return n.name.toLowerCase().indexOf(this.query) >= 0;
    }, this);
    if (hits.length) {                     // fly to the first hit
      this.view.x = hits[0].x; this.view.y = hits[0].y;
      this.view.s = Math.max(this.view.s, 1.2);
    }
    return hits.length;
  };

  global.VerimemGraph = Graph;
})(window);
