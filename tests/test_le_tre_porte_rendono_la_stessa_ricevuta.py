"""LA PROPRIETÀ DELLA FETTA 1: stesso ingresso, ricevuta identica sulle tre porte.

Scritta PRIMA del codice della fetta, e da chi non lo scriverà: è il RED che la
fetta deve spegnere. Oggi è rosso, ed è il punto.

CHE COSA CONFRONTA, e perché così:
  · le **chiavi** e i **tipi**, non i valori. Un id e un istante differiscono per
    costruzione e non sono una divergenza di contratto; un campo che da una parte
    è una stringa e dall'altra una lista lo è, ed è la forma che nessuno guarda
    perché il nome combacia.
  · la ricevuta **che la porta RENDE a chi la usa**, non quella che calcola
    dentro. `cli.py` calcola la ricevuta intera (`r = m.add(text, **kw)`) e ne
    stampa cinque campi in prosa: per un consumatore quella ricevuta non esiste.
    Contarla come presente misurerebbe il codice invece del prodotto.

IL CONTROLLO NEGATIVO sta qui dentro e non a parte: una scrittura FERMATA deve
dichiarare `fermato_da` su tutte e tre. Se fosse vuoto ovunque, «identiche»
sarebbe vero per il motivo sbagliato — tre ricevute ugualmente mute.

Ticket: fetta 1 (la ricevuta). Registro: la classe «giuntura: calcolato e non
letto», la stessa di T56 e T77.
"""
from __future__ import annotations

import json
import pathlib

import pytest

TESTO = "Il capannone 12 misura 400 metri quadri."
FONTE = "Perizia del 2026-03-04: il capannone 12 misura 400 mq."
TOPIC = "note"

#: I campi che un consumatore deve poter leggere per sapere COSA È SUCCESSO alla
#: sua scrittura. Non è la lista completa della ricevuta: è il minimo su cui le
#: tre porte devono coincidere perché la promessa «memoria verificata» si possa
#: controllare da fuori.
CAMPI_CHE_CONTANO = frozenset({
    "id", "stored", "status", "layers", "judged", "warnings", "adjudication",
})


def _ricevuta_sdk() -> dict:
    from verimem.client import open_memory
    #: senza argomento: legge le tre variabili che la fixture punta allo store
    #: di prova, che e' come lo apre un consumatore.
    m = open_memory()
    return dict(m.add(TESTO, topic=TOPIC, source=FONTE) or {})


async def _ricevuta_mcp() -> dict:
    from tests.test_mcp_thin import _invoke_tool
    blocchi = await _invoke_tool(
        "hippo_remember",
        {"proposition": TESTO, "topic": TOPIC, "source": FONTE},
    )
    return json.loads(blocchi[0])


