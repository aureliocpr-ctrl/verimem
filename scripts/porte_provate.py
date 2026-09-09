"""R5 — ogni comando della CLI ha un test che lo INVOCA DALLA PORTA?

Il righello confronta due liste:

  A. **i comandi che il parser registra** — letti con `ast` dai file che
     costruiscono le app Typer (`verimem/cli.py` piu' le sotto-app montate con
     `add_typer`, che stanno in ALTRI file: `swarm/cli.py`, `teams/cli.py`);
  B. **i test che li invocano**, e a che LIVELLO.

⚠️ CINQUE LIVELLI, STAMPATI SEPARATI — perche' qui sta tutto il punto di R5:

  ① PORTA      `subprocess([... "verimem", "facts", "add" ...])` oppure
               `runner.invoke(app, ["facts", "add", ...])` con `app` la RADICE:
               passa dal parser completo, come l'utente, **e il comando gira**.
  ①h AIUTO     l'unica invocazione e' `[… "--help"]`. Typer stampa l'aiuto ed
               esce: il test prova che il comando ESISTE e che il modulo si
               importa, **non che faccia quello che dice**. (`test_cli.py:82`
               ne tiene quattordici cosi', e il suo docstring lo dichiara:
               «Each subcommand must have a --help that prints and exits 0».)
  ①b GRUPPO    `runner.invoke(swarm_app, ["run", ...])`: il comando e' invocato,
               ma **sulla sotto-app**. Il montaggio (`app.add_typer(swarm_app,
               name="swarm")`) NON e' esercitato: togli quella riga e questi
               test restano tutti verdi mentre `verimem swarm run` sparisce per
               l'utente. E' un sensore scollegato dalla porta vera.
  ② FUNZIONE   il test importa la funzione e la chiama: il corpo e' esercitato,
               la porta no (firma Typer, default e `Option` non si vedono).
  ③ NOMINATO   il nome compare nel testo del test e nient'altro.

🎯 Solo ① conta come «provato alla porta».

🔴 E IL NUMERO NON E' IL VERDETTO: un comando che il righello dice «non provato»
va **ESEGUITO** prima di chiamarlo scoperto. L'esecuzione e' il giudice; questo
file dice solo DOVE guardare.

🪞 STORIA DI QUESTO FILE, perche' e' la lezione — **tre versioni, tre errori, e
ogni volta il numero sbagliato era quello che mi dava piu' ragione**:

  v1  confrontava solo la sequenza degli argomenti, e ha sbagliato **nelle due
      direzioni insieme**: `runner.invoke(swarm_app, ["run", cfg])` diventava
      una prova di `verimem run` (la RADICE, `cli.py:225`, che non c'entra) e
      insieme lasciava `verimem swarm run` fra i «solo nominati».
      🔑 **Un'invocazione si lega all'OGGETTO invocato, non ai soli argomenti.**
  v2  contava `["tui", "--help"]` come prova di `verimem tui`.
      🔑 **`--help` non esegue niente: e' un livello a parte, e va stampato.**
  v3  dava «MAI TOCCATO» a `providers scan`, `providers models`, `skills show`,
      `episodes show`, perche' la loro riga di comando sta in una
      `@pytest.mark.parametrize` e arriva all'`invoke` per variabile. Quello
      sbagliava **contro il prodotto**, cioe' ancora a favore del mio reperto.
      🔑 **Il legame parametro→invoke e' SCRITTO (stesso nome): si legge.**

Uso:
    PYTHONPATH=. python scripts/porte_provate.py             # tabella + elenchi
    PYTHONPATH=. python scripts/porte_provate.py --json      # per la CI
    PYTHONPATH=. python scripts/porte_provate.py --controllo # il controllo positivo

Esce 1 se un comando e' senza ①  →  in CI e' il RED di R5.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from dataclasses import dataclass, field

RADICE = pathlib.Path(__file__).resolve().parent.parent

#: I nomi con cui un test puo' lanciare l'eseguibile in un `subprocess`.
_ESEGUIBILE = {"verimem", "engram", "hippo"}


def file_con_typer(pacchetto: pathlib.Path) -> list[pathlib.Path]:
    """I file che costruiscono app Typer: si cercano, non si scrivono a mano."""
    fuori = []
    for p in sorted(pacchetto.rglob("*.py")):
        try:
            testo = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "typer.Typer(" in testo:
            fuori.append(p)
    return fuori


@dataclass
class Comando:
    """Un comando come lo digita l'utente: `verimem skills list`."""
    percorso: tuple[str, ...]
    app: str                           # la variabile Typer su cui e' registrato
    funzione: str
    file: str
    riga: int
    nascosto: bool = False
    porta: list[str] = field(default_factory=list)
    aiuto: list[str] = field(default_factory=list)
    gruppo: list[str] = field(default_factory=list)
    funzione_chiamata: list[str] = field(default_factory=list)
    nominato: list[str] = field(default_factory=list)

    @property
    def nome(self) -> str:
        return " ".join(self.percorso)

    @property
    def livello(self) -> str:
        if self.porta:
            return "① PORTA"
        if self.aiuto:
            return "①h AIUTO"
        if self.gruppo:
            return "①b GRUPPO"
        if self.funzione_chiamata:
            return "② FUNZIONE"
        if self.nominato:
            return "③ NOMINATO"
        return "MAI TOCCATO"


