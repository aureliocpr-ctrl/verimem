"""T58 — `verimem facts restore` abortito esce 0: uno script legge «riuscito».

Ticket: gravità di ws7 (b7ffe8ef), assegnato a ws2 dal controllore dopo #17.
Data: 2026-09-10. Ramo `giano/t58`.

COSA HA TROVATO LA LETTURA, prima di eseguire (`verimem/cli.py:4038`
`facts_restore`). Il comando ha TRE uscite e due sanno dire di no:

    4048  if not bp.exists():          console.print("backup not found")
    4049                               raise typer.Exit(1)          <- 1
    4066  except ValueError as exc:    console.print("refused: …")
    4069                               raise typer.Exit(1)          <- 1
    4060  if not ok:                   console.print("aborted")
    4061                               return                       <- **0**

Il terzo e' il ramo dell'ABORTO: l'utente risponde «no» alla conferma, oppure
interrompe (`typer.Abort`). Il ripristino NON avviene, e il processo esce
**0** — cioe' la parola che in una shell significa «fatto».

⚠️ PERCHE' NON E' UNA PIGNOLERIA, ed e' la ragione per cui questo banco passa
da un SUBPROCESS e non da una funzione. Il danno non e' nel testo stampato:
`aborted` in giallo si legge benissimo. Il danno e' nel **codice di uscita**,
che e' l'unica cosa che uno script guarda:

    verimem facts restore vecchio.db && rm -rf ./dati_correnti

Con exit 0 la seconda meta' parte. L'utente ha detto «no» e la sua roba viene
cancellata lo stesso, perche' il prodotto gli ha detto «riuscito».

⚠️ E LA CONTROIPOTESI, che va detta perche' e' seria: «l'utente ha scelto lui
di annullare, non e' un errore». Vera come descrizione dell'intenzione, falsa
come contratto di uscita: `0` non vuol dire «nessun errore», vuol dire
**«l'operazione richiesta e' avvenuta»**. Qui non e' avvenuta. E il caso
`typer.Abort` (interruzione) chiude la discussione da solo: un'interruzione
non e' un successo per nessuna convenzione.

⚠️ IL CONTROLLO POSITIVO E' SIMMETRICO, e senza quello questo file non prova
niente. Non basta «un comando che esce 0»: serve **lo stesso comando, sullo
stesso backup, con UNA VARIABILE SOLA diversa** — la risposta alla conferma —
che esce 0 **e ha davvero ripristinato**. Altrimenti «abortito esce 1» sarebbe
verde anche su un comando che fallisce sempre, e avrei scambiato un prodotto
rotto per un prodotto curato. (Stanotte ho pagato tre volte questa classe su
T49: un controllo positivo non simmetrico e' un controllo positivo finto.)

⛔ PERIMETRO: ogni sottoprocesso ha la sua tempdir, passata nell'ambiente
PRIMA dell'avvio. E' la differenza che conta rispetto ai banchi in-process di
T49: li' `CONFIG` era gia' congelato all'import e le variabili non spostavano
niente; qui il processo nasce dopo, quindi l'ambiente morde. Nessuna
esecuzione tocca lo store di casa, e il banco lo VERIFICA prima di eseguire.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]

#: ⚠️ QUESTA RIGA NON E' ORNAMENTALE, e serve al CONFTEST, non a me.
#: `tests/conftest.py:599` (`pytest_collection_modifyitems`) fa
#: `from tests._real_model import real_ce_cached`, che pretende la RADICE del
#: repo dentro `sys.path`. Ma nessuno la mette: ce la mettono i file di test,
#: uno per uno, con questa riga in cima. Finche' se ne lancia uno che ce l'ha,
#: il conftest funziona per tutti; lanciando da solo un file nuovo che non ce
#: l'ha, pytest muore in RACCOLTA e non gira NIENTE:
#:
#:     INTERNALERROR> ModuleNotFoundError: No module named 'tests._real_model'
#:     no tests ran in 1.74s          EXIT=3
#:
#: Misurato il 2026-09-10 su questo file. Non e' un difetto del prodotto — e'
#: una dipendenza dall'ORDINE che il conftest non dichiara, e che colpisce
#: esattamente chi scrive un file nuovo pulito.
sys.path.insert(0, str(RADICE))

import pytest  # noqa: E402


def _ambiente(tmp: Path) -> dict:
    """L'ambiente di un processo figlio, ancorato a `tmp`.

    I quattro alias insieme: il prodotto ne legge piu' d'uno a seconda del
    modulo, e il conftest ne ha curati quattro in quattro incidenti diversi
    («questa e' la quarta: si pinnano TUTTI»).
    """
    env = dict(os.environ)
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR",
                 "ENGRAM_DIR"):
        env[nome] = str(tmp)
    env.pop("HIPPO_ENCODE_DELEGATE_ONLY", None)
    #: il daemon di casa non si tocca: questo banco non deve giudicare niente.
    env["ENGRAM_ENCODE_SERVICE"] = "0"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _cli(args: list[str], env: dict, *, stdin: str = "") -> subprocess.CompletedProcess:
    """La PORTA: il processo che l'utente lancia, non la funzione python."""
    return subprocess.run(
        [sys.executable, "-m", "verimem.cli", *args],
        cwd=str(RADICE), env=env, input=stdin,
        capture_output=True, text=True, timeout=300, check=False)


def _n_fatti(db: Path) -> int:
    con = sqlite3.connect(str(db))
    try:
        return int(con.execute("SELECT count(*) FROM facts").fetchone()[0])
    finally:
        con.close()


@pytest.fixture()
def scena(tmp_path):
    """Uno store isolato con un fatto dentro, e un BACKUP che ne contiene due.

    Cosi' il ripristino e' OSSERVABILE: se avviene, il conteggio passa da 1 a
    2. Un backup identico all'originale renderebbe «riuscito» e «non
    avvenuto» indistinguibili — che e' esattamente il difetto che sto
    misurando, e sarebbe un bel modo di non misurarlo.
    """
    dati = tmp_path / "dati"
    dati.mkdir()
    env = _ambiente(dati)

    #: ⚠️ `--proposition`, NON un argomento posizionale: `facts add` prende la
    #: proposizione come OPZIONE (`cli.py`, `facts_add`). Al primo giro l'avevo
    #: passata posizionale e la porta ha risposto «Got unexpected extra
    #: argument» — un rosso che parla del banco, non del prodotto, ed e' la
    #: terza volta in due giorni che pago questa classe. La firma si legge
    #: prima di scrivere il banco, non dopo il rosso.
    r = _cli(["facts", "add", "-p", "il tornello 42 e' aperto",
              "--topic", "banco/t58"], env)
    assert r.returncode == 0, f"la scrittura di prova non riesce: {r.stdout}\n{r.stderr}"

    db = dati / "semantic" / "semantic.db"
    assert db.exists(), (
        "lo store non e' nella tempdir: il banco lavorerebbe sulla memoria di "
        f"Aurelio. cercato: {db}\n{r.stdout}")

    #: il BACKUP: una copia dello store con un fatto IN PIU'.
    r2 = _cli(["facts", "add", "-p", "la serratura del deposito nord risulta forzata",
               "--topic", "banco/t58"], env)
    assert r2.returncode == 0, f"la seconda scrittura non riesce: {r2.stdout}"
    backup = tmp_path / "backup_con_due.db"
    shutil.copy2(db, backup)
    assert _n_fatti(backup) == 2, _n_fatti(backup)

    #: e adesso lo store torna a UNO, cosi' il ripristino ha qualcosa da fare.
    con = sqlite3.connect(str(db))
    con.execute("DELETE FROM facts WHERE proposition LIKE '%serratura%'")
    con.commit()
    con.close()
    assert _n_fatti(db) == 1, _n_fatti(db)

    return {"env": env, "db": db, "backup": backup, "tmp": tmp_path}


def test_CONTROLLO_un_ripristino_che_AVVIENE_esce_zero_e_si_vede(scena):
    """Il controllo positivo, e dev'essere SIMMETRICO al caso sotto.

    Stesso comando, stesso backup, stessa scena: cambia solo che qui il
    ripristino viene confermato. Se questo cade, il rosso sotto non parla del
    codice di uscita — parla di un comando che non funziona affatto.
    """
    r = _cli(["facts", "restore", str(scena["backup"]), "--yes"], scena["env"])
    assert r.returncode == 0, (
        "un ripristino confermato non riesce: allora questo banco non misura "
        f"il ramo dell'aborto.\nEXIT={r.returncode}\n{r.stdout}\n{r.stderr}")
    assert _n_fatti(scena["db"]) == 2, (
        "il comando dice di aver ripristinato ma lo store non e' cambiato: "
        f"fatti={_n_fatti(scena['db'])}, attesi 2.\n{r.stdout}")


def test_CONTROLLO_un_backup_che_non_esiste_esce_uno(scena):
    """La prova che il comando SA uscire diverso da zero.

    Senza questa, «abortito esce 0» potrebbe voler dire «questo comando esce
    sempre 0 qualunque cosa succeda», che sarebbe un difetto diverso.
    """
    r = _cli(["facts", "restore", str(scena["tmp"] / "non_esiste.db")], scena["env"])
    assert r.returncode != 0, (
        "un backup inesistente esce 0: il comando non sa dire di no in nessun "
        f"caso, e il ticket va riscritto.\nEXIT={r.returncode}\n{r.stdout}")


def test_un_ripristino_ABORTITO_non_dice_successo(scena):
    """IL CASO IN ESAME: l'utente risponde «no» e il processo esce 0.

    `cli.py:4060-4061` — `if not ok: console.print("aborted"); return`. In
    typer un `return` e' un'uscita 0. Il ripristino non e' avvenuto, e lo
    store lo conferma.
    """
    prima = _n_fatti(scena["db"])
    r = _cli(["facts", "restore", str(scena["backup"])], scena["env"], stdin="n\n")
    dopo = _n_fatti(scena["db"])

    assert dopo == prima, (
        "lo store E' cambiato dopo un «no»: il difetto sarebbe piu' grave di "
        f"quello del ticket. prima={prima} dopo={dopo}\n{r.stdout}")
    assert r.returncode != 0, (
        "il ripristino NON e' avvenuto (lo store e' fermo a "
        f"{dopo} fatti) e il processo esce {r.returncode}. In una shell `0` "
        "vuol dire «l'operazione richiesta e' avvenuta»: uno script che fa "
        "`verimem facts restore vecchio.db && rm -rf ./dati` cancella i dati "
        "dopo che l'utente ha detto NO.\n"
        f"  stdout: {r.stdout.strip()[:300]}")


def test_un_ripristino_INTERROTTO_non_dice_successo(scena):
    """L'altra faccia dello stesso ramo, e quella che non ha controipotesi.

    `typer.Abort` — stdin chiuso, EOF sulla domanda: nessuno ha risposto
    «no», il processo e' stato interrotto. Che un'interruzione valga
    «riuscito» non lo sostiene nessuna convenzione.
    """
    prima = _n_fatti(scena["db"])
    r = _cli(["facts", "restore", str(scena["backup"])], scena["env"], stdin="")
    dopo = _n_fatti(scena["db"])

    assert dopo == prima, (
        f"lo store e' cambiato dopo un'interruzione. prima={prima} dopo={dopo}")
    assert r.returncode != 0, (
        f"il processo e' stato INTERROTTO sulla domanda e esce {r.returncode}. "
        f"Lo store e' fermo a {dopo} fatti: non e' successo niente, e il "
        "prodotto dice di si'.\n"
        f"  stdout: {r.stdout.strip()[:300]}")
