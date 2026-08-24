"""I quattro casi che `_entita_diverse` deve separare, misurati DALLA PORTA.

Perche' esiste: il 24/08 si e' scoperto che quattro coppie diverse arrivano
IDENTICHE alla funzione — `_entita_diverse` risponde `True` a tutte e quattro —
ma tre vogliono quel `True` e una lo vuole `False`. Qualunque cura proposta va
provata su tutte e quattro INSIEME: separarne una sola e' facile e non serve.

    magazzini   K-77 / di Ancona            TENERE entrambi   (ws5, dalla porta)
    paziente    Rossi / peso rilevato       TENERE entrambi   (04f40381)
    regimi      sotto pytest / fuori        TENERE entrambi   (43 coppie, ws6)
    rename      payments team -> Stripe     l'AVVISO deve uscire  (l3_subject_prefilter)

⚠️ SI MISURA ALLA PORTA, non sulla funzione. Il 22-24/08 la stessa domanda ha
avuto risposte OPPOSTE ai due livelli: sulla funzione una riga sembrava inerte,
dalla porta era l'unica cosa che impediva a un magazzino di cancellarne un altro.
Il livello a cui misuri decide il verdetto.

⚠️ E SI ESEGUE FUORI DA PYTEST: sotto pytest l'embedder e' uno stub su SHA-256
(`conftest`), quindi la rotta semantica non riconosce i due fatti come
contraddittori e il banco misurerebbe zero ovunque — un verde da assenza di
misura. Qui si usa la rotta lessicale `same-source`, deterministica.

    python docs/stato-reale/banchi/q_entita_quattro_casi.py
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

os.environ["ENGRAM_SUPERSEDE_SAME_SOURCE"] = "enforce"
os.environ.pop("ENGRAM_SEMANTIC_CONFLICT", None)

from verimem.anti_confab_gate import _entita_diverse  # noqa: E402
from verimem.client import Memory  # noqa: E402

CASI = [
    ("magazzini", "TENERE",
     "Il magazzino K-77 ha 4200 metri quadrati.",
     "Il magazzino di Ancona ha 2600 metri quadrati."),
    ("paziente", "TENERE",
     "Il paziente Rossi pesa 70 chilogrammi.",
     "Il peso rilevato e' di 95 chilogrammi."),
    ("regimi", "TENERE",
     "Sotto pytest la domanda in olandese ottiene score 0.7006.",
     "Fuori da pytest la domanda in olandese ottiene score 0.8509."),
    ("rename", "AVVISO",
     "The payments team migrated to Stripe in 2025.",
     "The checkout squad reverted to the legacy processor."),
]


def alla_porta(prima: str, poi: str) -> tuple[int, list[str]]:
    """Scrive i due fatti e riporta (quanti ritirati, layer del secondo write)."""
    db = Path(tempfile.mkdtemp()) / "q.db"
    mem = Memory(str(db))
    fonte = prima + "\n" + poi + "\n"
    mem.add(prima, topic="q/4", verified_by=["source-doc:q:1"],
            source=fonte, validate="full")
    ric = mem.add(poi, topic="q/4", verified_by=["source-doc:q:1"],
                  source=fonte, validate="full")
    conn = sqlite3.connect(f"file:{mem.semantic.db_path}?mode=ro", uri=True)
    try:
        riga = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()
        ritirati = int(riga[0]) if riga else 0
    finally:
        conn.close()
    layer = [str(w.get("layer")) for w in (ric.get("warnings") or [])]
    return ritirati, layer


def main() -> None:
    print(f"{'caso':11} {'vuole':7} {'_entita_diverse':16} {'ritirati':9} layer")
    print("-" * 76)
    for nome, vuole, a, b in CASI:
        ed = _entita_diverse(a, b)
        ritirati, layer = alla_porta(a, b)
        print(f"{nome:11} {vuole:7} {str(ed):16} {ritirati:<9} {layer}")
    print()
    print("COME SI LEGGE:")
    print("  TENERE  -> ritirati DEVE essere 0. Un ritiro qui cancella un fatto vero.")
    print("  AVVISO  -> ritirati 0 va bene, ma il layer NON deve essere vuoto:")
    print("             un soggetto rinominato che esce muto e' il vettore che")
    print("             `test_l3_subject_prefilter` esiste per chiudere.")
    print("  Tutte e quattro arrivano a `_entita_diverse` con la stessa risposta:")
    print("  una cura che ne separa una sola non ha separato niente.")


if __name__ == "__main__":
    main()