def _stringa(nodo: ast.AST) -> str | None:
    return nodo.value if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) else None


def _nome_app(nodo: ast.AST) -> str | None:
    """`skills_app.command(...)` → 'skills_app'; `app.command()` → 'app'."""
    if isinstance(nodo, ast.Attribute) and isinstance(nodo.value, ast.Name):
        return nodo.value.id
    return None


def _identificatore(nodo: ast.AST) -> str | None:
    """`app` → 'app'; `cli.app` → 'app' (il test puo' importare il modulo)."""
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        return nodo.attr
    return None


# ─────────────────────────── A. l'inventario ───────────────────────────

def inventario(pacchetto: pathlib.Path) -> tuple[list[Comando], dict[str, tuple[str, ...]], list[str]]:
    """(comandi, prefisso_per_app, note)."""
    grezzi: list[Comando] = []
    montaggi: dict[str, tuple[str, str]] = {}   # sub → (padre, nome del gruppo)
    note: list[str] = []

    for percorso in file_con_typer(pacchetto):
        rel = percorso.relative_to(RADICE).as_posix()
        albero = ast.parse(percorso.read_text(encoding="utf-8"), filename=str(percorso))

        for nodo in ast.walk(albero):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) \
               and nodo.func.attr == "add_typer":
                padre = _nome_app(nodo.func)
                sub = nodo.args[0].id if nodo.args and isinstance(nodo.args[0], ast.Name) else None
                nome = next((_stringa(kw.value) for kw in nodo.keywords if kw.arg == "name"), None)
                if sub and padre and nome:
                    montaggi[sub] = (padre, nome)
                elif sub:
                    note.append(f"{rel}: add_typer({sub}) senza name= leggibile → NON RISOLTO")

            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for deco in nodo.decorator_list:
                    chiamata = deco if isinstance(deco, ast.Call) else None
                    bersaglio = chiamata.func if chiamata else deco
                    if not (isinstance(bersaglio, ast.Attribute) and bersaglio.attr == "command"):
                        continue
                    app = _nome_app(bersaglio)
                    if app is None:
                        note.append(f"{rel}:{nodo.lineno}: `.command` su un'espressione non "
                                    f"semplice → NON RISOLTO")
                        continue
                    esplicito, nascosto = None, False
                    if chiamata:
                        if chiamata.args:
                            esplicito = _stringa(chiamata.args[0])
                            if esplicito is None:
                                note.append(f"{rel}:{nodo.lineno}: primo argomento di `.command()` "
                                            f"non e' una stringa costante → NON RISOLTO")
                        for kw in chiamata.keywords:
                            if kw.arg == "name" and _stringa(kw.value):
                                esplicito = _stringa(kw.value)
                            if kw.arg == "hidden" and isinstance(kw.value, ast.Constant):
                                nascosto = bool(kw.value.value)
                    # ⚠️ LETTA in typer.main.get_command_name, non indovinata:
                    #    `name.lower().replace("_", "-")`.
                    nome = esplicito or nodo.name.lower().replace("_", "-")
                    grezzi.append(Comando(percorso=(nome,), app=app, funzione=nodo.name,
                                          file=rel, riga=nodo.lineno, nascosto=nascosto))

    # prefisso completo di ogni app: app → (), swarm_app → ("swarm",),
    # gateway_keys_app → ("gateway", "keys")
    prefisso: dict[str, tuple[str, ...]] = {}

    def risolvi(a: str, visti: frozenset[str] = frozenset()) -> tuple[str, ...] | None:
        if a in prefisso:
            return prefisso[a]
        if a in visti:
            return None                      # ciclo nei montaggi
        if a not in montaggi:
            return () if a == "app" else None
        padre, gruppo = montaggi[a]
        sopra = risolvi(padre, visti | {a})
        if sopra is None:
            return None
        prefisso[a] = sopra + (gruppo,)
        return prefisso[a]

    prefisso["app"] = ()
    for c in grezzi:
        p = risolvi(c.app)
        if p is None:
            note.append(f"{c.file}:{c.riga}: `{c.app}` non risale ad `app` → il comando "
                        f"`{c.percorso[-1]}` e' IRRAGGIUNGIBILE dalla radice")
            p = ()
        c.percorso = p + c.percorso
    return grezzi, prefisso, note


