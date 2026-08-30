"""Tre consumatori sanno che il ranking puo' degradare. Il quarto no, e ha il
pavimento.

DA DOVE VIENE. Curando la ricevuta di `hippo_recall_history` (`e24d25d5`) ho
letto l'handler della porta gemella e ho visto la guardia; su questa porta non
c'era. `git grep _recall_degraded_count -- verimem/`::

    verimem/client.py:1126               guardia
    verimem/mcp_server.py:13764          guardia (hippo_facts_recall)
    verimem/proactive_step_injector.py:114  guardia
    verimem/temporal_context.py          NESSUNA   ← e qui c'e' il pavimento

Il filtro sta a `temporal_context.py:332`::

    if min_relevance:
        hits = [h for h in hits if float(h[1] or 0.0) >= _pav]

⇒ nessun controllo sul degrado. E il commento accanto spiega **perche' non puo'
stare nell'handler**: la funzione restituisce righe gia' formattate, «a valle lo
score non esiste piu'». Quindi la guardia dell'handler gemello non arriva qui
nemmeno volendo.

🔑 PERCHE' CONTA. Quando l'encoder non risponde entro il budget, `recall` cade
sul ramo keyword e assegna `score 0.0` a TUTTI i risultati: non «nessuna
somiglianza» ma **somiglianza NON MISURATA**. Confrontarla con una soglia di
somiglianza e' un errore di categoria — e con un pavimento qualsiasi svuota la
risposta. E' il canale degli agenti: chi riceve l'astensione falsa e' un modello
che non ha modo di sospettarla.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: **a caldo**, con lo stesso pavimento, la
porta deve rispondere. Se fosse gia' vuota a caldo non ci sarebbe niente da
svuotare e il degrado non spiegherebbe nulla.
⚠️ LA POPOLAZIONE OPPOSTA: **degradato SENZA pavimento** la risposta deve
restare piena. Se si svuotasse anche li', la causa non e' il pavimento.
⚠️ LA CELLA CHE ATTRIBUISCE: **la porta gemella nello stesso degrado e con lo
stesso pavimento** deve rispondere. E' cio' che separa «la guardia manca» da
«il degrado rompe tutto».
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO con cinque fatti, porte MCP in-process,
degrado simulato spegnendo `semantic._encode_prepared_within_budget` (lo stesso
modo di `tests/test_l_iniezione_proattiva_spariva_col_degrado.py`). Lo store di
Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-il-quarto-consumatore-che-non-conosce-il-degrado.py
"""

from __future__ import annotations

import json
import subprocess
import sys

DOMANDA = "quanti metri quadrati ha il magazzino K-77"
PAVIMENTO = 0.5

