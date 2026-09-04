"""LIVELLO: i processi — si misura la RAM, non il gate.

Quanto costa tenere B, il solo candidato dimostrabilmente migliore del nostro giudice.

🔴 IL 12,30x DI QUESTO BANCO E' SUPERATO — correzione del 2026-09-04 19:24.
`ws3-P5-il-mio-12x-regge-con-batch-e-fp16.py` ha rimisurato il rapporto sulle
STESSE 60 coppie e nello STESSO processo: e' **7,81x** senza batch e **4,19x**
con batch 8, non 12,30x.
Il difetto sta nell'impianto di QUESTO banco, ed e' mio: qui il tempo per coppia
si misura ripetendo DIECI VOLTE LA STESSA coppia. Ripetere un input non misura
la latenza di un giudice, misura il suo percorso caldo su un input solo — e
avvantaggia il nostro CE piu' di B (169,4 ms qui contro 448,6 ms su coppie tutte
diverse), gonfiando il rapporto.
✅ I numeri di MEMORIA di questo banco restano validi: sono RSS a fine processo,
non dipendono dalla ripetizione. Il costo incrementale di B e' 653 MB.

    python docs/stato-reale/banchi/ws3-P4-quanto-costa-tenere-il-giudice-che-vince.py

⚠️ Carica modelli, tre processi in sequenza. Serve uno slot di inferenza.

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`ws3-P3-...` ha stabilito che UN solo candidato batte il nostro giudice sulle
contraddizioni implicite in modo decidibile: `MoritzLaurer/DeBERTa-v3-large-
mnli-fever-anli-ling-wanli`, +0,2856 con l'intervallo appaiato che esclude lo
zero. Quel banco NON dice quanto costa tenerlo, e senza il costo «cambiamo
modello» resta una proposta.

━━ IL DISEGNO, e perche' non e' quello ovvio ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UN PROCESSO PER CONFIGURAZIONE. Due modelli nello stesso interprete NON
isolano l'RSS: il secondo eredita torch e transformers gia' caricati, e la
misura non dice quanto costa lui. E' un errore che ho gia' commesso il
2026-09-02 su un banco int8, dove produssi un numero di memoria che dovetti
dichiarare invalido.

    A  solo il nostro CE               -> RSS, secondi di carico, s/coppia
    B  solo DeBERTa-large-mnli-fever   -> idem
    C  tutti e due                     -> idem

⇒ il costo incrementale di B e' **C - A**, non B da solo: torch e transformers
stanno nell'RSS di entrambi, e contarli due volte gonfia il conto del secondo
modello. Chi legge B da solo come «quanto costa aggiungerlo» sbaglia di tutto
il runtime condiviso.

━━ PREDIZIONE ws3-P4, depositata sul canale prima di eseguire ━━━━━━━━━━━━━━━
 ① C - A e' MINORE di B da solo   🔴 muore se C-A ~ B: nessuna condivisione
 ② C - A sta fra 1,4 e 2,0 GB     🔴 muore fuori: il rapporto disco/RAM che ho
    in testa e' sbagliato (il file su disco pesa 841 MB)
 ③ B costa per coppia < 3x il nostro CE   🔴 muore sopra: il guadagno di P3 si
    paga in latenza e la decisione non e' piu' ovvia

━━ MISURATO IL 2026-09-04 alle 18:52 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    regime                       RSS base  RSS finale   carico   s/coppia
    A  solo il nostro CE             22MB     1075MB     46.6s    0.1694s
    B  solo DeBERTa-large-mnli       22MB     1615MB     50.5s    2.0844s
    C  tutti e due                   22MB     1728MB     48.3s    3.4179s

    costo INCREMENTALE di B (C − A)  :  653 MB
    B da solo, runtime incluso       : 1615 MB
    ⇒ il runtime condiviso vale      :  962 MB

 ① C−A < B da solo        ✅   653 contro 1615: il runtime non si paga due volte
 ② C−A fra 1400 e 2000 MB 🔴 FALSIFICATA: 653 MB. La mia intuizione «i pesi in
    RAM stanno sopra il file su disco» (841 MB) era sbagliata, e di parecchio.
 ③ B < 3x il nostro/coppia 🔴 FALSIFICATA, e non di poco: **12,30x**
    (2084,4 ms contro 169,4 ms)

⇒ **LA DECISIONE E' UN COMPROMESSO, NON UN AGGIORNAMENTO.** B vince di +0,2856
di AUROC sulle implicite (P3, intervallo appaiato che esclude lo zero) e costa
**due secondi a coppia** contro 0,17. In RAM e' poco: 653 MB incrementali. In
latenza e' dodici volte.

⚠️ COME VA LETTO IL 12,30x, per non farne dire piu' di quanto misura: e' CPU,
UNA coppia alla volta, fp32, senza batching. Batch e fp16 non sono stati
provati e potrebbero chiudere buona parte del divario — chi decide dovrebbe
chiedere quella misura prima di scartare B per la latenza.
⚠️ E lo 0,1694 s del nostro CE NON e' il costo di una scrittura: una scrittura
giudicata a regime costa ~0,45 s (banco `ws3-R1-...`), perche' il giudice e'
solo un pezzo del percorso.

━━ CIO' CHE NON DECIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il costo con quantizzazione (int8 sul giudice attuale l'ho misurato
inutilizzabile: -30 punti), il costo del daemon condiviso, la latenza in
esercizio sotto carico, e **il costo di B con batching e in fp16** — che e' la
misura che manca per decidere davvero. Qui si misura **quanto costa TENERLO**,
a freddo, una coppia alla volta, su questa macchina.
"""
from __future__ import annotations

