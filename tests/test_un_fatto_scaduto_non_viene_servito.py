"""Un fatto con `valid_until` nel passato non deve essere servito dal recall.

La lettura statica dice che la capacità è cablata: `_fact_is_stale`
(`semantic.py:1002`) mette `valid_until <= now` **prima** del calcolo del decay
— *«è più forte: un fatto scaduto è escluso anche se fresco»* — ed è chiamata da
`semantic.py:4086` (`valid_until=getattr(f, "valid_until", None)`) e da `:4446`
(`valid_until=_row_vu(r)`).

⚠️ E LA LETTURA STATICA ERA INCOMPLETA — l'ha corretta l'esecuzione. Spegnendo
il per-riga di `semantic.py:1039` questo test **passa lo stesso**: il recall non
ci passa. Il punto che morde è una **terza** implementazione, la maschera
vettoriale a `semantic.py:4249` e `:4252` — `fresh_mask = (view_lv <= now) &
(view_vu > now)`, dove `view_vu` vale `inf` per i fatti senza scadenza. È lei che
toglie il fatto scaduto dal top-k, ed è lei che questo test presidia: spegnendola
cade il caso e resta verde il controllo positivo.

⚠️ MA UNA FUNZIONE PUÒ ESSERE CHIAMATA E NON MORDERE. Il valore può arrivare
`None` per un attributo che non si popola, il ramo può essere in un percorso che
il recall normale non attraversa, il filtro può agire su una lista già svuotata.
La lettura del codice non chiude questa domanda: solo il comportamento la chiude.

⚠️ E il campo è popolato su **0 fatti su 17098** nel corpus di casa, quindi
nessuno se ne accorgerebbe: è una capacità cablata che non ha mai avuto
materiale. Questo test le dà del materiale.

Il **controllo positivo** è la metà che conta: lo stesso identico fatto, con la
stessa query, ma **senza scadenza**, deve essere servito. Senza di esso un recall
che non trova mai nulla — per la query sbagliata, per il pavimento, per un indice
vuoto — passerebbe il test e non misurerebbe niente.
"""
import tempfile
import time

import pytest

FRASE = "Il deposito di Verona ospita quattromilaseicento pallet di ricambi."
FONTE = "Inventario: il deposito di Verona ospita 4600 pallet di ricambi."
QUERY = "quanti pallet ospita il deposito di Verona"


@pytest.fixture()
def store_isolato(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="test_scaduto_")
    monkeypatch.setenv("HIPPO_DATA_DIR", tmp)
    monkeypatch.setenv("ENGRAM_DATA_DIR", tmp)
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
    return tmp


def _serve(mem, query: str) -> list[str]:
    """Le proposizioni che il recall consegna per ``query``.

    ⚠️ `Memory.recall` rende un `Risultati` di **dict con chiave `text`**, non
    oggetti con `.proposition`: il primo giro di questo file leggeva il campo
    sbagliato e vedeva sempre una lista vuota — col risultato che il test sulla
    scadenza PASSAVA per il motivo sbagliato. L'ha preso il controllo positivo.
    """
    out = []
    for r in mem.recall(query, k=10) or []:
        p = None
        if isinstance(r, dict):
            p = r.get("text") or r.get("proposition")
        if p is None:
            p = getattr(r, "text", None) or getattr(r, "proposition", None)
        if p:
            out.append(str(p))
    return out


def test_senza_scadenza_il_fatto_si_trova(store_isolato):
    """CONTROLLO POSITIVO — senza questo, il test sotto non misura nulla.

    Se il recall non servisse questo fatto (query sbagliata, pavimento, indice
    vuoto), l'assenza del fatto scaduto non proverebbe che la scadenza morde.
    """
    from verimem import Memory

    m = Memory()
    m.add(FRASE, topic="test/scadenza-controllo", source=FONTE)
    serviti = _serve(m, QUERY)
    assert any("Verona" in s for s in serviti), (
        f"il recall non serve nemmeno il fatto SENZA scadenza: {serviti!r}. "
        f"Il test sulla scadenza non misurerebbe la scadenza"
    )


def test_con_valid_until_nel_passato_il_fatto_non_si_trova(store_isolato):
    """Il caso: stessa frase, stessa fonte, stessa query — solo scaduta."""
    from verimem import Memory

    m = Memory()
    ieri = time.time() - 86_400
    r = m.add(FRASE, topic="test/scadenza", source=FONTE, valid_until=ieri)
    salvato = m.semantic.get(r["id"])
    assert salvato is not None, "il fatto scaduto dev'essere comunque SCRITTO"
    assert salvato.valid_until is not None, (
        "controllo del controllo: se `valid_until` non fosse stato persistito, "
        "l'assenza dal recall avrebbe un'altra causa e questo test mentirebbe"
    )

    serviti = _serve(m, QUERY)
    assert not any("Verona" in s for s in serviti), (
        f"un fatto con valid_until nel PASSATO viene ancora servito: {serviti!r}. "
        f"`_fact_is_stale` riceve il valore ma non morde sul percorso del recall"
    )
