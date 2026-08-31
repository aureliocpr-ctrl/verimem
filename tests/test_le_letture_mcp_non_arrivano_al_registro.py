"""Il tag `surface=mcp` c'e', e sulle LETTURE non arriva mai.

MISURATO SUL REGISTRO VIVO il 2026-08-31 alle 03:21 — `events.jsonl` **piu' il
ruotato `.1`** (chi legge solo il primo misura la coda), 40007 righe::

    superficie, sui soli `flow.recall`      eventi
    unknown                                   2468   52,3%
    gateway                                   2199   46,6%
    cli                                         47    1,0%
    sdk                                          2    0,04%
    mcp                                          0    MAI

⇒ **Zero letture attribuite alla porta MCP**, mentre `mcp` etichetta **1373**
eventi complessivi: la superficie e' tracciata, ma non li'.

LETTO NEL SORGENTE, e le due cose insieme spiegano il perche':

* `mcp_server` imposta `ENGRAM_FLOW_SURFACE=mcp` come tag di PROCESSO, col
  commento *«every flow.* event emitted by the core … is tagged surface=mcp»*;
* `flow.recall` e' emesso **solo** da `Memory.search` / `Memory.explain`
  (`client.py:1248`, `:1914`);
* gli handler MCP di lettura chiamano `a.semantic` **direttamente** — il
  commento accanto a `hippo_facts_recall` lo dice a chiare lettere.

⇒ 🔑 **«by the core» e' la parola portante, e ESCLUDE le letture.** Il tag
funziona; le letture non passano mai dal punto che emette. Le SCRITTURE si',
ed e' per questo che 1373 eventi risultano `mcp`.

⚖️ PERCHE' QUESTO FILE NON CURA IL COMPORTAMENTO: agganciare un emit agli
handler di lettura **aggiunge righe a un registro su cui piu' persone stanno
misurando stanotte** — cambierebbe i loro denominatori. E' una decisione di
gruppo, non una correzione silenziosa. Qui si fissa cio' che il codice DICE, e
il commento nel sorgente rende la lacuna leggibile a chi arriva dopo.

⚠️ CONSEGUENZA CHE VALE PER IL CONTRATTO DI USCITA: **nessuna affermazione del
tipo «la maggior parte delle letture passa da X» e' sostenibile** con questo
registro — il 52,3% delle letture e' `unknown` e la porta MCP non c'e'.

Banco: ``docs/stato-reale/le-quattro-promesse-sulle-porte-degli-agenti.md``
"""

from __future__ import annotations

import inspect

from verimem import mcp_server


def test_il_commento_dice_che_il_tag_non_raggiunge_le_letture():
    """IL CUORE: prima, chi leggeva «every flow.* event … is tagged
    surface=mcp» concludeva che le letture MCP fossero tracciate."""
    sorgente = inspect.getsource(mcp_server)
    i = sorgente.find('ENGRAM_FLOW_SURFACE')
    assert i > 0, "il tag di processo non c'e' piu': rimisurare prima di fidarsi"
    intorno = sorgente[max(0, i - 1800):i + 400]
    assert "flow.recall" in intorno, intorno[-500:]
    assert "ZERO times" in intorno or "ZERO" in intorno, intorno[-500:]


def test_il_commento_dice_anche_PERCHE_le_scritture_invece_si_vedono():
    """⚠️ LA META' CHE TIENE ONESTA L'ALTRA: dire «il tag non arriva» senza
    dire che sulle SCRITTURE arriva fa concludere che il tag sia rotto. Non lo
    e': funziona dove l'evento passa dal core."""
    sorgente = inspect.getsource(mcp_server)
    i = sorgente.find('ENGRAM_FLOW_SURFACE')
    intorno = sorgente[max(0, i - 1800):i + 400]
    assert "1373" in intorno, intorno[-500:]


def test_gli_handler_di_lettura_non_emettono_ancora_flow_recall():
    """⚠️ PRESIDIA LA PREMESSA, non la cura. Se un giorno qualcuno agganciasse
    l'emit agli handler di lettura — cosa che va decisa in gruppo, perche'
    aggiunge righe a un registro su cui altri misurano — questo test diventa
    rosso e obbliga ad aggiornare il commento, invece di lasciarlo mentire.
    """
    sorgente = inspect.getsource(mcp_server)
    assert "_emit_flow" not in sorgente, (
        "mcp_server ora emette eventi di flusso: la lacuna descritta nel "
        "commento accanto a ENGRAM_FLOW_SURFACE potrebbe essere chiusa. "
        "Rimisurare il registro e aggiornare il commento.")
