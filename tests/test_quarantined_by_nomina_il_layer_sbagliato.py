"""`quarantined_by` nomina il PRIMO layer che parla, non quello che ha deciso.

Misurato il 2026-08-26 alle 21:40, `ee5a439f`, fuori da pytest, store isolato.

Un fatto trattenuto con due layer sulla ricevuta:

    quarantined  g=43.59
      quarantined_by = 'L3-coexistence'
      layer che hanno parlato = ['L3-coexistence', 'L4-review']

`L3-coexistence` dichiara nel proprio messaggio di NON trattenere:

    «a contradiction was found but both facts are kept … both stay servable and
     recall returns them together»

A trattenere e' `L4-review`: «borderline grounding (44) in the CE review band
[40, 80) — held for review, **not admitted**».

Il controllo che isola la causa: una coppia dove parla un solo gruppo di layer
riceve l'etichetta giusta —

    quarantined  g=1.87   quarantined_by='moat'   layer=['L4-negazione','L4-grounding']  ok

⇒ Il difetto compare quando piu' layer parlano: l'etichetta prende il primo.

PERCHE' CONTA, e non e' cosmesi: chi indaga un rifiuto legge `quarantined_by`,
va a leggere il messaggio di quel layer, e trova scritto che il fatto **resta
servibile** — l'opposto di cio' che e' successo. La diagnosi diventa impossibile,
o peggio si conclude che il fatto e' servito quando non lo e'.

CONSEGUENZA MISURATA il 2026-08-27 alle 00:08, e vale piu' del difetto stesso:
il campo SOTTOSTIMA SISTEMATICAMENTE i layer bassi in priorita'. Sul corpus

    281x moat · 51x L4.1 · 49x gate · 26x L4-review · 7x L3-coexistence · 2x L1

`L1` risulta 2 su 417 e sembra irrilevante. Alla porta, su otto vanti canonici:

    trattenuti senza source 8/8 · con source 8/8
    casi in cui L1 e' l'UNICO bloccante (con source, nessun layer L4): 3/8

L1 li ferma tutti e otto, ed e' l'unico che parla in tre. Ma `L1` e' TERZO in
`_BLOCK_LAYER_PRIORITY` (dopo `L3` e `L4-grounding`), quindi ogni volta che uno
dei due parla insieme a lui l'etichetta va a loro — e nei due casi con
`L4-grounding` succede esattamente questo.

⇒ Chi conta il contributo di un layer da `quarantined_by` misura l'ETICHETTA e
non il layer. Il numero e' basso per costruzione, non per merito. Segnalato da
ws3 partendo da un caso ZH dove `L1.20` era l'unico bloccante utile: non era
un'anomalia.

Si aggancia a due cose gia' in casa: l'aperto «il perche' di un rifiuto non e'
persistito» (`quarantined_by` popolato nel 3,8% dei casi) — non e' solo poco
popolato, quando c'e' puo' nominare il layer sbagliato — e la riga del 20/08
«un'etichetta FALSA e' peggio di una mancante».
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

FONTE = "    2 passed     NO\n    1 xfailed    NO\n    2 test       NO\n    passati      NO"
PRIMO = "Nella source troncata 2 passed non compare."
SECONDO = "Nella source troncata 1 xfailed non compare."


def _coppia() -> dict:
    """Scrive le due proposizioni in sequenza e restituisce la ricevuta della seconda."""
    mem = Memory(str(Path(tempfile.mkdtemp()) / "qb.db"))
    mem.add(PRIMO, topic="t/qb", source=FONTE, validate="full")
    return mem.add(SECONDO, topic="t/qb", source=FONTE, validate="full")


def test_CONTROLLO_la_seconda_scrittura_e_trattenuta_da_piu_di_un_layer():
    """Il righello. Se non e' trattenuta, o parla un layer solo, il test sotto
    non misura il difetto: lo dice fallendo, non saltando."""
    ric = _coppia()
    layer = [str(w.get("layer")) for w in (ric.get("warnings") or [])]
    assert str(ric.get("status")) == "quarantined", (
        f"non e' trattenuta ({ric.get('status')}, g={ric.get('grounding_score')}): "
        "il banco non riproduce piu' il caso, rimisurare"
    )
    assert len(layer) >= 2, f"parla un layer solo ({layer}): il difetto non si presenta"


@pytest.mark.xfail(
    strict=True,
    reason="quarantined_by prende il PRIMO layer che parla invece del decisore: "
    "nomina L3-coexistence, che dichiara «both stay servable», mentre a "
    "trattenere e' L4-review (26/08)",
)
def test_quarantined_by_dovrebbe_nominare_chi_ha_deciso():
    ric = _coppia()
    etichetta = str(ric.get("quarantined_by"))
    assert etichetta != "L3-coexistence", (
        f"l'etichetta e' {etichetta!r}, ma quel layer dichiara di NON trattenere; "
        f"i layer sulla ricevuta sono "
        f"{[str(w.get('layer')) for w in (ric.get('warnings') or [])]}"
    )


def test_CONTROLLO_dove_parla_un_gruppo_solo_l_etichetta_e_giusta():
    """L'altra popolazione: il campo non e' rotto sempre, e va detto."""
    fonte = "    40 pezzi     NO\n    12 colli     NO\n    3 bolle      NO"
    mem = Memory(str(Path(tempfile.mkdtemp()) / "qc.db"))
    ric = mem.add(
        "Nel referto abbreviato 40 pezzi non compare.",
        topic="t/qc",
        source=fonte,
        validate="full",
    )
    if str(ric.get("status")) != "quarantined":
        pytest.fail(
            f"il caso di controllo non e' piu' trattenuto ({ric.get('status')}): "
            "rimisurare, il confronto fra i due casi non regge"
        )
    assert str(ric.get("quarantined_by")) == "moat", (
        f"anche il caso a un gruppo solo ha l'etichetta sbagliata "
        f"({ric.get('quarantined_by')!r}): il difetto e' piu' esteso di quanto "
        "questo banco dichiari"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-27, 19:24 — IL SECONDO MODO in cui lo stesso campo inganna: NON VIENE
# RIPULITO AL RESTORE.
#
# `restore_fact` riporta un fatto quarantinato a `model_claim` e lo rimette
# nella recall — verificato end-to-end: prima del restore la query non lo trova
# (0 risultati), dopo sì (1). Quella parte funziona.
#
# Ma `quarantined_by` resta popolato sul fatto tornato vivo:
#
#     il fatto dopo il restore:
#       status=model_claim   grounding=1.16   quarantined_by='moat'
#
# Sul corpus reale (27/08, sola lettura):
#
#     fatti totali ............................. 14417
#     con quarantined_by popolato .............. 577
#     di questi, NON quarantinati (cioè VIVI) .. 154      <- il 26,7%
#
# ⇒ Chi filtra `WHERE quarantined_by IS NOT NULL` per contare le quarantene ne
#   prende 577 e 154 sono vivi. Sommato al difetto della sezione precedente —
#   il campo nomina il primo layer che parla, non il decisore — lo stesso campo
#   è inaffidabile in DUE modi indipendenti: sbaglia CHI, e sbaglia SE.
#
# 📖 È la stessa classe già in casa per un altro campo: «`superseded_by IS NULL`
# non vuol dire vivo, vuol dire non ritirato». Un campo di stato che non viene
# ripulito quando lo stato cambia.
#
# ⚠️ E il `reason` passato a `restore()` non viene persistito da nessuna parte:
# cercato in ogni colonna di tutte e 6 le tabelle del db, zero occorrenze. Il
# parametro esiste nella firma (`reason: str = ""`), chi lo passa crede di
# lasciare una traccia, e non ne resta niente — il che rende il ripescaggio non
# ricostruibile: né chi, né quando, né perché.


def test_il_restore_rimette_davvero_il_fatto_nella_recall():
    """La metà che funziona, e sta qui perché il banco non esageri."""
    import tempfile
    from pathlib import Path

    from verimem.client import Memory

    fonte = "Il collaudo del lotto B12 ha rilevato 3 pezzi difformi su 40 controllati."
    falso = "Il collaudo non ha rilevato pezzi difformi."
    mem = Memory(str(Path(tempfile.mkdtemp()) / "rest.db"))
    ric = mem.add(falso, topic="t/restore", source=fonte, validate="full")
    fid = ric.get("id") or ric.get("fact_id")
    assert str(ric.get("status")) == "quarantined", (
        f"il banco presuppone che questo venga quarantinato, invece: {ric.get('status')}"
    )

    def _nella_recall() -> bool:
        return any(
            str(h.get("text")) == falso
            for h in (mem.search("Il collaudo ha rilevato difformita?", k=6) or [])
        )

    assert not _nella_recall(), "un quarantinato è nella recall: la promessa base è caduta"
    assert mem.restore(fid, reason="prova del presidio") is True, "restore() ha reso False"
    assert _nella_recall(), (
        "dopo il restore il fatto non torna nella recall: il backlog non sarebbe drenabile"
    )


@pytest.mark.xfail(
    strict=True,
    reason="quarantined_by resta popolato sul fatto tornato vivo: 154 fatti VIVI "
    "su 577 col campo popolato, nel corpus reale del 27/08",
)
def test_il_restore_dovrebbe_ripulire_quarantined_by():
    import sqlite3
    import tempfile
    from pathlib import Path

    from verimem.client import Memory

    fonte = "Il collaudo del lotto B12 ha rilevato 3 pezzi difformi su 40 controllati."
    falso = "Il collaudo non ha rilevato pezzi difformi."
    db = Path(tempfile.mkdtemp()) / "rest2.db"
    mem = Memory(str(db))
    ric = mem.add(falso, topic="t/restore2", source=fonte, validate="full")
    fid = ric.get("id") or ric.get("fact_id")
    mem.restore(fid, reason="prova del presidio")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    riga = con.execute(
        "SELECT status, quarantined_by FROM facts WHERE id=?", (fid,)
    ).fetchone()
    con.close()
    assert riga and str(riga[0]) != "quarantined", f"il restore non ha cambiato lo stato: {riga}"
    assert riga[1] is None, f"il fatto e' vivo ma porta ancora quarantined_by={riga[1]!r}"
