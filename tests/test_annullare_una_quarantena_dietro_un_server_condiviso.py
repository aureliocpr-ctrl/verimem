"""T61 — `hippo_quarantine_restore` muta i FATTI e non è nella deny-list.

Ticket assegnato dal controllore (RIPRESA 3, 19:58). Ramo `giano/t61`.
Data: 2026-09-10.

COSA DICE IL PRODOTTO DI SÉ, letto prima di eseguire (`mcp_server.py:260`):

    #: Fact-corpus MUTATIONS with no thin-tier delegation. Worse than a wrong
    #: read: they report an outcome ("removed", "merged", "superseded") after
    #: acting on the empty LOCAL store, so the caller believes the shared
    #: corpus changed when nothing did. A forget that silently forgets nothing
    #: is the most dangerous no-op here. Found by sweeping the mutating tools
    #: AFTER the first version of this guard covered only readers.

Quattordici tool sono in quella lista. Dietro un server condiviso il guardiano
(`:8109`) li RIFIUTA, con un messaggio che dice al chiamante perché.

`hippo_quarantine_restore` chiama `a.semantic.restore_fact(...)` — muta i
FATTI — e **non è nella lista**. Quindi, con `VERIMEM_SERVER_URL` impostata,
agisce sullo store LOCALE e risponde come se avesse ripristinato nel corpus
condiviso.

⚠️ PERCHÉ È PEGGIO DEGLI ALTRI QUATTORDICI, e non è retorica. Gli altri
mentono su un'operazione ordinaria («rimosso», «fuso»). Questo **annulla una
quarantena**: rimette nel recall di default un fatto che il gate aveva
fermato. Chi lo chiama sta facendo un'eccezione deliberata a una decisione di
sicurezza, e la porta gli dice che è riuscita quando non è successo niente —
oppure, sull'altro lato dello stesso equivoco, gliela fa riuscire **sul posto
sbagliato**. È l'esatto rovescio di T49: là un quarantenato tornava vero senza
che nessuno lo chiedesse, qui non torna vero anche se qualcuno l'ha chiesto.

⚠️ IL CONTROLLO POSITIVO È SIMMETRICO, e qui viene gratis: **la stessa
condizione, la stessa chiamata, un tool che È nella lista**. Se
`hippo_fact_forget` non venisse rifiutato, vorrebbe dire che il guardiano non
si accende affatto e il rosso sotto parlerebbe di quello, non della lista.
Una variabile sola fra i due casi: il nome del tool.

⚠️ E UN SECONDO CONTROLLO, perché «rifiutato» non basta: **senza** il server
condiviso la porta deve LAVORARE. Un tool che rifiuta sempre passerebbe il
primo controllo e sarebbe rotto in un altro modo.

⛔ PERIMETRO: store in tempdir, `assert_store_isolato` prima di scrivere.
Il server condiviso e' SIMULATO (vedi la nota su `_ServerFinto`): al banco non
serve un server vero, serve che il prodotto ne veda uno RAGGIUNGIBILE.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE))

import pytest  # noqa: E402

from verimem import mcp_server  # noqa: E402


#: ⚠️ NON BASTA impostare `VERIMEM_SERVER_URL`, e il primo giro me l'ha
#: insegnato facendo cadere il CONTROLLO POSITIVO: `_remote()` (`:181`) chiama
#: `rm.health()` e, se il server non risponde, logga «unreachable» e rende
#: `None` — cioe' **cade fail-soft sul locale**, e il guardiano della deny-list
#: non si accende affatto. Con una porta dove non ascolta nessuno, `hippo_
#: fact_forget` — che E' nella lista — passava tranquillo (`outcome=ok`).
#:
#: Quindi qui si simula un server RAGGIUNGIBILE, sostituendo `_remote`. Non e'
#: una scorciatoia: l'oggetto del banco e' il GUARDIANO della deny-list, non il
#: trasporto, e mettere in mezzo un server vero misurerebbe due cose insieme.
#:
#: 📌 E il comportamento che ho scoperto merita un ticket suo, perche' non e'
#: questo: se il server condiviso e' GIU', il prodotto serve dal locale in
#: silenzio — e allora TUTTE le quattordici mutazioni della deny-list tornano
#: ad agire sul locale, non solo quella di T61. La protezione esiste solo
#: mentre il server risponde. NON MISURATO qui: lo verifico a parte.
class _ServerFinto:
    """Un server condiviso che risponde. Serve solo a far dire `True` a
    `_remote()`: il banco non gli chiede altro."""

    def health(self) -> bool:
        return True


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
    from verimem.config import CONFIG
    for sotto in ("episodes", "skills", "semantic"):
        (radice / sotto).mkdir(parents=True, exist_ok=True)
    prima = {}
    for k, v in _campi(radice).items():
        prima[k] = getattr(CONFIG, k)
        object.__setattr__(CONFIG, k, v)
    return prima


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Uno store isolato con dentro un fatto QUARANTENATO da ripristinare."""
    from verimem.config import CONFIG
    from verimem.test_isolation import assert_store_isolato

    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR",
                 "ENGRAM_DIR"):
        monkeypatch.setenv(nome, str(tmp_path))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    monkeypatch.delenv("VERIMEM_SERVER_URL", raising=False)

    prima = _pinna(tmp_path)
    agente_di_prima = mcp_server._agent
    mcp_server._agent = None
    try:
        assert_store_isolato(CONFIG.semantic_db, tmp_root=tmp_path)
        a = mcp_server._ag()
        assert_store_isolato(getattr(a.semantic, "db_path", ""), tmp_root=tmp_path)

        from verimem.semantic import Fact
        a.semantic.store(Fact(id="quar000000001",
                              proposition="la serratura del deposito nord e' stata forzata",
                              topic="banco/t61", status="quarantined"))
        yield {"agente": a, "fact_id": "quar000000001"}
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


