"""Sopra le sei cifre nessun ramo di `event_indices` vede più un indice.

I due rami che portano un tetto hanno lo STESSO tetto, quindi il posizionale non
allarga il vocabolario su questo asse: cadono insieme.

    _EVENT_INDEX_RE     (day|issue|run|riga|lotto|…)\\s*(?:#\\s*)?(\\d{1,6})\\b
    _GENERIC_INDEX_RE   ([A-Za-z][A-Za-z_-]{2,})\\s*(?:#\\s*)?(\\d{1,6})\\b
    _ALNUM_CODE_RE      ([A-Za-z]{1,6})(\\d{2,})\\b     senza tetto, ma vuole le
                                                       lettere ATTACCATE al numero

⚠️ NON È UN CASO DI LABORATORIO. Misurato il 2026-08-20 sul corpus vivo
(`CONFIG.semantic_db`, 12816 proposizioni lette in una sola esecuzione, repo
fermo a `79f6adff` prima e dopo):

    con la forma «<parola> <intero di 7+ cifre>» nel claim ... 1440
       di cui `event_indices()` restituisce INSIEME VUOTO .... 125
       di cui già superseduti ...............................   9

E il danno è già avvenuto. Su 1928 coppie di supersessione, DUE hanno lo stesso
scheletro con numeri diversi, e sono una per popolazione:

    [indice riconosciuto] «…il campo n_facts vale 7.» -> «vale 3.»
                          un VALORE che cambia: supersessione giusta
    [nessun indice]       «Nel run ci 32356952191 … 3 failed, 11685 passed»
                       -> «Nel run ci 32357232783 … 2 failed, 11686 passed»
                          DUE RUN DIVERSI, collassati in uno

⚠️ Il numero da NON usare è 1440: in 1315 di quelle proposizioni c'è anche un
intero corto che fa da indice, quindi la frase non è cieca. Il numero è 125.
E «superseduto» non vuol dire «cancellato per sbaglio»: i 9 vanno guardati uno
per uno, non contati come vittime.

📌 LIVELLO DICHIARATO: qui si misura `event_indices`. Il caso reale sopra viene
dal corpus, non da questo file, ed è citato perché senza di lui questo banco
sembrerebbe un esercizio.

📌 PERCHÉ NON C'È ANCHE LA CURA: sembra `\\d{1,6}` -> `\\d{1,12}` in due regex,
ma cambierebbe il verdetto sui 1315 fatti che oggi hanno un indice corto e ne
guadagnerebbero un secondo. Quel numero non è misurato, e finché non lo è la
cura non si consegna.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import _EVENT_INDEX_RE, _GENERIC_INDEX_RE, event_indices

#: Un identificatore per lunghezza. Sei e sette cifre sono i due lati del tetto:
#: se un giorno si muove, sono le due celle che lo dicono per prime.
CORTI = ("42", "4242", "424242")
LUNGHI = ("4242424", "32356952191")

#: `issue` sta nel vocabolario dell'estrattore, `widget` in nessun elenco: le due
#: forme sono qui insieme perché il punto è che il tetto le fa cadere ENTRAMBE.
PORTATRICI = ("issue", "widget")


def _indice(portatrice: str, cifre: str) -> set:
    return event_indices(f"Il tracker mostra {portatrice} {cifre} in questo momento.")


@pytest.mark.parametrize("cifre", CORTI)
@pytest.mark.parametrize("portatrice", PORTATRICI)
def test_un_identificatore_fino_a_sei_cifre_e_un_indice(portatrice: str, cifre: str):
    """Il lato che funziona, e che una cura al tetto non deve far cadere."""
    assert (portatrice, int(cifre)) in _indice(portatrice, cifre), (
        f"«{portatrice} {cifre}» non è più un indice: {len(cifre)} cifre stanno "
        f"sotto il tetto di 6 e questo lato era verde il 2026-08-20")


@pytest.mark.parametrize("cifre", LUNGHI)
@pytest.mark.parametrize("portatrice", PORTATRICI)
@pytest.mark.xfail(strict=True, reason=(
    "APERTO 2026-08-20. Entrambi i rami con tetto usano `\\d{1,6}`, quindi sopra "
    "le sei cifre né il vocabolario né il posizionale vedono l'indice, e due "
    "fatti che parlano di due identificatori diversi si leggono come lo stesso "
    "soggetto. Misurato sul corpus vivo: 125 proposizioni restano senza alcun "
    "indice, 9 sono già superseduta, e una coppia di run CI si è cancellata a "
    "vicenda. strict=True: il giorno che il tetto si alza questi diventano "
    "XPASS e la suite chiede di togliere il marcatore."))
def test_un_identificatore_di_sette_o_piu_cifre_dovrebbe_essere_un_indice(
        portatrice: str, cifre: str):
    assert (portatrice, int(cifre)) in _indice(portatrice, cifre), (
        f"«{portatrice} {cifre}»: {len(cifre)} cifre superano il tetto di 6 e "
        f"l'identificatore non viene più riconosciuto")


def test_i_due_rami_col_tetto_hanno_LO_STESSO_tetto():
    """Se qualcuno ne allarga uno solo, questo lo dice prima che sembri curato.

    È la ragione per cui «il posizionale allarga il vocabolario» non vale su
    questo asse: sul numero di cifre i due rami sono identici, quindi cadono
    insieme e nessuno dei due copre l'altro.
    """
    tetti = {"_EVENT_INDEX_RE": _EVENT_INDEX_RE.pattern.count(r"\d{1,6}"),
             "_GENERIC_INDEX_RE": _GENERIC_INDEX_RE.pattern.count(r"\d{1,6}")}
    assert all(tetti.values()), (
        f"un ramo non ha più il tetto \\d{{1,6}}: {tetti}. Se è stato allargato, "
        f"gli xfail di questo file vanno rimisurati — e se ne è stato allargato "
        f"UNO SOLO, l'asse è diventato asimmetrico senza che nessuno lo dica")


def test_il_caso_REALE_del_corpus_e_ancora_cieco():
    """Le due frasi vere che si sono cancellate a vicenda nello store.

    Non è una parafrasi: sono copiate dal corpus il 2026-08-20, ed è la ragione
    per cui questo file esiste invece di essere una nota in un messaggio.
    """
    perdente = ("Nel run ci 32356952191 il job test (ubuntu-latest / py3.12) "
                "riporta 3 failed, 11685 passed.")
    vincitore = ("Nel run ci 32357232783 il job test (ubuntu-latest / py3.12) "
                 "riporta 2 failed, 11686 passed.")
    assert not (event_indices(perdente) & event_indices(vincitore)), (
        "i due run condividono un indice: se è successo perché il tetto si è "
        "alzato, questo test ha finito il suo lavoro e va tolto")
    assert 32356952191 not in {n for _, n in event_indices(perdente)}, (
        "l'identificatore del run è diventato un indice: il tetto si è alzato "
        "e gli xfail di questo file sono da rimisurare")
