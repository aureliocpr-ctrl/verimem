"""«gate» non è un'etichetta mancante: è un'etichetta che porta fuori strada.

`test_chi_ha_deciso_la_quarantena` ha portato `quarantined_by` a dire CHI ha
deciso, con tre valori: `moat`, `L1`, `gate`. Questo file continua quel lavoro
su ciò che finiva sotto `gate` — il ramo di default, che sul corpus è il **56%
dei quarantinati delle ultime 24h** (misurato il 21/08).

Il caso che l'ha fatto vedere, riprodotto alla porta::

    claim   «Con il tetto attivo il committed e 176,6 MB.»
    moat    passed   grounding 99.89        <- il giudice APPROVA
    warning layer='L4.1'  «il claim afferma un valore che la fonte non
                           contiene: 6 mb, 176»
    scritto quarantined_by = 'gate'

Il giorno dopo `quarantine_log(explain=True)` concludeva, in buona fede::

    «causa NON REGISTRATA, e NON è L4: il moat ha giudicato 99.89, cioè
     l'ha APPROVATA, e il fatto è trattenuto lo stesso»

…quando a decidere era stato L4.1. Un'etichetta generica si legge come
un'assenza, e da un'assenza si deduce il contrario del vero.

⚠️ LA PRECEDENZA NON CAMBIA, ed è il presidio che vale più di tutti: i rami
`store-screen` / `moat` / `L1` decidono come prima. Qui si nomina soltanto ciò
che prima si chiamava `gate`.

Il caso L4.1 vive nel banco fuori da pytest
(`docs/stato-reale/banchi/ws3-quale-layer-ha-deciso.py`) perché dipende dal
verdetto del giudice, e `tests/conftest.py` sostituisce l'embedder con uno
stub: qui misurerebbe il righello. Ciò che si prova qui è la parte
deterministica — la funzione che sceglie l'etichetta, e la porta che la legge.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory, _reason_from_warnings, chi_ha_quarantinato

FONTE = ("Verbale: il modulo di fatturazione e stato testato e funziona "
         "correttamente in produzione.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


# ─────────────────────────  la funzione che sceglie  ─────────────────────────

def test_il_layer_che_ha_agito_prende_il_posto_di_gate():
    """IL CUORE: `agito` porta il layer, e non finisce più sotto «gate»."""
    assert chi_ha_quarantinato(
        "passed", [{"layer": "L4.1", "reason": "…"}], agito=["L4.1"]) == "L4.1"


def test_quando_nessun_layer_ha_agito_resta_gate():
    """Il ramo di default sopravvive: senza layer non si inventa un colpevole.

    È la metà che conta quanto l'altra — un'etichetta FALSA sarebbe peggio di
    una generica.
    """
    assert chi_ha_quarantinato("passed", [], agito=[]) == "gate"
    assert chi_ha_quarantinato("passed", [], agito=[""]) == "gate"


def test_un_avviso_consultivo_non_diventa_il_colpevole():
    """`agito` sono i BLOCKING layers, non i warning: un avviso che NON ha
    fermato la scrittura non deve prendersene il merito.

    Qui il warning c'è ma `agito` è vuoto — il caso di un `*-observe`, che
    `_blocking_layers` esclude a monte.
    """
    assert chi_ha_quarantinato(
        "passed", [{"layer": "L3-semantic-observe"}], agito=[]) == "gate"


def test_fra_piu_layer_vince_la_stessa_priorita_della_ragione():
    """L'etichetta e il testo della spiegazione non possono indicare due layer
    diversi: entrambi ordinano con `_BLOCK_LAYER_PRIORITY` (L3 prima di L4)."""
    assert chi_ha_quarantinato(
        "passed", [], agito=["L4-grounding", "L3-supersession"]) == "L3-supersession"


@pytest.mark.parametrize("ordine", [
    ["L4.1", "L4-skipped"],
    ["L4-skipped", "L4.1"],   # l'ordine in cui arrivano non deve contare
])
def test_un_blocco_vero_non_perde_contro_un_avviso(ordine):
    """⚠️ `L4.1` mancava da `_BLOCK_LAYER_PRIORITY` e finiva in fondo, dietro a
    `L4-skipped` — che non è un blocco ma l'avviso «il giudice non è girato»::

        warnings ['L4.1', 'L4-skipped']
          prima ->  «nessun giudice disponibile, controllo non eseguito»
          dopo  ->  «il claim afferma un valore che la fonte non contiene…»

    I due COESISTONO davvero: L4.1 è lessicale e gira anche senza giudice. E
    da quando l'etichetta nomina il layer, senza questa riga direbbe
    `L4-skipped` — un'etichetta FALSA, cioè peggio di quella generica.
    """
    testi = {"L4.1": "il claim afferma un valore che la fonte non contiene",
             "L4-skipped": "nessun giudice disponibile, controllo non eseguito"}
    ws = [{"layer": lay, "reason": testi[lay]} for lay in ordine]
    assert chi_ha_quarantinato("passed", ws, agito=list(ordine)) == "L4.1"
    assert _reason_from_warnings(ws) == testi["L4.1"]


def test_presidio_L1_vince_anche_con_un_L41_accanto():
    """La precedenza dichiarata dal prodotto non si sposta: L1 esiste per
    intercettare le auto-affermazioni, e viene prima."""
    ws = [{"layer": "L1.10", "reason": "self-claim"},
          {"layer": "L4.1", "reason": "numero non nella fonte"}]
    assert chi_ha_quarantinato("passed", ws, agito=["L1.10", "L4.1"]) == "L1"
    assert _reason_from_warnings(ws) == "self-claim"


# ───────────────────────────  LA PRECEDENZA — presidio  ──────────────────────

def test_presidio_L1_resta_L1(mem):
    """Se questo cade, qualcuno ha cambiato la precedenza credendo di
    arricchire l'etichetta."""
    r = mem.add("Ho verificato che il modulo di fatturazione funziona "
                "correttamente.", topic="az/q", source=FONTE)
    assert r.get("status") == "quarantined"
    assert r.get("quarantined_by") == "L1", r.get("quarantined_by")


