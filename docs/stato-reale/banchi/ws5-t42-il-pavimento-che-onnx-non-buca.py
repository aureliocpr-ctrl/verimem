r"""T4.2 — prima di esportare in ONNX: quanto del giudice e' il MODELLO e quanto e' torch?

Il piano di ricerca promette per T4.2 (export ONNX + int8): «*RSS/processo <=250 MB*».
Ma int8 rimpicciolisce **il modello**, non la libreria che lo ospita. ⇒ Se `torch` resta
importato nel processo, il suo peso e' un **pavimento** che nessuna quantizzazione tocca.

📌 **QUESTA MISURA COSTA UN IMPORT, NON 200 MB DI DOWNLOAD.** `onnxruntime` e `optimum`
non sono installati e nel repo non c'e' una riga di ONNX: prima di tirarli giu' conviene
sapere se il bersaglio e' raggiungibile.

I QUATTRO PUNTI, in ordine di costo crescente::

    ①  interprete nudo
    ②  dopo `import torch`                  <- il pavimento vero
    ③  dopo `import transformers`
    ④  dopo il caricamento del modello      <- l'unica parte che int8 rimpicciolisce

⇒ Il margine su cui T4.2 puo' agire e' **④ − ③**, non ④.

🔴 ESITO — **il bersaglio del piano NON e' raggiungibile con int8 sul modello**::

    punto                        RSS (MB)   privata (MB)   durata
    ① interprete nudo                16.7            9.2      —
    ② + import torch                193.6          784.9     5.7s
    ③ + import transformers         221.4          811.6     8.6s
    ④ + modello caricato            861.8         2446.3    13.1s
    ---------------------------------------------------------------
    pavimento (torch+transformers)  221.4          811.6
    il MODELLO da solo (④−③)        640.4         1634.7

    controllo positivo: grounding 99.67  ⇒ il giudice ha davvero girato

🔑 **PERCHE' <=250 MB NON SI RAGGIUNGE**: il pavimento RSS (221,4 MB) sta appena sotto i
250, quindi per centrare il bersaglio int8 dovrebbe portare il modello da **640,4 MB a
28,6 MB** — una riduzione del **95,5%**. **int8 da fp32 riduce di ~4x**, cioe' a ~160 MB:
totale atteso **~381 MB**, non 250. ⇒ La predizione e' fuori di **piu' di 130 MB**, e non
per poco.

🔑🔑 **E SULLA PRIVATA — la grandezza che conta per «8 agenti» — VA PEGGIO**: `torch` da
solo pesa **784,9 MB di privata**, e quel numero **non scende nemmeno con il modello a
zero**. Su 1552,8 MB per processo (baseline `c8830190`), **oltre meta' e' la libreria**.
⇒ Anche una quantizzazione perfetta lascerebbe ~0,8 GB per processo: **8 agenti = 6,5 GB**
invece di 12,4. Un miglioramento reale, ma **lontano dal bersaglio dichiarato**.

📌 **COSA NE DISCENDE, ed e' una strada diversa da quella scritta nel piano**: il collo di
bottiglia non e' la precisione dei pesi, e' **torch nel processo**. ⇒ Per scendere davvero
il giudizio deve girare **senza torch importato** — `onnxruntime` **puro**, non `optimum`
sopra torch.
🔗 **E questo RIVALUTA T4.1**, che avevo appena ridimensionato: nel mio prototipo il
daemon risparmiava solo il **9%** perche' i client erano gia' leggeri e il daemon portava
tutto. Ma un daemon che gira su `onnxruntime` **senza torch** farebbe pagare ai client
**ne' la libreria ne' il modello**. ⇒ **T4.1 e T4.2 non sono alternative: la strada e' la
loro combinazione**, e da sole valgono molto meno di quanto ciascuna promette.

⚖️ PUNTI DEBOLI: il «~4x di int8» e' letteratura, non una mia misura — se il modello
fosse gia' in fp16 il guadagno sarebbe **2x** e il quadro peggiore, non migliore; una sola
macchina; e non ho verificato se `onnxruntime` da solo importi comunque qualcosa di
pesante (e' la misura che viene dopo, e costa il download).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-t42-il-pavimento-che-onnx-non-buca.py <venv>
"""
import os
import subprocess
import sys

