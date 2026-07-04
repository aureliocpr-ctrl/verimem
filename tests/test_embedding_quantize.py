"""Cycle 207 (2026-05-23) — embedding_quantize tests.

RED marker: ``from engram.embedding_quantize import quantize_float16``
must fail on master.
"""
from __future__ import annotations

import numpy as np

# RED MARKER
from engram.embedding_quantize import (
    dequantize_float16,
    max_relative_error,
    quantize_float16,
)

_DIM = 384
_F32_BYTES = _DIM * 4
_F16_BYTES = _DIM * 2


def _make_f32_blob(seed: int = 0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.standard_normal(_DIM).astype(np.float32)
    # L2-normalise (typical sentence-transformers output shape).
    n = np.linalg.norm(arr)
    if n > 0:
        arr = arr / n
    return arr.tobytes()


class TestQuantize:
    def test_round_trip_preserves_shape(self) -> None:
        blob = _make_f32_blob(seed=1)
        q = quantize_float16(blob)
        assert len(q) == _F16_BYTES
        recovered = dequantize_float16(q)
        assert len(recovered) == _F32_BYTES

    def test_round_trip_low_error(self) -> None:
        """L2-normalised embeddings → < 1e-2 max relative error."""
        blob = _make_f32_blob(seed=2)
        recovered = dequantize_float16(quantize_float16(blob))
        err = max_relative_error(blob, recovered)
        assert err < 1e-2, f"round-trip error too high: {err}"

    def test_quantize_wrong_size_returns_unchanged(self) -> None:
        bad = b"\x00" * 100
        assert quantize_float16(bad) == bad

    def test_dequantize_wrong_size_returns_unchanged(self) -> None:
        bad = b"\x00" * 100
        assert dequantize_float16(bad) == bad

    def test_quantize_compression_ratio_2x(self) -> None:
        blob = _make_f32_blob(seed=3)
        q = quantize_float16(blob)
        assert len(q) == len(blob) // 2

    def test_quantize_non_bytes_input_returned_unchanged(self) -> None:
        # int input is not bytes-like; should be returned as-is rather
        # than crash.
        result = quantize_float16(42)  # type: ignore[arg-type]
        assert result == 42  # type: ignore[comparison-overlap]

    def test_max_relative_error_inf_on_size_mismatch(self) -> None:
        a = _make_f32_blob(seed=4)
        b = b"\x00" * 100
        assert max_relative_error(a, b) == float("inf")

    def test_zero_vector_round_trip(self) -> None:
        """All-zeros embedding edge case."""
        zeros = (np.zeros(_DIM, dtype=np.float32)).tobytes()
        recovered = dequantize_float16(quantize_float16(zeros))
        assert recovered == zeros

    def test_quantize_preserves_relative_ordering(self) -> None:
        """Cosine ordering between two random vectors should survive
        round-trip (the whole point of quantization for retrieval)."""
        q = _make_f32_blob(seed=5)
        d1 = _make_f32_blob(seed=6)
        d2 = _make_f32_blob(seed=7)
        q_arr = np.frombuffer(q, dtype=np.float32)
        d1_arr = np.frombuffer(d1, dtype=np.float32)
        d2_arr = np.frombuffer(d2, dtype=np.float32)
        s1_f32 = float(q_arr @ d1_arr)
        s2_f32 = float(q_arr @ d2_arr)

        d1_recovered = np.frombuffer(
            dequantize_float16(quantize_float16(d1)), dtype=np.float32,
        )
        d2_recovered = np.frombuffer(
            dequantize_float16(quantize_float16(d2)), dtype=np.float32,
        )
        s1_f16 = float(q_arr @ d1_recovered)
        s2_f16 = float(q_arr @ d2_recovered)

        # Same ordering: if d1 was closer in f32, it must still be
        # closer after f16 round-trip.
        assert (s1_f32 > s2_f32) == (s1_f16 > s2_f16)
