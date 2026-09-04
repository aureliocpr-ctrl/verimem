# -*- coding: utf-8 -*-
"""OGNI COMANDO CHE IL README MOSTRA A UN UTENTE, ESISTE DAVVERO?

Il paragone promesso/fatto nella sua forma piu' diretta: la vetrina mostra a
un utente nuovo una lista di comandi da copiare. Se uno non esiste, il primo
minuto di quell'utente finisce con un errore.

IL RIGHELLO, gia' validato oggi per caso: `verimem <cmd> --help` esce
  · EXIT=0  se il comando esiste
  · EXIT=2  con «Error» se non esiste
L'ho scoperto stamattina cercando `forget`, che nel README non c'e' ma che io
davo per scontato: il suo `--help` usciva 2. Qui lo uso di proposito.

⚠️ `--help` NON esegue il comando: nessun dato viene toccato.

CONTROLLI OBBLIGATORI, tutti e due:
  · POSITIVO — un comando che esiste di sicuro (`doctor`) deve dare 0.
  · NEGATIVO — un nome inventato deve dare 2. Senza questo, un righello che
    dicesse sempre 0 direbbe «va tutto bene» ed e' il modo piu' facile di
    pubblicare un verde falso.

⚠️ LIMITE: raccolgo i comandi con una regola LESSICALE sulle righe del README
(una riga che comincia con `verimem `/`engram `, dentro o fuori un blocco di
codice). Un comando nominato in mezzo a una frase non lo vedo ⇒ il numero e'
un MINIMO. E non verifico che il comando FACCIA quel che il README promette:
solo che ESISTA.
"""
import io
import os
import re
import subprocess
import sys

README = os.environ.get("WS4_README", "README.md")
PY = sys.executable

testo = io.open(README, encoding="utf-8").read()
comandi, dove = {}, {}
for n, riga in enumerate(testo.split("\n"), 1):
    m = re.match(r"^\s*(?:verimem|engram|hippo)\s+([a-z][a-z0-9-]*)", riga)
    if m:
        c = m.group(1)
        comandi.setdefault(c, 0)
        comandi[c] += 1
        dove.setdefault(c, n)

print(f"  comandi distinti mostrati dal README: {len(comandi)}"
      f"   (in {sum(comandi.values())} righe)")


def prova(nome):
    r = subprocess.run([PY, "-m", "verimem.cli", nome, "--help"],
                       capture_output=True, text=True, timeout=120)
    return r.returncode


print("\n  == I CONTROLLI (senza, il numero non si legge) ==")
pos = prova("doctor")
neg = prova("questo-comando-non-esiste-xyz")
print(f"   POSITIVO  `doctor --help`                    → EXIT={pos}"
      f"   {'ACCESO' if pos == 0 else 'SPENTO'}")
print(f"   NEGATIVO  `questo-comando-non-esiste-xyz`    → EXIT={neg}"
      f"   {'ACCESO' if neg != 0 else 'SPENTO'}")
if pos != 0 or neg == 0:
    print("   ⛔ RIGHELLO ROTTO: non pubblico niente.")
    raise SystemExit(0)

print("\n  == I COMANDI DEL README, uno per uno ==")
mancanti, presenti = [], []
for c in sorted(comandi):
    e = prova(c)
    if e == 0:
        presenti.append(c)
    else:
        mancanti.append((c, e, dove[c]))
        print(f"   ⛔ {c:24s} EXIT={e}   README riga {dove[c]}")
print(f"\n   presenti: {len(presenti)}/{len(comandi)}"
      f"   ·  mancanti: {len(mancanti)}")
if not mancanti:
    print("   ✅ ogni comando che il README mostra esiste nella CLI installata.")
print(f"\n   (i presenti: {' '.join(presenti)})")
