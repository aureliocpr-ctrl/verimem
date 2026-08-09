"""Il fatto diceva «voto 98» e non c'era modo di sapere su cosa fosse stato dato.

IL DIFETTO, dalla fetta ⑦ del censimento (docs/stato-reale/07). Passi un
documento, verimem lo usa per giudicare, e poi lo BUTTA: nella tabella resta solo
un'impronta::

    source_signature   sha256:7146fe197ddf6418

⇒ puoi sapere che due fatti vengono dalla STESSA fonte
⇒ NON puoi più sapere COSA diceva quella fonte
⇒ davanti a un fatto con voto 98, non puoi rivedere su cosa è stato dato

⚠️ VERIFICATO A DUE LIVELLI, non dedotto: la fonte non è nel database (30 colonne,
solo l'impronta) e non è nel giornale degli eventi (14.920 righe, chiavi dentro
``payload``: surface, fact_id, topic, status, stored, layers… nessun campo che la
contenga). **Non esiste da nessuna parte.**

Per un prodotto che si chiama memoria VERIFICATA è il limite che pesa di più: la
verifica c'è, la **prova** della verifica no.

📌 LA CURA ERA GIÀ SCRITTA, e la strada giusta era la seconda che ho provato::

    ⛔ fact_grounding_span(llm, source, fact) -> {"score", "span"}
       docstring perfetto, ma PRETENDE un LLM conversazionale con .complete().
       Misurato: fact_grounding_score_ex(None, …) -> (97.39, 'local') FUNZIONA,
       fact_grounding_span(None, …) -> AttributeError. Il gate gira col
       cross-encoder LOCALE (Client().grounding_llm è None), quindi questa
       funzione NON PUÒ girare nel percorso di default: usarla significherebbe
       chiamare un modello remoto a ogni scrittura.

    ✅ select_relevant_span(source, fact, *, budget) -> str
       «Pure + deterministic — no embeddings». Misurato su 500 chiamate:
       **0,046 ms** contro i 32.800 ms del giudice, e soprattutto **non tocca il
       punteggio**: il rischio sui verdetti di ammissione è ZERO.

🔑 La differenza fra le due è una categoria che non avevamo: non «codice morto» né
«codice pronto e scollegato», ma **codice pronto per una configurazione che il
prodotto non usa**. Sembra la seconda e si comporta come la prima.
"""
from __future__ import annotations

import pytest

from verimem.grounding_gate import select_relevant_span

VERBALE = (
    "Verbale riunione 3 marzo 2026. Presenti: Bianchi, Rossi.\n"
    "Il magazzino di Verona contiene 480 pallet a scaffale.\n"
    "La consegna e' prevista per il 15 aprile.\n"
    "Il contratto con Ferrero vale 4500 euro.\n"
    "Varie ed eventuali: nessuna."
)


def test_la_porzione_di_fonte_contiene_la_riga_che_sostiene_il_fatto():
    """IL CUORE: chi legge un fatto deve poter vedere DA COSA è stato verificato.
    Non il documento intero — la riga."""
    span = select_relevant_span(
        VERBALE, "Il magazzino di Verona contiene 480 pallet.", budget=120)
    assert "480 pallet a scaffale" in span


def test_fatti_DIVERSI_dalla_stessa_fonte_ricevono_porzioni_diverse():
    """⚠️ IL PRESIDIO che distingue una selezione VERA da «restituisce sempre
    l'inizio del documento»: due fatti diversi devono pescare righe diverse."""
    a = select_relevant_span(VERBALE, "Il contratto con Ferrero vale 4500 euro.",
                             budget=60)
    b = select_relevant_span(VERBALE, "La consegna e' prevista per il 15 aprile.",
                             budget=60)
    assert "4500 euro" in a
    assert "15 aprile" in b
    assert a != b


def test_una_fonte_piu_corta_del_budget_torna_intera():
    """Il caso più comune in pratica: chi passa una riga sola come fonte deve
    ritrovarla identica, non un troncone."""
    fonte = "Inventario: il magazzino di Trento contiene 90 pallet."
    assert select_relevant_span(fonte, "Trento ha 90 pallet.", budget=500) == fonte


