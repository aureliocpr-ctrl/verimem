r"""C10 su una SECONDA popolazione — HaluMem, dove il falso e' uno SCAMBIO DI SOGGETTO.

    python benchmark/c10_seconda_popolazione_halumem.py --n 100

PERCHE' QUESTA E NON HaluEval. @lead-audit ha proposto HaluEval come seconda
popolazione. **Non va bene, ed e' misurato** (`LANT-90`): li' il claim falso e'
**6 volte piu' lungo** del vero in **98 item su 100**, e il criterio cieco alla
verita' segna **96-98%** — un confronto lo' misura la FORMA, non la verita'.

E **non si aggiusta sottocampionando**: per portare il criterio cieco vicino a
50 servono coppie con scarto di lunghezza <= 35%, e sono **5 su 100** (a <= 50%
sono 15, e il criterio e' ancora 76,7%). ⇒ Non e' rumore da filtrare: e' il
DISEGNO del dataset — `right_answer` e' un'entita' («Talbot-Taylor Wildlife
Sanctuary»), `hallucinated_answer` e' una frase intera. **Non si bilancia senza
svuotarlo.**

HaluMem invece costruisce il falso in un modo che rende l'artefatto di forma
IMPOSSIBILE PER COSTRUZIONE — e il protocollo esiste gia' nel repo
(`benchmark/halumem_admission_sweep.py`, da cui riuso l'estrazione):

    clean  = (memory_point dell'utente,  il dialogo che lo genera)     -> VERO
    noise  = (memory_point di UN ALTRO,  il dialogo di questo utente)  -> FALSO

⇒ **Il «falso» e' un fatto VERO, di un'altra persona, accoppiato alla fonte
sbagliata: e' uno SCAMBIO DI SOGGETTO.** I due gruppi escono dalla STESSA
distribuzione di testi (memory_points), quindi lunghezza, registro e marcatori
lessicali non possono separarli. **Ma lo misuro lo stesso**, perche' «la
popolazione e' pulita» vale solo sulla dimensione che hai misurato (`LANT-93`).

E IL BONUS CHE RENDE QUESTA POPOLAZIONE LA PIU' UTILE DELLE DUE:
`anti_confab_gate.py:177` dichiara che al cut 40 il gate perde il **33% dei
fatti PULITI**, e lo dichiara **proprio su HaluMem**. ⇒ Questo banco rende quel
numero VERIFICABILE da fuori, come `LANT-94` ha fatto con `README:102`.

ZERO API. Nessun LLM: il gate gira col cross-encoder LOCALE (lo sweep esistente
usa `LeanClaudeCLILLM`, io no — misuro la porta che l'utente ha di default).
Store TEMPORANEO (`HIPPO_DATA_DIR`), fuori pytest, store di Aurelio mai toccato.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE))

DATI = Path.home() / ".cache" / "halumem" / "HaluMem-Medium.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=100, help="quanti claim per classe")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--solo-forma", action="store_true",
                    help="misura i criteri ciechi e si ferma, senza far girare il gate")
    ap.add_argument("--out", default="benchmark/results/c10_halumem.json")
    a = ap.parse_args()

    #: estrazione RIUSATA dal banco esistente: se la riscrivessi misurerei una
    #: popolazione mia, e il confronto col 33% dichiarato non varrebbe piu'.
    from benchmark.halumem_writepath_moat import _all_facts, _clean_facts

    with open(DATI, encoding="utf-8") as f:
        utenti = [json.loads(r) for r in f if r.strip()]
    rng = random.Random(a.seed)
    rng.shuffle(utenti)
    io_, altri = utenti[0], utenti[1:4]

    clean = _clean_facts(io_)
    rng.shuffle(clean)
    clean = clean[: a.n]
    estranei: list[str] = []
    for o in altri:
        estranei.extend(_all_facts(o))
    rng.shuffle(estranei)
    fonti_proprie = [src for _, src in clean] or [""]
    noise = [(estranei[i], rng.choice(fonti_proprie))
             for i in range(min(a.n, len(estranei)))]

    casi = [("vero", txt, src) for txt, src in clean] + \
           [("falso", txt, src) for txt, src in noise]
    if not casi:
        print("  nessun caso estratto — controlla il dataset")
        return 1

    # ═══ i criteri ciechi PRIMA di spendere 40 minuti di gate ═══
    from benchmark.c10_falsita_servite_vs_mem0 import criteri_ciechi
    ciechi = criteri_ciechi(casi)
    veri = [c for et, c, _ in casi if et == "vero"]
    falsi = [c for et, c, _ in casi if et == "falso"]
    print(f"  HaluMem — {len(veri)} veri (memory point propri) + {len(falsi)} falsi "
          f"(memory point di ALTRI utenti sulla fonte propria)")
    print("  criteri CIECHI alla verita' (50% = il caso):")
    for nome, val in ciechi.items():
        if nome.startswith("_"):
            continue
        stato = ("— non misurabile sotto 40 claim" if len(casi) < 40
                 else "⚠️ ARTEFATTO DI FORMA" if abs(val - 50) > 10
                 else "✅ non predice la classe")
        print(f"     {nome:12} {val:5.1f}%   {stato}")
    print(f"     (negazione nel {ciechi['_neg_quota_veri']}% dei veri e nel "
          f"{ciechi['_neg_quota_falsi']}% dei falsi)")
    print("  ⚠️ le dimensioni non elencate sono IGNOTE, non sane.")
    if a.solo_forma:
        return 0

    # ═══ il gate, stesso protocollo di c10_falsita_servite_vs_mem0 ═══
    os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_c10_hm_")
    from verimem.client import Memory

    mem = Memory()
    esiti: list[dict] = []
    for i, (etichetta, claim, fonte) in enumerate(casi):
        try:
            r = mem.add(claim, source=fonte, topic="c10/halumem")
            stato = r.get("status") if isinstance(r, dict) else None
            chi = r.get("quarantined_by") if isinstance(r, dict) else None
            warn = (r.get("warnings") or []) if isinstance(r, dict) else []
            strati = sorted({(w or {}).get("layer") for w in warn if (w or {}).get("layer")})
        except Exception as e:
            stato, chi, strati = f"ERRORE:{type(e).__name__}", None, []
        esiti.append({"etichetta": etichetta, "stato": stato,
                      "quarantined_by": chi, "layer": strati, "claim": claim[:120]})
        if (i + 1) % 20 == 0:
            print(f"    …{i + 1}/{len(casi)} claim", flush=True)

    def servito(e: dict) -> bool:
        return not str(e["stato"]).startswith("quarantin")

    v = [e for e in esiti if e["etichetta"] == "vero"]
    f_ = [e for e in esiti if e["etichetta"] == "falso"]
    falsi_ammessi = [e for e in f_ if servito(e)]
    veri_persi = [e for e in v if not servito(e)]
    serviti = [e for e in esiti if servito(e)]
    falsi_serviti = [e for e in serviti if e["etichetta"] == "falso"]

    print(f"\n  === VERIMEM su HaluMem — {len(esiti)} claim ===")
    print(f"  faccia A  falsi AMMESSI:  {len(falsi_ammessi):4}/{len(f_):<4} = "
          f"{100 * len(falsi_ammessi) / max(1, len(f_)):5.1f}%")
    print(f"  faccia B  veri PERSI:     {len(veri_persi):4}/{len(v):<4} = "
          f"{100 * len(veri_persi) / max(1, len(v)):5.1f}%")
    print(f"\n  ⇒ di cio' che viene SERVITO, e' falso: {len(falsi_serviti)}/{len(serviti)} = "
          f"{100 * len(falsi_serviti) / max(1, len(serviti)):5.1f}%")
    print(f"  📌 `anti_confab_gate.py:177` dichiara 33% di fatti PULITI persi su HaluMem: "
          f"qui la faccia B misura {100 * len(veri_persi) / max(1, len(v)):.1f}%")

    from collections import Counter
    per_chi = Counter((e.get("quarantined_by") or "(non registrato)") for e in veri_persi)
    print(f"\n  CHI ferma i {len(veri_persi)} veri persi:")
    for k, n in per_chi.most_common():
        print(f"     {n:4}  {k}")

    sha = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=RADICE,
                         capture_output=True, text=True).stdout.strip()
    corpo = {"popolazione": "HaluMem-Medium.jsonl (scambio di soggetto)",
             "criteri_ciechi": {k: round(v_, 1) for k, v_ in ciechi.items()},
             "veri": len(v), "falsi": len(f_),
             "falsi_ammessi": len(falsi_ammessi), "veri_persi": len(veri_persi),
             "falsi_fra_i_serviti": len(falsi_serviti), "serviti": len(serviti),
             "veri_persi_per_decisore": dict(per_chi),
             "commit": sha, "store": "temporaneo (HIPPO_DATA_DIR)", "seed": a.seed}
    out = RADICE / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpo, indent=2), encoding="utf-8")
    print(f"\n  REGIME  commit {sha} · store temporaneo · seed {a.seed} · zero API")
    print(f"  scritto {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
