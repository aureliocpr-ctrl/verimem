"""Un fatto che esce dal prodotto porta con se' cio' che il prodotto sa di lui.

Misurato il 2026-07-30 su mcp_server.py — 13 punti costruiscono a mano il dict
di un fatto, e ognuno decide da solo quali campi metterci:

    proposition        13/13     (il campo del giorno uno)
    grounding_score     6/13
    asserted_at         2/13
    valid_until         1/13
    derives_from        1/13
    confidence_tier     0/13
    epistemic           0/13
    writer_principal    0/13
    last_verified_at    0/13

`Fact` ha 26 campi e nessun metodo di uscita, quindi ogni superficie riparte da
zero. Non e' che undici superfici hanno un bug: e' che non esiste un contratto,
e senza contratto la probabilita' di dimenticare un campo e' quella misurata —
sette punti su tredici hanno dimenticato il verdetto.

Il costo si vede sui campi appesi in coda al dataclass col tempo. Quattro sono
calcolati, persistiti e documentati col loro razionale, e NON ESCONO DA NESSUNA
SUPERFICIE: il tier di confidenza del giudice (v15), l'etichetta epistemica
proven/unbeaten/refuted (v14), l'identita' server-stamped di chi ha scritto
(anti-spoof, mai presa dagli argomenti del tool), e quando il fatto e' stato
verificato l'ultima volta. Il prodotto li calcola, li conserva, e nessun utente
puo' leggerli.

`test_ogni_campo_del_dataclass_e_deciso` e' l'invariante che chiude la classe:
il campo numero 27 non potra' nascere invisibile, perche' chi lo aggiunge dovra'
dire se esce o perche' no.
"""
from __future__ import annotations

import dataclasses

import pytest

from verimem.semantic import Fact

#: Campi che di proposito NON escono, col motivo. Sta qui e non nel codice
#: perche' un'esclusione deve costare una riga di spiegazione a chi la fa.
NON_ESCONO = {
    "source_signature": "impronta interna anti-tamper, non dice nulla al lettore",
}


def test_un_fatto_sa_uscire():
    f = Fact(proposition="x", topic="t")
    p = f.as_payload()
    assert isinstance(p, dict) and p["proposition"] == "x"


def test_il_verdetto_c_e_sempre_anche_quando_manca():
    """Assente e null non sono la stessa cosa.

    Una chiave che manca si legge «questa superficie non espone il verdetto»;
    un null esplicito si legge «il moat non ha girato». Il prodotto vende
    esattamente quella distinzione, quindi il verdetto e' l'unico campo che
    esce anche vuoto.
    """
    p = Fact(proposition="x").as_payload()
    assert "grounding_score" in p and p["grounding_score"] is None
    q = Fact(proposition="x", grounding_score=99.9).as_payload()
    assert q["grounding_score"] == 99.9


def test_i_campi_vuoti_non_gonfiano_il_payload():
    """Ogni chiave inutile e' contesto rubato a chi legge dall'altra parte."""
    p = Fact(proposition="x").as_payload()
    assert "epistemic" not in p, "un campo mai valorizzato non deve uscire"
    assert "superseded_by" not in p
    q = Fact(proposition="x", epistemic={"kind": "proven"}).as_payload()
    assert q["epistemic"] == {"kind": "proven"}


def test_i_quattro_campi_invisibili_ora_escono():
    """I quattro che 0 superfici su 13 mostravano."""
    f = Fact(proposition="x", confidence_tier="high", writer_principal="sdk:local",
             last_verified_at=1234.0, epistemic={"kind": "unbeaten"})
    p = f.as_payload()
    for campo in ("confidence_tier", "writer_principal", "last_verified_at",
                  "epistemic"):
        assert campo in p, f"{campo} continua a non uscire"


def test_ogni_campo_del_dataclass_e_deciso():
    """L'invariante che chiude la classe.

    Il campo numero 27 non puo' nascere invisibile: o esce, o e' in NON_ESCONO
    con scritto perche'. Senza questo, ogni campo aggiunto in futuro ripete la
    storia di confidence_tier — calcolato, persistito, e mai letto da nessuno.
    """
    pieno = Fact(
        proposition="x", topic="t", source_episodes=["e1"], superseded_by="s",
        superseded_at=1.0, superseded_reason="r", verified_by=["v"],
        source_signature="sig", trigger_keywords=["k"], applicable_when="w",
        worked_example="ex", lineage_to=["l"], writer_principal="p",
        last_verified_at=2.0, valid_until=3.0, derives_from=["d"],
        grounding_score=50.0, confidence_tier="high", asserted_at=4.0,
        epistemic={"kind": "proven"},
    )
    esce = set(pieno.as_payload())
    tutti = {f.name for f in dataclasses.fields(Fact)}
    dimenticati = tutti - esce - set(NON_ESCONO)
    assert not dimenticati, (
        f"campi del dataclass che non escono e non sono dichiarati: "
        f"{sorted(dimenticati)}\naggiungili al payload, oppure a NON_ESCONO "
        f"scrivendo perche' non servono a chi legge.")
    assert not (set(NON_ESCONO) - tutti), (
        "NON_ESCONO nomina campi che il dataclass non ha piu'")


@pytest.mark.parametrize("campo,valore", [
    ("grounding_score", 88.5), ("confidence_tier", "borderline"),
    ("status", "quarantined"), ("verified_by", ["pytest:x_PASS"]),
])
def test_il_valore_non_viene_trasformato(campo, valore):
    """Il payload trasporta, non interpreta."""
    p = Fact(proposition="x", **{campo: valore}).as_payload()
    assert p[campo] == valore
