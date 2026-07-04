"""Cycle #142 (2026-05-18 sera) — Coding error reflection loop.

Aurelio direttiva: HippoAgent deve essere infallibile su qualsiasi task —
non solo pentest, anche coding/learning/anti-confabulazione persistente.
Cycle 142 è il primo pezzo della copertura coding: registra ogni Edit/
Bash failure come episode con signature canonica + key_facts atomici,
così che il recall futuro pesca le lezioni passate e l'agent non rifaccia
lo stesso errore.

API surface (MVP):
    extract_error_signature(traceback_text)
        Canonical 'ErrorType:file:line:context_word' from Python traceback.
        Empty text → 'empty:::'. Non-Python text → 'unknown:?:?:<sha1[:8]>'.

    capture_coding_error(memory, *, task_text, traceback_text,
                         diff='', correction='', task_id='')
        Records a failure Episode. Final answer = traceback (+ optional
        '--- CORRECTION ---' block). Returns {episode_id, signature, task_id}.

    recall_similar_errors(memory, *, signature='', query='', k=5)
        Top-k past FAILURE episodes matching the signature (preferred)
        or a semantic query. Each item: {episode_id, signature,
        task_text, similarity, correction}.

Design note: ``capture_coding_error`` deliberately does NOT call
``hippo_dream_propose`` or any consolidation — it is the cheap write
path. Consolidation runs later via the existing Auto-Dream worker.
"""
from __future__ import annotations

import hashlib
import re
import time
from typing import TYPE_CHECKING

from .episode import Episode

if TYPE_CHECKING:
    from .memory import EpisodicMemory


# Last 'TypeError: msg', 'ValueError: msg', 'XxxException: msg', etc.
_ERR_LINE_RE = re.compile(
    r"^([A-Z]\w*(?:Error|Exception|Interrupt|Warning)): (.+)$",
    re.MULTILINE,
)

# Last 'File "path", line N' frame.
_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+)')

_CORRECTION_MARKER = "\n\n--- CORRECTION ---\n"


def extract_error_signature(traceback_text: str) -> str:
    """Canonical signature used as the recall key.

    Examples:
        TypeError stack at script.py:42 → 'TypeError:script.py:42:unsupported'
        '' → 'empty:::'
        free-form refusal → 'unknown:?:?:<sha1[:8]>'
    """
    if not traceback_text or not traceback_text.strip():
        return "empty:::"

    err_matches = _ERR_LINE_RE.findall(traceback_text)
    if err_matches:
        err_type, err_msg = err_matches[-1]
        frames = _FRAME_RE.findall(traceback_text)
        if frames:
            raw_path, line = frames[-1]
            # Basename only (Unix or Windows separators).
            fname = raw_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        else:
            fname, line = "?", "?"
        # First word of the message as a coarse semantic discriminator
        # — distinguishes e.g. 'unsupported operand …' vs 'invalid literal …'.
        first_word = err_msg.strip().split()[0] if err_msg.strip() else "?"
        # Strip punctuation to keep signature stable across phrasing.
        first_word = re.sub(r"[^\w]+", "", first_word)[:30] or "?"
        return f"{err_type}:{fname}:{line}:{first_word}"

    # Non-Python text — hash the content so identical refusals collide.
    h = hashlib.sha1(traceback_text.encode("utf-8")).hexdigest()[:8]
    return f"unknown:?:?:{h}"


def _extract_correction(final_answer: str) -> str:
    """Pull the correction block back out of an Episode.final_answer."""
    idx = final_answer.find(_CORRECTION_MARKER)
    if idx < 0:
        return ""
    return final_answer[idx + len(_CORRECTION_MARKER):].strip()


def capture_coding_error(
    memory: EpisodicMemory,
    *,
    task_text: str,
    traceback_text: str,
    diff: str = "",
    correction: str = "",
    task_id: str = "",
) -> dict:
    """Record a failure Episode for a coding error.

    Returns
    -------
    dict
        ``{episode_id, signature, task_id}``. The Episode itself is
        retrievable via ``memory.get(episode_id)``.
    """
    signature = extract_error_signature(traceback_text)

    # Compose final_answer: traceback first, then optional diff + correction.
    parts: list[str] = [traceback_text.rstrip()]
    if diff:
        parts.append(f"\n\n--- DIFF ---\n{diff.rstrip()}")
    if correction:
        parts.append(f"{_CORRECTION_MARKER}{correction.rstrip()}")
    final_answer = "".join(parts)

    # task_id namespace — default groups same-signature errors together.
    err_type = signature.split(":", 1)[0]
    final_task_id = task_id or f"coding/error/{err_type}"

    ep = Episode(
        task_id=final_task_id,
        task_text=task_text,
        final_answer=final_answer,
        outcome="failure",
        created_at=time.time(),
    )
    # ``EpisodicMemory.store`` returns None (or a bool when
    # ``return_replaced=True``) for backwards compat; the canonical id
    # lives on the Episode itself (default_factory=uuid4().hex).
    memory.store(ep)

    return {
        "episode_id": ep.id,
        "signature": signature,
        "task_id": final_task_id,
    }


def recall_similar_errors(
    memory: EpisodicMemory,
    *,
    signature: str = "",
    query: str = "",
    k: int = 5,
) -> list[dict]:
    """Top-k past FAILURE episodes matching signature or semantic query.

    Strategy:
      1. If ``signature`` is provided, prefer it as the recall query — the
         signature is a compact, content-rich string that the embedding
         model treats as a semantic fingerprint.
      2. Fall back to ``query`` (free text) if no signature.
      3. Filter to ``outcome_filter='failure'`` so a success episode that
         merely mentions an error type does NOT bubble up.

    Each result dict includes the recomputed signature of the matched
    Episode plus the correction block (if any) so the caller can act on
    the fix without a second round-trip.
    """
    q = signature or query
    if not q:
        return []

    # ``min_similarity=-1.0`` disables the cosine floor — a coding error
    # signature is a sparse non-natural string (e.g. ``TypeError:foo.py:
    # 42:unsupported``) whose embedding can score low against the
    # `[failure] task -> answer` summary even on a true match. We accept
    # all candidates and let the caller filter by their own threshold.
    results = memory.recall(
        q, k=k, outcome_filter="failure", min_similarity=-1.0,
    )
    out: list[dict] = []
    for ep, sim in results:
        ep_sig = extract_error_signature(ep.final_answer)
        out.append({
            "episode_id": ep.id,
            "signature": ep_sig,
            "task_text": ep.task_text,
            "similarity": float(sim),
            "correction": _extract_correction(ep.final_answer),
        })
    return out
