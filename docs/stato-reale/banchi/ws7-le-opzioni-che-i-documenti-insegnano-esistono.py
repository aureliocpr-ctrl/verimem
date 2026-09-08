"""Ogni opzione che i documenti insegnano esiste nel comando? — il livello di T30.

`test_i_comandi_che_il_readme_insegna_esistono.py` fa questa domanda per i
COMANDI, e la sua regex si ferma lì::

    citati = set(re.findall(r"`verimem\\s+([a-z][a-z0-9-]{2,})", testo))

cattura `save`, `import`, `airgap`; **non** cattura `--asserted-at`. Ed è
esattamente il livello dove è nato **T30** il 07/09::

    $ verimem save "..." --db /tmp/x
    Error: No such option: --db          (exit 2)

Comando presente, opzione assente, presidio verde. Questo righello chiude quel
gradino: prende ogni riga `verimem <comando> … --opzione` dai documenti del
repo (README, `docs/**.md`, la guida dell'agente) e verifica che quell'opzione
sia dichiarata **da quel comando** in `verimem/cli.py`.

⚠️ COME TYPER NOMINA UN'OPZIONE — le due forme, ed è la seconda che mi ha fregato:
  · `gate: bool = typer.Option(True, "--gate/--no-gate", …)` → nomi espliciti;
  · `daemon: bool = typer.Option(True, help=…)` → Typer deriva `--daemon`, e
    per un `bool` aggiunge il gemello `--no-daemon`.

🔴 IL RIGHELLO HA ACCUSATO DUE VOLTE A TORTO PRIMA DI QUESTA VERSIONE.
Diceva che `verimem warmup --no-daemon` non esiste, mentre
`tests/test_cli_warmup.py:36` lo invoca e passa. Causa: leggevo la chiamata
`typer.Option(...)` con una finestra fissa di 400 caratteri dal nome del
parametro, e la finestra **sconfinava nel parametro successivo** — `daemon`
ereditava i flag espliciti di `gate` (`"--gate/--no-gate"`), quindi il ramo che
deriva `--no-daemon` non veniva mai preso.

🔑 CONTROLLO POSITIVO A TRE FACCE — e la terza è quella che serviva davvero:
  · `airgap --live` (README:515) **deve** risultare VALIDA — forma esplicita;
  · `warmup --no-daemon` **deve** risultare VALIDA — forma **derivata**, ed è la
    forma che il righello sbagliava mentre la prima passava benissimo;
  · `airgap --questa-non-esiste` **deve** risultare INVALIDA.
Un controllo positivo che non tocca la forma rotta è un controllo che tace.

📏 PORTATA: legge la dichiarazione statica, non `--help` eseguito. Un'opzione
aggiunta a runtime o da un callback non si vede. Le opzioni globali dell'app
(prima del sottocomando) sono ammesse per tutti.

Uso::

    python docs/stato-reale/banchi/ws7-le-opzioni-che-i-documenti-insegnano-esistono.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RADICE = Path(__file__).resolve().parents[3]
CLI = RADICE / "verimem" / "cli.py"

_CMD = re.compile(r"@(\w+)\.command\(\s*(?:name\s*=\s*)?[\"']([\w-]+)[\"']")
_CMD_NUDO = re.compile(r"@(\w+)\.command\(\s*(?:\)|help=|$)")
_DEF = re.compile(r"^def\s+(\w+)\s*\(")
_ADDTYPER = re.compile(r"(\w+)\.add_typer\(\s*(\w+)\s*,\s*name\s*=\s*[\"']([\w-]+)[\"']")
_PARAM = re.compile(r"^\s{4}(\w+)\s*:\s*([^=\n]+?)\s*=\s*typer\.(Option|Argument)\(", re.M)
_FINE_FIRMA = re.compile(r"^\)\s*(?:->[^:]*)?:\s*$")
_FLAG = re.compile(r"[\"'](--[a-z][\w-]*(?:/--[a-z][\w-]*)?)[\"']")
_USO = re.compile(r"verimem\s+([a-z][\w -]*?(?:\s+--[a-z][\w-]*(?:[= ][^\s`]+)?)+)")

GLOBALI = {"--help", "--version"}


def _catena(padre: dict[str, tuple[str, str]], app: str) -> str:
    pezzi: list[str] = []
    visti: set[str] = set()
    cur = app
    while cur in padre and cur not in visti:
        visti.add(cur)
        genitore, nome = padre[cur]
        pezzi.insert(0, nome)
        cur = genitore
    return " ".join(pezzi)


def opzioni_per_comando(testo: str) -> dict[str, set[str]]:
    padre: dict[str, tuple[str, str]] = {}
    for genitore, figlio, nome in _ADDTYPER.findall(testo):
        padre[figlio] = (genitore, nome)
    prefisso = {figlio: _catena(padre, figlio) for figlio in padre}

    righe = testo.splitlines()
    fuori: dict[str, set[str]] = {}
    for n, riga in enumerate(righe):
        m = _CMD.search(riga)
        nome = app = None
        if m:
            app, nome = m.group(1), m.group(2)
        else:
            mn = _CMD_NUDO.search(riga)
            if mn:
                app = mn.group(1)
                for succ in righe[n : n + 12]:
                    md = _DEF.match(succ)
                    if md:
                        nome = md.group(1).replace("_", "-")
                        break
        if not nome or not app:
            continue
        pieno = f"{prefisso.get(app, '')} {nome}".strip()

        corpo: list[str] = []
        dentro = False
        for succ in righe[n : n + 300]:
            if not dentro and _DEF.match(succ):
                dentro = True
            if dentro:
                corpo.append(succ)
                if _FINE_FIRMA.match(succ):
                    break
        firma = "\n".join(corpo)

        # I parametri, IN ORDINE: la chiamata di ciascuno finisce dove comincia
        # il successivo. Con una finestra fissa un parametro eredita i flag del
        # vicino — ed e' cosi' che `--no-daemon` risultava inesistente.
        trovati = list(_PARAM.finditer(firma))
        opz: set[str] = set()
        for i, mp in enumerate(trovati):
            par, tipo, genere = mp.group(1), mp.group(2), mp.group(3)
            if genere == "Argument":
                continue
            fine = trovati[i + 1].start() if i + 1 < len(trovati) else len(firma)
            chiamata = firma[mp.start() : fine]
            espliciti = _FLAG.findall(chiamata)
            if espliciti:
                for e in espliciti:
                    opz.update(e.split("/"))
            else:
                base = par.replace("_", "-")
                opz.add("--" + base)
                if "bool" in tipo:
                    opz.add("--no-" + base)
        fuori[pieno] = opz
    return fuori


def insegnate() -> list[tuple[str, str, str]]:
    """(comando, 'flag|flag', 'file:riga') da README, docs/**.md, agent_guide."""
    fonti = [RADICE / "README.md", RADICE / "verimem" / "agent_guide.py"]
    fonti += sorted((RADICE / "docs").rglob("*.md"))
    fuori: list[tuple[str, str, str]] = []
    for f in fonti:
        try:
            testo = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n, riga in enumerate(testo.splitlines(), 1):
            for uso in _USO.findall(riga):
                token = uso.split()
                parole = [t for t in token if not t.startswith("-")]
                flag = [t.split("=")[0] for t in token if t.startswith("--")]
                if not parole or not flag:
                    continue
                fuori.append((" ".join(parole[:3]), "|".join(flag),
                              f"{f.relative_to(RADICE)}:{n}"))
    return fuori


def main() -> int:
    testo = CLI.read_text(encoding="utf-8")
    per_comando = opzioni_per_comando(testo)

    prove = [
        ("airgap", "--live", True, "README:515, forma esplicita"),
        ("warmup", "--no-daemon", True, "test_cli_warmup.py:36, forma DERIVATA"),
        ("airgap", "--questa-non-esiste", False, "opzione inventata"),
    ]
    for cmd, flag, atteso, perche in prove:
        visto = flag in per_comando.get(cmd, set())
        if visto is not atteso:
            print(f"!! righello rotto sul controllo positivo: {cmd} {flag} "
                  f"atteso={atteso} visto={visto} ({perche}). Numero NON stampato.")
            print(f"   opzioni lette per {cmd}: {sorted(per_comando.get(cmd, set()))}")
            return 2

    usi = insegnate()
    mancanti: list[tuple[str, str, str]] = []
    non_risolti: set[tuple[str, str]] = set()
    for cmd, flag, dove in usi:
        pezzi = cmd.split()
        scelto = None
        for k in range(len(pezzi), 0, -1):
            cand = " ".join(pezzi[:k])
            if cand in per_comando:
                scelto = cand
                break
        if scelto is None:
            non_risolti.add((cmd, dove))
            continue
        for f in flag.split("|"):
            if f in GLOBALI:
                continue
            if f not in per_comando[scelto]:
                mancanti.append((scelto, f, dove))

    print(f"comandi con le loro opzioni:  {len(per_comando)}")
    print("controllo positivo (3 facce): esplicita VISTA · derivata VISTA · "
          "inventata RIFIUTATA")
    print(f"usi documentati con opzioni:  {len(usi)}")
    print(f"comandi citati e non risolti: {len(non_risolti)}")
    print(f"OPZIONI INSEGNATE E ASSENTI:  {len(set(mancanti))}")
    print("")
    for cmd, f, dove in sorted(set(mancanti)):
        print(f"   {dove}:  verimem {cmd} {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
