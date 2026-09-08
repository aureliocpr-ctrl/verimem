"""La ricevuta della porta MCP deve dire IN CIMA se il moat ha giudicato.

⚠️ IL DIFETTO (T26a), che si legge nel codice e non nel corpus.

Il server MCP gira delegate-only — `mcp_server.py` fa
``setdefault("HIPPO_ENCODE_DELEGATE_ONLY", "1")`` — quindi non carica MAI il
giudice nel proprio processo: o risponde il daemon condiviso, o
``try_local_score`` torna ``None`` (`local_grounding.py:934-940`, «daemon
assente o muto -> None»). Con il daemon muto, una scrittura CON FONTE entra
nello store **non giudicata**, e la ricevuta che torna al chiamante diceva::

    ok: true                                        <- 1a chiave
    grounding_score: null                           <- 7a
    moat: "could not judge — …"                     <- 8a, stringa lunga
    status: "model_claim"
    anti_confab_warnings: [{layer: "L4-skipped"}]   <- 13a

Nessun booleano. C'era l'ASSENZA di un valore e una stringa da leggere in
ottava posizione — e chi consuma questa porta è un agente, che legge
``ok: true`` e va avanti. È la forma già vista su questo prodotto: **una
misura che non c'è si legge come perfetta.**

📌 E IL CAMPO NON È UN'INVENZIONE DI QUESTO FILE: il journal lo deriva già.
``flow_events.py:346`` scrive ``judged=_gs is not None`` su ogni scrittura, e
il commento sopra dice che si DERIVA e non si accetta dal chiamante. Il
prodotto lo sapeva, lo registrava per sé, e non lo diceva a chi aveva appena
scritto — la stessa forma curata per ``quarantined_by``.

⚠️ LIMITE DICHIARATO, e va detto perché cambia cosa prova questo file: dalla
porta MCP **non risulta nessuna scrittura con fonte nello store** (misura del
07/09). Il difetto è provato dal CODICE e dall'A/B misurato alla porta, non da
una popolazione di fatti guasti.

⚠️ NESSUN MODELLO QUI: ``try_local_score`` è sostituita da una funzione che
torna ciò che tornerebbe il giudice — ``None`` per «muto», ``(punteggio,
soglia)`` per «ha risposto». È la stessa firma di
``local_grounding.try_local_score``: ``tuple[float, float | None] | None``.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from verimem import local_grounding
from verimem.client import Memory

FONTE = ("Verbale del 3 marzo: il magazzino centrale misura 4200 metri "
         "quadrati ed e' stato inventariato.")
FATTO = "Il magazzino centrale ha 4200 metri quadrati."


def _remember_mcp(args: dict) -> dict:
    from verimem import mcp_server as srv
    return json.loads(asyncio.run(srv.call_tool("hippo_remember", args))[0].text)


@pytest.fixture()
def porta(tmp_path, monkeypatch):
    """La porta MCP su uno store nuovo, con l'ambiente ai valori di default."""
    from verimem import mcp_server as srv

    m = Memory(str(tmp_path / "s.db"))

    class _Ag:
        def __init__(self):
            self.semantic = m.semantic

    monkeypatch.setattr(srv, "_ag", lambda: _Ag())
    # il write-time grounding e' acceso di default: un env ereditato che lo
    # spegnesse renderebbe verde la cella del giudice muto per il motivo
    # sbagliato.
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    return m


@pytest.fixture()
def giudice_muto(monkeypatch):
    """Delegate-only con il daemon che non risponde: `try_local_score` -> None."""
    monkeypatch.setattr(local_grounding, "try_local_score",
                        lambda *a, **k: None)


@pytest.fixture()
def giudice_che_risponde(monkeypatch):
    """Il daemon risponde: (punteggio, soglia), come il giudice vero."""
    monkeypatch.setattr(local_grounding, "try_local_score",
                        lambda *a, **k: (98.5, 60.0))


def test_il_banco_distingue_davvero_i_due_stati(porta, giudice_che_risponde):
    """CONTROLLO POSITIVO sullo strumento, non sul prodotto.

    Se col giudice che risponde la ricevuta NON portasse un punteggio, allora
    il mio finto giudice non e' agganciato al percorso vero, e la cella del
    giudice muto qui sotto sarebbe verde per il motivo sbagliato — misurerebbe
    un mock che non tocca niente. Questa deve restare verde perche' le altre
    significhino qualcosa.
    """
    r = _remember_mcp({"proposition": FATTO, "topic": "az/m", "source": FONTE})
    assert isinstance(r.get("grounding_score"), (int, float)), (
        f"il finto giudice non e' sul percorso del write: la ricevuta non "
        f"porta nessun punteggio ({r.get('grounding_score')!r}). "
        f"moat={r.get('moat')!r}"
    )