import subprocess
import sys

MODELLO_B = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
FONTE = "Verbale: il collaudo si e' concluso con tre rilievi minori."
CLAIM = "Il collaudo si e' concluso senza rilievi."

#: `rss_mb` sta dentro ogni regime perche' i processi sono separati: un import
#: condiviso gonfierebbe la linea di base di tutti e tre.
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

CARICA_NOSTRO = """
from verimem.local_grounding import try_local_score
try_local_score(FONTE, CLAIM)
t_carico = time.time() - t0
t1 = time.time()
for _ in range(10):
    try_local_score(FONTE, CLAIM)
t_coppia_nostro = (time.time() - t1) / 10
"""

CARICA_B = """
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
tok = AutoTokenizer.from_pretrained(MODELLO_B)
mod = AutoModelForSequenceClassification.from_pretrained(MODELLO_B).eval()
def punteggio():
    with torch.no_grad():
        mod(**tok(FONTE, CLAIM, return_tensors="pt", truncation=True, max_length=512))
punteggio()
t_carico = time.time() - t0
t1 = time.time()
for _ in range(10):
    punteggio()
t_coppia_b = (time.time() - t1) / 10
"""

CODA = """
print("MISURA %.0f %.0f %.1f %.4f" % (base, rss_mb(), t_carico, t_coppia))
"""


def costanti() -> str:
    return (f"MODELLO_B = {MODELLO_B!r}\nFONTE = {FONTE!r}\nCLAIM = {CLAIM!r}\n")


REGIMI = {
    "A  solo il nostro CE": COMUNE + costanti() + CARICA_NOSTRO
    + "t_coppia = t_coppia_nostro\n" + CODA,
    "B  solo DeBERTa-large-mnli": COMUNE + costanti() + CARICA_B
    + "t_coppia = t_coppia_b\n" + CODA,
    "C  tutti e due": COMUNE + costanti() + CARICA_NOSTRO + CARICA_B
    + "t_coppia = t_coppia_b\n" + CODA,
}


def misura(codice: str, radice: str) -> list[float] | None:
    r = subprocess.run([sys.executable, "-c", codice], capture_output=True,
                       text=True, cwd=radice, timeout=1800)
    for riga in reversed(r.stdout.strip().splitlines()):
        if riga.startswith("MISURA "):
            return [float(x) for x in riga.split()[1:]]
    print("   (nessun numero — ultime righe di stderr:)")
    for riga in r.stderr.strip().splitlines()[-3:]:
        print("   ", riga[:130])
    return None


def main() -> None:
    from pathlib import Path
    radice = str(Path(__file__).resolve().parents[3])
    print("QUANTO COSTA TENERE IL GIUDICE CHE VINCE — un processo per configurazione\n")
    print(f"  radice usata per l'import: {radice}")
    print(f"{'regime':30s} {'RSS base':>10s} {'RSS finale':>11s} {'carico':>9s} {'s/coppia':>10s}")
    print("-" * 76)
    esiti: dict[str, list[float] | None] = {}
    for nome, codice in REGIMI.items():
        v = misura(codice, radice)
        esiti[nome[0]] = v
        if v:
            print(f"{nome:30s} {v[0]:>8.0f}MB {v[1]:>9.0f}MB {v[2]:>8.1f}s {v[3]:>9.4f}s",
                  flush=True)
        else:
            print(f"{nome:30s} {'errore':>10s}")

    a, b, c = esiti.get("A"), esiti.get("B"), esiti.get("C")
    if not (a and b and c):
        print("\n🔴 un regime non ha prodotto numeri: il confronto non si fa.")
        return
    inc = c[1] - a[1]
    print()
    print(f"  costo INCREMENTALE di B (C − A) : {inc:>8.0f} MB")
    print(f"  B da solo, runtime incluso      : {b[1]:>8.0f} MB")
    print(f"  ⇒ il runtime condiviso vale     : {b[1] - inc:>8.0f} MB")
    print()
    print(f"  ① C−A < B da solo        : {'✅' if inc < b[1] * 0.9 else '🔴 FALSIFICATA'}"
          f"   ({inc:.0f} contro {b[1]:.0f})")
    print(f"  ② C−A fra 1400 e 2000 MB : "
          f"{'✅' if 1400 <= inc <= 2000 else f'🔴 FALSIFICATA ({inc:.0f} MB)'}")
    rapporto = b[3] / max(1e-9, a[3])
    print(f"  ③ B < 3x il nostro/coppia: "
          f"{'✅' if rapporto < 3 else '🔴 FALSIFICATA'}   ({rapporto:.2f}x — "
          f"{b[3] * 1000:.1f} ms contro {a[3] * 1000:.1f} ms)")


if __name__ == "__main__":
    main()
