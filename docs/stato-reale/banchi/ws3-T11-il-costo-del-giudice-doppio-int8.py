"""T1.1 ① — il COSTO del secondo giudice: fp32 contro int8, e la FEDELTA'.

    python docs/stato-reale/banchi/ws3-T11-il-costo-del-giudice-doppio-int8.py

QUATTRO NUMERI, e il quarto il mandato non lo chiede ma decide se il secondo
(la soglia calibrata) sia valido:
  ① disco   ② RSS del processo   ③ secondi per esempio   ④ FEDELTA' int8/fp32

⚠️ PERCHE' LA FEDELTA'. La quantizzazione **cambia i punteggi**. La soglia del
giudice doppio verrebbe calibrata sugli score che abbiamo misurato — che sono
**fp32** — ma in produzione girerebbe **int8**. Se i punteggi si spostano, la
soglia e' tarata su un modello che non e' quello che gira: e' la stessa forma
del difetto che abbiamo passato la notte a misurare (un numero di vetrina
prodotto da una versione diversa da quella installata).

⛔ ONNX NON E' MISURATO: `optimum` e `onnxruntime` non sono installati, e
installarli e' una modifica persistente all'ambiente che non faccio senza
mandato. `torch.ao.quantization.quantize_dynamic` non chiede nulla di nuovo.
⚠️ int8 DINAMICO quantizza i soli `Linear`: e' il caso piu' favorevole al
confronto di fedelta' e il meno favorevole al guadagno di velocita'. Un ONNX
int8 statico darebbe numeri diversi in entrambi i sensi — non estrapolo.

🔮 PREDIZIONE depositata sul canale PRIMA (02/09 20:53):
  ① disco int8 < 1,2 GB (da 3,3 misurati) · ② RSS meno della meta'
  ③ 1,5-2,5x piu' veloce · ④ Spearman fp32/int8 > 0,99 e falsi fermati a
  iso-recall entro ±2 punti.
"""
import json
import os
import time
from pathlib import Path

MODELLO = "lytang/MiniCheck-DeBERTa-v3-Large"
QUI = Path(__file__).resolve().parent
SCORES_FP32 = QUI / "_ws3_curva_scores.json"
GATE = {"truthfulqa-600": 0.293, "halueval-400": 0.190}
CAMPIONE = 120          # per i tempi: bastano, e il run intero e' gia' stato fatto


