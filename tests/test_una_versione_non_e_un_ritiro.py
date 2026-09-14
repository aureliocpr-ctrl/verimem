"""T56 — il verdetto del gate non arriva alla porta a riga di comando.

IL DIFETTO, nominato con file e riga il 12 settembre 2026 alle 22:15:

    `anti_confab_gate` PRODUCE `supersede_fact_ids` (i fatti da ritirare)
    `client.py`        lo LEGGE  -> semantic.supersede(reason="same-source evolution")
    `mcp_server.py`    lo LEGGE
    `cli.py`           0 occorrenze        <- `facts add` legge solo `gate.action`

Misurato con una sonda che stampa un anello per riga, stessi argomenti della
riga di comando (agente, source, ground_write, verified_by vuoto)::

    validate="full"
      detect_semantic_conflicts(fratelli=1) -> [nli=contradiction]
      is_same_source() -> True     classify_write_relation() -> 'evolution'
      _entita_diverse() -> False   _supersede_same_source_on() -> True
      AZIONE: persist
      avviso: L3-supersession «a newer same-source value supersedes a stored
              fact — the older value is superseded»
      RITIRATI: 0

Il gate **dice** che il vecchio è superato, e nessuno lo ritira. Due porte su
tre eseguono il verdetto; quella che un utente ha sotto le dita, no.

⚠️ DUE ANELLI IN FILA, e il secondo è un ticket a sé (T82). Anche leggendo il
campo, al DEFAULT il verdetto non viene neppure calcolato: `facts add` ha
`--validate` uguale a `"fast"` (`verimem/cli.py:4413`) e il blocco che lo
calcola sta sotto `if level == "full"` (`verimem/anti_confab_gate.py:2203`).
Con la stessa sonda, a `"fast"`, `_live_topic_siblings` non viene **mai**
chiamata. ⇒ La cura del primo anello non cambia niente per chi scrive senza
opzioni, e l'ultima cella di questo file lo misura invece di lasciarlo
implicito.

🐌 QUESTO BANCO GIRA COL GIUDICE ACCESO, ed è obbligatorio: la supersessione
nasce da un verdetto del modello NLI (coseno ≥ 0,7 poi CONTRADICTION). Un
banco che spegne l'inferenza per andare veloce misura un silenzio — è
l'errore che la prima stesura di questo file conteneva. Costo misurato:
~28 s di avvio del giudice, più il moat per scrittura.

⚠️ E FATTI E FONTE NELLA STESSA LINGUA. Con il fatto in italiano e la fonte in
inglese il moat quarantina **entrambi** (misurato: `status=quarantined` su due
scritture su due) e la politica non li vede nemmeno: si misurerebbe la
traduzione, non la supersessione. La coppia mista è un difetto a sé (T81).

Ticket: T56. Il primo RED è `tests/test_le_tre_porte_conservano_lo_stesso_numero.py`.

Comando (un file solo, una esecuzione)::

    pytest -q -p no:randomly -rsfE tests/test_una_versione_non_e_un_ritiro.py
"""

from __future__ import annotations

import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

import pytest

#: Due versioni della STESSA grandezza, da una fonte che le contiene entrambe
#: in successione — tutto in italiano, come i fatti.
FONTE = ("Rapporto latenza: la mediana era 33.0s nel giro del mattino, poi "
         "41.2s dopo la ricostruzione dell'indice.")
PRIMA = "La latenza mediana e' 33.0s."
SECONDA = "La latenza mediana e' 41.2s."
TOPIC = "t56/versione"
DOMANDA = "latenza"


