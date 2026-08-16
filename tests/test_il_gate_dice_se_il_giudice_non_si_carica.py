"""Il ramo «il giudice c'è ma non si carica» non era esercitato da nessuno.

Il gate ha due modi di dire che non ha verificato, e sono testi diversi perché
sono cause diverse (`anti_confab_gate.py:1357` e `:1366`)::

    cartella del modello ASSENTE
      «source provided but no grounding judge is available — entailment NOT verified»
    cartella del modello ESISTENTE MA VUOTA
      «source provided but the grounding judge failed to load — entailment NOT verified»

Il primo caso ha il suo presidio
(`test_la_ricevuta_deve_dire_se_il_moat_ha_girato.py`). **Il secondo non
l'aveva**, e non è teorico: è il vicolo cieco misurato il 16/08 — un download
interrotto (rete caduta, Ctrl-C, sha256 che non torna) lascia la cartella
vuota, `local_ce_available()` risponde **True**, e `verimem warmup` dice
«✓ moat gate model already installed» senza scaricare nulla.

⇒ In quello stato il gate **crede** di avere il giudice. Ciò che salva l'utente
è che quando prova davvero scopre la verità e la **dichiara**, e che
`local_ce_available()` si corregge a `False` da lì in poi. Se quel ramo si
rompesse, il vicolo cieco diventerebbe **silenzioso** — un fatto non verificato
entrerebbe senza che nessuno lo dica, che è esattamente il danno che il prodotto
esiste per impedire.

⚠️ Costo dichiarato: il test paga il tentativo di caricamento vero (~35 s
misurati). Si potrebbe simulare il fallimento in un millisecondo, ma allora si
misurerebbe il finto e non il percorso che l'utente incontra.
"""
from __future__ import annotations

import pytest

from verimem.local_grounding import local_ce_available, reset_local_judge


@pytest.fixture
def cartella_del_modello_vuota(tmp_path, monkeypatch):
    """Un download interrotto: la cartella c'è, dentro non c'è niente."""
    vuota = tmp_path / "local_gate_ce_v2"
    vuota.mkdir()
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(vuota))
    reset_local_judge()          # non ereditare un giudice già caricato
    yield vuota
    reset_local_judge()          # non lasciarne uno rotto a chi viene dopo


def _ricevuta(claim: str, fonte: str):
    from verimem import Memory
    return Memory().add(claim, topic="prova/giudice-che-non-carica",
                        source=fonte)


def test_una_cartella_vuota_si_annuncia_come_giudice_disponibile(
        cartella_del_modello_vuota):
    """⚠️ LA TRAPPOLA, prima della cura che non c'è: qui sta la ragione per cui
    il caso è insidioso. `local_ce_available` è documentata «cheap by design:
    it NEVER loads the model», quindi non può accorgersi che la cartella è
    vuota — e risponde di sì."""
    assert local_ce_available() is True, (
        "se questo diventa False la trappola non esiste più e il resto del "
        "file misura un caso che non capita: rileggere, non cancellare")


def test_il_gate_dichiara_che_il_giudice_NON_si_e_caricato(
        cartella_del_modello_vuota):
    r = _ricevuta("Il magazzino di Verona contiene 900 pallet.",
                  "Il magazzino di Verona contiene 480 pallet.")
    d = r if isinstance(r, dict) else getattr(r, "__dict__", {})
    motivi = [w.get("reason", "") for w in (d.get("warnings") or [])]

    assert any("failed to load" in m for m in motivi), (
        f"il claim è entrato senza che la ricevuta dica che il giudice non si "
        f"è caricato. Avvisi presenti: {motivi}")
    assert any("NOT verified" in m for m in motivi), (
        f"manca la parte che l'utente deve leggere — che l'entailment non è "
        f"stato verificato. Avvisi presenti: {motivi}")


def test_dopo_il_tentativo_il_prodotto_smette_di_dire_che_il_giudice_c_e(
        cartella_del_modello_vuota):
    """⚠️ L'AUTOCORREZIONE, ed è la parte che limita il danno: dopo un
    fallimento il prodotto non sostiene più di avere un giudice. Senza questa,
    ogni scrittura successiva ripagherebbe il tentativo e la trappola durerebbe
    per sempre."""
    _ricevuta("Il magazzino di Verona contiene 900 pallet.",
              "Il magazzino di Verona contiene 480 pallet.")
    assert local_ce_available() is False, (
        "dopo un caricamento fallito `local_ce_available` risponde ancora "
        "True: il prodotto continua a dire di avere un giudice che non ha")


def test_il_testo_del_caso_assente_resta_diverso(tmp_path, monkeypatch):
    """⚠️ POPOLAZIONE OPPOSTA — i due messaggi devono restare DUE. Se qualcuno
    li unificasse in una formula sola, questo cade: distinguere «non c'è» da
    «c'è e non si carica» è ciò che dice all'utente se deve scaricare il
    modello o ripararne uno mezzo scaricato."""
    assente = tmp_path / "mai_scaricata"
    monkeypatch.setenv("ENGRAM_LOCAL_GATE_MODEL", str(assente))
    reset_local_judge()
    try:
        assert local_ce_available() is False, (
            "una cartella che non esiste non deve annunciarsi disponibile")
        r = _ricevuta("Il magazzino di Verona contiene 900 pallet.",
                      "Il magazzino di Verona contiene 480 pallet.")
        d = r if isinstance(r, dict) else getattr(r, "__dict__", {})
        motivi = [w.get("reason", "") for w in (d.get("warnings") or [])]
        assert any("no grounding judge is available" in m for m in motivi), (
            f"il caso «cartella assente» non usa più il suo testo: {motivi}")
        assert not any("failed to load" in m for m in motivi), (
            f"«failed to load» è comparso dove il modello non c'è proprio: i "
            f"due casi si sono confusi. Avvisi: {motivi}")
    finally:
        reset_local_judge()
