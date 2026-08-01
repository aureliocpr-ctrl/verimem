"""Un `MockLLM` non è un giudice, e impediva al moat di girare.

LA CAUSA VERA dietro il numero che gira da giorni: **152 fatti giudicati su
6572**, e su questo canale una `hippo_remember` con `source` che risponde
`grounding_score: None` mentre `judge_state()` dice `ready` e
`local_ce_available()` dice `True`.

Il gate decide cosi' (grounding_gate.py:380), e il commento sopra dichiara
l'intenzione giusta::

    # The moat runs off the free local CE when it's the configured backend OR
    # when no llm judge was injected (2026-07-18): a brand-new user with no llm
    # still gets the entailment moat ... instead of the gate fail-opening.
    if backend == "local" or (backend == "claude" and llm is None):
        r = try_local_score(source, fact, focus_budget=focus_budget)

Ma quando non c'e' nessun provider configurato, `verimem.llm` non passa `None`:
costruisce un **`MockLLM()`** e lo logga (`llm_using_mock reason='no provider
available'`). E `MockLLM() is None` e' **False**. Misurato::

    backend di default: claude
    MockLLM() is None : False
    => usa il CE locale: False      <- il caso reale
    => con llm=None    : True      <- quello che il commento voleva

Quindi il ramo locale non viene MAI preso, il gate va avanti e chiede il
punteggio al mock — che non giudica niente. L'utente «brand-new with no llm»,
cioe' proprio quello che la riga esisteva per proteggere, e' l'unico che il moat
non copre.

E' un caso particolare della classe curata tutta questa settimana: **una
condizione che sembra dire «non c'e' un giudice» e in realta' dice «l'oggetto e'
None»**. Il mock passa il controllo perche' e' un oggetto, non perche' sappia
giudicare.

LA CURA non e' una blocklist ne' un'euristica sul nome: `MockLLM` e' una classe
di questo prodotto, e `isinstance` e' la domanda esatta — «questo e' il
segnaposto che costruiamo quando non c'e' niente?». Un llm vero continua a
vincere sul backend `claude`, esattamente come prima.
"""
from __future__ import annotations

import pytest

from verimem.llm import MockLLM


def test_un_mock_non_conta_come_giudice_iniettato():
    """Il cuore: la domanda che il gate DEVE porsi."""
    from verimem.grounding_gate import _e_un_giudice_vero
    assert _e_un_giudice_vero(None) is False
    assert _e_un_giudice_vero(MockLLM()) is False, (
        "un MockLLM e' stato contato come giudice iniettato: e' il segnaposto "
        "che il prodotto costruisce quando NON c'e' nessun provider, e "
        "contarlo impedisce al CE locale di girare")

    class _LlmVero:
        def complete(self, *a, **k):
            # `complete` restituisce un oggetto con `.text`, non una stringa:
            # il gate legge `getattr(resp, "text", "")`. La prima stesura
            # tornava "80" e il gate lo leggeva come risposta VUOTA.
            return type("R", (), {"text": "80"})()

    assert _e_un_giudice_vero(_LlmVero()) is True, (
        "un llm vero non e' piu' riconosciuto: sul backend `claude` deve "
        "continuare a vincere sul CE locale, come prima")


def test_un_PROXY_che_avvolge_il_mock_non_e_un_giudice():
    """La causa VERA, trovata tracciando invece di dedurre.

    La prima stesura di questa cura guardava solo `MockLLM` e NON bastava: sul
    canale MCP l'oggetto iniettato e' un `LazyLLM`, un proxy trasparente che
    costruisce il backend al primo accesso. La traccia::

        [gate] fact_grounding_score_ex  llm=LazyLLM
        [gate] -> NoGroundingJudge: the grounding judge returned no score

    con `try_local_score` mai chiamato. Il docstring di `LazyLLM` dichiara la
    condizione che lo rende sicuro — «No isinstance checks are done on the llm
    in the wake/sleep hot paths (verified)» — e il write gate NON e' fra quei
    path: li' `llm is None` e' proprio un controllo di identita', e il proxy lo
    scavalca.

    Misurato sul canale MCP, stessa scrittura prima e dopo::

        prima: grounding_score None   · moat «could not judge»
        dopo : grounding_score 99.93  · moat «judged 99.9 — the source entails»
    """
    from verimem.grounding_gate import _e_un_giudice_vero
    from verimem.llm import LazyLLM
    assert _e_un_giudice_vero(LazyLLM()) is False, (
        "un LazyLLM che risolve a un mock (nessun provider configurato) e' "
        "stato contato come giudice: e' il caso REALE del canale MCP, e "
        "impediva al CE locale di girare")


def test_col_mock_il_moat_USA_il_CE_locale(monkeypatch):
    """Il comportamento, non solo il predicato: con un mock al posto del
    provider, il punteggio deve venire dal giudice locale — che e' cio' che il
    commento del 2026-07-18 prometteva a «a brand-new user with no llm»."""
    import verimem.grounding_gate as gg

    chiamato: list[str] = []

    def _finto_locale(source, fact, *, focus_budget=None):
        chiamato.append(fact)
        return 97.5, 40.0

    monkeypatch.setattr("verimem.local_grounding.try_local_score", _finto_locale)
    punteggio, backend = gg.fact_grounding_score_ex(
        MockLLM(),
        "La politica prevede il rimborso entro 7 giorni lavorativi.",
        "Il rimborso avviene entro 7 giorni lavorativi.")
    assert chiamato, (
        "il CE locale non e' stato interpellato: col mock il gate stava "
        "chiedendo il punteggio a un oggetto che non giudica")
    assert backend == "local", backend
    assert punteggio == 97.5


def test_un_llm_VERO_continua_a_vincere(monkeypatch):
    """Controprova: se la cura facesse ricadere TUTTO sul CE locale, un utente
    che ha configurato un llm perderebbe il giudice migliore senza saperlo.

    Si verifica che il ramo locale NON venga preso, non che l'llm finto sappia
    rispondere: il formato che `_SCORE_RE` accetta e' un dettaglio del prompt,
    e simularlo qui misurerebbe il mio finto invece del gate. Il segnale giusto
    e' `try_local_score` che resta non chiamato."""
    import verimem.grounding_gate as gg

    chiamato: list[str] = []

    def _spia(source, fact, *, focus_budget=None):
        chiamato.append(fact)
        return 97.5, 40.0

    class _LlmVero:
        def complete(self, *a, **k):
            return type("R", (), {"text": "88"})()

    monkeypatch.setattr("verimem.local_grounding.try_local_score", _spia)
    try:
        gg.fact_grounding_score_ex(
            _LlmVero(),
            "La politica prevede il rimborso entro 7 giorni lavorativi.",
            "Il rimborso avviene entro 7 giorni lavorativi.")
    except gg.NoGroundingJudge:
        pass  # l'llm finto non risponde nel formato atteso: irrilevante qui
    assert not chiamato, (
        "col un llm VERO iniettato il gate ha interpellato il CE locale: la "
        "cura ha fatto ricadere sul giudice di riserva chi ne aveva uno "
        "migliore configurato")
