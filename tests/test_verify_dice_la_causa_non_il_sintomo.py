"""«sufficiency: unreadable» faceva sembrare un guasto una dipendenza mancante.

Il dossier di `trust_report` promette un'astensione esplicita. L'astensione ha
DUE livelli: il pavimento di rilevanza (CE gate), che gira ovunque, e il
giudice di SUFFICIENZA — quello che prende un fatto ON TOPIC che pero' non
risponde — che ha bisogno di un provider LLM configurato.

Senza provider `get_llm()` restituisce un `MockLLM` (con un warning, non un
errore: il codice prosegue). Chiamarlo produce un verdetto che il regex non
sa leggere, e il campo diceva `unreadable` — che si legge come «il giudice si
e' rotto», mentre la verita' e' «il giudice non c'e'».

MISURATO il 2026-08-21 su questa macchina: nessuna variabile di provider
impostata (ANTHROPIC/OPENAI/OPENROUTER/... tutte assenti), quindi questo NON e'
un caso di laboratorio — e' l'ambiente di chiunque installi verimem senza
configurare nulla.

E' la stessa distinzione che `doctor` fa gia' bene (doctor.py:428): «non ho
potuto separarle» non e' «sono zero».
"""
from __future__ import annotations

from verimem.trust_report import build_trust_report


class _MockLLM:
    """Ha il nome che `get_llm()` produce quando non c'e' un provider."""

    __name__ = "MockLLM"

    def complete(self, *a, **k):  # noqa: ANN002, ANN003, ANN201
        raise AssertionError("il giudice non deve nemmeno essere chiamato")


# il nome della CLASSE e' cio' che il codice guarda, non l'istanza
_MockLLM.__qualname__ = "MockLLM"
MockLLM = type("MockLLM", (), {"complete": _MockLLM.complete})


def test_senza_provider_il_campo_dice_no_provider(tmp_path):
    from verimem.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    rep = build_trust_report(sm, "una domanda qualsiasi", k=3, llm=MockLLM())
    assert rep["verify"]["sufficiency"] == "no_provider", (
        "il campo deve nominare la CAUSA (manca un provider LLM), non il "
        f"sintomo: ha detto {rep['verify']['sufficiency']!r}")


def test_senza_llm_resta_off(tmp_path):
    """Il CONTROLLO: nessun llm passato non e' la stessa cosa di un mock."""
    from verimem.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    rep = build_trust_report(sm, "una domanda qualsiasi", k=3, llm=None)
    assert rep["verify"]["sufficiency"] == "off", (
        "senza llm il giudice e' spento per scelta del chiamante, e 'off' e' "
        f"la parola giusta: ha detto {rep['verify']['sufficiency']!r}")
