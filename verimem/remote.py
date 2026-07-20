"""RemoteMemory — the thin client of a shared verimem memory server.

Architecture A (2026-07-20): N clients on one SQLite file do not scale
(measured plateau ~11 ops/s past 5 clients; every process loads its own
models). The scalable topology is ONE server process owning the models and
the store — the existing hardened gateway — and every other consumer a THIN
client: no model load, no SQLite handle, just HTTP with the tenant's key.

Surface: the subset of :class:`verimem.client.Memory` the hot paths use —
``add`` / ``search`` / ``explain`` / ``get`` / ``delete`` / ``stats`` /
``health``. Methods raise honest, typed errors: ``PermissionError`` on a
bad key, ``ConnectionError`` when the server is unreachable, ``RuntimeError``
on any other non-2xx. ``get`` returns ``None`` on 404 like the embedded API.
"""
from __future__ import annotations

from typing import Any


class RemoteMemory:
    def __init__(self, url: str, api_key: str, *, timeout_s: float = 15.0,
                 request_timeout_s: float | None = None,
                 _client: Any = None) -> None:
        self.url = (url or "").rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        # PROBE timeout (health) stays snappy; DATA requests get their own,
        # longer budget - live e2e 2026-07-20: a 5s blanket timeout killed the
        # FIRST write while the server cold-loaded its models.
        if request_timeout_s is None:
            import os
            try:
                request_timeout_s = float(
                    os.environ.get("VERIMEM_SERVER_REQUEST_TIMEOUT_S", "60")
                    or 60)
            except ValueError:
                request_timeout_s = 60.0
        self._request_timeout_s = float(request_timeout_s)
        self._own_client = _client is None
        if _client is None:
            import httpx
            _client = httpx.Client(base_url=self.url, timeout=timeout_s)
        self._c = _client

    # -- plumbing -----------------------------------------------------------
    def _req(self, method: str, path: str, *, none_on_404: bool = False,
             **kw: Any) -> Any:
        kw.setdefault("timeout", self._request_timeout_s)
        try:
            r = self._c.request(method, path, headers=self._headers, **kw)
        except Exception as exc:  # noqa: BLE001 — network layer -> typed error
            raise ConnectionError(
                f"verimem server unreachable at {self.url or path}: "
                f"{type(exc).__name__}") from exc
        if r.status_code in (401, 403):
            raise PermissionError(
                f"verimem server rejected the API key ({r.status_code})")
        if r.status_code == 404 and none_on_404:
            return None
        if r.status_code >= 400:
            raise RuntimeError(
                f"verimem server error {r.status_code}: {r.text[:200]}")
        return r.json()

    # -- surface ------------------------------------------------------------
    def health(self, *, raise_on_down: bool = False) -> bool:
        """True iff the server answers /v1/health. Non-raising by default so
        callers can probe-and-fallback; ``raise_on_down`` surfaces the
        ConnectionError for callers that must not silently degrade."""
        try:
            self._req("GET", "/v1/health", timeout=None)  # client default = probe budget
            return True
        except ConnectionError:
            if raise_on_down:
                raise
            return False
        except PermissionError:
            # Kimi audit F1: an auth-REJECTED server is not a usable delegate.
            # Swallowing this as "up" kept the thin client installed with a
            # revoked key, and every op then fell back silently to the local
            # store - neutralizing central revocation and diverging the shared
            # corpus. The rejection surfaces; the caller decides (fail-closed).
            raise
        except Exception:  # noqa: BLE001 — other errors: the server IS up
            return True

    def add(self, content: str, *, topic: str = "user",
            verified_by: list[str] | None = None, source: str | None = None,
            asserted_at: float | None = None, **_ignored: Any) -> dict:
        body: dict[str, Any] = {"content": content, "topic": topic}
        if verified_by is not None:
            body["verified_by"] = list(verified_by)
        if source is not None:
            body["source"] = source
        if asserted_at is not None:
            body["asserted_at"] = float(asserted_at)
        # ONE idempotency key per logical write + ONE retry on timeout with the
        # SAME key: the live failure (server finished a slow cold write after
        # the client gave up) becomes a replayed receipt, never a twin.
        import uuid
        idem = uuid.uuid4().hex
        headers = {**self._headers, "Idempotency-Key": idem}
        for attempt in (1, 2):
            try:
                kw: dict[str, Any] = {"json": body, "headers": headers,
                                      "timeout": self._request_timeout_s}
                r = self._c.request("POST", "/v1/memories", **kw)
                break
            except Exception as exc:  # noqa: BLE001 -- retry ONCE on timeout-ish
                is_timeout = "timeout" in type(exc).__name__.lower() or \
                    "timeout" in str(exc).lower()
                if attempt == 2 or not is_timeout:
                    raise ConnectionError(
                        f"verimem server unreachable at {self.url}: "
                        f"{type(exc).__name__}") from exc
        if r.status_code in (401, 403):
            raise PermissionError(
                f"verimem server rejected the API key ({r.status_code})")
        if r.status_code >= 400:
            raise RuntimeError(
                f"verimem server error {r.status_code}: {r.text[:200]}")
        return r.json()

    def search(self, q: str, k: int = 5, **kw: Any) -> list[dict]:
        params: dict[str, Any] = {"q": q, "k": k}
        for key in ("deep", "as_of", "with_history"):
            if key in kw and kw[key] is not None:
                params[key] = kw[key]
        out = self._req("GET", "/v1/search", params=params)
        return list(out.get("hits", []))

    def explain(self, q: str, k: int = 5,
                min_relevance: Any = None) -> dict:
        params: dict[str, Any] = {"q": q, "k": k}
        if min_relevance is not None:
            params["min_relevance"] = min_relevance
        return self._req("GET", "/v1/explain", params=params)

    def get(self, fact_id: str) -> dict | None:
        return self._req("GET", f"/v1/memories/{fact_id}", none_on_404=True)

    def delete(self, fact_id: str, *, purge_history: bool = False) -> bool:
        out = self._req("DELETE", f"/v1/memories/{fact_id}",
                        params={"purge_history": purge_history})
        return bool((out or {}).get("removed"))

    def stats(self) -> dict:
        return self._req("GET", "/v1/stats")

    def close(self) -> None:
        if self._own_client:
            try:
                self._c.close()
            except Exception:  # noqa: BLE001
                pass


__all__ = ["RemoteMemory"]
