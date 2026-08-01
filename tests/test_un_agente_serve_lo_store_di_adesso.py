"""Nessun test eredita l'agente MCP di un altro.

``mcp_server._agent`` e' una globale di processo, costruita una volta sola
(double-checked locking: due build concorrenti sulle stesse SQLite, al momento
del cold start, erano un difetto vero). In produzione e' giusto cosi' — un
processo, uno store, un agente.

Sotto pytest quella globale attraversa i test, e nessuna delle quattro fixture
di isolamento del conftest la toccava. Misurato il 2026-07-30 sulla suite
intera, seed 2069628213: **7 rossi su 8592**, e nessuno dei sette era rotto —
passano tutti isolatamente (26 passed). Le firme::

    AssertionError: build() ran 0x — _ag() is not locked
    error="'_A' object has no attribute 'memory'"   tool=hippo_record_episode
    AssertionError: {'error': 'store failed: AttributeError'}

L'ordine di esecuzione lo dice: subito prima di ``test_cold_start_warmup``
girava ``test_mcp_anti_confab_scan``, che installa un ``MagicMock`` come
agente. Chi arriva dopo se lo ritrova — un mock, o uno stub ``_A`` di un altro
file, o un agente vero puntato allo store di qualcun altro. Con l'ordine
casuale la vittima cambia a ogni seed, ed e' per questo che il gate su cui si
decide ogni commit non era riproducibile: la stessa suite, sullo stesso codice,
dava verde o rosso secondo il seme.

La cura sta nel conftest, accanto alle altre quattro (embedding, settings,
token di sessione, CONFIG): la globale si azzera fra un test e l'altro. Non e'
un rattoppo dei sette test — quelli non hanno niente che non va — ed e' per
questo che non e' scritta come `xfail` o come import ordinato a mano.

Nota su una strada SBAGLIATA presa e abbandonata: prima ho scritto qui un test
che pretendeva che ``_ag()`` seguisse la data dir dell'ambiente, ricostruendo
l'agente quando cambia. Sembra ragionevole e non lo e': ``SemanticMemory``
prende il path da ``CONFIG.semantic_db`` e CONFIG e' congelato all'import,
quindi ricostruire avrebbe dato lo stesso store — un test che pretende cio' che
il prodotto non promette, e una cura che avrebbe ricostruito l'agente a vuoto.
"""
from __future__ import annotations

from verimem import mcp_server


def test_un_test_parte_senza_agente_ereditato():
    """L'invariante, visto dal singolo test."""
    assert mcp_server._agent is None, (
        "questo test e' partito con un agente gia' in piedi, costruito o "
        "installato da un altro test: da qui in poi legge lo store di un altro")


def test_a_SPORCA_la_globale(monkeypatch):
    """Fa quello che fa una dozzina di file della suite: mette un doppio al
    posto dell'agente. Non usa monkeypatch apposta — il punto e' proprio cio'
    che resta quando NESSUNO ripristina."""
    class _Finto:
        semantic = None

    mcp_server._agent = _Finto()
    assert mcp_server._agent is not None


def test_a2_SPORCA_anche_la_funzione():
    """L'altra meta' del difetto, e quella che ha fatto il danno vero: non la
    globale `_agent` ma la FUNZIONE `_ag`. Tre file la sostituivano cosi', con
    assegnazione diretta e nessun ripristino, mentre una trentina di altri
    usavano monkeypatch."""
    mcp_server._ag = lambda: "doppio"
    assert mcp_server._ag() == "doppio"


def test_b2_la_funzione_torna_quella_vera():
    assert mcp_server._ag() != "doppio", (
        "`_ag` e' rimasta sostituita dal test precedente: da qui in poi ogni "
        "tool MCP di ogni test riceve quel doppio al posto dell'agente")
    assert callable(mcp_server._ag)


def test_nessun_file_di_test_assegna_ag_direttamente():
    """Cricchetto, non stile: `monkeypatch.setattr` ripristina, `mod._ag = ...`
    no. La differenza non si vede scrivendo il test — si vede mesi dopo, in un
    altro file, come un rosso che cambia vittima a ogni seme."""
    import re
    from pathlib import Path
    colpevoli = []
    schema = re.compile(r"^\s*(?:mcp_server|dash(?:board)?)\._ag\s*=")
    qui = Path(__file__).resolve()
    for f in qui.parent.glob("**/*.py"):
        if f == qui:
            continue  # QUESTO file sporca apposta, per provare che la rete regge
        for n, riga in enumerate(
                f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if schema.match(riga):
                colpevoli.append(f"{f.name}:{n}")
    assert not colpevoli, (
        "questi assegnano `_ag` senza ripristinarlo, e la sostituzione "
        "sopravvive al test:\n  " + "\n  ".join(colpevoli)
        + "\n\nUsa `monkeypatch.setattr(mcp_server, \"_ag\", ...)`.")


def test_b_NON_lo_eredita():
    """Gira dopo il precedente (ordine alfabetico dei nomi in questo file, e
    con pytest-randomly l'ordine cambia — se la cura mancasse, questo test
    fallirebbe in alcune esecuzioni e non in altre, che e' esattamente il
    difetto). Se la fixture non azzerasse la globale, qui arriverebbe `_Finto`
    e ogni chiamata a `_ag()` lo userebbe."""
    assert mcp_server._agent is None, (
        f"ereditato {type(mcp_server._agent).__name__} dal test precedente: "
        f"la globale non viene azzerata fra i test")
