"""I dodici tool piu' chiamati devono stare nella matrice, non fuori.

PERCHE' QUESTI DODICI E NON ALTRI: misurato sul journal (W7-133), i 20 tool
classificati coprono il 38,1% delle chiamate reali; questi dodici ne coprono un
altro 10,6%. Classificare per FREQUENZA e non per elenco e' l'unica cosa che
sposta la copertura: con 32 tool su 249 si arriva al 48,7% del traffico vero.

LA CLASSIFICAZIONE NON E' A NASO — per ognuno la riga che la prova sta nella
cella W7-133. I due che erano rimasti aperti:
  * `hippo_contradictions_scan` = WRITE. `verimem/contradiction.py:625` dice
    «Run all detectors over the corpus and PERSIST new contradictions», e :637
    «INSERT OR IGNORE in ContradictionStore.add». Scrive.
  * `hippo_validate_claim` = READ. L'handler (mcp_server.py:12663-12673) chiama
    `validate_claim()` e ritorna; nel modulo (994 righe) le occorrenze di
    «write» sono TUTTE in commenti che parlano del «write path».
    ⚠️ limite dichiarato: «non ho trovato una scrittura» non e' «non c'e'».

⚠️ E TRE DI QUESTI DODICI STANNO NEL `GATING_BYPASS_LIST`, che salta il gate
senza lasciare traccia (`hippo_facts_list`, `hippo_facts_recent`,
`hippo_episode_list`). Classificarli NON li toglie dal bypass: rende esplicito
cio' che oggi e' deciso per esclusione da una seconda lista che nessuno aveva
contato — 28 voci, di cui 23 mai passate dal registro (W7-133).
"""
from __future__ import annotations

import pytest

from verimem.tool_registry import REGISTRY

#: i dodici, con la classificazione e la ragione in una parola.
ATTESI = {
    "hippo_recall_history": ("READ", False),
    "hippo_facts_list": ("READ", False),
    "hippo_trust_report": ("READ", False),
    "hippo_consolidate": ("WRITE", False),          # «Trigger a sleep cycle»
    "hippo_validate_claim": ("READ", False),
    "hippo_facts_recent": ("READ", False),
    "hippo_skill_retire": ("DESTRUCTIVE", True),    # «retire (archive) a skill»
    "hippo_search": ("READ", False),
    "hippo_contradictions_scan": ("WRITE", False),  # persist new contradictions
    "hippo_facts_find_conflicting": ("READ", False),
    "hippo_episode_list": ("READ", False),
    "hippo_contradictions_list": ("READ", False),
}


@pytest.mark.parametrize("nome", sorted(ATTESI))
def test_il_tool_e_nella_matrice(nome: str) -> None:
    assert nome in REGISTRY._caps, (
        f"{nome} e' fra i dodici tool piu' chiamati del journal e NON e' nella "
        f"matrice: in `enforce` sarebbe bloccato come sconosciuto, e in `warn` "
        f"riempie il log senza che nessuno sappia se e' READ o DESTRUCTIVE")


@pytest.mark.parametrize("nome", sorted(ATTESI))
def test_la_classificazione_e_quella_provata(nome: str) -> None:
    cap = REGISTRY._caps.get(nome)
    if cap is None:
        pytest.skip("coperto dal test sopra")
    atteso, confirm = ATTESI[nome]
    assert cap.capability == atteso, (
        f"{nome}: la matrice dice {cap.capability}, la lettura del codice dice "
        f"{atteso} (la riga che lo prova e' nel docstring di questo file)")
    assert cap.requires_confirm is confirm, (
        f"{nome}: requires_confirm={cap.requires_confirm}, atteso {confirm}")


def test_un_tool_irreversibile_chiede_conferma() -> None:
    """Il presidio che vale piu' della lista: un tool che distrugge SENZA
    ritorno deve chiedere conferma. Se domani qualcuno ne aggiunge uno senza,
    questo test lo ferma — la lista sopra invece invecchia in silenzio.

    ⚠️ LA PRIMA VERSIONE DI QUESTO TEST ERA TROPPO RIGIDA e il difetto era mio:
    chiedeva la conferma a OGNI DESTRUCTIVE, e ha trovato
    `hippo_fact_forget_with_undo` e `hippo_fact_supersede` — che pero' sono
    `reversibility="undoable"` (uno ha l'undo nel nome, l'altro versiona invece
    di cancellare). Avrei imposto attrito senza aggiungere sicurezza. La regola
    giusta usa il campo che esiste apposta, e con quella le violazioni sono
    zero: i tre irreversibili chiedono gia' tutti conferma."""
    senza = [c.name for c in REGISTRY._caps.values()
             if c.capability == "DESTRUCTIVE"
             and c.reversibility == "no" and not c.requires_confirm]
    assert not senza, (
        f"tool DESTRUCTIVE e IRREVERSIBILI senza requires_confirm: {senza}. "
        f"Da li' non si torna: o chiedono, o il gate in `enforce` non protegge")
