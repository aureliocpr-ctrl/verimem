"""A number inside a time of day is part of the time, not a quantity the source states.

The numeric layers read the source as a bag of numbers, and a time came apart into its pieces. Measured on
the product's own functions on 2026-09-30:

- L4.1 asks whether each value of the claim is in the source. «Il save ha ammesso 22 fatti» against «Alle
  22:40 il save e' finito: 5 fatti ammessi» found «22» inside «22:40» and said nothing: a false number equal
  to an hour, a minute or a second of the source passed, and L4.1 is one of the layers worth the judge.
- L4.1 also accused a TRUE claim: «partito alle 17:35» against «2026-09-24T17:35:21Z» gave ['17'], because
  the hour glued to the «T» was not read at all.
- L4.3 asks whether a value is predicated of the same subject. On a true claim with timestamps it read
  «17:35:21Z» as «21 z» and «17:39:00Z» as «0 z», and accused the claim of a swap: it happened on a real
  fact of the store (a CI note, «0 z contro 21 z»), and the minimal case below reproduces it.
- The conflict detector took the same «z» for a unit: two timestamps of one job that differ only in the
  seconds came out as a conflict on the seconds alone.

The cure reads a time whole, on a path of its own (`quantity_match.orari`), the way a date is. What the
piecewise reading did well stays: a wrong time is still stopped, now named as written («22:45», not
«45»), compared at the precision the claim writes (a claim that says «17:35» does not state seconds).

The controls keep the cure honest: a number absent everywhere is still stopped, a true quantity is not
flagged, a claim that cites the time itself finds it whole in the source, a time range keeps both ends,
and a claim with a time still counts as specific for the evidence requirement.

No model: the cells at the write port inject the judge's score. Run from the root of the checkout:

    python -m pytest tests/test_un_numero_dentro_un_orario_non_e_una_quantita.py -q -p no:randomly
"""
from __future__ import annotations

import pytest

from verimem import anti_confab_gate as g
from verimem import grounding_gate as gg
from verimem.evidence_requirement import is_specific_claim
from verimem.quantity_match import extract_quantities, numeric_conflict
from verimem.soggetto_valore import avviso_soggetto_valore
from verimem.valore_non_nella_fonte import valori_non_nella_fonte
from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto

SALVA = "Alle 22:40 il save e' finito: 5 fatti ammessi."
JOB = ("test (macos-latest)\t2026-09-24T17:35:21Z\t2026-09-24T18:10:59Z\tsuccess\n"
       "Dal log del job 1077, step Tests: completed success 17:39:00Z -> 18:10:52Z.")
PARTITO = "Il job e' partito il 2026-09-24T17:35:21Z."


def _assenti(claim: str, fonte: str) -> list[str]:
    return [v.come_scritto() for v in valori_non_nella_fonte(claim, fonte)]


@pytest.mark.parametrize("claim, fonte, numero", [
    ("Il save ha ammesso 22 fatti.", SALVA, "22"),                       # l'ora
    ("Il save ha ammesso 40 fatti.", SALVA, "40"),                       # i minuti
    ("The run took 21 minutes.", "Started 2026-09-24T17:35:21Z, finished 17:52:03Z.", "21"),   # i secondi
])
def test_un_numero_che_la_fonte_ha_solo_dentro_un_orario_e_assente(claim: str, fonte: str, numero: str) -> None:
    assert numero in _assenti(claim, fonte)


@pytest.mark.parametrize("claim, fonte, atteso", [
    ("Il save ha ammesso 23 fatti.", SALVA, ["23"]),       # assente ovunque: resta fermato
    ("Il save ha ammesso 5 fatti.", SALVA, []),            # vero
    ("Il save e' finito alle 22:40.", SALVA, []),          # l'orario citato intero c'e'
    ("La riunione finisce alle 12:30.", "La riunione va dalle 10:00-12:30.", []),   # un intervallo ha due capi
    ("Il save e' finito alle 16:06.", "Ore 16:06: il save e' finito.", []),         # i due punti dopo sono punteggiatura
])
def test_i_controlli_restano_come_sono(claim: str, fonte: str, atteso: list[str]) -> None:
    assert _assenti(claim, fonte) == atteso


@pytest.mark.parametrize("claim, fonte", [
    ("Il save e' finito alle 22:45.", SALVA),              # un altro minuto
    ("Il job e' partito alle 17:36.", PARTITO),            # 17:35:21 non si scrive 17:36, ne' troncato ne' arrotondato
])
def test_un_orario_sbagliato_resta_fermato(claim: str, fonte: str) -> None:
    assert _assenti(claim, fonte)


@pytest.mark.parametrize("claim, fonte, atteso", [
    ("Il save e' finito alle 22:45.", SALVA, ["22:45"]),               # la ricevuta nomina l'orario, non il 45
    ("Il job e' partito alle 17:35.", PARTITO, []),                    # l'ora di un timestamp citata al minuto
    ("Il job e' partito alle 17:36.", PARTITO, ["17:36"]),
    ("Il save e' finito alle 22:40:15.", SALVA, ["22:40:15"]),         # i secondi li aggiunge il claim
    ("The meeting ends at 5:00 PM.", "The meeting ends at 17:00.", []),
])
def test_un_orario_si_confronta_intero_alla_precisione_che_il_claim_scrive(
        claim: str, fonte: str, atteso: list[str]) -> None:
    assert _assenti(claim, fonte) == atteso


