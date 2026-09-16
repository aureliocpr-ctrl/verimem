"""README:616-617 — «Per-user scoped ops (`user_id`/`agent_id`/`run_id`) stay
local for isolation».

IL CLAIM, testuale dal README pubblicato:

    Per-user scoped ops (`user_id`/`agent_id`/`run_id`) stay local for isolation.

E' VERO, e il prodotto fa la cosa giusta su tutte e tre le chiavi
(`mcp_server.py:7863`):

    _scoped_w = any(arguments.get(_s) is not None
                    for _s in ("user_id", "agent_id", "run_id"))
    _rm = _remote() if not _scoped_w else None

E la ragione, che il prodotto scrive due righe piu' su, e' di SICUREZZA: una
scrittura con uno scope delegata all'`add` non-scoped del server condiviso
finirebbe nel corpus senza il prefisso del tenant, e «any unscoped read from
another session would return it (**cross-tenant leak**)».

PERCHE' QUESTO FILE, SE IL PRODOTTO E' SANO.

`tests/test_mcp_thin.py` presidia gia' la promessa, e la presidia BENE — asserisce
l'effetto (`spy.searched == []`, `spy.added == []`) e non il messaggio:

    :131  test_scoped_recall_does_not_delegate_to_server
    :144  test_scoped_remember_does_not_delegate_to_server

Ma **tutti e due passano solo `user_id`**. `agent_id` e `run_id` non compaiono in
nessuna asserzione dell'albero. Quindi:

⇒ **si riduce quella tupla a `("user_id",)` — un refactoring, una svista, un
merge — e i due test restano VERDI mentre una scrittura con `agent_id` o `run_id`
finisce nel corpus condiviso senza prefisso.** E' esattamente il cross-tenant leak
che quel docstring dichiara di prevenire, non intercettato dal test che lo dichiara.

⚠️ **LA FORMA, ed e' la terza volta in due giorni**: *la promessa nomina N cose, il
presidio ne prova UNA.* README:505-506 nominava due vie di consenso su tre; la
tabella GDPR (745-751) ne elenca cinque su sette; qui sono tre chiavi provate con
una. Un presidio che copre il primo membro di un elenco da' la stessa sensazione di
sicurezza di uno che li copre tutti, e costa un terzo.

⚠️ **ZERO COPIE**: `_invoke_tool` e `_SpyRemote` sono importati da
`tests.test_mcp_thin`, non riscritti. Due spie della stessa cosa divergono, e in
questa casa e' la classe che paghiamo di piu' (`_jaccard` in 18 moduli). `tests/` e'
un pacchetto e l'albero lo fa gia' (`from tests.causal_fixture_helper import …`).

ws7 «Iris», 10/09/2026. Misurato con:
`python -m pytest tests/test_lo_scope_tiene_le_TRE_chiavi_fuori_dal_server.py -q -p no:randomly`
"""
from __future__ import annotations

import json

import pytest

# Riuso, non copia: gli helper stanno nel file di ws2 e restano UNA superficie.
from tests.test_mcp_thin import _HIT, _invoke_tool, _SpyRemote  # noqa: E402
from verimem import mcp_server

#: Le tre chiavi che il README nomina, una per una.
SCOPE = ("user_id", "agent_id", "run_id")


# ── IL CONTROLLO POSITIVO PER PRIMO ─────────────────────────────────────────


def test_CONTROLLO_il_prodotto_dichiara_ancora_le_TRE_chiavi():
    """Se il prodotto ne nominasse due, i test sotto proverebbero una promessa
    che il README fa e il codice non fa piu': meglio saperlo da qui.

    Legge la riga del prodotto, non la ripete: se `_scoped_w` cambia forma questo
    cade e chiede di guardare, invece di restare verde su un confronto morto.
    """
    sorgente = (mcp_server.__file__ or "")
    assert sorgente, "non trovo il file di mcp_server"
    testo = open(sorgente, encoding="utf-8").read()
    for chiave in SCOPE:
        assert f'"{chiave}"' in testo, (
            f"`{chiave}` non compare piu' in mcp_server.py: il README:616-617 la "
            "nomina fra le chiavi che tengono l'operazione locale."
        )


# ── LA PROMESSA, UNA CHIAVE PER VOLTA ───────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("chiave", SCOPE)
async def test_una_LETTURA_con_questo_scope_non_va_al_server(chiave, monkeypatch, tmp_data_dir):
    """README:616-617 — la lettura con scope resta locale, per OGNI chiave.

    Delegarla alla `search` non-scoped del server perderebbe il filtro di
    isolamento e servirebbe i fatti di un altro tenant.
    """
    spia = _SpyRemote([_HIT])
    monkeypatch.setattr(mcp_server, "_remote", lambda: spia)

    blocchi = await _invoke_tool("hippo_facts_recall",
                                 {"query": "q", "k": 5, chiave: "t1"})

    payload = json.loads(blocchi[0])
    assert payload.get("remote") is not True, (
        f"con `{chiave}` la lettura e' stata servita dal server condiviso"
    )
    assert spia.searched == [], (
        f"con `{chiave}` la lettura E' ARRIVATA al server ({spia.searched}): "
        "il filtro di isolamento e' stato perso per strada. README:616-617 "
        "promette che le operazioni con scope restano locali."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("chiave", SCOPE)
async def test_una_SCRITTURA_con_questo_scope_non_va_al_server(chiave, monkeypatch, tmp_data_dir):
    """README:616-617 — e la scrittura con scope, che e' il caso GRAVE.

    Il prodotto lo scrive da se' (`mcp_server.py:7857-7862`): una scrittura con
    scope delegata all'`add` non-scoped finirebbe nel corpus condiviso SENZA il
    prefisso del tenant, «readable by any unscoped recall from another session».
    """
    spia = _SpyRemote([])
    monkeypatch.setattr(mcp_server, "_remote", lambda: spia)

    blocchi = await _invoke_tool("hippo_remember",
                                 {"proposition": "una nota privata.",
                                  "topic": "note", chiave: "t1"})

    payload = json.loads(blocchi[0])
    assert payload.get("remote") is not True, (
        f"con `{chiave}` la scrittura e' stata delegata al server condiviso"
    )
    assert spia.added == [], (
        f"CROSS-TENANT LEAK con `{chiave}`: la scrittura e' arrivata al server "
        f"({spia.added}) e li' non ha il prefisso del tenant, quindi una lettura "
        "senza scope da un'altra sessione la restituisce. E' testualmente il "
        "difetto che `mcp_server.py:7857` dichiara di prevenire."
    )

# FALSIFICATO, non solo scritto. Difetto simulato per un minuto a
# `mcp_server.py:7864` — la tupla ridotta a `("user_id",)` — e i due presidi
# eseguiti sullo STESSO difetto:
#
#     tests/test_mcp_thin.py (14 test, il file che DICHIARA di prevenire il
#     cross-tenant leak nel proprio docstring)      EXIT=0   14 passed
#
#     questo file                                    EXIT=1   2 failed
#       test_una_SCRITTURA_..._non_va_al_server[agent_id]
#       test_una_SCRITTURA_..._non_va_al_server[run_id]
#       «con `agent_id` la scrittura e' stata delegata al server condiviso»
#
# Il leak e' avvenuto davvero e quattordici test non l'hanno visto. Si sono
# accese SOLO le scritture, che e' esattamente cio' che era stato rotto
# (`_scoped_w` sta nel ramo di `hippo_remember`): il righello discrimina.
#
# Senza il difetto: EXIT=0, 7 passed. `mcp_server.py` ripristinato con
# `git checkout --` e verificato identico al backup.
