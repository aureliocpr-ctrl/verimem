"""Math challenge: Collatz, Goldbach, Twin primes — pure local.

Phase D del massive testing: dimostra che HippoAgent può fare
da spina dorsale di memoria per task computazionali reali.

Run: python scripts/math_challenge.py
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

# ---------- Collatz ----------

def collatz_steps(n: int) -> int:
    """Number of Collatz steps until n reaches 1."""
    s = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        s += 1
    return s


def collatz_max_in_range(N: int) -> dict[str, Any]:
    """For 1..N find the integer with MAX steps. Memoized."""
    cache: dict[int, int] = {1: 0}

    def steps(n: int) -> int:
        path = []
        m = n
        while m not in cache:
            path.append(m)
            m = m // 2 if m % 2 == 0 else 3 * m + 1
        base = cache[m]
        for i, x in enumerate(reversed(path), start=1):
            cache[x] = base + i
        return cache[n]

    best_n = 1
    best_s = 0
    for k in range(1, N + 1):
        s = steps(k)
        if s > best_s:
            best_s = s
            best_n = k
    return {"N": N, "best_n": best_n, "best_steps": best_s}


# ---------- Goldbach ----------

def sieve(N: int) -> list[bool]:
    """Sieve of Eratosthenes: is_prime[k] for 0..N."""
    is_prime = [True] * (N + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(N**0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, N + 1, i):
                is_prime[j] = False
    return is_prime


def goldbach_verify(N: int) -> dict[str, Any]:
    """Verify: every even k in [4, N] = p + q (both prime)."""
    is_prime = sieve(N)
    counterexample: int | None = None
    for k in range(4, N + 1, 2):
        found = False
        for p in range(2, k // 2 + 1):
            if is_prime[p] and is_prime[k - p]:
                found = True
                break
        if not found:
            counterexample = k
            break
    return {
        "N": N,
        "all_pass": counterexample is None,
        "counterexample": counterexample,
    }


# ---------- Twin primes ----------

def twin_primes_count(N: int) -> dict[str, Any]:
    """Count pairs (p, p+2) both prime in [2, N]."""
    is_prime = sieve(N)
    twins: list[tuple[int, int]] = []
    for p in range(3, N - 1, 2):
        if is_prime[p] and is_prime[p + 2]:
            twins.append((p, p + 2))
    return {
        "N": N,
        "count": len(twins),
        "smallest": twins[0] if twins else None,
        "largest": twins[-1] if twins else None,
    }


# ---------- Main ----------

def bench(name: str, fn) -> dict[str, Any]:
    t0 = time.perf_counter()
    result = fn()
    elapsed = (time.perf_counter() - t0) * 1000
    return {"name": name, "ms": round(elapsed, 1), "result": result}


def main():
    print("=== Math Challenge: Collatz / Goldbach / Twin primes ===\n")
    results = []

    # Collatz
    print(">> Collatz: max-steps integer in [1..10^6]")
    r = bench("collatz_max[10^6]", lambda: collatz_max_in_range(1_000_000))
    results.append(r)
    print(f"   ms={r['ms']}  n={r['result']['best_n']}  steps={r['result']['best_steps']}")

    # Goldbach
    print("\n>> Goldbach: ogni pari in [4..10^4] = somma di 2 primi?")
    r = bench("goldbach[10^4]", lambda: goldbach_verify(10_000))
    results.append(r)
    print(f"   ms={r['ms']}  all_pass={r['result']['all_pass']}")

    # Twin primes
    print("\n>> Twin primes in [2..10^5]")
    r = bench("twin_primes[10^5]", lambda: twin_primes_count(100_000))
    results.append(r)
    print(f"   ms={r['ms']}  count={r['result']['count']}  largest={r['result']['largest']}")

    # Sanity facts (per HippoAgent ingestion):
    facts = [
        f"Collatz: max steps in [1..10^6] is {results[0]['result']['best_steps']} reached at n={results[0]['result']['best_n']}",
        f"Goldbach holds for all even in [4..10^4]: {results[1]['result']['all_pass']}",
        f"Twin primes in [2..10^5]: {results[2]['result']['count']} pairs, largest={results[2]['result']['largest']}",
    ]
    print("\n=== Facts for HippoAgent ingestion ===")
    for f in facts:
        print(f"  - {f}")

    Path("math_report.json").write_text(__import__("json").dumps({
        "results": results,
        "facts": facts,
    }, indent=2, default=str))
    print("\nReport saved -> math_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