def _stdout_della_cli(testo: str = "", fonte: str | None = None,
                      extra_env: dict | None = None) -> str:
    """Lo stdout di una scrittura con fonte dalla CLI, come lo vede uno script.

    ⚠️ CORREZIONE DEL 18/09, e la premessa sbagliata era mia. La prima stesura
    usava `verimem remember`, che il `--json` non ce l'ha, e ne concludeva
    «la CLI non rende NIENTE». È vero di QUEL comando, non della porta: il
    comando di scrittura con la ricevuta leggibile è `save`, e il `--json` c'è
    (`cli.py:5428`). Misurare il comando sbagliato e chiamarlo «la porta» è la
    stessa forma di difetto che questo file esiste per rendere visibile.

    Sottoprocesso e non `CliRunner`: quest'ultimo mescola stdout e stderr, e con
    i flussi mescolati non si può dire se a sporcare la ricevuta sia il prodotto
    o il banco. Qui si legge lo stdout da solo, che è ciò che riceve chi mette
    `| jq` in fondo.
    """
    import os
    import subprocess
    import sys
    import tempfile

    radice = pathlib.Path(__file__).resolve().parents[1]
    store = pathlib.Path(tempfile.mkdtemp(prefix="ws1_cli_"))
    (store / "semantic").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({"ENGRAM_DATA_DIR": str(store), "HIPPO_DATA_DIR": str(store),
                "VERIMEM_DATA_DIR": str(store), "PYTHONPATH": str(radice)})
    #: 🪞 SI TOGLIE, E SENZA QUESTA RIGA IL TEST MENTE. `mcp_server.py:52` fa
    #: `os.environ["HIPPO_LOG_STDERR"] = "1"` AL MOMENTO DELL'IMPORT: questo
    #: file importa la porta MCP, quindi il sottoprocesso EREDITAVA quella
    #: variabile e vedeva uno stdout pulito che l'utente non ha. Misurato con
    #: un A/B a una variabile sullo stesso comando:
    #:     senza la variabile   stdout 759 caratteri -> NON e' JSON   exit 0
    #:     con  la variabile    stdout 482 caratteri -> JSON pulito   exit 0
    #: Qui si misura il regime di chi usa il prodotto, non quello che l'import
    #: di un'altra porta ha lasciato nell'ambiente.
    env.pop("HIPPO_LOG_STDERR", None)
    env.update(extra_env or {})
    comando = [sys.executable, "-m", "verimem.cli", "save", testo or TESTO,
               "--topic", TOPIC, "--json"]
    sorgente = FONTE if fonte is None else fonte
    if sorgente:
        comando += ["--source", sorgente]
    esito = subprocess.run(
        comando, cwd=str(radice), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=600,
    )
    return esito.stdout or ""


def _json_dallo_stdout(testo: str) -> dict:
    """L'ultimo oggetto JSON dello stdout, anche quando il flusso è sporco."""
    for riga in reversed(testo.splitlines()):
        riga = riga.strip()
        if riga.startswith("{"):
            try:
                return json.loads(riga)
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(testo)
    except (json.JSONDecodeError, ValueError):
        return {}


def _ricevuta_cli() -> dict:
    """La ricevuta della CLI, estratta dallo stdout anche se non è pulito.

    Il test qui sotto (`…_e_leggibile_da_sola`) inchioda il fatto che oggi
    **non** lo è: una riga di giornale la precede sullo stesso flusso. Qui si
    prende comunque l'ultimo oggetto JSON, perché il confronto fra le tre
    ricevute deve poter girare anche mentre quel difetto è aperto — altrimenti
    un difetto ne nasconderebbe un altro.
    """
    return _json_dallo_stdout(_stdout_della_cli())


def _forma(r: dict) -> dict:
    """Nome del campo -> nome del tipo. È il contratto, senza i valori."""
    return {k: type(v).__name__ for k, v in r.items()}


@pytest.mark.asyncio
async def test_CONTROLLO_ogni_porta_rende_qualcosa(isolated_corpus):
    """Senza questo, «le tre ricevute coincidono» sarebbe vero anche se fossero
    tutte e tre vuote: il verde più silenzioso che esista."""
    sdk = _ricevuta_sdk()
    mcp = await _ricevuta_mcp()
    assert sdk, "la porta SDK non ha reso nessuna ricevuta: il banco non misura"
    assert mcp, "la porta MCP non ha reso nessuna ricevuta: il banco non misura"


def test_la_ricevuta_json_della_cli_e_leggibile_da_sola():
    """`save --json` promette una ricevuta a macchina: deve poterla LEGGERE.

    Misurato il 18/09: `exit_code 0`, 759 caratteri su stdout, e
    `json.loads(stdout)` **fallisce** — una riga di giornale (`flow.write …
    layers=[] …`) precede l'oggetto JSON sullo STESSO flusso. Chi mette `| jq`
    in fondo riceve un errore di parsing con esito ZERO: il caso peggiore, uno
    script che crede di aver funzionato.

    📌 E quella riga porta `layers=[]`, cioè proprio il campo che nessuna delle
    tre ricevute rende: il dato esiste, viaggia sul canale sbagliato.
    """
    testo = _stdout_della_cli()
    assert testo.strip(), "la CLI non ha stampato niente su stdout"
    try:
        json.loads(testo)
    except json.JSONDecodeError as e:
        prima = "\n".join(testo.splitlines()[:2])[:300]
        raise AssertionError(
            "`save --json` non produce uno stdout leggibile come JSON "
            f"({e.__class__.__name__}): qualcosa scrive sullo stesso flusso "
            f"prima della ricevuta.\n  prime righe:\n{prima}"
        ) from None


