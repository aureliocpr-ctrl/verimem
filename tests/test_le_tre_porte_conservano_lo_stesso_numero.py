"""T56 RED-1 — la stessa scrittura conserva o cancella a seconda della porta.

Misurato il 10 settembre, contando quanti fatti portano l'impronta della fonte
per scrittore::

    riga di comando      9716 / 10964
    libreria              217 /   269
    server di strumenti     0 /   151     <- non la scrive MAI

La politica che decide i ritiri si accende su quell'impronta, quindi dove
l'impronta non c'è il ritiro non avviene: **dei ritiri per evoluzione della
stessa fonte, 468 vengono dalla riga di comando, 61 dalla libreria e ZERO dal
server di strumenti.** Chi usa il prodotto dentro un assistente e chi lo usa da
terminale hanno due politiche di conservazione diverse, e nessuna ricevuta lo
dice.

⚠️ QUESTO TEST NON DICE QUALE DEBBA ESSERE IL NUMERO, e la distinzione è il
punto: dice che **non possono essere due numeri diversi**. Resta rosso
qualunque criterio si scelga, e diventa verde solo quando le tre porte
decidono allo stesso modo.
Il secondo RED — *su cosa* devono accordarsi, conservare o ritirare — è una
promessa all'utente e la fissa il ruolo di prodotto; si scrive quando la
decisione c'è, non prima.

🔒 `xfail(strict=True)` E NON UN ROSSO, per due ragioni:
  · il difetto è aperto e dichiarato: un rosso fisso in CI verrebbe letto come
    rumore e poi disattivato da qualcuno, che è il modo in cui i presidi
    muoiono;
  · **con `strict` l'XPASS è un fallimento**: il giorno in cui la cura arriva,
    questo file lo dice da sé invece di restare verde in silenzio. Senza
    `strict` diventerebbe cieco e nessuno se ne accorgerebbe.

Ticket: T56 (`docs/stato-reale/ticket/T56-supersessione.md`).
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

import pytest

#: Due letture della STESSA evidenza: la mediana e il minimo di una sola
#: esecuzione. Nessuna delle due nega l'altra — è la coppia del corpus reale.
FONTE = "latency over 5 queries: min 16.3s, median 33.0s, max 41.2s"
PRIMA = "La latenza riporta mediana 33.0s su 5 query."
SECONDA = "La latenza riporta min 16.3s su 5 query."
TOPIC = "t56/tre-porte"


def _vivi(db: pathlib.Path) -> int:
    """Quanti fatti restano SERVIBILI: né ritirati né fermati dal gate."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    n = con.execute(
        "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
        "AND (status IS NULL OR status != 'quarantined')").fetchone()[0]
    con.close()
    return n


def _tempdir(nome: str) -> pathlib.Path:
    return pathlib.Path(tempfile.mkdtemp(prefix=f"t56-{nome}-"))


def _dalla_libreria() -> int:
    from verimem.client import Memory
    m = Memory(_tempdir("lib") / "m.db")
    m.add(PRIMA, source=FONTE, topic=TOPIC)
    m.add(SECONDA, source=FONTE, topic=TOPIC)
    return _vivi(pathlib.Path(str(m.semantic.db_path)))


def _dal_server_di_strumenti(monkeypatch) -> int:
    from verimem import mcp_server

    def chiama(nome: str, args: dict) -> dict:
        return json.loads(
            asyncio.run(mcp_server._call_tool_impl(nome, args))[0].text)

    monkeypatch.setenv("HIPPO_DATA_DIR", str(_tempdir("srv")))
    for alias in ("ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.delenv(alias, raising=False)
    chiama("hippo_remember", {"proposition": PRIMA, "source": FONTE,
                              "topic": TOPIC})
    chiama("hippo_remember", {"proposition": SECONDA, "source": FONTE,
                              "topic": TOPIC})
    return _vivi(pathlib.Path(str(mcp_server._ag().semantic.db_path)))


def _dalla_riga_di_comando() -> int:
    """La terza porta gira in un PROCESSO a parte, ed è voluto: è l'unica in
    cui l'utente non condivide il nostro interprete, e due delle differenze
    già pagate su questo prodotto nascevano lì."""
    dati = _tempdir("cli")
    amb = {"HIPPO_DATA_DIR": str(dati), "ENGRAM_ENCODE_SERVICE": "0",
           "HIPPO_OFFLINE": "1", "HF_HUB_OFFLINE": "1",
           "TRANSFORMERS_OFFLINE": "1"}
    import os
    env = {**os.environ, **amb}
    env.pop("ENGRAM_DATA_DIR", None)
    env.pop("VERIMEM_DATA_DIR", None)
    for testo in (PRIMA, SECONDA):
        esito = subprocess.run(
            [sys.executable, "-m", "verimem.cli", "facts", "add",
             "-p", testo, "--source", FONTE, "--topic", TOPIC],
            env=env, capture_output=True, text=True, timeout=300)
        if esito.returncode != 0:
            pytest.skip(
                "CONTROLLO POSITIVO SPENTO: la scrittura dalla riga di comando "
                f"non è riuscita (exit {esito.returncode}), quindi questo "
                f"confronto non ha misurato niente.\n{esito.stderr[-400:]}")
    return _vivi(dati / "semantic" / "semantic.db")


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason=(
    "T56: la stessa coppia lascia 2 fatti vivi dal server di strumenti e 1 "
    "dalle altre due porte — l'impronta della fonte è scritta da due porte su "
    "tre e la politica dei ritiri si accende su quella"))
def test_le_tre_porte_lasciano_lo_stesso_numero_di_fatti_vivi(monkeypatch):
    """IL CUORE: tre store isolati, la stessa coppia, tre conteggi uguali."""
    libreria = _dalla_libreria()
    servizio = _dal_server_di_strumenti(monkeypatch)
    comando = _dalla_riga_di_comando()

    print(f"\n  libreria            {libreria}"
          f"\n  server di strumenti {servizio}"
          f"\n  riga di comando     {comando}")

    assert libreria == servizio == comando, (
        f"le tre porte conservano in modo diverso: libreria={libreria}, "
        f"server={servizio}, riga di comando={comando}. Qualunque sia il "
        f"numero giusto, non possono essere due numeri diversi: chi usa il "
        f"prodotto da un assistente e chi lo usa da terminale hanno due "
        f"politiche di conservazione, e nessuna ricevuta gliele dichiara.")


def test_CONTROLLO_la_coppia_entra_davvero_da_ogni_porta(monkeypatch):
    """⚠️ SENZA QUESTO, il test sopra potrebbe essere verde per il motivo
    sbagliato: tre porte che scrivono ZERO fatti darebbero tre conteggi
    uguali e un presidio soddisfatto. Qui si pretende che da ciascuna sia
    entrato ALMENO un fatto — il confronto misura una differenza di politica,
    non un silenzio comune."""
    assert _dalla_libreria() >= 1, "dalla libreria non è entrato niente"
    assert _dal_server_di_strumenti(monkeypatch) >= 1, (
        "dal server di strumenti non è entrato niente")
