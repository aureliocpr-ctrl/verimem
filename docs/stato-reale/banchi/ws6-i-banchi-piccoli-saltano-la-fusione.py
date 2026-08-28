"""Sotto 50 fatti la fusione PPR+BM25 non parte: i nostri banchi misurano un
percorso di codice diverso da quello che gira in esercizio.

`semantic.py` salta la fusione quando il corpus e' sotto `ENGRAM_PPR_FUSION_FLOOR`
(default 50) e annota `fusion: skipped_small_corpus`. I nostri store temporanei
hanno tipicamente 2-15 fatti; il corpus vero ne ha oltre 15000.

A/B a un fattore: stesso store, stessa query, floor 50 (fusione saltata) contro
floor 0 (fusione forzata).

⛔ IL CONTROLLO CHE RENDE INTERPRETABILE LO ZERO: si verifica che la fusione sia
ACCESA prima di concludere che non cambia nulla. Senza, "ordine identico"
potrebbe voler dire "non e' mai partita".

LIMITE DICHIARATO: le query qui sono FACILI (il coseno trova gia' il fatto
giusto). La fusione esiste per i casi multi-hop e per il token esatto in un
testo lontano dalla query, e questo banco NON li contiene: prova che sui facili
la differenza e' zero, non che non esista.

    HIPPO_DATA_DIR=$(mktemp -d) python docs/stato-reale/banchi/ws6-i-banchi-piccoli-saltano-la-fusione.py
"""
import os

from verimem.config import CONFIG

assert "Temp" in str(CONFIG.semantic_db) or "tmp" in str(CONFIG.semantic_db), (
    "NON ISOLATO - questo banco scrive. Serve HIPPO_DATA_DIR su una tempdir.")

from verimem import Memory  # noqa: E402
from verimem.semantic import _ppr_fusion_enabled  # noqa: E402

FATTI = [
    ("Il codice di collaudo K-77 e' stato assegnato al lotto di marzo.", "banco/fusion/a"),
    ("Le sedi operative sono Verona, Trento e Bolzano.", "banco/fusion/b"),
    ("La potenza installata dell'impianto principale e' di 320 kW.", "banco/fusion/c"),
    ("Il magazzino centrale contiene 480 pallet suddivisi per reparto.", "banco/fusion/d"),
    ("Il collaudo finale e' previsto per il mese di marzo.", "banco/fusion/e"),
]
QUERY = ["Qual e' il codice K-77?", "Quando e' previsto il collaudo?"]


def _ordine(floor: int, query: str) -> list[str]:
    os.environ["ENGRAM_PPR_FUSION_FLOOR"] = str(floor)
    return [(x.get("proposition") or x.get("text") or str(x))[:54]
            for x in Memory().recall(query, k=3)]


def main() -> None:
    print(f"la fusione e' accesa? _ppr_fusion_enabled() -> {_ppr_fusion_enabled()}")
    if not _ppr_fusion_enabled():
        print("  ⛔ SPENTA: l'A/B qui sotto non misurerebbe niente. Fermo.")
        return

    m = Memory()
    for proposizione, topic in FATTI:
        m.add(proposizione, topic=topic, source=proposizione)
    print(f"corpus: {len(FATTI)} fatti (sotto il floor di 50)\n")

    for query in QUERY:
        saltata = _ordine(50, query)
        forzata = _ordine(0, query)
        print(f"=== {query}")
        for i in range(max(len(saltata), len(forzata))):
            a = saltata[i] if i < len(saltata) else "-"
            b = forzata[i] if i < len(forzata) else "-"
            print(f"  {'  ' if a == b else '≠ '}{i + 1}. floor=50: {a}")
            print(f"       floor=0 : {b}")
        print(f"  -> ordine identico? {saltata == forzata}\n")


if __name__ == "__main__":
    main()
