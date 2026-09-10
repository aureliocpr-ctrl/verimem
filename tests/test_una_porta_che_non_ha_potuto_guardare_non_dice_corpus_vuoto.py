"""Se lo store non risponde, la porta dice «vuoto» o dice «non ho potuto guardare»?

Rilievo di ws6 nella revisione della PR #17, e l'ha detto meglio di come
l'avevo scritto io nel docstring della funzione:

    «in `_fatti_per_il_recupero` i due `except Exception` rendono `([], 0)`.
     Il primo trasforma un errore in "il corpus e' vuoto", che e' esattamente
     l'incidente del CYCLE #10 raccontato nel docstring di `list_facts`»

E il docstring di `SemanticMemory.list_facts` racconta proprio quello:

    «mcp_server.py called a.semantic.list_facts(...) in 28 places, but the
     method did not exist -> AttributeError -> caught by bare
     `except Exception: pass` -> 28 MCP tools silently returned facts=[]»

⇒ Ventotto porte hanno detto «non so niente» per mesi mentre il corpus era
pieno. La cura di allora fu far esistere il metodo; il ripiego muto che
l'aveva nascosto e' ancora la forma che usiamo, e io l'ho appena rimesso in
una funzione NUOVA — dichiarandolo nel docstring, che e' meglio di niente e
non basta: **un limite dichiarato lo paga chi legge il payload, non chi ha
scritto il commento.**

LA DIFFERENZA CHE QUESTO FILE MISURA, e non e' filosofica:

    «il corpus e' vuoto»        -> l'agente conclude che non esiste memoria e
                                   procede: risponde senza sapere.
    «non ho potuto guardare»    -> l'agente sa di essere cieco e puo' fermarsi,
                                   riprovare, o dirlo all'utente.

Sono due risposte diverse alla stessa domanda, e oggi la porta ne da' una
sola. Il campo si chiama `scan_error`, nome concordato con ws6: lo useremo
IDENTICO sulle due PR — chiamarlo in due modi vorrebbe dire curare il
silenzio e introdurre la divergenza, che e' la classe che stiamo togliendo.

⚠️ IL CONTROLLO POSITIVO E' SIMMETRICO: la stessa porta, la stessa chiamata,
lo store SANO — deve rendere i fatti e **non** avere `scan_error`. Senza,
«c'e' scan_error quando lo store cade» sarebbe verde anche su una porta che
lo mette sempre, e avrei sostituito un difetto con un altro.

⛔ PERIMETRO: store in tempdir, `assert_store_isolato` prima di scrivere.
Il guasto e' SIMULATO sostituendo `list_facts` sull'oggetto dell'agente —
non si rompe niente sul disco.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE))

import pytest  # noqa: E402

from verimem import mcp_server  # noqa: E402


def _campi(radice: Path) -> dict:
    return {
        "data_dir": radice,
        "episodes_db": radice / "episodes" / "episodes.db",
        "skills_dir": radice / "skills",
        "skills_db": radice / "skills" / "skills_index.db",
        "semantic_db": radice / "semantic" / "semantic.db",
        "runs_dir": radice / "runs",
        "reports_dir": radice / "reports",
    }


def _pinna(radice: Path) -> dict:
    """`CONFIG` e' una frozen dataclass congelata a import-time: l'ambiente
    impostato dopo non la sposta (misurato su T49, dove senza questo l'agente
    puntava allo store di casa)."""
    from verimem.config import CONFIG
    for sotto in ("episodes", "skills", "semantic"):
        (radice / sotto).mkdir(parents=True, exist_ok=True)
    prima = {}
    for k, v in _campi(radice).items():
        prima[k] = getattr(CONFIG, k)
        object.__setattr__(CONFIG, k, v)
    return prima


@pytest.fixture()
def porta(tmp_path, monkeypatch):
    """Un agente su uno store isolato, con dentro un fatto vero."""
    from verimem.config import CONFIG
    from verimem.test_isolation import assert_store_isolato

    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR",
                 "ENGRAM_DIR"):
        monkeypatch.setenv(nome, str(tmp_path))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")

    prima = _pinna(tmp_path)
    agente_di_prima = mcp_server._agent
    mcp_server._agent = None
    try:
        assert_store_isolato(CONFIG.semantic_db, tmp_root=tmp_path)
        a = mcp_server._ag()
        assert_store_isolato(getattr(a.semantic, "db_path", ""), tmp_root=tmp_path)

        from verimem.semantic import Fact
        a.semantic.store(Fact(id="sano00000001",
                              proposition="il tornello 42 e' aperto",
                              topic="banco/scan-error", status="model_claim"))
        yield a
    finally:
        mcp_server._agent = agente_di_prima
        for k, v in prima.items():
            object.__setattr__(CONFIG, k, v)


def _chiama(nome: str, argomenti: dict) -> dict:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call",
                          params=CallToolRequestParams(name=nome, arguments=argomenti))
    r = asyncio.run(handler(req))
    payload = r.root if hasattr(r, "root") else r
    testo = " ".join(c.text for c in payload.content if hasattr(c, "text"))
    try:
        return json.loads(testo)
    except Exception:
        return {"_grezzo": testo}


#: Il guasto: `list_facts` solleva, come faceva davvero nel CYCLE #10
#: (AttributeError perche' il metodo non esisteva).
def _rompi_lo_store(agente, monkeypatch):
    def esplode(*a, **k):
        raise RuntimeError("disco non leggibile (simulato dal banco)")
    monkeypatch.setattr(agente.semantic, "list_facts", esplode)


def test_CONTROLLO_con_lo_store_SANO_la_porta_rende_i_fatti_e_nessun_errore(porta):
    """Il controllo positivo, simmetrico al caso sotto: stessa porta, stessa
    chiamata, store che funziona. Se cade questo, il rosso sotto non parla del
    campo mancante — parla di una porta che non funziona affatto."""
    d = _chiama("hippo_oracle_query", {"query": "tornello 42", "top_k_each": 5})
    testo = json.dumps(d, ensure_ascii=False, default=str)
    assert "sano00000001" in testo, (
        f"la porta non rende il fatto che c'e': {testo[:400]}")
    assert not d.get("scan_error"), (
        "lo store e' sano e la porta dichiara un errore di scansione: il campo "
        f"c'e' sempre e non vuol dire niente. scan_error={d.get('scan_error')!r}")


def test_una_porta_che_non_ha_potuto_guardare_lo_DICE(porta, monkeypatch):
    """IL CASO IN ESAME. `list_facts` solleva, e la porta risponde comunque.

    Oggi risponde con zero fatti e nessuna spiegazione: chi legge non puo'
    distinguere «non c'e' niente in memoria» da «non sono riuscito a
    guardare». Sono due risposte diverse, e la seconda cambia cosa fa un
    agente.
    """
    _rompi_lo_store(porta, monkeypatch)
    d = _chiama("hippo_oracle_query", {"query": "tornello 42", "top_k_each": 5})

    assert isinstance(d, dict) and "_grezzo" not in d, (
        f"la porta non ha nemmeno risposto: {d}")
    assert d.get("scan_error"), (
        "lo store ha sollevato e la porta ha risposto come se il corpus fosse "
        "VUOTO: nessun `scan_error` nel payload. E' la forma del CYCLE #10 — "
        "28 tool che rendevano facts=[] in silenzio — in una funzione scritta "
        f"ieri. Payload: {json.dumps(d, ensure_ascii=False, default=str)[:400]}")


def test_anche_il_CONTEGGIO_dei_nascosti_dice_quando_non_sa(porta, monkeypatch):
    """Il SECONDO `except`, che e' piu' sottile e per questo ha il suo caso.

    Se la prima lettura riesce e la seconda (quella che conta quanti ne ha
    tolti) fallisce, oggi `nascosti` diventa **0** — cioe' «non ne ho nascosto
    nessuno», che e' un'AFFERMAZIONE, non un «non lo so». Un lettore che vede
    `hidden_low_trust: 0` conclude che il corpus non ha righe fermate dal
    gate; e' la stessa classe del `.get(status, 0)` che traduce «non lo so» in
    «vale poco» (`semantic.py`, `_rango_di_fiducia`).
    """
    vera = porta.semantic.list_facts
    chiamate = {"n": 0}

    def prima_ok_poi_esplode(*a, **k):
        chiamate["n"] += 1
        if chiamate["n"] == 1:
            return vera(*a, **k)
        raise RuntimeError("seconda lettura fallita (simulata dal banco)")

    monkeypatch.setattr(porta.semantic, "list_facts", prima_ok_poi_esplode)
    d = _chiama("hippo_oracle_query", {"query": "tornello 42", "top_k_each": 5})

    assert d.get("scan_error"), (
        "il conteggio dei nascosti e' fallito e il payload dice "
        f"`hidden_low_trust={d.get('hidden_low_trust')!r}` senza nessun "
        "avviso: «zero nascosti» e «non ho potuto contarli» arrivano al "
        "chiamante con la stessa faccia. Payload: "
        f"{json.dumps(d, ensure_ascii=False, default=str)[:400]}")
