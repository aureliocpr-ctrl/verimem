"""Il banco del PACCHETTO — assegnato a ws2 nel mandato 0.7.5 (08/08).

Perché esiste, in una riga: il 08/08 sette istanze hanno misurato il prodotto
importandolo dall'albero di lavoro e hanno consegnato ad Aurelio un documento che
descriveva **codice che nessun utente possiede**. Il pacchetto pubblicato era la
0.7.0 del 22 luglio, 375 commit indietro, con lo stesso numero di versione del repo
(``docs/stato-reale/02e-chi-installa-riceve-il-22-luglio.md``).

Nessuno aveva sbagliato una misura: avevamo tutti misurato **l'artefatto sbagliato**.
Questi test rendono quell'errore rilevabile da una macchina invece che da un'istanza
fortunata.

Tre livelli, dal più economico al più caro:

1. ``test_i_comandi_che_il_readme_insegna_esistono`` — la vetrina non può insegnare
   un comando che non c'è. Costo: millisecondi, nessuna installazione.
2. ``test_i_prefissi_di_provenance_che_suggeriamo_sono_accettati`` — se l'aiuto in
   linea suggerisce ``--verified-by commit:...``, il detector deve accettarlo.
   **xfail(strict)**: oggi NON è così, ed è un difetto scritto, non nascosto.
3. ``test_il_wheel_contiene_i_comandi_del_repo`` (slow) — costruisce il wheel e
   guarda dentro: ciò che il repo definisce deve arrivare a chi installa.

⚠️ Il livello 3 è l'unico che risponde davvero alla domanda «cosa riceve l'utente»,
perché gli altri due leggono l'albero. Gli altri due esistono perché girano sempre.
"""
from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
CLI = RADICE / "verimem" / "cli.py"
README = RADICE / "README.md"


# Parole che seguono "verimem" nella prosa senza essere comandi ("verimem 0.7.5",
# "verimem recall will be instant"). Tenuta corta apposta: se cresce, significa che
# il README parla di sé in modo ambiguo, e vale la pena accorgersene.
_NON_COMANDI = {
    "recall",  # "Verimem recall will be instant" — frase, non invocazione
    "memory", "server", "facts", "is", "as", "in", "on", "to", "and", "the",
    "has", "installa", "usa", "e", "ha", "non",
}


def _comandi_definiti(sorgente: str) -> set[str]:
    """Ogni comando montato su ``app``, nelle TRE forme che la CLI usa davvero.

    Il primo giro di questo test cercava solo ``@app.command("x")`` e dichiarava
    inesistenti ``doctor``, ``trust``, ``warmup`` — che esistono eccome. Sono
    dichiarati con ``@app.command()`` nuda, dove il nome lo mette Typer a partire
    dalla funzione. Un parser che ne vede una forma su tre accusa la vetrina di un
    difetto suo: ecco perché le forme sono tutte e tre, ed elencate.
    """
    espliciti = set(re.findall(r'@app\.command\(\s*"([^"]+)"', sorgente))
    # @app.command()  /  @app.command(help=...)  → Typer usa il nome della funzione,
    # con gli underscore convertiti in trattini e il suffisso `_cmd` spogliato.
    impliciti = {
        n.removesuffix("_cmd").replace("_", "-")
        for n in re.findall(r"@app\.command\((?!\s*\")[^)]*\)\s*\ndef\s+(\w+)", sorgente)
    }
    gruppi = set(re.findall(r'add_typer\([^)]*name\s*=\s*"([^"]+)"', sorgente))
    return espliciti | impliciti | gruppi


def _comandi_citati(testo: str) -> set[str]:
    """``verimem <parola>`` nella prosa, saltando le righe che dichiarano un'assenza.

    Un referto che scrive «`verimem forget` → No such command» sta documentando il
    difetto, non insegnando il comando: farlo fallire punirebbe l'onestà.
    """
    # Il primo giro filtrava solo le forme italiane e accusava il README nel punto in
    # cui è più onesto: «`verimem forget` is not a command — the CLI cannot delete at
    # all». Un test che rompe la riga che dichiara un limite spinge a togliere il
    # limite, non a curarlo.
    _DICHIARA_ASSENZA = (
        "No such command", "non esiste", "non e' un comando", "non è un comando",
        "is not a command", "not a command", "cannot", "does not exist",
        "isn't a command", "no such",
    )
    citati: set[str] = set()
    for riga in testo.splitlines():
        if any(s in riga for s in _DICHIARA_ASSENZA):
            continue
        for m in re.finditer(r"\bverimem\s+([a-z][a-z0-9-]{2,})\b", riga):
            citati.add(m.group(1))
    return citati - _NON_COMANDI