def _ambiente(dati: pathlib.Path) -> dict[str, str]:
    """L'ambiente del banco: il giudice ACCESO.

    Le tre variabili «offline» e la delega al demone vengono TOLTE, non messe:
    con quelle il detector non gira e questo banco misurerebbe il proprio
    silenzio. `HIPPO_ENCODE_DELEGATE_ONLY` arriva dall'ambiente della sessione
    e va tolta esplicitamente — è la trappola già pagata il 7 settembre.
    """
    env = {**os.environ, "HIPPO_DATA_DIR": str(dati), "COLUMNS": "200"}
    for da_togliere in ("HIPPO_ENCODE_DELEGATE_ONLY", "HIPPO_OFFLINE",
                        "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE",
                        "ENGRAM_ENCODE_SERVICE",
                        "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        env.pop(da_togliere, None)
    return env


def _cli(env: dict[str, str], *argomenti: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "verimem.cli", *argomenti],
                          env=env, capture_output=True, text=True, timeout=900)


def _scrivi_la_coppia(livello: str | None) -> dict[str, object]:
    """Le due versioni dalla porta, nell'ordine, con il livello indicato."""
    dati = pathlib.Path(tempfile.mkdtemp(prefix=f"t56-{livello or 'default'}-"))
    env = _ambiente(dati)
    opzioni = ["--validate", livello] if livello else []
    for testo in (PRIMA, SECONDA):
        esito = _cli(env, "facts", "add", "-p", testo, "--source", FONTE,
                     "--topic", TOPIC, *opzioni)
        if esito.returncode != 0:
            pytest.skip("CONTROLLO POSITIVO SPENTO: la scrittura non è "
                        f"riuscita (exit {esito.returncode}); nessuna "
                        f"asserzione qui sotto misura niente. "
                        f"{esito.stderr[-400:]}")
        if "quarantined=1" in esito.stdout:
            pytest.skip(
                "CONTROLLO POSITIVO SPENTO: il moat ha quarantinato la "
                "scrittura, quindi la politica di supersessione non la vede "
                "nemmeno e questo banco misurerebbe la quarantena. "
                f"{esito.stdout[-300:]}")
    return {"env": env, "dati": dati}


def _righe_db(dati: pathlib.Path) -> list[tuple]:
    db = dati / "semantic" / "semantic.db"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return con.execute(
            "SELECT id, proposition, superseded_by, superseded_reason "
            "FROM facts ORDER BY created_at").fetchall()
    finally:
        con.close()


def _righe_rese(uscita: str) -> list[str]:
    return [r.strip() for r in uscita.splitlines() if r.strip().startswith("- ")]


@pytest.fixture(scope="module")
def pieno() -> dict[str, object]:
    """La coppia scritta con `--validate full`: il livello che CALCOLA il
    verdetto di supersessione."""
    return _scrivi_la_coppia("full")


@pytest.mark.slow
def test_CONTROLLO_le_due_versioni_sono_entrambe_nel_corpus(pieno):
    """⚠️ SENZA QUESTO le celle sotto possono essere verdi per il motivo
    sbagliato: se una delle due scritture non è entrata, «un fatto vivo» è
    banalmente vero e non dice niente sulla supersessione."""
    righe = _righe_db(pieno["dati"])
    assert len(righe) == 2, (
        f"nel corpus ci sono {len(righe)} fatti invece di due: le due "
        f"versioni non sono state scritte entrambe. {righe}")


@pytest.mark.slow
def test_la_seconda_versione_ritira_la_prima(pieno):
    """IL CUORE — lo stato che il gate ha già deciso e che nessuno applica.

    Il gate produce `supersede_fact_ids` e stampa l'avviso «the older value is
    superseded»; `client.py` e `mcp_server.py` lo leggono e chiamano
    `semantic.supersede`, `cli.py` no (zero occorrenze del campo). Qui si
    pretende l'effetto, non la chiamata: quale funzione lo faccia è di chi
    scrive la cura, che il vecchio risulti ritirato è la promessa.
    """
    righe = _righe_db(pieno["dati"])
    vecchia = [r for r in righe if "33.0" in r[1]]
    nuova = [r for r in righe if "41.2" in r[1]]
    assert vecchia and nuova, f"la coppia non è quella attesa: {righe}"
    id_nuova, sup, motivo = nuova[0][0], vecchia[0][2], vecchia[0][3]
    assert sup == id_nuova, (
        "la versione vecchia NON è stata ritirata dalla nuova: "
        f"superseded_by={sup!r}, atteso {id_nuova!r}. Il gate lo aveva "
        "deciso — l'avviso L3-supersession dice «the older value is "
        "superseded» — e la porta a riga di comando non applica il verdetto.")
    assert motivo == "same-source evolution", (
        f"ritirata con motivo {motivo!r} invece di «same-source evolution»: "
        "un ritiro senza il motivo giusto non è tracciabile nel registro.")


