"""`max_depth` prometteva il cammino più lungo e faceva una BFS.

Il commento diceva «Max depth (longest path root->leaf)» e il codice era una
BFS con `if ch in visited: continue`: ogni nodo veniva fissato alla PRIMA
volta che lo si raggiungeva, cioè alla distanza MINIMA.

Il banco in una figura — A che arriva a D per due strade:

    A → B → C → D        (tre passi)
    A ─────────→ D       (un passo)

La BFS raggiunge D dalla scorciatoia e scrive 1. Il cammino più lungo è 3.

Reale ma latente: sul corpus di Aurelio i due valori coincidono a 3, perché la
gerarchia delle skill non ha ancora scorciatoie. Un numero giusto per fortuna
resta un numero che nessuno ha verificato — e questo file lo verifica.

Trovato dall'altra istanza.
"""
from __future__ import annotations

from verimem.skill import Skill
from verimem.skills_topology import skills_topology


def _sk(sid: str, parents: list[str] | None = None) -> Skill:
    return Skill(id=sid, name=sid, trigger="t", status="candidate",
                 parent_skills=parents or [])


def test_la_scorciatoia_non_accorcia_la_profondita():
    """Il caso in figura: A→B→C→D e A→D."""
    skills = [_sk("A"), _sk("B", ["A"]), _sk("C", ["B"]), _sk("D", ["C", "A"])]
    assert skills_topology(skills)["max_depth"] == 3, skills_topology(skills)


def test_una_catena_semplice_resta_quella_che_e():
    """Il caso che la BFS calcolava bene non deve muoversi."""
    skills = [_sk("A"), _sk("B", ["A"]), _sk("C", ["B"])]
    assert skills_topology(skills)["max_depth"] == 2


def test_un_nodo_solo_ha_profondita_zero():
    assert skills_topology([_sk("A")])["max_depth"] == 0


def test_due_rami_prende_il_piu_lungo():
    skills = [_sk("A"), _sk("B", ["A"]), _sk("C", ["B"]),
              _sk("X", ["A"])]
    assert skills_topology(skills)["max_depth"] == 2


def test_un_ciclo_non_fa_girare_per_sempre():
    """Il grafo delle skill dovrebbe essere aciclico, ma «dovrebbe» non è una
    garanzia, e la vecchia BFS dai cicli era protetta: la protezione non si
    perde cambiando algoritmo."""
    skills = [_sk("A", ["C"]), _sk("B", ["A"]), _sk("C", ["B"])]
    rep = skills_topology(skills)
    assert isinstance(rep["max_depth"], int), rep
