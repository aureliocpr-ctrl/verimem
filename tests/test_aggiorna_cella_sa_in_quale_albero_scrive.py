"""`aggiorna_cella` deve sapere in QUALE albero scrive — e dirlo anche quando non sbaglia.

🔴 06/09 07:57 — il RED e' di @ws5 (Tara), che ha misurato il difetto con le
impronte dei file: lo script eseguito con la cwd in un worktree scriveva
nell'albero **dove sta il file** e stampava `RC = 0`.

    PRIMA  finto=154e1f06  worktree=a32a30e5  condiviso=a32a30e5
    RC = 0
    DOPO   finto=c2681000  worktree=a32a30e5  condiviso=a32a30e5

Non sbagliava il contenuto: sbagliava l'albero, ed e' peggio, perche' il
contenuto era giusto e nessuno se ne accorgeva.

🔑 Il docstring dello script dichiara «GARANZIE, e devono poter fallire» e ne
elenca quattro — separazione delle colonne, numero di colonne prima e dopo, la
barra finale, l'idempotenza di `--se-manca`. **Sono tutte sul CONTENUTO della
riga. Nessuna su DOVE finisce.** Queste due celle sono quella mancante.

Costo: zero modelli, zero server. Due `git init` in `tmp_path` e due subprocess.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aggiorna_cella.py"
RIGA = ("| LANT-999 | prova | prova | prova | prova | prova | verdetto |"
        " prova | prova | prova | prova |\n")


def _albero(dove: Path, con_registro: bool = True) -> Path:
    """Un albero git minimo, con o senza il registro."""
    dove.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=dove, check=True,
                   capture_output=True, timeout=60)
    if con_registro:
        reg = dove / "docs" / "stato-reale"
        reg.mkdir(parents=True, exist_ok=True)
        (reg / "00-ESAME.md").write_text(RIGA, encoding="utf-8")
    return dove


def _esegui(script: Path, cwd: Path, *argomenti: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *argomenti],
                          cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)


@pytest.fixture()
def coda(tmp_path: Path) -> Path:
    f = tmp_path / "coda.md"
    f.write_text("aggiunta di prova", encoding="utf-8")
    return f


def test_due_alberi_diversi_si_ferma_e_li_nomina(tmp_path: Path, coda: Path) -> None:
    """Il caso di Tara: la cwd e' un albero, lo script sta in un altro.

    Deve fermarsi, nominare ENTRAMBI i percorsi, e **non toccare** il registro
    dell'albero dello script — che e' quello che prima cambiava in silenzio.
    """
    dello_script = _albero(tmp_path / "albero_dello_script")
    (dello_script / "scripts").mkdir()
    copia = dello_script / "scripts" / "aggiorna_cella.py"
    copia.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    registro = dello_script / "docs" / "stato-reale" / "00-ESAME.md"
    prima = registro.read_text(encoding="utf-8")

    dove_lavoro = _albero(tmp_path / "dove_lavoro")

    r = _esegui(copia, dove_lavoro, "LANT-999", "--coda", str(coda))

    assert r.returncode != 0, f"non si e' fermato: RC=0\n{r.stdout}"
    assert str(dove_lavoro) in r.stdout, f"non nomina la radice del chiamante:\n{r.stdout}"
    assert str(dello_script) in r.stdout, f"non nomina l'albero dello script:\n{r.stdout}"
    assert registro.read_text(encoding="utf-8") == prima, (
        "ha scritto lo stesso nell'albero dello script")


def test_quando_non_sbaglia_dice_dove_ha_scritto(tmp_path: Path, coda: Path) -> None:
    """Il caso giusto deve restare comodo — e dire DOVE.

    Il difetto e' passato inosservato per mesi perche' la riga di esito diceva
    «fatto» senza dire dove: la stessa riga, col percorso, l'avrebbe mostrato il
    primo giorno.
    """
    albero = _albero(tmp_path / "un_albero_solo")
    (albero / "scripts").mkdir()
    copia = albero / "scripts" / "aggiorna_cella.py"
    copia.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    registro = albero / "docs" / "stato-reale" / "00-ESAME.md"

    r = _esegui(copia, albero, "LANT-999", "--coda", str(coda))

    assert r.returncode == 0, f"RC={r.returncode}\n{r.stdout}\n{r.stderr}"
    assert "aggiunta di prova" in registro.read_text(encoding="utf-8")
    assert str(registro) in r.stdout, (
        f"l'esito non dice dove ha scritto:\n{r.stdout}")


def test_repo_esplicito_vince_sulla_cwd(tmp_path: Path, coda: Path) -> None:
    """`--repo` e' la via d'uscita: chi sa quel che fa lo dice e si procede."""
    bersaglio = _albero(tmp_path / "bersaglio")
    altrove = _albero(tmp_path / "altrove", con_registro=False)
    (altrove / "scripts").mkdir()
    copia = altrove / "scripts" / "aggiorna_cella.py"
    copia.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

    r = _esegui(copia, altrove, "LANT-999", "--coda", str(coda),
                "--repo", str(bersaglio))

    assert r.returncode == 0, f"RC={r.returncode}\n{r.stdout}\n{r.stderr}"
    testo = (bersaglio / "docs" / "stato-reale" / "00-ESAME.md").read_text(encoding="utf-8")
    assert "aggiunta di prova" in testo, "non ha scritto nell'albero di --repo"
