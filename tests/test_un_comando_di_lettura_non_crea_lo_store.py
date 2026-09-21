"""Un comando di LETTURA non deve creare lo store che dice di leggere.

Rilievo arrivato dal lavoro di un pari: `facts list --db <file>` esce `EXIT=0`
con un elenco vuoto su uno store che ha migliaia di fatti, senza rifiuto e
senza avviso. Riprodotto il 2026-09-20, e la causa non è lo store vecchio: è il
**path che non esiste**. Il comando lo crea in quel momento, lo trova vuoto —
perché l'ha appena fatto lui — e lo racconta come «nessun fatto»:

    facts list --db <file che NON esiste>
      su main             tabella vuota   EXIT=0   file creato: 73728 byte
      col blocco v7       tabella vuota   EXIT=0   file creato: 73728 byte

La guardia sugli store da migrare non copre questo caso, e non è un suo
difetto: quello non è uno store vecchio, è un file che nasce lì. Basta un path
battuto male — un refuso, un percorso relativo, una maiuscola su Windows — e la
risposta del prodotto a «fammi vedere la mia memoria» è «è vuota», mentre i
fatti stanno intatti nel file accanto.

⚠️ 73728 byte è esattamente la dimensione di `~/.engram/semantic.db`, il file
vuoto alla radice dello store vero che teniamo fra le trappole note. Indizio,
non misura: ma la dimensione coincide al byte, e un fantasma così nasce da
qualche parte.

⚠️ LA CURA NON DEVE ESSERE TROPPO LARGA, e l'ultima cella è lì per impedirlo:
`remember --db <nuovo>` deve continuare a creare lo store, perché lì la
creazione è il mestiere del comando. Vietare la creazione dappertutto
sarebbe una cura peggiore del difetto.

Si misura DALLA PORTA, in sottoprocesso: la domanda è cosa fa il comando che
una persona batte, non cosa fa la funzione che sta sotto.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]


def _cli(*argomenti: str) -> subprocess.CompletedProcess:
    """Il comando vero, nel worktree di questo codice."""
    return subprocess.run(
        [sys.executable, "-m", "verimem.cli", *argomenti],
        cwd=RADICE, capture_output=True, text=True,
        # ⚠️ `encoding` ACCANTO a `text=True`, e non è pignoleria: senza,
        # la lettura usa la codifica di SISTEMA (cp1252 su Windows) e il
        # thread lettore muore sul primo byte che non sa decodificare —
        # «il processo esce 0 e il canale torna None», dice il prodotto nel
        # docstring di `_proc_quiet`. È successo qui: su windows-latest la
        # cella è morta con `returncode=0 stdout is None: True`, e la regola
        # era scritta dal 3 settembre.
        encoding="utf-8", errors="replace", timeout=300,
    )


#: LE PORTE DI LETTURA CHE ACCETTANO `--db`, contate invece che immaginate.
#: Il rilievo nominava `facts list`; misurate tutte, il 2026-09-20 ne creavano
#: uno **sette su sette**, e sei uscivano EXIT=0:
#:
#:     facts list  0 · facts get  1 · facts search  0 · facts recall  0
#:     recall  0   · stats  0 (98304 byte)  · audit verify  0
#:
#: Curare la sola porta del rilievo avrebbe lasciato le altre sei a rispondere
#: «memoria vuota» creandone una: è la classe «conta le porte prima di
#: dichiarare chiuso» del registro.
PORTE_DI_LETTURA = [
    ("facts list", ("facts", "list")),
    ("facts get", ("facts", "get", "abc123456789")),
    ("facts search", ("facts", "search", "prova")),
    ("facts recall", ("facts", "recall", "prova")),
    ("recall", ("recall", "prova")),
    ("stats", ("stats",)),
    ("audit verify", ("audit", "verify")),
]


# ------------------------------------------------------------- il bersaglio --
@pytest.mark.parametrize(
    "comando", [c for _, c in PORTE_DI_LETTURA],
    ids=[n for n, _ in PORTE_DI_LETTURA])
def test_una_lettura_su_un_path_inesistente_non_crea_niente(comando, tmp_path) -> None:
    """Il caso del rilievo, su ogni porta: il file non c'è e il comando se lo
    fabbrica, poi lo trova vuoto — perché l'ha appena fatto lui."""
    mancante = tmp_path / "questo_file_non_esiste.db"

    esito = _cli(*comando, "--db", str(mancante))

    assert not mancante.exists(), (
        f"un comando di sola lettura ha CREATO lo store che doveva leggere: "
        f"{mancante} ({mancante.stat().st_size if mancante.exists() else 0} "
        f"byte). Chi ha sbagliato a battere il path si sente dire che la sua "
        f"memoria è vuota, e intanto gliene nasce una nuova accanto")
    assert esito.returncode != 0, (
        f"EXIT={esito.returncode} su uno store che non esiste: il comando "
        f"risponde «nessun fatto» a una domanda che non ha potuto leggere.\n"
        f"--- stdout ---\n{esito.stdout[-600:]}")
    assert "non esist" in (esito.stdout + esito.stderr).lower() or \
           "not exist" in (esito.stdout + esito.stderr).lower(), (
        f"il comando esce diverso da zero ma non dice che il file non c'è, "
        f"quindi chi legge non sa cosa correggere.\n"
        f"--- stdout ---\n{esito.stdout[-600:]}\n--- stderr ---\n{esito.stderr[-600:]}")


