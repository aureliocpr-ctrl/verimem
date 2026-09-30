"""`decomponi()` splits French and Spanish coordinations, without breaking «il y a» or «et al.».

The v3 judge is trained on the units `decomponi()` produces, in four languages. Until now the splitter
knew only the Italian and English coordinators («e/ed», «and»), so a French or Spanish memory always
came out whole: the judge would have seen only whole sentences in two of its four languages.

The traps are fixed expressions that contain the coordinator: French «il y a» is «there is», not a
coordination, and «et al.» ends an author list. A noun coordination («pan y mantequilla») must stay one
claim too, as it does in Italian and English. The verb list is shared by all languages, so a French or
Spanish verb form that is also an English word («a», «son», «es») cannot enter it: a cell guards that the
English article «a» is still not a verb.

No model: the cells at the write port inject the judge's score. Run from the root of the checkout:

    python -m pytest tests/test_decomponi_spezza_francese_e_spagnolo.py -q -p no:randomly
"""
from __future__ import annotations

import pytest

from verimem import anti_confab_gate as g
from verimem import grounding_gate as gg
from verimem.atomic_claims import decomponi, ha_verbo_finito


@pytest.mark.parametrize("testo, atteso", [
    ("Claire est allée au marché et fait du vélo le dimanche.",
     ["Claire est allée au marché.", "Claire fait du vélo le dimanche."]),
    ("Lucía fue al mercado y compró pan fresco.",
     ["Lucía fue al mercado.", "Lucía compró pan fresco."]),
    ("Pablo terminó el informe y visitó a su abuela.",
     ["Pablo terminó el informe.", "Pablo visitó a su abuela."]),
    # the real «et» splits, the «y» of «il y avait» does not: without the guard the second claim was
    # «Claire avait du monde»
    ("Claire est arrivée hier et il y avait du monde.",
     ["Claire est arrivée hier.", "Il y avait du monde."]),
])
def test_la_coordinata_francese_e_spagnola_si_spezza(testo: str, atteso: list[str]) -> None:
    assert decomponi(testo) == atteso


@pytest.mark.parametrize("testo", [
    # these four stay whole also because a first piece with no finite verb is joined back
    "Il y a trois chats dans le jardin.",
    "Hier il y avait du vent sur la côte.",
    "Smith et al. ont publié l'article en mars.",
    "Pan y mantequilla son baratos en ese mercado.",
    # these two need the guard: both sides have a finite verb, and without it they gave
    # «Marc avait du soleil» and «Al. qui sont à Paris»
    "Marc est content quand il y avait du soleil.",
    "Le livre est de Smith et al. qui sont à Paris.",
])
def test_le_espressioni_fisse_restano_intere(testo: str) -> None:
    assert decomponi(testo) == [testo]


def test_l_articolo_inglese_non_diventa_un_verbo() -> None:
    # «a» is the French «has», and the English article: the shared list must not take it
    assert not ha_verbo_finito("a new bike for the trip")


# ── at the write port: the part the source does not say stops a French or Spanish memory ──────────
@pytest.mark.parametrize("memoria, fonte, debole", [
    ("Claire est allée au marché et fait du vélo le dimanche.",
     "Claire : je suis allée au marché ce matin.", "Claire fait du vélo le dimanche."),
    ("Lucía fue al mercado y compró pan fresco.",
     "Lucía: esta mañana fui al mercado.", "Lucía compró pan fresco."),
])
def test_alla_porta_la_parte_non_detta_ferma_la_memoria(monkeypatch, memoria, fonte, debole) -> None:
    visti: list[str] = []

    def giudice(_llm, _fonte, testo, **_k):
        visti.append(testo)
        return (12.0 if testo == debole else 96.0), "local"

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    monkeypatch.setenv("ENGRAM_BAND_LLM", "0")
    monkeypatch.setattr(gg, "fact_grounding_score_ex", giudice)
    gate = g.run_validation_gate(proposition=memoria, verified_by=["source-doc:x:1"], topic="t",
                                 agent=None, validate="fast", source=fonte)
    assert gate.action != "persist", (gate.action, gate.grounding_score, visti)
    claim = [w for w in gate.warnings if w.get("layer") == "L4-claim"]
    assert claim and debole in claim[0]["reason"], (visti, [w.get("layer") for w in gate.warnings])
