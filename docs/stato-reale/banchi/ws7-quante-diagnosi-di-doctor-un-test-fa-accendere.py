"""`doctor` è la voce che dice all'utente se sta bene: chi controlla la voce?

`verimem/doctor.py` (1.478 righe) emette **63 esiti** — ogni `add(nome, stato,
dettaglio)` è una diagnosi che un utente può leggersi in faccia. La domanda del
product owner non è «doctor funziona?»: è **«se un check smette di accorgersi
del guasto e dice OK per sempre, chi se ne accorge?»**

Un check rotto è più pericoloso di un check assente: l'assente non dice niente,
il rotto dice *«va tutto bene»*. È il quarto stato di un test — *il guardiano
che mente* — applicato al guardiano ufficiale del prodotto.

CRITERIO, e resta STRUTTURALE: si guardano solo i file di test che chiamano
`run_doctor(`, e dentro quelli si cerca il **nome del check quotato**. Cercare
il nome in tutta la suite non discriminerebbe (`version`, `mcp`, `daemon` sono
parole comuni); restringere ai file che invocano davvero il doctor sì.

📏 PORTATA: «nominato» ≠ «tutti i suoi esiti provati». Un check con tre esiti
(OK/WARN/FAIL) risulta coperto anche se un test ne prova uno solo — quindi
questo righello **sottostima** il buco. Meglio accusare di meno.

🔑 CONTROLLO POSITIVO A DUE FACCE, sulla forma che potrebbe sfuggire:
  · un nome che DEVE risultare coperto (`gateway`, provato da
    `test_doctor_conta_le_chiavi_invece_di_dedurle.py`);
  · un nome inventato che DEVE risultare scoperto.
Stasera tre righelli miei hanno taciuto perché il controllo positivo toccava una
forma che già funzionava: qui la faccia negativa c'è apposta.

Uso::

    python docs/stato-reale/banchi/ws7-quante-diagnosi-di-doctor-un-test-fa-accendere.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RADICE = Path(__file__).resolve().parents[3]
DOCTOR = RADICE / "verimem" / "doctor.py"
TESTS = RADICE / "tests"

_ADD = re.compile(r"\badd\(\s*[\"']([\w.-]+)[\"']\s*,\s*(\w+)", re.S)


def esiti() -> dict[str, set[str]]:
    fuori: dict[str, set[str]] = defaultdict(set)
    for nome, stato in _ADD.findall(DOCTOR.read_text(encoding="utf-8")):
        fuori[nome].add(stato)
    return dict(fuori)


def nominati_dai_test() -> tuple[set[str], int]:
    visti: set[str] = set()
    quanti = 0
    for f in sorted(TESTS.rglob("test_*.py")):
        try:
            testo = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "run_doctor(" not in testo:
            continue
        quanti += 1
        for tok in re.findall(r"[\"']([\w.-]+)[\"']", testo):
            visti.add(tok)
    return visti, quanti


def main() -> int:
    per_nome = esiti()
    visti, quanti_file = nominati_dai_test()

    if "gateway" not in visti:
        print("!! righello CIECO: 'gateway' non risulta nominato dai test del "
              "doctor, ma test_doctor_conta_le_chiavi_invece_di_dedurle.py lo "
              "interroga. Numero NON stampato.")
        return 2
    if "questo-check-non-esiste" in visti:
        print("!! righello COMPIACENTE: vede un nome inventato.")
        return 2

    scoperti = sorted(n for n in per_nome if n not in visti)
    tot_esiti = sum(len(v) for v in per_nome.values())
    testo_doctor = DOCTOR.read_text(encoding="utf-8")
    chiamate = len(re.findall(r'add\(\s*"[A-Za-z0-9._-]+"', testo_doctor))
    print(f"doctor.py:                    {len(testo_doctor.splitlines())} righe")
    print(f"file di test che lo invocano: {quanti_file}")
    print(f"chiamate add(<nome>, …):      {chiamate}")
    print(f"check distinti:               {len(per_nome)}")
    print(f"coppie (check, stato):        {tot_esiti}")
    print("controllo positivo (2 facce): 'gateway' VISTO · inventato RIFIUTATO")
    print(f"CHECK CHE NESSUN TEST NOMINA: {len(scoperti)}")
    print("")
    for n in scoperti:
        print(f"   {n}   (esiti: {', '.join(sorted(per_nome[n]))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
