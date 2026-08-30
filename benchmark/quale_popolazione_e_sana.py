r"""Quale popolazione è sana? I criteri CIECHI su tutti i dataset etichettati.

    python benchmark/quale_popolazione_e_sana.py

Due secondi, nessun gate, zero API, zero rete. Serve PRIMA di spendere 40 minuti
di banco su una popolazione che decide il verdetto al posto tuo.

PERCHE' ESISTE. Il 30/08 ho misurato C10 su HaluEval QA e ho ottenuto un numero
spettacolare — mem0 al 100% di falsita' servita. **Era un artefatto**: li' il
claim falso e' 6 volte piu' lungo del vero in 98 item su 100, e un confronto per
similarita' misura la FORMA, non la verita' (`LANT-90`). Due righe di mediana
me l'avrebbero detto prima. Poi ho certificato TruthfulQA «pulita» sulla
LUNGHEZZA e l'ho scritto due volte come verdetto generale — ma sulle NEGAZIONI
la stessa popolazione e' viziata 45% contro 16%, e stavo per proporre come cura
un layer che era solo messo davanti alla popolazione sbagliata (`LANT-93`).

⇒ 🔑 **Un criterio cieco alla verita' — che guarda solo la FORMA — deve sbagliare
come il caso (50%). Se ci prende, la forma predice la classe, e il tuo banco
misurera' quella.**

⇒ 🔑 **E uno solo non basta: «la popolazione e' pulita» vale SOLO sulla dimensione
che hai misurato.** Le altre sono IGNOTE, non sane. Questo strumento ne misura
due — lunghezza e negazione — perche' sono quelle che i layer del gate usano
davvero; **se il vostro criterio ne guarda una terza, aggiungetela qui.**

COME SI LEGGE

    50%          il caso: la forma non dice niente sulla classe        usabile
    scarto > 10  la forma predice la classe                            NON usabile
    < 40 claim   non misurabile: un righello che grida su un campione
                 minuscolo insegna a ignorarlo
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE))
ESTERNI = RADICE / "benchmark" / "data" / "external"


def _da_pairs(righe: list[dict]) -> list[tuple[str, str, str]]:
    return [("vero" if x["label"] == 1 else "falso", x["claim"], x.get("source", ""))
            for x in righe]


def _da_qa(righe: list[dict]) -> list[tuple[str, str, str]]:
    fuori = []
    for x in righe:
        fuori.append(("vero", x["right_answer"], x["knowledge"]))
        fuori.append(("falso", x["hallucinated_answer"], x["knowledge"]))
    return fuori


def _da_halumem(_: list[dict]) -> list[tuple[str, str, str]]:
    """HaluMem non e' claim+label: si costruisce (proprio vs di un altro utente).
    Riuso l'estrazione del banco esistente per non misurare una popolazione mia."""
    import random

    from benchmark.halumem_writepath_moat import _all_facts, _clean_facts
    p = Path.home() / ".cache" / "halumem" / "HaluMem-Medium.jsonl"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        utenti = [json.loads(r) for r in f if r.strip()]
    #: ⚠️ la sequenza di shuffle deve essere IDENTICA a quella del banco
    #: (`c10_seconda_popolazione_halumem.py`), o si misura un'altra popolazione.
    #: Misurato il 30/08: senza `shuffle(estranei)` questo strumento dava
    #: negazione 11,1% dove il banco dava 50,0% — **stesso dataset, campioni
    #: diversi.** Quarta volta in una notte che un righello scritto al volo
    #: diverge da quello che dovrebbe replicare.
    rng = random.Random(42)
    rng.shuffle(utenti)
    io_, altri = utenti[0], utenti[1:4]
    clean = _clean_facts(io_)
    rng.shuffle(clean)
    clean = clean[:100]
    estranei: list[str] = []
    for o in altri:
        estranei.extend(_all_facts(o))
    rng.shuffle(estranei)
    fonti = [s for _, s in clean] or [""]
    return ([("vero", t, s) for t, s in clean]
            + [("falso", t, rng.choice(fonti)) for t in estranei[:100]])


#: (etichetta leggibile, file, adattatore)
FONTI = [
    ("truthfulqa heldout", ESTERNI / "truthfulqa_pairs_heldout.jsonl", _da_pairs),
    ("truthfulqa dev", ESTERNI / "truthfulqa_pairs_dev.jsonl", _da_pairs),
    ("halueval heldout", ESTERNI / "halueval_qa_heldout.jsonl", _da_qa),
    ("halueval dev", ESTERNI / "halueval_qa_dev.jsonl", _da_qa),
    ("halueval unanswerable", ESTERNI / "halueval_qa_unanswerable.jsonl", _da_qa),
    ("halumem (scambio soggetto)", None, _da_halumem),
]


def main() -> int:
    from benchmark.c10_falsita_servite_vs_mem0 import criteri_ciechi

    print(f"  {'popolazione':30} {'claim':>6}  {'lunghezza':>10} {'negazione':>10}   verdetto")
    print(f"  {'-' * 30} {'-' * 6}  {'-' * 10} {'-' * 10}   {'-' * 30}")
    for nome, percorso, adattatore in FONTI:
        righe: list[dict] = []
        if percorso is not None:
            if not percorso.exists():
                print(f"  {nome:30} {'—':>6}  file assente")
                continue
            with open(percorso, encoding="utf-8") as f:
                righe = [json.loads(r) for r in f if r.strip()]
        casi = adattatore(righe)
        if not casi:
            print(f"  {nome:30} {'—':>6}  non costruibile (dataset assente?)")
            continue
        c = criteri_ciechi(casi)
        viziate = [k for k, v in c.items() if not k.startswith("_") and abs(v - 50) > 10]
        #: una dimensione con un fenomeno RARO non e' pulita: e' non misurata.
        if not c.get("_neg_misurabile"):
            note = f" (negazione: solo {int(c.get('_neg_occorrenze', 0))} occorrenze -> NON misurata)"
        else:
            note = ""
        if len(casi) < 40:
            verdetto = "— non misurabile (< 40 claim)"
        elif viziate:
            verdetto = "🔴 NON usabile: " + ", ".join(viziate) + note
        else:
            verdetto = "✅ usabile sulle dimensioni misurate" + note
        print(f"  {nome:30} {len(casi):6}  {c['lunghezza']:9.1f}% {c['negazione']:9.1f}%   {verdetto}")

    print()
    print("  ⚠️ «usabile» vale SOLO sulle due dimensioni qui sopra. Se il vostro criterio")
    print("     ne guarda una terza (entita' nominate, cifre, tempo verbale…), quella e'")
    print("     IGNOTA — non sana — finche' non la aggiungete a `criteri_ciechi`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
