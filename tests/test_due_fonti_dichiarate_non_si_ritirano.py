"""Due fonti DICHIARATE e diverse non si ritirano a vicenda — e una penna sola sì.

IL DIFETTO, misurato sul corpus il 2026-09-06: `canonical_source_of` non leggeva
`source_signature`, quindi due fatti senza `verified_by` canonicalizzavano ENTRAMBI
su `"user"`, «stessa fonte» era vero PER COSTRUZIONE, la coppia usciva `evolution` e
il piu' recente RITIRAVA l'altro.

    155 ritiri cosi', 0 prima del default ON del 19/07 e 155 dopo, 153 con
    grounding >= 85, e 54 sbagliati su 60 letti uno per uno.

Fra le vittime: le celle di uno stesso banco (un fatto ne ha ritirate tre) e i due
bracci dei nostri A/B — «GRADED_ADMISSION acceso: 296 falsi» archiviato da «spento:
40 falsi». Il recall serviva un braccio e taceva l'altro.

⚠️ IL PERIMETRO E' STRETTO, E LA RIGA CHE LO TIENE STRETTO E' LA PIU' IMPORTANTE DI
QUESTO FILE: `test_una_penna_dichiarata_decide_e_la_firma_non_la_scavalca`. La prima stesura
della cura metteva la firma DAVANTI al `verified_by` e rompeva l'aggiornamento piu'
comune che esista — la stessa fonte che corregge il proprio valore citando ogni volta
il testo nuovo. L'ha vista cadere il controllo positivo in
`test_la_ricevuta_non_annuncia_una_supersessione_mai_avvenuta.py`. La regola vera e':
**una penna dichiarata decide, la firma discrimina solo dentro l'anonimato.**

PERCHE' QUI SOLO LE FUNZIONI E `_route_evolutions`: il verdetto END-TO-END dipende
dal coseno, e `tests/conftest.py:121` stubba l'embedder in una fixture `autouse`.
La misura end-to-end sta nel banco-script
`docs/stato-reale/banchi/il-presidio-con-le-due-colonne.py`, che gira FUORI da
pytest — e che e' la ragione per cui questo file non prova a fare la sua parte.
"""
from __future__ import annotations

import time
import types

import pytest

from verimem.anti_confab_gate import _route_evolutions
from verimem.supersession_policy import (
    canonical_source_of,
    classify_write_relation,
    due_fonti_dichiarate_e_diverse,
    source_signature_of,
)

PENNA = ["source-doc:billing:1"]
ALTRA_PENNA = ["source-doc:vendite:9"]


def _fatto(*, firma=None, penna=None, quando=None, status="model_claim",
           proposizione="il valore e' 100"):
    return types.SimpleNamespace(
        id="abcdef123456", proposition=proposizione, source_signature=firma,
        verified_by=penna or [], asserted_at=None, status=status,
        created_at=quando if quando is not None else time.time())


# ═══ LA CURA ①: la firma entra dove il `verified_by` non dice niente ═══

def test_due_anonimi_con_firme_diverse_non_sono_la_stessa_fonte():
    """I 155. Senza `verified_by` entrambi canonicalizzavano su `"user"`."""
    a = _fatto(firma="sha256:aaaa")
    b = _fatto(firma="sha256:bbbb")
    assert canonical_source_of(a) != canonical_source_of(b)


def test_una_penna_dichiarata_decide_e_la_firma_non_la_scavalca():
    """⚠️ LA RIGA CHE TIENE STRETTO IL PERIMETRO. Due citazioni della stessa
    fonte non sono due fonti: se lo fossero, «100 euro» e «150 euro» del
    listino resterebbero vivi entrambi."""
    a = _fatto(firma="sha256:aaaa", penna=PENNA)
    b = _fatto(firma="sha256:bbbb", penna=PENNA)
    assert canonical_source_of(a) == canonical_source_of(b) == "billing"


def test_senza_firma_e_senza_penna_il_comportamento_e_quello_di_prima():
    """Il caso 3 del presidio: nessuno dei due dichiara niente."""
    assert canonical_source_of(_fatto()) == canonical_source_of(_fatto()) == "user"


# ═══ LA CURA ②: la quarta uscita ═══

@pytest.mark.parametrize("nuovo, vecchio, atteso, perche", [
    (dict(firma="sha256:aaaa"), dict(firma="sha256:bbbb"), True,
     "i 155: due anonimi con due firme diverse"),
    (dict(firma="sha256:aaaa", penna=PENNA), dict(firma="sha256:bbbb", penna=PENNA),
     False, "una penna sola che cita due testi: e' un aggiornamento"),
    (dict(firma="sha256:aaaa", penna=PENNA),
     dict(firma="sha256:bbbb", penna=ALTRA_PENNA), True, "due penne diverse"),
    (dict(firma="sha256:aaaa"), dict(firma="sha256:aaaa"), False, "stessa firma"),
    (dict(firma="sha256:aaaa"), dict(), False,
     "una sola firma: non si sa che sono diverse, si sa che una manca"),
    (dict(), dict(), False, "nessuna firma"),
    (dict(firma="   "), dict(firma="sha256:bbbb"), False, "firma di soli spazi"),
])
def test_quando_due_fonti_coesistono(nuovo, vecchio, atteso, perche):
    assert due_fonti_dichiarate_e_diverse(
        _fatto(**nuovo), _fatto(**vecchio)) is atteso, perche


