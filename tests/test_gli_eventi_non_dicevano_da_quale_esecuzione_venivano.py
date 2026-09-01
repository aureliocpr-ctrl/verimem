"""Gli eventi non dicevano da quale ESECUZIONE venivano, e un dato netto restava muto.

IL CASO, misurato il 2026-09-02 sul journal di casa::

    superficie   start   ready   ready/start
    mcp            686       5        0,01
    cli             77      67        0,87

Il numero e' netto e **non si puo' interpretare**: «686 avvii del giudice» ha
due letture opposte — *un processo che riparte 686 volte* oppure *686 processi
che partono una volta e muoiono* — e nessun campo dell'evento permetteva di
distinguerle. Peggio: con piu' istanze che lavorano insieme sullo stesso
journal, gli eventi di processi diversi si mescolano, quindi anche gli
intervalli fra un avvio e il successivo diventano inattribuibili (misurato:
moda attorno ai 20 s, ma su una popolazione mista che non dice nulla).

⚖️ IL CAMPO ESISTEVA GIA' PER GLI ALTRI DUE ASSI, e questo li completa:
``store`` dice a quale MEMORIA appartiene una riga, ``build`` da quale CODICE
— aggiunto quando tre indagini finirono sullo stesso confondente — e ``run``
da quale ESECUZIONE.

⚠️ NON E' IL PID DA SOLO: i pid si riciclano. L'impronta lega il pid
all'istante di avvio, cosi' due esecuzioni restano distinte anche se il
sistema riusa il numero.

⚠️ IL COSTO, dichiarato: otto caratteri in piu' per evento. Sui 22823 eventi
del journal di casa sono circa 340 KB su 5,3 MB. Va detto perche' chi aggiunge
un campo a OGNI evento sta spendendo spazio di tutti.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

import verimem.flow_events as fe


@pytest.fixture()
def journal(tmp_path, monkeypatch):
    """⚠️ TUTTI E TRE gli alias: `_compat.data_dir()` ne preferisce altri prima
    di `HIPPO_DATA_DIR`, e su questa macchina `ENGRAM_DATA_DIR` punta al corpus
    REALE. Un test che ne imposta uno solo scrive nel journal di casa."""
    for _env in ("VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        monkeypatch.setenv(_env, str(tmp_path))
    return tmp_path


def test_ogni_evento_dichiara_la_propria_esecuzione():
    """IL CUORE: senza questo campo il dato «686 avvii» resta a due letture
    opposte e nessuna verificabile."""
    amb = fe._ambient()
    assert "run" in amb, (
        f"l'evento non dice da quale esecuzione viene: {sorted(amb)}")
    assert isinstance(amb["run"], str) and amb["run"], amb["run"]


def test_e_STABILE_dentro_lo_stesso_processo():
    """Se cambiasse fra due eventi dello stesso processo, non seguirebbe
    niente: sarebbe un numero casuale con l'aria di un identificativo."""
    assert fe._ambient()["run"] == fe._ambient()["run"]
    assert fe._run() == fe._run()


def test_DUE_PROCESSI_hanno_impronte_DIVERSE():
    """⚠️ LA CELLA CHE PUO' DAVVERO FALLIRE, e senza la quale il campo
    sembrerebbe funzionare pur essendo inutile: se due esecuzioni ricevessero
    la stessa impronta, «un processo che riparte» e «processi diversi»
    resterebbero indistinguibili — cioe' il difetto che il campo cura.

    Si eseguono DUE interpreti veri: e' l'unico modo di misurarlo, perche'
    dentro un solo processo l'impronta e' cachata per costruzione.
    """
    codice = ("import verimem.flow_events as fe; "
              "print(fe._ambient()['run'])")
    prima = subprocess.run([sys.executable, "-c", codice],
                           capture_output=True, text=True, timeout=180)
    dopo = subprocess.run([sys.executable, "-c", codice],
                          capture_output=True, text=True, timeout=180)
    assert prima.returncode == 0, prima.stderr[-400:]
    assert dopo.returncode == 0, dopo.stderr[-400:]
    a, b = prima.stdout.strip(), dopo.stdout.strip()
    assert a and b, (a, b)
    assert a != b, (
        f"due esecuzioni diverse hanno la stessa impronta ({a}): il campo non "
        "distingue i processi, che e' l'unica cosa per cui esiste")


def test_gli_altri_due_ASSI_restano(journal):
    """⚖️ Il campo si AGGIUNGE, non sostituisce: `store` dice quale memoria,
    `build` quale codice. Se una di queste sparisse, avrei curato un
    confondente rompendone due."""
    amb = fe._ambient()
    for campo in ("store", "build", "surface"):
        assert campo in amb, (campo, sorted(amb))


def test_il_campo_ARRIVA_nel_giornale_non_solo_nel_dizionario(tmp_path):
    """⚠️ UN CAMPO CALCOLATO E NON SCRITTO E' UN CAMPO ASSENTE. Fra `_ambient`
    e il file c'e' l'emissione vera: e' li' che si verifica, non a monte.

    🪞 PRIMA STESURA SBAGLIATA, e la lascio scritta: impostavo la data-dir con
    una fixture e chiamavo `emit_flow` in-process. Non funziona, ed e' una
    trappola nota — il percorso del giornale si fissa **all'import** di
    verimem, quindi una data-dir impostata dopo non sposta niente e l'evento
    finisce altrove. La cella cadeva dicendo «non e' arrivato», che era vero e
    per la ragione sbagliata.

    Quindi si esegue un PROCESSO NUOVO con le variabili gia' nell'ambiente:
    e' l'unico modo di misurare dove l'evento atterra davvero.
    """
    codice = (
        "import verimem.flow_events as fe;"
        "fe.emit_flow('flow.warmup', what='banco-run', phase='start');"
        "print(fe._run())"
    )
    env = {**os.environ,
           "VERIMEM_DATA_DIR": str(tmp_path),
           "ENGRAM_DATA_DIR": str(tmp_path),
           "HIPPO_DATA_DIR": str(tmp_path)}
    res = subprocess.run([sys.executable, "-c", codice], env=env,
                         capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stderr[-500:]
    atteso = res.stdout.strip()

    righe = []
    for f in tmp_path.rglob("events*.jsonl*"):
        for r in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                d = json.loads(r)
            except Exception:  # noqa: BLE001
                continue
            if (d.get("payload") or {}).get("what") == "banco-run":
                righe.append(d)

    assert righe, (
        f"l'evento non e' arrivato in nessun giornale sotto {tmp_path}: il "
        "banco non puo' dire nulla sul campo")
    pl = righe[-1].get("payload") or {}
    assert pl.get("run") == atteso, (
        f"nel giornale l'impronta e' {pl.get('run')!r}, il processo che l'ha "
        f"scritta diceva {atteso!r}")
