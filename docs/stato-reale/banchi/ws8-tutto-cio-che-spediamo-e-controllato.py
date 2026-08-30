#!/usr/bin/env python
"""Il controllo sul registro guarda TUTTO cio' che il pacchetto spedisce?

PERCHE' ESISTE
  Il 2026-08-30 alle 19:03 avevo proposto di mettere nel pre-commit

      python scripts/controlla_registro.py verimem

  e venti minuti dopo ho scoperto che copriva **422 file su 424**. Il motivo sta
  in `pyproject.toml`::

      include = ["verimem*", "engram*", "hippoagent*"]

  Il wheel impacchetta TRE radici; il mio comando ne guardava UNA. I due file
  mancanti sono gli shim di compatibilita' — spediti all'utente, e non guardati.

  🔑 Avevo contato **la cartella che conoscevo**, non **quelle che il pacchetto
  imbarca**. La differenza fra «cosa controllo?» e «cosa viene spedito?» ERA il
  difetto. E la lista scritta a mano non risolve: la sposta di un gradino. Se
  domani `pyproject.toml` aggiunge una quarta radice, un comando con tre nomi
  cablati continua a dire EXIT=0 e nessuno se ne accorge.

COSA FA
  Legge le radici DALLA FONTE (`pyproject.toml`), le espande sul disco, e per
  ognuna esegue `scripts/controlla_registro.py`. Poi dichiara **tre numeri
  separati**: radici dichiarate, radici trovate, radici controllate. Se non
  coincidono lo dice — perche' una radice dichiarata e non trovata non e' uno
  zero, e' un buco.

COSA NON FA
  Non costruisce il wheel: gira sui sorgenti. L'equivalenza fra i due criteri e'
  stata misurata il 30/08 con un A/B a variabile singola (una cartella con e
  senza un file che porta un nome proprio: EXIT 1 e EXIT 0, e la riga nominata).
  Resta vero che il wheel puo' contenere file GENERATI dal build, che qui non
  esistono ancora: quel residuo non e' coperto.

    python docs/stato-reale/banchi/ws8-tutto-cio-che-spediamo-e-controllato.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[3]
CONTROLLO = RADICE / "scripts" / "controlla_registro.py"


def radici_dichiarate() -> list[str]:
    """I pattern che `pyproject.toml` dice di impacchettare.

    Si legge la FONTE e non una lista scritta qui: una lista qui invecchierebbe
    esattamente come quella che questo banco esiste per sostituire.
    """
    testo = (RADICE / "pyproject.toml").read_text(encoding="utf-8")
    blocco = re.search(r"^include\s*=\s*\[([^\]]*)\]", testo, re.M)
    if not blocco:
        return []
    return re.findall(r'"([^"]+)"', blocco.group(1))


def main() -> int:
    print("TUTTO CIO' CHE SPEDIAMO E' CONTROLLATO?\n")
    pattern = radici_dichiarate()
    if not pattern:
        print("  ?  `pyproject.toml` non dichiara `include`: non so cosa viene spedito.")
        print("     Questo NON e' un «va bene»: e' un'astensione. Il banco esce 1.")
        return 1
    print(f"  radici DICHIARATE in pyproject.toml: {len(pattern)}  ->  {', '.join(pattern)}\n")

    trovate: list[Path] = []
    orfani: list[str] = []
    for p in pattern:
        corrisp = sorted(d for d in RADICE.glob(p)
                         if d.is_dir() and not d.name.endswith(".egg-info"))
        if not corrisp:
            orfani.append(p)
        trovate.extend(corrisp)

    esito = 0
    totale_file = 0
    for d in trovate:
        fatto = subprocess.run([sys.executable, str(CONTROLLO), str(d)],
                               capture_output=True, text=True, errors="replace", timeout=600)
        uscita = (fatto.stdout or "") + (fatto.stderr or "")
        quanti = re.search(r"file \.py esaminati:\s*(\d+)", uscita)
        n = int(quanti.group(1)) if quanti else 0
        totale_file += n
        blocca = [r.strip() for r in uscita.splitlines() if "BLOCCA" in r]
        segno = "FERMA" if fatto.returncode != 0 else "passa"
        esito |= fatto.returncode
        print(f"  {d.name:<22} {segno:<6} EXIT={fatto.returncode}  file .py = {n}")
        for r in blocca:
            print(f"      {r}")

    print(f"\n  radici dichiarate {len(pattern)} · trovate sul disco {len(trovate)} · "
          f"controllate {len(trovate)} · file .py totali {totale_file}")
    if orfani:
        print(f"  ⚠️  DICHIARATE E NON TROVATE: {len(orfani)}  ->  {', '.join(orfani)}")
        print("      Un pattern senza corrispondenza non e' un «niente da controllare»:")
        print("      o il pacchetto dichiara cio' che non ha, o il glob non le trova e")
        print("      qualcosa viene spedito senza passare di qui. Va guardato.")
        esito |= 1
    print(f"\n  ⇒ EXIT del banco: {esito}   (0 = tutto cio' che risulta spedito e' pulito)")
    print("  ⚖️  Il banco gira sui SORGENTI. Se il build genera file .py, quelli non")
    print("      esistono ancora e nessun controllo sui sorgenti puo' vederli.")
    return esito


if __name__ == "__main__":
    sys.exit(main())
