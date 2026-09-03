"""T2.1, passo zero — IL BANCO A 100 FATTI ROMPE IL SOFFITTO? Prima di scaricare tre embedder.

    python scripts/banco_recall_100.py

Nell'anello ① (12 fatti x 2 lingue) tutte e quattro le celle davano il soffitto:
    ITALIANO 12/12 parola · 11/12 sinonimo    INGLESE 12/12 · 12/12
e restavano IDENTICHE aggiungendo 200 distrattori. Ho scritto allora la predizione:
«cambiando embedder il mio banco resta al soffitto e non mostra nulla».
⇒ prima di scaricare multilingual-e5-small (112,8 MB) e -base (~1 GB) sulla macchina di
Aurelio, verifico se a 100 fatti il banco diventa SENSIBILE. Se resta saturo, l'ablation
dell'embedder non e' misurabile qui e il download sarebbe tempo e banda per misurare zero.

DISEGNO: 50 fatti-BERSAGLIO (ognuno con un soggetto distinto e il suo sinonimo) + 50 fatti
RIEMPITIVI della stessa forma = 100 fatti per store; due store monolingui (IT, EN).
Per ogni bersaglio due query nella lingua del suo store: una col SOGGETTO come sta nel fatto,
una col SINONIMO e tutto il resto uguale. Metrica: il bersaglio e' al PRIMO POSTO? (k=10)
⚠️ I bersagli misurati sono 50 su 100 fatti: lo dichiaro invece di scrivere «100 query».

PREDIZIONE SCRITTA PRIMA (02/09 12:55), embedder ATTUALE:
    IT parola >= 45/50 · IT sinonimo 30-45/50
    EN parola >= 45/50 · EN sinonimo 30-45/50
cioe': mi aspetto che a 50 bersagli il soffitto si CREPI sul sinonimo ma non sulla parola.
CONDIZIONE D'USCITA:
    tutte e quattro >= 47/50  -> ancora SOFFITTO: l'ablation dell'embedder non e' misurabile
                                 su questo banco, e NON scarico i modelli
    almeno una <= 40/50       -> il banco e' sensibile: la baseline per T2.1 esiste e il
                                 confronto fra embedder ha un margine su cui muoversi
"""
import os
import sys
import tempfile
from pathlib import Path

for _v in ("ENGRAM_GROUNDING_BACKEND", "HIPPO_ENCODE_DELEGATE_ONLY", "ENGRAM_MIN_RELEVANCE",
           "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR", "ENGRAM_GATEWAY_MIN_RELEVANCE"):
    os.environ.pop(_v, None)
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402

K = 10

#: (soggetto IT, sinonimo IT, soggetto EN, sinonimo EN) — 50 bersagli, soggetti distinti.
SOGG = [
    ("caldaia", "bruciatore", "boiler", "burner"),
    ("magazzino", "deposito", "warehouse", "depot"),
    ("ponte", "viadotto", "bridge", "viaduct"),
    ("batteria", "accumulatore", "battery", "accumulator"),
    ("motore", "propulsore", "engine", "powerplant"),
    ("sala", "aula", "hall", "auditorium"),
    ("contratto", "accordo", "contract", "agreement"),
    ("regolamento", "normativa", "rulebook", "policy"),
    ("corso", "seminario", "course", "seminar"),
    ("pannello", "cruscotto", "panel", "dashboard"),
    ("filtro", "setaccio", "filter", "strainer"),
    ("pompa", "idrovora", "pump", "impeller"),
    ("nastro", "cinghia", "belt", "strap"),
    ("valvola", "saracinesca", "valve", "gate"),
    ("sensore", "rilevatore", "sensor", "detector"),
    ("cavo", "conduttore", "cable", "wire"),
    ("rullo", "cilindro", "roller", "cylinder"),
    ("ventola", "aspiratore", "fan", "blower"),
    ("giunto", "raccordo", "joint", "coupling"),
    ("piastra", "lastra", "plate", "slab"),
    ("serbatoio", "cisterna", "tank", "reservoir"),
    ("tubo", "condotto", "pipe", "duct"),
    ("scala", "gradinata", "staircase", "steps"),
    ("cancello", "portone", "gate", "portal"),
    ("finestra", "vetrata", "window", "pane"),
    ("tetto", "copertura", "roof", "covering"),
    ("muro", "parete", "wall", "partition"),
    ("pavimento", "suolo", "floor", "ground"),
    ("armadio", "guardaroba", "cupboard", "wardrobe"),
    ("scaffale", "ripiano", "shelf", "rack"),
    ("banco", "tavolo", "bench", "table"),
    ("sedia", "seggiola", "chair", "seat"),
    ("lampada", "lampadario", "lamp", "luminaire"),
    ("stufa", "radiatore", "stove", "radiator"),
    ("frigorifero", "congelatore", "fridge", "freezer"),
    ("forno", "fornello", "oven", "cooker"),
    ("cassa", "baule", "crate", "chest"),
    ("carrello", "vagoncino", "trolley", "cart"),
    ("gru", "argano", "crane", "winch"),
    ("trattore", "motocoltivatore", "tractor", "tiller"),
    ("furgone", "camioncino", "van", "pickup"),
    ("barca", "imbarcazione", "boat", "vessel"),
    ("bicicletta", "velocipede", "bicycle", "cycle"),
    ("orologio", "cronometro", "clock", "timepiece"),
    ("bilancia", "stadera", "scale", "balance"),
    ("termometro", "pirometro", "thermometer", "pyrometer"),
    ("microscopio", "lente", "microscope", "magnifier"),
    ("stampante", "plotter", "printer", "plotter"),
    ("schermo", "monitor", "screen", "monitor"),
    ("tastiera", "pulsantiera", "keyboard", "keypad"),
]
_PRED_IT = ["pesa", "misura", "costa", "resiste a", "consuma", "produce"]
_PRED_EN = ["weighs", "measures", "costs", "withstands", "consumes", "produces"]
_UNIT_IT = ["chilogrammi", "centimetri", "euro", "gradi", "litri", "pezzi"]
_UNIT_EN = ["kilograms", "centimetres", "euros", "degrees", "litres", "pieces"]


