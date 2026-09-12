"""T64 — la deny-list protegge solo MENTRE il server condiviso risponde.

Ticket T64, P0. Nasce come limite dichiarato del banco di T61, dove il
CONTROLLO POSITIVO cadde e disse la cosa che nessuno stava cercando:

    2026-09-10T20:19:02  audit_tool_call  outcome=ok  tool=hippo_fact_forget
    FAILED …::test_CONTROLLO_un_tool_GIA_nella_lista_viene_rifiutato
    2 failed, 1 passed in 10.28s     EXIT=1

Con `VERIMEM_SERVER_URL` puntata a una porta dove non ascolta nessuno,
`hippo_fact_forget` — che E' nella deny-list — NON e' stato rifiutato.

LA CATENA, letta nel codice (`verimem/mcp_server.py`):

    :181  def _remote():
              …
              if rm.health():  _remote_mem = rm
              else:            log.warning("… unreachable - MCP uses the local
                                            store")
              return _remote_mem          # <- None se il server non risponde

    :8109 if (name in _THIN_UNSUPPORTED_READS or
               name in _THIN_UNSUPPORTED_WRITES) and _remote() is not None:
              …rifiuta…

⇒ server giu' ⇒ `_remote()` e' `None` ⇒ la condizione e' falsa ⇒ **nessun
rifiuto**, e il tool agisce sullo store LOCALE. La lista che smette di
proteggere e' di 29 nomi (15 mutazioni + 14 letture), e il commento della lista
dice da se' perche' esiste:

    «Worse than a wrong read: they report an outcome ("removed", "merged",
     "superseded") after acting on the empty LOCAL store, so the caller
     believes the shared corpus changed when nothing did.»

PERCHE' E' P0 E NON P1. T49 era «un fatto fermato torna come vero»: grave, ma
il corpus resta uno. Qui il corpus **si sdoppia** — l'utente scrive in un posto
e legge da un altro — e il momento in cui succede e' **proprio quello in cui
nessuno guarda**: il server condiviso e' giu'. La protezione esiste solo
mentre la cosa da cui protegge non serve.

⚠️ QUESTO FILE NON E' STATO ESEGUITO DA CHI L'HA SCRITTO. E' un banco
consegnato con l'atteso dichiarato cella per cella, da eseguire a chi ha la
macchina. Ogni cella dice **cosa deve stampare** e **cosa significa se stampa
altro**: se l'esito non e' quello previsto, la lettura qui sopra e' sbagliata e
va riscritta, non aggirata.

⚠️ E IL BANCO MISURA LO STORE, NON SOLO LA RICEVUTA. «Il tool non e' stato
rifiutato» e «il tool ha cambiato qualcosa» sono due affermazioni diverse: la
prima e' la guardia assente, la seconda e' il danno. La prima senza la seconda
non basta a chiamarlo P0, ed e' precisamente il punto che a T61 era rimasto
NON MISURATO.

COME SI LANCIA:

    env -u HIPPO_ENCODE_DELEGATE_ONLY python -m pytest -q -p no:randomly \\
        tests/test_la_deny_list_protegge_solo_mentre_il_server_risponde.py

⛔ Store in tempdir, `assert_store_isolato` prima di scrivere. Nessun server
vero: si sostituisce `_remote`, perche' l'oggetto qui e' il GUARDIANO e non il
trasporto — un server vero in mezzo misurerebbe due cose insieme.
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


class _ServerVivo:
    """Un server condiviso che risponde: fa dire `True` a `_remote()`."""

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
    """`CONFIG` e' una frozen dataclass congelata a import-time: l'ambiente
    impostato dopo non la sposta."""
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
    """Uno store isolato con dentro DUE fatti veri da poter cancellare."""
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
        for i, testo in enumerate((
                "il tornello 42 e' aperto",
                "la serratura del deposito nord risulta forzata"), start=1):
            a.semantic.store(Fact(id=f"t64000000{i:04d}", proposition=testo,
                                  topic="banco/t64", status="model_claim"))
        yield {"agente": a, "ids": ["t640000000001", "t640000000002"]}
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
    """Il guardiano risponde con una frase che spiega il PERCHE', non un codice."""
    return "no shared-server path" in json.dumps(d, ensure_ascii=False,
                                                 default=str).lower()