def test_i_comandi_che_il_readme_insegna_esistono():
    """La vetrina non può insegnare un comando che il prodotto non ha.

    Il caso vero che questo test avrebbe preso: il 08/08 una tabella pronta per il
    README diceva «usa `verimem ignorance`», comando che nel pacchetto pubblicato
    risponde `No such command` (``docs/stato-reale/02f-...``).
    """
    assert README.exists(), "README.md è la vetrina: se sparisce, il test deve dirlo"
    definiti = _comandi_definiti(CLI.read_text(encoding="utf-8"))
    assert definiti, "nessun @app.command trovato: il parser è rotto, non il README"

    mancanti = sorted(_comandi_citati(README.read_text(encoding="utf-8")) - definiti)
    assert not mancanti, (
        f"il README insegna comandi che non esistono: {mancanti}\n"
        f"o li aggiungi alla CLI, o togli la riga dalla vetrina."
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "DIFETTO NOTO, misurato il 08/08 (docs/stato-reale/02j-trust-il-punto-c.md): "
        "l'aiuto di `trust` suggerisce `--verified-by commit:...` e `coverage:N`, ma "
        "_RUNTIME_EVIDENCE_PREFIXES non li contiene, quindi il claim resta FLAGGED e "
        "l'utente non sa perché. 3 prefissi su 5 funzionano. La cura è una riga di "
        "documentazione (cambiare gli esempi), NON allargare la lista: uno SHA di "
        "commit non è evidenza che qualcosa funzioni. Quando la cura entra, questo "
        "xfail diventa rosso e va tolto."
    ),
)
def test_i_prefissi_di_provenance_che_suggeriamo_sono_accettati():
    """Se lo suggeriamo nell'aiuto in linea, il detector deve accettarlo."""
    from verimem.l1_works_detector import _RUNTIME_EVIDENCE_PREFIXES

    testo = CLI.read_text(encoding="utf-8")
    # Ancora stabile: l'help del parametro, che è il posto dove l'utente li legge.
    # Il primo parser cercava `def trust` con find() e agganciava `trust_stats_cmd`
    # (riga 1359) invece di `trust` (1420), quindi non trovava NIENTE — e l'xfail
    # passava per la ragione sbagliata, il che è peggio di un test assente: sembra
    # documentare il difetto e documenta il proprio bug. Trovato falsificandolo con
    # --runxfail, che è l'unico modo di vedere PERCHÉ un xfail è rosso.
    i = testo.find("Provenance ref (repeatable)")
    assert i > 0, "l'help di --verified-by non ha più l'ancora attesa: parser da rivedere"
    zona = testo[i:i + 400]
    # Il prefisso è il PRIMO segmento del riferimento: in `ci:main:green` è `ci:`,
    # non `main:`. Senza l'ancora a inizio token il test accusava anche `main:`, che
    # non è un prefisso ma un ramo — un falso positivo che avrebbe gonfiato il difetto
    # da tre a quattro voci.
    suggeriti = {
        f"{p}:" for p in re.findall(r"(?:^|[\s,(\"])([a-z_]+):(?=[a-zA-Z#0-9])", zona)
    }
    assert suggeriti, "nessun esempio di provenance trovato nell'aiuto: parser da rivedere"

    non_accettati = sorted(suggeriti - set(_RUNTIME_EVIDENCE_PREFIXES))
    assert not non_accettati, (
        f"l'aiuto suggerisce prefissi che il detector non accetta: {non_accettati}\n"
        f"accettati: {sorted(_RUNTIME_EVIDENCE_PREFIXES)}"
    )


