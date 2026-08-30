"""Il QUINTO punto in cui un pavimento filtra senza sapere se il ranking sia
degradato — ed e' il dossier di custodia.

DA DOVE VIENE. Chiuso il quarto (`c97aa380`, `temporal_context`), ho fatto lo
sweep che avevo annunciato: `git grep -n min_relevance -- verimem/`, e per ogni
punto in cui un pavimento TAGLIA ho guardato se il chiamante legga
`_recall_degraded_count`::

    client.py:1219              guardia   (`Memory.search`)
    mcp_server.py:13850         guardia   (`hippo_facts_recall`)
    proactive_step_injector:118 guardia
    temporal_context.py:332     guardia   (curata stanotte)
    cli.py:1349                 delega a `m.search` -> coperto
    trust_report.py:234         NESSUNA   <-- il quinto

Il filtro::

    if min_relevance > 0.0 and not ce_ran:
        kept = [h for h in hits if h[1] is not None and h[1] >= min_relevance]

⇒ nessun controllo sul degrado. Ci si arriva da DUE superfici: l'SDK
(`Memory.explain(min_relevance=...)`) e la porta MCP (`hippo_trust_report`).

🔑 E QUI C'E' UN AGGRAVANTE che il quarto non aveva: il report mette
`floored = True`. Cioe' nel degrado il dossier **dichiara di aver filtrato per
rilevanza** dei risultati la cui rilevanza non e' stata misurata. Non e' solo
un'astensione falsa: e' un'astensione falsa che si giustifica.

⚖️ QUANDO IL CE GIRA il filtro grezzo non si applica (`not ce_ran`), quindi il
fenomeno riguarda chi NON ha il reranker installato o chi passa un pavimento
esplicito dall'SDK — dove `ce_gate` e' acceso solo per `"auto"`.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: **a caldo**, con lo stesso pavimento, il
dossier deve contenere qualcosa. Se fosse gia' vuoto non ci sarebbe niente che
il degrado possa svuotare.
⚠️ LA POPOLAZIONE OPPOSTA: **degradato SENZA pavimento** il dossier deve
restare pieno. Se si svuotasse anche li', la causa non e' il pavimento.
⚠️ E LE CHIAVI SI LEGGONO, non si indovinano: il banco stampa le chiavi del
report prima di contare qualsiasi cosa. Stanotte tre volte il difetto era nel
misuratore, una delle quali proprio per una chiave inventata.
═══════════════════════════════════════════════════════════════════════════════

REGIME: un processo, store TEMPORANEO con cinque fatti, SDK in-process, giudice
locale ASSENTE per costruzione (nessuno scaricamento) — quindi `ce_ran` e'
falso e il filtro grezzo e' sul percorso. Lo store di Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-il-quinto-consumatore-e-il-dossier.py
"""

from __future__ import annotations

import json
import subprocess
import sys

DOMANDA = "quanti metri quadrati ha il magazzino K-74"
PAVIMENTO = 0.5

FIGLIO = r'''
import json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
os.environ.pop("ENGRAM_MIN_RELEVANCE", None)

import verimem.semantic as sem
from verimem.client import Memory

domanda, pavimento = sys.argv[1], float(sys.argv[2])
m = Memory(str(os.path.join(tempfile.mkdtemp(), "s.db")))
for i in range(1, 6):
    m.add(f"Il magazzino K-{70 + i} di Rovigo ha {4000 + i * 100} metri quadrati.",
          source=f"Registro immobili, scheda K-{70 + i}: superficie {4000 + i * 100} metri quadrati.",
          topic="deg5/mag")

primo = m.explain(domanda, k=5)
CHIAVI = sorted(primo.keys())
# La chiave della lista si LEGGE fra quelle che il report porta davvero.
CANDIDATE = [c for c in ("facts", "results", "items", "hits", "evidence")
             if isinstance(primo.get(c), list)]

def misura(regime):
    fuori = []
    for etichetta, pav in ((f"pavimento {pavimento}", pavimento),
                           ("nessun pavimento", 0.0)):
        r = m.explain(domanda, k=5, min_relevance=pav)
        n = len(r.get(CANDIDATE[0]) or []) if CANDIDATE else -1
        fuori.append({"regime": regime, "caso": etichetta, "n": n,
                      # ⚠️ `floored` e' la variabile INTERNA di
                      # build_trust_report; nel report esposto la chiave e'
                      # `floor_applied_by`. La prima stesura leggeva la prima e
                      # stampava `None` per tutte le righe: quarta volta
                      # stanotte che il misuratore sbaglia chiave.
                      "floored": r.get("floor_applied_by"),
                      "abstained": r.get("abstained"),
                      "min_relevance": r.get("min_relevance")})
    return fuori

righe = misura("a caldo")
VERO = sem._encode_prepared_within_budget
sem._encode_prepared_within_budget = lambda *a, **k: None
righe += misura("degradato")
sem._encode_prepared_within_budget = VERO

print(json.dumps({"chiavi": CHIAVI, "lista": CANDIDATE, "righe": righe},
                 ensure_ascii=False, default=str))
'''


