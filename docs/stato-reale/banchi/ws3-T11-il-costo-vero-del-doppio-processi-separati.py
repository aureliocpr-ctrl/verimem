"""T1.1 — il costo VERO del giudice doppio: tre processi separati.

    python docs/stato-reale/banchi/ws3-T11-il-costo-vero-del-doppio-processi-separati.py

⚠️ RICHIEDE UNO SLOT DI INFERENZA: carica modelli. Non eseguirlo se gli slot
sono occupati (`board-get --key slot/inferenza-1|2`).

PERCHE' ESISTE: il mio banco precedente (`ws3-T11-il-costo-del-giudice-doppio-int8.py`)
ha dato un numero di memoria **INVALIDO**, e l'ho dichiarato consegnandolo:
teneva **fp32 e int8 nello stesso processo**, quindi l'RSS misurava i due
insieme e non isolava nulla. Qui la variabile e' isolata nel solo modo che
funziona: **un processo per configurazione**, e il costo del secondo giudice e'
la DIFFERENZA fra due processi, non un numero letto dentro uno solo.

    A   solo il nostro giudice          -> RSS, tempo di caricamento
    B   solo MiniCheck fp32             -> RSS, tempo di caricamento
    C   tutti e due, come il doppio     -> RSS, tempo di caricamento

⇒ costo incrementale del secondo giudice = **C − A**, non B (perche' i due
modelli condividono torch e transformers, gia' in RSS in entrambi i casi).
⚠️ Se qualcuno leggesse B come «il costo di aggiungere MiniCheck», conterebbe
due volte il runtime condiviso. E' l'errore che questo disegno esiste per
evitare.

🔮 PREDIZIONE, da depositare sul canale PRIMA di eseguire:
  ① C − A **< B** (il runtime condiviso non si paga due volte)
  ② C − A fra **1,2 e 1,9 GB** (i pesi di MiniCheck-DeBERTa-v3-Large in fp32)
  ③ il tempo di C **≈** A + (B − runtime), non A + B
🔴 COME MUORE: se C − A ≈ B, allora i due modelli non condividono nulla di
significativo e il costo del doppio e' pieno, non incrementale.

⚠️ NON misura la latenza per scrittura in esercizio: quella dipende dal pool di
un'altra istanza (daemon caldo: prima scrittura 0,150 s). Qui si misura solo
**quanto costa TENERE due giudici**, che e' la domanda della 0.8.0.
"""
import subprocess
import sys
import textwrap

# `rss_mb` sta dentro ogni regime perche' i processi sono separati: duplicarlo
# e' il prezzo dell'isolamento, ed e' meno costoso di un import condiviso che
# gonfierebbe la baseline di tutti e tre.
COMUNE = """
import os, time
def rss_mb():
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1e6
    except Exception:
        import ctypes, ctypes.wintypes as w
        class _P(ctypes.Structure):
            _fields_ = [("cb", w.DWORD), ("pf", w.DWORD),
                        ("pws", ctypes.c_size_t), ("ws", ctypes.c_size_t),
                        ("qppp", ctypes.c_size_t), ("qpp", ctypes.c_size_t),
                        ("qpnpp", ctypes.c_size_t), ("qnpp", ctypes.c_size_t),
                        ("pfu", ctypes.c_size_t), ("ppfu", ctypes.c_size_t)]
        p = _P(); p.cb = ctypes.sizeof(_P)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(p), p.cb)
        return p.ws / 1e6
base = rss_mb()
t0 = time.time()
"""

CODA = """
print("%.0f %.0f %.1f" % (base, rss_mb(), time.time() - t0))
"""

REGIMI = {
    "A  solo il nostro giudice": COMUNE + """
from verimem.local_grounding import LocalGroundingJudge
g = LocalGroundingJudge()
g.score("Il magazzino ha ricevuto 3 bancali.", "I bancali sono 3.")
""" + CODA,
    "B  solo MiniCheck fp32": COMUNE + """
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
tok = AutoTokenizer.from_pretrained("lytang/MiniCheck-DeBERTa-v3-Large")
mod = AutoModelForSequenceClassification.from_pretrained(
    "lytang/MiniCheck-DeBERTa-v3-Large").eval()
with torch.no_grad():
    mod(**tok("Il magazzino ha ricevuto 3 bancali.", "I bancali sono 3.",
              return_tensors="pt", truncation=True, max_length=512))
""" + CODA,
    "C  tutti e due (il doppio)": COMUNE + """
from verimem.local_grounding import LocalGroundingJudge
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
g = LocalGroundingJudge()
g.score("Il magazzino ha ricevuto 3 bancali.", "I bancali sono 3.")
tok = AutoTokenizer.from_pretrained("lytang/MiniCheck-DeBERTa-v3-Large")
mod = AutoModelForSequenceClassification.from_pretrained(
    "lytang/MiniCheck-DeBERTa-v3-Large").eval()
with torch.no_grad():
    mod(**tok("Il magazzino ha ricevuto 3 bancali.", "I bancali sono 3.",
              return_tensors="pt", truncation=True, max_length=512))
""" + CODA,
}


def misura(codice):
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(codice)],
                       capture_output=True, text=True, timeout=1800)
    for riga in reversed(r.stdout.strip().splitlines()):
        pezzi = riga.split()
        if len(pezzi) == 3:
            try:
                return [float(x) for x in pezzi]
            except ValueError:
                continue
    print("   (nessun numero letto — ultime righe di stderr:)")
    for riga in r.stderr.strip().splitlines()[-3:]:
        print("   ", riga[:120])
    return None


print("IL COSTO VERO DEL GIUDICE DOPPIO — un processo per configurazione\n")
print(f"{'regime':<28} {'RSS base':>10} {'RSS finale':>10} {'secondi':>10}")
print("-" * 62)
esiti = {}
for nome, codice in REGIMI.items():
    v = misura(codice)
    esiti[nome[0]] = v
    if v:
        print(f"{nome:<28} {v[0]:>8.0f}MB {v[1]:>8.0f}MB {v[2]:>9.1f}s")
    else:
        print(f"{nome:<28} {'errore':>10}")

a, b, c = esiti.get("A"), esiti.get("B"), esiti.get("C")
if a and b and c:
    inc = c[1] - a[1]
    print()
    print(f"  costo INCREMENTALE del secondo giudice (C − A): {inc:.0f} MB")
    print(f"  MiniCheck da solo (B, runtime incluso):          {b[1]:.0f} MB")
    print(f"  ⇒ il runtime condiviso vale circa {b[1] - inc:.0f} MB")
    print()
    if inc < b[1] * 0.9:
        print("  ✅ predizione ① confermata: C−A < B, il runtime non si paga due volte")
    else:
        print("  🔴 predizione ① falsificata: C−A ≈ B, nessuna condivisione utile")
    if 1200 <= inc <= 1900:
        print("  ✅ predizione ② confermata (1,2-1,9 GB)")
    else:
        print(f"  🔴 predizione ② falsificata: {inc:.0f} MB fuori da 1,2-1,9 GB")
print("\n⚠️  un giro per regime · misura quanto costa TENERE due giudici,")
print("   NON la latenza per scrittura (quella dipende dal pool).")
