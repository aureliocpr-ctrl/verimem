"""Tre consegne in tre date diverse: in inglese restano tre, in italiano una.

IL DIFETTO, misurato scrivendo la stessa cosa in tre forme::

    «La consegna a Prato e' avvenuta il 2026-03-12 / 04-20 / 05-30»
        scritti 3  ->  VIVI 1     (due superseded_by)
    «La visita a Chieti e' avvenuta il 12 marzo / 20 aprile / 30 maggio 2026»
        scritti 3  ->  VIVI 1
    «The audit in Turin took place on 12 March / 20 April / 30 May 2026»
        scritti 3  ->  VIVI 3     ✅

E il gate lo dice in chiaro, se glielo si chiede::

    ISO       ->  L3-supersession
    mese IT   ->  L3-supersession
    mese EN   ->  L3-coexistence   «a contradiction was found but both kept»

🔑 LA CAUSA È UN ACCIDENTE ORTOGRAFICO. La guardia che tiene in vita entrambi i
fatti è ``_entita_diverse`` (la cella 6), e riconosce le entità dalle MAIUSCOLE::

    EN   proper = {march} vs {april}    diverse -> la guardia blocca il ritiro
    IT   proper = {chieti} vs {chieti}  uguali  -> nessuna guardia
    ISO  proper = {prato}  vs {prato}   uguali  -> nessuna guardia

L'inglese scrive i mesi maiuscoli, l'italiano no, e il formato ISO non ha
nessuna parola. **Quella guardia — che ho scritto io — protegge una lingua sola,
e non per come è stata progettata: per come si scrivono i mesi in inglese.** È
la classe ③ di questa casa (liste monolingue in un prodotto mondiale) nella sua
forma più pura, perché qui non c'è nemmeno una lista da tradurre: c'è una regola
ortografica che vale in una lingua e in un'altra no.

⚠️ E COLPISCE IL NODO PIÙ COSTOSO CHE ABBIAMO: «catalogare tre cose ne perde
due» (`05c4619fcd83`), il 31% di memoria che non risponde. Un registro di
consegne, un calendario di visite, uno storico di ispezioni — tutto ciò che è
**una serie di eventi datati** — sopravvive in inglese e viene mangiato in
italiano.

LA CURA, e perché non inventa una politica nuova: **una data diversa rende due
asserzioni due EVENTI, non due versioni**. È esattamente ciò che il prodotto già
fa in inglese; qui si toglie all'inglese il privilegio accidentale e lo si
estende. La direzione è anche quella già decisa in casa dopo che otto criteri
sono caduti: *«non cancellare al write è l'unica strada che non chiede
l'impossibile»*.

⚠️ IL CASO CHE NON DEVE ROMPERSI, ed è la popolazione opposta: un valore che
cambia NEL TEMPO resta un'evoluzione. «Il prezzo del contratto è 100» → «il
prezzo del contratto è 120» deve continuare a ritirare il vecchio, altrimenti
la memoria smette di aggiornarsi — che è l'anti-tesi del prodotto.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory


def _vivi(mem, topic: str) -> int:
    """Quanti fatti di quel topic sono ancora SERVITI.

    ⚠️ Non basta ``superseded_by IS NULL``: un quarantinato è non-superseduto e
    invisibile. È l'errore con cui in questa casa si è annunciato «25 su 25
    vive» quando i serviti erano 1.
    """
    c = sqlite3.connect(str(mem.semantic.db_path))
    try:
        return c.execute(
            "SELECT COUNT(*) FROM facts WHERE topic=? AND superseded_by IS NULL "
            "AND status NOT IN ('quarantined','user_belief')", (topic,)
        ).fetchone()[0]
    finally:
        c.close()


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


@pytest.mark.parametrize("nome,frasi", [
    ("iso", ["La consegna a Prato e' avvenuta il 2026-03-12.",
             "La consegna a Prato e' avvenuta il 2026-04-20.",
             "La consegna a Prato e' avvenuta il 2026-05-30."]),
    ("mese_it", ["La visita a Chieti e' avvenuta il 12 marzo 2026.",
                 "La visita a Chieti e' avvenuta il 20 aprile 2026.",
                 "La visita a Chieti e' avvenuta il 30 maggio 2026."]),
])
def test_tre_eventi_datati_restano_tre(mem, nome, frasi):
    """IL CUORE. Un registro di consegne non è un valore che si aggiorna: sono
    tre fatti, e perderne due è perdere il registro."""
    fonte = " ".join(frasi)
    for f in frasi:
        mem.add(f, topic=f"az/{nome}", source=fonte)
    assert _vivi(mem, f"az/{nome}") == 3, (
        f"{nome}: dei tre eventi ne sopravvivono meno di tre")


def test_CONTROLLO_POSITIVO_l_inglese_continua_a_tenerli_tutti(mem):
    """⚠️ La popolazione che GIÀ funzionava, e il riferimento della cura: se
    cadesse, avrei allineato l'inglese all'italiano invece del contrario."""
    frasi = ["The audit in Turin took place on 12 March 2026.",
             "The audit in Turin took place on 20 April 2026.",
             "The audit in Turin took place on 30 May 2026."]
    for f in frasi:
        mem.add(f, topic="az/en", source=" ".join(frasi))
    assert _vivi(mem, "az/en") == 3


def test_CONTROLLO_POSITIVO_un_valore_che_CAMBIA_si_aggiorna_ancora(mem):
    """⚠️⚠️ IL PRESIDIO CHE VALE PIÙ DELLA CURA. Senza data, un valore nuovo
    sullo stesso soggetto DEVE continuare a ritirare il vecchio: una memoria che
    non si aggiorna più è l'anti-tesi del prodotto, ed è già successo qui una
    volta (`ENGRAM_SUPERSEDE_SAME_SOURCE=0`)."""
    fonte = "Listino: il contratto con Rossi vale 100 euro, poi aggiornato a 120 euro."
    mem.add("Il contratto con Rossi vale 100 euro.", topic="az/prezzo", source=fonte)
    mem.add("Il contratto con Rossi vale 120 euro.", topic="az/prezzo", source=fonte)
    assert _vivi(mem, "az/prezzo") == 1, (
        "il valore vecchio non è più stato ritirato: la memoria ha smesso di "
        "aggiornarsi")


def test_una_STESSA_data_ripetuta_resta_una_evoluzione(mem):
    """L'altro lato del criterio: è la data DIVERSA a fare due eventi. Con la
    stessa data si sta parlando dello stesso momento, e un valore nuovo lo
    aggiorna — altrimenti «date» diventerebbe un lasciapassare per non essere
    mai superseduti."""
    fonte = ("Verbale del 2026-03-12: erano presenti 40 operai; il conteggio "
             "definitivo del 2026-03-12 e' 45 operai.")
    mem.add("Il 2026-03-12 erano presenti 40 operai.", topic="az/stessa", source=fonte)
    mem.add("Il 2026-03-12 erano presenti 45 operai.", topic="az/stessa", source=fonte)
    assert _vivi(mem, "az/stessa") == 1