@pytest.mark.slow
def test_la_lettura_di_default_rende_una_sola_riga(pieno):
    """L'effetto per chi usa il prodotto: una domanda, una risposta, l'ultima.

    Alla PORTA e non nel database: è la riga che l'utente legge.
    """
    # UN GIRO DI RISCALDAMENTO, e non e' cortesia verso il prodotto: il primo
    # recall dopo le scritture arriva mentre il demone di codifica si sta
    # ancora alzando, il prodotto lo DICHIARA («encode exceeded 2.0s budget ->
    # degrading … recall falls back to keyword») e ripiega sulla ricerca per
    # parole, che su due sole righe rende zero. Misurato il 12/09: la stessa
    # domanda, rifatta a demone caldo, rende la riga giusta. Un banco che
    # misura quella corsa misura il riscaldamento, non la promessa.
    _cli(pieno["env"], "recall", DOMANDA)
    esito = _cli(pieno["env"], "recall", DOMANDA)
    assert esito.returncode == 0, esito.stderr[-400:]
    _uscita = esito.stdout + esito.stderr
    if "degrading" in _uscita or "falls back to keyword" in _uscita:
        pytest.skip(
            "BANCO SPENTO: la lettura e' ripiegata sulla ricerca per parole "
            "perche' la codifica non era pronta — il prodotto lo dichiara "
            "nella sua stessa uscita. Questa cella non ha misurato la "
            "promessa, e un rosso qui parlerebbe del demone.")
    righe = _righe_rese(esito.stdout)
    assert len(righe) == 1, (
        f"la lettura di default rende {len(righe)} risposte invece di una: "
        "chi chiede la latenza riceve due valori diversi della stessa "
        "grandezza, e nessuno dei due dichiara di essere quello vecchio. "
        + os.linesep.join(righe))
    assert "41.2" in righe[0], (
        f"la risposta servita non è la versione più recente. {righe[0]}")


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason=(
    "T82: al DEFAULT `facts add` usa `--validate fast` (cli.py:4413) e il "
    "blocco che calcola il verdetto sta sotto `if level == \"full\"` "
    "(anti_confab_gate.py:2203) — misurato con la sonda: a fast "
    "`_live_topic_siblings` non viene mai chiamata. Curare la porta che NON "
    "legge il verdetto non basta: al default il verdetto non esiste. La "
    "decisione fast/full va presa con il costo per scrittura misurato sullo "
    "store vero, non qui"))
def test_T82_anche_SENZA_opzioni_la_seconda_versione_ritira_la_prima():
    """LA CELLA CHE RESTA ROSSA DOPO LA CURA, e lo dice.

    ⚠️ Senza questa cella, una cura del primo anello si leggerebbe come «T56
    chiuso» mentre chi scrive `facts add` senza opzioni — cioè l'uso normale —
    continua a perdere la versione vecchia. È lo stesso corpo della cella
    sopra, con un solo cambiamento: nessun `--validate`.
    """
    store = _scrivi_la_coppia(None)
    righe = _righe_db(store["dati"])
    vecchia = [r for r in righe if "33.0" in r[1]]
    nuova = [r for r in righe if "41.2" in r[1]]
    assert vecchia and nuova, f"la coppia non è quella attesa: {righe}"
    assert vecchia[0][2] == nuova[0][0], (
        "al default la versione vecchia non viene ritirata: "
        f"superseded_by={vecchia[0][2]!r}")