def test_la_versione_dichiarata_non_e_troppo_lontana_dal_codice():
    """Il numero di versione deve distinguere due artefatti diversi.

    ⚠️ Questo è l'unico test del file che avrebbe preso il difetto vero del 08/08.
    Gli altri leggono l'albero o un wheel costruito dall'albero: nessuno di loro può
    accorgersi che il pacchetto PUBBLICATO è vecchio. Quel giorno il repo era a 375
    commit dall'ultimo bump e dichiarava ancora `0.7.0` — lo stesso numero del
    pacchetto su PyPI. Due artefatti diversi, un nome solo, e sette istanze che
    misuravano quello sbagliato senza avere modo di saperlo.

    La soglia è larga apposta: non impone di rilasciare spesso, impone che quando la
    distanza diventa grande qualcuno lo dica. È un avviso, non un veto — la stessa
    forma che il resto del progetto ha già scelto per il pavimento del recall.

    Nato in ``xfail(strict=True)`` l'08/08, quando la distanza era 387 commit e
    toglierlo dall'xfail avrebbe messo un rosso permanente in mezzo a un merge di
    sei rami. Il marcatore è stato rimosso il 09/08 **dal test stesso**: fatto il
    bump a 0.7.5, l'xfail è diventato XPASS(strict) e la suite ha chiesto di
    toglierlo, che è esattamente il lavoro per cui era stato messo lì.
    """
    SOGLIA = 150  # commit; a 375 eravamo ben oltre, a 20 nessuno si allarma

    def git(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=RADICE, capture_output=True,
                              text=True, timeout=60).stdout.strip()

    if not git("rev-parse", "--git-dir"):
        pytest.skip("non è un checkout git: la distanza non è calcolabile")
    versione = re.search(r'^version\s*=\s*"([^"]+)"',
                         (RADICE / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    assert versione, "pyproject.toml non dichiara una versione"

    bump = git("log", "--format=%H", "-1", "-S", f'version = "{versione.group(1)}"',
               "--", "pyproject.toml")
    if not bump:
        pytest.skip("bump di versione non trovato nella storia (shallow clone?)")
    distanza = int(git("rev-list", "--count", f"{bump}..HEAD") or 0)

    assert distanza <= SOGLIA, (
        f"la versione {versione.group(1)} è ferma da {distanza} commit (soglia {SOGLIA}).\n"
        f"Chi installa riceve un artefatto diverso da questo, con lo stesso numero: "
        f"o si pubblica, o si alza la versione, o si dichiara la distanza nel README."
    )


def test_le_dipendenze_che_pubblichiamo_hanno_un_tetto_dove_serve():
    """Una dipendenza senza tetto pubblica un prodotto che si romperà da solo.

    Il caso vero, e non è ipotetico: `verimem 0.7.0` su PyPI chiede `mcp>=1.0.0` senza
    limite superiore. `mcp 2.0.0` ha rimosso `Server.list_tools`, che il nostro server
    usa in 11 punti — quindi **ogni `pip install verimem` da luglio riceve un server MCP
    che non parte** (`verimem mcp` → AttributeError), mentre tutto il resto della CLI
    funziona. Il tetto è nel repo dal 29/07 (`bd4ff5ba`) e non è ancora pubblicato:
    ``docs/stato-reale/02n-il-server-mcp-e-morto-per-chi-installa.md``.

    Il test guarda le dipendenze che DICHIARIAMO, non quelle installate qui: è la riga
    che finisce nel wheel a decidere cosa riceve l'utente.
    """
    testo = (RADICE / "pyproject.toml").read_text(encoding="utf-8")
    dichiarate = re.findall(r'^\s*"([a-zA-Z0-9_.-]+)([^"]*)"', testo, re.M)

    # Solo le dipendenze la cui API usiamo direttamente e che hanno già rotto una volta.
    # Deliberatamente corta: un tetto ovunque è un dolore, un tetto qui è memoria.
    SENSIBILI = {"mcp"}
    # `set`: `mcp` è dichiarato in tre punti (core + due extra) e senza deduplica il
    # messaggio diceva ['mcp', 'mcp', 'mcp'], che si legge come tre dipendenze diverse.
    senza_tetto = sorted({
        n for n, v in dichiarate
        if n in SENSIBILI and "<" not in v and "==" not in v and "~=" not in v
    })
    assert not senza_tetto, (
        f"dipendenze sensibili dichiarate senza limite superiore: {senza_tetto}\n"
        f"una major nuova le romperà nel pacchetto pubblicato, dove non ce ne accorgiamo."
    )


def test_il_server_mcp_si_importa():
    """La porta degli agenti deve almeno partire.

    Complemento del test qui sopra: quello guarda ciò che dichiariamo, questo ciò che è
    installato QUI. Se qualcuno si porta in casa una `mcp` incompatibile, questo test lo
    dice subito invece di lasciarlo scoprire a un utente.
    """
    try:
        import verimem.mcp_server  # noqa: F401
    except Exception as exc:
        try:
            import importlib.metadata as md
            versione = md.version("mcp")
        except Exception:  # noqa: BLE001 — la versione è un dettaglio del messaggio
            versione = "sconosciuta"
        pytest.fail(
            f"verimem.mcp_server non si importa con mcp {versione}: "
            f"{type(exc).__name__}: {exc}"
        )


@pytest.fixture(scope="module")
def wheel_costruito(tmp_path_factory):
    """Costruisce il wheel UNA volta per tutti i test che devono guardarci dentro.

    Prima era una `subprocess.run` dentro il singolo test; con due consumatori il
    wheel veniva costruito due volte (~25 s ciascuno) per leggere lo stesso file.
    """
    dove = tmp_path_factory.mktemp("wheel")
    esito = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "-o", str(dove)],
        cwd=RADICE, capture_output=True, text=True, timeout=900,
    )
    if esito.returncode != 0:
        pytest.skip(f"build del wheel non riuscita in questo ambiente: {esito.stderr[-400:]}")
    wheels = list(dove.glob("*.whl"))
    if not wheels:
        pytest.skip(f"nessun wheel prodotto in {dove}")
    return wheels[0]


