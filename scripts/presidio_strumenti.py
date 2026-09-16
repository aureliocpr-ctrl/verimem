"""Ogni strumento MCP: c'e' un test che lo INVOCA, o solo che lo nomina?

    python scripts/presidio_strumenti.py [--tsv percorso.tsv]

Legge e basta: AST sul sorgente e sui test, nessuna esecuzione del prodotto.

═══ PERCHE' QUESTO FILE ESISTE ═══

La prima versione cercava le invocazioni con CINQUE regex, una per ogni forma
che il suo autore conosceva, e dava «42 invocati, 207 solo nominati». Il numero
era falso al ribasso di 67. A smascherarlo e' stata UNA RIGA non credibile
della lista — `hippo_audit_tail`, 11 occorrenze nei test, «mai invocato»:

    tests/test_mcp_export_import_test_audit.py:297
        blocks = await _invoke_tool("hippo_audit_tail", {"n": 3})

`_invoke_tool` era la sesta forma, e i dati dicono che e' la piu' usata del
repo (286 chiamate contro le 6 di `_call_tool_impl`, che era la prima delle
cinque regex).

⚠️ IL CONTROLLO POSITIVO ERA PASSATO LO STESSO, 3 su 3 — perche' i tre tool
scelti erano quelli dei banchi dell'autore, e quei banchi usano le forme che
l'autore aveva scritto. Un controllo positivo pescato dal proprio lavoro non
controlla niente: conferma che il righello vede cio' che gia' sapevi.

Da qui le tre regole di questo file, che valgono per qualunque censimento:

  ① NON SI CERCANO LE FORME NOTE, SI CERCANO I NOMI. Qualunque chiamata che
    riceve un nome-di-tool come stringa (posizionale, o kwarg name/tool/
    tool_name) conta, e i wrapper escono DAI DATI — il programma li stampa.
    Cosi' il righello non puo' piu' mancare una forma che non conosceva.
  ② IL CONTROLLO POSITIVO CONTIENE IL CASO CHE HA ROTTO LA VERSIONE PRIMA,
    non casi scelti dal proprio lavoro.
  ③ E UN CONTROLLO NEGATIVO: un nome inventato NON deve mai risultare
    invocato. Senza, «piu' largo» e' indistinguibile da «piu' giusto», ed e'
    il difetto che il controllo positivo da solo non vede mai: passa MEGLIO
    quanto piu' il criterio e' largo.

Il grep serve a TROVARE, mai a CONTARE: un nome dentro un docstring, dentro
una proposizione piu' lunga o dentro un commento non e' un'invocazione.
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import Counter, defaultdict
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]

#: Devono risultare INVOCATI. Il primo e' il caso che ha rotto la v1.
CONTROLLO_POSITIVO = (
    "hippo_audit_tail",
    "hippo_oracle_query",
    "hippo_quarantine_restore",
    "hippo_fact_forget",
)

#: NON deve risultare invocato: se ci finisce, il criterio marca qualunque
#: stringa e il numero degli invocati e' gonfio.
CONTROLLO_NEGATIVO = "hippo_questo_strumento_non_esiste"

#: Un file che tocca tanti strumenti diversi non li presidia: li spazza.
#: «Invocato» e «presidiato» non sono la stessa cosa, e il totale lo nasconde.
SOGLIA_SPAZZATA = 20


def strumenti_dichiarati() -> list[str]:
    """I nomi dall'AST di `mcp_server.py`: un `Tool(name="…")` e' una chiamata
    con un keyword `name`, cosi' un nome scritto in un commento non entra."""
    sorgente = (RADICE / "verimem" / "mcp_server.py").read_text(
        encoding="utf-8", errors="replace")
    fuori: list[str] = []
    for nodo in ast.walk(ast.parse(sorgente)):
        if not isinstance(nodo, ast.Call):
            continue
        if (getattr(nodo.func, "attr", None)
                or getattr(nodo.func, "id", None)) != "Tool":
            continue
        for kw in nodo.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                fuori.append(str(kw.value.value))
    return fuori


