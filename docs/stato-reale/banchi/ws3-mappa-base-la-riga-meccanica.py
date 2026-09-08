"""La BASE MECCANICA di una riga di mappa: per ogni funzione/classe di un file,
nome, riga, prima riga di docstring, chiamanti e test che la nominano.

⚠️ Cio' che questo script produce NON e' un verdetto: e' l'elenco di dove
guardare. «grep serve a TROVARE, mai a CONTARE» (regola del mandato): i
chiamanti trovati per nome vanno LETTI prima di scriverli nella mappa, e il
verdetto si mette solo col comando eseguito.

Uso: python mappa_base.py <wt> <file.py relativo a verimem/>
"""
import ast
import pathlib
import subprocess
import sys

WT = pathlib.Path(sys.argv[1]).resolve()
REL = sys.argv[2]
SRC = WT / "verimem" / REL
albero = ast.parse(SRC.read_text(encoding="utf-8"))


def _doc1(n) -> str:
    d = ast.get_docstring(n) or ""
    return " ".join(d.strip().split())[:120] if d else ""


def _riga(nome: str, dove: str) -> list[str]:
    """Righe che nominano `nome` sotto `dove` (repo-relative), max 4."""
    try:
        out = subprocess.run(["git", "-C", str(WT), "grep", "-n", "-w", nome, "--", dove],
                             capture_output=True, text=True, timeout=90, encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return []
    righe = [r for r in (out.stdout or "").splitlines() if f"verimem/{REL}:" not in r]
    return righe[:4]


voci = []
for nodo in ast.walk(albero):
    if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        tipo = "class" if isinstance(nodo, ast.ClassDef) else "def"
        voci.append((nodo.lineno, tipo, nodo.name, _doc1(nodo)))
voci.sort()
print(f"# {REL}: {len(voci)} fra funzioni e classi, {len(SRC.read_text(encoding='utf-8').splitlines())} righe\n")
for riga, tipo, nome, doc in voci:
    if nome.startswith("__") and nome.endswith("__"):
        continue
    chiamanti = _riga(nome, "verimem")
    test = _riga(nome, "tests")
    print(f"{riga}\t{tipo}\t{nome}\t{doc}")
    print(f"\tCHIAMANTI({len(chiamanti)}): {'; '.join(c[:90] for c in chiamanti[:3]) or 'NESSUNO trovato per nome'}")
    print(f"\tTEST({len(test)}): {'; '.join(t.split(':')[0] for t in test[:3]) or 'NESSUNO trovato per nome'}")