def test_col_giudice_muto_la_ricevuta_dichiara_di_NON_aver_giudicato(
        porta, giudice_muto):
    """IL CUORE: fonte data, giudizio assente, e la ricevuta lo dice."""
    r = _remember_mcp({"proposition": FATTO, "topic": "az/m", "source": FONTE})

    assert r.get("ok") is True, "la scrittura deve riuscire: si dichiara, non si rifiuta"
    assert r.get("judged") is False, (
        f"la ricevuta non dichiara che il moat NON ha giudicato questa "
        f"scrittura (judged={r.get('judged')!r}). Il fatto e' entrato nello "
        f"store con grounding_score={r.get('grounding_score')!r} e chi ha "
        f"scritto legge 'ok: true'."
    )


def test_col_giudice_muto_la_ricevuta_porta_un_avviso_leggibile(
        porta, giudice_muto):
    """E un avviso in chiaro, non una sigla da decifrare.

    L'avviso `L4-skipped` esiste gia' e arriva in `anti_confab_warnings` — ma
    e' la tredicesima chiave, ed e' una sigla. Questo campo dice il FATTO
    (il fatto e' entrato senza verdetto) e rimanda a `moat` per il perche',
    invece di ripetere la diagnosi in un secondo posto che puo' divergere.
    """
    r = _remember_mcp({"proposition": FATTO, "topic": "az/m", "source": FONTE})

    avviso = r.get("warning")
    assert isinstance(avviso, str) and avviso, (
        f"nessun avviso leggibile nella ricevuta: warning={avviso!r}"
    )
    assert "moat" in avviso, (
        f"l'avviso non manda a leggere il campo che porta il perche': {avviso!r}"
    )


def test_judged_sta_IN_CIMA_alla_ricevuta(porta, giudice_muto):
    """«in cima» e' il punto, non un dettaglio di stile.

    La diagnosi c'era gia' — in ottava e in tredicesima posizione, dentro
    stringhe lunghe. Se il campo finisse in fondo, questa cura non cambierebbe
    niente per chi legge: il difetto era proprio che l'informazione c'era e non
    si vedeva.
    """
    r = _remember_mcp({"proposition": FATTO, "topic": "az/m", "source": FONTE})
    chiavi = list(r)
    assert chiavi[:2] == ["ok", "judged"], (
        f"judged non e' la seconda chiave della ricevuta: {chiavi[:5]}"
    )


def test_una_scrittura_BOCCIATA_resta_giudicata(porta, monkeypatch):
    """⚠️ IL VERSO CHE FALSIFICA LA SCORCIATOIA, e va presidiato.

    Il prodotto ha gia' `judged_true(score)` — «il verdetto conta come: la
    fonte lo sostiene» — ed e' la funzione che viene in mente per riempire
    questo campo. Ma risponde a UN'ALTRA DOMANDA: torna False anche su una
    scrittura giudicata e BOCCIATA. Usarla qui farebbe dire alla ricevuta
    «non giudicato» proprio sulla scrittura che il moat ha esaminato e
    respinto — cioe' la ricevuta mentirebbe nel caso in cui la si legge di
    piu'.

    Se questa cella cade, qualcuno ha collegato `judged` alla soglia.
    """
    monkeypatch.setattr(local_grounding, "try_local_score",
                        lambda *a, **k: (3.0, 60.0))
    r = _remember_mcp({
        "proposition": "Il magazzino centrale ha 9999 metri quadrati.",
        "topic": "az/m", "source": FONTE})

    assert r.get("judged") is True, (
        f"una scrittura giudicata e bocciata risulta «non giudicata»: "
        f"judged={r.get('judged')!r} con grounding_score="
        f"{r.get('grounding_score')!r}. Il campo e' stato collegato alla "
        f"soglia (judged_true) invece che alla presenza del verdetto."
    )
    assert "warning" not in r, (
        f"avviso «non giudicato» su una scrittura giudicata: {r.get('warning')!r}"
    )


def test_una_scrittura_giudicata_non_cambia_forma(porta, giudice_che_risponde):
    """IL PRESIDIO: l'avviso compare SOLO dove c'e' qualcosa da avvisare.

    Stessa forma condizionale gia' usata da `quarantined_by` e
    `withheld_despite_judge` in questa ricevuta: una scrittura ordinaria non
    cambia forma, cosi' il campo nuovo non diventa rumore su ogni risposta.
    """
    r = _remember_mcp({"proposition": FATTO, "topic": "az/m", "source": FONTE})
    assert r.get("judged") is True, r.get("moat")
    assert "warning" not in r, (
        f"avviso su una scrittura regolarmente giudicata: {r.get('warning')!r}"
    )
