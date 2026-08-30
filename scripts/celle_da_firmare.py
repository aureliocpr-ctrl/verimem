"""Elenca le celle del registro che QUALCUN ALTRO puo' firmare in un minuto.

Nasce da un dato, non da un'idea: le celle che dichiarano `rifallo con:` sono
passate da 1 a 17 in una sera, ma le firme restano tutte di una sola istanza.
La cura era stata adottata e la firma no ⇒ l'attrito non era piu' «la cella non
dice come rifarla», era «non so QUALI celle posso firmare senza rileggerle
tutte». Questo script toglie quel passo: un comando, la lista, il comando da
incollare.

Uso:
    python scripts/celle_da_firmare.py --io <NomeAgente>     # es. --io Varco

Stampa solo le celle NON tue e NON gia' firmate da te, con la riga
`rifallo con` estratta. Esce 0 sempre: e' un elenco, non un cancello.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

REGISTRO = pathlib.Path("docs/stato-reale/00-ESAME.md")
#: una FIRMA vera e' preceduta da un marcatore di chiusura. Senza questo
#: vincolo il conteggio include le celle che PARLANO di firme e si conta da
#: sola (misurato due volte il 29/08: davi 2 celle «a due firme» che nessuno
#: aveva firmato).
FIRMA = re.compile(r"(?:✅|✍️|_)\s*(?:\*\*)?(?:2ª |seconda )?firma @([A-Za-z0-9_-]+)")
#: Comandi che la disciplina della copia CONDIVISA vieta: otto istanze e un
#: solo albero, dove uno `stash pop` tocca il lavoro non committato delle
#: altre sette. La ricetta di una cella e' testo scritto da un'ALTRA, e puo'
#: CITARE un comando invece di proporlo — `LANT-41` racconta uno stash pop
#: gia' avvenuto, non chiede di rifarlo. Misurato il 30/08: 1 ricetta su
#: 139. Questo resta un elenco e non un cancello (vedi il docstring): la
#: riga si stampa lo stesso, con l'avviso accanto.
VIETATO = re.compile(r"git\s+(stash|checkout\s+--|reset|clean|push)"
                     r"|--no-verify|rm\s+-rf|requalify\s+--apply", re.I)

RIFALLO = re.compile(r"🔎\s*\*{0,2}(?:rifallo con|Rifallo con)\*{0,2}[^`]*`([^`]+)`")
#: gli ID del registro NON sono di una forma sola: accanto a `W2-57` ci sono
#: `LANT-41` e le celle NUMERICHE (`| 12 |`). Misurato il 30/08: le numeriche
#: sono 86, e le scrivono soprattutto le istanze che ricevono MENO controfirme
#: (ws6 16, ws8 6, ws5 5). Riconoscendo un solo formato questo elenco le
#: teneva fuori TUTTE, cioe' nascondeva proprio il lavoro che aveva piu'
#: bisogno di essere offerto. Un marcatore non marca chi non lo conosce.
CELLA = re.compile(r"^\| ((?:[A-Z]+\d*-)?\d+) \| ([^|]*)\|")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--io", required=True,
                    help="il tuo nome agente (le tue celle e le tue firme sono escluse)")
    ap.add_argument("--tutte", action="store_true",
                    help="mostra anche le celle senza riga `rifallo con`")
    a = ap.parse_args()
    if not REGISTRO.exists():
        print(f"NON RIUSCITO: {REGISTRO} non c'e' — lancia dalla radice del repo")
        return 2
    io_l = a.io.lower()
    righe = REGISTRO.read_text(encoding="utf-8").split("\n")
    trovate = 0
    #: quante ne sto SCARTANDO perche' non dicono come rifarle. Senza
    #: questo numero l'elenco si legge come «ecco tutto il lavoro che
    #: puoi firmare», mentre e' «ecco la parte che qualcuno ha reso
    #: rifacibile»: un taglio silenzioso si legge come copertura piena.
    #: Misurato il 30/08 sulle celle W2: 47 scartate su 108 (43,5%), e
    #: chi chiedeva le firme — io — non lo sapeva.
    nascoste = 0
    for riga in righe:
        m = CELLA.match(riga)
        if not m:
            continue
        cid, titolo = m.group(1), m.group(2).strip()
        firme = [f.lower() for f in FIRMA.findall(riga)]
        if io_l in firme:            # gia' firmata da me
            continue
        autore = re.search(r"\| (ws\d) \|", riga)
        if autore and autore.group(1).lower() == io_l:
            continue
        rif = RIFALLO.search(riga)
        if not rif and not a.tutte:
            nascoste += 1
            continue
        trovate += 1
        stato = f"{len(firme)} firma/e" if firme else "NESSUNA firma"
        print(f"\n  {cid}  [{stato}]  {titolo[:74]}")
        if rif:
            _cmd = rif.group(1)
            # La ricetta e' il PRIMO backtick dopo «rifallo con», e quando
            # quel backtick e' lontano appartiene a un'altra frase: LANT-33
            # rimanda a un blocco in cima al file e il primo backtick che
            # segue e' una variabile citata 245 caratteri piu' in la',
            # stampata come se fosse il comando da eseguire. Misurato il
            # 30/08: 12 ricette su 148 (8%), e una a distanza NEGATIVA —
            # il backtick veniva da prima della riga stessa.
            _q = riga.lower().find("rifallo con")
            _d = riga.find("`" + _cmd + "`", _q) - _q if _q >= 0 else 999
            if 0 <= _d <= 70:
                print(f"      $ {_cmd[:110]}")
            else:
                # niente falso `$`: si stampa cio' che la cella DICE.
                _testo = riga[_q:_q + 150].split("`")[0] if _q >= 0 else ""
                print(f"      ↪ {_testo.strip()[:110]}")
                print("      ⚠️  non e' un comando: la cella rimanda "
                      "a un altro punto. Leggila prima di eseguire.")
            if VIETATO.search(_cmd):
                print("      ⛔ NON ESEGUIRLA COSI': contiene un comando "
                      "che la disciplina della copia condivisa vieta. "
                      "Probabile CITAZIONE nel racconto, non una ricetta.")
    coda = "." if a.tutte else " (con la ricetta gia' pronta)."
    print(f"\n  ⇒ {trovate} celle che puoi firmare{coda}")
    if nascoste:
        _quota = 100 * nascoste / (trovate + nascoste)
        print(f"  ⚠️  {nascoste} celle NON mostrate: non dicono come "
              f"rifarle ({_quota:.0f}% del totale). Non sono firmabili da "
              "nessuno finche' non portano una riga `🔎 rifallo con`. "
              "Vedile con --tutte.")
    print("  Rifai il banco, poi aggiungi in fondo alla cella:")
    print(f"      ✅ **firma @{a.io} <ora>** — rifatta, <cosa hai ottenuto>.")
    print("  ⚠️ Se i numeri NON tornano scrivilo lo stesso: ritirare vale piu' che confermare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
