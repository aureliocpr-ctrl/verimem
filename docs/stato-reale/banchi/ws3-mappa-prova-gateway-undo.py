"""Un dettaglio del gateway che non voglio lasciare a metà: `POST /v1/undo/<op>`
con un id di operazione **inventato** ha risposto **200**. Un 200 su una cosa che
non esiste è la forma che fa credere a un chiamante di aver annullato qualcosa.

Guardo il CORPO: se dice `ok: false` è un 200 con esito negativo dentro
(discutibile ma onesto); se dice `ok: true` è un difetto vero.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

WT = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(WT))
tmp = pathlib.Path(tempfile.mkdtemp(prefix="ws3-undo-"))
os.environ["ENGRAM_DATA_DIR"] = str(tmp)
os.environ.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
from fastapi.testclient import TestClient  # noqa: E402

from verimem import gateway as GW  # noqa: E402

keys = GW.GatewayKeys(tmp / "k.db")
k = keys.create(tenant_id="acme")
c = TestClient(GW.create_app(data_dir=tmp, keys=keys))
H = {"X-API-Key": k}
F = "Verbale del 3 marzo: il canone del capannone 12 e' 5900 euro."

r = c.post("/v1/undo/op-che-non-esiste-mai", headers=H)
print("POST /v1/undo/<inventato> ->", r.status_code)
print("  corpo:", r.json())

a = c.post("/v1/memories", json={"content": "Il canone del capannone 12 e' 5900 euro.",
                                 "source": F, "topic": "u/x"}, headers=H).json()
b = c.post("/v1/memories", json={"content": "Il canone del capannone 12 e' 6100 euro.",
                                 "source": F, "topic": "u/x"}, headers=H).json()
print("\nscritture: primo", a.get("id"), a.get("status"),
      "· secondo", b.get("id"), b.get("status"))
op = b.get("undo_op_id") or (b.get("superseded_undo_ops") or [None])[0]
print("  maniglia undo nella ricevuta HTTP:", op)
if op:
    u = c.post(f"/v1/undo/{op}", headers=H)
    print("  POST /v1/undo/<vero> ->", u.status_code, u.json())
print("\n  >>> il 200 sull'inventato e il 200 sul vero si distinguono nel CORPO:",
      "ok" in r.json() or "error" in r.json())

print("\n=== T-MAP-8 ALLA PORTA HTTP: la seconda scrittura ha superseduto la prima?")
serviti = c.get("/v1/search", params={"q": "canone capannone 12"}, headers=H).json()
righe = serviti if isinstance(serviti, list) else serviti.get(
    "results", serviti.get("hits", []))
print("  fatti serviti dopo le due scritture:", len(righe))
for x in righe:
    print("   ", str(x.get("id"))[:12], x.get("status"), str(x.get("text"))[:44])
primo = c.get(f"/v1/memories/{a.get('id')}", headers=H).json()
print("  il primo fatto ora:", primo.get("status"),
      "| superseded_by:", primo.get("superseded_by"))
print("  chiavi della ricevuta HTTP della scrittura quarantinata:", sorted(b))
print("  >>> la maniglia di annullamento arriva alla porta HTTP:",
      any(kk in b for kk in ("undo_op_id", "superseded_undo_ops")))
