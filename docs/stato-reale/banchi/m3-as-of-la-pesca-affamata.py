"""La pesca affamata: `as_of` NEL PASSATO, dove il banco di ieri era cieco.

    python docs/stato-reale/banchi/m3-as-of-la-pesca-affamata.py

REPERTO ① della QA, 04/09: «`hippo_facts_recall` con `as_of` da' 0 dove
`hippo_recall_as_of`, stesso istante e stesso k=5, da' 1». La causa e' nel
docstring del tool dedicato:

    hits = sm.recall(query or "", k=max(k * 6, k), deep=True, ...)
    # superseded rows, oversampled so the as-of filter doesn't starve top-k

Il tool dedicato pesca `k*6`; le due porte pescavano `k` e filtravano dopo.
Aprire la pesca ai ritirati (`include_superseded`) senza ALLARGARLA non basta:
se i primi `k` sono fatti nati DOPO l'istante chiesto, il filtro li scarta
tutti e la porta risponde vuoto pur avendo in archivio la risposta giusta.

⚠️ PERCHE' IL BANCO DI IERI NON POTEVA VEDERLO — `m3-as-of-e-scope-insieme.py`
mette `as_of` nel FUTURO, quando nessun fatto e' ancora ritirato: li' il
filtro non scarta niente e la pesca stretta non fa alcun danno. Un banco
costruito per isolare UNA causa e' cieco alla seconda, e la cura di ieri
(scope prima del taglio) NON copre questa. Sono due difetti, non uno.

IL RIFERIMENTO E' INDIPENDENTE: il verdetto non lo do' confrontando la porta
con se stessa, ma con `hippo_recall_as_of` allo STESSO istante e STESSO k —
il tool che quella risposta la sa dare. Se il riferimento torna 0, il banco
non misura niente e si ferma invece di dichiararsi verde.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time

_D = tempfile.mkdtemp(prefix="pesca_")
os.environ["HIPPO_DATA_DIR"] = _D
for _a in ("ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
    os.environ.pop(_a, None)

#: sys.path[0] e' la directory DELLO SCRIPT, non la radice del repo: senza
#: questa riga in un worktree si misura l'albero di qualcun altro (03/09).
_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

import asyncio  # noqa: E402
import json  # noqa: E402

import verimem  # noqa: E402
from verimem import mcp_server  # noqa: E402

_QUALE = pathlib.Path(verimem.__file__).resolve()
print(f"  verimem misurato: {_QUALE}")
if _ROOT not in _QUALE.parents:
    raise SystemExit(f"⛔ sto per misurare {_QUALE} invece del repo {_ROOT}.")

QUERY = "quale banca tratta il conto operativo della societa"
K = 2

#: i fatti di ALLORA: veri all'istante che chiederemo, ritirati dopo.
ALLORA = [
    "Il conto operativo della societa e' presso la Banca Alfa.",
    "Il conto operativo della societa ha IBAN aperto in Banca Alfa.",
]
#: i sostituti, e altro RUMORE di oggi: tutti nati DOPO l'istante chiesto e
#: tutti piu' vicini alla query, cosi' occupano i primi `k` della pesca.
OGGI = [
    "Il conto operativo della societa e' presso la Banca Beta.",
    "Il conto operativo della societa ha IBAN aperto in Banca Beta.",
    "Il conto operativo della societa tratta i bonifici con Banca Beta.",
    "Il conto operativo della societa e' gestito dalla filiale di Banca Beta.",
    "Il conto operativo della societa paga le commissioni a Banca Beta.",
    "Il conto operativo della societa riceve gli accrediti su Banca Beta.",
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
    """Quanti fatti ha RESTITUITO: dalla struttura, mai cercando id nel testo.

    Un record porta `superseded_by`, cioe' l'id del suo sostituto: cercare un
    id come sottostringa lo trova anche quando quel fatto non e' fra i
    risultati (rosso falso del 03/09).
    """
    for chiave in ("items", "results", "facts", "hits"):
        v = r.get(chiave)
        if isinstance(v, list):
            return len(v)
    return -1


def main() -> int:
    ag = mcp_server._ag()
    assert "pesca_" in str(ag.semantic.db_path), "non e' la dir temporanea"
    from verimem.client import Memory
    m = Memory()
    assert str(m.semantic.db_path) == str(ag.semantic.db_path), (
        "SDK e MCP su due store diversi: il banco non misurerebbe niente")

    vecchi = [m.add(t, topic="banco/pesca") for t in ALLORA]
    time.sleep(1.1)
    quando = time.time()          # <- l'istante che chiederemo: solo ALLORA
    time.sleep(1.1)
    nuovi = [m.add(t, topic="banco/pesca") for t in OGGI]

    def _id(x: object) -> str | None:
        return x.get("id") if isinstance(x, dict) else getattr(x, "id", None)

    for vecchio, nuovo in zip(vecchi, nuovi):
        m.semantic.supersede(_id(vecchio), _id(nuovo), principal="banco:pesca",
                             reason="same-source evolution")
    print(f"  scritti: {len(ALLORA)} di ALLORA (poi ritirati) · "
          f"{len(OGGI)} di OGGI, tutti piu' vicini alla query")
    print(f"  istante chiesto: {quando:.0f} — fra le due scritture")

    # ── IL RIFERIMENTO INDIPENDENTE ────────────────────────────────────────
    rif = quanti(asyncio.run(chiama(
        "hippo_recall_as_of", {"query": QUERY, "when": quando, "k": K})))
    print()
    print(f"  RIFERIMENTO — hippo_recall_as_of (pesca k*6): {rif} fatti")
    if rif <= 0:
        print("\n  ⛔ IL RIFERIMENTO E' VUOTO: il tool che sa rispondere non")
        print("     risponde, quindi il confronto non dice nulla sulle porte.")
        print("     Banco da riscrivere, non prodotto da accusare.")
        return 1

    # ── LE DUE PORTE, stessa domanda e stesso k ───────────────────────────
    esiti = {}
    for tool, chiave_k in (("hippo_facts_recall", "k"),
                           ("hippo_facts_search", "limit")):
        vivo = quanti(asyncio.run(chiama(tool, {"query": QUERY, chiave_k: K})))
        passato = asyncio.run(chiama(
            tool, {"query": QUERY, chiave_k: K, "as_of": quando}))
        n = quanti(passato)
        esiti[tool] = n
        print(f"  {tool}: {vivo} adesso · {n} all'istante chiesto"
              f" · scartati dichiarati: {passato.get('as_of_scartati')}")

    print()
    magre = {t: n for t, n in esiti.items() if n < rif}
    if magre:
        for tool, n in magre.items():
            print(f"  🔴 {tool} rende {n} dove il tool dedicato rende {rif}:")
        print("     la pesca e' stretta e il filtro temporale la affama.")
        return 1
    print(f"  🟢 ENTRAMBE le porte rendono quanto il tool dedicato ({rif}):")
    print("     la pesca e' allargata come in hippo_recall_as_of.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