def _rifiutato(d: dict) -> bool:
    """Il guardiano risponde con `_err(...)`: si riconosce dalla frase che
    spiega al chiamante PERCHE', non da un codice."""
    testo = json.dumps(d, ensure_ascii=False, default=str).lower()
    return "no shared-server path" in testo


def test_CONTROLLO_senza_server_condiviso_il_ripristino_LAVORA(store):
    """Primo controllo: la porta non e' rotta di suo.

    Senza `VERIMEM_SERVER_URL` il ripristino deve agire sul locale — che qui e'
    lo store giusto — e togliere la quarantena davvero.
    """
    d = _chiama("hippo_quarantine_restore",
                {"fact_id": store["fact_id"], "reason": "banco t61"})
    assert not _rifiutato(d), f"rifiutato SENZA server condiviso: {d}"
    f = store["agente"].semantic.get(store["fact_id"])
    assert f is not None and getattr(f, "status", "") != "quarantined", (
        "il ripristino non ha tolto la quarantena sullo store locale: questo "
        f"banco non misura la delega. status={getattr(f, 'status', None)!r} "
        f"payload={d}")


def test_CONTROLLO_un_tool_GIA_nella_lista_viene_rifiutato(store, monkeypatch):
    """Secondo controllo, ed e' quello SIMMETRICO al caso in esame.

    Stessa condizione (server configurato), stessa porta, un tool che **e'**
    nella deny-list. Se non venisse rifiutato, il guardiano non si accende e il
    rosso sotto parlerebbe di lui, non della lista.
    """
    monkeypatch.setattr(mcp_server, "_remote", lambda: _ServerFinto())
    d = _chiama("hippo_fact_forget", {"fact_id": store["fact_id"]})
    assert _rifiutato(d), (
        "`hippo_fact_forget` E' nella deny-list e NON e' stato rifiutato: il "
        f"guardiano non si accende, e il caso sotto non misurerebbe niente. {d}")


def test_annullare_una_quarantena_dietro_un_server_condiviso_non_agisce_sul_locale(
        store, monkeypatch):
    """IL CASO IN ESAME.

    Con un server condiviso configurato, `hippo_quarantine_restore` deve
    rifiutare come i quattordici della lista. Oggi non rifiuta: agisce sullo
    store LOCALE e toglie la quarantena li', mentre nel corpus condiviso —
    quello da cui l'utente legge davvero — il fatto resta fermato.
    """
    monkeypatch.setattr(mcp_server, "_remote", lambda: _ServerFinto())

    d = _chiama("hippo_quarantine_restore",
                {"fact_id": store["fact_id"], "reason": "banco t61"})

    f = store["agente"].semantic.get(store["fact_id"])
    stato_locale = getattr(f, "status", None) if f is not None else None

    assert _rifiutato(d), (
        "`hippo_quarantine_restore` muta i FATTI (`a.semantic.restore_fact`) e "
        "dietro un server condiviso NON viene rifiutato: ha agito sullo store "
        f"locale (status ora = {stato_locale!r}) mentre il corpus condiviso non "
        "e' cambiato. E' la stessa classe dei quattordici di "
        "`_THIN_UNSUPPORTED_WRITES`, con un'aggravante: qui l'operazione che "
        "finisce nel posto sbagliato e' l'ANNULLAMENTO DI UNA QUARANTENA, "
        "cioe' un'eccezione deliberata a una decisione di sicurezza.\n"
        f"  payload: {json.dumps(d, ensure_ascii=False, default=str)[:400]}")
