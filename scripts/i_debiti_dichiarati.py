"""I marcatori `xfail` e `skip` del repo: quanti dicono PERCHE', e quanti no.

Nato la sera del 2026-09-10, quando la decisione D-1 sul rosso di T38 ha
aggiunto un `xfail` al riepilogo di `main`. Il riepilogo diceva gia':

    1 failed, 12848 passed, 44 skipped, 40 deselected, 131 xfailed

131 esecuzioni marcate, e nessuno sapeva quali fossero. Un `xfail` e' un debito
con un contratto: «questo non funziona, e lo sappiamo». Un `xfail` **senza
`reason`** e' un debito senza contratto — dice che qualcosa non va e non dice
cosa, e nessuno potra' mai decidere se e' ora di toglierlo.

📊 LA RISPOSTA, il 10/09, e ha SMENTITO il sospetto che mi aveva fatto scrivere
questo righello: **52 marcatori, tutti con `reason`, tutti `strict=True`**. Zero
anonimi, zero non-strict. (I 131 del riepilogo sono le ESECUZIONI: un marcatore
su una classe o su una `parametrize` conta piu' volte a runtime.) La disciplina
c'era ed era al 100% — e la quarantena di T38 decisa quella sera introduce **il
primo `xfail` non strict del repo**. Il righello resta per poterlo rileggere.

Tre cose che il righello distingue, perche' hanno significati diversi:
  · `strict=True`   il difetto e' DETERMINISTICO: il giorno che la cura entra,
                    il test diventa rosso e costringe a togliere il marcatore.
  · `strict=False`  il difetto e' una GARA o dipende dall'ambiente: e' l'unica
                    scelta possibile quando il test a volte passa — ma non
                    avvisa nessuno quando la cura arriva.
  · senza `reason`  il debito non dice cosa lo giustifica.

⚠️ NON e' un elenco di difetti: un `xfail` motivato e' buona pratica. E'
l'elenco dei debiti, e serve a poterli rileggere.

Uso:
    PYTHONPATH=. python scripts/i_debiti_dichiarati.py
    PYTHONPATH=. python scripts/i_debiti_dichiarati.py --senza-motivo
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys

RADICE = pathlib.Path(__file__).resolve().parent.parent


def _e_marcatore(nodo: ast.AST) -> str | None:
    """`@pytest.mark.xfail(...)` → 'xfail'; `@pytest.mark.skip` → 'skip'."""
    bersaglio = nodo.func if isinstance(nodo, ast.Call) else nodo
    if isinstance(bersaglio, ast.Attribute) and bersaglio.attr in ("xfail", "skip", "skipif"):
        return bersaglio.attr
    return None


def raccogli(cartella: pathlib.Path) -> list[dict]:
    fuori: list[dict] = []
    for p in sorted(cartella.rglob("test_*.py")):
        try:
            albero = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        rel = p.relative_to(RADICE).as_posix()
        for n in ast.walk(albero):
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for deco in n.decorator_list:
                tipo = _e_marcatore(deco)
                if tipo is None:
                    continue
                strict = None
                motivo = None
                if isinstance(deco, ast.Call):
                    for kw in deco.keywords:
                        if kw.arg == "strict" and isinstance(kw.value, ast.Constant):
                            strict = bool(kw.value.value)
                        if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
                            motivo = str(kw.value.value)
                    #: `xfail("motivo")` posizionale
                    if motivo is None and deco.args:
                        a = deco.args[-1]
                        if isinstance(a, ast.Constant) and isinstance(a.value, str):
                            motivo = a.value
                fuori.append({"file": rel, "riga": n.lineno, "nome": n.name,
                              "tipo": tipo, "strict": strict, "motivo": motivo})
    return fuori


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--senza-motivo", action="store_true",
                    help="solo i debiti che non dicono perche'")
    args = ap.parse_args()

    tutti = raccogli(RADICE / "tests")
    xfail = [d for d in tutti if d["tipo"] == "xfail"]
    senza = [d for d in xfail if not d["motivo"]]
    strict_si = [d for d in xfail if d["strict"] is True]
    strict_no = [d for d in xfail if d["strict"] is False]
    strict_muto = [d for d in xfail if d["strict"] is None]

    if args.senza_motivo:
        print(f"== {len(senza)} `xfail` che NON dicono perche' ==\n")
        for d in senza:
            print(f"   {d['file']}:{d['riga']}  {d['nome'][:56]}")
        return 1 if senza else 0

    print(f"== marcatori nei test: {len(tutti)}  "
          f"(xfail {len(xfail)} · skip/skipif {len(tutti) - len(xfail)}) ==\n")
    print(f"   con un `reason`          {len(xfail) - len(senza):4d}")
    print(f"   SENZA `reason`           {len(senza):4d}   ← debito senza contratto")
    print()
    print(f"   strict=True              {len(strict_si):4d}   il difetto e' deterministico:"
          f" avvisa quando la cura entra")
    print(f"   strict=False             {len(strict_no):4d}   una gara o l'ambiente:"
          f" non avvisera' mai")
    print(f"   strict non detto         {len(strict_muto):4d}   prende il default"
          f" (`xfail_strict` in pyproject, altrimenti False)")
    if senza:
        print("\n   i primi senza motivo (tutti con --senza-motivo):")
        for d in senza[:8]:
            print(f"      {d['file']}:{d['riga']}  {d['nome'][:52]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
