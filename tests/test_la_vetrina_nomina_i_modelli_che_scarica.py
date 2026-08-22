"""La tabella dei costi del README nomina TUTTI i modelli che `warmup` scarica.

Il difetto, misurato il 19/08 alle 19:20 su questa macchina (Windows, py3.13):

    README:230   | first `verimem warmup` — embedding model + gate model | **~2.3 GB** |
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^ DUE modelli

    ma `warmup` ne scarica TRE, e il terzo pesa 470 MB:
        intfloat/multilingual-e5-base                    1083 MB  (misurato: du -sm)
        cross-encoder/mmarco-mMiniLMv2-L12-H384-v1        470 MB  <- MAI NOMINATO
        local_gate_ce_v2                                  712 MB
        ------------------------------------------------------
                                                         2265 MB  = ~2,2 GB

⇒ **Il numero della vetrina regge, l'elenco no.** Il totale dichiarato (~2,3 GB)
corrisponde a TRE modelli — chi l'ha misurato il 15/08 (`58a139c9`: «primo
warmup: modello di indicizzazione + giudice 2,26 GB») ha misurato la cartella
giusta e l'ha etichettata con due modelli su tre.

⚠️ E il reranker non è nominato NEMMENO ALTROVE fra i costi: nel README la
parola «rerank» compare 3 volte — due dentro esempi di ricevute, una in un
diagramma d'architettura che lo chiama «optional reranker». Misurato invece
alla porta, sul prodotto e senza nessuna env impostata:

    >>> semantic._rerank_enabled()
    True

⇒ **La vetrina lo chiama opzionale, il prodotto lo scarica di default.** La
conseguenza pratica è la sola che conti per chi installa: il README documenta
`warmup --no-gate` per risparmiare i 656 MB del giudice, e chi volesse
risparmiare gli altri 470 non sa nemmeno che esistono.

📌 IL CODICE NON HA QUESTO DIFETTO — ed è la ragione per cui il presidio va
sulla vetrina e non sul comando. `_MODEL_DOWNLOAD_MB` (curata il 19/08 con
`16bcd607` ed `edc1e9fe`) annuncia entrambi i modelli HF con la loro cifra, e
`test_il_download_annunciato_e_quello_del_modello_in_uso.py` lo presidia. Il
giudice ha la sua cifra presidiata da `test_il_costo_dichiarato_e_lo_stesso_
ovunque.py`. Sono le tre cifre giuste in tre posti giusti: **manca il legame fra
la lista del prodotto e la lista della vetrina**, ed è quello che si aggiunge qui.

⚠️⚠️ PERCHÉ IL CRITERIO NON È «CONTA LA PAROLA `model` NELLA RIGA»: sarebbe
sintattico su un fenomeno semantico — la stessa trappola che
`test_il_comando_non_annuncia_piu_un_download_senza_cifra` ha pagato scrivendosi
(l'«1» di «R@1» assolveva la riga). «embedding, rerank and gate models» ha UN
solo «models» e nomina tutti e tre: il conteggio lo direbbe rosso a torto. Qui
si cercano i RUOLI, che è ciò che il lettore deve trovare.

E il terzo test è quello che impedisce a questo file di invecchiare in silenzio:
lega il numero dei ruoli attesi al numero di modelli che il PRODOTTO scarica. Un
quarto modello domani rende rosso questo file invece di scivolare in vetrina non
dichiarato — che è esattamente com'è entrato il reranker.
"""
from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
README = RADICE / "README.md"

#: I RUOLI che la riga dei costi deve nominare, uno per modello scaricato.
#: Non sono i nomi HF (in vetrina non compaiono e non devono): sono le parole
#: con cui il lettore riconosce il modello. Il terzo test tiene questa lista
#: legata a quanti modelli il prodotto scarica davvero.
RUOLI_ATTESI = ("embedding", "rerank", "gate")


def _riga_del_warmup() -> str:
    """La riga della tabella dei costi che parla del primo `warmup`.

    Cercata per il comando che nomina, non per numero di riga: una riga
    aggiunta sopra non deve rompere il collaudo.
    """
    for riga in README.read_text(encoding="utf-8").splitlines():
        if riga.startswith("|") and "verimem warmup" in riga:
            return riga
    raise AssertionError(
        "nella tabella dei costi del README non c'è più una riga per "
        "`verimem warmup`: se è stata tolta, il lettore non sa più quanto "
        "scarica al primo avvio")


