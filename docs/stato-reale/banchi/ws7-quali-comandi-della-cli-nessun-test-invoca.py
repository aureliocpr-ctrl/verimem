"""Quali comandi della CLI nessun test invoca — e il criterio è STRUTTURALE.

`verimem/cli.py` espone 88 comandi su 13 gruppi Typer. La domanda del product
owner è quella dell'utente: **se domani rinomino un comando, chi se ne accorge?**

⚠️ IL CRITERIO NON PUÒ ESSERE UN GREP DEL NOME. Un comando si chiama `add`,
`list`, `show`, `serve`: `serve` compare in 672 file di test e `code` in 462,
quasi sempre come parola inglese. È lo stesso errore che ho fatto tre volte
stasera sul README — cercare una PAROLA dove serve una STRUTTURA. Qui la
struttura è la lista di argomenti::

    CliRunner().invoke(cli.app, ["facts", "retirement-log", "--counts"])
                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^

🔴 DUE DIFETTI DEL RIGHELLO, TROVATI PRIMA DI PUBBLICARE IL NUMERO

**①** La prima versione risolveva **un solo livello** di `add_typer`, e
dichiarava orfani `keys create/list/revoke`: quei comandi si chiamano
`gateway keys create`. Tre nomi falsi — chi fosse andato a cercarli non avrebbe
trovato niente e avrebbe dato ragione all'accusa.

**②** La seconda diceva che nessun test invoca `warmup`, mentre
`tests/test_cli_warmup.py:36` fa esattamente
``runner.invoke(cli.app, ["warmup", "--no-daemon"])``. Causa: la regex chiedeva
``invoke\\(\\s*\\w+`` e **`cli.app` contiene un punto**, che `\\w` non copre. Tutte
le invocazioni scritte in quella forma erano invisibili.

🔑 Il controllo positivo di allora — «se raccolgo meno di 20 invocazioni il
parser è rotto» — **non poteva accorgersene**: ne vedeva 135 e taceva. Guardava
che il righello dicesse *qualcosa*, non che vedesse *tutte le forme*. Quello
giusto è un **caso che DEVE rispondere**: `warmup` è invocato alla lettera, se
non risulta visto il numero non si stampa.

📏 PORTATA DICHIARATA — perché non gonfi il risultato:
  · «invocato» ≠ «coperto»: dice che qualcuno lo chiama, non che ne verifichi
    l'esito;
  · un test che costruisce gli argomenti a runtime resta invisibile;
  · nel dubbio **sottostima gli orfani** (raccoglie anche le liste di stringhe
    fuori da `invoke`): meglio accusare di meno che accusare a torto;
  · non guarda le **opzioni**, ed è il livello dove T30 è nato
    (`verimem save … --db` → `No such option: --db`, exit 2).

Uso::

    python docs/stato-reale/banchi/ws7-quali-comandi-della-cli-nessun-test-invoca.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RADICE = Path(__file__).resolve().parents[3]
CLI = RADICE / "verimem" / "cli.py"
TESTS = RADICE / "tests"

_CMD = re.compile(r"@(\w+)\.command\(\s*(?:name\s*=\s*)?[\"']([\w-]+)[\"']")
_CMD_NUDO = re.compile(r"@(\w+)\.command\(\s*(?:\)|help=|$)")
_DEF = re.compile(r"^def\s+(\w+)\s*\(", re.M)
# I gruppi sono ANNIDATI (gateway_keys_app dentro gateway_app dentro app): il
# nome pieno è la catena intera, e va risolta risalendo di padre in padre.
_ADDTYPER = re.compile(r"(\w+)\.add_typer\(\s*(\w+)\s*,\s*name\s*=\s*[\"']([\w-]+)[\"']")
# [\w.]+ e non \w+: i test scrivono invoke(cli.app, [...]).
_INVOKE = re.compile(r"invoke\(\s*[\w.]+\s*,\s*\[([^\]]*)\]", re.S)
_SUBPROC = re.compile(r"\[\s*[\"'](?:verimem|python)[\"'][^\]]*\]", re.S)
# Le liste di argomenti non stanno solo dentro invoke(): i test le raccolgono in
# tuple e le ciclano (test_cli_agent_namespace.py:34). Qui si prende ogni
# lista/tupla di sole stringhe.
_LISTA = re.compile(r"[\[(]((?:\s*[\"'][^\"'\n]+[\"']\s*,)+\s*[\"'][^\"'\n]+[\"']\s*)[\])]")
_TOKEN = re.compile(r"[\"']([^\"']+)[\"']")


def comandi_dichiarati(testo: str) -> dict[str, str]:
    """{'facts retirement-log': 'facts_app', 'serve': 'app', …}"""
    padre: dict[str, tuple[str, str]] = {}
    for genitore, figlio, nome in _ADDTYPER.findall(testo):
        padre[figlio] = (genitore, nome)

    def catena(app: str) -> str:
        pezzi: list[str] = []
        visti: set[str] = set()
        cur = app
        while cur in padre and cur not in visti:
            visti.add(cur)
            genitore, nome = padre[cur]
            pezzi.insert(0, nome)
            cur = genitore
        return " ".join(pezzi)

    prefisso = {figlio: catena(figlio) for figlio in padre}
    righe = testo.splitlines()
    fuori: dict[str, str] = {}
    for n, riga in enumerate(righe):
        m = _CMD.search(riga)
        nome = app = None
        if m:
            app, nome = m.group(1), m.group(2)
        else:
            mn = _CMD_NUDO.search(riga)
            if mn:
                # @app.command() senza nome: Typer usa il nome della funzione,
                # con gli underscore trasformati in trattini.
                app = mn.group(1)
                for succ in righe[n : n + 12]:
                    md = _DEF.match(succ)
                    if md:
                        nome = md.group(1).replace("_", "-")
                        break
        if not nome or not app:
            continue
        fuori[f"{prefisso.get(app, '')} {nome}".strip()] = app
    return fuori


def invocazioni_nei_test() -> set[tuple[str, ...]]:
    viste: set[tuple[str, ...]] = set()
    for f in sorted(TESTS.rglob("test_*.py")):
        try:
            testo = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pezzo in _INVOKE.findall(testo) + _SUBPROC.findall(testo) + _LISTA.findall(testo):
            utili: list[str] = []
            for t in _TOKEN.findall(pezzo):
                if t.startswith("-"):
                    break
                if t in {"verimem", "python", "-m"}:
                    continue
                utili.append(t)
            for k in (1, 2, 3):
                if len(utili) >= k:
                    viste.add(tuple(utili[:k]))
    return viste


def main() -> int:
    testo = CLI.read_text(encoding="utf-8")
    dichiarati = comandi_dichiarati(testo)
    viste = invocazioni_nei_test()

    # CONTROLLO POSITIVO su un caso che DEVE rispondere: test_cli_warmup.py:36
    # invoca `warmup` alla lettera. Se il righello non lo vede, non è la CLI a
    # non essere testata — e un elenco gonfiato è indistinguibile da uno vero.
    if ("warmup",) not in viste or len(viste) < 20:
        print(f"!! righello rotto: {len(viste)} invocazioni raccolte, "
              f"warmup visto = {('warmup',) in viste} (deve essere True: "
              f"tests/test_cli_warmup.py:36). Numero NON stampato.")
        return 2

    orfani = [c for c in sorted(dichiarati) if tuple(c.split()) not in viste]
    print(f"cli.py:                         {len(testo.splitlines())} righe")
    print(f"comandi dichiarati:             {len(dichiarati)}")
    print(f"invocazioni viste nei test:     {len(viste)}")
    print(f"controllo positivo (warmup):    visto")
    print(f"comandi che NESSUN test invoca: {len(orfani)}")
    print("")
    for c in orfani:
        print(f"   {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
