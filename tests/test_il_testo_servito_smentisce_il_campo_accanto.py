"""Un numero CITATO dentro il testo servito non deve smentire il campo
vivo che gli sta di fianco nello stesso payload.

Il difetto, letto il 30/08 chiamando il prodotto da utente
(``hippo_retirement_log breakdown=true`` sul corpus di casa)::

    "by_scope": {"same_topic": 698, "cross_topic": 1538}
    "scope_means": "... The same-topic 266 are where supersession is a
                    real editorial act ..."

698 accanto a 266, nella stessa risposta. Nessuno dei due e' sbagliato:
1463 e 1538 vengono da un EVENTO congelato (il collasso del 2026-07-02) e
sono esatti ancora oggi, mentre 266 e' un FLUSSO che da allora e'
cresciuto. Il testo li mette in fila senza distinguerli, e il lettore
confronta l'ultimo col campo di fianco.

La cura del 2026-08-07 (``measured_at``, ``since``, le ``formula``) aveva
gia' affrontato questo: dare l'istante ai numeri. Ha coperto i numeri
VIVI e ha lasciato scoperti quelli citati DENTRO il testo — la stessa
forma del difetto che curava.

Qui il numero non si data: si DERIVA. Un valore calcolato tre righe
sopra non puo' divergere da se stesso.
"""
from __future__ import annotations

import re

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_breakdown


@pytest.fixture()
def mem_con_same_topic(tmp_path):
    """Due ritiri DENTRO lo stesso topic: e' il caso che la fixture del
    banco gemello (``test_housekeeping_non_vuol_dire_senza_perdita``) non
    produce, perche' li' ``same_topic`` vale 0 e il confronto non si vede."""
    m = Memory(tmp_path / "m.db")
    a = m.add("the depot holds 10 crates", topic="log/a")["id"]
    b = m.add("the depot holds 20 crates", topic="log/a")["id"]
    c = m.add("the depot holds 30 crates", topic="log/a")["id"]
    m.semantic.supersede(a, b, principal="test", reason="banco")
    m.semantic.supersede(b, c, principal="test", reason="banco")
    return m


def test_il_numero_citato_nel_testo_NON_deve_smentire_il_campo_vivo(
        mem_con_same_topic):
    bd = retirement_breakdown(mem_con_same_topic.semantic)
    vivo = bd["by_scope"]["same_topic"]
    assert vivo == 2, bd["by_scope"]
    citato = re.search(r"same-topic\s+([\d,]+)", bd["scope_means"])
    assert citato is not None, bd["scope_means"]
    assert int(citato.group(1).replace(",", "")) == vivo, (
        f"il testo dice {citato.group(1)}, il campo accanto dice {vivo}")


def test_i_numeri_dell_EVENTO_restano_letterali_e_datati(mem_con_same_topic):
    """Il rovescio: 1463 e 1538 NON vanno derivati. Sono la misura di un
    evento del passato, dichiarata con la sua data, e su un banco da tre
    fatti diventerebbero 0 — cioe' si perderebbe l'informazione."""
    nota = retirement_breakdown(mem_con_same_topic.semantic)["scope_means"]
    assert "1463" in nota and "1538" in nota, nota
    assert "2026-08-07" in nota, nota


# ─────────────────────────────────────────────────────────────────────
# LO SWEEP. Curato `scope_means`, la domanda che segue e' «chi altro fa
# la stessa cosa?». Nello stesso modulo altri due testi serviti citano
# un numero-flusso letterale, e il payload che li accompagna lo smentisce
# gia' oggi: `chain.formula` dice 37% mentre `ends_servable` su tutte le
# catene ne da' un altro, e `principal_means` dice «174 of 1805» mentre
# `attribution` accanto somma il totale corrente.
# ─────────────────────────────────────────────────────────────────────


def test_la_formula_delle_catene_non_deve_citare_una_quota_smentita(
        mem_con_same_topic):
    bd = retirement_breakdown(mem_con_same_topic.semantic)
    ch = bd["chain"]
    tot = ch["ends_servable"] + ch["ends_dead"] + ch["ends_missing"]
    atteso = round(ch["ends_servable"] / tot * 100)
    citate = [int(x) for x in re.findall(r"(\d+)%\s+overall", ch["formula"])]
    assert citate == [] or citate == [atteso], (
        f"la formula cita {citate}%, il payload ne da' {atteso}%")


