"""«Quanti fatti parlano di zinco?» → 0, con dodici fatti che contengono zinco.

MISURATO su otto lingue, con i fatti NELLA LINGUA DELLA DOMANDA::

    lg  routing  n   atteso   termini estratti
    it  COUNT    12    12     «magazzino»
    it  COUNT     0    12     «fatti parlano zinco»     <-
    en  COUNT    12    12     «warehouse»
    en  COUNT     0    12     «facts zinc»              <-
    de  find      5    12     (routing non riconosciuto)
    fr  find      5    12     (routing non riconosciuto)
    es  find      5    12     (routing non riconosciuto)
    pt  find      5    12     (routing non riconosciuto)
    ROUTING 4/8 · CONTEGGIO 2/8

DUE DIFETTI DISTINTI, e questo file cura solo il secondo:
  ① il routing e' bilingue (IT/EN): de/fr/es/pt non riconosciute -> rispondono
    `5`, cioe' il valore di k, invece del totale. Dichiarato, non curato qui.
  ② il conteggio da' **0** perche' `content_terms` lascia dentro parole
    funzionali («fatti», «parlano», «facts») e il `count` le richiede TUTTE in
    AND: nessun fatto contiene «parlano».

⚠️ NON SI CURA LA STOPLIST: «curare tutte le 15 stoplist» e' gia' nella lista
delle strade falsificate di questa casa, perche' e' una lista infinita —
«parlano» c'e' ma «parlano» no, e domani sara' «citano» o «riguardano».

Si cura il SILENZIO: uno `0` su una domanda di conteggio e' la risposta
peggiore possibile — «non ho trovato niente» detto con certezza — e chi legge
non ha modo di sapere QUALE termine lo ha azzerato. Il conteggio per singolo
termine non decide nulla: MOSTRA. «zinco: 12, parlano: 0» si legge in un
secondo, e la diagnosi la fa chi ha scritto la domanda.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory


@pytest.fixture()
def magazzino(tmp_path):
    m = Memory(str(tmp_path / "mag.db"))
    for i in range(1, 13):
        m.add(f"Il magazzino K-{70 + i} contiene zinco per {100 + i} "
              f"chilogrammi.", topic="az/mag")
    return m


def test_un_conteggio_a_zero_dice_quale_termine_lo_ha_azzerato(magazzino):
    """IL CUORE: dodici fatti contengono «zinco», la risposta e' 0, e la
    ragione dev'essere leggibile senza aprire il codice."""
    rep = magazzino.ask("Quanti fatti parlano di zinco?")
    assert rep.get("count") == 0, "il difetto non si riproduce piu': rivedi il test"
    per_termine = rep.get("per_term")
    assert per_termine, f"nessuna diagnosi del conteggio a zero: {sorted(rep)}"
    assert per_termine.get("zinco") == 12, per_termine
    assert per_termine.get("parlano") == 0, per_termine


def test_il_totale_non_si_azzera_per_una_parola_che_non_esiste(magazzino):
    """LA CURA DEL 2026-08-25: mostrare il `per_term` non bastava, perche' chi
    legge il numero PROGRAMMATICAMENTE non lo vede.

    `per_term` e' prodotto da `client.py` e consumato da `cli.py` — e da
    nessun altro: `benchmark/competitor_probe_verimem.py:30` fa
    `mem.ask(...)["count"]`, cioe' il nostro stesso benchmark competitivo
    legge il campo che si azzerava. Un umano alla CLI vedeva la diagnosi, un
    programma prendeva lo zero.

    Un termine con conteggio individuale ZERO non compare in NESSUN fatto:
    non e' un criterio, e' rumore, e toglierlo dall'AND non inventa niente.
    """
    rep = magazzino.ask("Quanti fatti parlano di zinco?")
    # `count` NON cambia: e' il totale dell'AND, vero per definizione.
    assert rep.get("count") == 0, rep
    assert rep.get("per_term", {}).get("zinco") == 12, rep
    # Cio' che cambia e' che la lettura alternativa ESISTE come campo, invece
    # di stare solo dentro una tabella che il chiamante deve saper leggere.
    assert rep.get("count_without_absent_terms") == 12, (
        "la ricevuta non porta la lettura alternativa: chi legge `count` "
        f"programmaticamente non ha modo di sapere che esiste. {rep}")
    assert set(rep.get("absent_terms") or []) == {"fatti", "parlano"}, rep


def test_CONTROLLO_uno_zero_VERO_resta_zero(magazzino):
    """LA DIFESA, e senza di lei la cura sopra inventa numeri.

    Se i termini esistono TUTTI ma non compaiono insieme, lo zero e' la
    risposta giusta e va lasciata: «zinco» c'e' (12) e «K-77» c'e' (1), ma
    nessun fatto parla di zinco per il K-77 in quantita' 999. Degradare qui
    vorrebbe dire rispondere col conteggio di un ALTRO insieme di fatti.
    """
    rep = magazzino.ask("Quanti fatti parlano di zinco e di alluminio?")
    assert rep.get("count") == 0, (
        "un AND legittimo che non trova nulla e' stato degradato: la cura "
        f"sta inventando un numero. {rep}")
    # ⚠️ E QUI STA IL LIMITE, scritto perche' non si scopra per caso: la
    # lettura alternativa vale **12** anche in questo caso, dove la risposta
    # giusta e' zero. `count` non mente; `count_without_absent_terms` non e'
    # un totale piu' furbo, e' «cosa risponderebbe l'AND senza i termini che
    # non compaiono in nessun fatto» — e fra quelli c'e' «alluminio», che e'
    # contenuto e non rumore. Chi usa quel campo deve leggere `absent_terms`.
    assert rep.get("count_without_absent_terms") == 12, rep
    assert "alluminio" in (rep.get("absent_terms") or []), rep


def test_un_conteggio_che_torna_non_porta_la_diagnosi(magazzino):
    """IL PRESIDIO: la diagnosi costa una query per termine, quindi si paga
    SOLO quando serve. Un conteggio che risponde non la porta."""
    rep = magazzino.ask("Quante volte ho parlato del magazzino?")
    assert rep.get("count") == 12
    assert "per_term" not in rep


def test_un_termine_solo_non_porta_la_diagnosi(magazzino):
    """L'altro presidio: con UN termine il conteggio a zero non ha nulla da
    spiegare — non c'e' nessun AND che possa averlo azzerato."""
    rep = magazzino.ask("Quante volte ho parlato di alluminio?")
    assert rep.get("count") == 0
    assert "per_term" not in rep


def test_la_domanda_normale_resta_una_ricerca(magazzino):
    """La compatibilita': `ask` senza intento di conteggio non cambia."""
    rep = magazzino.ask("Cosa dice il magazzino K-77?")
    assert "count" not in rep
    assert rep.get("results") is not None
