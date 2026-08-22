"""Il caso protetto da DUE guardie insieme, e da nessuna delle due da sola.

2026-08-22. Censendo il loop di `run_validation_gate` una guardia alla volta —
spegnerla, guardare se il numero si muove — tre guardie su cinque risultavano
INERTI. Il numero e' giusto e la conclusione che invitava a trarre e' falsa::

    references_fact ON  + `if ea or eb` ON    ritirati=0   protetto
    references_fact OFF + `if ea or eb` ON    ritirati=0   l'ALTRA copre
    `if ea or eb` OFF   + references_fact ON  ritirati=0   l'ALTRA copre
    ENTRAMBE OFF                              ritirati=1   il fatto vero si perde

Sono mutuamente ridondanti: provata da sola ognuna sembra morta, perche' l'altra
raccoglie il caso. Un censimento a variabile singola non puo' vederlo, e chi lo
leggesse come «se ne possono togliere tre» produrrebbe esattamente il difetto che
quelle guardie esistono per impedire — un fatto vero cancellato in silenzio.

PERCHE' QUESTO PRESIDIO NON NOMINA NESSUNA GUARDIA. Presidiare «la guardia X e'
accesa» lega il test a un'implementazione: oggi ne bastano due, domani una terza
puo' sostituirle entrambe e il test direbbe rosso su un prodotto sano. E il verso
opposto e' peggio — un presidio scritto sul NOME di una funzione interna muore
quando qualcun altro cura lo stesso difetto in un altro modo (misurato oggi: un
mio file di test e' caduto con `ImportError` perche' la cura era entrata in una
forma diversa dalla mia). Qui si inchioda il COMPORTAMENTO, dalla porta: chiunque
lo garantisca, deve continuare a garantirlo.

⚠️ REGIME: rotta lessicale `same-source`, ENGRAM_SUPERSEDE_SAME_SOURCE=enforce.
Sotto pytest l'embedder e' uno stub su SHA-256 (`conftest`), quindi la rotta
semantica non riconosce i due fatti come contraddittori e nessuna supersessione
avverrebbe: un presidio scritto su quella rotta passerebbe anche a difetto
presente. Il CONTROLLO POSITIVO qui sotto e' cio' che lo dimostra ogni volta.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from verimem.client import Memory

FONTE = ["source-doc:coda:1"]
SORGENTE = ("verbale: la coda aveva 500 elementi\n"
            "rettifica: la coda aveva 540 elementi\n")


def _ritiri(seconda: str) -> tuple[int, str]:
    """Scrive due fatti sulla stessa source e conta i ritiri.

    `seconda` puo' contenere `{fid}`: viene sostituito con l'id del PRIMO fatto,
    che e' il modo in cui un chiamante cita esplicitamente cio' che sta
    rettificando.
    """
    db = Path(tempfile.mkdtemp()) / "coppia.db"
    mem = Memory(str(db))
    prima = mem.add("La coda ha 500 elementi.", topic="t/coppia",
                    verified_by=FONTE, source=SORGENTE, validate="full")
    fid = prima.get("id") or prima.get("fact_id") or ""
    mem.add(seconda.format(fid=fid), topic="t/coppia",
            verified_by=FONTE, source=SORGENTE, validate="full")
    conn = sqlite3.connect(f"file:{mem.semantic.db_path}?mode=ro", uri=True)
    try:
        riga = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL").fetchone()
        return (int(riga[0]) if riga else 0), fid
    finally:
        conn.close()


def test_un_fatto_che_cita_l_id_di_un_altro_non_lo_ritira():
    """L'invariante. Diventa rosso solo se cadono TUTTE le guardie che lo
    coprono — che e' esattamente l'evento che nessun'altra misura vede."""
    ritiri, fid = _ritiri("La coda ha 540 elementi (rettifica del fatto {fid}).")
    assert ritiri == 0, (
        f"un fatto che cita esplicitamente {fid[:8]} lo ha comunque ritirato: "
        f"sono cadute tutte le guardie che coprivano questo caso, non una. "
        f"Provale a COPPIE, non una alla volta: da sola ognuna sembra inerte.")


def test_CONTROLLO_senza_la_citazione_il_ritiro_avviene_ancora():
    """Impedisce all'invariante di essere soddisfatto dal silenzio.

    Se il prodotto smettesse di superseder in generale — o se il banco finisse
    su una rotta che sotto pytest non vede nulla — il test qui sopra passerebbe
    per la ragione sbagliata. Questo lo rende impossibile: senza la citazione
    quel ritiro DEVE avvenire.
    """
    ritiri, _ = _ritiri("La coda ha 540 elementi.")
    assert ritiri == 1, (
        "la rettifica di uno stesso valore non aggiorna piu' il precedente: il "
        "presidio qui accanto non sta piu' misurando niente")
