"""«az/mag» e «az/mag » sono due contenitori diversi, e nessuno lo dice.

MISURATO DA UTENTE, sei scritture con varianti dello stesso topic::

    count(topic='az/mag')     = 1
    count(topic='az/mag ')    = 1     <- silo separato
    count(topic=' az/mag')    = 1     <- un altro
    count(topic='AZ/MAG')     = 1     <- un altro ancora
    count(topic_prefix='az/') = 3     <- il PREFISSO normalizza il case…
    count(topic_prefix='AZ/') = 3        …ma non gli spazi

Un topic è la CHIAVE con cui si separa e si ritrova. Uno spazio finale da
copia-incolla crea un contenitore che non si troverà mai cercando quello
giusto — e le due superfici hanno semantiche diverse: il prefisso ignora le
maiuscole, il topic esatto no.

⚠️ NON SI NORMALIZZA, ed è una scelta con un motivo. Sul corpus vero il danno
NON ESISTE ANCORA — 5716 topic distinti, **0** con spazi ai bordi, **0**
collisioni normalizzando. E `topic` è la chiave usata anche per l'isolamento
fra tenant (`topic_prefix`): cambiare la normalizzazione di una chiave del
genere, per un difetto con zero istanze misurate, è un rischio sproporzionato
al beneficio.

Si DICHIARA invece: chi scrive un topic con spazi ai bordi lo scopre subito,
il comportamento non cambia di una virgola, e la decisione resta sua.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

FATTO = "Il magazzino K-71 ha 4100 metri quadrati."


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def _avvisi(ricevuta):
    return [w for w in (ricevuta.get("warnings") or [])
            if str(w.get("layer", "")) == "topic_spazi"]


@pytest.mark.parametrize("topic", ["az/mag ", " az/mag", " az/mag ", "az/mag\t"])
def test_un_topic_con_spazi_ai_bordi_si_dichiara(mem, topic):
    """IL CUORE: chi ha incollato uno spazio lo scopre alla scrittura, non fra
    un mese cercando dei fatti che «sono spariti»."""
    ric = mem.add(FATTO, topic=topic)
    avvisi = _avvisi(ric)
    assert avvisi, f"topic {topic!r}: nessun avviso — {ric.get('warnings')}"
    assert repr(topic.strip()) in str(avvisi[0]) or topic.strip() in str(avvisi[0])


def test_il_fatto_ENTRA_e_il_topic_NON_viene_toccato(mem):
    """IL PRESIDIO PRINCIPALE. Si dichiara, non si corregge: il topic resta
    quello che chi scrive ha passato — è una CHIAVE, e le chiavi non si
    riscrivono alle spalle di nessuno. Se questo cade, abbiamo cambiato in
    silenzio il contenitore di qualcuno."""
    import sqlite3

    ric = mem.add(FATTO, topic="az/mag ")
    assert ric.get("stored") is True
    assert ric.get("status") != "quarantined"
    con = sqlite3.connect(f"file:{mem.semantic.db_path}?mode=ro", uri=True)
    topic_scritto = con.execute(
        "SELECT topic FROM facts WHERE id = ?", (ric.get("id"),)).fetchone()[0]
    con.close()
    assert topic_scritto == "az/mag ", (
        f"il topic e' stato riscritto: {topic_scritto!r}")


@pytest.mark.parametrize("topic", ["az/mag", "città/perché", "AZ/MAG", ""])
def test_un_topic_ordinario_non_porta_avvisi(mem, topic):
    """L'ALTRO PRESIDIO: accenti, maiuscole e topic vuoto non sono anomalie.
    Il vuoto in particolare — è un default legittimo, non una svista."""
    assert not _avvisi(mem.add(FATTO, topic=topic))