# ------------------------------------------------------- controllo positivo --
def test_lo_stesso_comando_su_uno_store_vero_continua_a_funzionare(tmp_path) -> None:
    """Se il bersaglio diventasse verde perché il comando non funziona più,
    questa cella lo dice: su uno store che esiste deve leggere come prima."""
    from verimem import Memory

    percorso = tmp_path / "vero" / "sem.db"
    mem = Memory(path=percorso)
    mem.add("Il magazzino contiene 100 pezzi.", topic="banco/porta", ground=False)

    esito = _cli("facts", "list", "--db", str(percorso))
    # ⚠️ `capture_output=True` promette due stringhe, e su windows-latest/py3.12
    # questa cella è morta con `TypeError: argument of type 'NoneType' is not
    # iterable` — cioè `stdout` era None, che quella promessa esclude. Finché
    # non si sa perché, la cella non deve esplodere su un `in`: deve DIRE che
    # cosa ha ricevuto, altrimenti il prossimo giro costa un'ora di CI per
    # riscoprire lo stesso nulla.
    uscita = esito.stdout if esito.stdout is not None else ""
    diagnostica = (f"returncode={esito.returncode} "
                   f"stdout is None: {esito.stdout is None} "
                   f"len(stdout)={len(uscita)} "
                   f"stderr={(esito.stderr or '')[-400:]!r}")

    assert esito.returncode == 0, (
        f"il comando non legge più uno store che esiste. {diagnostica}\n"
        f"--- stdout ---\n{uscita[-600:]}")
    assert "100 pezzi" in uscita or "magazzino" in uscita, (
        f"lo store esiste e ha un fatto dentro, ma il comando non lo mostra: "
        f"la cura ha rotto la lettura, oppure l'uscita non è arrivata affatto. "
        f"{diagnostica}\n--- stdout ---\n{uscita[-800:]}")


# ------------------------------------------------------- controllo negativo --
def test_una_scrittura_puo_ancora_creare_uno_store_nuovo(tmp_path) -> None:
    """IL LIMITE DELLA CURA. Scrivere in uno store che non c'è ancora deve
    continuare a crearlo: è il primo comando che una persona dà.

    Se questa cella cade, la cura ha vietato la creazione dappertutto invece
    che nei soli comandi di lettura, ed è peggio del difetto che toglie."""
    nuovo = tmp_path / "nuovo" / "sem.db"

    esito = _cli("remember", "Il contatore segna 10 unità.", "--db", str(nuovo))

    assert esito.returncode == 0, (
        f"scrivere in uno store nuovo non funziona più: EXIT="
        f"{esito.returncode}\n--- stdout ---\n{esito.stdout[-600:]}\n"
        f"--- stderr ---\n{esito.stderr[-600:]}")
    assert nuovo.exists(), (
        "il comando di scrittura non ha creato lo store: la cura ha tolto "
        "anche la creazione legittima")
