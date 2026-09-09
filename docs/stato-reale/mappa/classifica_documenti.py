"""Raccoglie gli INDIZI per classificare i 287 .md di docs/ — non il verdetto.

    python classifica_documenti.py <radice-repo> > indizi.tsv

Il verdetto VIVO / MORTO / CONTRADDICE IL CODICE lo do leggendo. Questo script
fa la parte meccanica, che a mano su 287 file sarebbe sia lenta sia sbagliata:

  · CHI LO CITA — README, CHANGELOG, codice, test, altri documenti. Un documento
    che nessuno cita non e' per questo morto (puo' essere una cronaca), ma un
    documento CITATO dal README non puo' essere morto senza che il README menta.
  · I PATH CHE NOMINA ESISTONO ANCORA? Un documento che rimanda a
    `verimem/qualcosa.py` sparito e' un candidato a CONTRADDICE, e lo script
    stampa QUALE path manca: e' la riga che dovro' mettere nel verdetto.
  · QUANDO E' STATO TOCCATO. L'eta' da sola non decide niente — un documento
    fermo puo' essere ancora vero — ma ordina la coda.

Il verdetto NON e' automatizzabile e non lo automatizzo: la colonna `verdetto`
esce vuota, e la riempio io file per file.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

R = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
DOCS = R / "docs"

md = sorted(p for p in DOCS.rglob("*.md") if p.is_file())

# --- il corpus che cita: lo leggo UNA volta ----------------------------------
def leggi(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

readme = leggi(R / "README.md")
changelog = leggi(R / "CHANGELOG.md")
codice = {p: leggi(p) for p in (R / "verimem").rglob("*.py")}
test = {p: leggi(p) for p in (R / "tests").rglob("*.py")}
altri_doc = {p: leggi(p) for p in md}
tutto_codice = "\n".join(codice.values())
tutto_test = "\n".join(test.values())
tutti_doc = "\n".join(altri_doc.values())

PATH_RE = re.compile(r"\b((?:verimem|tests|scripts|benchmark)/[A-Za-z0-9_./-]+\.py)\b")

print("file\tcitato_da\tpath_rotti\tultimo_commit\tverdetto\tprova")
for p in md:
    rel = p.relative_to(R).as_posix()
    nome = p.name
    cit = []
    if nome in readme or rel in readme: cit.append("README")
    if nome in changelog or rel in changelog: cit.append("CHANGELOG")
    if nome in tutto_codice or rel in tutto_codice: cit.append("codice")
    if nome in tutto_test or rel in tutto_test: cit.append("test")
    # i doc che lo citano, escluso se stesso
    testo = altri_doc[p]
    altri = sum(1 for q, t in altri_doc.items() if q != p and (nome in t or rel in t))
    if altri: cit.append(f"doc×{altri}")

    rotti = []
    for m in dict.fromkeys(PATH_RE.findall(testo)):
        if not (R / m).exists():
            rotti.append(m)

    try:
        d = subprocess.run(["git", "-C", str(R), "log", "-1", "--format=%ad",
                            "--date=format:%Y-%m-%d", "--", rel],
                           capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        d = "?"

    print(f"{rel}\t{','.join(cit) or '-'}\t{';'.join(rotti[:3]) or '-'}\t{d or '?'}\t\t")