if os.environ.get("_WS5_PULITO") != "1":
    # il filtro DENTRO lo script: uno nel comando puo' saltare — mi e' successo tre
    # volte oggi, e i numeri sono usciti META' di quelli veri.
    if len(sys.argv) < 2:
        print("uso: python %s <venv>" % sys.argv[0])
        raise SystemExit(2)
    venv = sys.argv[1]
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        print("  🔴 venv assente: %s" % venv)
        raise SystemExit(1)
    import tempfile
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    env.update({"_WS5_PULITO": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "HIPPO_DATA_DIR": tempfile.mkdtemp(prefix="ws5_pav_")})
    raise SystemExit(subprocess.run([py, "-u", os.path.abspath(__file__)] + sys.argv[1:],
                                    env=env).returncode)

import ctypes
import ctypes.wintypes as wt
import time


class _PMCEX(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


def mem():
    c = _PMCEX(); c.cb = ctypes.sizeof(_PMCEX)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    h = ctypes.windll.kernel32.GetCurrentProcess()
    fn = ctypes.windll.kernel32.K32GetProcessMemoryInfo
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMCEX), wt.DWORD]
    fn.restype = wt.BOOL
    if not fn(h, ctypes.byref(c), c.cb):
        raise OSError("GetProcessMemoryInfo err=%d" % ctypes.windll.kernel32.GetLastError())
    return c.WorkingSetSize / 1048576.0, c.PrivateUsage / 1048576.0


punti = []
r, p = mem()
punti.append(("① interprete nudo", r, p, None))
t = time.time()
import torch  # noqa: F401
r, p = mem()
punti.append(("② + import torch", r, p, time.time() - t))
t = time.time()
import transformers  # noqa: F401
r, p = mem()
punti.append(("③ + import transformers", r, p, time.time() - t))

FONTE = ("La coda della CI contiene 2557 run completati, 149 run in attesa "
         "e 3 run in corso.")
t = time.time()
from verimem.anti_confab_gate import run_validation_gate
g = run_validation_gate(proposition="Nella coda ci sono 149 run in attesa.",
                        verified_by=None, topic=None, agent=None,
                        source=FONTE, ground_write=True)
r, p = mem()
punti.append(("④ + modello caricato", r, p, time.time() - t))

print("  %-26s %10s %14s %10s" % ("punto", "RSS (MB)", "privata (MB)", "durata"))
print("  " + "-" * 66)
for nome, rr, pp, dd in punti:
    print("  %-26s %9.1f %13.1f %9s" % (nome, rr, pp, ("%.1fs" % dd) if dd else "—"))

# IL CONTROLLO PRIMA DEI NUMERI: se il giudice non ha girato, ④ non e' il suo punto
gs = getattr(g, "grounding_score", None)
if gs is None:
    print("\n  ⚠️ grounding None: il giudice NON ha girato ⇒ il punto ④ non e' il modello.")
    raise SystemExit(1)
print("\n  ✅ controllo positivo: grounding %.2f ⇒ il giudice ha girato davvero" % gs)

pav_r, pav_p = punti[2][1], punti[2][2]
mod_r, mod_p = punti[3][1] - pav_r, punti[3][2] - pav_p
print("\n  === IL PAVIMENTO E IL MARGINE ===")
print("  pavimento (torch+transformers):  %7.1f MB RSS   %7.1f MB privata" % (pav_r, pav_p))
print("  il MODELLO da solo (④−③):        %7.1f MB RSS   %7.1f MB privata" % (mod_r, mod_p))
print("  totale:                          %7.1f MB RSS   %7.1f MB privata"
      % (punti[3][1], punti[3][2]))
serve = mod_r - (250 - pav_r)
print("\n  ⇒ per centrare i 250 MB del piano, int8 dovrebbe togliere %.1f MB su %.1f"
      % (serve, mod_r))
print("    cioe' il %.1f%% del modello. int8 da fp32 riduce di ~4x (75%%)."
      % (100.0 * serve / mod_r if mod_r else 0))
atteso = pav_r + mod_r / 4.0
print("    ⇒ atteso realistico: %.0f MB RSS, non 250." % atteso)
if atteso > 250:
    print("  🔴 IL BERSAGLIO DEL PIANO NON E' RAGGIUNGIBILE con int8 sul solo modello.")
    print("     Il collo di bottiglia e' torch NEL PROCESSO (%.1f MB di privata al solo"
          % punti[1][2])
    print("     import): per scendere davvero il giudizio deve girare SENZA torch —")
    print("     onnxruntime puro, non optimum sopra torch. E allora T4.1 e T4.2 non")
    print("     sono alternative: la strada e' la loro combinazione.")
else:
    print("  🟢 il bersaglio e' raggiungibile: int8 basta.")
