"""T206 — un fatto PERSONALE con «described» non è una dichiarazione di documentazione.

Dalla linea di base del pilota LoCoMo (23/09, codice c524fa07): la memoria p025
«Maria described a view of a waterfall and bridge as awesome and
breath-taking» è sostenuta dal turno citato — le etichettatrici sono d'accordo —
e il giudice la ammette a 98,38. Finisce in QUARANTENA per lo strato lessicale
L1.14, «Documentation claim … lacks docs evidence». È una memoria vera che
l'utente non riceve.

La causa, letta nel codice: `l1_documentation_detector._DOC_PATTERN` scatta
sulla PAROLA (documented, explained, described e le forme italiane) senza
guardare come è usata. I veri positivi che i test di maggio proteggono sono
tutti PARTICIPI SENZA OGGETTO («Module documented in latest commit», «Behavior
described in docs», «Comportamento descritto»). I falsi positivi delle
conversazioni sono VERBI ATTIVI CON UN OGGETTO: «described a view», «explained
that …», «ha descritto il panorama».

I LIVELLI, dichiarati:
- le celle rosse passano dalla PORTA (`Memory.add`), perché è lì che l'utente
  perde il fatto; il giudice è iniettato a punteggio alto, nessun modello da
  caricare, così il moat ammette e l'unica cosa che può fermare la scrittura è
  uno strato lessicale — la variabile è una sola;
- una cella rossa sta alla FUNZIONE, per nominare la parola che scatta;
- i negativi (la dichiarazione di documentazione vera resta fermata) e il
  controllo positivo (con la prova `docs:` lo strato tace) passano oggi e
  devono passare dopo la cura: sono ciò che la cura non deve muovere.
"""
from __future__ import annotations

import os

import pytest

# encoder in-process, nessun daemon condiviso: come le altre celle della porta
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.setdefault("VERIMEM_HOSTED", "1")

from verimem.client import Memory  # noqa: E402
from verimem.l1_documentation_detector import detect_unsupported_doc_claim  # noqa: E402

P025 = ("Maria described a view of a waterfall and bridge as awesome and "
        "breath-taking.")
P025_FONTE = ("Maria: Hiking to the top and seeing this was awesome! "
              "Breath-taking. [shares photo: a photo of a waterfall with a "
              "bridge over it]")

#: fatti personali, sostenuti dalla loro fonte: la porta li deve AMMETTERE
FATTI_PERSONALI = [
    pytest.param(P025, P025_FONTE, id="p025-described"),
    pytest.param(
        "John explained that he hopes to get into local politics.",
        "John: I'm really hoping to get into local politics. I love helping "
        "the community.",
        id="explained-that"),
    pytest.param(
        "Maria ha descritto il panorama dalla cima come mozzafiato.",
        "Maria: il panorama dalla cima era mozzafiato!",
        id="ha-descritto"),
]

#: dichiarazioni di documentazione senza prova: devono RESTARE fermate
DICHIARAZIONI_DI_DOCUMENTAZIONE = [
    pytest.param("The API is fully documented.",
                 "The API has a reference page.", id="is-documented"),
    pytest.param("Il modulo è documentato.",
                 "Il modulo ha una pagina di riferimento.", id="e-documentato"),
    pytest.param("Le API sono documentate.",
                 "Le API hanno una pagina di riferimento.", id="sono-documentate"),
]


class _GiudiceFinto:
    """Giudice iniettato: punteggio fisso e alto, nessuna rete, nessun modello."""

    def complete(self, system, messages, **kw):  # noqa: ANN001
        return type("R", (), {"text": "Score: 98"})()


@pytest.fixture
def porta(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")
    return Memory(str(tmp_path / "porta.db"), grounding_llm=_GiudiceFinto())


def _strati(r: dict) -> list[str]:
    return [str(w.get("layer")) for w in (r.get("warnings") or [])
            if isinstance(w, dict) and w.get("layer")]


@pytest.mark.parametrize("fatto, fonte", FATTI_PERSONALI)
def test_alla_porta_il_fatto_personale_sostenuto_entra(porta, fatto, fonte):
    r = porta.add(fatto, source=fonte)
    disp = (r.get("adjudication") or {}).get("disposition")
    assert disp == "admitted", (
        f"fatto personale sostenuto dalla fonte, giudice a 98: disposizione "
        f"{disp!r}, strati {_strati(r)}")


def test_la_parola_di_p025_non_e_una_dichiarazione_di_documentazione():
    """Livello: la funzione. Rossa oggi, e dice QUALE parola scatta."""
    w = detect_unsupported_doc_claim(proposition=P025, verified_by=[])
    assert w is None, f"L1.14 scatta su {getattr(w, 'matched_text', w)!r}"


@pytest.mark.parametrize("fatto, fonte", DICHIARAZIONI_DI_DOCUMENTAZIONE)
def test_la_dichiarazione_di_documentazione_resta_fermata(porta, fatto, fonte):
    r = porta.add(fatto, source=fonte)
    disp = (r.get("adjudication") or {}).get("disposition")
    assert disp == "quarantined" and "L1.14" in _strati(r), (
        f"una dichiarazione di documentazione senza prova deve restare "
        f"fermata da L1.14: disposizione {disp!r}, strati {_strati(r)}")


def test_controllo_positivo_con_la_prova_docs_lo_strato_tace(porta):
    """Se questa cadesse, le celle rosse non direbbero che la colpa è di L1.14."""
    r = porta.add(P025, source=P025_FONTE, verified_by=["docs:README.md"])
    assert "L1.14" not in _strati(r), f"strati {_strati(r)}"
