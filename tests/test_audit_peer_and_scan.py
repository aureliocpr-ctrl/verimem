"""Two more findings from the independent red-team audit (F5, F8).

F5 — personal (no-key) mode authenticated on the client-controlled Host header
alone. `request.client.host`, the actual peer, was never inspected. A deployment
that binds non-loopback AND sets local_tenant therefore hands the local tenant
to any remote caller that simply sends `Host: localhost` — takeover with no key.

F8 — extract_dates() re-scanned the whole prefix (`re.findall` over
`t[:m.start()]`) for EVERY bare-month match, i.e. O(n*m). Propositions are not
length-capped on this path (`validate="full"` runs it on every write), so one
tenant could pin the shared gateway process.
"""
from __future__ import annotations

import time

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from verimem.gateway import GatewayKeys, create_app  # noqa: E402


def test_personal_mode_rejects_a_remote_peer_spoofing_the_host_header(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    app = create_app(data_dir=tmp_path / "gwdata", keys=keys, local_tenant="me")

    remote = TestClient(app, client=("203.0.113.5", 44321))   # a real network peer
    r = remote.get("/v1/stats", headers={"Host": "localhost"})
    assert r.status_code in (401, 403), (
        f"remote peer got in with a spoofed Host header: {r.status_code}")


def test_personal_mode_still_works_for_a_local_caller(tmp_path):
    keys = GatewayKeys(tmp_path / "keys.db")
    app = create_app(data_dir=tmp_path / "gwdata", keys=keys, local_tenant="me")
    local = TestClient(app, client=("127.0.0.1", 51000))
    assert local.get("/v1/stats", headers={"Host": "localhost"}).status_code == 200


def test_extract_dates_does_not_rescan_the_whole_prefix():
    """Quadratic before the fix: 40k bare-month matches each re-scanning an
    ever-longer prefix. The guard only ever needs the word immediately before
    the match, so a bounded window is enough."""
    from verimem.quantity_match import extract_dates
    # CAPITALIZED: a lowercase "may" short-circuits on the modal guard BEFORE
    # the prefix scan, so it never reaches the quadratic path (a first version
    # of this test used "may" and passed for that wrong reason).
    # Measured BEFORE the fix (perfectly quadratic): 20k chars 1.35s,
    # 40k 5.80s, 80k 23.38s. This size took 23s; anything near it now is a
    # regression back to the full-prefix scan.
    text = "May " * 20_000                      # 80k chars, 20k scanning matches
    t0 = time.perf_counter()
    extract_dates(text)
    dt = time.perf_counter() - t0
    assert dt < 2.0, f"extract_dates took {dt:.1f}s on 80k chars — quadratic?"


def test_extract_dates_guard_still_correct():
    """The bounded window must not change the anchoring decision."""
    from verimem.quantity_match import extract_dates
    assert extract_dates("May I help you") == set()          # unanchored
    assert extract_dates("we ship in May") != set()          # temporal preposition
    assert extract_dates("may slip") == set()                # lowercase modal