def _vivo(agente, fid: str) -> bool:
    try:
        return agente.semantic.get(fid) is not None
    except Exception:
        return False


# ════════════════════ CELLA 1 — il controllo positivo ════════════════════
# ATTESO: PASSA, oggi e dopo la cura.
# SE CADE: il guardiano non funziona nemmeno col server vivo, e le due celle
#          sotto non misurano il fail-soft — misurano una guardia rotta sempre.
#          In quel caso T64 va riscritto: l'oggetto non e' piu' `_remote()`.

def test_CELLA1_col_server_VIVO_una_mutazione_della_lista_e_rifiutata(store, monkeypatch):
    """Il guardiano c'e' e si accende: e' la cella che da' senso alle altre due."""
    monkeypatch.setattr(mcp_server, "_remote", lambda: _ServerVivo())
    d = _chiama("hippo_fact_forget", {"fact_id": store["ids"][0]})
    assert _rifiutato(d), (
        "col server VIVO una mutazione della deny-list NON e' stata rifiutata: "
        "il guardiano non si accende mai e questo banco non puo' misurare il "
        f"fail-soft. payload={json.dumps(d, ensure_ascii=False, default=str)[:400]}")
    assert _vivo(store["agente"], store["ids"][0]), (
        "il tool e' stato rifiutato E ha cancellato lo stesso: il rifiuto "
        "arriva DOPO l'azione, che sarebbe un difetto diverso e peggiore.")


# ═══════════ CELLA 2 — il caso in esame: la guardia sparisce ═══════════
# ATTESO OGGI:  CADE (il tool non e' rifiutato)      -> il difetto c'e'
# ATTESO DOPO:  PASSA                                 -> la cura tiene
# SE PASSA OGGI: la lettura di `_remote()`/`:8109` e' sbagliata, T64 non esiste
#          nella forma descritta, e va riscritto il ticket — non il test.

def test_CELLA2_col_server_GIU_la_stessa_mutazione_NON_e_piu_rifiutata(store, monkeypatch):
    """Una variabile sola rispetto alla cella 1: la salute del server.

    `_remote()` rende `None` esattamente come quando `health()` fallisce.
    """
    monkeypatch.setattr(mcp_server, "_remote", lambda: None)
    d = _chiama("hippo_fact_forget", {"fact_id": store["ids"][0]})
    assert _rifiutato(d), (
        "col server GIU' la deny-list non protegge piu': `hippo_fact_forget` "
        "e' passato e ha agito sullo store LOCALE. La lista esiste per "
        "impedire che un tool «report an outcome after acting on the empty "
        "LOCAL store», e quando il server non risponde la protezione sparisce "
        "— cioe' proprio quando servirebbe. "
        f"payload={json.dumps(d, ensure_ascii=False, default=str)[:400]}")


# ════════ CELLA 3 — il DANNO, che e' un'altra affermazione ════════
# ATTESO OGGI:  CADE (il fatto e' sparito davvero)
# ATTESO DOPO:  PASSA
# SE CADE la 2 e PASSA la 3: la guardia manca ma il danno non avviene, e T64
#          scende di gravita' — resta un difetto, non un P0. E' la distinzione
#          che a T61 era rimasta NON MISURATA, ed e' la ragione di questa cella.

def test_CELLA3_col_server_GIU_la_mutazione_CAMBIA_davvero_lo_store(store, monkeypatch):
    """«Non rifiutato» e «ha fatto danno» sono due cose diverse: qui la seconda."""
    monkeypatch.setattr(mcp_server, "_remote", lambda: None)
    fid = store["ids"][1]
    assert _vivo(store["agente"], fid), "il fatto di prova non c'e': cella cieca"
    _chiama("hippo_fact_forget", {"fact_id": fid})
    assert _vivo(store["agente"], fid), (
        f"col server GIU' il fatto {fid} e' stato CANCELLATO dallo store "
        "locale da un tool che la deny-list avrebbe dovuto fermare. Non e' "
        "solo una guardia assente: e' il danno che quella guardia esiste per "
        "impedire, e l'utente riceve un «removed» mentre il corpus condiviso "
        "non e' cambiato.")
