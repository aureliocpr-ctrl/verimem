"""L'avviso sulla coda diceva COME TACERE con precisione e come agire a gesti.

Quando la coda di revisione supera la soglia, ogni scrittura che la ingrossa
riceve un avviso. Fino al 2026-08-15 il suo consiglio era::

    drain the backlog (review and restore or forget) — a queue nobody drains
    turns 'held for review' into 'silently dropped'; tune or disable with
    ENGRAM_REVIEW_QUEUE_MAX (0 = off)

Le azioni sono nominate a gesti — «review and restore or forget» — mentre
l'unica cosa scritta per esteso, col suo nome esatto, è **la variabile che
spegne l'avviso**.

🔑 L'istruzione precisa era quella che non drena niente.

═══ IL NUMERO CHE HA FATTO SCRIVERE QUESTO FILE ═══

Misurato sullo store di lavoro il 15/08::

    quarantinati non superseduti (il backlog)        882
    `facts requalify-quarantined` (dry run) dichiara 136 RECUPERABILI
        di quei 136:  99 approvati dal giudice
                      37 mai giudicati
                       0 respinti

Centotrentasei fatti veri, trattenuti da falsi positivi di un gate già
corretto, con **zero** respinti — e lo strumento per liberarli **esiste già**
(`facts quarantine-log`, `facts requalify-quarantined`, `facts restore`,
`facts forget`). L'avviso c'era, lo strumento c'era, e non si nominavano.

⇒ **Il backlog è cresciuto per attrito, non per disaccordo.** È la stessa
misura che in casa aveva già dato «1 adozione su 15» per un comando che
chiedeva un dato che nessuno aveva sottomano: quando una cura non viene usata,
il difetto sta nello strumento, non nella disciplina di chi legge.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from verimem import review_queue

_RADICE = Path(__file__).resolve().parents[1]

#: I comandi che l'avviso insegna, estratti dal suo stesso testo.
_COMANDO_RE = re.compile(r"verimem ([a-z][a-z0-9-]+(?: [a-z][a-z0-9-]+)?)")


@pytest.fixture
def consiglio(monkeypatch, tmp_path) -> str:
    """Il testo che il prodotto mostra a chi ingrossa la coda.

    ⚠️ La soglia si abbassa dalla **porta pubblica** (`ENGRAM_REVIEW_QUEUE_MAX`),
    non sostituendo `threshold` nel modulo: la prima versione di questo file
    faceva così e i tre test **saltavano tutti e tre**, cioè non verificavano
    niente — proprio il difetto che questo presidio esiste per impedire.

    🔑 Un banco che salta non è neutro: dice «verificato» a chi legge il verde.
    Perciò qui non c'è nessuno `skip`. Lo store è costruito apposta con una
    riga in quarantena, così l'avviso deve uscire e, se non esce, è ROSSO.
    """
    import sqlite3

    db = tmp_path / "semantic.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE facts (id TEXT, status TEXT, superseded_by TEXT, "
                "created_at INTEGER)")
    con.execute("INSERT INTO facts VALUES ('x', 'quarantined', NULL, "
                "strftime('%s','now'))")
    con.commit()
    con.close()

    import verimem.review_queue as rq
    monkeypatch.setenv("ENGRAM_REVIEW_QUEUE_MAX", "1")
    rq.reset_cache()
    avviso = rq.backpressure_warning(str(db))
    rq.reset_cache()
    assert avviso is not None, (
        "con una riga in quarantena e soglia 1 l'avviso non esce: o la lettura "
        "dello store fallisce in silenzio (la funzione cattura ogni eccezione "
        "e torna None), o il segnale è stato disattivato")
    return avviso["advice"]


def test_l_avviso_NOMINA_almeno_un_comando_eseguibile(consiglio):
    """Il cuore: chi legge dev'essere in grado di agire, non solo di capire."""
    comandi = _COMANDO_RE.findall(consiglio)
    assert comandi, (
        "il consiglio non nomina nessun comando `verimem …`: descrive l'azione "
        "senza dire con che cosa si fa, e chi legge una ricevuta non ha modo "
        "di eseguirla")


def test_OGNI_COMANDO_NOMINATO_ESISTE_DAVVERO(consiglio):
    """⚠️ Un avviso che insegna un comando inesistente è peggio di uno vago:
    manda chi legge a sbattere e poi a ignorare i prossimi avvisi."""
    comandi = _COMANDO_RE.findall(consiglio)
    r = subprocess.run(
        [sys.executable, "-m", "verimem.cli", "facts", "--help"],
        capture_output=True, text=True, timeout=300, cwd=str(_RADICE))
    testo = (r.stdout or "") + (r.stderr or "")
    esposti = set(re.findall(r"│\s([a-z][a-z0-9-]{2,})\s{2,}", testo))
    if not esposti:
        pytest.skip(f"l'help di `facts` non è parsabile (rc={r.returncode}): "
                    f"aggiorna QUESTA funzione invece di credere a uno zero")
    mancanti = [c for c in comandi
                if c.startswith("facts ") and c.split(" ", 1)[1] not in esposti]
    assert not mancanti, (
        f"l'avviso insegna comandi che la CLI non espone: {mancanti}. "
        f"Esposti sotto `facts`: {sorted(esposti)}")


def test_NON_SPIEGA_SOLO_COME_TACERE(consiglio):
    """⚠️⚠️ IL VERSO OPPOSTO, ed è la ragione per cui questo file esiste.

    Un avviso che nomina per esteso la variabile che lo disattiva, e lascia
    l'azione utile a un gesto generico, insegna una cosa sola: come non vederlo
    più. Qui si pretende che accanto al modo di spegnerlo ci sia almeno un modo
    di RISOLVERE, altrettanto eseguibile.

    Se un domani qualcuno «semplificasse» il testo togliendo i comandi, questo
    test cade prima che il backlog ricominci a crescere in silenzio.
    """
    spegnimento = "ENGRAM_REVIEW_QUEUE_MAX" in consiglio
    azione = bool(_COMANDO_RE.search(consiglio))
    assert not (spegnimento and not azione), (
        "il consiglio dice come DISATTIVARE l'avviso ma non come drenare la "
        "coda con un comando: l'unica istruzione precisa sarebbe quella che "
        "non risolve niente")