def materiale():
    """Fatti bersaglio + riempitivi + le due forme di query, nelle due lingue."""
    it_f, en_f, it_qp, it_qs, en_qp, en_qs = [], [], [], [], [], []
    for i, (sit, xit, sen, xen) in enumerate(SOGG):
        p, u = i % len(_PRED_IT), i % len(_UNIT_IT)
        val = 17 + i * 3
        it_f.append(f"Il {sit} {_PRED_IT[p]} {val} {_UNIT_IT[u]}.")
        en_f.append(f"The {sen} {_PRED_EN[p]} {val} {_UNIT_EN[u]}.")
        it_qp.append(f"Quanto {_PRED_IT[p]} il {sit}?")
        it_qs.append(f"Quanto {_PRED_IT[p]} il {xit}?")
        en_qp.append(f"How much does the {sen} {_PRED_EN[p].rstrip('s')}?")
        en_qs.append(f"How much does the {xen} {_PRED_EN[p].rstrip('s')}?")
    # 50 riempitivi della stessa forma, soggetti NON interrogati
    riemp_it, riemp_en = [], []
    for j in range(50):
        p, u = j % len(_PRED_IT), (j + 2) % len(_UNIT_IT)
        riemp_it.append(f"Il componente numero {j} {_PRED_IT[p]} {200 + j} {_UNIT_IT[u]}.")
        riemp_en.append(f"Component number {j} {_PRED_EN[p]} {200 + j} {_UNIT_EN[u]}.")
    return it_f, en_f, it_qp, it_qs, en_qp, en_qs, riemp_it, riemp_en


def costruisci(bersagli, riempitivi):
    mem = Memory(Path(tempfile.mkdtemp()) / "s.db")
    for f in bersagli + riempitivi:
        mem.add(f, topic="t21/banco100")
    return mem


def misura(mem, bersagli, queries, nome):
    primo = entro = 0
    for i, q in enumerate(queries):
        r = mem.search(q, k=K)
        for j, x in enumerate(r):
            if (x.get("text") or "")[:40].strip() == bersagli[i][:40].strip():
                if j == 0:
                    primo += 1
                entro += 1
                break
    print(f"  {nome:<30} primo posto {primo:>3}/{len(queries)} | entro k={K} "
          f"{entro:>3}/{len(queries)}", flush=True)
    return primo


def main():
    it_f, en_f, it_qp, it_qs, en_qp, en_qs, r_it, r_en = materiale()
    n = len(it_f)
    # 🔑 DA CHE ALBERO STIAMO LEGGENDO: nel worktree si importa il worktree, da
    # uno script lanciato altrove si importa l albero condiviso. Un banco che non
    # lo dichiara puo misurare un codice diverso da quello che credi (@ws2, 03/09).
    print(f"IMPORT DA {verimem.__file__}", flush=True)
    print(f"verimem {verimem.__version__} | {n} bersagli + {len(r_it)} riempitivi = "
          f"{n + len(r_it)} fatti per store, k={K}", flush=True)
    mem_it = costruisci(it_f, r_it)
    mem_en = costruisci(en_f, r_en)
    print("=== store ITALIANO ===", flush=True)
    a = misura(mem_it, it_f, it_qp, "A  parola del fatto")
    b = misura(mem_it, it_f, it_qs, "B  sinonimo")
    print("=== store INGLESE ===", flush=True)
    c = misura(mem_en, en_f, en_qp, "C  parola del fatto")
    d = misura(mem_en, en_f, en_qs, "D  sinonimo")

    print("\n" + "=" * 74, flush=True)
    print(f"{'':<14}{'parola del fatto':>20}{'sinonimo':>14}", flush=True)
    print(f"{'ITALIANO':<14}{a:>17}/{n}{b:>11}/{n}", flush=True)
    print(f"{'INGLESE':<14}{c:>17}/{n}{d:>11}/{n}", flush=True)
    soffitto = min(a, b, c, d) >= 47
    sensibile = min(a, b, c, d) <= 40
    print(f"  effetto LINGUA |A-C| = {abs(a-c)}   effetto SINONIMO A-B = {a-b}, C-D = {c-d}",
          flush=True)
    if soffitto:
        print("  => ANCORA SOFFITTO: l'ablation dell'embedder non e' misurabile su questo\n"
              "     banco. NON scarico mE5-small ne' mE5-base.", flush=True)
    elif sensibile:
        print("  => BANCO SENSIBILE: la baseline per T2.1 esiste, il confronto fra embedder\n"
              "     ha un margine su cui muoversi.", flush=True)
    else:
        print("  => intermedio (nessuna cella <=40 ne' tutte >=47): lo dichiaro cosi'.",
              flush=True)
    print("=" * 74, flush=True)
    print("PREDIZIONE (scritta prima): IT parola >=45 · IT sinonimo 30-45 · "
          "EN parola >=45 · EN sinonimo 30-45.", flush=True)


if __name__ == "__main__":
    main()
