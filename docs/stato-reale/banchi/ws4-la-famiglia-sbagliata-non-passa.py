# -*- coding: utf-8 -*-
"""IL README PROMETTE CHE LA FAMIGLIA SBAGLIATA NON PASSA. E' VERO?

`verimem trust --help` fa una promessa precisa e falsificabile:

    «the ref has to MATCH THE KIND OF CLAIM, because each detector accepts its
     own family: "works/tested" wants runtime evidence that also shows it
     PASSED (--verified-by pytest:1234_passed), "shipped/merged" wants
     commit:<sha> or pr:#12 … A commit sha does not prove something works, and
     a passing test does not prove it shipped: GIVE THE WRONG FAMILY AND THE
     CLAIM STAYS FLAGGED. Exit 0 if trusted, 1 if flagged.»

E' la promessa piu' verificabile che ho trovato nella vetrina: due tipi di
claim, due famiglie di prova, un exit code dichiarato. Se la famiglia sbagliata
passasse, chiunque potrebbe far passare un «funziona» con uno sha di commit —
che e' esattamente cio' che il prodotto dice di impedire.

IL DISEGNO — una matrice 2x2, una variabile per cella:
                        pytest:...        commit:<sha>
    «works/tested»      atteso 0          atteso 1  ← famiglia sbagliata
    «shipped/merged»    atteso 1          atteso 0  ← famiglia sbagliata
La diagonale deve passare, l'antidiagonale no.

CONTROLLI, e sono tre:
  · SENZA REF   — lo stesso claim senza prova deve restare flagged (1).
    Senza, non saprei se il ref serve a qualcosa.
  · NEUTRO      — un claim che non e' un self-claim deve passare (0).
    Senza, un gate che flagga TUTTO darebbe la matrice giusta per il motivo
    sbagliato.
  · NON SCRIVE  — l'help dice «would Verimem trust», al condizionale. CONTO i
    fatti prima e dopo: se il numero cambia, `trust` scrive e la promessa e'
    rotta in un modo piu' grave della matrice.
"""
import os
import re
import subprocess
import sys

PY = sys.executable
REPO = os.environ.get("WS4_REPO", ".")

# ⚠️ I DUE CLAIM SONO SCELTI PERCHE' ACCENDONO IL CONTROLLO, non a gusto mio.
# I primi che avevo messo («the retry helper works and is tested end to end»,
# «… shipped and is merged into main») passavano ANCHE SENZA REF: su quelli la
# matrice non dice niente sulla famiglia, dice solo che quel claim non viene
# flaggato. Sondati sei claim, questi due sono quelli che senza prova escono 1.
LAVORA = "all tests pass and the module is verified"
SPEDITO = "this feature is done and shipped"
PYTEST = "pytest:1234_passed"
COMMIT = "commit:9f3a1c7d2b4e5a6f8c0d1e2f3a4b5c6d7e8f9a0b"


def trust(claim, ref=None):
    cmd = [PY, "-m", "verimem.cli", "trust", claim]
    if ref:
        cmd += ["--verified-by", ref]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                       cwd=REPO)
    return r.returncode, (r.stdout or "")


def quanti_fatti():
    r = subprocess.run([PY, "-m", "verimem.cli", "status"],
                       capture_output=True, text=True, timeout=300, cwd=REPO)
    m = re.search(r"semantic facts:\s*([0-9]+)", r.stdout or "")
    return int(m.group(1)) if m else None


prima = quanti_fatti()
print(f"  fatti in memoria PRIMA: {prima}")

print("\n  == LA MATRICE (una variabile per cella) ==")
casi = [
    ("works/tested",   LAVORA,  PYTEST, 0, "famiglia GIUSTA"),
    ("works/tested",   LAVORA,  COMMIT, 1, "famiglia SBAGLIATA"),
    ("shipped/merged", SPEDITO, COMMIT, 0, "famiglia GIUSTA"),
    ("shipped/merged", SPEDITO, PYTEST, 1, "famiglia SBAGLIATA"),
]
esiti = []
for tipo, claim, ref, atteso, nota in casi:
    e, out = trust(claim, ref)
    ok = (e == atteso)
    esiti.append(ok)
    print(f"   {tipo:16s} {ref.split(':')[0]:8s} → EXIT={e} (atteso"
          f" {atteso})  {'✅' if ok else '⛔ NON COME PROMESSO'}   {nota}")

print("\n  == I CONTROLLI ==")
e_senza, _ = trust(LAVORA)
print(f"   SENZA REF  «{LAVORA[:34]}…» → EXIT={e_senza} (atteso 1)"
      f"   {'ACCESO' if e_senza == 1 else 'SPENTO: il ref non serve a nulla'}")
neutro = "the configuration file lists three retry attempts"
e_neutro, _ = trust(neutro)
print(f"   NEUTRO     «{neutro[:34]}…» → EXIT={e_neutro} (atteso 0)"
      f"   {'ACCESO' if e_neutro == 0 else 'SPENTO: il gate flagga tutto'}")
dopo = quanti_fatti()
print(f"   NON SCRIVE  fatti prima {prima} · dopo {dopo}"
      f"   {'ACCESO (nessuna scrittura)' if prima == dopo else '⛔ HA SCRITTO'}")

print("\n  == IL VERDETTO ==")
if e_senza != 1 or e_neutro != 0:
    print("   ⛔ i controlli non sono accesi: la matrice non si legge.")
elif all(esiti):
    print("   ✅ LA PROMESSA REGGE su tutte e quattro le celle: la famiglia")
    print("      sbagliata NON passa, e quella giusta si'.")
else:
    quali = [f"{c[0]}+{c[2].split(':')[0]}" for c, o in zip(casi, esiti)
             if not o]
    print(f"   🔴 LA PROMESSA CADE su {len(quali)} celle su 4: {quali}")
