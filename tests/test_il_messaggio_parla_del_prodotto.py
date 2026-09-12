r"""Il cancello sui messaggi di commit deve FERMARE un commit vero, non solo dire di no.

12/09/2026. Il repository e' pubblico e i suoi ultimi quaranta commit erano,
misurati con `scripts/messaggio_pulito.py` su `d60cc326~40..d60cc326`:

    oltre 10 righe    : 39
    nome di sessione  : 24
    nome utente       :  5
    percorso locale   :  2
    PULITI            :  0     <- zero su quaranta

L'autotest dello script copre i CASI (undici righe, un percorso, un nome). Qui
si copre cio' che l'autotest non puo' vedere, perche' non passa dalle porte:

  - l'hook `commit-msg` FERMA DAVVERO un `git commit`, e il commit non nasce;
  - la via d'uscita dichiarata lascia passare;
  - `--file` legge il file come lo scrivera' git, senza le righe di commento
    che git stesso poi toglie (l'hook riceve il messaggio PRIMA della pulizia:
    contarle direbbe «22 righe» a chi ne ha scritte due);
  - un intervallo VUOTO non e' un verde.

🔑 L'ultimo e' la lezione che ci e' costata di piu': una misura che non c'e' si
legge come perfetta. `git log A..B` su un intervallo vuoto stampa zero righe, e
zero messaggi sporchi su zero messaggi sarebbe «VERDE».

Costo: zero modelli, zero server, zero rete. `git init` in `tmp_path` e
subprocess — e i commit di prova nascono in un repository usa e getta, con
`core.hooksPath` puntato ai SOLI hook che si stanno provando.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
SCRIPT = RADICE / "scripts" / "messaggio_pulito.py"
ELENCO = RADICE / "scripts" / "nomi_delle_sessioni.py"
HOOK = RADICE / ".githooks" / "commit-msg"

SPORCO = ("T38: il presidio che si riarmava\n\n"
          "Rilievo di Marie, riprodotto in C:\\Users\\tizio\\Code con la gamba windows.\n"
          "Chiesto da lead-audit.\n")
PULITO = ("Restart a dead encode daemon instead of degrading forever\n\n"
          "A write that finds the daemon gone now brings it back.\n")


def _esegui(*argomenti: str, cwd: Path | None = None,
            ambiente: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    import os
    env = {**os.environ, **(ambiente or {})}
    return subprocess.run([sys.executable, str(SCRIPT), *argomenti],
                          cwd=cwd or RADICE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120, env=env)


def _git(repo: Path, *argomenti: str, controlla: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *argomenti], cwd=repo, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=120, check=controlla)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Un repository usa e getta con dentro lo script e l'hook che proviamo.

    ⚠️ `core.hooksPath` di questo progetto e' LOCALE (sta in `.git/config`),
    quindi un repository nuovo non lo eredita: qui lo si punta a mano alla sola
    cartella che vogliamo provare. Cosi' il test misura QUESTI due file e non
    gli hook installati sulla macchina di chi lo esegue.
    """
    dove = tmp_path / "repo"
    (dove / "scripts").mkdir(parents=True)
    (dove / ".githooks").mkdir(parents=True)
    # ⚠️ DUE file, non uno: dal 12/09 il controllo legge l'elenco dei nomi da
    # `nomi_delle_sessioni.py` invece di portarsene una copia. Copiandone uno
    # solo, cinque celle sono diventate rosse con `ModuleNotFoundError` — ed e'
    # la stessa cosa che succederebbe a chi installasse solo lo script.
    shutil.copy2(SCRIPT, dove / "scripts" / SCRIPT.name)
    shutil.copy2(ELENCO, dove / "scripts" / ELENCO.name)
    shutil.copy2(HOOK, dove / ".githooks" / "commit-msg")
    (dove / ".githooks" / "commit-msg").chmod(0o755)

    _git(dove, "init", "-q")
    _git(dove, "config", "core.hooksPath", ".githooks")
    _git(dove, "config", "user.email", "prova@esempio.invalid")
    _git(dove, "config", "user.name", "Prova")
    _git(dove, "add", "-A")
    # Il primo commit nasce con la via d'uscita: serve un punto di partenza, non
    # e' il commit che stiamo misurando.
    _git(dove, "-c", "core.hooksPath=.nessuno", "commit", "-q", "-m", "base")
    return dove