def main() -> int:
    p = subprocess.run([sys.executable, "-c", FIGLIO, DOMANDA, str(PAVIMENTO)],
                       capture_output=True, text=True, timeout=2400)
    if p.returncode != 0:
        print(f"  PROCESSO MORTO exit={p.returncode}: {p.stderr.strip()[-500:]}")
        return 1
    dati = json.loads(p.stdout.strip().splitlines()[-1])
    righe = dati["righe"]

    print(f"  CHIAVI DEL REPORT (lette, non indovinate): {dati['chiavi']}")
    print(f"  la lista dei fatti sta in: {dati['lista'] or 'NESSUNA — non contabile'}")
    if not dati["lista"]:
        print("\n  NESSUN VERDETTO: senza sapere dove stia la lista, ogni conteggio")
        print("  sarebbe inventato. E' il difetto che stanotte mi e' costato tre")
        print("  misure sbagliate.")
        return 1

    print(f"\n  {'regime':<12} {'caso':<20} {'n':>3}  {'floor_by':<10} "
          f"{'abstained':<10} pavimento")
    print("  " + "-" * 76)
    for r in righe:
        print(f"  {r['regime']:<12} {r['caso']:<20} {r['n']:>3}  "
              f"{str(r['floored']):<8} {str(r['abstained']):<10} "
              f"{r['min_relevance']}")

    def _r(regime: str, prefisso: str) -> dict:
        for x in righe:
            if x["regime"] == regime and x["caso"].startswith(prefisso):
                return x
        return {"n": -1}

    caldo = _r("a caldo", "pavimento")
    print(f"\n  [1] CONTROLLO — a caldo col pavimento il dossier ha "
          f"qualcosa: n={caldo['n']}")
    if caldo["n"] <= 0:
        print("      CONTROLLO CADUTO: gia' vuoto a caldo ⇒ niente da svuotare.")
        print("      NESSUN VERDETTO.")
        return 1

    senza = _r("degradato", "nessun")
    print(f"  [2] POPOLAZIONE OPPOSTA — degradato SENZA pavimento: n={senza['n']}")
    if senza["n"] <= 0:
        print("      Il degrado da solo svuota ⇒ la causa non e' il pavimento.")
        print("      NESSUN VERDETTO sul pavimento.")
        return 1

    con = _r("degradato", "pavimento")
    print("\n  ══ VERDETTO ══")
    if con["n"] <= 0:
        print(f"     🔴 IL QUINTO CONSUMATORE: degradato col pavimento n={con['n']},")
        print(f"     senza pavimento n={senza['n']}, a caldo n={caldo['n']}.")
        print(f"     ⚠️ E il dossier lo GIUSTIFICA: floor_applied_by={con['floored']}, "
              f"abstained={con['abstained']} — dichiara di aver filtrato per")
        print("     rilevanza dei risultati la cui rilevanza NON e' stata")
        print("     misurata. Un'astensione falsa che si spiega da sola.")
    else:
        # ⚠️ UN BANCO CHE NON SA IN QUALE REGIME GIRA DICE LA COSA
        # SBAGLIATA NEL RAMO VERDE. Tre volte stanotte un mio banco ha
        # attribuito a «lettura incompleta» un verde che era la MIA cura
        # appena applicata. Qui il regime si LEGGE dal sorgente.
        import pathlib
        sorgente = pathlib.Path(__file__).resolve().parents[3] / "verimem" / "trust_report.py"
        curato = ("_ranking_degradato" in sorgente.read_text(encoding="utf-8")
                  if sorgente.exists() else None)
        if curato:
            print(f"     🟢 IL DOPO: la guardia e' in vigore ({sorgente.name} "
                  f"contiene `_ranking_degradato`) e il dossier regge anche")
            print(f"     degradato (n={con['n']}, abstained={con['abstained']}).")
            print("     Per rivedere il PRIMA, togli `and not _ranking_degradato`")
            print("     dalla condizione del filtro e riesegui.")
        else:
            print(f"     🟢 il dossier regge anche degradato (n={con['n']}) SENZA")
            print("     che la guardia sia nel sorgente: la lettura era")
            print("     incompleta, o il CE ha girato e il filtro grezzo non era")
            print("     sul percorso.")

    print("\n  ⚠️ LIMITI: cinque fatti, una domanda, un pavimento, degrado")
    print("     SIMULATO, giudice locale assente. Con un reranker installato e")
    print("     `ce_ran` vero il filtro grezzo non si applica: questo banco NON")
    print("     dice quanto spesso il caso si presenti in servizio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