@pytest.mark.asyncio
async def test_le_tre_porte_rendono_la_stessa_ricevuta(isolated_corpus):
    """IL CUORE. Stesso testo, stessa fonte, stesso topic, stesso store."""
    forme = {
        "SDK": _forma(_ricevuta_sdk()),
        "MCP": _forma(await _ricevuta_mcp()),
        "CLI": _forma(_ricevuta_cli()),
    }
    chiavi = {porta: set(f) for porta, f in forme.items()}
    comuni = set.intersection(*chiavi.values())
    differenze = []
    for porta, k in chiavi.items():
        altre = set.union(*(v for p, v in chiavi.items() if p != porta))
        solo_qui = sorted((k - altre) & (k | CAMPI_CHE_CONTANO))
        if solo_qui:
            differenze.append(f"solo su {porta}: {solo_qui}")
    for porta, k in chiavi.items():
        mancanti = sorted(CAMPI_CHE_CONTANO - k)
        if mancanti:
            differenze.append(f"{porta} non rende: {mancanti}")
    # ⚠️ UN CAMPO A `None` NON E' UNA DIVERGENZA DI CONTRATTO: e' un campo che
    # in QUESTO regime nessuno ha prodotto. Il 18/09 avevo pubblicato
    # «grounding_score: float su SDK/MCP, NoneType sulla CLI» come divergenza —
    # e l'A/B a una variabile sulla STESSA riga di comando dice che era il mio
    # banco:
    #     ambiente dell'utente  -> 11 chiavi, grounding_score 98.87, judged_by 'daemon'
    #     ambiente del banco    -> 10 chiavi, grounding_score None,  judged_by None
    # (il sottoprocesso eredita `HIPPO_OFFLINE=1` e l'embedder stub che il
    # conftest impone, mentre SDK e MCP girano in-process col giudice finto che
    # un punteggio lo rende). Il tipo si confronta solo sui valori PRODOTTI.
    for campo in sorted(comuni):
        tipi = {porta: f[campo] for porta, f in forme.items()
                if campo in f and f[campo] != "NoneType"}
        if len(set(tipi.values())) > 1:
            differenze.append(f"stesso nome, tipo diverso: {campo} -> {tipi}")

    assert not differenze, (
        "le tre porte non rendono la stessa ricevuta.\n  "
        + "\n  ".join(differenze)
        + "\n  chiavi per porta:\n    "
        + "\n    ".join(f"{p}: {sorted(k)}" for p, k in chiavi.items())
    )


