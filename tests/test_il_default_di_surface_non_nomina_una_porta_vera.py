"""Il default di ``surface`` non deve nominare una porta vera.

LA CURA DEL 2026-08-04, dal commento al punto di emissione
(``flow_events.py``)::

    9357 of 9603 real-corpus writes claimed "sdk" while 438 MCP write calls
    produced ZERO "mcp" events — a dashboard cannot tell a default from a
    datum. Every real entrypoint now declares itself; what remains genuinely
    unknown SAYS unknown.

⇒ Il default e' stato tolto **di proposito**: ``os.environ.get(...) or
"unknown"``. Ma la docstring del modulo ha continuato a dichiarare ``sdk
(default)`` fino al 2026-08-30 — **prosa vecchia contro codice curato**, nel
modulo che DEFINISCE il campo.

PERCHE' UN PRESIDIO E NON SOLO UNA CORREZIONE: la riga e' esattamente il genere
di frase che chi costruisce un cruscotto legge per decidere come contare. Se
tornasse a dire ``sdk (default)``, chi conta leggerebbe di nuovo un default come
un dato — cioe' il difetto che la cura del 04/08 ha misurato in 9357 casi.

⚠️ MISURATO SUL JOURNAL DI CASA il 2026-08-30 alle 21:34, finestra 21/08 10:02
-> 30/08 21:20, in sola lettura (``events.jsonl.1`` + ``events.jsonl``, perche'
il journal RUOTA e chi legge solo la coda misura la coda)::

    flow.write    tot 10955   unknown 6960 · cli 2990 · gateway 987 · sdk 18 · mcp 0
    flow.warmup   tot  2117   mcp 1230 · cli 557 · unknown 320 · gateway 10

Il valore ``mcp`` **esiste** nel journal e non compare **mai** su una scrittura.
⚠️ Due letture, e il controllo che le distingue e' CADUTO: ho provato a
raggruppare per ``build``, ma ``build`` identifica la VERSIONE del codice, non
il processo (un solo build porta sia ``cli`` sia ``unknown``). ⇒ Non so dire se
(a) il server MCP scriva senza marcarsi, oppure (b) non scriva affatto in questo
corpus. **Il dato e' pubblicato come domanda, non come accusa**, e il presidio
qui sotto riguarda solo la parte certa: la prosa del default.
"""

from __future__ import annotations

import inspect

from verimem import flow_events


def test_la_docstring_non_dichiara_sdk_come_default():
    """IL CUORE: e' la riga che un cruscotto legge per decidere come contare.

    ⚠️ E LA CRONACA NON PUO' CITARE LA FRASE VECCHIA ALLA LETTERA, o questo
    presidio diventa rosso su di essa: la prima stesura della cura scriveva
    «this line said ``sdk (default)`` until…» e faceva fallire il test che
    doveva difenderla. **Si riformula la cronaca, non si indebolisce il
    presidio** — e' la seconda volta stasera che questa forma mi morde (la
    prima su `RIMEDIO_LLM`).
    """
    testo = inspect.getdoc(flow_events) or ""
    assert "``sdk`` (default)" not in testo, testo[:400]
    assert "sdk (default)" not in testo, testo[:400]


def test_la_docstring_nomina_il_default_vero():
    testo = inspect.getdoc(flow_events) or ""
    assert "unknown" in testo, testo[:400]


def test_il_default_del_codice_e_unknown(monkeypatch):
    """⚠️ MISURATO, non letto: la prosa si allinea al CODICE, quindi il codice va
    interrogato. Senza questa cella il presidio difenderebbe una frase, non un
    comportamento."""
    monkeypatch.delenv("ENGRAM_FLOW_SURFACE", raising=False)
    ambiente = flow_events._ambient()
    assert ambiente.get("surface") == "unknown", ambiente


def test_una_porta_dichiarata_vince_sul_default(monkeypatch):
    """⚠️ LA POPOLAZIONE OPPOSTA: un default onesto non deve diventare un campo
    che ignora chi si dichiara. Se questa cadesse, «unknown» ovunque sarebbe
    indistinguibile da «il campo non funziona»."""
    monkeypatch.setenv("ENGRAM_FLOW_SURFACE", "mcp")
    ambiente = flow_events._ambient()
    assert ambiente.get("surface") == "mcp", ambiente