# ─────────────────────────── B. i test ───────────────────────────

def _app_importate(albero: ast.AST) -> dict[str, str]:
    """nome locale nel test → nome della variabile app nel pacchetto."""
    fuori: dict[str, str] = {}
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith("verimem"):
            for alias in nodo.names:
                if alias.name.endswith("app"):
                    fuori[alias.asname or alias.name] = alias.name
    return fuori


def _liste_di_stringhe(nodo: ast.AST) -> list[list[str | None]]:
    """Ogni List/Tuple sotto `nodo`, con `None` al posto di cio' che non e' costante."""
    return [[_stringa(e) for e in n.elts]
            for n in ast.walk(nodo) if isinstance(n, (ast.List, ast.Tuple))]


def _parametrizzazioni(albero: ast.AST) -> dict[str, list[list[str | None] | str]]:
    """`@pytest.mark.parametrize("group_args", [["providers","scan","--help"], …])`.

    Il legame fra il parametro e l'`invoke` che lo usa e' SCRITTO — il nome del
    parametro e' lo stesso della variabile — quindi si legge, non si deduce.
    Senza questo, `runner.invoke(app, group_args)` e' opaco e il righello
    dichiara «MAI TOCCATO» comandi che un test invoca davvero: sbaglia CONTRO
    il prodotto, cioe' a favore del proprio reperto.
    """
    fuori: dict[str, list[list[str | None] | str]] = {}
    for nodo in ast.walk(albero):
        if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "parametrize" and len(nodo.args) >= 2):
            continue
        nomi = _stringa(nodo.args[0])
        if not nomi or "," in nomi:          # parametri multipli: non li risolvo
            continue
        valori: list[list[str | None] | str] = []
        if isinstance(nodo.args[1], (ast.List, ast.Tuple)):
            for elemento in nodo.args[1].elts:
                if isinstance(elemento, (ast.List, ast.Tuple)):
                    valori.append([_stringa(e) for e in elemento.elts])
                elif (s := _stringa(elemento)) is not None:
                    valori.append(s)
        if valori:
            fuori.setdefault(nomi.strip(), []).extend(valori)
    return fuori


