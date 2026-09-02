"""Quante modifiche possono cambiare il verdetto del gate, e quante toccano il CODICE?

Nasce da un mio errore: ho pubblicato due volte «11 commit su
anti_confab_gate.py fra i due punti», e la cura che HA CAMBIATO il verdetto —
`c857752e`, l'apostrofo — NON E' in quella lista: sta in `subject_extract.py`.
⇒ contare i commit del modulo del gate NON copre le cause che cambiano il gate.
E' la classe ② del metodo (manca lo sweep: chi altro fa la stessa cosa?).

CRITERIO, dichiarato prima:
  · PERIMETRO = i moduli che concorrono al verdetto, non il solo gate
  · un commit «tocca il CODICE» se nel diff esiste almeno una riga aggiunta o
    rimossa che NON sia un commento (dopo lo spazio non inizia per #) e non sia
    vuota. E' grezzo: una riga di docstring conta come codice.
  · gli altri sono «igiene» (commenti, docstring, riferimenti)

DUE CONTROLLI CHE DEVONO ACCENDERSI, uno per verso:
  · `c857752e` (apostrofo)                    -> deve risultare CODICE
  · `8def48d1` (i due commenti citavano…)     -> deve risultare IGIENE
Se uno dei due sbaglia, il criterio non separa e i numeri non vanno usati.
"""
import subprocess
import sys

DA = "2026-08-26 00:00"
MODULI = [
    "verimem/anti_confab_gate.py",
    "verimem/subject_extract.py",
    "verimem/quantity_match.py",
    "verimem/grounding_gate.py",
    "verimem/admission_gate.py",
    "verimem/supersession_policy.py",
]


def sh(args):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def tocca_codice(sha, path):
    diff = sh(["git", "show", "--format=", "--unified=0", sha, "--", path])
    for r in diff.splitlines():
        if r.startswith(("+++", "---")):
            continue
        if r[:1] in "+-":
            corpo = r[1:].strip()
            if corpo and not corpo.startswith("#"):
                return True
    return False


print(f"  finestra: dal {DA}\n")
per_modulo, tutti = {}, {}
for m in MODULI:
    out = sh(["git", "log", "--pretty=%h|%s", f"--since={DA}", "--", m])
    righe = [r for r in out.splitlines() if r.strip()]
    per_modulo[m] = righe
    for r in righe:
        sha, _, sub = r.partition("|")
        tutti.setdefault(sha, (sub, set()))[1].add(m)
    print(f"  {m:38s} {len(righe):>3} commit")

print(f"\n  commit DISTINTI su tutti i moduli del verdetto: {len(tutti)}")
print(f"  contro i {len(per_modulo['verimem/anti_confab_gate.py'])} del solo gate"
      f"  ⇒ il perimetro stretto ne perde"
      f" {len(tutti) - len(per_modulo['verimem/anti_confab_gate.py'])}\n")

codice, igiene = [], []
for sha, (sub, mods) in tutti.items():
    if any(tocca_codice(sha, m) for m in mods):
        codice.append((sha, sub))
    else:
        igiene.append((sha, sub))

print(f"  toccano il CODICE : {len(codice)}")
print(f"  solo IGIENE       : {len(igiene)}")
print("\n  CODICE:")
for sha, sub in codice:
    print(f"    {sha}  {sub[:78]}")
print("\n  IGIENE:")
for sha, sub in igiene:
    print(f"    {sha}  {sub[:78]}")

sha_cod = {s for s, _ in codice}
sha_ig = {s for s, _ in igiene}
print()
ok1 = any(s.startswith("c857752e") for s in sha_cod)
ok2 = any(s.startswith("8def48d1") for s in sha_ig)
print(f"  controllo 1 (c857752e apostrofo -> CODICE): {'ACCESO' if ok1 else 'SPENTO'}")
print(f"  controllo 2 (8def48d1 commenti  -> IGIENE): {'ACCESO' if ok2 else 'SPENTO'}")
if not (ok1 and ok2):
    print("  => il criterio non separa, i numeri sopra NON vanno usati")
    sys.exit(1)
print("  => il criterio separa nei due versi: i numeri sono leggibili")
sys.exit(0)