def test_presidio_il_moat_resta_moat(mem):
    r = mem.add("Il modulo di fatturazione ha 9999 utenti attivi.",
                topic="az/w", source="Verbale: il modulo ha 12 utenti attivi.")
    assert r.get("status") == "quarantined"
    assert r.get("quarantined_by") == "moat", r.get("quarantined_by")


def test_presidio_un_fatto_ammesso_non_dichiara_nessun_decisore(mem):
    r = mem.add("Il magazzino centrale ha 4200 metri quadrati.", topic="az/m",
                source="Planimetria: magazzino centrale, 4200 metri quadrati.")
    assert r.get("status") != "quarantined"
    assert "quarantined_by" not in r


# ──────────────────────────────  la porta che legge  ─────────────────────────

def test_la_porta_espone_il_layer_senza_audit_trail(mem, monkeypatch):
    """`quarantine_log()` prendeva il perché SOLO dall'audit trail, che è
    opt-in e di default spento: misurato il 21/08, `reason` usciva None su
    40 righe su 40. La colonna sulla riga c'era e la SELECT non la leggeva."""
    monkeypatch.delenv("VERIMEM_AUDIT_LOG", raising=False)
    mem.add("Ho verificato che il modulo di fatturazione funziona "
            "correttamente.", topic="az/q", source=FONTE)
    righe = mem.quarantine_log(limit=5)
    assert righe, "il banco non produce nessun quarantinato"
    r = righe[0]
    assert r.get("quarantined_by"), "la SELECT non porta la colonna"
    assert r.get("layers"), "la porta non espone il layer che ha deciso"


def test_explain_non_cancella_il_layer_che_la_riga_gia_sapeva(mem, monkeypatch):
    """⚠️ LA FUNZIONE CHE DEVE SPIEGARE CANCELLAVA L'INFORMAZIONE.

    `_spiega_le_quarantene` ricalcola e riscrive `layers`; sul ramo «causa non
    ricostruibile» lo azzerava, buttando via il layer che la riga portava::

        senza explain   layers=['L4.1']
        con   explain   layers=[]        <- e il why asseriva «NON è L4»
    """
    monkeypatch.delenv("VERIMEM_AUDIT_LOG", raising=False)
    mem.add("Ho verificato che il modulo di fatturazione funziona "
            "correttamente.", topic="az/q", source=FONTE)
    senza = mem.quarantine_log(limit=5)[0]
    con = mem.quarantine_log(limit=5, explain=True)[0]
    assert senza.get("layers"), "il caso base non è riprodotto"
    assert con.get("layers"), (
        "explain=True ha cancellato il layer che la riga sapeva già: "
        f"senza={senza.get('layers')!r} con={con.get('layers')!r}")
