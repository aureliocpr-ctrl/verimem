"""Quanti rimandi del README portano a un file che parla di CIO' che il numero
misura? (v3 — e le prime due versioni sono la parte istruttiva)

v1 fermata dal controllo: finestra di una riga, il caso noto stava tre righe sopra.
v2 fermata dal controllo: la domanda era «la CIFRA compare nel file?», e in un file
   da 73 KB quasi ogni sequenza di cifre compare — per giunta «0.81» matcha dentro
   «0.813». Il proxy era sbagliato, non la finestra.

v3 cambia la DOMANDA, non la soglia: un rimando porta alla fonte se il file di
arrivo parla del BANCO che il numero misura. Il soggetto, non la cifra.
Nel caso noto: «locomo» compare 0 volte in docs/BENCHMARKS.md e 11 in BENCHMARKS.md.

CRITERIO, dichiarato prima: per ogni link a un DOCUMENTO del repo, se nel suo
paragrafo compare il nome di un banco noto, quel nome deve comparire nel file di
arrivo. CONTROLLO CHE DEVE ACCENDERSI: LoCoMo -> docs/BENCHMARKS.md.
"""
import io
import os
import re
import sys

BANCHI = ["locomo", "longmemeval", "truthfulqa", "halumem", "musique",
          "squad", "halueval", "hotpotqa", "loco", "nq-open"]
LINK = re.compile(r"\[([^\]]{1,120})\]\(([^)]{1,300})\)")
GITHUB = re.compile(r"https?://github\.com/[^/]+/[^/]+/blob/[^/]+/(.+?)(?:#.*)?$")
SCRIPT = (".py", ".sh", ".yml", ".yaml", ".toml", ".cfg", ".json")


def risolvi(url):
    url = url.strip()
    m = GITHUB.match(url)
    if m:
        return m.group(1)
    if url.startswith(("http://", "https://", "mailto:", "#")):
        return None
    return url.split("#")[0].lstrip("./")


def paragrafi(righe):
    mappa, blocco, inizio = {}, [], 0
    for i, r in enumerate(righe + [""]):
        if r.strip():
            if not blocco:
                inizio = i
            blocco.append(r)
        elif blocco:
            t = "\n".join(blocco)
            for j in range(inizio, i):
                mappa[j] = t
            blocco = []
    return mappa


righe = io.open("README.md", encoding="utf-8").read().splitlines()
par = paragrafi(righe)
dentro = False
porta, non_porta, saltati = [], [], 0
for i, r in enumerate(righe):
    if r.strip().startswith("```"):
        dentro = not dentro
        continue
    if dentro:
        continue
    for _t, url in LINK.findall(r):
        path = risolvi(url)
        if not path or not os.path.exists(path) or path.endswith(SCRIPT):
            continue
        testo = par.get(i, r).lower()
        nomi = sorted({b for b in BANCHI if b in testo})
        if not nomi:
            saltati += 1
            continue
        corpo = io.open(path, encoding="utf-8", errors="replace").read().lower()
        for n in nomi:
            (porta if n in corpo else non_porta).append((i + 1, path, n))

tot = len(porta) + len(non_porta)
print(f"  rimandi a un DOCUMENTO col nome di un banco accanto : {tot}")
print(f"     il file di arrivo NOMINA quel banco              : {len(porta)}")
print(f"     NON lo nomina                                    : {len(non_porta)}")
print(f"  rimandi a documenti senza nome di banco accanto     : {saltati}")
if non_porta:
    print("\n  I RIMANDI CHE NON PORTANO ALLA FONTE:")
    for riga, path, n in non_porta:
        print(f"    README:{riga:<5} {n:<14} ->  {path}")
acceso = any(p.endswith("docs/BENCHMARKS.md") and n == "locomo" for _, p, n in non_porta)
print()
if not acceso:
    print("  CONTROLLO SPENTO: non ritrova LoCoMo -> docs/BENCHMARKS.md (W7-114)")
    print("  => i numeri sopra NON vanno usati")
    sys.exit(1)
print("  CONTROLLO ACCESO: ritrova da solo il caso noto di W7-114")
sys.exit(0)
