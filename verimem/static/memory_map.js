// Sigma + graphology + d3 are loaded as UMD globals by <script> tags in the
// page (see memory_map.py). This file is a CLASSIC script (no type="module"),
// so it MUST use those globals — an ES `import` at the top is a SyntaxError
// that silently kills the ENTIRE file -> blank graph (the dashboard-broken bug,
// 2026-06-06). graphology was already used as a global below; Sigma now too.
(function() {
  "use strict";

  window.onerror = function(msg, url, lineNo, columnNo, error) {
    const el = document.getElementById("sigma-container");
    if(el) el.innerHTML = "<div style='color:red;font-size:20px;padding:20px;background:black;z-index:9999;position:relative;'>ERROR: " + msg + "<br/>" + (error&&error.stack ? error.stack : "") + "</div>";
  };
  window.addEventListener("unhandledrejection", function(event) {
    const el = document.getElementById("sigma-container");
    if(el) el.innerHTML = "<div style='color:red;font-size:20px;padding:20px;background:black;z-index:9999;position:relative;'>PROMISE ERROR: " + event.reason + "</div>";
  });

  // Colors based on type
  const COLORS = {
    episode: "#3b82f6", // Blue
    fact: "#10b981",    // Green
    skill: "#f59e0b",   // Amber
    entity: "#8b5cf6",  // Purple
    contradiction: "#ef4444" // Red
  };

  const EDGE_COLORS = {
    parent_of: "rgba(255,255,255,0.25)",
    uses_skill: "rgba(245, 158, 11, 0.4)",
    source_episode: "rgba(16, 185, 129, 0.4)",
    superseded_by: "rgba(239, 68, 68, 0.6)",
    lineage_to: "rgba(255,255,255,0.15)",
    default: "rgba(255,255,255,0.1)"
  };

  // State
  let graph;
  let sigmaInstance;
  let hoveredNode = null;
  let hoveredNeighbors = new Set();
  let searchQuery = "";
  let layerFilters = {
    episode: true,
    fact: true,
    skill: true
  };
  let esSource = null;

  // DOM Elements
  const container = document.getElementById("sigma-container");
  const loadingEl = document.getElementById("mm-loading");
  const detailPanel = document.getElementById("mm-detail-panel");
  const detailContent = document.getElementById("mm-detail");
  const countsEl = document.getElementById("mm-counts");
  const searchInput = document.getElementById("mm-search");
  
  // Toggles
  const toggles = {
    episode: document.getElementById("mm-layer-episode"),
    fact: document.getElementById("mm-layer-fact"),
    skill: document.getElementById("mm-layer-skill")
  };

  function init() {
    graph = new graphology.Graph({ multi: true });
    loadData().then(() => {
        connectSSE();
    });
    bindEvents();
  }

  async function loadData() {
    try {
      loadingEl.style.display = "flex";
      // We can bump the limit since WebGL handles it like butter
      const res = await fetch("/api/memory-map/graph?limit=1500");
      if (!res.ok) throw new Error("Failed to load graph data");
      const data = await res.json();
      
      buildGraphology(data);
      initSigma();
      updateCounts(data);
      
      loadingEl.style.display = "none";
    } catch (err) {
      console.error(err);
      loadingEl.innerHTML = `<span>Error: ${err.message}</span>`;
    }
  }

  function buildGraphology(data) {
    graph.clear();
    
    // Add nodes
    data.nodes.forEach((n) => {
      // Circle layout initial state
      const angle = Math.random() * Math.PI * 2;
      const radius = 50 + Math.random() * 50;
      
      graph.addNode(n.id, {
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        size: 5, // Placeholder, updated later
        color: COLORS[n.type] || "#ffffff",
        label: n.label,
        // domain type stored as `kind` — Sigma v2 RESERVES `type` for the
        // render program (circle/image/...), so a domain `type:"skill"` made
        // it throw "could not find a suitable program for node type skill".
        kind: n.type,
        raw: n,
        hidden: false,
        highlighted: false
      });
    });

    // Add edges
    data.edges.forEach((e, idx) => {
      if (graph.hasNode(e.from) && graph.hasNode(e.to)) {
        try {
            graph.addEdge(e.from, e.to, {
                kind: e.type,
                color: EDGE_COLORS[e.type] || EDGE_COLORS.default,
                size: e.type === "superseded_by" ? 2 : 1
            });
        } catch (err) {
            // multi edge might conflict if graphology isn't multi:true, but we set it
        }
      }
    });

    // Degree-based sizing
    graph.forEachNode((node, attributes) => {
      const degree = graph.degree(node);
      // Min size 4, max size 24, scales logarithmically/sqrt
      const nodeSize = Math.max(4, Math.min(24, 4 + Math.sqrt(degree) * 1.5));
      graph.setNodeAttribute(node, "size", nodeSize);
      graph.setNodeAttribute(node, "originalSize", nodeSize);
    });
  }

  function initSigma() {
    if (sigmaInstance) {
      sigmaInstance.kill();
    }

    // Run D3 Force layout statically
    const nodesData = [];
    const nodeMap = new Map();
    
    graph.forEachNode((node, attrs) => {
        const d3Node = { id: node, x: attrs.x, y: attrs.y, radius: attrs.size };
        nodesData.push(d3Node);
        nodeMap.set(node, d3Node);
    });
    
    const linksData = [];
    graph.forEachEdge((edge, attrs, source, target) => {
        linksData.push({ source: source, target: target });
    });
    
    const simulation = d3.forceSimulation(nodesData)
        .force("link", d3.forceLink(linksData).id(d => d.id).distance(40))
        .force("charge", d3.forceManyBody().strength(-150))
        .force("center", d3.forceCenter(0, 0))
        .force("collision", d3.forceCollide().radius(d => d.radius + 10).iterations(2))
        .stop();
        
    for (let i = 0; i < 250; ++i) simulation.tick();
    
    nodesData.forEach(d => {
        graph.setNodeAttribute(d.id, "x", d.x);
        graph.setNodeAttribute(d.id, "y", d.y);
    });

    // sigma's UMD build may expose the class as `Sigma` (default) or as
    // `Sigma.Sigma` (namespace) depending on the bundle — handle both.
    const SigmaCtor = (typeof Sigma !== "undefined" && Sigma.Sigma) ? Sigma.Sigma : Sigma;
    sigmaInstance = new SigmaCtor(graph, container, {
      allowInvalidContainer: true,
      defaultNodeType: "circle",
      labelFont: "Inter, sans-serif",
      labelWeight: "500",
      labelColor: { color: "#e5e7eb" },
      labelSize: 11,
      minCameraRatio: 0.1,
      maxCameraRatio: 5,
      // Hover and filter reducers
      nodeReducer: (node, data) => {
        const res = { ...data };
        
        // Handle layer visibility (res.kind = domain type; see addNode)
        if (!layerFilters[res.kind]) {
          res.hidden = true;
        }

        // Handle search
        if (searchQuery && !res.label.toLowerCase().includes(searchQuery)) {
          res.color = "#333333";
          res.label = "";
        }

        // Handle hover
        if (hoveredNode) {
          if (node === hoveredNode || hoveredNeighbors.has(node)) {
            res.highlighted = true;
            if (node === hoveredNode) {
              res.size = data.originalSize * 1.3;
              res.zIndex = 1;
            }
          } else {
            res.color = "#22222b"; // Dimmed
            res.label = "";
          }
        }
        
        if (res.hidden) {
          res.color = "transparent";
          res.label = "";
        }
        
        return res;
      },
      edgeReducer: (edge, data) => {
        const res = { ...data };
        const ext = graph.extremities(edge);
        const node1 = ext[0];
        const node2 = ext[1];
        
        // Hide edge if either endpoint is hidden
        if (!layerFilters[graph.getNodeAttribute(node1, "kind")] ||
            !layerFilters[graph.getNodeAttribute(node2, "kind")]) {
            res.hidden = true;
            return res;
        }

        if (hoveredNode) {
          if (node1 === hoveredNode || node2 === hoveredNode) {
            res.size = data.size * 2;
            // Use solid color for highlighted edges
            res.color = data.color.replace(/[\d.]+\)$/g, '1)'); 
            res.zIndex = 1;
          } else {
            res.hidden = true;
          }
        }
        
        return res;
      }
    });

    // Bind Sigma events
    sigmaInstance.on("enterNode", (e) => {
      hoveredNode = e.node;
      hoveredNeighbors = new Set(graph.neighbors(hoveredNode));
      sigmaInstance.refresh();
      container.style.cursor = "pointer";
    });

    sigmaInstance.on("leaveNode", () => {
      hoveredNode = null;
      hoveredNeighbors.clear();
      sigmaInstance.refresh();
      container.style.cursor = "default";
    });

    sigmaInstance.on("clickNode", (e) => {
      const attrs = graph.getNodeAttributes(e.node);
      renderDetail(attrs.raw);
    });

    sigmaInstance.on("clickStage", () => {
      detailPanel.classList.remove("visible");
    });
    
    // Fit to screen
    sigmaInstance.getCamera().animatedReset({ duration: 600 });
  }

  function bindEvents() {
    document.getElementById("mm-reload").addEventListener("click", () => {
      detailPanel.classList.remove("visible");
      loadData();
    });

    document.getElementById("mm-fit").addEventListener("click", () => {
      if (sigmaInstance) {
          sigmaInstance.getCamera().animatedReset({ duration: 400 });
      }
    });

    searchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      if (sigmaInstance) sigmaInstance.refresh();
    });

    ["episode", "fact", "skill"].forEach(type => {
      toggles[type].addEventListener("change", (e) => {
        layerFilters[type] = e.target.checked;
        if (sigmaInstance) sigmaInstance.refresh();
      });
    });
  }

  function renderDetail(raw) {
    const color = COLORS[raw.type] || "#ffffff";
    const title = raw.label || raw.id;
    const typeLabel = raw.type.toUpperCase();
    
    let html = `
      <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
        <span style="background:${color}20; color:${color}; padding:4px 10px; border-radius:12px; font-size:10px; font-weight:700; border:1px solid ${color}40; letter-spacing: 0.5px;">${typeLabel}</span>
        <span style="font-family:var(--font-mono); font-size:12px; color:#9ca3af;">${raw.id}</span>
      </div>
      <h3 style="margin:0 0 16px 0; font-size:18px; font-weight:600; line-height:1.4;">${title}</h3>
      <hr>
    `;
    
    // Key-value attributes
    const skipFields = ["id", "type", "label"];
    let hasMeta = false;
    
    for (const [key, value] of Object.entries(raw)) {
      if (skipFields.includes(key)) continue;
      if (value === null || value === undefined || value === "") continue;
      
      hasMeta = true;
      let displayValue = value;
      if (typeof value === "boolean") displayValue = value ? "True" : "False";
      if (typeof value === "number" && !Number.isInteger(value)) displayValue = value.toFixed(2);
      
      html += `
        <div style="margin-bottom:12px; display:flex; flex-direction:column; gap:4px;">
          <span style="font-size:11px; color:#9ca3af; text-transform:uppercase; font-weight:600; letter-spacing: 0.5px;">${key.replace(/_/g, " ")}</span>
          <span style="font-size:14px; color:#f3f4f6; line-height: 1.5;">${displayValue}</span>
        </div>
      `;
    }
    
    if (!hasMeta) {
      html += `<div style="color:#6b7280; font-size:13px; font-style:italic;">No additional metadata.</div>`;
    }
    
    // Connectivity
    html += `<hr>`;
    html += `
      <div style="display:grid; grid-template-columns:1fr; gap:8px;">
        <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:10px; text-align:center; border: 1px solid rgba(255,255,255,0.05);">
          <div style="font-size:24px; font-weight:700; color:#fff;">${graph.degree(raw.id)}</div>
          <div style="font-size:11px; color:#9ca3af; text-transform:uppercase; font-weight:600; margin-top:4px;">Connections</div>
        </div>
      </div>
    `;

    detailContent.innerHTML = html;
    detailPanel.classList.add("visible");
  }

  function updateCounts(data) {
    const l = data.layers || {};
    countsEl.textContent = `${l.episode || 0} episodes · ${l.fact || 0} facts · ${l.skill || 0} skills · ${data.n_edges || 0} edges`;
  }
  
  // SSE Integration
  let lastEventTs = 0;
  function connectSSE() {
    if (esSource) {
      esSource.close();
    }
    const statusEl = document.getElementById("mm-status");
    esSource = new EventSource("/api/memory-map/events?since=" + lastEventTs);

    esSource.onopen = () => {
      statusEl.textContent = "● live";
      statusEl.style.color = "#3fb950";
      statusEl.style.background = "rgba(63, 185, 80, 0.1)";
      statusEl.style.borderColor = "rgba(63, 185, 80, 0.2)";
    };

    esSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.ts) lastEventTs = Math.max(lastEventTs, data.ts);
      
      // When events happen, we could pulse the node. 
      // For now, if we get an event, we could trigger a reload.
      // But auto-reload might disrupt the user.
      // So we just log or do a subtle UI indication.
    };

    esSource.onerror = () => {
      statusEl.textContent = "● reconnecting...";
      statusEl.style.color = "#f59e0b";
      statusEl.style.background = "rgba(245, 158, 11, 0.1)";
      statusEl.style.borderColor = "rgba(245, 158, 11, 0.2)";
      esSource.close();
      setTimeout(connectSSE, 3000);
    };
  }

  // Start
  init();

})();
