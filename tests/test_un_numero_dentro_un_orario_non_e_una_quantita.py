"""A number inside a time of day is part of the time, not a quantity the source states.

The numeric layers read the source as a bag of numbers, and a time came apart into its pieces. Two effects,
both measured on the product's own functions on 2026-09-30:

- L4.1 asks whether each value of the claim is in the source. «Il save ha ammesso 22 fatti» against «Alle
  22:40 il save e' finito: 5 fatti ammessi» found «22» inside «22:40» and said nothing: a false number equal
  to an hour, a minute or a second of the source passed, and L4.1 is one of the layers worth the judge.
- L4.3 asks whether a value is predicated of the same subject. On a true claim with timestamps it read
  «17:35:21Z» as «21 z» and «17:39:00Z» as «0 z», and accused the claim of a swap: it happened on a real
  fact of the store (a CI note, «0 z contro 21 z»), and the minimal case below reproduces it.

The controls keep the cure honest: a number absent everywhere is still stopped, a true quantity is not
flagged, and a claim that cites the time itself finds it whole in the source.

No model: the cells at the write port inject the judge's score. Run from the root of the checkout:

    python -m pytest tests/test_un_numero_dentro_un_orario_non_e_una_quantita.py -q -p no:randomly
"""
from __future__ import annotations

import pytest

from verimem import anti_confab_gate as g
from verimem import grounding_gate as gg
from verimem.soggetto_valore import avviso_soggetto_valore
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

SALVA = "Alle 22:40 il save e' finito: 5 fatti ammessi."
JOB = ("test (macos-latest)\t2026-09-24T17:35:21Z\t2026-09-24T18:10:59Z\tsuccess\n"
       "Dal log del job 1077, step Tests: completed success 17:39:00Z -> 18:10:52Z.")


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
])
def test_i_controlli_restano_come_sono(claim: str, fonte: str, atteso: list[str]) -> None:
    assert _assenti(claim, fonte) == atteso


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


def test_alla_porta_il_claim_vero_coi_timestamp_non_e_accusato(monkeypatch) -> None:
    gate = _alla_porta(monkeypatch, "Il job 1077 e' andato in success (2026-09-24T17:35:21Z → 2026-09-24T18:10:59Z).",
                       JOB)
    assert not [w for w in gate.warnings if w.get("layer") == "L4.3"], gate.warnings
