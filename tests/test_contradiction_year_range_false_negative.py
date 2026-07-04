r"""RED test (sorella-4, 2026-06-03) — FALSE NEGATIVE nel contradiction detector
quando un valore NON-anno cade nel range 1900-2099.

BUCO (verificato leggendo il codice live, non assunto):
  engram/contradiction.py:115  ``_YEAR_RE = r"\b(?:19|20)\d{2}\b"`` classifica
  QUALSIASI intero a 4 cifre in [1900, 2099] come "anno", indipendentemente dal
  fatto che sia davvero una data.
  engram/contradiction.py:134-139  ``_classify_numbers`` sposta quel numero nel
  bucket ``year`` e lo RIMUOVE da ``other``.
  engram/contradiction.py:172-187  ``_values_clash`` confronta i numeri SOLO
  all'interno dello stesso bucket (year vs year, percent vs percent, other vs
  other). Quando un lato ha un valore in [1900,2099] (→ bucket ``year``) e
  l'altro un valore fuori range (→ bucket ``other``), i bucket sono DISGIUNTI:
  nessun confronto avviene → nessun clash → ``_values_clash`` ritorna False.

PERCHÉ È REALE: 1900-2099 è un range pienissimo di quantità non-temporali —
conteggi corpus (es. "2024 facts"), latenze ms, porte, token count, numeri di
riga, dimensioni. Due fatti sullo stesso topic che dichiarano "2024 X" vs
"8000 X" sono palesemente contraddittori ma il detector li IGNORA. La prova:
lo STESSO confronto col fallback posizionale (senza testo) ritorna True →
è la classificazione type-aware a introdurre il falso negativo.

Hermetic: funzioni pure + Fact in memoria, ZERO DB reale ~/.engram, ZERO
embedding (``_cosine`` monkeypatchato). NON tocca il sorgente (lo coordina il capo).
"""
from __future__ import annotations

import pytest

from engram import contradiction
from engram.contradiction import _values_clash, detect_numeric_clashes
from engram.semantic import Fact


def test_values_clash_year_range_vs_out_of_range_count() -> None:
    """Unit: 2024 (count) vs 8000 (count) DEVE essere un clash.

    RED: 2024 finisce nel bucket 'year', 8000 in 'other' → bucket disgiunti →
    nessun confronto → ritorna False.
    """
    clash = _values_clash(
        [2024.0], [8000.0],
        tolerance=0.05,
        text_a="the corpus has 2024 facts",
        text_b="the corpus has 8000 facts",
    )
    # Sanity: il fallback posizionale (senza testo) lo vede correttamente.
    assert _values_clash([2024.0], [8000.0], tolerance=0.05) is True
    assert clash is True, (
        "FALSE NEGATIVE: 2024 (count) classificato come 'anno' e mai "
        "confrontato con 8000 (other) → contraddizione numerica reale persa "
        "(contradiction.py:115/134-139/172-187)"
    )


def test_detect_numeric_clashes_misses_year_range_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Path pubblico: due fatti same-topic '2024 facts' vs '8000 facts'.

    Isoliamo la logica numerica forzando alta similarità (``_cosine``→1.0),
    così l'unico discriminante è il numeric-clash. Atteso: 1 contraddizione.
    RED: oggi ne rileva 0 (il bucket-year ingoia il 2024).
    """
    monkeypatch.setattr(contradiction, "_cosine", lambda a, b: 1.0)

    fa = Fact(id="fa", proposition="the corpus has 2024 facts", topic="stats/corpus")
    fb = Fact(id="fb", proposition="the corpus has 8000 facts", topic="stats/corpus")

    found = detect_numeric_clashes([fa, fb], similarity_threshold=0.75)
    kinds = [c.kind for c in found]
    assert len(found) == 1 and kinds == ["numeric_clash"], (
        "BUCO contraddizione persa: '2024 facts' vs '8000 facts' (stesso topic, "
        f"sim=1.0) NON rilevato come numeric_clash (found={kinds}); causa = "
        "_YEAR_RE che cattura 2024 come anno e lo isola dal confronto con 8000"
    )