def _righe_concrete(lista: list[ast.expr], parametri: dict[str, list]) -> list[list[str | None]]:
    """Espande `[subcommand, "--help"]` nelle righe vere, una per valore del parametro."""
    posti = [i for i, e in enumerate(lista)
             if isinstance(e, ast.Name) and isinstance(parametri.get(e.id), list)
             and any(isinstance(v, str) for v in parametri[e.id])]
    base = [_stringa(e) for e in lista]
    if len(posti) != 1:                      # zero o piu' di un parametro: non espando
        return [base]
    i = posti[0]
    nome = lista[i].id
    fuori = []
    for v in parametri[nome]:
        if isinstance(v, str):
            riga = list(base)
            riga[i] = v
            fuori.append(riga)
    return fuori or [base]


def _contiene(lista: list[str | None], seq: tuple[str, ...]) -> bool:
    n = len(seq)
    return any(tuple(lista[i:i + n]) == seq for i in range(len(lista) - n + 1))


#: le opzioni che stampano l'aiuto e FANNO USCIRE Typer senza eseguire il comando
_AIUTO = {"--help", "-h"}


def _solo_aiuto(lista: list[str | None], seq: tuple[str, ...]) -> bool:
    """`["skills","list","--help"]` → True; `["skills","list"]` → False.

    Un `--help` non esegue il comando: Typer stampa l'aiuto ed esce. Il test
    prova che il comando ESISTE, non che FUNZIONA — e chiamare «provato alla
    porta» quel caso e' il modo piu' comodo di gonfiare il verde.
    """
    resto = [e for e in lista if e is not None and e not in seq]
    return bool(resto) and all(e in _AIUTO for e in resto)


def esamina_test(cartella: pathlib.Path, comandi: list[Comando],
                 prefisso: dict[str, tuple[str, ...]]) -> list[str]:
    note: list[str] = []
    for percorso in sorted(cartella.rglob("test_*.py")):
        rel = percorso.relative_to(RADICE).as_posix()
        try:
            testo = percorso.read_text(encoding="utf-8")
            albero = ast.parse(testo, filename=str(percorso))
        except (OSError, UnicodeDecodeError):
            continue
        except SyntaxError as e:
            note.append(f"{rel}: SyntaxError, file saltato ({e})")
            continue

        importate = _app_importate(albero)
        parametri = _parametrizzazioni(albero)

        #: (prefisso gia' consumato dall'app invocata, argomenti) per ogni invoke
        invocazioni: list[tuple[tuple[str, ...] | None, list[str | None]]] = []
        #: le liste che sembrano una riga di comando di subprocess
        da_subprocess: list[list[str | None]] = []

        for n in ast.walk(albero):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
                continue
            if n.func.attr == "invoke" and n.args:
                locale = _identificatore(n.args[0])
                variabile = importate.get(locale or "", locale or "")
                pre = prefisso.get(variabile)
                if pre is None:
                    note.append(f"{rel}: invoke su `{locale}`, app non riconosciuta → "
                                f"NON CLASSIFICATO (non conta come provato)")
                #: gli argomenti sono una VARIABILE parametrizzata: `invoke(app, group_args)`
                if len(n.args) >= 2 and isinstance(n.args[1], ast.Name) \
                   and n.args[1].id in parametri:
                    for v in parametri[n.args[1].id]:
                        if isinstance(v, list):
                            invocazioni.append((pre, v))
                #: oppure una lista scritta lì, con al piu' un parametro dentro
                for nodo_lista in [a for a in n.args[1:2] if isinstance(a, (ast.List, ast.Tuple))]:
                    for riga in _righe_concrete(nodo_lista.elts, parametri):
                        invocazioni.append((pre, riga))
                #: e le liste annidate piu' in fondo (kwargs, chiamate dentro chiamate)
                for lista in _liste_di_stringhe(n):
                    invocazioni.append((pre, lista))
            elif n.func.attr in {"run", "check_output", "Popen", "check_call"}:
                for lista in _liste_di_stringhe(n):
                    if any(e in _ESEGUIBILE for e in lista if e) or \
                       _contiene(lista, ("-m", "verimem")):
                        da_subprocess.append(lista)

        chiamate = {nn.func.id for nn in ast.walk(albero)
                    if isinstance(nn, ast.Call) and isinstance(nn.func, ast.Name)}
        importati = {a.asname or a.name for nn in ast.walk(albero)
                     if isinstance(nn, ast.ImportFrom) for a in nn.names}

        for c in comandi:
            #: ① dalla radice — subprocess, oppure invoke sull'app radice.
            #:    Se l'unico argomento in piu' e' `--help`, e' ①h, non ①.
            candidati = [riga for riga in da_subprocess if _contiene(riga, c.percorso)] \
                + [riga for pre, riga in invocazioni
                   if pre == () and _contiene(riga, c.percorso)]
            if any(not _solo_aiuto(riga, c.percorso) for riga in candidati):
                c.porta.append(rel)
                continue
            if candidati:
                c.aiuto.append(rel)
                continue
            #: ①b sulla sotto-app — il prefisso e' gia' consumato dall'oggetto
            residuo = None
            for pre, lista in invocazioni:
                if pre and c.percorso[:len(pre)] == pre:
                    residuo = c.percorso[len(pre):]
                    if residuo and _contiene(lista, residuo):
                        c.gruppo.append(rel)
                        break
            if c.gruppo and c.gruppo[-1] == rel:
                continue
            #: ② la funzione chiamata per nome, e importata da questo file
            if c.funzione in chiamate and c.funzione in importati:
                c.funzione_chiamata.append(rel)
                continue
            #: ③ il nome completo del comando compare nel testo
            if c.nome in testo:
                c.nominato.append(rel)
    return note


