"""La mappa e' completa? Uguaglianza di insiemi, stampata, non un'impressione.

Aurelio, 08/09/2026 20:41: «non vi fermate finche' non avete la certezza
matematica di aver davvero guardato tutto». La certezza e' questa: l'insieme
delle funzioni e classi che stanno nel codice (ast su verimem/) deve essere
UGUALE all'insieme delle righe della mappa (docs/stato-reale/mappa/*.md);
idem per le 811 righe del README e per i file di docs/. Lo script stampa,
per owner, quante ne mancano e QUALI, e il conteggio dei verdetti.

Uso:  python scripts/mappa_completa.py [--owner ws2] [--mancanti N]
Una riga della mappa e' riconosciuta quando la seconda colonna contiene
`<file>:<riga>` e il nome qualificato (`Classe.metodo` o `funzione`), es.
| 3 | `verimem/semantic.py:1234` `SemanticMemory.store` | ... | FUNZIONA COME PROMESSO | ... |
Le righe di README-claims.md portano `README.md:<riga>`; quelle di
documenti.md portano il percorso `docs/...md`.
"""

from __future__ import annotations

import argparse
import ast
import glob
import os
import re
import sys


def _radice() -> str:
    """La radice del repo: la cwd se e' un checkout (ha verimem/ e docs/),
    altrimenti la cartella sopra lo script. Lanciato da /tmp su un albero
    vuoto stampava «mancanti 0» (ws2, 08/09 20:55): un righello che non
    trova niente deve dirlo, non dichiarare completa la mappa."""
    for cand in (os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        if os.path.isdir(os.path.join(cand, "verimem")) and os.path.isdir(
            os.path.join(cand, "docs")
        ):
            return cand
    sys.exit("mappa_completa: nessun checkout trovato (serve una cwd con verimem/ e docs/)")


RADICE = _radice()
MAPPA = os.path.join(RADICE, "docs", "stato-reale", "mappa")
VERDETTI = ("FUNZIONA COME PROMESSO", "NON COME PROMESSO", "NON MISURATO", "MAI CHIAMATA")


def funzioni_nel_codice() -> dict[str, set[str]]:
    """{file relativo: {nomi qualificati}} per ogni funzione, metodo e classe."""
    out: dict[str, set[str]] = {}
    for p in sorted(glob.glob(os.path.join(RADICE, "verimem", "**", "*.py"), recursive=True)):
        rel = os.path.relpath(p, RADICE).replace(os.sep, "/")
        try:
            albero = ast.parse(open(p, encoding="utf-8", errors="replace").read())
        except SyntaxError:
            out[rel] = {"<SyntaxError>"}
            continue
        nomi: set[str] = set()

        def visita(nodo: ast.AST, prefisso: str, nomi: set[str]) -> None:
            for figlio in ast.iter_child_nodes(nodo):
                if isinstance(figlio, ast.ClassDef):
                    nomi.add(prefisso + figlio.name)
                    visita(figlio, prefisso + figlio.name + ".", nomi)
                elif isinstance(figlio, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nomi.add(prefisso + figlio.name)
                    visita(figlio, prefisso + figlio.name + ".", nomi)
                else:
                    visita(figlio, prefisso, nomi)

        visita(albero, "", nomi)
        out[rel] = nomi
    return out


def owner_per_file() -> dict[str, str]:
    """Dall'indice: | `file` | righe | funzioni | owner | stato |."""
    indice = os.path.join(MAPPA, "00-INDICE.md")
    own: dict[str, str] = {}
    if not os.path.exists(indice):
        return own
    for riga in open(indice, encoding="utf-8"):
        m = re.match(r"\|\s*`([^`]+)`\s*\|[^|]*\|[^|]*\|\s*(\w+)\s*\|", riga)
        if m:
            own[m.group(1)] = m.group(2)
    return own


RIGA_FUNZIONE = re.compile(r"`(verimem/[^`:]+\.py):(\d+)`\s*`([^`]+)`")
#: la forma senza riga di codice: `| n | `Nome` |` (ws6, ws8); conta solo se
#: il nome esiste nel modulo che dà il nome al file .md
RIGA_NOME = re.compile(
    r"^\|\s*(?:\d+\s*\|\s*)?\**`([A-Za-z_][\w.]*)(?:\([^`]*\))?`")
SENZA_RIGA = [0]
#: la forma di ws8: `### `verimem/swarm/` — 33 funzioni` sopra, e sotto
#: `| n | `nome(args)` | `file.py` | ...`
INTESTAZIONE_PKG = re.compile(r"`(verimem/[^`]+?)/?`")
RIGA_PKG = re.compile(
    r"^\|\s*\d+\s*\|\s*`([A-Za-z_][\w.]*)(?:\([^`]*\))?`\s*\|\s*`((?:[\w.-]+/)*[\w.-]+\.py)`")
RIGA_README = re.compile(r"`README\.md:(\d+)`")
RIGA_DOC = re.compile(r"`(docs/[^`]+\.md)`")


def righe_della_mappa() -> tuple[dict[str, set[str]], set[int], set[str], dict[str, int]]:
    mappate: dict[str, set[str]] = {}
    readme: set[int] = set()
    docs: set[str] = set()
    verdetti = {v: 0 for v in VERDETTI}
    for md in glob.glob(os.path.join(MAPPA, "*.md")):
        nome = os.path.basename(md)
        pacchetto = ""
        for riga in open(md, encoding="utf-8", errors="replace"):
            if riga.startswith("#"):
                # la forma di ws8 (funzioni.md): l'intestazione dice il
                # pacchetto (`verimem/swarm/`), la terza colonna il file
                mh = INTESTAZIONE_PKG.search(riga)
                pacchetto = mh.group(1) if mh else pacchetto
                continue
            if not riga.startswith("|"):
                continue
            if nome not in ("README-claims.md", "documenti.md", "00-INDICE.md"):
                mp = RIGA_PKG.match(riga)
                # la terza colonna puo' portare il file nudo (`bridge.py`, il
                # pacchetto viene dall'intestazione) o il percorso dentro
                # verimem (`teams/inbox.py`): nel secondo caso l'intestazione
                # non serve
                if mp and (pacchetto or "/" in mp.group(2)):
                    modulo = ("verimem/" + mp.group(2) if "/" in mp.group(2)
                              else pacchetto + "/" + mp.group(2))
                    mappate.setdefault(modulo, set()).add(mp.group(1))
                    SENZA_RIGA[0] += 1
                    for v in VERDETTI:
                        if v in riga:
                            verdetti[v] += 1
                            break
                    continue
            if nome == "README-claims.md":
                for m in RIGA_README.finditer(riga):
                    readme.add(int(m.group(1)))
                # la forma di ws7: la PRIMA colonna e' la riga del README, o un
                # intervallo `A-B` (tutte le righe dell'intervallo contano)
                m3 = re.match(r"^\|\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*\|", riga)
                if m3:
                    a_, b_ = int(m3.group(1)), int(m3.group(2) or m3.group(1))
                    if b_ >= a_ and b_ - a_ < 811:
                        readme.update(range(a_, b_ + 1))
                # i verdetti a simbolo di ws7 contano come i nostri
                if "✅" in riga:
                    verdetti["FUNZIONA COME PROMESSO"] += 1
                    continue
                if "❌" in riga:
                    verdetti["NON COME PROMESSO"] += 1
                    continue
                if "⬜" in riga:
                    verdetti["NON MISURATO"] += 1
                    continue
            elif nome == "documenti.md":
                for m in RIGA_DOC.finditer(riga):
                    docs.add(m.group(1))
            elif nome != "00-INDICE.md":
                trovata = False
                for m in RIGA_FUNZIONE.finditer(riga):
                    mappate.setdefault(m.group(1), set()).add(m.group(3))
                    trovata = True
                if not trovata:
                    # Riga SENZA `verimem/f.py:riga`: il nome nella seconda
                    # colonna vale per il modulo che dà il nome al file
                    # (consolidation.md -> verimem/consolidation.py,
                    # dashboard_routes-settings.md -> verimem/dashboard_routes/
                    # settings.py). Il nome deve esistere nel modulo per contare:
                    # l'uguaglianza di insiemi resta quella. Le righe così
                    # contate sono stampate a parte (`senza riga di codice`).
                    m2 = RIGA_NOME.match(riga)
                    if m2:
                        modulo = "verimem/" + nome[:-3].replace("-", "/") + ".py"
                        mappate.setdefault(modulo, set()).add(m2.group(1))
                        SENZA_RIGA[0] += 1
            for v in VERDETTI:
                if v in riga:
                    verdetti[v] += 1
                    break
    return mappate, readme, docs, verdetti


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", help="stampa solo questo owner")
    ap.add_argument(
        "--mancanti", type=int, default=15, help="quante funzioni mancanti elencare per file"
    )
    a = ap.parse_args()
    codice = funzioni_nel_codice()
    if sum(len(v) for v in codice.values()) == 0:
        sys.exit(
            f"mappa_completa: nessuna funzione trovata sotto {RADICE}/verimem: radice sbagliata, non una mappa completa"
        )
    own = owner_per_file()
    mappate, readme, docs, verdetti = righe_della_mappa()

    per_owner: dict[str, list[int]] = {}
    mancanti_per_file: dict[str, set[str]] = {}
    estranee: dict[str, set[str]] = {}
    for rel, nomi in codice.items():
        o = own.get(rel, "?")
        fatte = mappate.get(rel, set())
        # un nome NUDO nella mappa (`store`) copre il metodo qualificato del
        # codice (`SemanticMemory.store`): la forma di ws6. Se due classi
        # dello stesso modulo hanno un metodo omonimo, il nome nudo li copre
        # entrambi (sovraconteggio dichiarato, non nascosto).
        fatte_eff = set(fatte)
        for n in nomi:
            if n not in fatte_eff and "." in n and n.rsplit(".", 1)[1] in fatte:
                fatte_eff.add(n)
        fatte = fatte_eff
        manc = nomi - fatte
        extra = fatte - nomi
        if manc:
            mancanti_per_file[rel] = manc
        if extra:
            estranee[rel] = extra
        t = per_owner.setdefault(o, [0, 0])
        t[0] += len(nomi)
        t[1] += len(nomi & fatte)

    print("== FUNZIONI E CLASSI: nel codice contro nella mappa ==")
    tot_c = tot_m = 0
    for o in sorted(per_owner):
        if a.owner and o != a.owner:
            continue
        c, m = per_owner[o]
        tot_c += c
        tot_m += m
        print(f"  {o:5}  mappate {m:5} / {c:5}   mancanti {c - m:5}")
    print(f"  TUTTE  mappate {tot_m:5} / {tot_c:5}   mancanti {tot_c - tot_m:5}")
    print(f"  (righe contate SENZA `verimem/f.py:riga`, per nome del file: {SENZA_RIGA[0]})")
    if estranee:
        print(
            f"  righe della mappa che NON corrispondono a nessuna funzione del codice: {sum(len(v) for v in estranee.values())}"
        )
        for rel, s in sorted(estranee.items())[:10]:
            print(f"    {rel}: {sorted(s)[:5]}")
    print(f"== CHI MANCA, per file (prime {a.mancanti}) ==")
    for rel, s in sorted(mancanti_per_file.items(), key=lambda kv: -len(kv[1])):
        if a.owner and own.get(rel, "?") != a.owner:
            continue
        print(f"  {own.get(rel, '?'):5} {rel}: {len(s)} mancanti  {sorted(s)[: a.mancanti]}")
    # Le righe del README che possono portare un claim: non vuote, non
    # recinzioni di codice, non separatori di tabella o righe orizzontali.
    # Le altre (116 su 811 al tip 20257636) non promettono niente a nessuno,
    # e contarle come «scoperte» farebbe dire NON COMPLETA a una mappa
    # completa; sono stampate a parte, cosi' chi legge sa cosa e' escluso.
    righe_readme = open(os.path.join(RADICE, "README.md"), encoding="utf-8").read().splitlines()
    dentro_codice = False
    portano_claim: set[int] = set()
    for i, r in enumerate(righe_readme, 1):
        s = r.strip()
        if s.startswith("```") or s.startswith("> ```"):
            dentro_codice = not dentro_codice
            continue
        if dentro_codice or not s or s in ("---", "***", ">") or re.fullmatch(r"\|?[\s:|-]+\|?", s):
            continue
        if s.startswith("#"):
            continue  # un titolo di sezione non promette niente
        # riga di intestazione di una tabella: la riga dopo e' il separatore
        nxt = righe_readme[i].strip() if i < len(righe_readme) else ""
        if s.startswith("|") and re.fullmatch(r"\|?[\s:|-]+\|?", nxt):
            continue
        portano_claim.add(i)
    # una riga di CONTINUAZIONE (comincia con minuscola o con un backtick, e non
    # e' un elenco) appartiene al claim della riga precedente: se quella e'
    # collegata, lo e' anche questa
    for i in sorted(portano_claim):
        s = righe_readme[i - 1].strip()
        if i - 1 in readme and i not in readme and re.match(r"[a-z`(]", s):
            readme.add(i)
    n_readme = len(portano_claim)
    readme = readme & portano_claim
    print(f"== README: righe che portano un claim {n_readme} / {len(righe_readme)} "
          f"(escluse {len(righe_readme) - n_readme}: vuote, codice, separatori) ==")
    # la mappa stessa non e' un documento da classificare: senza questa
    # esclusione il denominatore cresce a ogni file di mappa scritto
    n_docs = len([p for p in glob.glob(os.path.join(RADICE, "docs", "**", "*.md"), recursive=True)
                  if os.sep + "mappa" + os.sep not in p and "/mappa/" not in p])
    print("== README ==")
    print(f"  righe collegate {len(readme)} / {n_readme}   mancanti {n_readme - len(readme)}")
    print("== DOCUMENTI ==")
    print(f"  classificati {len(docs)} / {n_docs}   mancanti {n_docs - len(docs)}")
    print("== VERDETTI ==")
    for v, n in verdetti.items():
        print(f"  {v:24} {n}")
    # COMPLETA = uguaglianza di insiemi su funzioni, righe del README che
    # portano un claim e documenti. Le righe «estranee» (una tabella
    # esplicativa che nomina L1.10, una regola del gate, non una funzione:
    # ws5, 09/09 13:26) sono stampate sopra e non fermano il verdetto: sono
    # informazione in piu', non copertura in meno.
    completa = (
        (tot_c - tot_m == 0)
        and (n_readme - len(readme) == 0)
        and (n_docs - len(docs) == 0)
    )
    print("COMPLETA" if completa else "NON COMPLETA")
    return 0 if completa else 1


if __name__ == "__main__":
    sys.exit(main())
