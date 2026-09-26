"""Il doctor deve dichiarare la soglia che una scrittura subirebbe davvero.

MISURATO il 2026-09-19 su due processi puliti, stessa build:

    ambiente              doctor dichiara      write path applica
    nessun provider       40 (local)           40 (local)
    OPENAI_API_KEY=finta  70 (openai)          40 (local)

Il doctor deduce il giudice da `_autodetect_provider()`, che guarda
l'AMBIENTE: basta una chiave in una variabile, e nessuno verifica che quel
provider venga poi INIETTATO. Il write path usa il giudice effettivamente
adoperato (`fact_grounding_score_ex(grounding_llm, ...)`) e senza un LLM
iniettato ripiega sul cross-encoder locale, dove la soglia e' 40.

⇒ Su una macchina con una chiave in ambiente e un'applicazione che non la
inietta, la riga dice «admission threshold IN FORCE: 70» mentre ogni scrittura
passa a 40. E' la forma gia' in indice: «il numero DICHIARATO non e' quello
APPLICATO» — qui su una superficie che esiste apposta per dire quali regole
valgono adesso.

⚠️ Nessuna chiamata di rete parte in questo banco: la chiave e' finta e il
write path non la inietta, che e' esattamente il difetto.
"""
from __future__ import annotations

import pytest

from verimem import doctor as D

NOME = "gate"


def _riga_della_soglia(checks):
    for c in checks:
        testo = f"{c.get('name', '')} {c.get('detail', '')}"
        if "admission threshold" in testo:
            return testo
    return ""


@pytest.fixture
def _senza_llm_iniettato(monkeypatch):
    """Un provider VISIBILE nell'ambiente, nessun LLM iniettato: il caso."""
    monkeypatch.setenv("OPENAI_API_KEY", "finta-non-usata-da-nessuno")
    yield


def test_con_un_provider_in_ambiente_il_doctor_non_promette_70(
        _senza_llm_iniettato):
    """RED sul tronco: dice 70, mentre una scrittura passerebbe a 40."""
    riga = _riga_della_soglia(D.run_doctor())
    assert riga, "il controllo che nomina la soglia non c'e' piu'"
    assert "threshold in force: 40" in riga, riga


def test_e_dice_a_quale_condizione_quel_provider_conterebbe(
        _senza_llm_iniettato):
    """L'assenza ha un canale: il provider visto va NOMINATO, con la condizione.

    Tacere del provider sarebbe l'errore opposto — chi ha davvero un LLM
    iniettato leggerebbe 40 e concluderebbe che la sua chiave non serve.
    """
    riga = _riga_della_soglia(D.run_doctor())
    assert "openai" in riga, riga
    assert "70" in riga, riga


def test_senza_provider_la_riga_non_cambia(monkeypatch):
    """NON-REGRESSIONE: dove non c'era divergenza, non si muove nulla."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    riga = _riga_della_soglia(D.run_doctor())
    assert "threshold in force: 40" in riga, riga