def rss_mb():
    """RSS del processo. `psutil` se c'e', altrimenti l'API di Windows."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1e6
    except Exception:
        try:
            import ctypes
            import ctypes.wintypes as w

            class _PMC(ctypes.Structure):
                _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = _PMC()
            pmc.cb = ctypes.sizeof(_PMC)
            ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(pmc), pmc.cb)
            return pmc.WorkingSetSize / 1e6
        except Exception:
            return None


def spearman(a, b):
    def ranghi(v):
        ordine = sorted(range(len(v)), key=lambda i: v[i])
        fuori = [0.0] * len(v)
        i = 0
        while i < len(ordine):
            j = i
            while j + 1 < len(ordine) and v[ordine[j + 1]] == v[ordine[i]]:
                j += 1
            for k in range(i, j + 1):
                fuori[ordine[k]] = (i + j) / 2.0
            i = j + 1
        return fuori
    ra, rb = ranghi(a), ranghi(b)
    n = len(ra)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((y - mb) ** 2 for y in rb) ** 0.5
    return round(num / (da * db), 5) if da and db else None


def iso(pos, neg, quota):
    ordinati = sorted(pos)
    idx = min(len(ordinati) - 1, max(0, int(round(quota * len(ordinati)))))
    s = ordinati[idx]
    return sum(1 for n in neg if n < s) / len(neg)


def main():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    base = rss_mb()
    print(f"RSS a vuoto: {base:.0f} MB\n")

    tok = AutoTokenizer.from_pretrained(MODELLO)
    t0 = time.time()
    fp32 = AutoModelForSequenceClassification.from_pretrained(MODELLO).eval()
    t_load_fp32 = time.time() - t0
    rss_fp32 = rss_mb()

    t0 = time.time()
    int8 = torch.ao.quantization.quantize_dynamic(
        fp32, {torch.nn.Linear}, dtype=torch.qint8).eval()
    t_quant = time.time() - t0
    rss_int8 = rss_mb()

    # disco: si SALVANO entrambi e si pesano, invece di stimarli
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="ws3_int8_"))
    torch.save(fp32.state_dict(), tmp / "fp32.pt")
    torch.save(int8.state_dict(), tmp / "int8.pt")
    d_fp32 = (tmp / "fp32.pt").stat().st_size / 1e6
    d_int8 = (tmp / "int8.pt").stat().st_size / 1e6

    print("① DISCO (state_dict salvato, non stimato)")
    print(f"   fp32 {d_fp32:8.0f} MB      int8 {d_int8:8.0f} MB"
          f"      {d_fp32 / max(1, d_int8):.1f}x piu' piccolo")
    print(f"   (la cache HF del modello pesa 3,3 GB: include piu' formati)\n")
    print("② MEMORIA")
    print(f"   RSS dopo fp32 {rss_fp32:.0f} MB   dopo quantizzazione "
          f"{rss_int8:.0f} MB")
    print(f"   ⚠️  qui i DUE modelli sono in RAM insieme: il secondo numero non "
          f"e' il costo di int8 da solo\n")
    print(f"   caricamento fp32 {t_load_fp32:.1f}s   quantizzazione "
          f"{t_quant:.1f}s\n")

    dati = json.loads(SCORES_FP32.read_text(encoding="utf-8"))
    print("③ VELOCITA' e ④ FEDELTA'\n")
    # Il json porta gli score fp32 ma non i TESTI: quelli si rileggono dai dump
    # originali, gli stessi due file della curva.
    RADICE = QUI.parents[2]
    DUMP = [
        ("truthfulqa-600",
         RADICE / "benchmark/data/external/truthfulqa_pairs_heldout.jsonl"),
        ("halueval-400",
         Path("C:/Users/aurel/AppData/Local/Temp/claude/"
              "C--Users-aurel-Desktop-ProgettiAI/"
              "c062024e-cc77-4fac-ba67-fb1db54449b6/scratchpad/"
              "halueval_come_truthfulqa.jsonl")),
    ]

    def punteggio(mod, s, c):
        enc = tok(s, c, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            lg = mod(**enc).logits
        return (float(torch.softmax(lg, dim=-1)[0, 1]) if lg.shape[-1] == 2
                else float(torch.sigmoid(lg)[0, 0]))

    for nome, percorso in DUMP:
        if not percorso.exists() or nome not in dati:
            continue
        righe = [json.loads(r) for r in
                 percorso.read_text(encoding="utf-8").splitlines() if r.strip()]
        pos = [d for d in righe if int(d["label"]) == 1]
        neg = [d for d in righe if int(d["label"]) == 0]

        # ③ tempi su un campione, fp32 e int8 sugli STESSI esempi
        camp = (pos + neg)[:CAMPIONE]
        t0 = time.time()
        for d in camp:
            punteggio(fp32, d["source"], d["claim"])
        t_fp32 = (time.time() - t0) / len(camp)
        t0 = time.time()
        s_int8_camp = [punteggio(int8, d["source"], d["claim"]) for d in camp]
        t_int8 = (time.time() - t0) / len(camp)

        # ④ fedelta': int8 su TUTTI, contro gli score fp32 gia' salvati
        s_int8 = {"pos": [punteggio(int8, d["source"], d["claim"]) for d in pos],
                  "neg": [punteggio(int8, d["source"], d["claim"]) for d in neg]}
        s_fp32 = dati[nome]["minicheck"]
        tutti_i8 = s_int8["pos"] + s_int8["neg"]
        tutti_f32 = s_fp32["pos"] + s_fp32["neg"]

        quota = GATE[nome]
        iso_f32 = iso(s_fp32["pos"], s_fp32["neg"], quota)
        iso_i8 = iso(s_int8["pos"], s_int8["neg"], quota)

        print(f"  {nome}")
        print(f"    ③ fp32 {t_fp32:.3f}s/es   int8 {t_int8:.3f}s/es   "
              f"{t_fp32 / max(1e-9, t_int8):.2f}x")
        print(f"    ④ Spearman fp32/int8: {spearman(tutti_f32, tutti_i8)}")
        print(f"       falsi fermati a iso-recall {100 * quota:.1f}%:  "
              f"fp32 {100 * iso_f32:.1f}%   int8 {100 * iso_i8:.1f}%   "
              f"Δ {100 * (iso_i8 - iso_f32):+.1f} punti")
        print()

    print("predizione: disco <1,2 GB · RSS meno della meta' · 1,5-2,5x piu' "
          "veloce · Spearman >0,99 · Δ iso-recall entro ±2 punti")


if __name__ == "__main__":
    main()
