"""H3 — `as_of` E lo SCOPE insieme: il taglio nell'ordine sbagliato perde fatti.

    python docs/stato-reale/banchi/m3-as-of-e-scope-insieme.py

Il difetto l'ha trovato @ws1 Marie il 04/09 LEGGENDO il codice, non eseguendolo:
in `hippo_facts_recall` il taglio `hits = _tenuti[:k]` avveniva PRIMA del filtro
di scope, mentre nella porta gemella `hippo_facts_search` lo scope viene prima.
`_recall_k = _scoped_fetch_limit(...)` pesca di piu' PROPRIO perche' lo scope
filtrera' dopo: tagliare a `k` prima butta candidati che allo scope sarebbero
sopravvissuti.

⚠️ IL BANCO DELL'AUTORE NON POTEVA VEDERLO: `m3-as-of-sulla-porta-ordinaria.py`
prova `as_of` SENZA scope. Un difetto che nasce nella COMBINAZIONE di due
opzioni non si vede esercitandone una sola — ed e' la ragione per cui la
falsificazione la fa qualcun altro.

PERCHE' `agent_id` E NON `user_id` — ed e' la ragione per cui la mia prima
stesura di questo banco NON DISCRIMINAVA (verde anche col difetto rimesso,
04/09 21:58). La QA l'ha eseguito su tutte e tre le dimensioni:

    scope      SENZA as_of   CON as_of   as_of_scartati
    user_id            2           2              0      non perde
    agent_id           2           0              0      PERDE TUTTO
    run_id             2           0              0      PERDE TUTTO

`user_id` da solo produce un prefisso canonico LEADING, e la pesca e' gia'
ristretta al tenant nel DB: il taglio anticipato non ha nulla da buttare.
`agent_id`/`run_id` SENZA `user_id` non sono leading -> oversample +
post-filtro -> il taglio a `k` prima del post-filtro cancella tutto. Avevo
costruito il banco sull'unica dimensione PROTETTA: non era un problema di
ranking indovinato, era la dimensione sbagliata.

⚠️ E la perdita e' MUTA: `as_of_scartati` resta 0 mentre spariscono TUTTI i
risultati — tecnicamente onesto (nessuno scartato per il tempo) e illeggibile
per chi chiama, che sente dire «ho applicato as_of, non ho scartato niente,
non ho trovato niente».

COME ISOLA L'ORDINE DAL TEMPO: `as_of` e' messo un minuto NEL FUTURO, quando
tutti i fatti esistono gia'. Il filtro temporale non deve quindi togliere
NIENTE: se il numero cala, e' l'ordine delle operazioni, non il tempo.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time

_D = tempfile.mkdtemp(prefix="h3scope_")
os.environ["HIPPO_DATA_DIR"] = _D
for _a in ("ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
    os.environ.pop(_a, None)

#: `python docs/.../questo.py` mette in sys.path[0] la directory DELLO SCRIPT:
#: senza questa riga `import verimem` prende il pacchetto INSTALLATO, e in un
#: worktree si misura l'albero di qualcun altro (03/09: tre rossi falsi).
_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

import asyncio  # noqa: E402
import json  # noqa: E402

import verimem  # noqa: E402
from verimem import mcp_server  # noqa: E402
from verimem.scope import scoped_topic  # noqa: E402

_QUALE = pathlib.Path(verimem.__file__).resolve()
print(f"  verimem misurato: {_QUALE}")
if _ROOT not in _QUALE.parents:
    raise SystemExit(f"⛔ sto per misurare {_QUALE} invece del repo {_ROOT}.")

AGENTE = "atlas"   # <- agent_id, NON user_id: vedi il perche qui sotto
QUERY = "politica di rimborso dei clienti"
K = 2

#: fuori scope, e scritti per stare IN CIMA alla classifica: sono la query.
FUORI = [
    "La politica di rimborso dei clienti prevede quattordici giorni.",
    "La politica di rimborso dei clienti esclude i prodotti digitali.",
    "La politica di rimborso dei clienti richiede lo scontrino.",
    "La politica di rimborso dei clienti copre i resi difettosi.",
]
#: in scope, e piu' lontani dalla query: senza il difetto tornano lo stesso,
#: perche' la pesca e' ampia PROPRIO per lasciarli passare allo scope.
DENTRO = [
    "Il rimborso ai clienti di Atlas segue la regola dei quattordici giorni.",
    "Atlas gestisce i rimborsi con la stessa politica del negozio.",
]


async def chiama(nome: str, args: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    res = await mcp_server.server.request_handlers[CallToolRequest](
        CallToolRequest(method="tools/call",
                        params=CallToolRequestParams(name=nome, arguments=args)))
    p = res.root if hasattr(res, "root") else res
    t = next(c.text for c in p.content if hasattr(c, "text"))
    try:
        return json.loads(t)
    except Exception:  # noqa: BLE001
        return {"raw": t}


def quanti(r: dict) -> int:
    for chiave in ("items", "results", "facts", "hits"):
        v = r.get(chiave)
        if isinstance(v, list):
            return len(v)
    return -1


def main() -> int:
    ag = mcp_server._ag()
    assert "h3scope_" in str(ag.semantic.db_path), "non e' la dir temporanea"
    topic_dentro = scoped_topic("banco/h3", agent_id=AGENTE)
    print(f"  topic in scope: {topic_dentro}")

    from verimem.client import Memory
    _m = Memory()
    assert str(_m.semantic.db_path) == str(ag.semantic.db_path), (
        "SDK e MCP su due store diversi: il banco non misurerebbe niente")
    for t in FUORI:
        _m.add(t, topic="banco/h3")
    for t in DENTRO:
        _m.add(t, topic=topic_dentro)
    print(f"  scritti: {len(FUORI)} fuori scope · {len(DENTRO)} dentro")

    dopo = time.time() + 60   # tutti esistono gia': il tempo non deve togliere

    senza = asyncio.run(chiama("hippo_facts_recall", {
        "query": QUERY, "k": K, "agent_id": AGENTE}))
    con = asyncio.run(chiama("hippo_facts_recall", {
        "query": QUERY, "k": K, "agent_id": AGENTE, "as_of": dopo}))
    n_senza, n_con = quanti(senza), quanti(con)

    print()
    print(f"  CONTROLLO POSITIVO — con scope e SENZA as_of: {n_senza} fatti")
    print(f"  con scope e CON as_of (istante futuro)      : {n_con} fatti")
    print(f"  la risposta dichiara i filtri accesi da as_of?"
          f" include_superseded={con.get('include_superseded')}"
          f" deep={con.get('deep')}")

    if n_senza <= 0:
        print("\n  ⛔ CONTROLLO POSITIVO SPENTO: senza as_of non torna niente,")
        print("     quindi il confronto non dice nulla. Banco da riscrivere.")
        return 1
    if n_con < n_senza:
        print(f"\n  🔴 H3 CONFERMATA: con `as_of` si perdono {n_senza - n_con}")
        print("     fatti su cui il tempo non aveva nulla da dire — e' il")
        print("     taglio a k eseguito PRIMA del filtro di scope.")
        return 1
    print("\n  🟢 as_of e scope insieme non perdono fatti: il taglio avviene")
    print("     DOPO lo scope, come nella porta gemella facts_search.")
    if con.get("include_superseded") is None:
        print("  🟡 ma la risposta non dichiara i filtri che `as_of` accende.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
