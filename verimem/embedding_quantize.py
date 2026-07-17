"""Cycle 207 (2026-05-23) — float16 embedding quantization.

Closes gap §5.1 of docs/sota/embedding-compression.md (cycle 206).
Pure-numpy float32 ↔ float16 conversion of HippoAgent embedding
blobs.

Compression: 2× (1536 bytes f32 → 768 bytes f16 for 384-dim).
Expected recall loss: sub-1% (community wisdom, see cycle 206 §2).

Defensive
---------
* Empty / non-bytes / wrong-size input → returned unchanged.
* Quantize then dequantize round-trip preserves the 16-bit
  precision values (max relative error ~1e-3 for typical
  L2-normalised embeddings).
"""
from __future__ import annotations

import numpy as np

#: Expected dim of the active sentence-transformers model.
_EXPECTED_DIM: int = 384
_F32_BYTES: int = _EXPECTED_DIM * 4   # 1536
_F16_BYTES: int = _EXPECTED_DIM * 2   # 768


def quantize_float16(embedding_f32_blob: bytes) -> bytes:
    """Convert a float32 embedding blob to float16.

    Args:
        embedding_f32_blob: bytes of length ``_F32_BYTES`` containing
            a flat float32 array of shape (384,).

    Returns:
        bytes of length ``_F16_BYTES`` with the same values rounded
        to float16. Returns the input unchanged if size mismatches.
    """
    if not isinstance(embedding_f32_blob, (bytes, bytearray, memoryview)):
        return embedding_f32_blob  # type: ignore[return-value]
    if len(embedding_f32_blob) != _F32_BYTES:
        return bytes(embedding_f32_blob)
    arr32 = np.frombuffer(embedding_f32_blob, dtype=np.float32)
    arr16 = arr32.astype(np.float16)
    return arr16.tobytes()


def dequantize_float16(embedding_f16_blob: bytes) -> bytes:
    """Reverse of ``quantize_float16``. Returns a float32 blob.

    Args:
        embedding_f16_blob: bytes of length ``_F16_BYTES`` (768) for
            384-dim float16 array.

    Returns:
        bytes of length ``_F32_BYTES`` (1536) with values cast to
        float32. Returns the input unchanged if size mismatches.
    """
    if not isinstance(embedding_f16_blob, (bytes, bytearray, memoryview)):
        return embedding_f16_blob  # type: ignore[return-value]
    if len(embedding_f16_blob) != _F16_BYTES:
        return bytes(embedding_f16_blob)
    arr16 = np.frombuffer(embedding_f16_blob, dtype=np.float16)
    arr32 = arr16.astype(np.float32)
    return arr32.tobytes()


def max_relative_error(
    original_f32: bytes, recovered_f32: bytes,
) -> float:
    """Helper for tests: compute max relative error after round-trip.

    Returns ``inf`` on shape / size mismatch so test failures are
    obvious rather than silently zero.
    """
    if (
        len(original_f32) != _F32_BYTES
        or len(recovered_f32) != _F32_BYTES
    ):
        return float("inf")
    a = np.frombuffer(original_f32, dtype=np.float32)
    b = np.frombuffer(recovered_f32, dtype=np.float32)
    denom = np.abs(a)
    denom[denom < 1e-9] = 1e-9
    rel = np.abs(a - b) / denom
    return float(rel.max())


__all__ = [
    "quantize_float16",
    "dequantize_float16",
    "max_relative_error",
]
