"""Working-memory pruning — one algorithm, two encodings.

The wake loop trims old tool observations once the running message list
exceeds the budget, so small models don't lose track of the original
task. Before this module the algorithm lived twice in `wake.py`:
once for native tool-use messages (Anthropic `tool_result` blocks +
OpenAI `tool` role) and once for ReAct text-mode messages (`Observation:`
lines). Both copies did the same three things:

  1. Walk the message list, identify pruning candidates.
  2. Skip the last `keep_tail` of them — recent context is sacred.
  3. Replace the rest with a placeholder until size ≤ budget.

What varied was *what counts as a candidate* and *how to substitute the
placeholder in place*. Both are tiny pure functions of one message —
exactly the right shape for strategy injection. The loop logic is the
same in both encodings; isolating it here makes that fact visible.

The functions in this module are pure (no logging, no metrics) so they
can be reused outside the wake loop — e.g. by a future replay tool that
wants to fit a long episode into a critic's context window. Logging stays
at the WakeAgent layer where the call site has the right context to
emit the right event name.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def estimate_size(messages: list[dict[str, Any]]) -> int:
    """Cheap char-count proxy for token usage.

    Walks every message's content, summing string lengths. Tool-result and
    tool-use blocks contribute the length of their textual content (or a
    small fixed cost when content is structured but not directly stringy).
    The system prompt + tool schemas are NOT counted — they're handed to
    the LLM separately and don't compete for the same budget.
    """
    total = 0
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            total += len(content)
            continue
        if isinstance(content, list):
            for blk in content:
                if isinstance(blk, dict):
                    if blk.get("type") == "tool_result":
                        c = blk.get("content")
                        total += len(c) if isinstance(c, str) else 200
                    else:
                        total += len(str(blk.get("text", blk)))
                else:
                    total += len(str(blk))
    return total


def prune_messages(
    messages: list[dict[str, Any]],
    *,
    budget: int,
    keep_tail: int,
    placeholder: str,
    is_candidate: Callable[[int, dict[str, Any]], bool],
    replace_in_place: Callable[[dict[str, Any], str], bool],
) -> tuple[list[dict[str, Any]], int]:
    """Generic working-memory pruner.

    `is_candidate(idx, msg)` flags a message as eligible for pruning
    (typically: it carries an old tool observation). Index 0 is always
    excluded — that's the original user task and the model needs it.

    `replace_in_place(msg, placeholder)` performs the substitution and
    returns True if the message actually changed (so callers can count
    real prunes, not idempotent passes).

    Returns `(messages, n_pruned)`. The list is mutated in place; we
    return it for fluency / explicit dataflow.

    Bails out immediately when already within budget — the common case
    on short trajectories. This is the only place the function consults
    `estimate_size`; the per-step recheck inside the loop is what gives
    the algorithm its early-exit behaviour.
    """
    if estimate_size(messages) <= budget:
        return messages, 0

    indices = [
        i for i, m in enumerate(messages)
        if i > 0 and is_candidate(i, m)
    ]
    # The last `keep_tail` candidates are sacrosanct — recent observations
    # are what the model is reasoning over right now.
    prunable = indices[:-keep_tail] if keep_tail else indices

    n_pruned = 0
    for i in prunable:
        if replace_in_place(messages[i], placeholder):
            n_pruned += 1
        if estimate_size(messages) <= budget:
            break

    return messages, n_pruned


# ----- Strategy implementations ------------------------------------------
#
# Each pair of (is_candidate, replace_in_place) is the entire variation
# between native tool-use and ReAct text mode. Two short pure functions
# each — anything more would mean we missed the abstraction.


def native_tool_is_candidate(_idx: int, m: dict[str, Any]) -> bool:
    """A message carries old tool output if it's:
      • role=tool (OpenAI / Ollama style — one tool message per call), OR
      • role=user with a content list containing tool_result blocks
        (Anthropic style — all tool results bundled in one user turn).
    """
    role = m.get("role")
    if role == "tool":
        return True
    if role == "user" and isinstance(m.get("content"), list):
        return any(
            isinstance(b, dict) and b.get("type") == "tool_result"
            for b in m["content"]
        )
    return False


def native_tool_replace(m: dict[str, Any], placeholder: str) -> bool:
    """Substitute the textual content of every tool_result inside `m`.

    Two shapes to handle, mirroring `native_tool_is_candidate`. Returns
    True iff at least one slot actually changed (idempotent passes
    return False so callers don't double-count).
    """
    if m.get("role") == "tool":
        if isinstance(m.get("content"), str) and m["content"] != placeholder:
            m["content"] = placeholder
            return True
        return False
    # role == user with tool_result blocks
    changed = False
    if isinstance(m.get("content"), list):
        for blk in m["content"]:
            if (
                isinstance(blk, dict)
                and blk.get("type") == "tool_result"
                and isinstance(blk.get("content"), str)
                and blk["content"] != placeholder
            ):
                blk["content"] = placeholder
                changed = True
    return changed


# ReAct text mode: the loop alternates assistant Thought/Action/ActionInput
# turns with user 'Observation: ...' messages. The candidate predicate
# matches the latter; the replace builds a placeholder observation
# preserving the trailing 'Continue.' anchor.

_REACT_OBSERVATION_PREFIX = "Observation:"


def react_obs_is_candidate(_idx: int, m: dict[str, Any]) -> bool:
    return (
        m.get("role") == "user"
        and isinstance(m.get("content"), str)
        and m["content"].startswith(_REACT_OBSERVATION_PREFIX)
    )


def react_obs_replace(m: dict[str, Any], placeholder: str) -> bool:
    new_content = f"Observation:\n{placeholder}\n\nContinue."
    if m["content"] != new_content:
        m["content"] = new_content
        return True
    return False


__all__ = [
    "estimate_size",
    "prune_messages",
    "native_tool_is_candidate",
    "native_tool_replace",
    "react_obs_is_candidate",
    "react_obs_replace",
]
