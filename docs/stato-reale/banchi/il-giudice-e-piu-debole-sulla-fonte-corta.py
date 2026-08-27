# -*- coding: utf-8 -*-
"""Il falso ha preso 55.2 sul regime corto e 0.2 su tutti gli altri. Quella
cella conteneva il caricamento dei pesi (24.712 ms): n=1 con dentro il warmup
non e' una misura. Cinque ripetizioni, la prima a freddo e quattro a caldo."""
import tempfile, time
from pathlib import Path
from verimem.client import Memory

testo = Path("docs/archive/2026-05-13_FORGIA.md").read_text(encoding="utf-8", errors="replace")
fonte = testo[:2000]
mem = Memory(str(Path(tempfile.mkdtemp()) / "riprova.db"))
print(f"  fonte: primi 2000 char del documento reale · «1143» presente: {'1143' in fonte}")
print(f"  claim: «Il file wake.py conta 9999 LOC.» · «9999» nella fonte: {'9999' in fonte}\n")
for i in range(5):
    t0 = time.monotonic()
    r = mem.add("Il file wake.py conta 9999 LOC.", topic=f"riprova/{i}", source=fonte, validate="full")
    ms = (time.monotonic() - t0) * 1000
    w = str(r.get("warnings"))[:70].replace("\n", " ")
    print(f"  giro {i+1}: {str(r.get('status')):<12} ground {float(r.get('grounding_score') or -1):6.1f}  {ms:7.0f} ms  {w}")
