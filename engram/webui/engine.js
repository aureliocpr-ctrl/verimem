/* VERIMEM — LIVE ENGINE ROOM (/ui/engine).
   External script by CSP design (script-src 'self': no inline JS, no eval).
   Streams /v1/events/flow (authed fetch-streaming; bearer in a header +
   sessionStorage, never in a URL) and animates the custody line with the
   REAL events of this tenant. Payloads are flow metadata only. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var counters = { adm: 0, quar: 0, ans: 0, abs: 0 };
  var queue = [], playing = false, aborter = null;

  var KEY_SS = "verimem_api_key";
  $("key").value = sessionStorage.getItem(KEY_SS) || "";

  function setLive(on, tx) {
    $("live").classList.toggle("on", on);
    $("liveTx").textContent = tx;
  }
  function clearBench() {
    ["n-ingest", "n-l1", "n-l4", "n-query", "n-rec", "n-fl", "n-v"].forEach(function (id) {
      $(id).classList.remove("pass", "fail");
    });
    ["w-in-l1", "w-l1-l4", "w-l4-led", "w-l1-q", "w-l4-q", "w-q-rec", "w-rec-fl", "w-fl-v"]
      .forEach(function (id) { $(id).classList.remove("flow", "q"); });
    ["st-led", "st-q", "st-v"].forEach(function (id) {
      $(id).classList.remove("on", "adm", "ref", "ans", "abs");
    });
  }
  function play(evt) {
    clearBench();
    var p = evt.payload || {};
    if (evt.name === "flow.write") {
      $("n-ingest").classList.add("pass"); $("w-in-l1").classList.add("flow");
      // quarantined IS written to the ledger but excluded from recall → red branch
      var ok = p.stored && p.status !== "quarantined";
      if (ok) {
        $("n-l1").classList.add("pass"); $("w-l1-l4").classList.add("flow");
        $("n-l4").classList.add("pass"); $("w-l4-led").classList.add("flow");
        $("st-led").textContent = "ADMITTED"; $("st-led").classList.add("on", "adm");
        counters.adm++;
      } else {
        $("n-l1").classList.add("fail");
        $("w-l1-q").classList.add("flow", "q");
        $("st-q").textContent = (p.status || "REFUSED").toUpperCase();
        $("st-q").classList.add("on", "ref");
        counters.quar++;
      }
    } else if (evt.name === "flow.recall") {
      $("n-query").classList.add("pass"); $("w-q-rec").classList.add("flow");
      $("n-rec").classList.add("pass"); $("w-rec-fl").classList.add("flow");
      if (p.abstained) {
        $("n-fl").classList.add("fail");
        $("w-fl-v").classList.add("flow", "q");
        $("n-v").classList.add("fail");
        $("vSub").textContent = "honest silence";
        $("st-v").textContent = "ABSTAIN"; $("st-v").classList.add("on", "abs");
        counters.abs++;
      } else {
        $("n-fl").classList.add("pass");
        $("w-fl-v").classList.add("flow");
        $("n-v").classList.add("pass");
        $("vSub").textContent = "answer + provenance";
        $("st-v").textContent = "ANSWER"; $("st-v").classList.add("on", "ans");
        counters.ans++;
      }
    }
    $("cAdm").textContent = counters.adm; $("cQuar").textContent = counters.quar;
    $("cAns").textContent = counters.ans; $("cAbs").textContent = counters.abs;
  }
  function feed(evt) {
    var p = evt.payload || {};
    var d = new Date((evt.ts || 0) * 1000);
    var hh = ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2)
      + ":" + ("0" + d.getSeconds()).slice(-2);
    var row = document.createElement("div"); row.className = "evt";
    // build with createElement + textContent only — no innerHTML on event data
    var t = document.createElement("span"); t.className = "t"; t.textContent = hh;
    var tag = document.createElement("span");
    var detail;
    if (evt.name === "flow.write") {
      var ok = p.stored && p.status !== "quarantined";
      tag.className = ok ? "adm" : "ref";
      tag.textContent = ok ? "ADMITTED" : String(p.status || "refused").toUpperCase();
      detail = " · write · topic " + (p.topic || "—")
        + (p.fact_id ? " · id " + String(p.fact_id).slice(0, 8) : "");
    } else {
      tag.className = p.abstained ? "abs" : "ans";
      tag.textContent = p.abstained ? "ABSTAIN" : "ANSWER";
      detail = " · recall/" + (p.kind || "?") + " · n=" + (p.n != null ? p.n : "?")
        + (p.best != null ? " · best " + p.best : "");
    }
    row.appendChild(t); row.appendChild(document.createTextNode(" "));
    row.appendChild(tag); row.appendChild(document.createTextNode(detail));
    var f = $("feed"); f.insertBefore(row, f.firstChild);
    while (f.children.length > 40) f.removeChild(f.lastChild);
  }
  function pump() {
    if (playing) return;
    var evt = queue.shift();
    if (!evt) return;
    playing = true;
    play(evt); feed(evt);
    setTimeout(function () { playing = false; pump(); }, 900);
  }

  async function connect() {
    var key = $("key").value.trim();
    $("err").textContent = "";
    // personal mode (`verimem console`, loopback): no key needed — an empty
    // field connects as the local tenant; a 401 explains when one IS needed.
    if (key) sessionStorage.setItem(KEY_SS, key);
    if (aborter) aborter.abort();
    aborter = new AbortController();
    setLive(false, "connecting…");
    try {
      var hdrs = key ? { Authorization: "Bearer " + key } : {};
      var r = await fetch("/v1/events/flow?replay=20",
        { headers: hdrs, signal: aborter.signal });
      if (r.status === 401) { setLive(false, "disconnected"); $("err").textContent = key ? "401 — invalid key" : "401 — this gateway needs an API key (personal mode not active)"; return; }
      if (!r.ok || !r.body) { setLive(false, "disconnected"); $("err").textContent = "HTTP " + r.status; return; }
      setLive(true, "LIVE");
      var reader = r.body.getReader(), dec = new TextDecoder(), buf = "";
      for (;;) {
        var ch = await reader.read();
        if (ch.done) break;
        buf += dec.decode(ch.value, { stream: true });
        var idx;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          var chunk = buf.slice(0, idx); buf = buf.slice(idx + 2);
          if (chunk.indexOf("data: ") === 0) {
            try { queue.push(JSON.parse(chunk.slice(6))); pump(); } catch (e) { /* skip bad line */ }
          }
        }
      }
      setLive(false, "stream closed");
    } catch (e) {
      if (e.name !== "AbortError") { setLive(false, "disconnected"); $("err").textContent = String(e); }
    }
  }
  $("go").addEventListener("click", connect);
  $("key").addEventListener("keydown", function (e) { if (e.key === "Enter") connect(); });
})();
