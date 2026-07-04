"""R2.1: Extract causal signal from success/failure trajectory pair.

Given a successful and a failed trajectory of similar tasks, find:
  - cause: what the failure DID that the success did NOT
  - alternative: what the success DID instead
  - divergence_step: where the paths split
  - evidence: ids of both trajectories
"""
from __future__ import annotations


def _s(idx, kind, content, **kw):
    from engram.trajectory import TrajectoryStep
    return TrajectoryStep(step_idx=idx, kind=kind, content=content, **kw)


def test_extract_identifies_divergence():
    from engram.causal_extract import causal_extract

    failure = [
        _s(0, "thought", "start recon"),
        _s(1, "action", "aggressive nmap", tool_name="nmap"),
        _s(2, "observation", "WAF banned IP"),
    ]
    success = [
        _s(0, "thought", "start recon"),
        _s(1, "action", "passive crtsh", tool_name="crtsh"),
        _s(2, "observation", "subdomain found"),
    ]
    out = causal_extract(
        success_traj=success, failure_traj=failure,
        success_id="ep_succ", failure_id="ep_fail",
    )
    assert out["divergence_step"] == 1
    assert "nmap" in out["cause"].lower() or "aggressive" in out["cause"].lower()
    assert "crtsh" in out["alternative"].lower() or "passive" in out["alternative"].lower()


def test_extract_no_divergence_when_identical():
    from engram.causal_extract import causal_extract

    same = [_s(0, "thought", "X"), _s(1, "action", "Y", tool_name="t")]
    out = causal_extract(
        success_traj=same, failure_traj=same,
        success_id="a", failure_id="b",
    )
    assert out["divergence_step"] is None
    assert out["cause"] == ""


def test_extract_includes_evidence():
    from engram.causal_extract import causal_extract

    out = causal_extract(
        success_traj=[_s(0, "action", "A", tool_name="ta")],
        failure_traj=[_s(0, "action", "B", tool_name="tb")],
        success_id="ep_succ_42",
        failure_id="ep_fail_42",
    )
    assert out["evidence"]["success_id"] == "ep_succ_42"
    assert out["evidence"]["failure_id"] == "ep_fail_42"


def test_extract_proposes_rule_when_tools_differ():
    """If tools differ at divergence, propose a rule based on tool names."""
    from engram.causal_extract import causal_extract

    out = causal_extract(
        success_traj=[_s(0, "action", "scan", tool_name="masscan")],
        failure_traj=[_s(0, "action", "scan", tool_name="nmap")],
        success_id="s",
        failure_id="f",
    )
    assert "rule" in out
    # Rule should mention both tools or at least the success tool
    assert "masscan" in out["rule"].lower() or "nmap" in out["rule"].lower()


def test_extract_handles_empty_trajectory():
    from engram.causal_extract import causal_extract

    out = causal_extract(
        success_traj=[], failure_traj=[_s(0, "thought", "X")],
        success_id="s", failure_id="f",
    )
    # Empty success vs non-empty failure: divergence at 0
    assert out["divergence_step"] == 0


def test_extract_full_payload_keys():
    from engram.causal_extract import causal_extract

    out = causal_extract(
        success_traj=[_s(0, "action", "A")],
        failure_traj=[_s(0, "action", "B")],
        success_id="s",
        failure_id="f",
    )
    for k in ("divergence_step", "cause", "alternative", "rule",
              "evidence", "confidence"):
        assert k in out


def test_extract_confidence_higher_when_clear_tool_diff():
    """Confidence should be higher when divergence is on tool_name."""
    from engram.causal_extract import causal_extract

    out_tool_diff = causal_extract(
        success_traj=[_s(0, "action", "x", tool_name="A")],
        failure_traj=[_s(0, "action", "x", tool_name="B")],
        success_id="s", failure_id="f",
    )
    out_content_only = causal_extract(
        success_traj=[_s(0, "thought", "X")],
        failure_traj=[_s(0, "thought", "Y")],
        success_id="s", failure_id="f",
    )
    assert out_tool_diff["confidence"] >= out_content_only["confidence"]