FIGLIO = r'''
import asyncio, json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

from verimem import mcp_server
import verimem.semantic as sem

domanda, pavimento = sys.argv[1], float(sys.argv[2])

def chiama(nome, args):
    d = json.loads(asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)
    # ⚠️ OGNI PORTA HA IL SUO NOME PER LA LISTA, e la prima stesura ne
    # indovinava uno (`results`) che non esiste su nessuna delle due: tutte le
    # celle della porta gemella davano n=0, ANCHE a caldo e senza pavimento, e
    # il banco stava per concludere «anche la gemella si svuota» — falso. Le
    # chiavi vere, LETTE dalla ricevuta: `context` di qua, `items` di la'.
    chiave = "context" if nome == "hippo_recall_history" else "items"
    assert chiave in d, f"{nome}: chiave {chiave} assente, ricevuta {sorted(d)}"
    return len(d.get(chiave) or []), d.get("min_relevance")

for i in range(1, 6):
    asyncio.run(mcp_server._call_tool_impl("hippo_remember", {
        "proposition": f"Il magazzino K-{70 + i} di Rovigo ha {4000 + i * 100} metri quadrati.",
        "source": f"Registro immobili, scheda K-{70 + i}: superficie {4000 + i * 100} metri quadrati.",
        "topic": "deg/mag"}))

VERO = sem._encode_prepared_within_budget

def celle(regime):
    fuori = []
    for porta in ("hippo_recall_history", "hippo_facts_recall"):
        for etichetta, extra in ((f"pavimento {pavimento}", {"min_relevance": pavimento}),
                                 ("nessun pavimento", {})):
            n, pav = chiama(porta, {"query": domanda, "k": 5, **extra})
            fuori.append({"regime": regime, "porta": porta, "caso": etichetta,
                          "n": n, "pavimento_riportato": pav})
    return fuori

righe = celle("a caldo")
sem._encode_prepared_within_budget = lambda *a, **k: None   # degrado
righe += celle("degradato")
sem._encode_prepared_within_budget = VERO

print(json.dumps(righe, ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO, DOMANDA, str(PAVIMENTO)],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-400:]}")
        return 1
    righe = json.loads(p.stdout.strip().splitlines()[-1])

    print(f"  {'regime':<12} {'porta':<22} {'caso':<20} {'n':>3}  pavimento")
    print("  " + "-" * 74)
    for r in righe:
        print(f"  {r['regime']:<12} {r['porta']:<22} {r['caso']:<20} "
              f"{r['n']:>3}  {r['pavimento_riportato']}")

    def _n(regime: str, porta: str, caso_prefisso: str) -> int:
        for r in righe:
            if (r["regime"] == regime and r["porta"] == porta
                    and r["caso"].startswith(caso_prefisso)):
                return int(r["n"])
        return -1

    caldo = _n("a caldo", "hippo_recall_history", "pavimento")
    print(f"\n  [1] CONTROLLO — a caldo col pavimento la porta risponde: n={caldo}")
    if caldo <= 0:
        print("      CONTROLLO CADUTO: gia' vuota a caldo ⇒ non c'e' niente che")
        print("      il degrado possa svuotare. NESSUN VERDETTO.")
        return 1

    senza = _n("degradato", "hippo_recall_history", "nessun")
    print(f"  [2] POPOLAZIONE OPPOSTA — degradato SENZA pavimento: n={senza}")
    if senza <= 0:
        print("      Il degrado da solo svuota ⇒ la causa non e' il pavimento.")
        print("      NESSUN VERDETTO sul pavimento.")
        return 1

    gemella = _n("degradato", "hippo_facts_recall", "pavimento")
    con = _n("degradato", "hippo_recall_history", "pavimento")
    print(f"  [3] CELLA CHE ATTRIBUISCE — la GEMELLA, stesso degrado e stesso "
          f"pavimento: n={gemella}")

    print("\n  ══ VERDETTO ══")
    if con <= 0 < gemella:
        print(f"     🔴 LA PORTA SI SVUOTA COL DEGRADO: n={con} col pavimento,")
        print(f"     n={senza} senza, mentre la gemella nello STESSO degrado e")
        print(f"     con lo STESSO pavimento risponde n={gemella}.")
        print("     ⇒ La differenza e' la guardia, non il degrado. E' il QUARTO")
        print("     consumatore del contatore: tre ce l'hanno, questo no.")
        print("     ⚠️ E' un'astensione FALSA su un canale letto da modelli.")
    elif con > 0:
        print(f"     🟢 la porta risponde anche degradata (n={con}): la guardia")
        print("     c'e' per un'altra via, o il ramo keyword assegna punteggi")
        print("     sopra il pavimento. La lettura del sorgente era incompleta.")
    else:
        print(f"     🟡 anche la gemella si svuota (n={gemella}): il fenomeno non")
        print("     e' la guardia mancante. Nessuna attribuzione.")

    print("\n  ⚠️ LIMITI: uno store da cinque fatti, una domanda, un pavimento,")
    print("     degrado SIMULATO spegnendo una funzione. NON misura quanto")
    print("     spesso l'encoder degradi davvero in servizio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
