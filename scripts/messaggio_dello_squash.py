#!/usr/bin/env python3
"""Il messaggio con cui una PR entra in main, composto invece che scritto a mano.

    python scripts/messaggio_dello_squash.py <numero>          # stampa il messaggio
    python scripts/messaggio_dello_squash.py <numero> --file M # lo scrive su M
    python scripts/messaggio_dello_squash.py --tutte           # li prova tutti

PERCHE' NON BASTA LASCIAR FARE A GITHUB. Le impostazioni di questo repository
dicono (`gh api repos/<owner>/<repo>`):

    squash_merge_commit_message : COMMIT_MESSAGES
    squash_merge_commit_title   : COMMIT_OR_PR_TITLE

`COMMIT_MESSAGES` vuol dire che il corpo del commit di squash e' la
CONCATENAZIONE dei messaggi dei commit della PR. Misurato il 12/09 alle 13:55,
su 20 PR aperte: **70 messaggi su 130 sono sporchi**, e una PR ne ha 48 (il
numero porta la sua popolazione e la sua ora: dipende da quante PR sono aperte,
e in mezza giornata e' gia' passato da 66 su 99 su 14 PR). Lasciando il
valore predefinito, in main entrerebbe quel muro di testo — che e' esattamente
il `git log` che stiamo ripulendo.

E `COMMIT_OR_PR_TITLE` mette `(#N)` solo quando la PR ha PIU' di un commit: le
PR di un commit solo entrerebbero senza numero.

⇒ Il messaggio si COMPONE da cio' che gia' esiste ed e' gia' pulito: il titolo
della PR e le due righe che ogni corpo porta dal 12/09 (riga 1 = cosa cambia per
chi usa il prodotto, riga 2 = come e' provato). Quattro righe, sempre la stessa
forma, e il numero della PR nel titolo.

🔑 IL NUMERO NEL TITOLO NON E' COSMESI. Dopo uno squash i commit originali non
sono antenati di main e il loro patch-id non esiste piu' (provato: 0 su 7).
Dopo un rebase gli SHA cambiano e `--is-ancestor` risponde NO su lavoro che c'e'
(provato: 0 su 7, patch-id 7 su 7). **L'unico appiglio che regge a tutt'e due e'
il numero della PR**, e oggi zero dei quaranta commit di main ce l'ha. Con
`(#N)` scritto, «la cura e' in main?» si risponde cosi':

    git log --oneline --grep "(#<N>)" origin/main
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

RADICE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "scripts"))

from messaggio_pulito import controlla  # noqa: E402

# La checklist DoD comincia con un titoletto: il corpo utile e' cio' che viene prima.
DOD = re.compile(r"^#+\s*Definition of Done", re.MULTILINE | re.IGNORECASE)
# La riga di attribuzione dello strumento non e' parte del racconto.
CODA = re.compile(r"^\s*🤖.*$", re.MULTILINE)


def _gh(*argomenti: str) -> str:
    fatto = subprocess.run(["gh", *argomenti], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    if fatto.returncode != 0:
        raise SystemExit(f"gh {' '.join(argomenti)}: {fatto.stderr.strip()[:160]}")
    return fatto.stdout


def due_righe(corpo: str) -> list[str]:
    """Le righe del corpo prima della checklist, senza la coda dello strumento."""
    corpo = DOD.split(corpo)[0]
    corpo = CODA.sub("", corpo)
    return [r.strip() for r in corpo.splitlines() if r.strip()]


def componi(numero: int) -> tuple[str, list[str]]:
    dati = json.loads(_gh("pr", "view", str(numero), "--json", "title,body"))
    righe = due_righe(dati["body"] or "")
    if not righe:
        # Un corpo vuoto non si riempie da soli: si dice che manca.
        raise SystemExit(
            f"#{numero}: il corpo non ha righe prima della checklist. "
            "Il messaggio dello squash si compone da quelle: scrivile nella PR.")
    testo = f"{dati['title']} (#{numero})\n\n" + "\n".join(righe) + "\n"
    return testo, controlla(testo)


def tutte() -> int:
    numeri = [v["number"] for v in json.loads(
        _gh("pr", "list", "--state", "open", "--limit", "50", "--json", "number"))]
    sporche = 0
    for n in sorted(numeri, reverse=True):
        try:
            testo, problemi = componi(n)
        except SystemExit as e:
            print(f"  FERMO    #{n:<3} {e}")
            sporche += 1
            continue
        righe = len([r for r in testo.splitlines() if r.strip()])
        if problemi:
            sporche += 1
            print(f"  BOCCIATO #{n:<3} {righe} righe  {testo.splitlines()[0][:52]}")
            for p in problemi:
                print(f"              - {p}")
        else:
            print(f"  ok       #{n:<3} {righe} righe  {testo.splitlines()[0][:52]}")
    print()
    if sporche:
        print(f"VERDETTO: ROSSO - {sporche} PR su {len(numeri)} non hanno un "
              "messaggio di squash pulito da comporre.")
        return 1
    print(f"VERDETTO: VERDE - tutte e {len(numeri)} le PR aperte hanno un "
          "messaggio di squash pulito, gia' composto e gia' col numero.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("numero", nargs="?", type=int)
    p.add_argument("--file", help="scrivi il messaggio su questo file")
    p.add_argument("--tutte", action="store_true")
    a = p.parse_args(argv)
    if a.tutte:
        return tutte()
    if a.numero is None:
        p.error("serve il numero della PR, oppure --tutte")
    testo, problemi = componi(a.numero)
    if problemi:
        print(f"IL MESSAGGIO COMPOSTO NON E' PULITO — #{a.numero}:", file=sys.stderr)
        for x in problemi:
            print(f"  - {x}", file=sys.stderr)
        print(testo, file=sys.stderr)
        return 1
    if a.file:
        pathlib.Path(a.file).write_text(testo, encoding="utf-8")
        print(f"scritto su {a.file}")
    else:
        print(testo, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