def _stringhe_passate(chiamata: ast.Call) -> list[str]:
    """Le stringhe che la chiamata riceve come NOME di qualcosa."""
    fuori = [a.value for a in chiamata.args
             if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    fuori += [k.value.value for k in chiamata.keywords
              if k.arg in ("name", "tool", "tool_name")
              and isinstance(k.value, ast.Constant)
              and isinstance(k.value.value, str)]
    return fuori


def invocazioni(nomi: set[str]) -> tuple[dict[str, set[str]],
                                         dict[str, set[str]], Counter]:
    """(tool -> file che lo invocano, file -> tool che tocca, censimento
    dei wrapper). I wrapper non sono una lista scritta a mano: escono dai
    dati, e il chiamante li stampa."""
    dove: dict[str, set[str]] = defaultdict(set)
    per_file: dict[str, set[str]] = defaultdict(set)
    wrapper: Counter = Counter()
    for f in sorted((RADICE / "tests").rglob("*.py")):
        if "__pycache__" in str(f):
            continue
        try:
            albero = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.Call):
                continue
            chi = (getattr(nodo.func, "attr", None)
                   or getattr(nodo.func, "id", None) or "?")
            for s in _stringhe_passate(nodo):
                if s in nomi:
                    dove[s].add(f.name)
                    per_file[f.name].add(s)
                    wrapper[chi] += 1
    return dove, per_file, wrapper


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tsv", type=Path, default=None,
                    help="scrive la lista per strumento in questo file")
    args = ap.parse_args(argv)

    dichiarati = strumenti_dichiarati()
    unici = sorted(set(dichiarati))
    print(f"strumenti dichiarati (AST, Tool(name=…)): {len(dichiarati)} "
          f"· nomi UNICI: {len(unici)}")
    if len(dichiarati) != len(unici):
        doppi = [n for n, c in Counter(dichiarati).items() if c > 1]
        print(f"  ⚠️ dichiarati PIU' DI UNA VOLTA: {doppi}")

    invocati, per_file, wrapper = invocazioni(
        set(unici) | {CONTROLLO_NEGATIVO})

    # ── i due controlli, PRIMA di stampare qualunque numero ──
    rotti = [t for t in CONTROLLO_POSITIVO if t not in invocati]
    if rotti:
        print(f"\n🔴 RIGHELLO ROTTO: {rotti} risultano NON invocati, e sono "
              f"invocati. Il conteggio sotto non vale niente.", file=sys.stderr)
        return 1
    if CONTROLLO_NEGATIVO in invocati:
        print(f"\n🔴 RIGHELLO TROPPO LARGO: {CONTROLLO_NEGATIVO} risulta "
              f"invocato: marca qualunque stringa.", file=sys.stderr)
        return 1
    print(f"✅ controllo positivo {len(CONTROLLO_POSITIVO)}/"
          f"{len(CONTROLLO_POSITIVO)} · controllo negativo: non invocato")

    print("\n=== I WRAPPER, COME ESCONO DAI DATI ===")
    for chi, quante in wrapper.most_common(8):
        print(f"  {chi:26s} {quante:5d}")

    spazzate = {f for f, t in per_file.items() if len(t) >= SOGLIA_SPAZZATA}
    solo_spazzata = [t for t, fs in invocati.items()
                     if t in set(unici) and fs and fs <= spazzate]
    presidiati = [n for n in unici if n in invocati]
    print(f"\n{'INVOCATI da almeno un test':36s} {len(presidiati):4d}")
    print(f"{'  di cui SOLO dentro una spazzata':36s} "
          f"{len(solo_spazzata):4d}   ({', '.join(sorted(spazzate)) or '—'})")
    print(f"{'  invocati da un file MIRATO':36s} "
          f"{len(presidiati) - len(solo_spazzata):4d}")
    print(f"{'MAI invocati':36s} {len(unici) - len(presidiati):4d}")
    print(f"{'TOTALE':36s} {len(unici):4d}")
    print(f"\n⇒ SENZA UN TEST MIRATO: "
          f"{len(unici) - len(presidiati) + len(solo_spazzata)} su {len(unici)}")

    # Le famiglie contano piu' del totale: 140 nomi sono un muro, «queste
    # famiglie sono scoperte» e' un piano di lavoro.
    fam_tot: Counter = Counter()
    fam_sco: Counter = Counter()
    for n in unici:
        chiave = "_".join(n.split("_")[:2])
        fam_tot[chiave] += 1
        if n not in invocati:
            fam_sco[chiave] += 1
    print("\n=== LE FAMIGLIE PIU' SCOPERTE (scoperti/totale) ===")
    for chiave, quanti in sorted(
            fam_sco.items(), key=lambda kv: (-kv[1], kv[0]))[:12]:
        intera = "  ← famiglia INTERA" if quanti == fam_tot[chiave] else ""
        print(f"  {chiave:24s} {quanti:3d}/{fam_tot[chiave]:<3d}{intera}")

    if args.tsv:
        with args.tsv.open("w", encoding="utf-8") as fh:
            fh.write("strumento\tstato\tquanti_file\tfile_che_lo_invocano\n")
            for n in unici:
                f = sorted(invocati.get(n, ()))
                if not f:
                    stato = "SCOPERTO"
                elif n in solo_spazzata:
                    stato = "SOLO SPAZZATA"
                else:
                    stato = "INVOCATO"
                fh.write(f"{n}\t{stato}\t{len(f)}\t{';'.join(f[:3])}\n")
        print(f"\nlista per strumento: {args.tsv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
