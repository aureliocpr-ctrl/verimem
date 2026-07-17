#!/usr/bin/env python
"""Ingest un file MD (o glob) nel tier documents di Engram — snapshot versionato.

Caso d'uso CONTINUITA-MD: linki un MD -> Engram ne tiene una copia versionata-per-hash
in uno store ISOLATO (fuori dal corpus di recall accettato). Re-run IDEMPOTENTE finche'
il contenuto non cambia (poi nuova versione). Niente scrittura sul corpus facts/episodi.

Run:  python scripts/ingest_md.py <path-o-glob> [<path2> ...]
Es.:  python scripts/ingest_md.py "docs/**/*.md" "~/notes/*.md"
"""
from __future__ import annotations

import glob
import sys
import time
from pathlib import Path

from verimem.documents import DocumentStore


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: ingest_md.py <path-o-glob> [...]")
        return 2
    paths: list[str] = []
    for a in argv:
        if any(ch in a for ch in "*?["):
            paths.extend(glob.glob(a, recursive=True))
        else:
            paths.append(a)
    files = [p for p in dict.fromkeys(paths) if Path(p).is_file()]
    if not files:
        print("nessun file trovato")
        return 1
    ds = DocumentStore()
    now = time.time()
    new = unchanged = 0
    for p in files:
        r = ds.ingest_file(p, fetched_at=now)
        if r["is_new"]:
            new += 1
            tag = f"NEW v{r['version']}"
        else:
            unchanged += 1
            tag = f"unchanged v{r['version']}"
        print(f"  {tag:<13} {Path(p).name:<40} {r['content_hash'][:12]}  id={r['id']}")
    print(f"DONE: {len(files)} file ({new} nuovi/versionati, {unchanged} invariati) -> {ds.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
