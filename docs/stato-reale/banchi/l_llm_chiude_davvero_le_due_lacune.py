"""L'A/B che manca: il giudice llm chiude davvero le due lacune note?

⛔ NON SI ESEGUE DA SOLO. Serve `--eseguo-e-so-che-costa`, e serve
   l'autorizzazione esplicita di chi paga il piano: ogni cella e' una chiamata
   `Memory(llm=...)`, cioe' `claude -p --model <modello>`. Sono 6 celle (contate dal codice, non a memoria: il piano
   a vuoto le stampa).
   Senza il flag stampa il piano e i numeri gia' noti, e non chiama nulla.

PERCHE' ESISTE. `README:30-32` dichiara due lacune note e dice che si chiudono
«only with an llm judge»:

    «a plausible added inference the source never states (e.g. "…reduced
     latency") scores high and is admitted»

Quella frase e' oggi una PROMESSA NON VERIFICATA: nessuno di noi l'ha misurata,
perche' richiede il giudice llm. Finche' non e' misurata, «si chiude con un llm
judge» non e' un fatto — e' un'attesa.

I NUMERI COL SOLO CE, misurati il 2026-08-26 (`198e49eb`, fuori da pytest, store
isolato). Sono la colonna «prima» dell'A/B:

    caso                                        CE      atteso con llm
    «e' conforme» / fonte «due pezzi difformi»  99.3    dovrebbe CADERE
    «ha superato i test» / fonte che tace       95.3    dovrebbe CADERE
    «il collaudo e' superato» / fonte nega      4.5     resta trattenuto
    «la copertura e' completa» / 9 senza test   78.4    dovrebbe CADERE
    fatto VERO che la fonte enuncia             99.9    deve RESTARE ammesso
    fatto VERO piu' basso della batteria        97.5    deve RESTARE ammesso

CRITERIO DI LETTURA, deciso PRIMA di eseguire — cosi' il risultato non si puo'
raccontare a posteriori:

  · la lacuna e' CHIUSA se i quattro «dovrebbe cadere» cadono E i due veri
    restano ammessi;
  · e' APERTA se anche uno solo dei quattro resta ammesso;
  · la cura e' PEGGIORE DEL MALE se un fatto vero viene rifiutato — ed e' il
    caso da temere di piu', perche' non comparirebbe in nessun rosso.

⚠️ Un llm judge che vede le stesse frasi che ho scritto io non e' una prova
   forte: le ho costruite conoscendo il difetto. Se il banco gira, vale
   aggiungere qualche caso preso dal corpus reale e non dalla mia testa.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

CASI = [
    ("vanto: conforme/difforme", 99.3, "cade",
     "Il lotto B12 e arrivato il 3 marzo con 40 pezzi. Due pezzi risultano difformi.",
     "Il lotto B12 e conforme alle specifiche."),
    ("vanto: riformulato", 95.3, "cade",
     "Il modulo di pagamento e stato scritto il 3 marzo. Restano aperte due segnalazioni.",
     "Il modulo ha superato i test."),
    ("vanto: contraddetto", 4.5, "resta trattenuto",
     "Il collaudo del lotto B12 non e stato eseguito.",
     "Il collaudo del lotto B12 e stato superato."),
    ("vanto: copertura", 78.4, "cade",
     "La suite ha 40 moduli. Nove moduli non hanno nessun test.",
     "La suite e completamente coperta dai test."),
    ("VERO: la fonte lo enuncia", 99.9, "resta AMMESSO",
     "Il lotto B12 e arrivato il 3 marzo con 40 pezzi. Due pezzi risultano difformi.",
     "Due pezzi del lotto B12 risultano difformi."),
    ("VERO: il piu' basso", 97.5, "resta AMMESSO",
     "L audit e cominciato il primo marzo e copre tre reparti.",
     "L audit copre tre reparti."),
]


def _piano() -> None:
    print(__doc__.split("I NUMERI COL SOLO CE")[0].rstrip())
    print(f"  celle: {len(CASI)}  ·  ogni cella = 1 chiamata al giudice llm")
    print(f"  {'caso':<28} {'CE':>7}   atteso con llm")
    for nome, ce, atteso, _f, _c in CASI:
        print(f"  {nome:<28} {ce:>7.1f}   {atteso}")
    print("\n  per eseguire:  python docs/stato-reale/banchi/"
          "l_llm_chiude_davvero_le_due_lacune.py --eseguo-e-so-che-costa <modello>")
    print("  ⛔ solo col via esplicito di chi paga il piano.")


def _esegui(modello: str) -> int:
    from verimem.client import Memory

    print(f"  giudice: {modello}\n")
    print(f"  {'caso':<28} {'CE':>7} {'llm':>10}  esito")
    esiti = []
    for nome, ce, atteso, fonte, claim in CASI:
        mem = Memory(str(Path(tempfile.mkdtemp()) / "llm.db"), llm=modello)
        ric = mem.add(claim, topic="t/llm", source=fonte, validate="full")
        stato = str(ric.get("status"))
        g = ric.get("grounding_score")
        gs = f"{g:.1f}" if isinstance(g, (int, float)) else str(g)
        caduto = stato == "quarantined"
        ok = caduto if atteso.startswith(("cade", "resta trattenuto")) else not caduto
        esiti.append((nome, ok))
        print(f"  {nome:<28} {ce:>7.1f} {gs:>10}  {'✅' if ok else '🔴'} {stato}")
    falliti = [n for n, ok in esiti if not ok]
    print()
    if not falliti:
        print("  ✅ la lacuna e' CHIUSA dal giudice llm su tutte le celle previste")
        return 0
    print(f"  🔴 celle che non rispettano il criterio deciso prima: {falliti}")
    return 1


if __name__ == "__main__":
    if "--eseguo-e-so-che-costa" not in sys.argv:
        _piano()
        raise SystemExit(0)
    i = sys.argv.index("--eseguo-e-so-che-costa")
    modello = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
    if not modello:
        print("  ⛔ manca il modello: --eseguo-e-so-che-costa <modello>")
        print("     mai senza, o il CLI figlio parte col default e brucia il piano.")
        raise SystemExit(2)
    raise SystemExit(_esegui(modello))
