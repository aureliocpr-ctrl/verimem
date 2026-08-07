"""Il briefing di progetto serviva i quarantinati, contati come vivi.

ws2, sonda empirica su store isolato del 2026-08-07 — misurata, non
dedotta:

    add(vanto)          -> quarantined
    add(sano)           -> model_claim
    correct(sano→vanto) -> il nuovo esce QUARANTINED, il sano viene superseduto

    summary_topic('project/prova/*')
        n_total 4 · n_superseded 2 · **n_live 2**
        payload `facts`: ESATTAMENTE i due vanti quarantinati,
                         **nessun campo `status`**

⇒ I due fatti che il gate ha RESPINTO sono gli unici «fatti del progetto»
che il briefing serve, contati come vivi e indistinguibili da fatti sani.
E il tool si vende come «load the full cross-session context», consigliato
«when the user mentions a project by name»: è il canale con cui un claim
respinto rientra nel contesto di un agente come testo di progetto.

Due difetti distinti, e li tratto in modo diverso:

1. **`n_live = n_total - n_superseded`** è FALSO come nome, non come
   politica: un quarantinato non-superseduto non è vivo — è la lezione
   `superseded_by IS NULL ≠ vivo` che questo ramo ha già pagato una volta
   (il quartetto nasce da lì). Un contatore che smentisce il proprio nome
   si corregge, e la correzione non è una scelta di prodotto.
2. **Il payload senza `status`** si cura per addizione: chi legge deve
   poter distinguere. Additivo, non toglie niente a nessuno.

⛔ Quello che NON faccio è FILTRARE i quarantinati dal payload. Quella è
una decisione di prodotto — cambia cosa un agente riceve — e va misurata
su quanti briefing di produzione ne contengono oggi. Rendo visibile, non
decido: chi vuole tagliare ora ha il campo per farlo.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

_VANTO = "I have verified that the migration is complete and working."


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _prepara(m: Memory) -> str:
    sano = m.add("the depot holds 10 crates", topic="project/prova/a")["id"]
    cattivo = m.add(_VANTO, topic="project/prova/b")["id"]
    m.semantic.quarantine_fact(cattivo, reason="banco: premessa esplicita")
    return sano, cattivo


def test_n_live_non_conta_i_quarantinati(mem):
    """`superseded_by IS NULL` non vuol dire vivo: e' la lezione da cui
    nasce il quartetto, e questo contatore non l'aveva imparata."""
    _prepara(mem)
    out = mem.semantic.summary_topic("project/prova/*")

    assert out["n_total"] == 2
    assert out["n_live"] == 1, out


def test_il_payload_dice_lo_STATO_di_ogni_fatto(mem):
    """Senza `status` un claim respinto dal gate e uno ammesso sono la
    stessa riga per chi legge il briefing."""
    _, cattivo = _prepara(mem)
    out = mem.semantic.summary_topic("project/prova/*")

    per_id = {f["id"]: f for f in out["facts"]}
    assert cattivo in per_id, "il banco deve servire il quarantinato"
    assert per_id[cattivo]["status"] == "quarantined", per_id[cattivo]


def test_il_payload_porta_anche_il_VERDETTO(mem):
    """La promessa scritta nelle istruzioni del prodotto — «every read
    carries grounding_score» — vale anche qui: e' una lettura."""
    _prepara(mem)
    out = mem.semantic.summary_topic("project/prova/*")
    assert all("grounding_score" in f for f in out["facts"]), out["facts"][0]


def test_i_quarantinati_RESTANO_nel_payload_e_lo_dichiara(mem):
    """⛔ Non filtro: cambiare cosa un agente riceve e' una decisione di
    prodotto, e va misurata sui briefing veri. Il contratto qui e'
    «visibile», non «tolto» — e il risultato deve DIRLO, o chi legge
    penserebbe che il gate abbia gia' ripulito."""
    _, cattivo = _prepara(mem)
    out = mem.semantic.summary_topic("project/prova/*")

    assert cattivo in {f["id"] for f in out["facts"]}
    assert "quarantined" in out["counts_mean"].lower(), out.get("counts_mean")


def test_il_contatore_dichiara_la_sua_formula(mem):
    """Stessa regola del quartetto: un numero esce con la sua
    definizione, o il prossimo lo interpreta a modo suo."""
    _prepara(mem)
    out = mem.semantic.summary_topic("project/prova/*")
    assert "superseded" in out["counts_mean"] and "n_live" in out["counts_mean"]