@pytest.mark.asyncio
async def test_CONTROLLO_NEGATIVO_una_scrittura_fermata_dichiara_chi_l_ha_fermata(
        isolated_corpus):
    """Una scrittura che il cancello FERMA deve dirlo su tutte e tre.

    È il controllo che rende onesto il test sopra: se una ricevuta tace quando
    la scrittura è stata trattenuta, «identiche» non vuol dire «giuste».
    """
    vanto = "Questo sistema funziona perfettamente e non sbaglia mai."
    from verimem.client import open_memory
    sdk = dict(open_memory().add(vanto, topic=TOPIC) or {})
    from tests.test_mcp_thin import _invoke_tool
    mcp = json.loads((await _invoke_tool(
        "hippo_remember", {"proposition": vanto, "topic": TOPIC}))[0])

    def _fermato_da(r: dict) -> str:
        for campo in ("fermato_da", "quarantined_by", "withheld_by"):
            if r.get(campo):
                return f"{campo}={r[campo]!r}"
        avvisi = r.get("warnings") or []
        strati = [w.get("layer") for w in avvisi if isinstance(w, dict) and w.get("layer")]
        return f"warnings[].layer={strati}" if strati else ""

    cli = _json_dallo_stdout(_stdout_della_cli(vanto, fonte=""))
    esiti = {"SDK": _fermato_da(sdk), "MCP": _fermato_da(mcp),
             "CLI": _fermato_da(cli)}
    assert all(esiti.values()), (
        "una scrittura trattenuta non dichiara CHI l'ha fermata su ogni porta: "
        f"{esiti}. Senza questo campo la ricevuta e' muta proprio nel caso in "
        "cui l'utente deve sapere perche' il suo fatto non e' entrato."
    )


@pytest.mark.asyncio
async def test_CONTROLLO_NEGATIVO_T96_una_scrittura_degradata_non_si_chiama_ammessa(
        isolated_corpus):
    """T96. Una scrittura AMMESSA IN FORMA DEGRADATA non è una scrittura ammessa.

    Il meccanismo, letto prima di scrivere il test: con
    ``ENGRAM_GRADED_ADMISSION=1`` (`anti_confab_gate.py:175-190`) un punteggio
    sotto la soglia su un fatto CON fonte non va più in quarantena — il fatto
    resta come `model_claim` a bassa fiducia e la ricevuta registra lo scarto
    con uno strato ``L4-grounding-graded`` (`:2875-2892`).

    ⇒ Il negativo: nessuna porta può dire «ammesso» SENZA portarsi dietro quel
    marchio. Se una lo dice, chi legge quella ricevuta crede di avere un fatto
    verificato e ne ha uno tenuto per cortesia.

    ⚠️ Se la degradazione non si accende, il test lo DICE invece di passare: un
    controllo che non trova il caso non ha misurato niente.
    """
    import os

    claim = "La coda ha 999 elementi."
    fonte = "verbale: la coda aveva 500 elementi / rettifica: 540 elementi"
    acceso = {"ENGRAM_GRADED_ADMISSION": "1"}
    for chiave, valore in acceso.items():
        os.environ[chiave] = valore
    try:
        from verimem.client import open_memory
        sdk = dict(open_memory().add(claim, topic=TOPIC, source=fonte) or {})
        from tests.test_mcp_thin import _invoke_tool
        mcp = json.loads((await _invoke_tool(
            "hippo_remember",
            {"proposition": claim, "topic": TOPIC, "source": fonte}))[0])
        cli = _json_dallo_stdout(
            _stdout_della_cli(claim, fonte=fonte, extra_env=acceso))
    finally:
        for chiave in acceso:
            os.environ.pop(chiave, None)

    def _degradata(r: dict) -> bool:
        return "-graded" in json.dumps(r, default=str)

    def _dice_ammesso(r: dict) -> bool:
        disp = (r.get("adjudication") or {}).get("disposition")
        return str(disp).lower() in ("admitted", "ammesso")

    porte = {"SDK": sdk, "MCP": mcp, "CLI": cli}
    if not any(_degradata(r) for r in porte.values()):
        raise AssertionError(
            "il caso degradato non si e' acceso su NESSUNA porta: il controllo "
            "non ha misurato niente. Disposizioni: "
            + str({p: (r.get("adjudication") or {}).get("disposition")
                   for p, r in porte.items()})
        )
    mute = {p: (r.get("adjudication") or {}).get("disposition")
            for p, r in porte.items()
            if _dice_ammesso(r) and not _degradata(r)}
    assert not mute, (
        "una scrittura degradata viene chiamata «ammessa» senza il marchio "
        f"«-graded» da queste porte: {mute}. Chi legge crede di avere un fatto "
        "verificato e ne ha uno tenuto in forma degradata."
    )
