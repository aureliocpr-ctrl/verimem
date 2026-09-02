"""Quante delle modifiche al verdetto DICHIARANO la popolazione su cui sono misurate?

Nasce dalla chiusura di @ws6: il commit che ha aperto il tipo «stato»
(`5ea77b6d`) e' stato isolato per bisezione, e la sua giustificazione era «come
veto il beneficio e' ZERO — dove ferma, i lessicali fermano gia'». Su quel caso
non fermava nessun altro. MA il commit DICHIARA la propria popolazione: «ZERO su
tre popolazioni indipendenti (80 handoff: L1.13 68 volte, L1.15 40, L1.20 2)» —
handoff REALI, mentre il banco che trova il costo e' AVVERSARIALE.

⇒ la decisione non era sbagliata: il costo e' cio' che quella misura non poteva
vedere. E la mia domanda («quante cure hanno un prezzo non misurato?») diventa
misurabile in una forma piu' precisa: QUANTE DICHIARANO LA POPOLAZIONE?
Perche' e' proprio la dichiarazione che ha permesso di vedere il limite.

CRITERIO, dichiarato prima: un commit «dichiara la popolazione» se il suo
messaggio contiene un riferimento esplicito al campione o al banco su cui la
misura e' fatta — un numero di casi, un nome di banco, la parola popolazione,
campione, handoff, oppure una forma «N su M».

DUE CONTROLLI, uno per verso:
  · `5ea77b6d` -> deve DICHIARARE (sappiamo che lo fa: «su tre popolazioni…»)
  · `8def48d1` (igiene commenti) -> NON deve dichiarare
Se uno dei due sbaglia, il criterio non separa e i numeri non vanno usati.
"""
import re
import subprocess
import sys

DA = "2026-08-26 00:00"
MODULI = [
    "verimem/anti_confab_gate.py", "verimem/subject_extract.py",
    "verimem/quantity_match.py", "verimem/grounding_gate.py",
    "verimem/admission_gate.py", "verimem/supersession_policy.py",
]
POP = re.compile(
    r"\b\d+\s*(?:su|/|contro)\s*\d+|\bn\s*=\s*\d+|popolazion|campion|handoff|"
    r"\bbanco\b|banchi/|\b\d+\s+cas[oi]\b|\b\d+\s+esempi|misurat[oa] su", re.I)


def sh(a):
    return subprocess.run(a, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


sha_visti = {}
for m in MODULI:
    for r in sh(["git", "log", "--pretty=%h", f"--since={DA}", "--", m]).split():
        sha_visti[r] = None
print(f"  commit distinti sui moduli del verdetto dal 26/08: {len(sha_visti)}\n")

dichiara, muti = [], []
for sha in sha_visti:
    msg = sh(["git", "log", "-1", "--pretty=%B", sha])
    sub = msg.strip().splitlines()[0] if msg.strip() else ""
    (dichiara if POP.search(msg) else muti).append((sha, sub))

print(f"  DICHIARANO la popolazione : {len(dichiara)}")
print(f"  NON la dichiarano         : {len(muti)}")
print("\n  NON la dichiarano:")
for sha, sub in muti:
    print(f"    {sha}  {sub[:76]}")

ok1 = any(s.startswith("5ea77b6d") for s, _ in dichiara)
ok2 = any(s.startswith("8def48d1") for s, _ in muti)
print()
print(f"  controllo 1 (5ea77b6d -> DICHIARA)     : {'ACCESO' if ok1 else 'SPENTO'}")
print(f"  controllo 2 (8def48d1 igiene -> MUTO)  : {'ACCESO' if ok2 else 'SPENTO'}")
if not (ok1 and ok2):
    print("  => il criterio non separa nei due versi: i numeri NON vanno usati")
    sys.exit(1)
print("  => il criterio separa: i numeri sono leggibili")
sys.exit(0)
