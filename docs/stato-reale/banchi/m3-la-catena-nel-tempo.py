"""M3 — su una CATENA di supersessioni, `as_of` ricostruisce lo stato di allora?

    python docs/stato-reale/banchi/m3-la-catena-nel-tempo.py

Il banco gemello (`m3-il-passato-torna-davvero.py`) ha misurato che il
time-travel regge su UN asse solo — il write time — perché `hippo_remember`
accetta `asserted_at` e lo scarta. Ma quella prova usava DUE scritture e
chiedeva solo «prima della scrittura è vuoto, dopo è pieno»: un filtro che
guardasse soltanto l'esistenza passerebbe lo stesso.

**Questo banco è di TRE scritture**, che è il minimo per avere una CATENA
(A ritirato da B, B ritirato da C) e quindi uno stato intermedio da
ricostruire. La domanda:

    all'istante fra B e C, `hippo_recall_as_of` restituisce B — che a quel
    momento era la verità corrente — oppure restituisce C, o niente?

═══════════════════════════════════════════════════════════════════════════
LA PREDIZIONE, DEPOSITATA QUI PRIMA DI ESEGUIRE (ws2, 03/09 ore 20:45)
═══════════════════════════════════════════════════════════════════════════

**Predico che B NON torni**, e la ragione è precisa: il filtro temporale ha
solo `created_at` (l'evento non è scrivibile da questa porta) e lo stato di
supersessione che legge è quello **ATTUALE**, non quello di allora. B oggi
risulta superseduto, quindi verrebbe escluso anche all'istante in cui era
corrente. Se è così, `as_of` sa dire «questo fatto non esisteva ancora» ma
non «questo fatto era quello giusto allora» — cioè filtra sulla NASCITA e non
sulla VITA, che è metà di una ricostruzione bi-temporale.

**Mi falsifica**: B che torna all'istante intermedio.

**Controprova che devo accettare come mia sconfitta anche al contrario**: se
NEMMENO C torna a un istante successivo a tutto, il banco non sta misurando la
catena ma un time-travel rotto in generale, e la predizione non è confermata —
è indecidibile. Per questo il controllo positivo qui è DOPPIO.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import time

_D = tempfile.mkdtemp(prefix="m3cat_")
os.environ["HIPPO_DATA_DIR"] = _D          # PRIMA dell'import: è tutto il punto
os.environ.pop("ENGRAM_DATA_DIR", None)

#: ⚠️ `python docs/.../questo.py` mette in `sys.path[0]` la directory DELLO
#: SCRIPT: `import verimem` prenderebbe il pacchetto INSTALLATO. In un
#: `git worktree` è l'albero di qualcun altro — il 03/09 è costato tre rossi
#: a un banco gemello, tutti attribuiti al prodotto.
_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

import asyncio  # noqa: E402
import json  # noqa: E402

import verimem  # noqa: E402
from verimem import mcp_server  # noqa: E402

_QUALE = pathlib.Path(verimem.__file__).resolve()
if _ROOT not in _QUALE.parents:
    raise SystemExit(
        f"⛔ sto per misurare {_QUALE}\n"
        f"   invece del repo {_ROOT}: il verdetto non direbbe niente.")

A = "Il prezzo di listino del modello X è 1200 euro."
B = "Il prezzo di listino del modello X è 1350 euro."
C = "Il prezzo di listino del modello X è 1500 euro."
QUERY = "qual è il prezzo di listino del modello X"


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


def ids_dei_risultati(risposta: dict) -> set:
    """Gli id dei fatti RESTITUITI, non ogni id che compare nella risposta.

    ⚠️ SERVE PERCHE' LA RICERCA PER SOTTOSTRINGA MENTE: il record di un fatto
    porta `superseded_by`, cioe' l'id del suo SOSTITUTO. Cercando l'id di C
    dentro il JSON serializzato lo si trova anche quando C non e' fra i
    risultati — e il banco accusa il prodotto di restituire un fatto del
    futuro. E' successo alle 20:52 del 03/09, e sarebbe stato il SECONDO rosso
    della giornata attribuito al prodotto e dovuto al misuratore.
    """
    out = set()
    for r in (risposta.get("facts") or risposta.get("items") or []):
        v = r.get("id") if isinstance(r, dict) else None
        if v:
            out.add(v)
    return out


def scrivi(prop: str, euro: str) -> str:
    r = asyncio.run(chiama("hippo_remember", {
        "proposition": prop, "topic": "banco/m3cat",
        "source": f"Listino: modello X, {euro} euro."}))
    return r.get("id")


def main() -> int:
    ag = mcp_server._ag()
    assert "m3cat_" in str(ag.semantic.db_path), "non è la dir temporanea"

    t0 = time.time()
    ida = scrivi(A, "1200")
    idb = scrivi(B, "1350")
    ag.semantic.supersede(ida, idb, principal="banco:m3cat", reason="listino rev.2")
    t_fra_b_e_c = time.time()          # ⬅ QUI B è la verità corrente
    time.sleep(4.0)                    # distacco AMPIO: un 'C torna' con un
                                       # secondo di margine non distinguerebbe
                                       # il difetto dalla granularita' del filtro
    idc = scrivi(C, "1500")
    ag.semantic.supersede(idb, idc, principal="banco:m3cat", reason="listino rev.3")
    t_fine = time.time()

    print(f"  catena: A={ida} -> B={idb} -> C={idc}")
    print(f"  l'istante in cui B era corrente: {t_fra_b_e_c:.0f} "
          f"(t0={t0:.0f}, fine={t_fine:.0f})")

    #: ⚠️ CLASSIFICARE PRIMA DI SPIEGARE: «C torna a un istante precedente»
    #: ha due cause opposte — il filtro non filtra, oppure i miei istanti sono
    #: cosi' vicini che C e' nato PRIMA di quello che chiamo «fra B e C».
    #: Senza questi numeri il verdetto accusa il prodotto di un difetto che
    #: potrebbe essere del banco.
    import sqlite3 as _s
    _c = _s.connect(f"file:{ag.semantic.db_path}?mode=ro", uri=True)
    _nati = {}
    for _i, _e in ((ida, "A"), (idb, "B"), (idc, "C")):
        _r = _c.execute("SELECT created_at FROM facts WHERE id=?", (_i,)).fetchone()
        _nati[_e] = _r[0] if _r else None
        _d = (_nati[_e] - t_fra_b_e_c) if _nati[_e] else None
        print(f"     {_e} created_at={_nati[_e]:.2f}  "
              f"{'DOPO' if _d and _d > 0 else 'prima'} l'istante chiesto "
              f"di {abs(_d):.2f}s")
    _c.close()

    prima = ids_dei_risultati(asyncio.run(chiama(
        "hippo_recall_as_of", {"query": QUERY, "when": t0 - 1, "k": 5})))
    intermedio = ids_dei_risultati(asyncio.run(chiama(
        "hippo_recall_as_of", {"query": QUERY, "when": t_fra_b_e_c, "k": 5})))
    dopo = ids_dei_risultati(asyncio.run(chiama(
        "hippo_recall_as_of", {"query": QUERY, "when": t_fine + 1, "k": 5})))
    oggi = ids_dei_risultati(asyncio.run(chiama(
        "hippo_facts_recall", {"query": QUERY, "k": 5})))

    print()
    print("  CONTROLLO POSITIVO 1 — oggi torna C (l'ultimo)?      ", idc in oggi)
    print("  CONTROLLO POSITIVO 2 — a fine catena as_of torna C?  ", idc in dopo)
    print("  prima di tutto, il passato è vuoto?                  ",
          not any(i in prima for i in (ida, idb, idc)))
    print()
    print("  ⭐ ALL'ISTANTE IN CUI B ERA CORRENTE, as_of torna:")
    print(f"       B (la risposta giusta di allora)?  {idb in intermedio}")
    print(f"       A (già ritirato allora)?           {ida in intermedio}")
    print(f"       C (non ancora scritto allora)?     {idc in intermedio}")
    print()

    if idc not in oggi:
        print("  ⛔ CONTROLLO POSITIVO 1 SPENTO: la recall di oggi non torna")
        print("     nemmeno l'ultimo della catena. Nulla qui dice niente.")
        return 1
    if idc not in dopo:
        print("  ⛔ CONTROLLO POSITIVO 2 SPENTO: as_of non torna C nemmeno a")
        print("     catena finita ⇒ il time-travel è rotto in generale e questo")
        print("     banco NON può decidere sulla catena. Indecidibile, non")
        print("     'predizione confermata'.")
        return 1
    if idc in intermedio:
        print("  🔴 as_of restituisce un fatto scritto DOPO l'istante chiesto:")
        print("     non è una ricostruzione, è la vista di oggi rietichettata.")
        return 1
    if idb in intermedio:
        print("  🟢 LA MIA PREDIZIONE È FALSIFICATA, ed è la notizia buona:")
        print("     la catena conserva lo stato di allora — B torna all'istante")
        print("     in cui era corrente, pur essendo superseduto OGGI.")
        return 0
    print("  🟡 PREDIZIONE CONFERMATA: B non torna all'istante in cui era la")
    print("     verità corrente. `as_of` filtra sulla NASCITA del fatto, non")
    print("     sulla sua VITA: sa dire «non esisteva ancora», non sa dire")
    print("     «era questo». Su una catena, metà della ricostruzione")
    print("     bi-temporale manca — e il caso d'uso dichiarato dal tool")
    print("     («state of knowledge at signature date») è esattamente questo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
