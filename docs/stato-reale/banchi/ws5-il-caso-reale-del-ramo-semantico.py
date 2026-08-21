"""Il caso REALE che la guardia del gate (a) non vedeva — e perché non è un test.

    python docs/stato-reale/banchi/ws5-il-caso-reale-del-ramo-semantico.py

IL CASO, preso dal corpus di casa il 2026-08-21 (trovato da ws2, riprodotto da ws5):

    7a0fbf8ad953   grounding 99.83   ->  superseded_by = 83407efc3a25
    83407efc3a25   grounding None    <-  mai giudicato, e ha vinto

Un fatto che il giudice sostiene a 99.83 è stato ritirato da un claim che nessun
giudice ha mai visto. Le due proposizioni non sono nemmeno lo stesso valore che
evolve: una dice che lo stato è LIVE, l'altra che `visibilityState` è hidden.

PERCHÉ UNO SCRIPT E NON UN TEST. `tests/conftest.py:121` sostituisce l'embedder con
uno stub in una fixture `autouse=True`, e questo percorso decide col coseno. Misurato
il 21/08 sullo STESSO caso e le STESSE stringhe:

    fuori da pytest   il fatto viene RITIRATO
    dentro pytest     il fatto sopravvive  ->  il test PASSA

Un test qui è verde per costruzione: non misura il prodotto, misura lo stub. È la
ragione per cui la prima guardia (`aeee8305`) sembrava a posto pur non toccando
questo ramo — il suo banco era numerico e passava dal percorso lessicale, dove
`_route_evolutions` decide. Su questo caso quella funzione non viene chiamata
nemmeno una volta: 0, misurato strumentandola.

Le due stringhe qui sotto sono copiate BYTE PER BYTE dallo store (198 e 152
caratteri). Alla prima stesura le avevo ricopiate da un print troncato a 150 e
avevo completato la frase a mano: spariva il «1016», cioè il numero su cui il ramo
lessicale decide, e il banco dava il verdetto rovesciato.
"""
from __future__ import annotations

import os
import sys
import tempfile
import warnings

# ⚠️ LA RADICE DEL CHECKOUT VA PRIMA, e non e' pedanteria: `sys.path[0]` e' la
# cartella dello SCRIPT, cioe' `docs/stato-reale/banchi/`. Senza questa riga
# `import verimem` risolve sul primo che trova nel path — tipicamente il clone
# principale — e il banco misura un ALTRO albero senza dirlo. Misurato il
# 2026-08-21: lo stesso banco dava «il fatto e' RITIRATO» girando in un worktree
# che conteneva gia' la cura, perche' stava importando il repo di sviluppo.
# Per questo `main()` stampa da dove arriva il modulo: un banco che non dichiara
# COSA sta misurando puo' solo confermare quello che chi lo lancia si aspetta.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3]))

warnings.filterwarnings("ignore")
os.environ["ENGRAM_SUPERSEDE_SAME_SOURCE"] = "enforce"
os.environ.pop("ENGRAM_SEMANTIC_CONFLICT", None)

TOPIC = "project/verimem/dogfooding-ws6-feed-non-renderizza"
FONTE = ["source-doc:enginroom:1"]
GIUDICATO = (
    "Nella Engine Room di ws6 lo stato dice LIVE e il contenitore del feed ha zero "
    "figli mentre una fetch sullo stesso endpoint dalla stessa pagina legge 1016 "
    "byte con data: e il separatore doppio a capo")
MAI_GIUDICATO = (
    "Nella Engine Room di ws6 document.visibilityState vale hidden e il contenitore "
    "del feed ha zero figli prima e dopo aver forzato un requestAnimationFrame")


def _store():
    from verimem import Memory
    return Memory(path=os.path.join(tempfile.mkdtemp(prefix="ws5_caso_"), "s", "s.db"))


def il_caso() -> bool:
    """Un claim mai giudicato NON deve ritirare un fatto che il giudice sostiene."""
    mem = _store()
    r1 = mem.add(GIUDICATO, topic=TOPIC, verified_by=FONTE, source=GIUDICATO,
                 validate="full")
    r2 = mem.add(MAI_GIUDICATO, topic=TOPIC, verified_by=FONTE, validate="full")
    vecchio = mem.semantic.get(r1["id"])
    vivo = vecchio.superseded_by is None
    print("  il fatto giudicato (%s) e': %s"
          % (r1.get("grounding_score"), "VIVO" if vivo else
             "RITIRATO da %s" % vecchio.superseded_by))
    print("  il claim mai giudicato e': %s" % r2.get("status"))
    return vivo


def il_controllo() -> bool:
    """...ma con la SUA source l'aggiornamento deve continuare a passare.
    Senza questa meta', una guardia che blocca tutto passerebbe il caso qui sopra
    spegnendo l'evoluzione dei fatti, che e' la promessa centrale del prodotto."""
    mem = _store()
    r1 = mem.add(GIUDICATO, topic=TOPIC, verified_by=FONTE, source=GIUDICATO,
                 validate="full")
    r2 = mem.add(MAI_GIUDICATO, topic=TOPIC, verified_by=FONTE,
                 source=MAI_GIUDICATO, validate="full")
    ritirato = mem.semantic.get(r1["id"]).superseded_by == r2["id"]
    print("  nuovo CON source: %s · il vecchio e': %s"
          % (r2.get("status"), "RITIRATO" if ritirato else "VIVO"))
    return ritirato and r2.get("status") != "quarantined"


def main() -> int:
    import verimem
    print("verimem importato da: %s" % verimem.__file__)
    print()
    print("[1] IL CASO — 7a0fbf8ad953 contro 83407efc3a25")
    caso = il_caso()
    print("    %s" % ("OK" if caso else "NO  il fatto giudicato e' stato ritirato"))
    print()
    print("[2] IL CONTROLLO — con la source l'evoluzione passa ancora")
    ctrl = il_controllo()
    print("    %s" % ("OK" if ctrl else "NO  la guardia ha spento l'aggiornamento"))
    print()
    print("=" * 70)
    print("VERE %d su 2" % (int(caso) + int(ctrl)))
    return 0 if (caso and ctrl) else 1


if __name__ == "__main__":
    sys.exit(main())