@pytest.mark.parametrize("claim, fonte", [
    ("Il deploy ha rilasciato 10 pacchetti.", "Alle 10:30 il job del backup e' ripartito."),
    ("The deploy shipped 10 packages.", "At 10:30 the backup job restarted."),
])
def test_un_numero_che_la_fonte_ha_solo_come_ora_lo_accusa_un_layer_solo(claim: str, fonte: str) -> None:
    # L4.1 lo dice assente; L4.2, che cercava il numero nel testo, trovava l'ora di «10:30» e lo attaccava
    # alle parole dell'orario: due avvisi sullo stesso numero, e il secondo sbagliato.
    assert _assenti(claim, fonte) == ["10"]
    assert valori_riusati_da_altro_contesto(claim, fonte) == []


def test_un_punteggio_riscritto_in_due_numeri_resta_accusato() -> None:
    # IL PREZZO DICHIARATO, qui e non solo nella richiesta: «21:15» ha la forma di un orario e si legge come un
    # valore solo, ma in un punteggio i pezzi sono punti. Chi lo riscrive «21 a 15» viene accusato: un'accusa
    # sbagliata si legge nella ricevuta, un perdono sbagliato no, e perdonare chi cita tutti e due i pezzi
    # riaprirebbe il buco a «22 fatti e 40 errori». Se un giorno si cura, questa cella dice che cosa cambia.
    assert _assenti("La partita e' finita 21 a 15.", "Set finito 21:15.") == ["15", "21"]


def test_la_ricevuta_scrive_il_numero_come_lo_scrive_il_claim() -> None:
    assert _assenti("Alle 22:40 il save ha ammesso 22.0 fatti.", "Il save ha ammesso 5 fatti.") == ["22.0", "22:40"]


@pytest.mark.parametrize("testo, atteso", [
    (SALVA, {("fatto", 5.0)}),
    (JOB, {("", 1077.0)}),
])
def test_i_pezzi_di_un_orario_non_sono_quantita(testo: str, atteso: set) -> None:
    assert extract_quantities(testo, come_fonte=True) == atteso


def test_due_timestamp_non_litigano_sui_soli_secondi() -> None:
    assert numeric_conflict("Il job 1077 e' finito alle 18:10:52Z.",
                            "Il job 1077 e' finito alle 18:10:59Z.") is None


def test_un_claim_con_un_orario_resta_specifico() -> None:
    assert is_specific_claim("Il save e' finito alle 22:40.")


@pytest.mark.parametrize("claim", [
    "Il job 1077 e' andato in success (2026-09-24T17:35:21Z → 2026-09-24T18:10:59Z).",
    "The job 1077 succeeded (2026-09-24T17:35:21Z → 2026-09-24T18:10:59Z).",
])
def test_un_orario_non_e_un_valore_attaccato_a_un_soggetto(claim: str) -> None:
    assert avviso_soggetto_valore(claim, JOB) is None


def _alla_porta(monkeypatch, claim: str, fonte: str):
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    monkeypatch.setenv("ENGRAM_BAND_LLM", "0")
    monkeypatch.setattr(gg, "fact_grounding_score_ex", lambda *_a, **_k: (96.0, "local"))
    return g.run_validation_gate(proposition=claim, verified_by=["source-doc:x:1"], topic="t", agent=None,
                                 validate="fast", source=fonte)


def test_alla_porta_il_numero_falso_uguale_a_un_ora_si_ferma(monkeypatch) -> None:
    gate = _alla_porta(monkeypatch, "Il save ha ammesso 22 fatti.", SALVA)
    l41 = [w for w in gate.warnings if w.get("layer") == "L4.1"]
    assert l41 and "22" in l41[0]["reason"], [w.get("layer") for w in gate.warnings]
    assert gate.action != "persist", gate.action


def test_alla_porta_l_orario_sbagliato_si_ferma_e_si_nomina(monkeypatch) -> None:
    gate = _alla_porta(monkeypatch, "Il save e' finito alle 22:45.", SALVA)
    l41 = [w for w in gate.warnings if w.get("layer") == "L4.1"]
    assert l41 and "22:45" in l41[0]["reason"], [(w.get("layer"), w.get("reason")) for w in gate.warnings]
    assert gate.action != "persist", gate.action


def test_alla_porta_il_claim_vero_coi_timestamp_non_e_accusato(monkeypatch) -> None:
    gate = _alla_porta(monkeypatch, "Il job 1077 e' andato in success (2026-09-24T17:35:21Z → 2026-09-24T18:10:59Z).",
                       JOB)
    assert not [w for w in gate.warnings if w.get("layer") == "L4.3"], gate.warnings


def test_alla_porta_l_ora_di_un_timestamp_citata_al_minuto_passa(monkeypatch) -> None:
    gate = _alla_porta(monkeypatch, "Il job e' partito alle 17:35.", PARTITO)
    assert not [w for w in gate.warnings if w.get("layer") == "L4.1"], gate.warnings
