"""Lightweight recall + forward planning orchestrator.

FORGIA pezzo #248 — Wave 47. For each top-k recall result, also
build a forward trajectory starting from that skill. Less heavy
than full reason_about_task (no STRIPS, no analogy): faster,
smaller payload, ideal for hover/preview UI.
"""
from __future__ import annotations

import math
from typing import Any

from .momentum_macro import momentum_macro_candidate
from .reasoning import _appaia
from .successor_repr import build_transition_matrix, forward_plan


def recall_chain(
    *,
    task: str,
    agent: Any,
    k_recall: int = 3,
    forward_depth: int = 2,
    forward_beam: int = 3,
    n_episodes: int = 500,
) -> dict[str, Any]:
    """Recall + per-result forward trajectory.

    Returns: `{task, recalls: [{skill_id, name, score, forward_plans}],
    n_episodes_used, momentum}`. `momentum` (idea #3) flags the strongest
    forward chain worth fusing into a macro; has_candidate False when none.
    """
    skills_store = getattr(agent, "skills", None)
    memory = getattr(agent, "memory", None)

    # Recall. `_appaia` porta alla forma (skill, score) cio' che la superficie
    # restituisce: `SkillLibrary.retrieve` e' dichiarata `-> list[Skill]`
    # (skill.py:415) e da' oggetti NUDI, mentre la riga che segue spacchetta
    # coppie — ed e' FUORI dal try, quindi il `TypeError: cannot unpack
    # non-iterable Skill object` usciva dal tool. E' l'identico difetto gia'
    # curato in reasoning.py, dove l'audit di produzione lo misurava a 6
    # chiamate e 5 exception: la cura esisteva, applicata a un solo call site.
    # Qui non si vedeva perche' il test provava un doppio la cui `retrieve`
    # restituiva coppie — scritto sull'aspettativa del chiamante invece che
    # sul comportamento del fornitore — e perche' sulla lista vuota il ciclo
    # non gira, quindi uno store senza skill fa passare qualunque versione.
    recall_pairs: list[tuple[Any, float | None]] = []
    if skills_store is not None and hasattr(skills_store, "retrieve"):
        try:
            recall_pairs = _appaia(list(skills_store.retrieve(task, k=k_recall)))
        except Exception:
            recall_pairs = []

    # Build transition matrix once.
    sequences: list[list[str]] = []
    if memory is not None and hasattr(memory, "all"):
        try:
            for ep in memory.all(limit=n_episodes):
                seq = getattr(ep, "skills_used", None) or []
                if seq:
                    sequences.append(list(seq))
        except Exception:
            sequences = []
    ids, P = build_transition_matrix(sequences)

    recalls_out: list[dict[str, Any]] = []
    for sk, score in recall_pairs:
        plans: list[dict[str, Any]] = []
        if sk.id in ids:
            raw = forward_plan(
                sk.id, ids, P,
                depth=forward_depth, beam_width=forward_beam,
            )
            for path, lp in raw:
                plans.append({
                    "path": list(path),
                    "log_prob": float(lp),
                    "prob": float(math.exp(lp)),
                })
        recalls_out.append({
            "skill_id": sk.id,
            "name": sk.name,
            # None quando la superficie di richiamo non da' un punteggio (vedi
            # `_appaia`): «non misurato» non si legge come «misurato zero», ed
            # e' la seconda meta' della stessa cura — `float(None)` esplodeva
            # qui appena il primo TypeError smetteva di coprirlo.
            "score": None if score is None else float(score),
            "forward_plans": plans,
        })

    return {
        "task": task,
        "recalls": recalls_out,
        "n_episodes_used": len(sequences),
        # Atomic idea #3: the momentum decision — which recalled chain has crossed
        # the threshold to be worth fusing into one macro (hippo_compose_macro).
        # Always present; has_candidate False when no chain is probable enough.
        "momentum": momentum_macro_candidate(recalls_out),
    }


__all__ = ["recall_chain"]
