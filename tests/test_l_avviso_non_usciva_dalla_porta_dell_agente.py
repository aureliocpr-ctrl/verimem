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


# ── IL BUG CHE IL MIO STESSO BANCO NON PRENDEVA ─────────────────────────────
# ws4 l'ha isolato con un A/B: la prima versione dell'helper cercava
# `agent.memory` e basta. Ma `Memory` (il client) NON ha un attributo `memory`,
# e nell'agente MCP `a.memory` è la memoria EPISODICA — un'altra cosa. Quindi
# l'helper restituiva un dict vuoto SEMPRE, e l'agente continuava a non ricevere
# niente.
#
# ⚠️ E i miei test passavano lo stesso, perché costruivo un oggetto finto
# `class _Agent: memory = memoria` — cioè la forma che l'helper si aspettava,
# non quella che il prodotto passa davvero. **Il banco confermava la mia
# assunzione invece di misurarla.** Dodicesima volta oggi.

def test_l_avviso_esce_da_TUTTE_le_forme_di_oggetto_che_il_prodotto_passa(memoria):
    """⚠️ IL PRESIDIO CHE MANCAVA. L'helper riceve oggetti diversi a seconda
    della superficie, e una sola forma indovinata non basta: se sbaglia,
    restituisce silenzio — che è indistinguibile dal «non c'è niente»."""
    from verimem.mcp_server import _avvisi_di_lettura

    memoria.add("Ho implementato l'export del magazzino e funziona perfettamente.",
                topic="mag")

    forme = {
        "il client stesso": memoria,
        "oggetto con .memory": type("_A", (), {"memory": memoria})(),
        "oggetto con .semantic": type("_A", (), {"semantic": memoria.semantic})(),
    }
    for nome, ogg in forme.items():
        avvisi = _avvisi_di_lettura(ogg, "export del magazzino")
        assert avvisi.get("trattenuti"), f"silenzio con «{nome}»"


# ── IL SECONDO AVVISO: il metro accanto al punteggio ────────────────────────
# ws4: «l'agente riceve il punteggio senza il metro». ws1 ha poi misurato che la
# prima cura ne portava UNO SU DUE — `trattenuti` arrivava, `sotto_il_pavimento`
# no. Non era una svista: l'avevo lasciato fuori apposta, in attesa del numero di
# ws5 sul pavimento. Il numero è arrivato ed è un VINCOLO, non un via libera:
#     «NON innestarlo come TAGLIO: 7 valori su 11 stanno a 0.86+, dove la mia
#      curva perde risposte VERE. Come AVVISO va bene sempre.»
# Quindi entra come avviso — la stessa disciplina di `Risultati` nell'SDK, dove
# la nota dice testualmente «i risultati sono qui sotto, NON tagliati».

def test_l_agente_riceve_il_METRO_non_solo_il_punteggio(memoria):
    """IL CUORE: su una domanda la cui risposta non è in memoria, l'agente deve
    sapere che nessun risultato supera la soglia di rilevanza — altrimenti legge
    un punteggio senza sapere se è alto o basso PER QUESTO corpus."""
    from verimem.mcp_server import _avvisi_di_lettura

    memoria.add("Il magazzino di Verona contiene 480 pallet.", topic="m",
                source="Inventario: Verona 480 pallet.")
    memoria.add("La sede di Milano ha 120 dipendenti.", topic="m",
                source="Inventario: Milano 120 dipendenti.")

    avvisi = _avvisi_di_lettura(memoria, "qual e' il fatturato trimestrale")
    pav = avvisi.get("sotto_il_pavimento")
    assert pav, "l'agente riceve il punteggio senza il metro"
    assert "pavimento" in pav and "score_migliore" in pav


def test_CONTROLLO_POSITIVO_una_domanda_CON_risposta_non_riceve_l_avviso(memoria):
    """⚠️ LA POPOLAZIONE OPPOSTA, ed è quella che rende l'avviso utile: se
    comparisse anche quando la risposta c'è, l'agente imparerebbe a ignorarlo —
    e allora non servirebbe più quando conta."""
    from verimem.mcp_server import _avvisi_di_lettura

    memoria.add("Il magazzino di Verona contiene 480 pallet.", topic="m",
                source="Inventario: Verona 480 pallet.")
    memoria.add("La sede di Milano ha 120 dipendenti.", topic="m",
                source="Inventario: Milano 120 dipendenti.")

    avvisi = _avvisi_di_lettura(memoria, "magazzino di Verona pallet")
    assert "sotto_il_pavimento" not in avvisi


def test_i_due_avvisi_sono_INDIPENDENTI(memoria, monkeypatch):
    """⚠️ Se il conteggio dei trattenuti esplode, il metro deve arrivare lo
    stesso: due avvisi in un try solo cadono insieme, e un guasto in uno
    spegnerebbe silenziosamente anche l'altro."""
    from verimem.mcp_server import _avvisi_di_lettura

    memoria.add("Il magazzino di Verona contiene 480 pallet.", topic="m",
                source="Inventario: Verona 480 pallet.")
    memoria.add("La sede di Milano ha 120 dipendenti.", topic="m",
                source="Inventario: Milano 120 dipendenti.")

    def esplode(self, q):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(type(memoria), "_trattenuti_safe", esplode, raising=False)
    avvisi = _avvisi_di_lettura(memoria, "qual e' il fatturato trimestrale")
    assert avvisi.get("sotto_il_pavimento"), "un guasto nel primo ha spento il secondo"