def test_principal_means_non_deve_citare_un_totale_smentito(
        mem_con_same_topic):
    bd = retirement_breakdown(mem_con_same_topic.semantic)
    att = bd["attribution"]
    tot = att["attributed"] + att["unattributed"]
    m = re.search(r"(\d+) of (\d+) retirements carry one",
                  bd["principal_means"])
    assert m is not None, bd["principal_means"]
    assert (int(m.group(1)), int(m.group(2))) == (att["attributed"], tot), (
        f"il testo dice {m.group(1)} of {m.group(2)}, il payload accanto "
        f"dice {att['attributed']} of {tot}")


def test_su_un_corpus_SENZA_dati_la_formula_non_inventa_una_quota(tmp_path):
    """Zero su zero non e' una percentuale: e' la regola che questo stesso
    modulo applica gia' a `concentration`. Derivando, la frase deve
    perdere il numero, non stamparne uno finto."""
    m = Memory(tmp_path / "vuoto.db")
    ch = retirement_breakdown(m.semantic)["chain"]
    assert "%" not in ch["formula"] or "overall" not in ch["formula"], (
        ch["formula"])
    assert "must not travel alone" in ch["formula"], ch["formula"]


# ─────────────────────────────────────────────────────────────────────
# IL PRESIDIO DI CLASSE. Curati tre casi uno per uno, la lezione dice che
# la cura vera e' un CONTROLLO, non tre toppe. La regola che li separa
# tutti: un numero dentro un testo servito o e' DERIVATO — e allora
# coincide col payload — o e' un EVENTO, e allora porta la sua data.
# Senza nessuna delle due, invecchia in silenzio contro il campo accanto.
# ─────────────────────────────────────────────────────────────────────

_DATA_ISO = re.compile(r"\b20\d\d-\d\d-\d\d\b")
_NUMERO = re.compile(r"\b\d+(?:[.,]\d+)?\s*%|\b\d{3,}\b")


def _testi_serviti(payload, _dove=()):
    """Ogni stringa lunga che il payload SERVE, col suo percorso."""
    if isinstance(payload, dict):
        for k, v in payload.items():
            if isinstance(v, str) and len(v) > 60:
                yield ".".join((*_dove, str(k))), v
            else:
                yield from _testi_serviti(v, (*_dove, str(k)))
    elif isinstance(payload, list):
        for i, v in enumerate(payload):
            yield from _testi_serviti(v, (*_dove, str(i)))


def _numeri_del_payload(payload) -> set[str]:
    """I valori numerici che il payload calcola, come li stamperebbe."""
    fuori: set[str] = set()
    if isinstance(payload, dict):
        for v in payload.values():
            fuori |= _numeri_del_payload(v)
    elif isinstance(payload, list):
        for v in payload:
            fuori |= _numeri_del_payload(v)
    elif isinstance(payload, bool):
        pass
    elif isinstance(payload, int):
        fuori.add(str(payload))
    elif isinstance(payload, float):
        fuori |= {str(round(payload * 100)), f"{payload * 100:.1f}"}
    return fuori


@pytest.mark.parametrize("vista", ["retirement", "quarantine"])
def test_ogni_numero_servito_e_DERIVATO_oppure_DATATO(mem_con_same_topic,
                                                      vista):
    from verimem.retirement_log import quarantine_breakdown
    bd = (retirement_breakdown if vista == "retirement"
          else quarantine_breakdown)(mem_con_same_topic.semantic)
    vivi = _numeri_del_payload(bd)
    scoperti = []
    for dove, testo in _testi_serviti(bd):
        if _DATA_ISO.search(testo):
            continue                      # e' un evento e dichiara quando
        for n in _NUMERO.findall(testo):
            if n.rstrip("%").strip() not in vivi:
                scoperti.append((dove, n, testo[:80]))
    assert not scoperti, (
        "numeri letterali senza data e senza corrispondenza nel payload: "
        f"{scoperti}")