def test_il_budget_e_rispettato_su_una_fonte_lunga():
    """Il costo su disco dipende da questo: se il budget non tenesse, conservare
    la porzione equivarrebbe a conservare il documento."""
    lunga = "\n".join(f"Riga {i}: contenuto di riempimento del verbale." for i in range(400))
    span = select_relevant_span(lunga + "\nIl magazzino di Verona contiene 480 pallet.",
                                "Il magazzino di Verona contiene 480 pallet.",
                                budget=200)
    assert len(span) <= 200 + 80        # il taglio è per unità, non per carattere
    assert "480 pallet" in span


def test_e_DETERMINISTICA_lo_stesso_fatto_da_sempre_la_stessa_porzione():
    """⚠️ Serve perché la porzione finisce nel database: se cambiasse a ogni
    chiamata, due esecuzioni dello stesso write darebbero prove diverse dello
    stesso fatto."""
    fatto = "Il magazzino di Verona contiene 480 pallet."
    valori = {select_relevant_span(VERBALE, fatto, budget=120) for _ in range(20)}
    assert len(valori) == 1


def test_LIMITE_DICHIARATO_un_fatto_NON_sostenuto_riceve_comunque_una_porzione():
    """⚠️ Il limite, scritto invece che nascosto: la funzione SELEZIONA, non
    giudica. Per un fatto che la fonte non sostiene restituisce comunque le righe
    più simili.

    Non è un difetto, ed è una scelta che va portata all'utente e non sepolta
    qui: il giudizio ce l'ha già il punteggio (0,32 su 100 per questo caso), e
    vedere COSA il giudice ha guardato senza trovarlo convincente è informativo —
    è la differenza fra «non ti credo» e «non ti credo, ed ecco cosa ho letto».
    """
    span = select_relevant_span(VERBALE, "L'ordine 77 conteneva 40 pezzi.",
                                budget=120)
    assert span                      # non è vuoto
    assert "ordine 77" not in span   # e non inventa: quella riga non c'è


# ── LA PORTA DEL PRODOTTO ───────────────────────────────────────────────────
# Sopra si misura la funzione. Qui si misura ciò che l'utente ottiene davvero:
# scrivo un fatto e vado a guardare nel database. È il livello che conta, ed è
# quello a cui questa casa ha già sbagliato («ho promesso una supersessione
# avendo misurato il detector», 2026-08-07).

def test_LA_PORTA_la_prova_arriva_davvero_nel_database(tmp_path, monkeypatch):
    """END-TO-END: `add(..., source=...)` deve lasciare nel database sia il voto
    sia la porzione di fonte che lo giustifica."""
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    import sqlite3

    from verimem.client import Client

    c = Client()
    c.add("Il magazzino di Verona contiene 480 pallet.", topic="t", source=VERBALE)
    cx = sqlite3.connect(str(c.semantic.db_path))
    voto, prova = cx.execute(
        "SELECT grounding_score, grounding_span FROM facts").fetchone()
    assert voto is not None and voto > 50
    assert prova and "480 pallet a scaffale" in prova


def test_LA_PORTA_un_fatto_SENZA_fonte_non_rompe_e_non_inventa(tmp_path, monkeypatch):
    """⚠️ LA POPOLAZIONE OPPOSTA, e il banco l'ha presa al primo giro: la prima
    versione della cura calcolava lo span solo dentro il ramo «c'è una fonte», e
    ogni scrittura SENZA fonte moriva con un NameError.

    Non è un caso di bordo: nel corpus di casa i fatti senza fonte sono 4.279 su
    6.425 serviti — i due terzi. La cura avrebbe rotto il caso più comune del
    prodotto, e sarebbe passata se avessi misurato solo i fatti con fonte.
    """
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    import sqlite3

    from verimem.client import Client

    c = Client()
    c.add("Il magazzino di Trento contiene 90 pallet.", topic="t")   # nessuna fonte
    cx = sqlite3.connect(str(c.semantic.db_path))
    voto, prova = cx.execute(
        "SELECT grounding_score, grounding_span FROM facts").fetchone()
    assert voto is None      # nessun giudice è girato: non c'era niente da giudicare
    assert prova is None     # e nessuna prova inventata
