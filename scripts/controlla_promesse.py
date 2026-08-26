#!/usr/bin/env python
"""Dove vive una promessa dentro l'artefatto che si sta per pubblicare.

`controlla_registro.py` verifica che il pacchetto non nomini chi l'ha scritto.
Questo verifica una cosa diversa e non coperta: **che una promessa non sia
scritta in più posti**, perché quando lo è, curarne uno lascia gli altri.

Il caso che ha motivato lo strumento: la promessa sulle citazioni esatte è stata
precisata in `agent_guide.py`, e la stessa promessa continuava a vivere — nella
formulazione vecchia — nel README che diventa la pagina PyPI e nella
``description`` di un tool MCP, cioè nel testo che l'agente dell'utente legge a
runtime. Il pacchetto era già stato dichiarato pronto da un altro controllo.

    python scripts/controlla_promesse.py dist/verimem-0.7.5-py3-none-any.whl
    python scripts/controlla_promesse.py .  --frase "exact citation"

Uscita 0 sempre: **questo non è un veto**. Una promessa su più superfici non è
un difetto — è un rischio, e chi rilascia decide. Un veto qui bloccherebbe ogni
rilascio, e un controllo che blocca sempre viene disattivato.

Le superfici sono nominate perché non pesano uguale: il METADATA è la pagina
pubblica, una ``description`` di tool la legge una macchina, un docstring lo
legge chi apre il file.
"""

from __future__ import annotations

import pathlib
import re
import sys
import tarfile
import zipfile
from collections import defaultdict

#: FORMULAZIONI di promessa già viste vivere su più superfici. È un registro di
#: casi, non una teoria: cresce quando se ne trova un'altra.
#:
#: Devono essere *formule*, non termini del dominio. Il primo elenco conteneva
#: anche ``abstain`` e ``quarantined``: danno 105 e 390 occorrenze, e a quel
#: punto il controllo segnala tutto e non separa niente — un termine che il
#: prodotto usa ovunque non è una promessa scritta in più posti, è il suo
#: vocabolario. È lo stesso errore che ``controlla_registro.py`` faceva
#: confondendo un'attribuzione con un'omonimia: un criterio lessicale non
#: distingue la formula dalla parola.
FRASI = (
    "exact citation",
    "never silently",
)

ESCLUSE = frozenset({
    "build", "dist", ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".tox", ".mypy_cache", ".pytest_cache", "site-packages",
})


def _superficie(nome: str) -> str:
    """Che cosa è il file per chi riceve il pacchetto."""
    if nome.endswith("METADATA") or nome.endswith("PKG-INFO"):
        return "pagina pubblica (METADATA)"
    if nome.endswith("README.md"):
        return "README nel sorgente"
    if "mcp_server" in nome:
        return "description dei tool (la legge l'agente)"
    if "agent_guide" in nome:
        return "guida per l'agente"
    if nome.endswith("cli.py"):
        return "aiuto della riga di comando"
    return "sorgente"


def _sorgenti(percorso: pathlib.Path):
    if percorso.is_dir():
        for p in sorted(percorso.rglob("*")):
            if not p.is_file() or ESCLUSE & set(p.parts):
                continue
            if p.suffix not in (".py", ".md") and p.name not in ("METADATA", "PKG-INFO"):
                continue
            yield str(p.relative_to(percorso)).replace("\\", "/"), p.read_text(
                encoding="utf-8", errors="replace")
    elif percorso.suffix in (".whl", ".zip"):
        with zipfile.ZipFile(percorso) as z:
            for nome in sorted(z.namelist()):
                if nome.endswith((".py", ".md", "METADATA", "PKG-INFO")):
                    yield nome, z.read(nome).decode("utf-8", errors="replace")
    else:
        with tarfile.open(percorso) as t:
            for m in sorted(t.getmembers(), key=lambda x: x.name):
                if m.isfile() and m.name.endswith((".py", ".md", "PKG-INFO")):
                    f = t.extractfile(m)
                    if f is not None:
                        yield m.name, f.read().decode("utf-8", errors="replace")


def controlla(percorso: pathlib.Path, frasi: tuple[str, ...]) -> int:
    dove: defaultdict[str, list[tuple[str, int]]] = defaultdict(list)
    for nome, testo in _sorgenti(percorso):
        for frase in frasi:
            n = len(re.findall(re.escape(frase), testo, re.I))
            if n:
                dove[frase].append((nome, n))

    print(f"artefatto: {percorso}\n")
    for frase in frasi:
        righe = dove.get(frase, [])
        if not righe:
            print(f"  «{frase}» — assente")
            continue
        tot = sum(n for _, n in righe)
        # ⚠️ «FORMULA», non «promessa» — corretto il 2026-08-26, perché la
        # parola sbagliata faceva contare un debito che non c'era. Questo
        # script cerca una STRINGA: lo dice il commento di `FRASI` più sopra
        # («FORMULAZIONI di promessa»), e il messaggio invece diceva
        # «promesse», che è cosa diversa.
        #
        # Misurato sul wheel 0.7.6: «never silently» → 12 occorrenze in 8
        # file, marcate SU PIÙ SUPERFICI. Aperte le occorrenze, sono promesse
        # DIVERSE che condividono la formula: «a caught hallucination is
        # reported, never silently dropped» (client), «never silently
        # admitted» (composer), «a hit never silently disappears from the
        # result» (semantic), «who ASKED for signing must never silently not
        # get it» (tamper_evidence). Chi legge questo avviso prima di un
        # rilascio contava otto superfici da riconciliare e ne trovava UNA
        # vera. Il conteggio era esatto; la parola no.
        marchio = ("la stessa FORMULA su più superfici" if len(righe) > 1
                   else "in un posto solo")
        print(f"  «{frase}» — {tot} occorrenze in {len(righe)} file · {marchio}")
        for nome, n in righe:
            print(f"       {n:>3d}  {nome}   [{_superficie(nome)}]")
        print()

    sparse = [f for f in frasi if len(dove.get(f, [])) > 1]
    if sparse:
        print("Queste FORMULE vivono su più superfici. Dove le occorrenze sono la\n"
              "STESSA promessa, precisarne una lascia le altre com'erano: prima di\n"
              "pubblicare, verificare che dicano ancora la stessa cosa.\n"
              "Ma una formula condivisa può coprire promesse DIVERSE — aprire le\n"
              "occorrenze prima di contarle come un debito.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    scelte = FRASI
    if "--frase" in sys.argv:
        scelte = (sys.argv[sys.argv.index("--frase") + 1],)
    sys.exit(controlla(pathlib.Path(sys.argv[1]), scelte))
