"""Positive control: does the SHARED-SERVER path hold the load that collapses
the direct N-process path?

concurrency_multiprocess.py measured the anti-pattern — 2 separate processes,
each its own Memory, each loading its OWN embedding + reranker models, competing
for the CPU → write p50 24s. This harness runs the SAME 2-client read/write mix
against ONE gateway server process (which owns the models + DB exactly once) via
RemoteMemory thin clients. If the architecture is the cure, writes stay in the
hundreds-of-ms range instead of tens of seconds.

Server in its OWN process (real uvicorn hop), clients in their OWN processes —
faithful to 'two Claude instances, one memory server'.

    python -m benchmark.concurrency_shared_server --workers 2 --secs 15
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _pctl(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    i = min(len(xs) - 1, int(round(p / 100.0 * (len(xs) - 1))))
    return round(xs[i] * 1000, 1)


# ---- the server launcher runs as `python -m ...concurrency_shared_server --serve`
def _serve(data_dir: str, key_db: str, api_key_tenant: str, port: int) -> None:
    import logging
    logging.disable(logging.CRITICAL)
    import uvicorn

    from verimem.gateway import GatewayKeys, create_app, mark_multi_writer
    mark_multi_writer()   # process-global marker the server owns
    keys = GatewayKeys(Path(key_db))
    # tenant provisioned by the parent; here we just build the app on it
    app = create_app(data_dir=Path(data_dir), keys=keys)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="critical")


def _client(url: str, api_key: str, secs: float, wid: int, q: mp.Queue) -> None:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    from verimem.remote import RemoteMemory
    m = RemoteMemory(url, api_key)
    reads: list[float] = []
    writes: list[float] = []
    errors: list[str] = []
    n = 0
    stop = time.time() + secs
    while time.time() < stop:
        n += 1
        if n % 4 == 0:
            t0 = time.perf_counter()
            try:
                m.add(f"Worker {wid} observation {n}: subsystem {n % 7} "
                      f"changed state at tick {n}.", topic=f"w{wid}/obs")
                writes.append(time.perf_counter() - t0)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"write:{type(exc).__name__}:{exc}"[:120])
        else:
            t0 = time.perf_counter()
            try:
                m.search(f"subsystem {n % 7} state", k=5)
                reads.append(time.perf_counter() - t0)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"read:{type(exc).__name__}:{exc}"[:120])
    q.put({"wid": wid, "reads": reads, "writes": writes, "errors": errors})


def _wait_health(url: str, timeout_s: float = 120.0) -> bool:
    import urllib.error
    import urllib.request
    stop = time.time() + timeout_s
    while time.time() < stop:
        try:
            with urllib.request.urlopen(url + "/v1/health", timeout=3) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(1.0)
    return False


def run(n_workers: int, secs: float) -> dict:
    import shutil
    import tempfile
    base = Path(tempfile.mkdtemp(prefix="verimem_ss_"))
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    key_db = base / "keys.db"

    # provision one tenant key in the parent, share it with server + clients.
    # plan=self_host: uncapped, the correct tier for a self-hosted deployment
    # measuring its OWN store — the free tier's 60/min cap (gateway.py:948)
    # otherwise throttles the load and we'd measure the rate limiter, not the
    # store. (Separate honest note: 2 clients sharing a FREE key DO hit that
    # 60/min cliff — a real deployment concern, but not what this control tests.)
    from verimem.gateway import GatewayKeys
    api_key = GatewayKeys(key_db).create(tenant_id="stress", name="bench",
                                         plan="self_host")
    port = _free_port()
    url = f"http://127.0.0.1:{port}"

    server = subprocess.Popen(
        [sys.executable, "-m", "benchmark.concurrency_shared_server", "--serve",
         "--data-dir", str(data_dir), "--key-db", str(key_db),
         "--port", str(port)],
        cwd=str(Path(__file__).resolve().parents[1]))
    try:
        if not _wait_health(url):
            server.terminate()
            return {"workers": n_workers, "error": "server did not become healthy"}
        # seed via one client
        from verimem.remote import RemoteMemory
        seeder = RemoteMemory(url, api_key)
        for i in range(40):
            seeder.add(f"Seed {i}: subsystem {i % 7} handles case {i}.",
                       topic=f"seed/{i % 5}")

        ctx = mp.get_context("spawn")
        q: mp.Queue = ctx.Queue()
        procs = [ctx.Process(target=_client, args=(url, api_key, secs, w, q))
                 for w in range(n_workers)]
        t0 = time.perf_counter()
        for p in procs:
            p.start()
        results = [q.get() for _ in procs]
        for p in procs:
            p.join()
        wall = time.perf_counter() - t0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(base, ignore_errors=True)

    reads = [x for r in results for x in r["reads"]]
    writes = [x for r in results for x in r["writes"]]
    errors = [e for r in results for e in r["errors"]]
    allops = reads + writes
    return {
        "workers": n_workers, "wall_s": round(wall, 1),
        "n_reads": len(reads), "n_writes": len(writes), "n_errors": len(errors),
        "read_p50": _pctl(reads, 50), "read_p99": _pctl(reads, 99),
        "read_max": _pctl(reads, 100),
        "write_p50": _pctl(writes, 50), "write_p99": _pctl(writes, 99),
        "write_max": _pctl(writes, 100),
        "ops_over_5s": sum(1 for x in allops if x > 5.0),
        "ops_over_10s": sum(1 for x in allops if x > 10.0),
        "throughput_ops_s": round(len(allops) / wall, 1) if wall else 0.0,
        "error_samples": errors[:5],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true", help="internal: run the server")
    ap.add_argument("--data-dir")
    ap.add_argument("--key-db")
    ap.add_argument("--port", type=int)
    ap.add_argument("--workers", type=int, nargs="+", default=[2])
    ap.add_argument("--secs", type=float, default=15.0)
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    if args.serve:
        _serve(args.data_dir, args.key_db, "stress", args.port)
        return

    rows = []
    print("shared-server concurrency — ONE server process, N thin clients")
    print(f"  {'N':>2}  {'reads':>6} {'writes':>6} {'err':>4}  "
          f"{'r_p50':>6} {'r_p99':>7}  {'w_p50':>6} {'w_p99':>7} {'w_max':>8}  "
          f"{'>5s':>4} {'>10s':>5} {'op/s':>6}")
    for w in args.workers:
        r = run(w, args.secs)
        rows.append(r)
        if r.get("error"):
            print(f"  {w:>2}  ERROR: {r['error']}")
            continue
        print(f"  {r['workers']:>2}  {r['n_reads']:>6} {r['n_writes']:>6} "
              f"{r['n_errors']:>4}  {r['read_p50']:>6} {r['read_p99']:>7}  "
              f"{r['write_p50']:>6} {r['write_p99']:>7} {r['write_max']:>8}  "
              f"{r['ops_over_5s']:>4} {r['ops_over_10s']:>5} "
              f"{r['throughput_ops_s']:>6}", flush=True)
        if r["error_samples"]:
            print(f"      errors: {r['error_samples']}", flush=True)
    if args.json_out:
        import json
        Path(args.json_out).write_text(json.dumps({"rows": rows}, indent=2),
                                       encoding="utf-8")


if __name__ == "__main__":
    main()
