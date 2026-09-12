#!/usr/bin/env python3
"""Una chiave scritta due volte nello stesso blocco YAML: `safe_load` la nasconde.

    python scripts/chiavi_doppie.py .github/workflows/*.yml
    python scripts/chiavi_doppie.py --autotest

🔴 PERCHE' ESISTE, 12/09. Ho modificato `ci.yml` lasciando per sbaglio la chiave
`matrix:` vecchia sopra quella nuova:

    strategy:
      fail-fast: false
      matrix:                                   <- orfana
      matrix: ${{ fromJSON(...) }}              <- la nuova

L'ho validato con `yaml.safe_load` e **e' passato**: la libreria tiene
l'ultima e non dice niente. GitHub l'ha rifiutato, due volte, con

    run …  name=.github/workflows/ci.yml  completed/failure  jobs=0
    «This run likely failed because of a workflow file issue»

e nessun messaggio leggibile dall'API. Ho passato mezz'ora a cercare l'errore
nell'espressione della matrice — che era giusta — perche' il mio validatore
misurava a un livello a cui il difetto non esiste.

🔑 **Il livello a cui misuri decide il verdetto.** Un file «YAML valido» non e'
un file che il suo consumatore accetta: qui il consumatore e' il parser di
Actions, e la distanza fra i due e' esattamente questa classe di difetti.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import yaml


class _Severo(yaml.SafeLoader):
    """SafeLoader che si RIFIUTA di scegliere quando una chiave e' ripetuta.

    ⚠️ EREDITA DA `SafeLoader` e sostituisce SOLO il costruttore delle mappe:
    non puo' costruire oggetti Python arbitrari, quindi `yaml.load` con questo
    loader e' sicuro quanto `safe_load`. Sta scritto qui perche' `yaml.load`
    e' una riga che fa giustamente alzare un sopracciglio a chi la legge.
    """


def _mappa_senza_doppioni(loader, nodo, deep=False):  # noqa: ANN001
    mappa = {}
    for chiave_n, valore_n in nodo.value:
        chiave = loader.construct_object(chiave_n, deep=deep)
        if chiave in mappa:
            raise yaml.constructor.ConstructorError(
                "mentre leggo una mappa", nodo.start_mark,
                f"la chiave «{chiave}» e' scritta due volte nello stesso blocco: "
                "la seconda cancella la prima in silenzio",
                chiave_n.start_mark)
        mappa[chiave] = loader.construct_object(valore_n, deep=deep)
    return mappa


_Severo.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mappa_senza_doppioni)


def controlla(percorso: pathlib.Path) -> str | None:
    """Il problema in chiaro, o None se il file e' pulito."""
    try:
        yaml.load(percorso.read_text(encoding="utf-8"), Loader=_Severo)
    except yaml.YAMLError as e:
        return str(e).replace("\n", " ")[:300]
    return None


DOPPIA = """a: 1
b:
  c: 2
  c: 3
"""
SINGOLA = """a: 1
b:
  c: 2
  d: 3
"""


def autotest() -> int:
    esiti = []
    for nome, testo, deve_cadere in (("una chiave ripetuta", DOPPIA, True),
                                     ("nessuna ripetuta", SINGOLA, False)):
        try:
            yaml.load(testo, Loader=_Severo)
            caduto = False
        except yaml.YAMLError:
            caduto = True
        ok = caduto == deve_cadere
        esiti.append(ok)
        print(f"  [{'OK ' if ok else 'ROSSO'}] {nome:26s} -> "
              f"{'rifiutato' if caduto else 'accettato'}")
    # Il controllo che prova che `safe_load` NON lo vede: se lo vedesse,
    # questo script non servirebbe, e la ragione scritta sopra sarebbe falsa.
    try:
        d = yaml.safe_load(DOPPIA)
        cieco = d["b"]["c"] == 3
    except yaml.YAMLError:
        cieco = False
    esiti.append(cieco)
    print(f"  [{'OK ' if cieco else 'ROSSO'}] {'safe_load NON la vede':26s} -> "
          f"{'tiene l ultima, in silenzio' if cieco else 'la vede: lo script e inutile'}")
    print()
    if all(esiti):
        print(f"AUTOTEST VERDE: {len(esiti)} su {len(esiti)}.")
        return 0
    print(f"AUTOTEST ROSSO: {esiti.count(False)} sbagliati su {len(esiti)}.")
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("file", nargs="*", type=pathlib.Path)
    p.add_argument("--autotest", action="store_true")
    a = p.parse_args(argv)
    if a.autotest:
        return autotest()
    if not a.file:
        p.error("serve almeno un file, oppure --autotest")
    sporchi = 0
    for f in a.file:
        problema = controlla(f)
        if problema:
            sporchi += 1
            print(f"  BOCCIATO {f}")
            print(f"           {problema}")
        else:
            print(f"  ok       {f}")
    print()
    if sporchi:
        print(f"VERDETTO: ROSSO - {sporchi} file su {len(a.file)} hanno una "
              "chiave scritta due volte.")
        return 1
    print(f"VERDETTO: VERDE - {len(a.file)} file, nessuna chiave ripetuta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
