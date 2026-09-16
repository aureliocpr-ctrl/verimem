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
WORKFLOW = RADICE / ".github" / "workflows" / "messaggi.yml"
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


def test_senza_l_elenco_l_hook_non_blocca_ma_DICHIARA_di_non_aver_misurato(
        repo: Path) -> None:
    """Fail-open sì, silenzio no — rilievo di QA del 12/09 16:37.

    Su un albero dove l'elenco dei nomi non c'è, python uscirebbe con
    `ModuleNotFoundError`: senza la guardia l'hook bloccherebbe il commit **per
    un file mancante**, non per il messaggio. Quindi non blocca.

    🔴 MA LA PRIMA VERSIONE TACEVA, e questa cella presidiava il silenzio: un
    messaggio sporco passava e chi l'aveva scritto credeva di essere stato
    controllato. È la forma che questo progetto conosce — *una misura che non
    c'è si legge come perfetta* — e che il passo della mappa in CI evita
    stampando «NON MISURATO». Qui l'avevo violata.

    ⚖️ E la distinzione vale: se manca lo SCRIPT il cancello non è installato e
    tacere è giusto; se manca l'ELENCO il cancello c'è e non può misurare, e
    deve dirlo.
    """
    (repo / "scripts" / "nomi_delle_sessioni.py").unlink()
    (repo / "nuovo.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", "nuovo.txt")
    prima = _quanti_commit(repo)

    esito = _git(repo, "commit", "-m", SPORCO, controlla=False)
    detto = esito.stdout + esito.stderr

    assert esito.returncode == 0, (
        f"ha bloccato il commit invece di passare:\n{detto}")
    assert _quanti_commit(repo) == prima + 1
    assert "Traceback" not in detto
    assert "NON MISURATO" in detto, (
        "l'hook è passato IN SILENZIO: un messaggio sporco è entrato e chi "
        f"l'ha scritto crede di essere stato controllato.\n{detto}")


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

def test_anche_l_elenco_dei_nomi_morde() -> None:
    """🔴 21 controlli che non eseguiva nessuno — rilievo del pari, 12/09.

    L'elenco dei nomi ha il suo autotest (le maiuscole per i nomi che sono
    anche parole comuni, gli identificatori generati, i ruoli che NON sono
    nomi), e non lo lanciava ne' la CI ne' il pytest: **un presidio che nessuno
    esegue e uno che non esiste si equivalgono**.

    ⚠️ E non basta l'autotest del cancello: quello importa l'elenco ma i suoi
    casi non nominano `Varco` ne' `Saggiatore`. Se il criterio dell'elenco si
    rompesse, il cancello sbaglierebbe e il suo autotest resterebbe verde.
    """
    esito = subprocess.run(
        [sys.executable, str(ELENCO), "--autotest"],
        cwd=RADICE, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120)

    assert esito.returncode == 0, esito.stdout + esito.stderr
    assert "AUTOTEST VERDE" in esito.stdout, esito.stdout


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


def test_il_corpo_della_richiesta_e_giudicato_dallo_stesso_controllo() -> None:
    """Il criterio del corpo vive nello stesso file delle altre regole.

    Se un giorno qualcuno lo spostasse in uno script suo, i nomi e i percorsi
    verrebbero cercati da due liste che divergono — e questo progetto l'ha gia'
    pagato con l'elenco dei nomi in quattro posti con tre contenuti.
    """
    esito = _esegui("--autotest")
    assert esito.returncode == 0, esito.stdout + esito.stderr
    assert "corpo:" in esito.stdout, (
        "l'autotest non nomina i casi del corpo: girano da un posto in meno\n"
        + esito.stdout)


