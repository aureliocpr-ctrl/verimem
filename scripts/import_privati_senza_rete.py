"""Chi importa un nome PRIVATO di un altro modulo, e senza rete sotto.

Nato da un rilievo di @ws3 su una PR che **io avevo approvato**
(PR #16, 2026-09-10): `hooks/pre_tool_use._marchio` fa
`from ..semantic import _rango_di_fiducia`, e il chiamante sta fuori dal `try`
di `run()`. Se quel nome cambia, l'hook esce con `ImportError` su **ogni tool
call**, mentre il suo docstring promette «Returns 0 on every path so the hook
never blocks a tool call». Lui l'ha provato con un A/B a una variabile sola; il
mio metro di revisione **non faceva questa domanda**, e infatti non l'ho vista.

Il righello la fa per tutte le PR future, e la fa su tutto il pacchetto: un
rilievo singolo diventa una classe contata.

Che cosa cerca — un import che ha TUTTE E TRE queste proprieta':
  1. e' `from <altro modulo> import _nome` (il nome comincia con `_`);
  2. il modulo di partenza e' un ALTRO file del pacchetto (non `from . import`
     di se' stesso): il contratto fra i due non e' pubblico e nessuno lo
     sorveglia;
  3. **non e' dentro un `try`** — ne' l'import, ne' la funzione che lo contiene
     ha un `try` che lo copra.

⚠️ QUESTO NON E' UN ELENCO DI DIFETTI. Un import privato dentro lo stesso
pacchetto e' normale e spesso giusto. Diventa un difetto quando sta su un
percorso che PROMETTE di non fallire (un hook, un banner, un fallback). La
colonna «promette di non fallire?» il righello non la sa: la legge una persona.
Per questo stampa i nomi e non un verdetto.

Uso:
    PYTHONPATH=. python scripts/import_privati_senza_rete.py
    PYTHONPATH=. python scripts/import_privati_senza_rete.py --autotest
    PYTHONPATH=. python scripts/import_privati_senza_rete.py --solo verimem/hooks
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys

RADICE = pathlib.Path(__file__).resolve().parent.parent


def _dentro_try(albero: ast.AST) -> set[int]:
    """id() di ogni nodo che sta sotto un `try` (nel body, non nell'handler)."""
    protetti: set[int] = set()
    for n in ast.walk(albero):
        if isinstance(n, ast.Try):
            for ramo in n.body:
                for figlio in ast.walk(ramo):
                    protetti.add(id(figlio))
    return protetti


def _funzione_contenitrice(albero: ast.AST) -> dict[int, ast.FunctionDef]:
    dentro: dict[int, ast.FunctionDef] = {}
    for n in ast.walk(albero):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for figlio in ast.walk(n):
                dentro.setdefault(id(figlio), n)
    return dentro


#: Le parole con cui un percorso PROMETTE di non fallire. Un import nudo su un
#: percorso cosi' non e' «uno dei 64»: e' una promessa che il codice non puo'
#: piu' mantenere. La lista e' volutamente corta e letterale — allargarla
#: farebbe salire il numero senza che nessuno abbia letto le righe nuove.
#: ⚠️ LA v1 DI QUESTA LISTA CERCAVA «never» DA SOLO, e nel docstring del MODULO:
#:    prendeva «almost never before», «the detectors just never use meaning»,
#:    «never become a back-door asymmetry» — prosa, non promesse. Nove righe su
#:    nove erano rumore, e il numero saliva **a favore del mio reperto**: la
#:    nona volta oggi che il mio strumento pende dalla stessa parte.
#:    Ora: solo frasi che promettono sul FALLIMENTO, e solo nel docstring della
#:    FUNZIONE che contiene l'import — quello del modulo e' prosa lunga.
_PROMESSE = (
    "never raises", "never fails", "never throws", "never blocks",
    "always returns", "on every path", "cannot fail", "does not raise",
    "best-effort", "best effort", "fail-open", "non solleva", "non blocca",
)


def _promette_di_non_fallire(albero: ast.AST, funzione: ast.AST | None) -> str | None:
    """La promessa sul FALLIMENTO, nel docstring della funzione che importa.

    Non guarda il docstring del modulo: li' «never» compare nella prosa e non
    promette niente sul comportamento di questa riga.
    """
    if funzione is None:
        return None
    for riga in (ast.get_docstring(funzione) or "").splitlines():
        basso = riga.lower()
        for parola in _PROMESSE:
            if parola in basso:
                return riga.strip()
    return None


def trova(radice: pathlib.Path, solo: str | None = None) -> list[dict]:
    fuori: list[dict] = []
    for p in sorted((radice / "verimem").rglob("*.py")):
        rel = p.relative_to(radice).as_posix()
        if solo and not rel.startswith(solo):
            continue
        try:
            albero = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        protetti = _dentro_try(albero)
        contenitrice = _funzione_contenitrice(albero)

        for n in ast.walk(albero):
            if not isinstance(n, ast.ImportFrom):
                continue
            #: `from . import x` (livello 1 senza modulo) e' il proprio package
            if n.level == 0 or not n.module:
                continue
            privati = [a.name for a in n.names if a.name.startswith("_")]
            if not privati:
                continue
            f = contenitrice.get(id(n))
            fuori.append({
                "file": rel, "riga": n.lineno,
                "da": ("." * n.level) + n.module,
                "nomi": privati,
                "protetto": id(n) in protetti,
                "funzione": f.name if f else "<modulo>",
                "promessa": _promette_di_non_fallire(albero, f),
            })
    return fuori


def autotest() -> int:
    """La domanda che deve poter fallire: il righello vede la rete quando c'e'?"""
    casi = [
        ("A  import privato NUDO           → deve comparire",
         "from ..semantic import _rango_di_fiducia\n", 1),
        ("B  lo stesso dentro un try       → NON deve comparire",
         "try:\n    from ..semantic import _rango_di_fiducia\nexcept ImportError:\n    pass\n", 0),
        ("C  import PUBBLICO               → NON deve comparire",
         "from ..semantic import rango_di_fiducia\n", 0),
        ("D  import privato dal proprio package (`from . import _x`)",
         "from . import _x\n", 0),
    ]
    esito = 0
    print("== AUTOTEST ==")
    tmp = RADICE / "verimem" / "_autotest_ws1_tmp.py"
    for nome, sorgente, attesi in casi:
        tmp.write_text(sorgente, encoding="utf-8")
        try:
            # ⚠️ la v1 di QUESTO autotest contava TUTTI i trovati, e il caso B
            #    (import dentro un `try`) risultava rosso: il righello lo vedeva
            #    protetto, ero io a contare la colonna sbagliata. Un autotest
            #    puo' fallire per un difetto suo: si legge quale dei due parla.
            n = len([r for r in trova(RADICE)
                     if r["file"].endswith("_autotest_ws1_tmp.py") and not r["protetto"]])
        finally:
            tmp.unlink(missing_ok=True)
        ok = n == attesi
        print(f"  {'OK ' if ok else '🔴 '} {nome:52s} trovati {n}, attesi {attesi}")
        esito |= 0 if ok else 1
    print("\n  AUTOTEST VERDE: distingue la rete dall'assenza di rete."
          if esito == 0 else "\n  🔴 AUTOTEST ROSSO.")
    return esito


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--autotest", action="store_true")
    ap.add_argument("--solo", help="restringe a un prefisso di percorso")
    ap.add_argument("--promesse", action="store_true",
                    help="solo quelli su un percorso che PROMETTE di non fallire")
    args = ap.parse_args()
    if args.autotest:
        return autotest()

    trovati = trova(RADICE, args.solo)
    nudi = [r for r in trovati if not r["protetto"]]
    print(f"== import di nomi PRIVATI da un altro modulo: {len(trovati)} "
          f"({len(nudi)} senza un `try` sopra) ==\n")
    print("⚠️  NON e' un elenco di difetti: lo diventa dove il percorso PROMETTE")
    print("    di non fallire (un hook, un banner, un ripiego). Quella colonna")
    print("    la legge una persona.\n")
    if args.promesse:
        nudi = [r for r in nudi if r["promessa"]]
        print(f"   → di cui su un percorso che PROMETTE di non fallire: {len(nudi)}\n")
    for r in sorted(nudi, key=lambda x: (x["file"], x["riga"])):
        print(f"  {r['file']}:{r['riga']:<6d} in `{r['funzione']}`")
        print(f"      from {r['da']} import {', '.join(r['nomi'])}")
        if r["promessa"]:
            print(f"      🔴 promette: «{r['promessa'][:88]}»")
    if not nudi:
        print("  (nessuno)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
