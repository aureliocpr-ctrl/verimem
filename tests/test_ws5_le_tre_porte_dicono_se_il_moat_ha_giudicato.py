"""T26a/a — quando il moat NON giudica, le tre porte lo dicono **e nello stesso modo**?

⚠️ PERCHE' ESISTE. In delegate-only senza un daemon raggiungibile
``try_local_score`` torna ``None``: una scrittura CON FONTE entra **non
giudicata**, e nessuno la rimette in coda quando il giudice si sveglia
(``preload._deve_scaldare_il_giudice``, misurato il 2026-07-30). La cura
``d47f5ebc`` ha messo ``judged`` in cima alla ricevuta MCP perche' «l'assenza di
una misura si legge come un verdetto buono».

🔴🔴 LA PRIMA VERSIONE DI QUESTO FILE ERA SBAGLIATA, e come lo era conta piu'
del difetto. Cercava ``"judged" in json.dumps(ricevuta)`` — una sottostringa
nell'INTERO json — e passava perche' la parola compariva **dentro una frase di
consiglio**::

    "advice": "…What gets the FIRST write judged is a reachable shared
               encode daemon; `verimem doctor` says whether one is…"

Un verde comprato da una parola in prosa. E il reperto che ne avevo tratto — «la
porta SDK tace, una porta su tre» — era **falso**: la ricevuta SDK dichiara il
verdetto mancante nel suo PRIMO campo (``"moat": "not_run:no_judge"``), piu'
``grounding_score: null``, un warning ``L4-skipped`` e
``adjudication.evidence_class: "ungated"``. Ritirato sul canale il 09/09.

🔑 QUINDI IL CRITERIO QUI GUARDA I CAMPI, MAI IL TESTO. Una ricevuta «dichiara»
solo se un campo STRUTTURATO porta il verdetto mancante. La prosa di aiuto e'
esclusa apposta: e' utile a un umano e invisibile a un agente che legge chiavi.

📏 E LA DOMANDA VERA NON E' «quante porte lo dicono» MA «lo dicono nello STESSO
MODO»: R4 chiede una superficie sola per tutte e tre. Tre forme diverse per lo
stesso stato costringono chi integra a conoscerle tutte e tre, ed e' la classe
«una copia invece della superficie unica».

Giudice = ORACOLO (``try_local_score`` -> None): misura SE LA PORTA LO DICE, non
quanto e' bravo il modello. Zero RAM, gira in CI senza il CE.

⛔ TRAPPOLA DI GIANO, rispettata: ``CONFIG`` e' ``frozen=True`` istanziata a
import-time (``config.py:119`` e ``:559``), quindi l'ambiente si imposta PRIMA e
verimem si importa DENTRO la fixture; c'e' un assert che ``CONFIG.data_dir`` sia
nella tempdir e il conteggio delle righe dello store VERO prima/dopo.
"""
from __future__ import annotations

import importlib
import pathlib
import sqlite3
import sys

import pytest

STORE_VERO = pathlib.Path.home() / ".engram" / "semantic" / "semantic.db"

FATTO = "Il canone del capannone 12 e' 5900 euro."
FONTE = "Contratto del 3 marzo: il canone mensile del capannone 12 e' 5900 euro."


def _righe_dello_store_vero() -> int:
    if not STORE_VERO.exists():
        return -1
    con = sqlite3.connect(f"file:{STORE_VERO}?mode=ro", uri=True)
    try:
        return con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    finally:
        con.close()