# ─────────────────────────── il controllo ───────────────────────────

def controllo_positivo(comandi: list[Comando], prefisso: dict[str, tuple[str, ...]]) -> int:
    """Un righello che dice sempre «provato» non fallisce mai: qui lo si prova.

    Cinque domande, ognuna con una risposta che puo' smentirmi:
      C1 un comando inventato non deve risultare invocato da nessuno;
      C2 un comando che SO provato alla porta (`verimem save`, con `subprocess`
         in tests/test_cli.py) deve risultare ①;
      C3 la sequenza si conta CONTIGUA;
      C4 `verimem run` (radice) NON deve prendersi il test che invoca
         `swarm_app` con `["run", ...]` — l'errore della v1;
      C5 `verimem swarm run` (sotto-app) deve risultare ①b, non ③.
    """
    esito = 0
    print("== CONTROLLO POSITIVO ==")

    finto = Comando(percorso=("comando", "che-non-esiste-1908"), app="app",
                    funzione="_funzione_inventata_1908", file="(finto)", riga=0)
    esamina_test(RADICE / "tests", [finto], prefisso)
    ok = finto.livello == "MAI TOCCATO"
    print(f"  C1 comando inventato        → {finto.livello:12s} {'OK' if ok else '🔴 TROVA il falso'}")
    esito |= 0 if ok else 1

    def trova(nome: str) -> Comando | None:
        return next((c for c in comandi if c.nome == nome), None)

    for etichetta, nome, atteso in (
        ("C2 `verimem save`         ", "save", "① PORTA"),
        ("C4 `verimem run` (radice) ", "run", None),          # NON deve essere ①
        ("C5 `verimem swarm run`    ", "swarm run", "①b GRUPPO"),
        # C6: `["providers","scan","--help"]` sta in una `parametrize` e arriva
        # all'invoke per variabile. La v2 dava MAI TOCCATO: sbagliava CONTRO il
        # prodotto, cioe' a favore del mio reperto.
        ("C6 `verimem providers scan`", "providers scan", "①h AIUTO"),
        # C7: e il comando che ha SOLO il --help non deve mai finire in ①.
        ("C7 `verimem tui`          ", "tui", "①h AIUTO"),
    ):
        c = trova(nome)
        if c is None:
            print(f"  {etichetta} → 🔴 comando non trovato nell'inventario")
            esito |= 1
            continue
        if atteso is None:
            ok = c.livello != "① PORTA" or all("swarm" not in f for f in c.porta)
            print(f"  {etichetta} → {c.livello:12s} "
                  f"{'OK (non ruba il test dello swarm)' if ok else '🔴 ruba il test di swarm run'}")
        else:
            ok = c.livello == atteso
            print(f"  {etichetta} → {c.livello:12s} {'OK' if ok else '🔴 atteso ' + atteso}")
        esito |= 0 if ok else 1

    ok3 = not _contiene(["facts", "altro", "add"], ("facts", "add"))
    print(f"  C3 sequenza non contigua    → {'OK' if ok3 else '🔴 combacia per caso'}")
    esito |= 0 if ok3 else 1
    return esito


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--controllo", action="store_true", help="solo il controllo positivo")
    ap.add_argument("--elenco", action="store_true", help="solo l'elenco dei senza-①")
    args = ap.parse_args()

    comandi, prefisso, note = inventario(RADICE / "verimem")
    note += esamina_test(RADICE / "tests", comandi, prefisso)
    comandi.sort(key=lambda c: c.nome)

    if args.controllo:
        return controllo_positivo(comandi, prefisso)

    senza = [c for c in comandi if not c.porta]
    per_livello: dict[str, list[Comando]] = {}
    for c in comandi:
        per_livello.setdefault(c.livello, []).append(c)

    if args.json:
        print(json.dumps({
            "totale": len(comandi),
            "alla_porta": len(comandi) - len(senza),
            "per_livello": {k: [c.nome for c in v] for k, v in sorted(per_livello.items())},
            "senza_porta": [c.nome for c in senza],
            "note": note,
        }, indent=2, ensure_ascii=False))
        return 1 if senza else 0

    if not args.elenco:
        print(f"== COMANDI REGISTRATI DAL PARSER: {len(comandi)} ==")
        print("   da " + ", ".join(f"{f} ({sum(1 for c in comandi if c.file == f)})"
                                   for f in sorted({c.file for c in comandi})))
        print()
        print(f"{'livello':12s} {'comando':38s} {'implementato in':40s} chi lo invoca (primo)")
        print("-" * 128)
        for c in comandi:
            chi = (c.porta or c.gruppo or c.funzione_chiamata or c.nominato or ["—"])[0]
            marchio = " [hidden]" if c.nascosto else ""
            print(f"{c.livello:12s} {('verimem ' + c.nome + marchio):38s} "
                  f"{(c.file + ':' + str(c.riga)):40s} {chi}")
        print()

    for livello in ("① PORTA", "①h AIUTO", "①b GRUPPO", "② FUNZIONE", "③ NOMINATO", "MAI TOCCATO"):
        print(f"   {livello:12s} {len(per_livello.get(livello, [])):3d}")
    print(f"   {'-' * 12} ---")
    print(f"   {'TOTALE':12s} {len(comandi):3d}   ·   senza ① : {len(senza)}")

    if senza:
        print("\n-- SENZA UN TEST CHE LI INVOCHI DALLA PORTA (da ESEGUIRE a mano) --")
        for c in senza:
            print(f"   verimem {c.nome:32s} {c.livello:12s} {c.file}:{c.riga}")
    if note:
        print("\n-- NOTE (casi che il righello NON sa risolvere: non contarli come provati) --")
        for n in sorted(set(note)):
            print(f"   ⚠️  {n}")
    return 1 if senza else 0


if __name__ == "__main__":
    sys.exit(main())
