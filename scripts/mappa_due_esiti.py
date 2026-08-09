"""LA QUARTA MAPPA: dove il prodotto decide con due esiti e ne servirebbero tre.

PERCHE'. Il 04/08 la stessa forma e' uscita TRE VOLTE, da punti che non si
parlano fra loro:
  1. il giudice di supersessione — supporta / non-supporta, e il `neutral` di
     NLI manca: i ~30 frozenset di CONTRAST_QUALIFIERS lo surrogano a mano
     (ws4)
  2. il detector L1 — personale / software, e fra i due mondi c'e' il terzo,
     scientifico-professionale, dove nessuna guardia arrivava (ws5)
  3. gli esiti di SCRITTURA — supersede / quarantena, e manca «ammetti
     entrambi»: il caso di due entita' distinte non e' rappresentabile (io)
Tre occorrenze indipendenti non sono una coincidenza: e' il modo in cui il
prodotto pensa. Quindi conviene cercarla APPOSTA invece di aspettare che salti
fuori una quarta volta.

COSA CERCA. Le funzioni che rispondono `bool` a una domanda di CLASSIFICAZIONE
— «e' un X?», «ha Y?», «vale Z?» — nei moduli che decidono qualcosa di
irreversibile o di visibile all'utente. Un bool va benissimo per una proprieta'
davvero binaria (un file esiste o no); diventa un difetto quando la realta' ha
un terzo stato e lo si deve schiacciare su uno dei due.

⚠️ COSA NON PUO' FARE, dichiarato: questa e' una LISTA DI CANDIDATI, non un
verdetto. Come la mappa dell'ignoranza legge i docstring e non il
comportamento, questa legge le firme e non la semantica. Il lavoro vero e'
leggere ogni candidato e chiedersi: ESISTE UN CASO REALE CHE NON E' NE' SI' NE'
NO? Su questo la macchina non aiuta.
"""
from __future__ import annotations

import ast
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent

#: I moduli dove una decisione binaria ha conseguenze: ammettere, ritirare,
#: astenersi, classificare. Non tutto il prodotto — solo dove si decide.
DECISORI = ("gate", "contradiction", "supersession", "quantity_match",
            "anti_confab", "validate_claim", "trust", "relevance_floor",
            "semantic_conflict", "l1_", "admission", "grounding")

#: Prefissi di nome che indicano una DOMANDA, non un calcolo.
DOMANDE = ("is_", "has_", "_is_", "_has_", "can_", "_can_", "should_",
           "_should_", "e_", "_e_", "puo_", "_puo_", "sono_", "_sono_")


def candidati():
    fuori = []
    for f in sorted((REPO / "verimem").rglob("*.py")):
        if not any(d in f.name for d in DECISORI):
            continue
        try:
            albero = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for n in ast.walk(albero):
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            ritorno = getattr(n.returns, "id", None)
            if ritorno != "bool":
                continue
            if not any(n.name.startswith(p) or p in n.name for p in DOMANDE):
                continue
            doc = (ast.get_docstring(n) or "").split("\n")[0][:66]
            fuori.append((f.relative_to(REPO).as_posix(), n.name, n.lineno, doc))
    return fuori


def main() -> None:
    c = candidati()
    print(f"funzioni che rispondono bool a una domanda, nei moduli che "
          f"decidono: {len(c)}\n")
    per_file: dict[str, list] = {}
    for file, nome, riga, doc in c:
        per_file.setdefault(file, []).append((nome, riga, doc))
    for file in sorted(per_file):
        print(f"  {file}")
        for nome, riga, doc in sorted(per_file[file], key=lambda x: x[1]):
            print(f"     :{riga:<5} {nome:<34} {doc}")
    print("\n⚠️ Sono CANDIDATI. Il verdetto e' una lettura: per ognuno,")
    print("   ESISTE UN CASO REALE CHE NON E' NE' SI' NE' NO?")


if __name__ == "__main__":
    main()
