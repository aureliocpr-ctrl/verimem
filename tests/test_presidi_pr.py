"""Il tetto delle righe di una PR, e il workflow che lo esegue (regola R6).

Due cose provate qui:
  1. `righe_della_pr.py` conta su un repo git VERO, non solo su tuple finte —
     il conteggio passa da `git diff --numstat`, e un errore lì non si vedrebbe
     mai nei casi di laboratorio.
  2. il workflow `presidi-pr.yml` invoca script che esistono davvero e passa
     ogni cricchetto per il suo `--autotest` — un presidio in CI che non è mai
     diventato rosso è un sensore scollegato, e un `run:` che nomina uno script
     inesistente rende rosso ogni PR per la ragione sbagliata.

    python -m pytest tests/test_presidi_pr.py -q
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess

import pytest

RADICE = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("righe_della_pr", RADICE / "scripts" / "righe_della_pr.py")
righe = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(righe)

WORKFLOW = RADICE / ".github" / "workflows" / "presidi-pr.yml"


def _git(cartella: pathlib.Path, *argomenti: str) -> str:
    return subprocess.run(["git", *argomenti], cwd=cartella, capture_output=True,
                          text=True, check=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    """Un repo con due commit: la base e la punta di una PR finta."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "banco@example.invalid")
    _git(tmp_path, "config", "user.name", "banco")
    (tmp_path / "verimem").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "verimem" / "gia_qui.py").write_text("x = 1\n" * 10, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    return tmp_path, base


def test_conta_le_righe_di_prodotto_su_un_repo_vero(repo):
    cartella, base = repo
    (cartella / "verimem" / "nuovo.py").write_text("y = 2\n" * 42, encoding="utf-8")
    (cartella / "tests" / "test_nuovo.py").write_text("assert True\n" * 500, encoding="utf-8")
    _git(cartella, "add", "-A")
    _git(cartella, "commit", "-q", "-m", "punta")
    head = _git(cartella, "rev-parse", "HEAD")

    m = righe.misura(righe.numstat(base, head, cwd=str(cartella)))
    assert m["aggiunte_prodotto"] == 42, m
    assert m["aggiunte_altro"] == 500, "i test non entrano nel tetto ma si stampano lo stesso"
    assert righe.stampa(m, deroga=False) == 0


def test_una_cancellazione_grande_non_e_una_pr_grande(repo):
    """Togliere codice è ciò che vogliamo: contarlo come «grande» punirebbe proprio quello."""
    cartella, base = repo
    (cartella / "verimem" / "gia_qui.py").unlink()
    _git(cartella, "add", "-A")
    _git(cartella, "commit", "-q", "-m", "tolgo")
    head = _git(cartella, "rev-parse", "HEAD")

    m = righe.misura(righe.numstat(base, head, cwd=str(cartella)))
    assert m["aggiunte_prodotto"] == 0
    assert m["tolte_prodotto"] == 10
    assert righe.stampa(m, deroga=False) == 0


def test_oltre_il_tetto_diventa_rosso_e_la_deroga_lo_riapre(repo):
    """IL CONTROLLO POSITIVO."""
    cartella, base = repo
    (cartella / "verimem" / "grosso.py").write_text("z = 3\n" * (righe.TETTO + 1), encoding="utf-8")
    _git(cartella, "add", "-A")
    _git(cartella, "commit", "-q", "-m", "grosso")
    head = _git(cartella, "rev-parse", "HEAD")

    m = righe.misura(righe.numstat(base, head, cwd=str(cartella)))
    assert m["aggiunte_prodotto"] == righe.TETTO + 1
    assert righe.stampa(m, deroga=False) == 1, "oltre il tetto deve uscire 1"
    assert righe.stampa(m, deroga=True) == 0, "con l'etichetta del lead deve passare"


def test_il_diff_usa_tre_punti_e_non_due(repo):
    """Con `base..head` una PR ferma diventa «grande» appena main va avanti.
    Qui main avanza per conto suo e la PR non deve accorgersene."""
    cartella, base = repo
    _git(cartella, "checkout", "-q", "-b", "pr")
    (cartella / "verimem" / "mio.py").write_text("a = 1\n" * 5, encoding="utf-8")
    _git(cartella, "add", "-A")
    _git(cartella, "commit", "-q", "-m", "il mio pezzo")
    head = _git(cartella, "rev-parse", "HEAD")

    _git(cartella, "checkout", "-q", "main")
    (cartella / "verimem" / "di_un_altro.py").write_text("b = 2\n" * 400, encoding="utf-8")
    _git(cartella, "add", "-A")
    _git(cartella, "commit", "-q", "-m", "il pezzo di un altro")
    main_avanzato = _git(cartella, "rev-parse", "HEAD")

    m = righe.misura(righe.numstat(main_avanzato, head, cwd=str(cartella)))
    assert m["aggiunte_prodotto"] == 5, (
        "la PR deve valere 5 righe, non le 400 che main ha aggiunto altrove"
    )


def test_il_workflow_nomina_solo_script_che_esistono():
    yaml = pytest.importorskip("yaml")
    contenuto = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    passi = contenuto["jobs"]["cricchetti"]["steps"]
    nominati = set()
    for passo in passi:
        for parola in (passo.get("run") or "").split():
            if parola.startswith("scripts/") and parola.endswith(".py"):
                nominati.add(parola)
    assert nominati, "il workflow non invoca nessuno script: sarebbe un presidio vuoto"
    mancanti = sorted(n for n in nominati
                      if not (RADICE / n).exists() and "mappa_completa" not in n)
    assert not mancanti, f"il workflow invoca script che non esistono: {mancanti}"


def test_ogni_cricchetto_del_workflow_passa_dal_suo_autotest():
    """Se un presidio entra in CI senza il suo autotest, nessuno saprà mai se morde."""
    yaml = pytest.importorskip("yaml")
    contenuto = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    tutti_i_run = " ".join((p.get("run") or "") for p in contenuto["jobs"]["cricchetti"]["steps"])
    for script in ("scripts/copie.py", "scripts/senza_chiamante.py", "scripts/righe_della_pr.py"):
        assert f"{script} --autotest" in tutti_i_run, (
            f"{script} entra in CI senza il suo --autotest"
        )
