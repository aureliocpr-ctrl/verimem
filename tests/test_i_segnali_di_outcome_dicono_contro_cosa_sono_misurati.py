"""I segnali di outcome dicono CONTRO COSA sono misurati, o non si possono leggere.

⚠️ **TROVATO USANDO IL PRODOTTO**, chiamando il tool MCP `hippo_outcome_patterns`
sul corpus vero (459 episodi) — non leggendo il codice. Il tool si presenta::

    FORGIA #325 — Round 42: tokens correlated with success vs failure.

e ha restituito **30 `positive_signals`, tutti con `success_rate` 1.0**, e
**`negative_signals` VUOTO**. La ragione sta nel corpus, non nel codice::

    success   451
    failure     8      (1.7%)

⇒ 🔑 **Non c'e' un «vs».** Con 8 failure su 459, un token deve comparire quasi
solo dentro quegli 8 per scendere sotto `negative_threshold=0.3`: i negativi
sono **strutturalmente** impossibili, e i positivi a 1.0 non discriminano —
sono **i token piu' frequenti**, non i token correlati al successo.

📌 **Il payload diceva `n_episodes_scanned: 459` e nient'altro.** Chi legge non
ha modo di sapere che il denominatore del confronto e' 8: legge «correlated with
success» e crede a una correlazione che non e' stata misurata contro nulla.
E' la forma gia' registrata in casa — *una misura che non c'e' si legge come
perfetta* — nella variante piu' scivolosa: **la misura c'e', ma manca cio' che
la rende interpretabile.**

⚖️ **COSA QUESTA CURA NON FA**: non cambia **quali** token escono, ne' le
soglie, ne' l'ordine. Aggiunge al payload i due conteggi con cui il lettore
giudica da se'. Se cambiasse la selezione servirebbe una misura appaiata sui
segnali, e sarebbe un altro voto.

🔴 **UN SECONDO REPERTO, RIPORTATO E NON CURATO QUI**: fra i 30 segnali ci sono
**«per» (41), «con» (37), «non» (25)** — parole funzionali italiane, in un tool
che dichiara *«Stopwords excluded»*: la `_STOP` di `outcome_pattern.py` ha 11
voci inglesi e zero italiane. Curarlo **cambierebbe quali token escono**, quindi
va con la sua misura e il suo voto: una cura atomica alla volta.
"""

from __future__ import annotations

from types import SimpleNamespace

from verimem.outcome_pattern import find_outcome_patterns


def _ep(testo: str, esito: str) -> SimpleNamespace:
    """La funzione legge con `getattr`, quindi vuole oggetti e non dict.

    ⚠️ Passandole dei dict risponde **zero segnali senza un errore** — ci sono
    caduta io alle 19:14 prima di guardare il chiamante (`mcp_server.py:9602`,
    che passa `a.memory.all(...)`, cioe' oggetti). Lo scrivo qui perche' il
    prossimo che scrive un banco su questa funzione non ci ricada.
    """
    return SimpleNamespace(task_text=testo, outcome=esito)


def test_il_payload_dice_quanti_erano_i_successi_e_quanti_i_fallimenti() -> None:
    """Il cuore: senza i due conteggi, «correlated with success» non e'
    leggibile."""
    eps = [_ep("alfa beta gamma", "success")] * 9 + [_ep("alfa delta", "failure")]
    out = find_outcome_patterns(eps, min_occurrence=3)
    assert out["n_success"] == 9
    assert out["n_failure"] == 1


def test_il_conteggio_degli_episodi_non_cambia() -> None:
    """Il campo che c'era resta: la cura aggiunge, non sostituisce."""
    eps = [_ep("alfa beta", "success")] * 4
    assert find_outcome_patterns(eps)["n_episodes_scanned"] == 4


def test_gli_esiti_diversi_da_success_e_failure_non_spariscono() -> None:
    """`n_success + n_failure` puo' essere minore del totale: un esito terzo
    non va contato come fallimento solo perche' non e' un successo — leggere
    l'assenza come un valore e' un errore gia' pagato in casa."""
    eps = [_ep("alfa beta", "success")] * 3 + [_ep("alfa gamma", "partial")] * 2
    out = find_outcome_patterns(eps)
    assert (out["n_success"], out["n_failure"]) == (3, 0)
    assert out["n_episodes_scanned"] == 5


# ── I PRESIDI: la selezione dei token NON deve muoversi

def test_presidio_i_segnali_positivi_non_cambiano() -> None:
    eps = [_ep("alfa beta", "success")] * 5
    out = find_outcome_patterns(eps, min_occurrence=3)
    tok = sorted(e["token"] for e in out["positive_signals"])
    assert tok == ["alfa", "beta"]
    assert all(e["success_rate"] == 1.0 for e in out["positive_signals"])


def test_presidio_i_segnali_negativi_restano_selezionati_come_prima() -> None:
    """Un token che sta solo nei fallimenti resta negativo."""
    eps = [_ep("alfa buono", "success")] * 7 + [_ep("alfa rotto", "failure")] * 3
    out = find_outcome_patterns(eps, min_occurrence=3)
    assert [e["token"] for e in out["negative_signals"]] == ["rotto"]


def test_presidio_la_soglia_di_occorrenza_vale_ancora() -> None:
    eps = [_ep("alfa beta", "success")] * 2
    assert find_outcome_patterns(eps, min_occurrence=3)["positive_signals"] == []
