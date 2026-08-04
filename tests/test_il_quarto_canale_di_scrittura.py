"""C'è un quarto canale che scrive fatti, e il moat non è raggiungibile da lì.

`test_all_write_channels_judge_a_source` apre dicendo «**Three** entry points
write facts» ed elenca SDK, `save_checkpoint` e `hippo_remember`. Ma
``verimem facts add`` — il comando dell'import BULK, quello con
``--jsonl-stdin`` per caricare i risultati di un tool a pacchi — ne è un quarto,
e non ha nessuna porta per la `source`: ha ``--verified-by``, che è un'altra
cosa. Lo dice il prodotto stesso nelle proprie istruzioni MCP:

    `verified_by` records WHO vouches for a fact and does not run this check;
    pass the source text to get it.

Quindi da quel canale il moat non è SPENTO per configurazione: **non c'è il modo
di accenderlo**. È la stessa forma di `key_facts`, curata il 2026-07-30
(«su quel canale il moat non poteva girare NEMMENO volendo»), e nello stesso
giorno la cura non è stata portata al gemello — la classe «la cura c'era e
mancava lo sweep», la terza volta in una settimana.

E C'È UN SECONDO DIFETTO, che è il motivo per cui nessuno se n'era accorto: il
presidio che dovrebbe vederlo **enumera i canali a mano**. La sua docstring
promette l'invariante universale — «A new channel that skips the gate breaks
this, which is the only thing that stops the bug from coming back under a
different name» — ma un canale che non è nella lista non è coperto. Un invariante
verificato su una lista scritta a mano vale quanto la lista.

L'ultimo test di questo file chiude proprio quello: non elenca niente, **scopre**
dall'AST chi chiama il gate e pretende che ognuno abbia la porta.

Deterministico e senza giudice: il gate è sostituito da un doppio che registra i
kwargs ricevuti. Serve sapere se il canale CHIEDE il giudizio e se PERSISTE il
verdetto — non quanto vale il verdetto.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sqlite3
import types
from typing import Any

import pytest
from typer.testing import CliRunner

from verimem.cli import app

PROP = "La fattura totale è di 1240 euro."
SRC = "Fattura 88: imponibile 1000, IVA 240, totale 1240 euro."


class _GateFinto:
    """Registra come è stato chiamato e restituisce un verdetto persistibile."""

    def __init__(self) -> None:
        self.chiamate: list[dict[str, Any]] = []

    def __call__(self, **kw: Any):
        self.chiamate.append(kw)
        return types.SimpleNamespace(
            action="persist", advice="", warnings=[], grounding_score=95.0,
            judge="stub", to_dict=lambda: {"action": "persist"},
        )


@pytest.fixture()
def gate(monkeypatch: pytest.MonkeyPatch) -> _GateFinto:
    finto = _GateFinto()
    import verimem.anti_confab_gate as acg
    monkeypatch.setattr(acg, "run_validation_gate", finto)
    return finto


@pytest.fixture()
def store(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """`facts add` prende lo store da `_facts_sm()`: lo si punta su tmp."""
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "q.db")
    import verimem.cli as cli
    monkeypatch.setattr(cli, "_facts_sm", lambda *a, **k: sm)
    return sm


def _grounding(sm: Any, fact_id: str) -> float | None:
    with sqlite3.connect(str(sm.db_path)) as c:
        r = c.execute("SELECT grounding_score FROM facts WHERE id = ?",
                      (fact_id,)).fetchone()
    return r[0] if r else None


def test_il_comando_accetta_una_source(gate, store):
    """La porta esiste. Senza, non c'è discussione su cosa ci passi dentro."""
    r = CliRunner().invoke(app, ["facts", "add", "-p", PROP, "-t", "q/uno",
                                 "--source", SRC])
    assert r.exit_code == 0, (
        f"`facts add --source` non è accettato (exit {r.exit_code}): il canale "
        f"dell'import bulk non ha modo di consegnare l'evidenza al moat.\n"
        f"{r.output}")


