"""CLI avvisa, SDK avvisa, MCP taceva — e MCP è la porta che usa l'agente.

IL DIFETTO, isolato da ws4 con una frase che vale il referto: *«l'avviso
sotto-il-pavimento NON esce dalla porta MCP, cioè da quella dell'agente. Il
payload ha score 0.8387 ma non il pavimento 0.8608, quindi l'agente riceve il
punteggio senza il metro»*.

⚠️ E LA STESSA COSA VALEVA PER LA MIA CURA DI UN'ORA PRIMA. Avevo aggiunto
``trattenuti`` a ``Risultati`` (client.py) perché il silenzio di un fatto
quarantinato era indistinguibile dall'assenza. Verificato dopo::

    grep -rn "sotto_il_pavimento" verimem/ --include=*.py  ->  solo client.py

Nessuna superficie MCP leggeva quegli attributi. La mia cura girava e non
arrivava all'agente: è **esattamente la categoria (c) del censimento di ws4** —
«codice che gira e il cui effetto non raggiunge mai l'utente» — e l'avevo appena
creata io, un'ora dopo aver proposto a ws4 quella stessa categoria.

🔑 In una memoria PER AGENTI, MCP è la porta che conta di più: la CLI la usa un
umano che può leggere una riga in fondo, l'SDK lo usa chi ha scritto il codice e
sa cosa cercare. L'agente riceve un JSON e non va a cercare attributi che non
sono nel JSON.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def memoria(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    from verimem.client import Client
    return Client()


def test_l_avviso_esce_dalla_porta_dell_agente(memoria):
    """IL CUORE: l'agente che interroga la memoria deve sapere che sull'argomento
    c'era qualcosa e il gate l'ha trattenuto."""
    from verimem.mcp_server import _avvisi_di_lettura

    memoria.add("Ho implementato l'export del magazzino e funziona perfettamente.",
                topic="mag")

    class _Agent:            # ciò che la porta MCP ha in mano
        memory = memoria

    avvisi = _avvisi_di_lettura(_Agent(), "export del magazzino")
    assert avvisi.get("trattenuti"), "l'agente non riceve nessun avviso"
    assert avvisi["trattenuti"]["quanti"] >= 1


def test_CONTROLLO_POSITIVO_senza_trattenuti_il_payload_resta_pulito(memoria):
    """⚠️ LA POPOLAZIONE OPPOSTA: un avviso che compare sempre è rumore, e in un
    payload JSON il rumore costa contesto all'agente a ogni chiamata."""
    from verimem.mcp_server import _avvisi_di_lettura

    memoria.add("Il magazzino di Verona contiene 480 pallet.", topic="mag",
                source="Inventario: magazzino Verona, 480 pallet.")

    class _Agent:
        memory = memoria

    assert _avvisi_di_lettura(_Agent(), "magazzino di Verona") == {}


def test_NON_espone_il_testo_del_fatto_trattenuto(memoria):
    """⚠️ IL PRESIDIO. Portare l'avviso all'agente non deve diventare una porta
    di servizio per il contenuto: un fatto è in quarantena perché non ci si fida,
    e l'agente che lo leggesse nel payload lo userebbe come se fosse vero."""
    from verimem.mcp_server import _avvisi_di_lettura

    memoria.add("Ho implementato l'export del magazzino e funziona perfettamente.",
                topic="mag")

    class _Agent:
        memory = memoria

    assert "funziona perfettamente" not in str(
        _avvisi_di_lettura(_Agent(), "export del magazzino"))


def test_un_avviso_non_fa_cadere_la_risposta_dell_agente():
    """⚠️ Se il conteggio esplode, la porta MCP deve rispondere lo stesso: un
    avviso è un di più, la risposta è il contratto."""
    from verimem.mcp_server import _avvisi_di_lettura

    class _MemoriaRotta:
        def _trattenuti_safe(self, q):
            raise RuntimeError("database is locked")

    class _Agent:
        memory = _MemoriaRotta()

    assert _avvisi_di_lettura(_Agent(), "qualsiasi cosa") == {}


def test_un_agente_senza_memoria_non_rompe():
    """La porta MCP serve superfici diverse: alcune non hanno una `memory`."""
    from verimem.mcp_server import _avvisi_di_lettura

    class _Agent:
        pass

    assert _avvisi_di_lettura(_Agent(), "qualsiasi cosa") == {}