def _quanti_modelli_scarica_warmup() -> int:
    """Quanti modelli il comando scarica, chiesto AL PRODOTTO.

    ⚠️ IL `+1` ERA UN'ASSUNZIONE SULLA STRUTTURA, ED È CADUTA IL 2026-08-21.
    Questa funzione sommava «i modelli della tabella» + 1, perché il giudice del
    moat aveva una sua via (una release pubblica) e non compariva lì. Poi
    `904be678` — «warmup: annunciava un terzo di quello che scarica» — ha messo
    anche il giudice nella tabella, per poter dichiarare il totale vero::

        intfloat/multilingual-e5-base                1082 MB   embedding
        cross-encoder/mmarco-mMiniLMv2-L12-H384-v1    470 MB   rerank
        local_gate_ce_v2                              746 MB   gate  <- il giudice

    Da quel momento il `+1` conta il giudice DUE VOLTE: il prodotto scarica
    TRE modelli e questa funzione ne dichiarava quattro.

    🔑 E il difetto non era innocuo: il messaggio d'errore chiedeva «aggiungere
    il ruolo del modello n.4», cioè mandava a scrivere in vetrina un modello che
    non esiste. Un presidio che sbaglia induce a peggiorare la cosa che sorveglia.

    Adesso si chiede alla tabella e basta — che è l'unica fonte, da quando il
    giudice ci è dentro.
    """
    from verimem.cli import _MODEL_DOWNLOAD_MB
    return len(_MODEL_DOWNLOAD_MB)


def test_la_riga_dei_costi_nomina_ogni_modello_che_il_comando_scarica():
    """Il difetto: nominava «embedding model + gate model» e ne scaricava tre."""
    riga = _riga_del_warmup().lower()
    mancanti = [r for r in RUOLI_ATTESI if r not in riga]
    assert not mancanti, (
        f"la riga dei costi del primo warmup non nomina {mancanti}: «{riga.strip()}». "
        f"Il comando scarica {_quanti_modelli_scarica_warmup()} modelli e la vetrina "
        f"ne nomina meno — chi legge non sa cosa sta per prendere, e non sa "
        f"nemmeno che potrebbe evitarlo")


def test_il_criterio_riconoscerebbe_il_difetto():
    """Controllo positivo: sul testo di PRIMA il collaudo deve essere rosso.

    Senza questo, un criterio che non guarda niente resterebbe verde per
    sempre — e sarebbe indistinguibile da uno che funziona.
    """
    riga_di_prima = "| first `verimem warmup` — embedding model + gate model | **~2.3 GB** |"
    mancanti = [r for r in RUOLI_ATTESI if r not in riga_di_prima.lower()]
    assert mancanti == ["rerank"], (
        f"col testo che aveva il difetto il criterio doveva accusare il reranker "
        f"e ha accusato {mancanti}: il criterio non misura ciò che dice")


def test_l_elenco_dei_ruoli_resta_legato_a_quanti_modelli_il_prodotto_scarica():
    """L'anello che impedisce a questo file di invecchiare in silenzio.

    Il reranker è entrato in `warmup` senza che nessuno aggiornasse la vetrina.
    Se domani entra un quarto modello, questo test diventa rosso e obbliga a
    dire in vetrina che c'è — invece di lasciarlo scivolare dentro come è
    successo al terzo.
    """
    quanti = _quanti_modelli_scarica_warmup()
    assert len(RUOLI_ATTESI) == quanti, (
        f"il prodotto scarica {quanti} modelli e questo collaudo ne presidia "
        f"{len(RUOLI_ATTESI)} ({list(RUOLI_ATTESI)}): aggiungere il ruolo del "
        f"modello nuovo qui E nella tabella dei costi del README")


def test_la_riga_dei_costi_porta_ancora_una_cifra():
    """Tiene onesti i tre sopra: la via più facile per farli passare tutti è
    riscrivere la riga elencando i ruoli e togliendo il numero. Allora la
    vetrina direbbe COSA si scarica e non più QUANTO, che per chi installa è
    l'informazione che conta."""
    riga = _riga_del_warmup()
    assert re.search(r"\d[\d.,]*\s*(GB|MB)", riga, re.IGNORECASE), (
        f"la riga dei costi non dichiara più una taglia: «{riga.strip()}»")