def test_la_source_arriva_al_gate_e_ne_ACCENDE_il_giudizio(gate, store):
    """Non basta accettare l'opzione: deve arrivare al gate, e con
    `ground_write`. È la coppia esatta usata da `verimem save` (cli.py:1401) e
    dalla cura di `key_facts` (mcp_server.py:8617)."""
    CliRunner().invoke(app, ["facts", "add", "-p", PROP, "-t", "q/due",
                             "--source", SRC])
    assert gate.chiamate, "il gate non è stato chiamato affatto"
    kw = gate.chiamate[-1]
    assert kw.get("source") == SRC, (
        f"la source non arriva al gate: {kw.get('source')!r}. `verified_by` "
        f"registra CHI garantisce e non fa girare questo controllo")
    assert kw.get("ground_write") is True, (
        f"ground_write={kw.get('ground_write')!r}: senza, il canale ricade "
        f"su ENGRAM_GROUNDING_WRITE, che nessun file dell'albero imposta — "
        f"esattamente il buco chiuso il 2026-07-29 sull'altro canale")


def test_senza_source_NON_si_chiede_il_giudizio(gate, store):
    """Il contrario, perché la cura non diventi un interruttore sempre acceso:
    senza evidenza non c'è niente da verificare, e chiedere il giudizio
    costerebbe una chiamata al giudice per nulla."""
    CliRunner().invoke(app, ["facts", "add", "-p", PROP, "-t", "q/tre"])
    kw = gate.chiamate[-1]
    assert not kw.get("source")
    assert kw.get("ground_write") in (None, False), (
        f"ground_write={kw.get('ground_write')!r} senza source")


def test_il_verdetto_viene_PERSISTITO_non_solo_calcolato(gate, store):
    """«Giudicato ma non PERSISTITO» è la formula con cui il presidio SDK
    boccia questo caso: un verdetto che muore col processo non è provenienza, e
    ogni lettura successiva chiamerebbe il fatto non giudicato."""
    r = CliRunner().invoke(app, ["facts", "add", "-p", PROP, "-t", "q/quattro",
                                 "--source", SRC])
    assert r.exit_code == 0, r.output
    fatti = store.all()
    assert fatti, "nessun fatto salvato"
    assert _grounding(store, fatti[-1].id) is not None, (
        "il moat ha girato e il suo verdetto non è finito nel DB: il fatto "
        "risulterà NON GIUDICATO a ogni lettura futura")


def test_anche_l_import_BULK_puo_portare_la_propria_source(gate, store):
    """Il caso per cui il comando esiste: un record per riga, ognuno con la
    sua evidenza. Se la porta fosse solo sul flag, il bulk — cioè l'uso
    principale — resterebbe fuori dal moat."""
    riga = json.dumps({"proposition": PROP, "topic": "q/cinque", "source": SRC})
    r = CliRunner().invoke(app, ["facts", "add", "--jsonl-stdin"], input=riga)
    assert r.exit_code == 0, r.output
    assert gate.chiamate and gate.chiamate[-1].get("source") == SRC, (
        f"la source per-record del JSONL non arriva al gate: "
        f"{gate.chiamate[-1].get('source')!r}")


def test_OGNI_comando_che_passa_dal_gate_ha_una_porta_per_la_source():
    """IL CRICCHETTO, e non elenca niente: SCOPRE.

    Il presidio esistente enumera tre canali a mano, e per questo non ha visto
    il quarto. Qui si legge l'AST di `cli.py`, si trovano le funzioni che
    chiamano `run_validation_gate`, e si pretende che ognuna abbia un parametro
    `source`. Un canale nuovo che nasce senza la porta accende questo test il
    giorno in cui viene scritto, non il giorno in cui qualcuno lo prova a mano.

    Si guarda la STRUTTURA e non il testo: cercare 'source' nel sorgente
    accenderebbe su ogni commento che nomina la parola."""
    sorgente = pathlib.Path("verimem/cli.py").read_text(encoding="utf-8")
    albero = ast.parse(sorgente)

    senza_porta: list[str] = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        chiama_il_gate = any(
            isinstance(c, ast.Call)
            and getattr(c.func, "id", getattr(c.func, "attr", None))
            == "run_validation_gate"
            for c in ast.walk(nodo)
        )
        if not chiama_il_gate:
            continue
        nomi = {a.arg for a in nodo.args.args} | {a.arg for a in nodo.args.kwonlyargs}
        if "source" not in nomi:
            senza_porta.append(f"{nodo.name} (riga {nodo.lineno})")

    assert not senza_porta, (
        "questi comandi consegnano una scrittura al gate ma non hanno modo di "
        "consegnargli l'EVIDENZA, quindi da lì il moat non è accendibile:\n  "
        + "\n  ".join(senza_porta)
        + "\naggiungi un parametro `source` e passalo come fa `verimem save`: "
          "`source=source, ground_write=True if source else None`")