def _quanti_commit(repo: Path) -> int:
    return int(_git(repo, "rev-list", "--count", "HEAD").stdout.strip())


# ── l'hook, alla porta vera ───────────────────────────────────────────────────

def test_l_hook_ferma_un_commit_vero_e_il_commit_non_nasce(repo: Path) -> None:
    (repo / "nuovo.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "nuovo.txt")
    prima = _quanti_commit(repo)

    esito = _git(repo, "commit", "-m", SPORCO, controlla=False)

    assert esito.returncode != 0, (
        "l'hook ha lasciato passare un messaggio con un percorso locale e due "
        f"nomi di sessione:\n{esito.stdout}\n{esito.stderr}"
    )
    assert _quanti_commit(repo) == prima, "il commit e' nato lo stesso"
    testo = esito.stdout + esito.stderr
    assert "percorso locale" in testo and "nome di sessione" in testo, testo


def test_l_hook_lascia_passare_un_messaggio_pulito(repo: Path) -> None:
    (repo / "nuovo.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "nuovo.txt")
    prima = _quanti_commit(repo)

    esito = _git(repo, "commit", "-m", PULITO, controlla=False)

    assert esito.returncode == 0, f"{esito.stdout}\n{esito.stderr}"
    assert _quanti_commit(repo) == prima + 1


def test_il_testo_respinto_non_e_perso_e_il_comando_per_riprenderlo_funziona(
        repo: Path, monkeypatch) -> None:
    """🔑 Il pezzo che decide se il cancello viene corretto o spento.

    Un messaggio di quaranta righe respinto SEMBRA buttato via, e la reazione di
    chi l'ha appena scritto e' `--no-verify`, che spegne anche tutti gli altri
    hook. L'hook dice dove sta il testo e con quale comando riprenderlo: qui si
    prova che quel comando fa davvero nascere il commit, perche' un'istruzione
    sbagliata in un messaggio d'errore e' peggio di nessuna istruzione.
    """
    (repo / "nuovo.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "nuovo.txt")

    respinto = _git(repo, "commit", "-m", SPORCO, controlla=False)
    assert respinto.returncode != 0
    conservato = (repo / ".git" / "COMMIT_EDITMSG").read_text(encoding="utf-8")
    assert "Marie" in conservato, "il testo respinto non e' stato conservato"

    # L'editor corregge la riga incriminata: una variabile sola cambia.
    # ⚠️ Sta in un FILE e i percorsi hanno le barre in avanti: git passa
    # GIT_EDITOR a una shell, che sui percorsi di Windows si mangia i
    # backslash («C:Usersaurel…: command not found», misurato qui).
    editore = repo / "correggi.py"
    editore.write_text(
        "import pathlib, sys\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "t = p.read_text(encoding='utf-8')\n"
        "t = t.replace('Rilievo di Marie, riprodotto in', 'Reported in')\n"
        "t = t.replace('C:\\\\Users\\\\tizio\\\\Code', 'the tree')\n"
        "t = t.replace('Chiesto da lead-audit.', '')\n"
        "p.write_text(t, encoding='utf-8')\n",
        encoding="utf-8")
    monkeypatch.setenv(
        "GIT_EDITOR",
        f'"{Path(sys.executable).as_posix()}" "{editore.as_posix()}"')
    ripreso = _git(repo, "commit", "-e", "-F", ".git/COMMIT_EDITMSG", controlla=False)

    assert ripreso.returncode == 0, (
        "il comando che l'hook suggerisce non fa nascere il commit:\n"
        f"{ripreso.stdout}\n{ripreso.stderr}")
    assert "Reported in" in _git(repo, "log", "-1", "--format=%B").stdout


def test_senza_l_elenco_dei_nomi_l_hook_tace_invece_di_bloccare(repo: Path) -> None:
    """Un ramo che ha lo script ma non ancora l'elenco non si deve fermare.

    Dal 12/09 l'elenco dei nomi sta in un file a parte. Su un albero dove
    quel file non c'e' ancora, python esce con `ModuleNotFoundError`: senza la
    guardia l'hook bloccherebbe il commit **per un file mancante**, non per il
    messaggio — e chi lo subisce non ha modo di capirlo.
    """
    (repo / "scripts" / "nomi_delle_sessioni.py").unlink()
    (repo / "nuovo.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "nuovo.txt")
    prima = _quanti_commit(repo)

    esito = _git(repo, "commit", "-m", SPORCO, controlla=False)

    assert esito.returncode == 0, (
        "senza l'elenco l'hook ha bloccato il commit invece di tacere:\n"
        f"{esito.stdout}\n{esito.stderr}")
    assert _quanti_commit(repo) == prima + 1
    assert "Traceback" not in (esito.stdout + esito.stderr)


def test_la_via_d_uscita_e_dichiarata_e_funziona(repo: Path, monkeypatch) -> None:
    """Un cancello senza via d'uscita si aggira con `--no-verify`, che spegne
    ANCHE tutti gli altri hook. Meglio una porta con la targa."""
    (repo / "nuovo.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "nuovo.txt")
    monkeypatch.setenv("VERIMEM_MESSAGGIO_LUNGO", "1")

    esito = _git(repo, "commit", "-m", SPORCO, controlla=False)

    assert esito.returncode == 0, f"{esito.stdout}\n{esito.stderr}"
    assert "SALTATO" in (esito.stdout + esito.stderr)


# ── lo script, sulle sue tre interfacce ───────────────────────────────────────

def test_il_controllo_morde(tmp_path: Path) -> None:
    """L'autotest dello script e' il suo controllo positivo: qui si esige che
    sia verde, perche' un controllo che non puo' diventare rosso e' un semaforo."""
    esito = _esegui("--autotest")
    assert esito.returncode == 0, esito.stdout + esito.stderr
    assert "AUTOTEST VERDE" in esito.stdout


def test_i_commenti_di_git_non_contano(tmp_path: Path) -> None:
    """L'hook riceve `COMMIT_EDITMSG` PRIMA che git tolga le righe `# ...`.

    Senza questa cura un commit di due righe scritto nell'editor verrebbe
    bocciato per «22 righe», e il primo a non credere piu' al cancello sarebbe
    chi l'ha scritto.
    """
    messaggio = tmp_path / "COMMIT_EDITMSG"
    messaggio.write_text(
        "Titolo vero\n\nCorpo vero.\n"
        + "# Please enter the commit message for your changes.\n"
          "# On branch main\n" * 9,
        encoding="utf-8")

    esito = _esegui("--file", str(messaggio))

    assert esito.returncode == 0, esito.stdout + esito.stderr
    assert "righe non vuote" not in esito.stdout


def test_un_intervallo_vuoto_non_e_un_verde(repo: Path) -> None:
    """Una misura che non c'e' si legge come perfetta: qui deve dirsi assente."""
    esito = _esegui("--range", "HEAD..HEAD", cwd=repo)

    assert esito.returncode != 0, esito.stdout
    assert "non ho misurato niente" in (esito.stdout + esito.stderr).lower()


def test_il_range_nomina_il_commit_sporco(repo: Path) -> None:
    (repo / "a.txt").write_text("a", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "-c", "core.hooksPath=.nessuno", "commit", "-q", "-m", SPORCO)
    sporco = _git(repo, "rev-parse", "--short=8", "HEAD").stdout.strip()

    esito = _esegui("--range", "HEAD~1..HEAD", cwd=repo)

    assert esito.returncode == 1, esito.stdout
    assert sporco in esito.stdout, f"non nomina CHI cade:\n{esito.stdout}"
    assert "percorso locale" in esito.stdout


def test_il_trailer_di_attribuzione_non_conta(repo: Path) -> None:
    """`Agent: <Nome>` e' la cura dei commit non attribuibili del 13/08: e' un
    campo del registro, non racconto. Se contasse, ogni commit firmato sarebbe
    bocciato dal nome della sessione che l'ha scritto."""
    (repo / "b.txt").write_text("b", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "-c", "core.hooksPath=.nessuno", "commit", "-q",
         "-m", PULITO + "\nAgent: Corrado\n")

    esito = _esegui("--range", "HEAD~1..HEAD", cwd=repo)

    assert esito.returncode == 0, esito.stdout


def test_il_corpo_di_una_pr_si_riduce_alle_due_righe() -> None:
    """Il messaggio con cui una PR entra in main si COMPONE, non si riscrive.

    La parte che si puo' provare senza rete e' questa: dal corpo di una PR nella
    forma decisa il 12/09 devono restare esattamente le due righe, senza la
    checklist e senza la riga dello strumento.
    """
    sys.path.insert(0, str(RADICE / "scripts"))
    from messaggio_dello_squash import due_righe  # noqa: PLC0415

    corpo = (
        "The scan no longer reports an empty corpus when it could not read.\n\n"
        "RED at the port before the fix, GREEN after.\n\n"
        "### Definition of Done\n"
        "- [ ] RED at the port, with the output in the PR\n"
        "- [ ] GREEN\n\n"
        "\U0001f916 Generated with [Claude Code](https://claude.com/claude-code)\n"
    )

    righe = due_righe(corpo)

    assert len(righe) == 2, righe
    assert righe[0].startswith("The scan no longer")
    assert righe[1] == "RED at the port before the fix, GREEN after."
    assert not any("[ ]" in r or "Generated with" in r for r in righe), righe


def test_citare_un_file_che_esiste_non_e_parlare_della_stanza(repo: Path) -> None:
    """🔑 12/09: 472 file tracciati portano un nome di sessione nel PERCORSO, e
    si stanno rinominando. Un `git mv` si descrive citando i due percorsi.

    Senza questa cura il cancello bocciava esattamente i commit che curano il
    difetto — e un cancello che ferma la cura viene aggirato, non corretto.
    """
    (repo / "docs").mkdir()
    (repo / "docs" / "ws7-porte.md").write_text("contenuto pulito\n", encoding="utf-8")
    _git(repo, "add", "docs/ws7-porte.md")
    _git(repo, "-c", "core.hooksPath=.nessuno", "commit", "-q", "-m",
         "Add a note\n\nNothing to see here.\n")

    esito = _git(repo, "commit", "--allow-empty", "-m",
                 "Rename the note so its name carries a role\n\n"
                 "docs/ws7-porte.md becomes docs/porte.md.\n", controlla=False)

    assert esito.returncode == 0, (
        "l'hook ha bocciato la citazione di un file che esiste:\n"
        f"{esito.stdout}\n{esito.stderr}")


def test_una_barra_non_basta_il_percorso_deve_esistere(repo: Path) -> None:
    """L'esenzione e' un CRITERIO, non una via d'uscita: se bastasse la forma di
    un percorso, per evadere il controllo basterebbe scrivere una barra."""
    esito = _git(repo, "commit", "--allow-empty", "-m",
                 "Fix the parser\n\nvedi ws7/appunti per il dettaglio\n",
                 controlla=False)

    assert esito.returncode != 0, (
        f"una barra e' bastata a nascondere il nome:\n{esito.stdout}\n{esito.stderr}")
    assert "nome di sessione" in (esito.stdout + esito.stderr)


def test_una_riga_del_corpo_travestita_da_trailer_non_sfugge(repo: Path) -> None:
    """🔴 IL BUCO DELLA PRIMA VERSIONE, e il motivo per cui i trailer ammessi
    sono una LISTA CHIUSA.

    Scartando ogni riga della forma `Parola: ...` bastava scrivere `Nota:` per
    far sparire dal controllo un percorso locale e un nome di sessione. Il
    messaggio qui sotto passava PULITO, e l'autotest era 12 su 12 verde perche'
    i dodici casi li avevo scelti io.
    """
    (repo / "c.txt").write_text("c", encoding="utf-8")
    _git(repo, "add", "c.txt")
    _git(repo, "-c", "core.hooksPath=.nessuno", "commit", "-q", "-m",
         "Fix the parser\n\nNota: trovato da Marie in C:\\Users\\tizio\\x\n")

    esito = _esegui("--range", "HEAD~1..HEAD", cwd=repo)

    assert esito.returncode == 1, f"la riga travestita e' sfuggita:\n{esito.stdout}"
    assert "percorso locale" in esito.stdout
    assert "nome di sessione" in esito.stdout