def test_la_relazione_fra_due_misure_distinte_non_e_una_evoluzione():
    """I due bracci di un A/B: due source distinte, la seconda non aggiorna la prima."""
    ora = time.time()
    nuovo = _fatto(firma=source_signature_of("Banco 30/08, braccio spento: 40 falsi"),
                   proposizione="col graded spento il gate ammette 40 falsi su 300")
    vecchio = _fatto(firma=source_signature_of("Banco 30/08, braccio acceso: 296 falsi"),
                     proposizione="col graded acceso il gate ammette 296 falsi su 300",
                     quando=ora - 60)
    assert classify_write_relation(nuovo, vecchio) == "conflict"


# ═══ IL CHIAMANTE: `_route_evolutions` non ritira e non quarantina ═══

class _StoreFinto:
    """Il minimo che `_route_evolutions` interroga: `agent.semantic.get(id)`."""

    def __init__(self, fatti):
        self.semantic = self
        self._fatti = fatti

    def get(self, cid):
        return self._fatti[cid]


def test_route_evolutions_tiene_vivi_entrambi_e_lo_dichiara(monkeypatch):
    """⚠️ E' QUI CHE LA PRIMA STESURA DELLA CURA CADEVA, senza che nessun test lo
    dicesse: il candidato sintetico di `_route_evolutions` non portava
    `source_signature`, quindi il confronto leggeva ASSENZA di firma invece che
    DIFFERENZA, e i casi passavano da ritiro a QUARANTENA — la stessa perdita
    con un altro nome. Il campo si passa da `cand_source`, che e' il TESTO."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    vecchio = _fatto(firma=source_signature_of("Cartella A: Rossi pesa 70 kg"),
                     proposizione="il paziente Rossi pesa 70 kg")
    agent = _StoreFinto({"abcdef123456": vecchio})

    supersede_ids: list[str] = []
    fonti_distinte: list[str] = []
    conflitti = _route_evolutions(
        agent, None, None, ["abcdef123456"], supersede_ids,
        proposition="il paziente Rossi pesa 95 kg",
        cand_source="Cartella B: Rossi pesa 95 kg",
        fonti_distinte=fonti_distinte)

    assert conflitti == [], "quarantinato: la misura sparisce, cambia solo il nome"
    assert supersede_ids == [], "ritirato: e' il difetto dei 155"
    assert fonti_distinte == ["abcdef123456"], (
        "tenuto vivo ma in SILENZIO: chi scrive ha diritto di sapere che due "
        "fonti non concordano")


def test_route_evolutions_ritira_ancora_quando_la_penna_e_una_sola(monkeypatch):
    """Il gemello obbligatorio del test sopra: se la cura tenesse vivi ANCHE
    questi, passerebbe quello di sopra smettendo di ritirare qualunque cosa."""
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    vecchio = _fatto(firma=source_signature_of("Listino di marzo: 100 euro"),
                     penna=PENNA, quando=time.time() - 60,
                     proposizione="l'abbonamento costa 100 euro al mese")
    agent = _StoreFinto({"abcdef123456": vecchio})

    supersede_ids: list[str] = []
    fonti_distinte: list[str] = []
    conflitti = _route_evolutions(
        agent, PENNA, None, ["abcdef123456"], supersede_ids,
        proposition="l'abbonamento costa 150 euro al mese",
        cand_source="Listino di settembre: 150 euro",
        fonti_distinte=fonti_distinte)

    assert supersede_ids == ["abcdef123456"], (
        "la stessa fonte che corregge il proprio valore DEVE ancora ritirare: "
        "senza, il recall serve due prezzi e uno e' vecchio")
    assert conflitti == []
    assert fonti_distinte == []


def test_l_impronta_e_una_sola_regola_per_tutto_il_corpus():
    """`source_signature_of` esiste perche' il calcolo serviva in due posti e la
    seconda copia sarebbe divergita. Se cambia, non combacia piu' con NESSUNA
    delle impronte gia' in archivio: e' un valore pin-ato, non un dettaglio."""
    assert source_signature_of("Cartella A: Rossi pesa 70 kg") == \
        "sha256:af166710ceeae2f7"
    assert source_signature_of("  Cartella A:   Rossi\n pesa 70 kg  ") == \
        source_signature_of("Cartella A: Rossi pesa 70 kg"), \
        "gli spazi si normalizzano: e' cosi' che `client.add` la calcolava"
    assert source_signature_of(None) is None
    assert source_signature_of("   ") is None
