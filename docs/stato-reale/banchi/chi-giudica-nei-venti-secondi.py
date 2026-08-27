# -*- coding: utf-8 -*-
"""Chi risponde nei 20 secondi. Le chiavi le stampo, non le presumo."""
import json, tempfile, time
from pathlib import Path
from verimem.client import Memory

testo = Path("docs/archive/2026-05-13_FORGIA.md").read_text(encoding="utf-8", errors="replace")
mem = Memory(str(Path(tempfile.mkdtemp()) / "chi.db"))
for n in (2000, 6000):
    t0 = time.monotonic()
    r = mem.add("Il file wake.py conta 9999 LOC.", topic=f"chi/{n}", source=testo[:n], validate="full")
    ms = (time.monotonic() - t0) * 1000
    print(f"\n===== taglio {n} · {ms:.0f} ms · ground {r.get('grounding_score')} · {r.get('status')}")
    for k in ("moat", "adjudication"):
        print(f"  {k}: {json.dumps(r.get(k), ensure_ascii=False, default=str)[:600]}")
