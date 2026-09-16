#!/usr/bin/env python3
"""Il cricchetto dei moduli senza porta (regola R2: aggiunta zero senza porta).

Un modulo che nessuno importa e che nessuna porta lancia è codice pubblicato che
l'utente non può raggiungere: paga il download, la superficie di attacco e la
manutenzione, e non riceve niente. Il numero non deve salire.

    python scripts/senza_chiamante.py              # verdetto, uscita 0/1
    python scripts/senza_chiamante.py --dettaglio  # anche le classi B e C1 per esteso
    python scripts/senza_chiamante.py --autotest   # prova che il cricchetto morde

QUATTRO CLASSI, NON UN NUMERO SOLO — perché «senza chiamante» significa cose
diverse e sommarle nasconde proprio la distinzione che serve:

  A  importato da un altro modulo del pacchetto          -> ha una porta interna
  B  non importato, ma dichiarato in [project.scripts]   -> È una porta (la CLI)
  C1 non importato, senza entry point, ma con
     `if __name__ == "__main__"`                          -> solo `python -m verimem.x`
  C2 non importato, nessun entry point, nessun __main__   -> NESSUNA PORTA

Il tetto sta su **C2**: è la classe che l'utente paga e non può usare. C1 è
contata a parte perché `python -m` è una porta che il README non insegna e
nessun test invoca: sorvegliata, non conteggiata nel tetto.

COSA CONTA COME IMPORT — il criterio, che vale quanto il numero:
  * `import verimem.x` / `from verimem.x import ...` / `from verimem import x`
  * `from . import x` / `from .x import ...` (anche annidati, col livello giusto)
  * `importlib.import_module("verimem.x")` col nome scritto come stringa letterale
NON conta:
  * un import fatto dai TEST — il criterio è «raggiungibile dal PRODOTTO»: un
    modulo con il test verde e nessuna porta resta senza porta (misurato più
    volte in casa)
  * il proprio import di sé stesso
  * un nome costruito a runtime (`import_module(f"verimem.{nome}")`): questo
    script NON può vederlo. Per questo stampa i NOMI e non solo la cifra — chi
    legge deve poter controllare uno per uno.

IL NUMERO DEL RESOCONTO È 19, QUESTO SCRIPT NE CONTA DI PIÙ: sono due criteri
diversi. Il 19 del RESOCONTO §3 sono i «moduli interi senza chiamante nel
pacchetto pubblicato» scelti leggendoli; questo conta ogni file .py del
pacchetto, banchi e adattatori di laboratorio compresi. Il tetto qui sotto è il
numero di QUESTO criterio, misurato il 09/09/2026 sul tip 20257636. Se
l'agenzia decide di togliere i banchi dal pacchetto pubblicato, il numero scende
e il tetto va abbassato nello stesso commit.

COME SI ABBASSA IL TETTO: quando un modulo viene cablato a una porta o spostato
fuori dal pacchetto, si abbassa QUI, a mano. Non esiste un `--aggiorna`: un
cricchetto che si ripara da solo non morde.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys
from collections import defaultdict

RADICE = pathlib.Path(__file__).resolve().parent.parent
PACCHETTO = RADICE / "verimem"
PYPROJECT = RADICE / "pyproject.toml"

TETTO_C2 = 35          # nessuna porta: né import, né entry point, né python -m
TETTO_C1 = 5           # raggiungibili solo con `python -m` (sorvegliati, non nel tetto)
TETTO_D = 62           # irraggiungibili da ogni porta, chiusura transitiva (35 C2 + 5 C1 + 22 solo-per-catena)

# `__init__` è l'ingresso del pacchetto e `__main__` è ciò che `python -m verimem` lancia:
# non sono moduli senza porta, sono la porta.
ESCLUSI = {"__init__", "__main__"}


def _nome_modulo(percorso: pathlib.Path, pacchetto: pathlib.Path) -> str:
    """`verimem/a/b.py` -> `a.b`; `verimem/a/__init__.py` -> `a` (il PACCHETTO).

    L'`__init__` di un sottopacchetto si chiama col nome del pacchetto, non
    `a.__init__`: chi scrive `from .a import b` importa `a`, e un grafo che
    tenesse i due nomi separati direbbe che nessuno importa `a.__init__`.
    Costato una misura sbagliata il 09/09: `dashboard_routes` risultava
    irraggiungibile mentre `dashboard.py:35` lo importa.
    """
    parti = percorso.relative_to(pacchetto).with_suffix("").parts
    if parti and parti[-1] == "__init__":
        parti = parti[:-1]          # `verimem/__init__.py` -> "" (la radice)
    return ".".join(parti)


def entry_point_dichiarati(pyproject: pathlib.Path, radice_pkg: str) -> set[str]:
    """I moduli nominati in [project.scripts] / [project.gui-scripts] / [project.entry-points]."""
    if not pyproject.exists():
        return set()
    testo = pyproject.read_text(encoding="utf-8", errors="replace")
    trovati = set()
    for bersaglio in re.findall(r'=\s*"([\w.]+):[\w.]+"', testo):
        if bersaglio.startswith(radice_pkg + "."):
            trovati.add(bersaglio[len(radice_pkg) + 1:])
    return trovati


def _importati_da(albero: ast.AST, mio_nome: str, radice_pkg: str,
                  e_init: bool = False) -> set[str]:
    """I moduli del pacchetto che questo albero importa, come nomi relativi al pacchetto.

    `e_init` cambia dove punta un import relativo: dentro `pkg/__init__.py` il
    livello 1 e' **pkg stesso** (`from .chat import x` -> `pkg.chat`), dentro
    `pkg/mod.py` e' il genitore. Senza questa distinzione i nove moduli di
    `dashboard_routes/` risultavano senza chiamante (misurato il 09/09).
    """
    trovati: set[str] = set()
    mie_parti = [p for p in mio_nome.split(".") if p]
    if e_init:
        mie_parti = mie_parti + [""]   # il pacchetto stesso fa da "genitore"

    def aggiungi_assoluto(punteggiato: str) -> None:
        if not punteggiato.startswith(radice_pkg + "."):
            return
        parti = punteggiato[len(radice_pkg) + 1:].split(".")
        for i in range(1, len(parti) + 1):
            trovati.add(".".join(parti[:i]))

    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                aggiungi_assoluto(alias.name)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level == 0:
                if nodo.module:
                    aggiungi_assoluto(nodo.module)
                    for alias in nodo.names:      # `from verimem import decay`
                        aggiungi_assoluto(f"{nodo.module}.{alias.name}")
                continue
            base = mie_parti[: len(mie_parti) - nodo.level]
            pezzi = base + (nodo.module.split(".") if nodo.module else [])
            for i in range(1, len(pezzi) + 1):
                trovati.add(".".join(pezzi[:i]))
            for alias in nodo.names:              # `from . import decay`
                candidato = ".".join(pezzi + [alias.name])
                if candidato:
                    trovati.add(candidato)
        elif isinstance(nodo, ast.Call):
            nome_f = getattr(nodo.func, "attr", None) or getattr(nodo.func, "id", None)
            if nome_f != "import_module" or not nodo.args:
                continue
            primo = nodo.args[0]
            if not (isinstance(primo, ast.Constant) and isinstance(primo.value, str)):
                continue  # nome costruito a runtime: invisibile, e il docstring lo dichiara
            if primo.value.startswith("."):
                pezzi = mie_parti[:-1] + primo.value.lstrip(".").split(".")
                trovati.add(".".join(p for p in pezzi if p))
            else:
                aggiungi_assoluto(primo.value)
    return trovati


def analizza(pacchetto: pathlib.Path, pyproject: pathlib.Path = PYPROJECT,
             modulo_finto: str | None = None) -> dict:
    radice_pkg = pacchetto.name
    moduli: list[str] = []
    con_main: set[str] = set()
    importatori: dict[str, set[str]] = defaultdict(set)
    non_letti: list[tuple[str, str]] = []

    for percorso in sorted(pacchetto.rglob("*.py")):
        nome = _nome_modulo(percorso, pacchetto)
        moduli.append(nome)
        testo = percorso.read_text(encoding="utf-8", errors="replace")
        try:
            albero = ast.parse(testo, filename=str(percorso))
        except SyntaxError as errore:
            # i suoi import mancano: il numero dei senza-porta diventa un MASSIMO
            non_letti.append((nome, str(errore)))
            continue
        if '__name__ == "__main__"' in testo or "__name__ == '__main__'" in testo:
            con_main.add(nome)
        for bersaglio in _importati_da(albero, nome, radice_pkg,
                                       e_init=percorso.name == "__init__.py"):
            if bersaglio != nome:
                importatori[bersaglio].add(nome)

    if modulo_finto:
        moduli.append(modulo_finto)

    entry = entry_point_dichiarati(pyproject, radice_pkg)
    b, c1, c2 = [], [], []
    for nome in moduli:
        if not nome or nome.rsplit(".", 1)[-1] in ESCLUSI or importatori.get(nome):
            continue
        if nome in entry:
            b.append(nome)
        elif nome in con_main:
            c1.append(nome)
        else:
            c2.append(nome)

    # D: la RAGGIUNGIBILITA', che non e' la stessa cosa di «qualcuno lo importa».
    # `resonator_memory` ha due importatori e nessuno dei due ha una porta: la
    # catena finisce nel vuoto. Si parte dalle porte e si cammina in avanti.
    avanti: dict[str, set[str]] = defaultdict(set)
    for bersaglio, chi_lo_importa in importatori.items():
        for chi in chi_lo_importa:
            avanti[chi].add(bersaglio)
    veri = set(moduli)
    porte = ({"", "__main__"} | entry) & veri
    visti: set[str] = set()
    coda = list(porte)
    while coda:
        nodo_corrente = coda.pop()
        if nodo_corrente in visti:
            continue
        visti.add(nodo_corrente)
        coda.extend(s for s in avanti.get(nodo_corrente, ()) if s in veri and s not in visti)
    irraggiungibili = sorted(m for m in veri - visti if m)

    return {
        "D_irraggiungibili": irraggiungibili,
        "B_entry_point": sorted(b),
        "C1_solo_python_m": sorted(c1),
        "C2_nessuna_porta": sorted(c2),
        "importatori": importatori,
        "moduli": len(moduli),
        "pacchetto": str(pacchetto.resolve()),
        "non_letti": non_letti,
        "entry_point": sorted(entry),
    }


def _percorso_umano(nome: str) -> str:
    """Il percorso vero: un pacchetto e' una cartella con l'__init__, non `nome.py`."""
    base = PACCHETTO / pathlib.Path(*nome.split("."))
    if base.is_dir():
        return f"verimem/{nome.replace('.', '/')}/__init__.py"
    return f"verimem/{nome.replace('.', '/')}.py"


def stampa(risultato: dict, dettaglio: bool) -> int:
    c2, c1, b = risultato["C2_nessuna_porta"], risultato["C1_solo_python_m"], risultato["B_entry_point"]
    # il percorso ASSOLUTO: vedi la nota in copie.py — uno script ancorato a __file__
    # lanciato da un altro albero misura quello, e il verde non vale niente.
    print(f"senza_chiamante.py — {risultato['moduli']} moduli sotto {risultato['pacchetto']} (ast)")
    if risultato["moduli"] == 0:
        print("VERDETTO: ROSSO — zero moduli letti: questo non è l'albero del prodotto.")
        return 1
    if risultato["non_letti"]:
        print(f"  ATTENZIONE: {len(risultato['non_letti'])} file NON letti: i loro import "
              "mancano, quindi questi numeri sono un MASSIMO")
        for nome, errore in risultato["non_letti"]:
            print(f"    {nome}: {errore[:70]}")
    print()
    print(f"  B  entry point dichiarati in pyproject : {len(b)}  {b}")
    print(f"  C1 raggiungibili solo con `python -m`  : {len(c1)} / sorveglianza {TETTO_C1}")
    if dettaglio or len(c1) != TETTO_C1:
        for nome in c1:
            print(f"       {_percorso_umano(nome)}")
    print(f"  C2 NESSUNA PORTA                       : {len(c2)} / tetto {TETTO_C2}")
    for nome in c2:
        print(f"       {_percorso_umano(nome)}")
    d = risultato["D_irraggiungibili"]
    solo_catena = [m for m in d if m not in c2 and m not in c1]
    print(f"  D  IRRAGGIUNGIBILI da ogni porta      : {len(d)} / tetto {TETTO_D}")
    print(f"       di cui C2 {len([m for m in d if m in c2])} · C1 {len([m for m in d if m in c1])} · "
          f"visibili SOLO per catena {len(solo_catena)}")
    for nome in solo_catena:
        chi = sorted(risultato["importatori"].get(nome, ()))[:2]
        print(f"       {_percorso_umano(nome)}   <- importato da {chi}, che non ha porta")
    print()

    uscita = 0
    if len(c2) > TETTO_C2:
        print(f"VERDETTO: ROSSO — C2 {len(c2)} > {TETTO_C2}: un modulo è stato pubblicato "
              "senza nessuna porta che lo raggiunga.")
        print("  Cura: cablalo a una porta (CLI, MCP, SDK), oppure tienilo fuori dal pacchetto. "
              "Se deve restare così, alza il tetto in scripts/senza_chiamante.py, col motivo.")
        uscita = 1
    elif len(c2) < TETTO_C2:
        print(f"VERDETTO: VERDE — e C2 è SCESA ({len(c2)} < {TETTO_C2}): abbassa il tetto "
              "in scripts/senza_chiamante.py nello stesso commit.")
    if len(d) > TETTO_D:
        print(f"VERDETTO: ROSSO — D {len(d)} > {TETTO_D}: un modulo non e' raggiungibile "
              "da nessuna porta, nemmeno passando per altri moduli.")
        uscita = 1
    elif len(d) < TETTO_D:
        print(f"VERDETTO: VERDE — e D e' SCESA ({len(d)} < {TETTO_D}): abbassa il tetto.")
    if len(c1) > TETTO_C1:
        print(f"VERDETTO: ROSSO — C1 {len(c1)} > {TETTO_C1}: un modulo nuovo è raggiungibile "
              "solo con `python -m`, che il README non insegna e nessun test invoca.")
        uscita = 1
    if uscita == 0 and len(c2) == TETTO_C2 and len(c1) == TETTO_C1 and len(d) == TETTO_D:
        print(f"VERDETTO: VERDE — fermo a C2={TETTO_C2}, C1={TETTO_C1}, D={TETTO_D}.")
    return uscita


def autotest() -> int:
    """Il controllo positivo: un modulo nuovo senza porta DEVE far salire C2."""
    print("=== autotest: (a) il pacchetto com'è ===")
    a = analizza(PACCHETTO)
    uscita_a = stampa(a, dettaglio=False)
    print("\n=== autotest: (b) con un modulo finto che nessuno importa ===")
    b = analizza(PACCHETTO, modulo_finto="modulo_finto_senza_porta")
    uscita_b = stampa(b, dettaglio=False)
    print()
    if uscita_a == 0 and uscita_b == 1:
        print("AUTOTEST VERDE: (a) esce 0 e (b) esce 1 — il cricchetto morde.")
        return 0
    print(f"AUTOTEST ROSSO: (a) esce {uscita_a} (atteso 0), (b) esce {uscita_b} (atteso 1).")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dettaglio", action="store_true")
    parser.add_argument("--autotest", action="store_true")
    argomenti = parser.parse_args(argv)
    if argomenti.autotest:
        return autotest()
    return stampa(analizza(PACCHETTO), dettaglio=argomenti.dettaglio)


if __name__ == "__main__":
    sys.exit(main())
