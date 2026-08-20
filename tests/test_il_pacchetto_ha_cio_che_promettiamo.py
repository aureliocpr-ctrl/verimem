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

import importlib.metadata
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # tomllib è 3.11+
    tomllib = None

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


def test_i_prefissi_di_provenance_che_suggeriamo_sono_accettati():
    """Se lo suggeriamo nell'aiuto in linea, il detector deve accettarlo.

    ✅ CHIUSO il 2026-08-14, dopo sei giorni: era il debito piu' vecchio fra
    quelli marcati. L'aiuto di ``--verified-by`` suggeriva cinque esempi e il
    detector ne accettava DUE; ora ne suggerisce tre e sono tutti accettati.
    La cura e' quella che questo marcatore prescriveva — **cambiare gli esempi,
    non allargare la lista**: uno SHA di commit dice che il codice ESISTE, non
    che funziona, e allargare ``_RUNTIME_EVIDENCE_PREFIXES`` avrebbe fatto
    passare il gate a un'evidenza che non prova niente.

    🪞 IL MARCATORE DOCUMENTAVA IL DIFETTO CON UN NUMERO SBAGLIATO, e vale
    scriverlo perche' e' la classe che censiamo tutto il giorno applicata a noi:
    diceva «3 prefissi su 5 funzionano» e nominava solo ``commit:`` e
    ``coverage:``. Eseguito con ``--runxfail``, questo test elencava
    **``['commit:', 'coverage:', 'pr:']``** — TRE non accettati, quindi ne
    funzionavano **due**, e ``pr:`` non era nominato da nessuno. Il presidio era
    acceso e puntava nella direzione giusta; il suo conto no.

    📌 Il caso resta come guardiano: se un domani l'aiuto torna a suggerire un
    prefisso che il detector non accetta, questo test diventa rosso da solo.
    """
    from verimem.l1_extended_detector import _COMMIT_REF_PREFIXES
    from verimem.l1_works_detector import _RUNTIME_EVIDENCE_PREFIXES

    # ⚠️ NON basta la famiglia RUNTIME, e la prima versione di questo test lo
    # assumeva. Il gate ha PIÙ famiglie di prova, una per detector, e ciascuna
    # accetta la sua — misurato dalla porta il 2026-08-14 sullo stesso gate:
    #   claim «SHIPPED» + commit:abc123def  -> PASSA   (famiglia commit-tracking)
    #   claim «SHIPPED» + pytest:1234_passed-> flagged (il runtime non vale lì)
    #   claim «works»   + commit:abc123def  -> flagged (un commit non prova che funzioni)
    # Un help che suggerisse SOLO la famiglia runtime sarebbe sbagliato quanto
    # uno che ne suggerisce solo una commit-tracking: entrambi mandano metà
    # degli utenti contro un rifiuto senza spiegazione. Il criterio giusto è
    # quindi «accettato da ALMENO una famiglia», non «accettato dal detector
    # works». I ref del tracker (`issue:`, `task:`, `gh:`) vivono in una regex
    # (`anti_confabulation._TRACKER_REF_RE`) e non in una tupla importabile:
    # sono elencati qui a mano, e se quella regex cambia questo elenco va con lei.
    _TRACKER_PREFIXES = ("pr:", "issue:", "task:", "git:", "commit:", "gh:")
    accettati = set(_RUNTIME_EVIDENCE_PREFIXES) | set(_COMMIT_REF_PREFIXES) | set(_TRACKER_PREFIXES)

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

    non_accettati = sorted(suggeriti - accettati)
    assert not non_accettati, (
        f"l'aiuto suggerisce prefissi che nessuna famiglia del gate accetta: "
        f"{non_accettati}\naccettati (unione delle famiglie): {sorted(accettati)}"
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


def _cosa_manca_per_costruire() -> list[str] | None:
    """I requisiti di build che l'ambiente non ha. ``None`` = non misurabile.

    L'elenco NON è scritto qui: viene da ``[build-system] requires`` del
    pyproject, così se un domani il backend cambia, il criterio lo segue invece
    di descrivere il passato. Si interroga ``importlib.metadata`` e non un
    ``import``, perché ``requires`` nomina **distribuzioni**, e il nome della
    distribuzione non sempre è il nome del modulo importabile.
    """
    if tomllib is None:  # non sappiamo leggere: non accusiamo il prodotto
        return None
    dati = tomllib.loads((RADICE / "pyproject.toml").read_text(encoding="utf-8"))
    mancanti = []
    for spec in dati.get("build-system", {}).get("requires", []):
        nome = re.split(r"[<>=!~;\[ ]", spec, maxsplit=1)[0].strip()
        try:
            importlib.metadata.version(nome)
        except importlib.metadata.PackageNotFoundError:
            mancanti.append(nome)
    return mancanti


@pytest.fixture(scope="module")
def wheel_costruito(tmp_path_factory):
    """Costruisce il wheel UNA volta per tutti i test che devono guardarci dentro.

    Prima era una `subprocess.run` dentro il singolo test; con due consumatori il
    wheel veniva costruito due volte (~25 s ciascuno) per leggere lo stesso file.

    QUI UN SOLO RAMO COPRIVA DUE CAUSE OPPOSTE, e saltava su entrambe::

        if esito.returncode != 0:
            pytest.skip(f"build del wheel non riuscita in questo ambiente: …")

    «non riuscita in questo ambiente» è una delle due letture possibili di
    quel codice di uscita. L'altra è **il nostro pacchetto non si costruisce
    più**, che non è una condizione da tollerare: è il difetto più grave che
    questo file possa incontrare, perché un pacchetto che non si costruisce non
    si pubblica. Sotto lo stesso skip, il caso che verifica *il controllo che
    PyPI fa prima di accettare* taceva proprio nel momento in cui aveva più
    ragione di parlare.

    Le due cause ora si separano leggendo cosa il prodotto **dichiara** di
    volere per costruirsi. Se l'ambiente ha tutto, un fallimento è nostro.

    Misurato il 2026-08-15 prima di toccare: ``build 1.5.1`` presente,
    returncode **0**, `verimem-0.7.5-py3-none-any.whl` prodotto — lo skip non
    scattava. Terza volta in un pomeriggio che un ramo inerte si rivela
    orientato al contrario del suo scopo.
    """
    dove = tmp_path_factory.mktemp("wheel")
    esito = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "-o", str(dove)],
        cwd=RADICE, capture_output=True, text=True, timeout=900,
    )
    if esito.returncode != 0:
        manca = _cosa_manca_per_costruire()
        if manca is None:
            pytest.skip(
                "la build fallisce e questo Python non ha tomllib (3.11+), "
                "quindi non si può stabilire se manchi all'ambiente o al "
                f"pacchetto: {esito.stderr[-300:]}")
        if manca:
            pytest.skip(
                f"l'ambiente non ha {manca}, che «[build-system] requires» "
                f"dichiara necessari: la build non poteva riuscire qui, e non "
                f"è il pacchetto a essere in difetto")
        pytest.fail(
            f"l'ambiente ha tutto ciò che «[build-system] requires» dichiara "
            f"e `python -m build --wheel` esce {esito.returncode}: non è "
            f"l'ambiente, è il pacchetto che non si costruisce più — e un "
            f"pacchetto che non si costruisce non si pubblica.\n"
            f"{esito.stderr[-800:]}")
    wheels = list(dove.glob("*.whl"))
    if not wheels:
        pytest.fail(
            f"`build` è uscito 0 e in {dove} non c'è alcun .whl: un comando "
            f"che dichiara di aver funzionato senza produrre l'artefatto è un "
            f"difetto, non una condizione dell'ambiente da saltare")
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

    ⚠️ LIMITE, misurato il 09/08 e non dedotto: `twine check` verifica che il markup
    RENDA SENZA ERRORI, non che renda COME VUOI. Due wheel dello stesso giorno —
    `bf283ef1` con 7 righe di tabella indentate dentro un bullet e `00581a4f` con 0 —
    passano ENTRAMBI. Una tabella indentata non è un errore di sintassi: PyPI la
    accetta e la mostra male. Questo test copre «l'upload viene RIFIUTATO», non «la
    pagina viene bene»; per il secondo serve un occhio, e non c'è modo di automatizzarlo
    qui. Scritto perché senza questa riga il test verrebbe letto come una garanzia che
    non dà.
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


