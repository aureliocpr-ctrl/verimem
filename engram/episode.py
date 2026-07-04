"""Episode data structures.

Tulving's episodic memory: temporally-bound, particular, "what happened when".
Each Episode captures one task attempt with full ReAct trajectory and outcome.
"""
from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

Outcome = Literal["success", "failure", "partial"]


# Default decay half-life — 14 days at neutral strength. Tuned so a
# 60-day-old never-accessed episode lands ~0.014 retention (well below
# default 0.30 threshold) while a 2-day-old fresh one lands ~0.87.
_RETENTION_TAU_BASE_S = 14.0 * 86400.0

# Strength coefficients — how much each "this matters" signal multiplies
# the half-life. A episode with access_count=10 + salience=0.8 gets a
# strength of 1 + 3.0 + 0.8 = 4.8 — its 14-day base half-life stretches
# to ~67 days, which is what spaced-repetition theory predicts.
_RETENTION_GAMMA_ACCESS = 0.3
_RETENTION_DELTA_SALIENCE = 1.0


@dataclass
class Trace:
    """One step of a ReAct trajectory."""
    step: int
    thought: str
    action: str
    action_input: str
    observation: str


@dataclass
class Episode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_id: str = ""
    task_text: str = ""
    traces: list[Trace] = field(default_factory=list)
    outcome: Outcome = "failure"
    final_answer: str = ""
    tokens_used: int = 0
    skills_used: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    notes: str = ""
    critique: str = ""  # Reflexion-style self-critique on failure
    # FORGIA pezzo #6 — salience-weighted recall.
    # `last_accessed_at`/`access_count` track usage (Mattar-Daw 2018,
    # "need" component); `salience_score` caches the prediction-error
    # surprise relative to similar past episodes (Buzsáki 2015, "gain"
    # component). Defaults preserve v1 schema behaviour for fresh objects.
    last_accessed_at: float = 0.0
    access_count: int = 0
    salience_score: float = 0.5
    # FORGIA pezzo #14 — TCM contextual reinstatement (Howard & Kahana
    # 2002, Tulving 1973). Optional encoding-time context vector,
    # serialised float32. `None` = NULL column = neutral contribution
    # to context-weighted recall. Stored bytes match the
    # `summary_embedding` format (4 × CONFIG.embedding_dim).
    context_embedding: bytes | None = None
    # FORGIA pezzo #197 — pin protection. Pinned episodes are excluded
    # from decay-pruning candidates, regardless of Ebbinghaus retention.
    # The MCP tool `hippo_episode_pin` toggles this flag.
    pinned: bool = False

    def summary(self) -> str:
        """One-line summary used for embedding/recall."""
        return f"[{self.outcome}] {self.task_text} -> {self.final_answer[:120]}"

    def trajectory_text(self, max_chars_per_obs: int = 600) -> str:
        """Full trajectory as string for dream-mode replay."""
        lines = [f"TASK: {self.task_text}"]
        for t in self.traces:
            lines.append(f"--- step {t.step} ---")
            lines.append(f"Thought: {t.thought}")
            lines.append(f"Action: {t.action}({t.action_input[:300]})")
            obs = t.observation
            if len(obs) > max_chars_per_obs:
                obs = obs[:max_chars_per_obs] + " ...[truncated]"
            lines.append(f"Observation: {obs}")
        lines.append(f"OUTCOME: {self.outcome}")
        lines.append(f"FINAL_ANSWER: {self.final_answer[:400]}")
        if self.critique:
            lines.append(f"SELF_CRITIQUE: {self.critique}")
        return "\n".join(lines)

    @property
    def num_steps(self) -> int:
        return len(self.traces)

    def retention_strength(
        self, *,
        tau_base_s: float = _RETENTION_TAU_BASE_S,
        now: float | None = None,
    ) -> float:
        """Ebbinghaus-curve retention score — `R(t) = exp(-Δt / (τ × S))`.

        Three signals modulate the strength multiplier `S`:
          - **access_count**: spaced-repetition (Ebbinghaus 1885,
            Wozniak SuperMemo); episodes recalled often retain longer.
          - **salience_score**: prediction-error (Buzsáki 2015); surprises
            are encoded more deeply.
          - the implicit `1.0` base so a never-accessed neutral-salience
            episode still has half-life = τ_base, not zero.

        `Δt` is measured from the most recent of `created_at` and
        `last_accessed_at`. Recall (which bumps `last_accessed_at`)
        therefore RESETS the decay clock — that's the spaced-repetition
        invariant.

        Defensive: `tau_base_s = 0` returns 0.0 rather than raising.
        Used by the sleep cycle's decay-pruning stage.
        """
        if tau_base_s <= 0:
            return 0.0
        n = now if now is not None else time.time()
        last_significant = max(self.created_at, self.last_accessed_at)
        delta = max(0.0, n - last_significant)
        strength = (
            1.0
            + _RETENTION_GAMMA_ACCESS * float(self.access_count)
            + _RETENTION_DELTA_SALIENCE * float(self.salience_score)
        )
        return float(math.exp(-delta / (tau_base_s * strength)))