def test_il_corpo_arriva_per_ENV_e_non_interpolato_nello_script() -> None:
    """⚠️ IL PRESIDIO CONTRO UNA «SEMPLIFICAZIONE» CHE APRE IL RUNNER.

    Scrivere `${{ github.event.pull_request.body }}` dentro un `run:` e' piu'
    corto e sembra identico. Non lo e': l'espressione viene sostituita PRIMA
    che la shell parta, quindi un corpo che contiene `$(...)`, un apice o un
    `;` esegue quello che vuole sul runner — e chiunque puo' aprire una
    richiesta. Per `env` il corpo resta un DATO.

    Provato il 13/09 col corpo `- [x] $(touch PROVA.txt) e `touch ALTRO.txt``:
    EXIT=0 e nessuno dei due file creato.
    """
    # ⚠️ SI LEGGE LO YAML PARSATO, NON IL TESTO. La prima versione di questa
    # cella faceva `split("run:")` ed e' diventata ROSSA su un file CORRETTO:
    # la parola `run:` compare prima dentro il commento che spiega perche' non
    # si usa. E' lo stesso difetto gia' misurato il 12/08 su `concurrency`, che
    # il fixture della matrice documenta — e ci sono cascato scrivendo il
    # presidio contro un altro difetto. Lo YAML parsato e' anche il livello a
    # cui Actions legge il file.
    import yaml

    d = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    passi = [p for p in d["jobs"]["messaggi"]["steps"]
             if p.get("name") == "Il corpo di questa PR"]
    assert len(passi) == 1, "il passo sul corpo non c'e' piu'"
    passo = passi[0]

    env = passo.get("env", {})
    assert env.get("CORPO") == "${{ github.event.pull_request.body }}", (
        f"il corpo non arriva piu' per env: env = {env}")
    # Il TITOLO per la stessa ragione: su main diventa la prima riga del
    # messaggio, e un nome di sessione scritto li' passerebbe intatto.
    assert env.get("TITOLO") == "${{ github.event.pull_request.title }}", (
        f"il titolo non e' giudicato: env = {env}")
    assert "github.event.pull_request.body" not in str(passo.get("run", "")), (
        "il corpo della richiesta e' INTERPOLATO dentro lo script: un corpo "
        "con $(...) esegue comandi sul runner. Passalo per `env`.")


def test_il_modello_della_richiesta_passa_il_controllo_che_lo_accompagna() -> None:
    """⚠️ IL MODELLO E IL CRITERIO NON POSSONO DIVERGERE.

    Scritto il 13/09 dopo averlo misurato: il modello di allora, riempito come
    lo riempirebbe chi apre una richiesta, produceva un corpo di **39 righe di
    prosa** — cioe' il file che il repository propone violava il controllo che
    il repository esegue. Nessuno dei due era sbagliato da solo: erano due
    superfici che si erano mosse in tempi diversi.

    Questa cella lega le due: se qualcuno allunga il modello o stringe il
    criterio, diventa rossa qui invece che addosso al primo che apre una
    richiesta.
    """
    import json
    import subprocess

    modello = (RADICE / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    # riempito come lo riempie un autore: le due righe al posto dei segnaposto,
    # e i commenti del modello LASCIATI dove sono — che e' il caso peggiore e
    # anche quello piu' comune.
    corpo = modello.replace(
        "\n\n\n",
        "\nIl prodotto dichiara una cosa in piu' a chi lo usa.\n\n"
        "Provato dal banco: resta rosso quando fallisce.\n", 1)

    commenti = json.dumps(["### Definition of Done\n- [x] GREEN"])
    (percorso := RADICE / "commenti_di_prova.json").write_text(commenti, encoding="utf-8")
    corpo_file = RADICE / "corpo_di_prova.md"
    corpo_file.write_text(corpo, encoding="utf-8")
    try:
        esito = subprocess.run(
            [sys.executable, str(SCRIPT), "--corpo", str(corpo_file),
             "--commenti", str(percorso)],
            cwd=RADICE, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120)
    finally:
        corpo_file.unlink(missing_ok=True)
        percorso.unlink(missing_ok=True)

    assert esito.returncode == 0, (
        "il modello che il repository propone non passa il controllo che il "
        "repository esegue:\n" + esito.stdout + esito.stderr)


def test_sulle_richieste_i_nomi_bloccano_e_la_lunghezza_e_solo_un_rapporto() -> None:
    """⚠️ DUE URGENZE DIVERSE, e vanno separate senza rilassare niente.

    Sulle richieste i commit sono quelli grezzi dell'autore e lo squash non li
    porta in main: chiedere di riscrivere una storia che nessuno leggera' e'
    attrito che non compra niente. Ma la PAGINA di una richiesta e' pubblica
    quanto il tronco, quindi un nome di sessione li' si legge oggi.

    Le due direzioni si provano ENTRAMBE, o non si sta misurando una
    distinzione: si sta solo allargando una soglia.
    """
    sys.path.insert(0, str(RADICE / "scripts"))
    import messaggio_pulito as mp

    lungo_e_pulito = [("aaaaaaa", "Titolo\n" + "\n".join(
        f"una riga di racconto numero {i}" for i in range(20)))]
    lungo_e_con_nome = [("bbbbbbb", "Titolo\n" + "\n".join(
        f"una riga numero {i}" for i in range(20)) + "\nrilievo di Marie")]

    assert mp.stampa(lungo_e_pulito) == 1, (
        "sul tronco un messaggio di venti righe deve restare bloccante")
    assert mp.stampa(lungo_e_pulito, righe_solo_rapporto=True) == 0, (
        "sulle richieste la sola lunghezza non deve bloccare")
    assert mp.stampa(lungo_e_con_nome, righe_solo_rapporto=True) == 1, (
        "un nome di sessione deve bloccare ANCHE sulle richieste: quella "
        "pagina e' pubblica")