def dichiara_il_verdetto_mancante(ricevuta) -> tuple[bool, str]:
    """Un CAMPO della ricevuta dice che il moat non ha giudicato?

    Torna (sì/no, quale campo). Le forme accettate sono quelle che un agente
    puo' leggere senza interpretare prosa:

      - ``judged`` booleano falso                      (la forma di MCP)
      - ``moat`` che comincia per ``not_run``          (la forma dell'SDK)
      - ``adjudication.evidence_class == "ungated"``   (idem, piu' in basso)
      - un warning il cui ``layer`` e' ``L4-skipped``  (campo, non testo)

    ⚠️ NON accettato: la parola «judged» dentro ``advice`` o dentro il testo di
    un warning. E' esattamente cio' che ha comprato il falso verde della prima
    versione, ed e' escluso qui per costruzione, non per attenzione.
    """
    if not isinstance(ricevuta, dict):
        return False, "(la ricevuta non e' un dizionario)"
    if ricevuta.get("judged") is False:
        return True, "judged=False"
    moat = ricevuta.get("moat")
    if isinstance(moat, str) and moat.startswith("not_run"):
        return True, f"moat={moat!r}"
    adj = ricevuta.get("adjudication")
    if isinstance(adj, dict) and adj.get("evidence_class") == "ungated":
        return True, "adjudication.evidence_class='ungated'"
    for w in ricevuta.get("warnings") or []:
        if isinstance(w, dict) and w.get("layer") == "L4-skipped":
            return True, "warnings[].layer='L4-skipped'"
    return False, "(nessun campo lo dichiara)"


@pytest.fixture
def porta_isolata(tmp_path, monkeypatch):
    dati = tmp_path / "engram"
    dati.mkdir(parents=True, exist_ok=True)
    # tutti e tre gli alias, o il prodotto avvisa che litigano e ne sceglie uno
    for chiave in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(chiave, str(dati))
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.setenv("ENGRAM_ADMISSION_GATE", "1")
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setenv("HIPPO_OFFLINE", "1")

    for nome in [m for m in list(sys.modules) if m.startswith("verimem")]:
        del sys.modules[nome]
    config = importlib.import_module("verimem.config")

    percorso = str(getattr(config.CONFIG, "data_dir", ""))
    assert str(tmp_path) in percorso, (
        f"IL BANCO NON E' ISOLATO: CONFIG.data_dir = {percorso!r}. Fermarsi: la "
        "prossima riga scriverebbe nello store vero di Aurelio."
    )
    prima = _righe_dello_store_vero()
    yield dati
    dopo = _righe_dello_store_vero()
    assert prima == dopo, (
        f"IL BANCO HA TOCCATO LO STORE VERO: {prima} righe prima, {dopo} dopo."
    )


@pytest.fixture
def giudice_muto(monkeypatch):
    """L'oracolo: nessun verdetto. E' il delegate-only senza daemon riprodotto,
    non imitato — `try_local_score` che torna None E' quello stato."""
    from verimem import local_grounding
    chiamate: list[str] = []

    def _muto(*a, **kw):
        chiamate.append("chiesto")
        return None

    monkeypatch.setattr(local_grounding, "try_local_score", _muto)
    return chiamate


def test_la_porta_SDK_dichiara_il_verdetto_mancante(porta_isolata, giudice_muto):
    """VERDE atteso, ed e' il controllo positivo del criterio: se questo non
    passasse, il criterio sarebbe troppo severo e i rossi degli altri due non
    direbbero niente."""
    from verimem.client import Memory

    ricevuta = Memory().add(FATTO, topic="ws5/banco", source=FONTE)
    assert giudice_muto, (
        "la porta SDK non ha nemmeno CHIESTO il giudizio: sarebbe il difetto di "
        "T-MAP-11, e questo banco misurerebbe un'altra cosa"
    )
    dichiara, dove = dichiara_il_verdetto_mancante(ricevuta)
    assert dichiara, f"la porta SDK non lo dichiara in nessun campo: {ricevuta}"
    print(f"\n[SDK] lo dichiara in: {dove}")


def test_la_porta_MCP_dichiara_il_verdetto_mancante(porta_isolata, giudice_muto):
    """La porta curata da ``d47f5ebc``. La chiave del tool e' ``proposition``:
    passargli ``content`` fa tornare un errore, e il prodotto lo dice per nome
    (preso in faccia il 09/09, era un mio errore di banco, non suo)."""
    import asyncio
    import json as _json

    from verimem import mcp_server as srv

    grezza = asyncio.run(
        srv._call_tool_impl(
            "hippo_remember",
            {"proposition": FATTO, "topic": "ws5/banco", "source": FONTE},
        )
    )
    # il tool torna una lista di blocchi di testo: la ricevuta e' il json dentro
    ricevuta = grezza
    if isinstance(grezza, list) and grezza:
        testo = getattr(grezza[0], "text", None) or str(grezza[0])
        try:
            ricevuta = _json.loads(testo)
        except Exception:
            pytest.fail(f"la porta MCP non ha reso un json leggibile: {testo[:300]}")
    assert "error" not in ricevuta, f"la chiamata alla porta e' stata rifiutata: {ricevuta}"
    dichiara, dove = dichiara_il_verdetto_mancante(ricevuta)
    assert dichiara, f"la porta MCP non lo dichiara in nessun campo: {ricevuta}"
    print(f"\n[MCP] lo dichiara in: {dove}")


