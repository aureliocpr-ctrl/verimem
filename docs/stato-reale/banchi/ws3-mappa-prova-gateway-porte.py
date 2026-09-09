"""`gateway.py`, secondo blocco: **tutte le porte HTTP restanti**, più le
difese (limite del corpo, header di sicurezza, tetto di richieste, idempotenza,
piano di controllo admin).

Le domande che decidono, e ognuna si prova attaccando:
  · `_host_only` cita un bug corretto sull'IPv6 (`"[::1]"` diventava `"[:"` e il
    client loopback cadeva in 401): il controllo positivo è proprio `[::1]`;
  · il limite del corpo promette **413** su una richiesta troppo grande;
  · gli header di sicurezza sono promessi su **OGNI** risposta — anche sul 413;
  · `Idempotency-Key` promette che un secondo invio **non scriva un gemello**;
  · senza `admin_key` gli endpoint `/admin/*` **non devono esistere**;
  · il tetto di richieste promette **429 con Retry-After**.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-gw2-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from fastapi.testclient import TestClient  # noqa: E402

from verimem import gateway as GW  # noqa: E402

F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."

print("=== 1. _host_only: il bug dell'IPv6 che il docstring dichiara curato")
for grezzo in ("localhost:8000", "127.0.0.1:9000", "[::1]:8000", "[::1]",
               "esempio.it", None, ""):
    print(f"  {grezzo!r:20} -> {GW._host_only(grezzo)!r}")

print("\n=== 2. _gateway_min_relevance: il pavimento di astensione della porta")
os.environ.pop("ENGRAM_GATEWAY_MIN_RELEVANCE", None)
print("  senza variabile:", GW._gateway_min_relevance())
for v in ("auto", "0.75", "spazzatura", "-1"):
    os.environ["ENGRAM_GATEWAY_MIN_RELEVANCE"] = v
    print(f"  ={v!r:12} -> {GW._gateway_min_relevance()!r}")
os.environ.pop("ENGRAM_GATEWAY_MIN_RELEVANCE", None)

print("\n=== 3. _parse_flow_line: la riga del flusso e la privacy del tenant")
# la forma vera, LETTA (righe 511-514): il nome dell'evento sta in `name` e il
# tenant dentro `payload`. Con le mie chiavi inventate tornava None su tutto,
# compreso il caso che doveva passare: era il mio formato a essere sbagliato.
riga_mia = '{"name": "flow.recall", "payload": {"tenant": "acme"}, "n": 1}'
riga_altrui = '{"name": "flow.recall", "payload": {"tenant": "globex"}}'
riga_senza = '{"name": "flow.recall", "payload": {}}'
riga_non_flow = '{"name": "altro", "payload": {"tenant": "acme"}}'
for nome, r in (("mia", riga_mia), ("di un altro tenant", riga_altrui),
                ("senza tenant", riga_senza), ("non flow.*", riga_non_flow),
                ("non json", "{rotta")):
    print(f"  {nome:20} see_untenanted=False -> {str(GW._parse_flow_line(r, 'acme', False))[:60]}")
print("  senza tenant, see_untenanted=True ->",
      str(GW._parse_flow_line(riga_senza, "acme", True))[:60])

print("\n=== 4. quota: _quota_reserve / _quota_release (TOCTOU-safe)")
import threading  # noqa: E402

from verimem.gateway_plans import Plan  # noqa: E402

# un piano vero con tetto 3 (Plan.within_facts, gateway_plans.py:39)
piano = Plan(name="prova", max_facts=3, rate_limit_per_minute=None,
             max_document_bytes=1024)
pending: dict[str, int] = {}
lk = threading.Lock()
print("  tetto del piano: 3 fatti · fatti gia' presenti (count_fn): 1")
for i in range(5):
    ok = GW._quota_reserve(pending, lk, "acme", piano, lambda: 1)
    print(f"  prenotazione {i + 1}: {ok} · in volo: {dict(pending)}")
GW._quota_release(pending, lk, "acme", piano)
print("  dopo una release:", dict(pending))
print("  con un piano SENZA tetto (max_facts=None):",
      GW._quota_reserve(pending, lk, "altro",
                        Plan(name="illimitato", max_facts=None,
                             rate_limit_per_minute=None, max_document_bytes=1024),
                        lambda: 10_000))

print("\n" + "=" * 74)
print("LE PORTE, con TestClient")
print("=" * 74)
keys = GW.GatewayKeys(tmp / "k.db")
k = keys.create(tenant_id="acme", name="prova")
app = GW.create_app(data_dir=tmp, keys=keys, max_body_bytes=2048)
c = TestClient(app)
H = {"X-API-Key": k}

r = c.post("/v1/memories", json={"content": "Il canone del capannone 12 e' 5900 euro.",
                                 "source": F, "topic": "gw/x"}, headers=H)
fid = r.json().get("id")
print("POST /v1/memories ->", r.status_code, "| id", fid)

print("\n=== 5. gli header di sicurezza su OGNI risposta")
for percorso, kwargs in (("/v1/health", {}), ("/v1/search?q=canone", {"headers": H}),
                         ("/v1/search?q=x", {})):
    resp = c.get(percorso, **kwargs)
    interessanti = {kk: vv for kk, vv in resp.headers.items()
                    if kk.lower().startswith(("x-", "content-security", "referrer",
                                              "strict-transport", "permissions"))}
    print(f"  {percorso:26} {resp.status_code} -> {interessanti}")

print("\n=== 6. il limite del corpo: 413, e gli header ci sono lo stesso")
grande = c.post("/v1/memories", json={"content": "x" * 5000, "source": F}, headers=H)
print("  corpo da ~5 KB con max_body_bytes=2048 ->", grande.status_code)
print("  header di sicurezza anche sul rifiuto:",
      {kk: vv for kk, vv in grande.headers.items() if kk.lower().startswith("x-")})

print("\n=== 7. Idempotency-Key: due invii identici, una sola scrittura")
corpo = {"content": "La consegna del capannone 12 e' il 3 marzo.",
         "source": "Verbale: la consegna del capannone 12 e' il 3 marzo.",
         "topic": "gw/idem"}
h2 = dict(H)
h2["Idempotency-Key"] = "prova-123"
p1 = c.post("/v1/memories", json=corpo, headers=h2)
p2 = c.post("/v1/memories", json=corpo, headers=h2)
print("  primo  ->", p1.status_code, p1.json().get("id"))
print("  secondo->", p2.status_code, p2.json().get("id"))
print("  >>> stessa ricevuta (nessun gemello):", p1.json().get("id") == p2.json().get("id"))
conta = c.get("/v1/search", params={"q": "consegna capannone"}, headers=H).json()
print("  fatti serviti sul tema:", len(conta) if isinstance(conta, list)
      else len(conta.get("results", conta.get("hits", []))))

print("\n=== 8. le altre porte di lettura")
for percorso, params in (("/v1/quota", {}), ("/v1/usage", {}), ("/v1/stats", {}),
                         ("/v1/quarantine", {"limit": 5}), ("/v1/tiers", {}),
                         ("/v1/retirements", {"limit": 5}), ("/v1/graph", {}),
                         ("/v1/graph/full", {}), ("/v1/snapshot", {}),
                         ("/v1/explain", {"q": "canone"}),
                         ("/v1/correct", {"q": "canone"}),
                         ("/v1/memories/" + str(fid), {})):
    try:
        resp = c.get(percorso, params=params, headers=H)
        print(f"  {percorso:24} -> {resp.status_code} · {str(resp.json())[:90]}")
    except Exception as e:  # noqa: BLE001
        print(f"  {percorso:24} -> {type(e).__name__}: {str(e)[:70]}")

print("\n=== 9. answer senza llm (O4: niente LLM implicito)")
ans = c.get("/v1/answer", params={"q": "quanto costa il capannone 12?"}, headers=H)
print("  /v1/answer ->", ans.status_code, str(ans.json())[:140])

print("\n=== 10. restore / undo / delete")
print("  POST /v1/memories/<id>/restore ->",
      c.post(f"/v1/memories/{fid}/restore", headers=H).status_code)
print("  POST /v1/undo/<op inventato>   ->",
      c.post("/v1/undo/op-inesistente", headers=H).status_code)
print("  DELETE /v1/memories/<id>       ->",
      c.delete(f"/v1/memories/{fid}", headers=H).status_code)
print("  GET dello stesso id dopo       ->",
      c.get(f"/v1/memories/{fid}", headers=H).status_code)

print("\n=== 11. le pagine: /, /dashboard, /ui, un asset")
for p in ("/", "/dashboard", "/ui", "/ui/app.js", "/ui/non-esiste.js"):
    resp = c.get(p)
    print(f"  {p:20} -> {resp.status_code} · {resp.headers.get('content-type', '')[:40]}"
          f" · etag: {resp.headers.get('etag', '-')[:22]}")

print("\n=== 12. il piano di controllo admin: senza chiave NON deve esistere")
for p in ("/admin/tenants", "/admin/stats", "/admin/overview", "/admin/audit"):
    print(f"  {p:20} (app senza admin_key) -> {c.get(p).status_code}")
app2 = GW.create_app(data_dir=tmp / "due", keys=GW.GatewayKeys(tmp / "k2.db"),
                     admin_key="segreto")
c2 = TestClient(app2)
print("  con admin_key, senza header  ->", c2.get("/admin/stats").status_code)
print("  con admin_key, header giusto ->",
      c2.get("/admin/stats", headers={"X-Admin-Key": "segreto"}).status_code)
print("  con admin_key, header errato ->",
      c2.get("/admin/stats", headers={"X-Admin-Key": "sbagliato"}).status_code)
nuovo = c2.post("/admin/tenants", json={"tenant_id": "nuovo-cliente"},
                headers={"X-Admin-Key": "segreto"})
print("  POST /admin/tenants ->", nuovo.status_code, str(nuovo.json())[:100])

print("\n=== 13. il tetto di richieste: 429 con Retry-After")
app3 = GW.create_app(data_dir=tmp / "tre", keys=GW.GatewayKeys(tmp / "k3.db"),
                     rate_limit_per_minute=2)
k3 = GW.GatewayKeys(tmp / "k3.db").create(tenant_id="acme3")
c3 = TestClient(app3)
for i in range(4):
    resp = c3.get("/v1/search", params={"q": "x"}, headers={"X-API-Key": k3})
    print(f"  richiesta {i + 1}: {resp.status_code}"
          f" · Retry-After: {resp.headers.get('retry-after', '-')}")
print("  /v1/health non e' mai limitato ->", c3.get("/v1/health").status_code)
