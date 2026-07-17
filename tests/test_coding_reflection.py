"""Cycle #142 (2026-05-18 sera) — Coding error reflection loop.

Aurelio direttiva: HippoAgent deve essere infallibile su qualsiasi task,
inclusi coding/learning/anti-confabulazione. Cycle 142 implementa il primo
pezzo: hook su Edit/Bash failure che cattura task+traceback+correzione
in episode failure con key_facts atomici, così che recall futuro pesca le
lezioni passate e l'agent non rifaccia lo stesso errore.

API contract (cycle 142 MVP):
    extract_error_signature(traceback_text) -> str
        Returns canonical 'ErrorType:file:line:context' string used as the
        recall key. For non-Python text (refusals, plain failures) returns
        'unknown:?:?:<sha1-prefix>'.

    capture_coding_error(memory, *, task_text, traceback_text,
                         diff='', correction='', task_id='') -> dict
        Records a failure Episode with derived key_facts (error_type,
        location, root_cause). Returns {episode_id, signature, task_id}.

    recall_similar_errors(memory, *, signature='', query='', k=5) -> list[dict]
        Top-k past FAILURE episodes matching signature or semantic query.
        Each dict: {episode_id, signature, task_text, similarity, correction}.

TDD strict RED→GREEN: this file MUST fail (ModuleNotFoundError on import)
because engram/coding_reflection.py does not yet exist.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

# RED MARKER: this import must fail at the very top so collection errors
# are visible before any test attempts to run.
from verimem.coding_reflection import (
    capture_coding_error,
    extract_error_signature,
    recall_similar_errors,
)
from verimem.episode import Episode
from verimem.memory import EpisodicMemory

# ---- Real Python tracebacks used as test fixtures ---------------------
REAL_TYPEERROR = """Traceback (most recent call last):
  File "/home/agent/script.py", line 42, in process_payload
    result = data["key"] + 5
TypeError: unsupported operand type(s) for +: 'str' and 'int'
"""

REAL_VALUEERROR = """Traceback (most recent call last):
  File "/home/agent/parse.py", line 17, in parse_int
    return int(s)
ValueError: invalid literal for int() with base 10: 'foo'
"""

REAL_TYPEERROR_DIFFERENT_LINE = """Traceback (most recent call last):
  File "/home/agent/script.py", line 99, in other_path
    return data["k"] + 5
