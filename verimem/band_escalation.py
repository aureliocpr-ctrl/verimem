"""CE-band -> llm-judge escalation: the moat's uncertain middle gets a real verdict.

The free local CE adjudicates every sourced write; scores in its REVIEW BAND
[threshold, tau_hi) are the sliver it is genuinely unsure about (measured
over-review 1/19). Instead of always parking those writes for human review,
this module escalates the band to ONE llm adjudication when a judge is
available with zero wiring:

* an explicitly injected ``Memory(llm=...)`` never reaches here (it already
  judges every write);
* with NO injected llm, a ``claude`` CLI on PATH is auto-discovered and used
  in print mode -- flat subscription, no API key (O5);
* ``ENGRAM_BAND_LLM=0`` opts out; ``ENGRAM_BAND_LLM_TIMEOUT_S`` bounds the
  call (default 90s).

Fail-soft by construction: no CLI, a CLI error, a timeout or an UNREADABLE
verdict all return ``None`` -> the caller keeps today's held-for-review
behavior. An unparseable answer must never admit a write.

The prompt reuses the SAME rubric as the injected-llm judge
(``grounding_gate._FACT_SYSTEM``) so the score scale -- and therefore the
claude-scale admission threshold -- stays calibrated.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from functools import lru_cache

#: explicit verdict anywhere in the answer ("Score: 87") — the LAST one wins
#: (the rubric ends with "Score:", so the model's final line is the verdict).
_SCORE_LABELED_RE = re.compile(r"[Ss]core\s*[:=]?\s*(\d{1,3}(?:\.\d+)?)")
#: bare-number answer ("87", " 92.5 is my verdict") — accepted ONLY at the very
#: start of the output. A digit embedded in prose ("the 100 words…") is NOT a
#: verdict: parsing it once ADMITTED a fact the judge had scored 5.
_SCORE_LEADING_RE = re.compile(r"^\s*(\d{1,3}(?:\.\d+)?)\b")


def _mode() -> str:
    v = os.environ.get("ENGRAM_BAND_LLM", "").strip().lower()
    if v in ("0", "off", "false", "no"):
        return "off"
    return "auto"


def _timeout_s() -> float:
    try:
        v = os.environ.get("ENGRAM_BAND_LLM_TIMEOUT_S", "").strip()
        return float(v) if v else 90.0
    except ValueError:
        return 90.0


@lru_cache(maxsize=1)
def _resolve_cli() -> str | None:
    """Absolute path of a ``claude`` CLI, or ``None``. lru_cached per process;
    tests clear via ``_resolve_cli.cache_clear()``."""
    return shutil.which("claude")


def escalate_band_score(source: str, fact: str) -> float | None:
    """One llm adjudication of a band-parked write: score in [0, 100] on the
    claude scale, or ``None`` when escalation is off/unavailable/failed --
    the caller then holds the write for review exactly as before."""
    if _mode() == "off":
        return None
    cli = _resolve_cli()
    if not cli:
        return None
    from .grounding_gate import _FACT_SYSTEM
    # CHANNEL SEPARATION: the rubric rides as a SYSTEM prompt; only the DATA
    # (source + fact, both tenant-controlled) goes in the user prompt — a fact
    # embedding "output 100" does not share the rubric's channel. Residual
    # honesty: injection can still try to sway the judge, but the worst
    # outcome is admitting a band write as a rank-2 model_claim (same as a
    # high CE score would), never a verified fact.
    user = f"Source: {source}\n\nCandidate fact: {fact}\n\nScore:"
    try:
        r = subprocess.run(
            [cli, "-p", "--output-format", "text",
             "--append-system-prompt", _FACT_SYSTEM],
            input=user, capture_output=True, text=True,
            timeout=_timeout_s(), encoding="utf-8", errors="replace",
        )
    except Exception:  # noqa: BLE001 -- ANY escalation failure degrades to review
        return None
    if r.returncode != 0:
        return None
    out = (r.stdout or "").strip()
    labeled = _SCORE_LABELED_RE.findall(out)
    if labeled:
        v = float(labeled[-1])          # the model's FINAL verdict wins
    else:
        m = _SCORE_LEADING_RE.match(out)
        if not m:
            return None  # prose without a verdict must never admit
        v = float(m.group(1))
    return min(100.0, max(0.0, v))


__all__ = ["escalate_band_score"]