@pytest.mark.slow
def test_il_wheel_passa_il_controllo_che_pypi_fa_prima_di_accettarlo(wheel_costruito):
    """Un README che non si renderizza fa RIFIUTARE l'upload — e brucia il numero.

    PyPI valida la `Description` (che è il README, finito nel METADATA) e risponde
    400 se non rende. E un numero di versione non si riusa: PyPI rifiuta un filename
    già visto **anche dopo che la release è stata cancellata**, quindi un upload
    fallito per il README costringe a passare alla versione successiva, davanti a
    tutti e per sempre nello storico.

    `twine check` è la stessa validazione, eseguita prima. Costa un secondo qui e
    una versione bruciata là.
    """
    esito = subprocess.run(
        [sys.executable, "-m", "twine", "check", str(wheel_costruito)],
        cwd=RADICE, capture_output=True, text=True, timeout=300,
    )
    if "No module named twine" in (esito.stderr or ""):
        pytest.skip("twine non installato in questo ambiente")
    assert esito.returncode == 0 and "PASSED" in esito.stdout, (
        f"il pacchetto non passerebbe la validazione di PyPI:\n"
        f"{esito.stdout[-600:]}\n{esito.stderr[-400:]}"
    )


@pytest.mark.slow
def test_il_wheel_contiene_i_comandi_del_repo(wheel_costruito):
    """Ciò che il repo definisce deve arrivare dentro il pacchetto.

    ⚠️ Limite dichiarato: il wheel viene costruito DA QUESTO ALBERO, quindi contiene
    per forza lo stesso ``cli.py``. Il test copre il packaging (un modulo escluso da
    ``pyproject``, un file che non entra nella distribuzione) e **non** copre la
    pubblicazione: se il wheel su PyPI è vecchio, questo test passa lo stesso. Per
    quello c'è ``test_la_versione_dichiarata_non_e_troppo_lontana_dal_codice``.
    """
    with zipfile.ZipFile(wheel_costruito) as z:
        nomi = [n for n in z.namelist() if n.endswith("verimem/cli.py")]
        assert nomi, f"il wheel non contiene verimem/cli.py: {z.namelist()[:10]}"
        nel_wheel = _comandi_definiti(z.read(nomi[0]).decode("utf-8"))

    nel_repo = _comandi_definiti(CLI.read_text(encoding="utf-8"))
    persi = sorted(nel_repo - nel_wheel)
    assert not persi, (
        f"comandi definiti nel repo e assenti dal wheel: {persi}\n"
        f"repo {len(nel_repo)} · wheel {len(nel_wheel)}"
    )