def test_le_tre_forme_sono_LA_STESSA(porta_isolata, giudice_muto):
    """LA DOMANDA DI R4. Non «quante porte lo dicono» ma «lo dicono nello stesso
    modo»: chi integra due porte non deve imparare due vocabolari per lo stesso
    stato. Rosso qui = c'e' da unificare, non da aggiungere."""
    import asyncio
    import json as _json

    from verimem import mcp_server as srv
    from verimem.client import Memory

    _, dove_sdk = dichiara_il_verdetto_mancante(
        Memory().add(FATTO, topic="ws5/banco", source=FONTE)
    )
    grezza = asyncio.run(
        srv._call_tool_impl(
            "hippo_remember",
            {"proposition": FATTO, "topic": "ws5/banco/2", "source": FONTE},
        )
    )
    ric_mcp = grezza
    if isinstance(grezza, list) and grezza:
        testo = getattr(grezza[0], "text", None) or str(grezza[0])
        try:
            ric_mcp = _json.loads(testo)
        except Exception:
            pytest.fail(f"la porta MCP non ha reso un json leggibile: {testo[:300]}")
    _, dove_mcp = dichiara_il_verdetto_mancante(ric_mcp)

    assert dove_sdk == dove_mcp, (
        "LE DUE PORTE DICONO LA STESSA COSA IN DUE FORME DIVERSE — chi integra "
        f"deve conoscerle entrambe:\n  SDK -> {dove_sdk}\n  MCP -> {dove_mcp}"
    )


def test_la_porta_CLI_dichiara_il_verdetto_mancante(porta_isolata, giudice_muto):
    """La TERZA porta. Misurata il 10/09 PRIMA della cura: con il giudice muto
    stampava::

        inserted: 1 fact(s). quarantined=0 rejected=0 parse_errors=0
          id=a6766f179a14  status=ok

    e NESSUNA delle sei parole cercate (judged / not_run / giudic / moat /
    unverified / ungated). Non e' silenzio: e' `status=ok`, cioe' l'affermazione
    che e' andato tutto bene su una scrittura CON FONTE che nessuno ha
    verificato — e il giudice ERA stato interrogato (1 volta): la porta chiede e
    non riporta la risposta mancante.

    ⚠️ Il testo va in ``--proposition``, non posizionale: passarlo come argomento
    fa tornare «Got unexpected extra argument» (preso in faccia il 10/09, il
    prodotto lo dice per nome).

    ⚠️ ``CliRunner`` mette l'eccezione in ``result.exception``, NON nell'output:
    un assert sul solo output non puo' fallire su un errore (trappola pagata da
    @ws1 lo stesso giorno). Qui si guarda entrambi.
    """
    from typer.testing import CliRunner

    from verimem.cli import app

    r = CliRunner().invoke(
        app,
        ["facts", "add", "--proposition", FATTO,
         "--topic", "ws5/banco", "--source", FONTE],
    )
    assert r.exception is None, (
        f"la porta CLI ha sollevato: {type(r.exception).__name__}: {r.exception}"
    )
    assert r.exit_code == 0, f"exit={r.exit_code}, output: {r.output[:300]}"
    assert giudice_muto, (
        "la porta CLI non ha nemmeno CHIESTO il giudizio: sarebbe un difetto "
        "diverso e questo banco misurerebbe la cosa sbagliata"
    )
    # qui il criterio NON puo' guardare i campi (la CLI stampa prosa): guarda
    # la PAROLA CANONICA, che e' la stessa delle altre due porte.
    assert "judged=false" in r.output.lower(), (
        "LA PORTA CLI TACE, e dice `status=ok` su una scrittura che il moat non "
        f"ha giudicato. Quello che l'utente vede e':\n{r.output[:400]}"
    )
