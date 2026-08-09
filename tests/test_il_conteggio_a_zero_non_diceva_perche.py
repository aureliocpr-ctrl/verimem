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
