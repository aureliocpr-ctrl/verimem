"""opus tenant-pass #4: the plan fact-quota was CHECK-then-ACT — `count()` (line
~862) then `mem.add()` (line ~881) with nothing between them. N concurrent writes
to a tenant at cap-1 all read the same `used`, all pass `within_facts`, and all
store → the quota is exceeded by up to N-1. A `free` tenant (1000 facts) could be
pushed past its cap under load.

The fix is an atomic reserve-counter: `count()` + in-flight reservations counted
UNDER ONE LOCK, so the TOCTOU window closes — a slot in flight already counts
against the cap. These pin the reserve/release contract directly (pure fns), incl.
a real-thread race so the concurrency claim is measured, not asserted.
"""
from __future__ import annotations

import threading

from engram.gateway import _quota_release, _quota_reserve
from engram.gateway_plans import get_plan

FREE = get_plan("free")            # max_facts = 1000
ENTERPRISE = get_plan("enterprise")  # max_facts = None (uncapped)


def test_uncapped_plan_always_reserves():
    # enterprise/self_host: no cap → always True, no pending state touched
    pending: dict[str, int] = {}
    lock = threading.Lock()
    assert _quota_reserve(pending, lock, "t", ENTERPRISE, lambda: 10**9) is True
    assert pending == {}


def test_reserve_counts_inflight_so_only_one_slot_at_cap():
    # count STUCK at 999 (adds in flight, not yet reflected in count()) — this IS
    # the TOCTOU window. Old inline logic: all 5 see 999<1000 → all True (overflow).
    pending: dict[str, int] = {}
    lock = threading.Lock()
    got = [_quota_reserve(pending, lock, "t1", FREE, lambda: 999) for _ in range(5)]
    assert got == [True, False, False, False, False]
    assert pending["t1"] == 1


def test_release_frees_the_reserved_slot():
    pending: dict[str, int] = {}
    lock = threading.Lock()
    assert _quota_reserve(pending, lock, "t1", FREE, lambda: 999) is True
    assert pending["t1"] == 1
    _quota_release(pending, lock, "t1", FREE)
    assert pending.get("t1", 0) == 0
    # slot freed → a fresh reserve at the same count succeeds again
    assert _quota_reserve(pending, lock, "t1", FREE, lambda: 999) is True


def test_release_is_noop_for_uncapped():
    pending: dict[str, int] = {}
    _quota_release(pending, threading.Lock(), "t", ENTERPRISE)
    assert pending == {}


def test_tenants_do_not_share_quota_budget():
    pending: dict[str, int] = {}
    lock = threading.Lock()
    assert _quota_reserve(pending, lock, "a", FREE, lambda: 999) is True
    # a different tenant at its own 999 is independent — its slot is still free
    assert _quota_reserve(pending, lock, "b", FREE, lambda: 999) is True
    assert pending == {"a": 1, "b": 1}


def test_real_threads_grant_exactly_one_slot():
    # 40 threads race to reserve the single remaining slot (count pinned at 999).
    pending: dict[str, int] = {}
    lock = threading.Lock()
    out: list[bool] = []
    out_lock = threading.Lock()
    start = threading.Barrier(40)

    def worker():
        start.wait()  # maximize contention
        ok = _quota_reserve(pending, lock, "t1", FREE, lambda: 999)
        with out_lock:
            out.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(out) == 1          # exactly ONE write may proceed
    assert pending["t1"] == 1     # exactly one reservation held
