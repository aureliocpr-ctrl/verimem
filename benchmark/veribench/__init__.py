"""VeriBench — the public standard for trusted memory (#11).

v0 core: the SCORING function that makes a trust memory's defining property
(knowing when it doesn't know) visible. Axis probes plug in on top; the
competitor arms and a defended λ come once the seed's blockers clear
(docs/VERIBENCH_DESIGN_INPUTS.md §6). This package is blocker-free by design:
it scores OUR shipped behavior, deterministically, no model or network.
"""