def test_LA_CI_DA_AL_PRESIDIO_LA_STORIA_CHE_GLI_SERVE():
    """⚠️ IL PRESIDIO SUL PRESIDIO, e non e' zelo: senza questa riga il test
    qui sopra e' MUTO in CI e nessuno se ne accorge.

    `test_la_versione_dichiarata_non_e_troppo_lontana_dal_codice` cerca nella
    storia il commit che ha introdotto `version = "X"`. Con
    ``actions/checkout@v4`` senza ``fetch-depth`` il clone e' profondo **1**:
    quel commit non c'e', il test fa `pytest.skip("...(shallow clone?)")`, e
    lo skip finisce fra i 44 skipped che ogni cella riporta — **si legge
    verde**.

    🔑 Il presidio non era spento e non sbagliava: era ACCESO, diceva il vero,
    e l'ambiente gli aveva tolto l'informazione per parlare. Misurato il
    20/08: in locale `1 failed` con «ferma da 425 commit (soglia 150)», in CI
    `SKIPPED` da sempre.

    ⚖️ Un test che si spegne da solo quando l'ambiente non collabora e' peggio
    di un test assente: un test assente si nota, questo si conta fra i verdi.
    """
    import pathlib

    import yaml

    ci = pathlib.Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
    if not ci.exists():                     # pacchetto installato senza il repo
        pytest.skip("ci.yml non presente in questo albero")
    passi = yaml.safe_load(ci.read_text(encoding="utf-8"))["jobs"]["test"]["steps"]
    checkout = [s for s in passi
                if str(s.get("uses", "")).startswith("actions/checkout")]
    assert checkout, "il job di test non fa checkout: non e' piu' questo il file"
    with_ = checkout[0].get("with") or {}
    assert str(with_.get("fetch-depth")) == "0", (
        "il checkout del job di test non chiede la storia completa "
        f"(fetch-depth={with_.get('fetch-depth')!r}): il presidio della "
        "versione tornera' a SKIPPARE in CI, e uno skip si legge come un verde")
