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
                 _client: Any = None) -> None:
        self.url = (url or "").rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._own_client = _client is None
        if _client is None:
            import httpx
            _client = httpx.Client(base_url=self.url, timeout=timeout_s)
        self._c = _client

    # -- plumbing -----------------------------------------------------------
    def _req(self, method: str, path: str, *, none_on_404: bool = False,
             **kw: Any) -> Any:
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
            self._req("GET", "/v1/health")
            return True
        except ConnectionError:
            if raise_on_down:
                raise
            return False
        except Exception:  # noqa: BLE001 — auth errors etc: server IS up
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
        return self._req("POST", "/v1/memories", json=body)

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
