"""Togliere il nome di un file dalla FONTE nasconde un'evidenza che c'era.

⚠️ QUESTA CELLA È ROSSA SUL TRONCO `42a09da9`, ed è il suo scopo: tiene il
posto della cura, come il suo gemello per T175.

#120 ha curato un difetto vero — `00-ESAME.md` veniva accusato del suo `00` —
sostituendo i nomi di file con un segnaposto. La sostituzione però avviene su
ENTRAMBI i lati del confronto::

    verimem/valore_non_nella_fonte.py, dentro `valori_non_nella_fonte`
        proposition = _senza_i_nomi_di_file(proposition)   # toglie un'ACCUSA
        source      = _senza_i_nomi_di_file(source)        # toglie un'EVIDENZA

Sul claim è giusto e funziona: misurato sulle coppie vere dello store, 13
letture su 17 perdono un'accusa che non meritavano. Sulla fonte cambia di
segno, perché la fonte non è il posto dove si tolgono letture — è il posto
dove si CERCANO. Quattro letture su diciassette vanno nel verso sbagliato, e
quel verso trattiene fatti VERI.

IL CASO, misurato il 22/09 (A/B fra `954ca671` e `42a09da9`, coppie reali)::

    claim : 'Il registro 00-ESAME ha 215 celle.'
    fonte : 'docs/stato-reale/00-ESAME.md — celle totali 215'
    prima di #120  accuse []        <- niente da contestare
    dopo   #120    accuse [0.0]     <- «il claim afferma 0, la fonte non ce l'ha»

La fonte ce l'ha: sta dentro `00-ESAME.md`, e la cura l'ha nascosta proprio a
chi doveva trovarla. Il claim scrive lo stesso nome SENZA estensione, quindi
non è riconosciuto come file e il suo `00` resta in piedi da accusare.

Gli altri tre hanno la stessa forma (il claim cita un file, la fonte no):
`verimem-due-artefatti-11-08.md`, `source_trust_…_2026-07-13.json`,
`fact_grounding.json`.

LE DUE STRADE, e non scelgo io: o la sostituzione resta solo sul claim, o il
confronto tratta `00-ESAME` e `00-ESAME.md` come lo stesso token. La prima
riga di questo file diventa verde con entrambe.
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import valori_non_nella_fonte


def _valori(prop: str, fonte: str) -> list[float]:
    return sorted({float(getattr(v, "valore", getattr(v, "value", 0)))
                   for v in valori_non_nella_fonte(prop, fonte)})


# ─────────────────────────  il difetto: ROSSO oggi  ──────────────────────────

def test_un_valore_scritto_dentro_il_nome_di_file_della_fonte_non_si_perde():
    """Il caso misurato sullo store. ROSSO sul tronco `42a09da9`."""
    accuse = _valori("Il registro 00-ESAME ha 215 celle.",
                     "docs/stato-reale/00-ESAME.md — celle totali 215")
    assert accuse == [], (
        f"accusato di {accuse}: il valore sta nel nome del file della FONTE, "
        f"e la cura di #120 l'ha tolto proprio a chi doveva trovarlo")


@pytest.mark.parametrize("claim, fonte", [
    ("Il registro 00-ESAME ha 215 celle.",
     "docs/stato-reale/00-ESAME.md — celle totali 215"),
    ("La nota 03-cose-spente elenca 7 voci.",
     "Il file 03-cose-spente.md elenca 7 voci."),
])
def test_lo_stesso_nome_con_e_senza_estensione_e_lo_stesso_token(claim, fonte):
    """La forma generale: il claim nomina il documento senza estensione, la
    fonte con. Sono lo stesso documento e lo stesso numero."""
    assert _valori(claim, fonte) == [], claim


# ──────────────────  il CONTROLLO POSITIVO: la cura di #120 resta  ───────────

def test_la_cura_di_120_resta_in_piedi():
    """⚠️ Senza questa riga, «nessuna accusa» si otterrebbe anche spegnendo il
    confronto — e la cura che #120 ha portato (giusta, e misurata su 13 letture
    delle 17 che cambiano) verrebbe buttata via insieme al suo rovescio.

    Qui il numero del nome di file sta nel CLAIM e non nella fonte: deve
    restare non accusato, che è esattamente ciò che #120 ha ottenuto.
    """
    accuse = _valori("Il documento 00-ESAME.md elenca 12 punti.",
                     "La revisione elenca dodici punti in un documento.")
    assert 0.0 not in accuse, (
        f"accuse {accuse}: lo 0 del nome di file nel CLAIM è tornato a essere "
        f"accusato — questa è la regressione di #120, non il suo rovescio")


def test_un_valore_che_la_fonte_davvero_non_contiene_resta_accusato():
    """Il secondo controllo positivo: il modulo deve ancora accusare.

    Se questa cella diventasse verde perché `valori_non_nella_fonte` ha smesso
    di accusare qualunque cosa, le tre sopra sarebbero verdi per il motivo
    sbagliato e nessuno se ne accorgerebbe.
    """
    accuse = _valori("Il registro ha 999 celle.",
                     "docs/stato-reale/00-ESAME.md — celle totali 215")
    assert 999.0 in accuse, (
        f"accuse {accuse}: il modulo non accusa più un valore che la fonte "
        f"davvero non contiene, quindi non sta più misurando niente")
