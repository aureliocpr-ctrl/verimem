"""VeriBench — the public standard for trusted memory (#11). See README.md.

Scores what recall@k cannot see: abstention (knowing when you don't know) and
independent provenance (corroboration that survives copies/collusion). Everything
is deterministic, model-free, network-free.

Modules: ``scoring`` (NET λ-sweep core) · ``axes`` (ProbeItem + run_axis) ·
``runner`` (Verimem adapter) · ``competitors`` (mem0 adapter) · ``causal_axis``
(provenance ≠ causality, defended λ*) · ``adversarial_axis`` (collusion + sleeper
on the real SourceTrustBook — only the two-channel policy survives both).
"""