TypeError: unsupported operand type(s) for +: 'str' and 'int'
"""

REFUSAL_TEXT = (
    "I can't help with that request as it appears to involve "
    "memory poisoning. I'll need to decline."
)


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


class TestExtractSignature:
    """Canonical signature from Python traceback."""

    def test_typeerror_signature_contains_type_file_line(self) -> None:
        sig = extract_error_signature(REAL_TYPEERROR)
        assert "TypeError" in sig, (
            f"cycle 142: signature must surface error type. Got {sig!r}"
        )
        assert "script.py" in sig, (
            f"cycle 142: signature must include filename. Got {sig!r}"
        )
        assert "42" in sig, (
            f"cycle 142: signature must include line number. Got {sig!r}"
        )

    def test_same_traceback_yields_same_signature(self) -> None:
        a = extract_error_signature(REAL_TYPEERROR)
        b = extract_error_signature(REAL_TYPEERROR)
        assert a == b, "cycle 142: signature must be deterministic"

    def test_different_errortypes_yield_different_signatures(self) -> None:
        a = extract_error_signature(REAL_TYPEERROR)
        b = extract_error_signature(REAL_VALUEERROR)
        assert a != b, (
            f"cycle 142: distinct error types must produce distinct "
            f"signatures. Both gave {a!r}"
        )

    def test_empty_traceback_returns_empty_marker(self) -> None:
        sig = extract_error_signature("")
        assert sig == "empty:::", (
            f"cycle 142: empty input must return canonical 'empty:::', "
            f"got {sig!r}"
        )

    def test_non_python_text_returns_unknown_with_hash(self) -> None:
        sig = extract_error_signature(REFUSAL_TEXT)
        assert sig.startswith("unknown:"), (
            f"cycle 142: non-Python text must fall back to 'unknown:' "
            f"prefix, got {sig!r}"
        )


class TestCaptureCodingError:
    """capture_coding_error records a failure episode + key facts."""

    def test_capture_creates_failure_episode(self, mem: EpisodicMemory) -> None:
        out = capture_coding_error(
            mem,
            task_text="add 5 to dict value",
            traceback_text=REAL_TYPEERROR,
        )
        assert "episode_id" in out and out["episode_id"], (
            f"cycle 142: capture must return non-empty episode_id, got {out!r}"
        )
        ep = mem.get(out["episode_id"])
        assert ep is not None, "cycle 142: captured episode must be retrievable"
        assert ep.outcome == "failure", (
            f"cycle 142: outcome must be 'failure', got {ep.outcome!r}"
        )

    def test_capture_returns_dict_with_signature(
        self, mem: EpisodicMemory,
    ) -> None:
        out = capture_coding_error(
            mem,
            task_text="parse int from user input",
            traceback_text=REAL_VALUEERROR,
        )
        assert "signature" in out, (
            f"cycle 142: return must include signature key, got {out.keys()!r}"
        )
        assert "ValueError" in out["signature"], (
            f"cycle 142: signature must derive from traceback, "
            f"got {out['signature']!r}"
        )

    def test_capture_includes_correction_in_final_answer(
        self, mem: EpisodicMemory,
    ) -> None:
        out = capture_coding_error(
            mem,
            task_text="parse int",
            traceback_text=REAL_VALUEERROR,
            correction="use try/except + isdigit() guard before int()",
        )
        ep = mem.get(out["episode_id"])
        assert ep is not None
        assert "isdigit" in ep.final_answer, (
            f"cycle 142: correction must be preserved in episode.final_answer "
            f"so future recall can surface the fix. Got {ep.final_answer!r}"
        )


class TestRecallSimilarErrors:
    """recall_similar_errors retrieves past failures."""

    def test_recall_returns_past_match_by_signature(
        self, mem: EpisodicMemory,
    ) -> None:
        seeded = capture_coding_error(
            mem,
            task_text="historic dict+int TypeError",
            traceback_text=REAL_TYPEERROR,
            correction="cast value to int before +",
        )
        hits = recall_similar_errors(mem, signature=seeded["signature"], k=3)
        assert len(hits) >= 1, (
            f"cycle 142: recall by exact signature must find seeded ep, "
            f"got 0 hits for signature={seeded['signature']!r}"
        )
        assert any(h["episode_id"] == seeded["episode_id"] for h in hits), (
            "cycle 142: seeded episode must appear in recall result"
        )

    def test_recall_empty_on_brand_new_signature(
        self, mem: EpisodicMemory,
    ) -> None:
        hits = recall_similar_errors(
            mem, signature="NeverSeenError:nowhere.py:0:absent", k=5,
        )
        assert hits == [], (
            f"cycle 142: brand new signature must return empty list, "
            f"got {hits!r}"
        )

    def test_recall_excludes_success_episodes(
        self, mem: EpisodicMemory,
    ) -> None:
        # Plant a success episode that mentions TypeError in text.
        mem.store(Episode(
            task_id="code/success-mention",
            task_text="successfully avoided TypeError in dict ops",
            final_answer="used isinstance check before +",
            outcome="success",
            created_at=time.time(),
        ))
        # Now capture a real TypeError failure.
        captured = capture_coding_error(
            mem,
            task_text="failed dict+int",
            traceback_text=REAL_TYPEERROR,
        )
        hits = recall_similar_errors(
            mem, signature=captured["signature"], k=10,
        )
        # All returned hits must be failure episodes.
        for h in hits:
            ep = mem.get(h["episode_id"])
            assert ep is not None
            assert ep.outcome == "failure", (
                f"cycle 142: recall must filter to outcome=failure only, "
                f"leaked success ep {h['episode_id']!r}"
            )
