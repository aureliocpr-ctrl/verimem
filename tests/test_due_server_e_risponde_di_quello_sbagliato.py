"""Due server, due scritture: chiedi di `nexus` e ti risponde di `alfa`.

IL CASO MINIMO del difetto che ws4 ha chiamato «catalogare tre cose ne perde
due». Qui ne bastano DUE, e il valore di questo file è che mostra il sintomo
**come lo vede chi usa il prodotto** invece del conteggio dei fatti vivi:

    m.add("Il server nexus di produzione ha 64 gigabyte di memoria RAM…")
    m.add("Il server alfa  di produzione ha 16 gigabyte di memoria RAM…")
    domanda: «quanta RAM ha il server NEXUS?»   ->   risponde di ALFA

🔑 E IL RETRIEVAL NON C'ENTRA — è la scoperta che questo banco isola. Chiedendo
lo stesso al recall senza il filtro sui superseduti:

    recall normale          : solo alfa   (0.860)
    include_superseded=True : nexus (0.929) PRIMO, poi alfa (0.860)

Il ranking mette `nexus` davanti, e con un margine netto: il sistema **sa**
qual è la risposta giusta. È la supersessione al write ad averla tolta dalla
vista. Ogni cura futura va misurata qui, non sul ranking.

E il danno è completo, non parziale: il punteggio della risposta SBAGLIATA
(0.8599) sta **sotto il pavimento del rumore** (0.8661) misurato sullo stesso
store. Il prodotto classifica quella risposta come rumore e la serve lo stesso,
perché è l'unica rimasta.

⚠️ QUESTO TEST DOCUMENTA UN DIFETTO APERTO, non una cura. È `xfail(strict=True)`
apposta: il giorno in cui qualcuno risolve il nodo, questo file FALLISCE e
obbliga a rileggerlo — che è il modo giusto perché una cura non passi
inosservata. Le strade già misurate e cadute sono cinque, elencate in
`verimem-criteri-falsificati-04-08.md`:
  alzare la soglia del rapporto (+0.000) · il residuo (0/6 sui numeri-identità)
  · conservare token corti e cifre (848→2293 coppie sopra soglia) · ≥2 token
  esclusivi fuori dalle quantità (65/65 evoluzioni bloccate) · prendere le
  sonde del pavimento dai topic lontani (0/3).
"""
from __future__ import annotations

import logging
import pathlib
import tempfile

import pytest

from verimem import Memory

logging.disable(logging.INFO)

NEXUS = "Il server nexus di produzione ha 64 gigabyte di memoria RAM installata."
ALFA = "Il server alfa di produzione ha 16 gigabyte di memoria RAM installata."
DOMANDA = "quanta RAM ha il server nexus?"


def _store() -> Memory:
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    m.add(NEXUS, topic="dc")
    m.add(ALFA, topic="dc")
    return m


@pytest.mark.xfail(reason="difetto APERTO: la supersessione ritira nexus. "
                          "Cinque strade misurate e cadute — vedi il docstring",
                   strict=True)
def test_chiedendo_di_nexus_si_riceve_nexus():
    """Il cuore, dal punto di vista di chi usa il prodotto: due macchine
    diverse, e la domanda ne nomina UNA."""
    hits = _store().semantic.recall(DOMANDA, k=3)
    assert hits, "nessun risultato"
    assert "nexus" in hits[0][0].proposition, (
        f"chiesto di NEXUS, risposto: «{hits[0][0].proposition[:60]}»")


def test_il_RANKING_invece_e_giusto():
    """La parte che funziona, e che va presidiata perché non venga «curata»
    per sbaglio insieme al resto: togliendo il filtro sui superseduti, il
    retrieval mette nexus PRIMO e con un margine netto. Il difetto è a
    monte — al write — non nel recupero."""
    hits = _store().semantic.recall(DOMANDA, k=3, include_superseded=True)
    assert hits, "nessun risultato"
    assert "nexus" in hits[0][0].proposition, (
        "il ranking non mette nexus primo: allora il difetto NON è solo della "
        "supersessione e questa diagnosi va rifatta")
    if len(hits) > 1:
        assert hits[0][1] > hits[1][1], "nexus non batte alfa nel punteggio"


def test_e_nexus_e_stato_SUPERSEDUTO_non_perso():
    """Dove finisce: il fatto è nel DB, marcato `superseded_by`. Non è
    cancellato — è invisibile al recall di default. La distinzione conta per
    chi un domani vorrà ripristinarlo: basta una WHERE."""
    m = _store()
    per_prop = {f.proposition[:20]: f for f in m.semantic.all()}
    nexus = next(f for k, f in per_prop.items() if "nexus" in f.proposition)
    alfa = next(f for k, f in per_prop.items() if "alfa" in f.proposition)
    assert getattr(nexus, "superseded_by", None), (
        "nexus non risulta superseduto: il meccanismo è cambiato, rileggere")
    assert not getattr(alfa, "superseded_by", None), "alfa non è vivo"
