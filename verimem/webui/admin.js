/* Verimem org console — the SaaS/team view: one trust card per tenant.
 * Static file; data arrives only via authenticated fetch (X-Admin-Key from
 * sessionStorage). Every interpolated string passes esc(). */
(function () {
  "use strict";
  var STORE = "verimem_admin_key";
  var $ = function (id) { return document.getElementById(id); };
  var err = $("err"), board = $("board");

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;",
               '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fail(e) {
    board.hidden = true;
    err.textContent = e.message; err.hidden = false;
  }

  function ringSvg(led) {
    // Number(): counters are ints from OUR gateway, but nothing that ends
    // up in markup is trusted by type — coerce before concatenating
    var a = Number(led.admitted) || 0, q = Number(led.quarantined) || 0,
        r = Number(led.rejected) || 0;
    var tot = a + q + r, C = 2 * Math.PI * 26;
    if (!tot) {
      return '<svg viewBox="0 0 64 64" class="mini-ring">' +
        '<circle class="ring-track" cx="32" cy="32" r="26" ' +
        'style="stroke-width:6"></circle>' +
        '<text x="32" y="37" text-anchor="middle" class="mini-pct">—</text></svg>';
    }
    function arc(cls, from, frac) {
      return '<circle class="ring-arc ' + cls + '" cx="32" cy="32" r="26" ' +
        'style="stroke-width:6;stroke-dasharray:' + (frac * C) + " " + C +
        ';stroke-dashoffset:' + (-from * C) + ';transition:none"></circle>';
    }
    var fa = a / tot, fq = q / tot, fr = r / tot;
    return '<svg viewBox="0 0 64 64" class="mini-ring">' +
      '<circle class="ring-track" cx="32" cy="32" r="26" ' +
      'style="stroke-width:6"></circle>' +
      arc("arc-rejected", fa + fq, fr) +
      arc("arc-quarantined", fa, fq) +
      arc("arc-admitted", 0, fa) +
      '<text x="32" y="37" text-anchor="middle" class="mini-pct">' +
      Math.round(fa * 100) + "%</text></svg>";
  }

  function render(data) {
    board.hidden = false; err.hidden = true;
    var host = $("tenants");
    var ts = data.tenants || [];
    if (!ts.length) {
      host.innerHTML = '<p class="empty">No tenants yet — create one: ' +
        "<code>POST /admin/tenants</code>.</p>";
    } else {
      host.innerHTML = ts.map(function (t) {
        var led = t.ledger || {}, u = t.usage || {};
        return '<div class="card org-card">' +
          '<div class="org-ring">' + ringSvg(led) + "</div>" +
          '<div class="org-body"><div class="org-name">' + esc(t.tenant) +
          "</div>" +
          '<div class="org-nums">' +
          '<span class="ok">' + (Number(led.admitted) || 0) + " adm</span>" +
          '<span class="warn">' + (Number(led.quarantined) || 0) + " quar</span>" +
          '<span class="bad">' + (Number(led.rejected) || 0) + " rej</span>" +
          '<span class="dim">' + (Number(led.abstained) || 0) + " abst</span>" +
          "</div>" +
          '<div class="org-usage">' + (Number(u.requests) || 0) +
          " requests &middot; " + (Number(u.stored_ok) || 0) +
          " stored</div></div></div>";
      }).join("");
    }
    $("meta").textContent = data.n_tenants + " tenants - refreshed " +
      new Date().toLocaleTimeString() + " - auto-refresh 30s";
  }

  function load() {
    var k = sessionStorage.getItem(STORE);
    if (!k) { return; }
    fetch("/admin/overview", { headers: { "X-Admin-Key": k } })
      .then(function (r) {
        if (r.status === 401) {
          sessionStorage.removeItem(STORE);
          throw new Error("invalid admin key — paste it again");
        }
        if (!r.ok) { throw new Error("gateway error " + r.status); }
        return r.json();
      })
      .then(render).catch(fail);
  }

  $("keyform").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var v = $("key").value.trim();
    if (v) { sessionStorage.setItem(STORE, v); $("key").value = ""; load(); }
  });
  setInterval(load, 30000);
  load();
})();
