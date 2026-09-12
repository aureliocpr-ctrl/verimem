"""Nessun workflow porta una chiave scritta due volte — e il lettore normale non la vede.

🔴 12/09. Ho modificato `ci.yml` lasciando per sbaglio la chiave `matrix:`
vecchia sopra quella nuova:

    strategy:
      fail-fast: false
      matrix:                       <- orfana
      matrix: ${{ fromJSON(...) }}  <- la nuova

L'ho validato con `yaml.safe_load` e **e' passato**: la libreria tiene l'ultima
e non dice niente. La piattaforma l'ha rifiutato due volte, con

    run …  name=.github/workflows/ci.yml  completed/failure  jobs=0
    «This run likely failed because of a workflow file issue»

e nessun messaggio recuperabile dall'API. Mezz'ora spesa a cercare l'errore
nell'espressione della matrice, **che era corretta**.

🔑 **Il livello a cui misuri decide il verdetto.** «YAML valido» non e' «il
consumatore lo accetta»: fra i due c'e' esattamente questa classe di difetti, e
il controllo va messo al livello del consumatore o non serve.

⚠️ E questa cella sta nel pytest e NON nel job dei messaggi: quel job non
installa niente di proposito, e il controllo ha bisogno di un parser che nella
libreria standard non c'e'. Ce l'avevo messo, ed e' caduto con
`ModuleNotFoundError` — **una cura che rompe la proprieta' del posto in cui la
metti non e' al suo posto.**
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
SCRIPT = RADICE / "scripts" / "chiavi_doppie.py"
WORKFLOW = sorted((RADICE / ".github" / "workflows").glob("*.yml"))


def _esegui(*argomenti: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *argomenti],
                          cwd=RADICE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)


def test_il_controllo_morde() -> None:
    """Il suo autotest: boccia una chiave ripetuta, accetta un file sano, e
    PROVA che `safe_load` non la vede — senza quel terzo caso lo script
    potrebbe essere inutile e nessuno se ne accorgerebbe."""
    esito = _esegui("--autotest")
    assert esito.returncode == 0, esito.stdout + esito.stderr
    assert "AUTOTEST VERDE" in esito.stdout, esito.stdout


def test_nessun_workflow_ha_una_chiave_ripetuta() -> None:
    assert WORKFLOW, "nessun workflow trovato: il controllo misurerebbe il vuoto"
    esito = _esegui(*[str(f) for f in WORKFLOW])
    assert esito.returncode == 0, esito.stdout + esito.stderr


def test_il_controllo_diventa_rosso_su_un_file_che_la_porta(tmp_path: Path) -> None:
    """Il controllo positivo che deve ACCENDERSI: un file costruito apposta.

    Senza questo, un controllo che non trovasse mai niente sarebbe
    indistinguibile da uno rotto — ed e' la forma che questo progetto ha gia'
    pagato piu' volte.
    """
    doppio = tmp_path / "doppio.yml"
    doppio.write_text("jobs:\n  x:\n    runs-on: a\n    runs-on: b\n", encoding="utf-8")

    esito = _esegui(str(doppio))

    assert esito.returncode == 1, (
        f"il controllo non ha visto la chiave ripetuta:\n{esito.stdout}")
    assert "due volte" in esito.stdout, esito.stdout
