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


def _ricevuta_cli() -> dict:
    """Ciò che la CLI rende LEGGIBILE a un consumatore.

    `verimem remember` non ha `--json` (verificato: le opzioni sono `--topic`,
    `--source`, `--valid-until`, `--db`), quindi stampa prosa colorata. Un
    consumatore non ha una ricevuta: ha un testo. Qui si tenta di leggerlo come
    JSON e, quando non lo è, si rende il vocabolario vuoto — che è esattamente
    ciò che quel consumatore può usare.
    """
    from typer.testing import CliRunner

    from verimem.cli import app
    esito = CliRunner().invoke(
        app, ["remember", TESTO, "--topic", TOPIC, "--source", FONTE])
    try:
        return json.loads(esito.stdout)
    except (json.JSONDecodeError, ValueError):
        return {}


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
    for campo in sorted(comuni):
        tipi = {porta: f[campo] for porta, f in forme.items() if campo in f}
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

    esiti = {"SDK": _fermato_da(sdk), "MCP": _fermato_da(mcp)}
    assert all(esiti.values()), (
        "una scrittura trattenuta non dichiara CHI l'ha fermata su ogni porta: "
        f"{esiti}. Senza questo campo la ricevuta e' muta proprio nel caso in "
        "cui l'utente deve sapere perche' il suo fatto non e' entrato."
    )
