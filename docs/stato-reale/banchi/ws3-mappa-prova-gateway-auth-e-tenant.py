"""Mappa di `verimem/gateway.py`, primo blocco: **l'autenticazione e
l'isolamento fra tenant** — cioè i claim di sicurezza che l'intestazione del
modulo fa per iscritto:

  «auth API-key — chiavi vm_<40hex> generate server-side, mostrate UNA volta; a
   riposo solo lo sha256»
  «un DB per tenant … il tenant deriva SOLO dalla chiave presentata, mai da un
   campo della richiesta — niente path traversal, niente confused deputy»
  «stessa semantica dell'SDK — ogni write passa il gate anti-confab»
  «niente LLM implicito (O4) … senza, 400 onesto»

Un claim di sicurezza si prova ATTACCANDOLO, non rileggendolo: qui il tenant
sbagliato viene dichiarato nel corpo della richiesta, la chiave viene cercata in
chiaro dentro il database, e i nomi di tenant pericolosi vengono davvero
provati. Ogni controllo ha il caso che deve passare accanto a quello che deve
essere respinto: un rifiuto che rifiuta tutto non prova niente.
"""
import os
import pathlib
import sqlite3
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-gw-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402

FONTE = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."
keys = GatewayKeys(tmp / "gateway_keys.db")
k_acme = keys.create(tenant_id="acme", name="prova")
k_globex = keys.create(tenant_id="globex", name="prova")
app = create_app(data_dir=tmp, keys=keys)
c = TestClient(app)
print("chiave di acme:", k_acme[:6] + "…", "| lunghezza:", len(k_acme),
      "| prefisso vm_:", k_acme.startswith("vm_"))

print("\n=== 1. chi entra senza chiave")
print("  GET /v1/health  senza chiave ->", c.get("/v1/health").status_code,
      c.get("/v1/health").json())
r = c.get("/v1/search", params={"q": "canone"})
print("  GET /v1/search  senza chiave ->", r.status_code, str(r.json())[:70])
r = c.get("/v1/search", params={"q": "canone"}, headers={"X-API-Key": "vm_" + "0" * 40})
print("  GET /v1/search  chiave finta ->", r.status_code)
r = c.get("/v1/search", params={"q": "canone"}, headers={"X-API-Key": k_acme})
print("  GET /v1/search  chiave vera  ->", r.status_code)
r = c.get("/v1/search", params={"q": "canone"},
          headers={"Authorization": f"Bearer {k_acme}"})
print("  GET /v1/search  Bearer       ->", r.status_code)

print("\n=== 2. IL CLAIM: il tenant viene dalla CHIAVE, mai dal corpo")
r = c.post("/v1/memories",
           json={"content": "Il canone del capannone 12 e' 5900 euro.",
                 "source": FONTE, "topic": "gw/x", "tenant_id": "globex"},
           headers={"X-API-Key": k_acme})
print("  POST con chiave ACME e tenant_id='globex' nel corpo ->", r.status_code,
      {k: str(v)[:28] for k, v in list(r.json().items())[:4]})
ra = c.get("/v1/search", params={"q": "canone capannone"}, headers={"X-API-Key": k_acme})
rg = c.get("/v1/search", params={"q": "canone capannone"}, headers={"X-API-Key": k_globex})


def quanti(resp):
    d = resp.json()
    for campo in ("results", "hits", "memories", "facts"):
        if isinstance(d, dict) and campo in d:
            return len(d[campo])
    return len(d) if isinstance(d, list) else str(d)[:60]


print("  il fatto lo vede ACME  :", quanti(ra))
print("  il fatto lo vede GLOBEX:", quanti(rg))
print("  >>> l'isolamento regge:", quanti(ra) == 1 and quanti(rg) == 0)
db_acme = tmp / "tenants" / "acme" / "memory.db"
db_glob = tmp / "tenants" / "globex" / "memory.db"
print("  file per tenant:", db_acme.exists(), "|", db_glob.exists(),
      "| cartelle:", sorted(p.name for p in (tmp / "tenants").iterdir()))

print("\n=== 3. i nomi di tenant che NON devono nascere")
for cattivo in ("../evil", "acme.", "con", "ACME", "a" * 65, "acme/../x", ""):
    try:
        keys.create(tenant_id=cattivo)
        print(f"  {cattivo!r:12} -> CREATO (nessun rifiuto)")
    except Exception as e:  # noqa: BLE001
        print(f"  {cattivo!r:12} -> {type(e).__name__}: {str(e)[:64]}")
print("  (controllo positivo) 'acme-2' ->",
      "creato" if keys.create(tenant_id="acme-2").startswith("vm_") else "?")

print("\n=== 4. la chiave a riposo: c'e' il testo in chiaro nel database?")
grezzo = (tmp / "gateway_keys.db").read_bytes()
print("  la chiave in chiaro compare nei byte del db:", k_acme.encode() in grezzo)
con = sqlite3.connect(f"file:{tmp / 'gateway_keys.db'}?mode=ro", uri=True)
tab = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")]
print("  tabelle:", tab)
for t in tab:
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
    print(f"  colonne di {t}:", cols)
    riga = con.execute(f"SELECT * FROM {t} LIMIT 1").fetchone()  # noqa: S608
    if riga:
        print("  prima riga:", [str(x)[:34] for x in riga])
con.close()

print("\n=== 5. revoca")
elenco = keys.list()
kid = elenco[0].get("key_id") or elenco[0].get("id")
print("  revoke(", str(kid)[:12], ") ->", keys.revoke(kid))
print("  la chiave revocata ora ->",
      c.get("/v1/search", params={"q": "x"}, headers={"X-API-Key": k_acme}).status_code)
print("  l'altra chiave ->",
      c.get("/v1/search", params={"q": "x"}, headers={"X-API-Key": k_globex}).status_code)

print("\n=== 6. ogni write passa il GATE, come nell'SDK")
r = c.post("/v1/memories",
           json={"content": "Il canone del capannone 12 e' 7300 euro.",
                 "source": FONTE, "topic": "gw/ko"},
           headers={"X-API-Key": k_globex})
print("  confab ->", r.status_code, {k: str(v)[:40] for k, v in list(r.json().items())[:6]})

print("\n=== 7. niente LLM implicito (O4)")
r = c.post("/v1/memories",
           json={"messages": [{"role": "user", "content": "il canone e' 5900"}]},
           headers={"X-API-Key": k_globex})
print("  ingest conversazionale senza llm ->", r.status_code, str(r.json())[:150])

print("\n=== 8. corpo malformato: 400, mai 500 (un 500 su input costruito e' un DoS)")
for corpo in ({}, {"content": 123}, {"messages": "non una lista"},
              {"content": "x" * 10, "topic": {"a": 1}}):
    r = c.post("/v1/memories", json=corpo, headers={"X-API-Key": k_globex})
    print(f"  {str(corpo)[:38]:40} -> {r.status_code}")
