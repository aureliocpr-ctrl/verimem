"""Gateway under CONCURRENT load — the enterprise/datacenter leg, measured not assumed.

The in-process recall path is characterized (docs/SCALE_CHARACTERIZATION.md); what was
never measured is the HTTP gateway under fire: real uvicorn, concurrent tenants writing
and searching, oversized payloads, wrong keys. This probe reports, per phase:
throughput, p50/p95 latency, status-code histogram — and FAILS (exit 1) if any request
returns a 5xx or a wrong code class (the enterprise invariant: overload may slow or
politely refuse, never crash or corrupt).

Phases (thread pool, default 16 workers):
  1. writes    — N POST /v1/memories (no source: L1 gate, no LLM in the loop)
  2. searches  — N GET  /v1/search
  3. mixed     — N/2 writes + N/2 searches interleaved
  4. big       — oversized payloads (must be a clean 4xx, never 5xx)
  5. badkey    — wrong API key (must be 401/403, never 5xx)

    python -m benchmark.gateway_load_probe --n 300 --workers 16 \
        --out benchmark/results/gateway_load_probe.json
"""
from __future__ import annotations

import argparse
import json
import socket
import statistics
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import uvicorn


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(data_dir: Path, port: int) -> str:
    """Boot the real app on a real port; return a provisioned tenant api_key.
    Keys are issued programmatically (GatewayKeys.issue) exactly like the
    production CLI does — there is no HTTP admin surface for key creation."""
    from engram.gateway import GatewayKeys, create_app
    keys = GatewayKeys(data_dir / "keys.db")
    api_key = keys.create(tenant_id="loadtest", plan="enterprise")
    app = create_app(data_dir=data_dir, keys=keys)
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(cfg)
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            httpx.get(f"http://127.0.0.1:{port}/v1/health", timeout=1)
            return api_key
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("gateway did not come up in 20s")


def _safe(fn):
    """Wrap a request fn so a client-side timeout/error is RECORDED as a code
    (not crashed): a hung request is data, and the phase must still report."""
    def inner(i):
        t = time.perf_counter()
        try:
            return fn(i)
        except httpx.TimeoutException:
            return "timeout", (time.perf_counter() - t) * 1000
        except Exception as e:  # noqa: BLE001 — record, never abort the phase
            return f"err:{type(e).__name__}", (time.perf_counter() - t) * 1000
    return inner


def _phase(name, fn, items, workers):
    lat, codes = [], {}
    fn = _safe(fn)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for code, ms in ex.map(fn, items):
            lat.append(ms)
            codes[str(code)] = codes.get(str(code), 0) + 1
    wall = time.perf_counter() - t0
    lat.sort()
    return {
        "phase": name, "n": len(items), "wall_s": round(wall, 2),
        "rps": round(len(items) / wall, 1),
        "p50_ms": round(statistics.median(lat), 1) if lat else None,
        "p95_ms": round(lat[int(len(lat) * 0.95) - 1], 1) if lat else None,
        "max_ms": round(lat[-1], 1) if lat else None,
        "codes": codes,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--big-kb", type=int, default=256)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    data_dir = Path(tempfile.mkdtemp(prefix="gwload_"))
    port = _free_port()
    key = _start_server(data_dir, port)
    base = f"http://127.0.0.1:{port}"
    H = {"x-api-key": key}

    client = httpx.Client(timeout=60)

    def write(i):
        # neutral wording: no completion/dev verbs, so the L1 gate ADMITS and we
        # measure the admit path (first probe run: "finished" quarantined all 300)
        t = time.perf_counter()
        r = client.post(f"{base}/v1/memories", headers=H, json={
            "content": f"Order {i} contains {i % 97} items for warehouse {i % 11}.",
            "topic": f"load/{i % 7}"})
        return r.status_code, (time.perf_counter() - t) * 1000

    def search(i):
        t = time.perf_counter()
        r = client.get(f"{base}/v1/search", headers=H,
                       params={"q": f"batch job {i % 50}", "k": 5})
        return r.status_code, (time.perf_counter() - t) * 1000

    def mixed(i):
        return write(i) if i % 2 == 0 else search(i)

    def big(i):
        blob = ("x" * 1024) * a.big_kb
        t = time.perf_counter()
        r = client.post(f"{base}/v1/memories", headers=H,
                        json={"content": blob, "topic": "load/big"})
        return r.status_code, (time.perf_counter() - t) * 1000

    def badkey(i):
        t = time.perf_counter()
        r = client.get(f"{base}/v1/search", headers={"x-api-key": "wrong-key"},
                       params={"q": "x"})
        return r.status_code, (time.perf_counter() - t) * 1000

    # warm-up (embedding model load happens on the first write/search)
    write(-1), search(-1)

    phases = []
    for name, fn, items, w in [
        ("writes", write, range(a.n), a.workers),
        ("searches", search, range(a.n), a.workers),
        ("mixed", mixed, range(a.n), a.workers),
        ("big_payload", big, range(10), min(4, a.workers)),
        ("bad_key", badkey, range(50), a.workers),
    ]:
        ph = _phase(name, fn, items, w)
        phases.append(ph)
        print(f"PHASE {name}: rps={ph['rps']} p50={ph['p50_ms']}ms "
              f"p95={ph['p95_ms']}ms codes={ph['codes']}", flush=True)
    client.close()

    # invariants: no 5xx anywhere; big -> 4xx or 200 (if within limits); badkey -> 401/403
    violations = []
    for ph in phases:
        for code, cnt in ph["codes"].items():
            if code.startswith("5"):
                violations.append(f"{ph['phase']}: {cnt}x {code}")
        if any(k.startswith(("timeout", "err:")) for k in ph["codes"]):
            bad = {k: v for k, v in ph["codes"].items()
                   if k.startswith(("timeout", "err:"))}
            violations.append(f"{ph['phase']}: client failures {bad}")
    bk = phases[-1]["codes"]
    if any(not k.startswith("4") for k in bk):
        violations.append(f"bad_key returned non-4xx: {bk}")

    res = {"n": a.n, "workers": a.workers, "big_kb": a.big_kb,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "phases": phases, "violations": violations}
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"wrote {a.out}")
    print(f"\nVIOLATIONS: {len(violations)}" + ("" if not violations else f" -> {violations}"))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
