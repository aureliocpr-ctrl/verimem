"""Una fonte cancellata si DICHIARA, non sparisce.

L'opzione C, decisa insieme all'altra istanza dopo che ha falsificato la mia B.

Il fatto: la bonifica del 2026-07-30 ha rimosso 1735 episodi di telemetria, e
75 master fact su 75 sono rimasti con ``source_episodes`` che puntano a episodi
che non esistono piu'. Le tre vie possibili:

  (A) ricreare gli episodi-ancora  -> FABBRICA EVIDENZA: scrive record che
      dicono «questo lavoro e' avvenuto» quando non e' avvenuto. Scartata.
  (B) azzerare ``source_episodes`` -> l'altra istanza l'ha falsificata con un
      argomento che non avevo: gli id dangling SONO l'informazione. Azzerarli
      rende «la fonte c'era ed e' stata rimossa» indistinguibile da «non ha mai
      avuto una fonte». Scartata.
  (C) dirlo in lettura -> quello che fa questo file.

Oggi il camminatore del lineage restituisce l'id e basta; chi lo consuma non lo
risolve e lo lascia cadere — ``briefing_by_project`` lo dichiara pure nel
proprio commento: «silently dropped». Il risultato e' che una catena di
provenienza con un anello mancante e una catena senza quell'anello si leggono
uguali, e la differenza fra le due e' esattamente il genere di cosa che questo
prodotto esiste per non perdere.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def agente(tmp_path, monkeypatch):
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.agent import VerimemAgent
    return VerimemAgent.build()


def _fatto_con_fonte(agente, eid: str):
    from verimem.semantic import Fact
    f = Fact(id="f-dangling", proposition="Il server sta a Francoforte.",
             topic="infra", source_episodes=[eid])
    agente.semantic.store(f)
    return f


def test_un_episodio_che_non_esiste_piu_viene_DICHIARATO(agente):
    """Il cuore della C: la relazione dice che l'anello e' stato rimosso."""
    from verimem.lineage_trace import trace
    _fatto_con_fonte(agente, "ep-cancellato-123")
    r = trace("f-dangling", "fact", agente)
    relazioni = {e["relation"] for e in r["edges"]}
    assert any("removed" in rel for rel in relazioni), (
        f"l'anello mancante e' indistinguibile da uno vivo: {r['edges']}")


def test_anche_il_NODO_dice_che_non_c_e_piu(agente):
    """Chi legge i nodi (una vista, un grafo) non deve dover incrociare gli
    archi per sapere che quell'episodio non esiste."""
    from verimem.lineage_trace import trace
    _fatto_con_fonte(agente, "ep-cancellato-123")
    r = trace("f-dangling", "fact", agente)
    nodo = next((n for n in r["nodes"] if n["id"] == "ep-cancellato-123"), None)
    assert nodo is not None, r["nodes"]
    assert "removed" in (nodo.get("label") or "").lower(), nodo


def test_un_episodio_VIVO_resta_una_relazione_normale(agente):
    """La cura non deve marcare come rimosso cio' che c'e'."""
    from verimem.episode import Episode
    from verimem.lineage_trace import trace
    ep = Episode(task_text="un lavoro vero", final_answer="fatto",
                 outcome="success")
    agente.memory.store(ep)
    _fatto_con_fonte(agente, ep.id)
    r = trace("f-dangling", "fact", agente)
    relazioni = {e["relation"] for e in r["edges"]}
    assert "from_episode" in relazioni, r["edges"]
    assert not any("removed" in rel for rel in relazioni), (
        f"un episodio vivo e' stato dichiarato rimosso: {r['edges']}")


def test_l_id_resta_visibile(agente):
    """Non si perde l'id: e' l'informazione che B avrebbe cancellato, e serve
    a chi vuole cercarlo in un backup."""
    from verimem.lineage_trace import trace
    _fatto_con_fonte(agente, "ep-cancellato-123")
    r = trace("f-dangling", "fact", agente)
    assert any(n["id"] == "ep-cancellato-123" for n in r["nodes"]), r["nodes"]
