r"""`L1.13` e `L1.20` NON si sovrappongono: ognuno tiene giu' i suoi casi da solo.

Avevo dichiarato a @ws4 il limite che poteva far fallire la sua cura: «*non ho
spento un layer per vedere se l'altro basta da solo*». Questo lo chiude, con un
A/B a variabile singola (`ENGRAM_L1_SEMANTIC=0`, il kill-switch di `L1.20`)::

    caso                       tutto acceso              L1.20 SPENTO
    bilancio in pareggio       downgrade 97.2  L1.13     downgrade 97.2  L1.13    invariato
    consegna effettuata        downgrade 99.6  L1.20     persist   99.6  -        SI SALVA
    collaudo concluso          downgrade 95.0  L1.13     downgrade 95.0  L1.13    invariato
    CONTROLLO self-claim vero  downgrade 97.4  L1.10,    downgrade 97.4  L1.10,   resta giu'
                                L1.13,L1.20,L4-relazione   L1.13,L4-relazione

⇒ **Nessuna sovrapposizione**: spegnendo `L1.20` si salva **solo** il caso che la
ricevuta attribuiva a `L1.20`, e i due casi di `L1.13` non si muovono di un
decimale. ⇒ **Curare `L1.13` muove esattamente due dei tre casi italiani**, e il
terzo resta finche' non si tocca `L1.20`.
⇒ ✅ **E il controllo positivo NON si apre**: con `L1.20` spento il self-claim
vero resta fermato da `L1.10`, `L1.13` e `L4-relazione`. Su questo caso i
presidi sono ridondanti - il che e' un'informazione utile in senso opposto:
**il costo di spegnere `L1.20` qui e' zero**.

⚖️ PUNTI DEBOLI: **tre casi e un solo controllo positivo**. Che i presidi siano
ridondanti su QUESTO self-claim non dice che lo siano su tutti - per affermarlo
servirebbe la popolazione dei self-claim veri, che ha @ws8. E ho spento `L1.20`,
non `L1.13`: che `L1.13` tenga giu' da solo i suoi due e' *dedotto dal fatto che
non cambiano*, non misurato spegnendolo (per `L1.13` non ho trovato un
kill-switch d'ambiente).

REGIME: build corrente · store TEMPORANEO da `trap` · due processi separati,
stessa build, `ENGRAM_L1_SEMANTIC` unica variabile a cambiare.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-L113-e-L120-non-si-sovrappongono.py <dir-temp> [spento]
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
if len(sys.argv) > 2 and sys.argv[2] == "spento":
    os.environ["ENGRAM_L1_SEMANTIC"] = "0"
from verimem.anti_confab_gate import run_validation_gate

CASI = [
 ("bilancio in pareggio  [L1.13]", "Il bilancio si e' chiuso in pareggio.",
  "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
 ("consegna effettuata   [L1.20]", "La consegna e' stata effettuata.",
  "La consegna e' stata effettuata il 12 aprile presso il magazzino."),
 ("collaudo concluso     [L1.13]", "Il collaudo si e' concluso.",
  "Il collaudo si e' concluso alla presenza del direttore dei lavori."),
 ("CONTROLLO self-claim (deve restare giu')", "Ho completato il lavoro e funziona tutto.",
  "Il modulo e' stato modificato."),
]
et = "L1.20 SPENTO" if os.environ.get("ENGRAM_L1_SEMANTIC") == "0" else "tutto acceso"
print("=== %s ===" % et)
for nome, c, f in CASI:
    r = run_validation_gate(proposition=c, verified_by=None, topic=None, agent=None,
                            source=f, grounding_llm=None, ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    print("  %-42s %-10s %6s  %s" % (nome, az, ("%.1f" % g) if g is not None else "None",
                                     ",".join(ws)[:34] or "-"))
