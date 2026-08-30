r"""C10 — CHE TASSO DI FALSITA' SERVIAMO NOI, E QUALE NE SERVE UN CONCORRENTE.

La domanda e' di Aurelio, verbatim: **«che tasso di figure di merda fanno loro
e quale noi»**. Questo banco produce quel numero su una popolazione PUBBLICA e
su ENTRAMBE le facce.

POPOLAZIONE — default `truthfulqa_pairs_heldout.jsonl` (600 righe: un claim per
riga, con `source`, `claim`, `label`). TruthfulQA, licenza e sha256 della fonte
in `benchmark/data/external/README.md`. Non l'abbiamo scritto noi: e' il punto
di `TRUST_CORE.md` — «i numeri di fiducia smettono di correggere i nostri
compiti».

  ⚠️ Questo blocco ha dichiarato `halueval_qa_heldout` per DUE esecuzioni fatte
  su truthfulqa — costante rimasta dal primo giro, esattamente come il titolo
  del log che stampava la popolazione sbagliata. **I numeri erano giusti e
  l'etichetta no**, che e' il difetto che passiamo le giornate a smontare.
  `halueval` resta selezionabile con `--popolazione halueval`, ma **solo per
  poter RIFARE il suo artefatto di forma** (LANT-90), non per misurarci sopra.

  ⚠️ DISCIPLINA DEL README, rispettata: `heldout` si ESEGUE e non si legge. Lo
  sviluppo di questo banco e' avvenuto guardando UN item del `dev`.

  🔁 REPLICA su campione DISGIUNTO: `--salta 200` misura sulle righe che la
  prima corsa non ha visto (600 in tutto, 200 usate). Stessa disciplina, stesso
  apparecchio, materiale nuovo.

PERCHE' DUE FACCE, E PERCHE' UNA SOLA SAREBBE MARKETING.
  mem0 non ha un gate di ammissione: con `infer=False` scrive cio' che riceve.
  ⇒ Dire «mem0 ammette il 100% dei falsi» e' vero e **banale**, e pubblicarlo da
  solo sarebbe esattamente la figura che stiamo cercando di non fare. Il numero
  che conta e' il PREZZO: quanti VERI perdiamo per il vantaggio sui falsi.

      faccia A   falsi AMMESSI   (la nostra promessa: dovrebbero essere pochi)
      faccia B   veri PERSI      (il prezzo: quarantinati a torto)

  Un sistema che ammette 0 falsi rifiutando tutto ha faccia A perfetta e faccia
  B catastrofica. **Le due si leggono insieme o non si leggono.**

ZERO API ESTERNE. Il gate usa il cross-encoder LOCALE; mem0 gira in
`.venv-mem0bench` con embedder e5 locale — lo stesso modello che usiamo noi — e
`infer=False`, quindi il suo LLM non viene mai chiamato. Nessuna chiave, nessuna
rete verso terzi. *(Il lato mem0 sta in `c10_lato_mem0.py`: gira in un altro
interprete e non puo' importare `verimem`.)*

    python benchmark/c10_falsita_servite_vs_mem0.py --n 60

Store TEMPORANEO (`HIPPO_DATA_DIR`), fuori pytest. Non tocca lo store di Aurelio.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
ESTERNI = RADICE / "benchmark" / "data" / "external"

#: DUE popolazioni, e la differenza fra loro E' il reperto (LANT-68).
#: `halueval` resta selezionabile per POTER RIFARE l'artefatto, non per usarlo.
POPOLAZIONI = {
    "truthfulqa": ("truthfulqa_pairs_heldout.jsonl", "pairs"),
    "halueval": ("halueval_qa_heldout.jsonl", "qa"),
}


def carica(nome: str, n: int | None, salta: int = 0) -> tuple[list[tuple[str, str, str]], str]:
    """Restituisce [(etichetta, claim, fonte)] — forma unica per le due popolazioni.

    `salta` serve alla REPLICA su campione DISGIUNTO: `truthfulqa_pairs_heldout`
    ha 600 righe e la prima misura ne ha usate 200, quindi `--salta 200` misura
    su materiale **mai visto dalla misura precedente**, con la stessa disciplina
    (sempre `heldout`, che si esegue e non si legge) e lo stesso apparecchio.
    ⇒ **Un numero che si riproduce su un campione disgiunto non e' un caso; uno
    che non si riproduce e' instabile e va detto.**
    """
    f_nome, forma = POPOLAZIONI[nome]
    with open(ESTERNI / f_nome, encoding="utf-8") as f:
        righe = [json.loads(r) for r in f if r.strip()]
    passo = 1 if forma == "qa" else 2   # `pairs` ha una riga per claim, `qa` due per item
    righe = righe[salta * passo:]
    fuori: list[tuple[str, str, str]] = []
    if forma == "qa":
        for it in (righe[:n] if n else righe):
            fuori.append(("vero", it["right_answer"], it["knowledge"]))
            fuori.append(("falso", it["hallucinated_answer"], it["knowledge"]))
    else:
        for it in (righe[: 2 * n] if n else righe):
            fuori.append(("vero" if it["label"] == 1 else "falso", it["claim"], it["source"]))
    return fuori, f_nome


#: parole che segnalano una NEGAZIONE. E' una dimensione di forma quanto la
#: lunghezza, e i layer del gate la usano davvero (`L4-negazione`).
_NEGAZIONE = re.compile(
    r"\b(no|not|never|none|nothing|cannot|can't|doesn't|don't|isn't|aren't|won't)\b", re.I)


def criteri_ciechi(casi: list[tuple[str, str, str]]) -> dict[str, float]:
    """I righelli che dicono se la POPOLAZIONE e' viziata, PRIMA di eseguire.

    Un criterio cieco alla verita' — che guarda solo la FORMA — quanto ci
    prende? **50% e' il caso; molto di piu' significa che la forma predice la
    classe**, e allora il confronto misurera' la forma invece della verita'.

    ⚠️ **UNO SOLO NON BASTA, ed e' la lezione che mi e' costata di piu' il
    30/08.** Avevo certificato `truthfulqa` «pulita» con il criterio sulla
    LUNGHEZZA (50,0%, il caso esatto) e l'ho scritto due volte come se fosse un
    verdetto generale. Poi ho misurato le NEGAZIONI sulla stessa popolazione:

        veri con negazione  45%   ·   falsi con negazione  16%     (heldout)
        veri con negazione  43%   ·   falsi con negazione   7%     (dev)

    ⇒ **Su TruthfulQA negare vuol dire quasi sempre dire il vero** — e' un
    dataset di *misconception*, dove la risposta corretta SMENTISCE. ⇒ Il layer
    `L4-negazione`, che fermava 12 falsi e 11 veri, sembrava «non discriminare»:
    **stavo per proporlo come candidato cura, e sarebbe stato un peggioramento.**

    ⇒ 🔑 **«La popolazione e' pulita» vale SOLO sulla dimensione che hai
    misurato.** Serve un criterio cieco per OGNI dimensione di forma che i layer
    usano davvero — e le dimensioni non misurate vanno dichiarate ignote, non
    assunte sane.

    Misurato 30/08 sulla lunghezza: halueval **98%** · truthfulqa **50,0%**.
    """
    import statistics as st

    fuori: dict[str, float] = {}
    lun = [len(c.split()) for _, c, _ in casi]
    soglia = st.median(lun)
    fuori["lunghezza"] = 100 * sum(
        1 for (et, c, _) in casi if (len(c.split()) > soglia) == (et == "falso")
    ) / max(1, len(casi))

    #: per la negazione non c'e' una soglia: si guarda se la sua PRESENZA e'
    #: sbilanciata fra le classi. 50% = indifferente, lontano da 50 = predice.
    veri = [c for et, c, _ in casi if et == "vero"]
    falsi = [c for et, c, _ in casi if et == "falso"]
    qv = sum(1 for c in veri if _NEGAZIONE.search(c)) / max(1, len(veri))
    qf = sum(1 for c in falsi if _NEGAZIONE.search(c)) / max(1, len(falsi))
    #: quota fra i negativi che sono FALSI: 50% se la negazione non dice nulla
    tot_neg = qv * len(veri) + qf * len(falsi)
    fuori["negazione"] = 100 * (qf * len(falsi)) / tot_neg if tot_neg else 50.0
    fuori["_neg_quota_veri"] = round(100 * qv, 1)
    fuori["_neg_quota_falsi"] = round(100 * qf, 1)
    return fuori


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=None,
                    help="quanti ITEM (ognuno da' 2 claim: 1 vero + 1 falso)")
    ap.add_argument("--popolazione", choices=sorted(POPOLAZIONI), default="truthfulqa")
    ap.add_argument("--salta", type=int, default=0,
                    help="salta i primi N item: serve alla REPLICA su campione disgiunto")
    ap.add_argument("--out", default="benchmark/results/c10_lato_verimem.json")
    a = ap.parse_args()

    os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_c10_")
    from verimem.client import Memory  # noqa: E402 — dopo HIPPO_DATA_DIR
    #: la porta che usa `verimem save` (cli.py:975 e :1762), non una scorciatoia:
    #: se misurassi da una porta diversa misurerei un altro prodotto.

    casi, f_nome = carica(a.popolazione, a.n, a.salta)
    ciechi = criteri_ciechi(casi)
    print(f"  popolazione {a.popolazione} ({f_nome}) — {len(casi)} claim")
    #: sotto una quarantina di claim questi numeri sono degeneri: con 6 claim
    #: la lunghezza dava 83,3% e la negazione 0,0% su una popolazione che a 200
    #: claim risulta pulita sulla lunghezza. **Un righello che grida su un
    #: campione minuscolo insegna a ignorarlo**, ed e' il difetto dei presidi
    #: che gridano sul sano. ⇒ sotto la soglia si dice «non misurabile», che e'
    #: un'informazione diversa da «pulito».
    CAMPIONE_MINIMO = 40
    piccolo = len(casi) < CAMPIONE_MINIMO
    print("  criteri CIECHI alla verita' (50% = il caso; lontano da 50 = la forma predice):")
    for nome, val in ciechi.items():
        if nome.startswith("_"):
            continue
        scarto = abs(val - 50)
        if piccolo:
            esito = f"— non misurabile sotto {CAMPIONE_MINIMO} claim"
        elif scarto > 10:
            esito = "⚠️ ARTEFATTO DI FORMA"
        else:
            esito = "✅ non predice la classe"
        print(f"     {nome:12} {val:5.1f}%   {esito}")
    print(f"     (negazione presente nel {ciechi['_neg_quota_veri']}% dei veri e nel "
          f"{ciechi['_neg_quota_falsi']}% dei falsi)")
    print("  ⚠️ le dimensioni NON elencate qui sono IGNOTE, non sane: se un layer")
    print("     guarda una forma che non e' misurata sopra, il suo numero non e' letto.")
    cieco = ciechi["lunghezza"]
    if not piccolo and any(abs(v - 50) > 10 for k, v in ciechi.items() if not k.startswith("_")):
        print("  ⇒ almeno una dimensione e' viziata: i rapporti per LAYER che")
        print("     dipendono da quella forma NON sono interpretabili qui.")

    mem = Memory()
    esiti: list[dict] = []
    for i, (etichetta, claim, fonte) in enumerate(casi):
        try:
            r = mem.add(claim, source=fonte, topic=f"c10/{a.popolazione}")
            stato = getattr(r, "status", None) or (r.get("status") if isinstance(r, dict) else None)
            punteggio = (getattr(r, "grounding_score", None)
                         or (r.get("grounding_score") if isinstance(r, dict) else None))
            #: CHI ha fermato il fatto. `quarantined_by` lo dice direttamente;
            #: i layer stanno in `warnings[].layer` — NON in un campo `layers`,
            #: che e' vuoto (me l'aveva gia' detto @ws3 e avevo guardato quello
            #: sbagliato). Senza questo il banco dava un totale di veri persi
            #: che non si puo' interrogare: 29% e nessuna idea di chi li ferma.
            chi = r.get("quarantined_by") if isinstance(r, dict) else None
            warn = (r.get("warnings") or []) if isinstance(r, dict) else []
            strati = sorted({(w or {}).get("layer") for w in warn if (w or {}).get("layer")})
        except Exception as e:  # il banco non deve morire su un caso
            stato, punteggio, chi, strati = f"ERRORE:{type(e).__name__}", None, None, []
        esiti.append({"i": i, "etichetta": etichetta, "stato": stato,
                      "grounding": punteggio, "claim": claim[:120],
                      "quarantined_by": chi, "layer": strati})
        if (i + 1) % 20 == 0:
            print(f"    …{i + 1}/{len(casi)} claim", flush=True)
    item = casi

    #: «servito» = torna nel recall di default. Il quarantinato NON torna.
    def servito(e: dict) -> bool:
        return not str(e["stato"]).startswith("quarantin")

    veri = [e for e in esiti if e["etichetta"] == "vero"]
    falsi = [e for e in esiti if e["etichetta"] == "falso"]
    falsi_ammessi = [e for e in falsi if servito(e)]
    veri_persi = [e for e in veri if not servito(e)]

    #: il nome della popolazione si LEGGE dalla variabile, non si scrive a mano:
    #: questa riga ha stampato «HaluEval QA heldout» per due esecuzioni intere
    #: fatte su truthfulqa, perche' era una costante rimasta dal primo giro.
    #: Un log che dichiara la popolazione sbagliata e' il difetto che passiamo
    #: le giornate a smontare — con l'aggravante che il numero era giusto.
    print(f"\n  === VERIMEM su {a.popolazione} ({f_nome}) — {len(esiti)} claim ===")
    print(f"  faccia A  falsi AMMESSI (serviti):  {len(falsi_ammessi):4}/{len(falsi):<4} "
          f"= {100 * len(falsi_ammessi) / max(1, len(falsi)):5.1f}%")
    print(f"  faccia B  veri PERSI (quarantinati):{len(veri_persi):4}/{len(veri):<4} "
          f"= {100 * len(veri_persi) / max(1, len(veri)):5.1f}%")

    #: e la grandezza che l'utente subisce davvero: di cio' che gli viene
    #: SERVITO, quanto e' falso? (le due facce si combinano qui)
    serviti = [e for e in esiti if servito(e)]
    falsi_serviti = [e for e in serviti if e["etichetta"] == "falso"]
    print(f"\n  ⇒ di cio' che viene SERVITO, e' falso: {len(falsi_serviti)}/{len(serviti)} "
          f"= {100 * len(falsi_serviti) / max(1, len(serviti)):5.1f}%   <- il numero di Aurelio")
    print(f"     (senza gate lo stesso corpus servirebbe "
          f"{len(falsi)}/{len(esiti)} = {100 * len(falsi) / max(1, len(esiti)):.1f}% falso)")

    sha = subprocess.run(["git", "log", "-1", "--format=%h"], cwd=RADICE,
                         capture_output=True, text=True).stdout.strip()
    #: la LUNGHEZZA per esito: e' il modo di verificare A POSTERIORI se
    #: l'artefatto di forma (LANT-68) ha morso anche su questa popolazione.
    #: Se i veri PERSI sono sistematicamente piu' corti dei veri AMMESSI, il
    #: gate sta punendo la brevita' e non la falsita'. Senza questi numeri il
    #: banco dava un totale che non si puo' interrogare — ed e' la lezione
    #: «un rapporto senza regime inganna» applicata al mio stesso strumento.
    import statistics as st

    def _med(gruppo: list[dict]) -> float:
        L = [len(e["claim"].split()) for e in gruppo]
        return round(st.median(L), 1) if L else 0.0

    veri_ammessi = [e for e in veri if servito(e)]
    falsi_fermati = [e for e in falsi if not servito(e)]
    lunghezze = {"veri_ammessi": _med(veri_ammessi), "veri_persi": _med(veri_persi),
                 "falsi_ammessi": _med(falsi_ammessi), "falsi_fermati": _med(falsi_fermati)}
    print("")
    print("  lunghezza mediana (parole) per esito — il controllo dell'artefatto:")
    for k, v in lunghezze.items():
        print(f"     {k:16} {v:5.1f}")
    if lunghezze["veri_persi"] and lunghezze["veri_ammessi"]:
        r = lunghezze["veri_persi"] / lunghezze["veri_ammessi"]
        print(f"     ⇒ veri persi / veri ammessi = {r:.2f}x  "
              f"{'⚠️ il gate punisce la brevita' if r < 0.7 else 'la lunghezza non spiega chi cade'}")

    #: ═══ CHI ferma i VERI — la domanda lasciata aperta in LANT-69 ═══
    #: Il 29% di veri persi era un totale che non si poteva interrogare. Qui si
    #: conta per DECISORE (`quarantined_by`) e per LAYER (`warnings[].layer`,
    #: non un campo `layers` che resta vuoto). Senza questa riga il banco dice
    #: quanto perdiamo e non da chi: e' la differenza fra un numero e una cura.
    from collections import Counter

    per_chi = Counter((e.get("quarantined_by") or "(non registrato)") for e in veri_persi)
    per_layer = Counter(s for e in veri_persi for s in (e.get("layer") or []) or ["(nessun layer)"])
    print("")
    print(f"  CHI ferma i {len(veri_persi)} VERI persi — per decisore:")
    for k, n in per_chi.most_common():
        print(f"     {n:4}  {k}")
    print(f"  e per layer (un fatto puo' averne piu' d'uno):")
    for k, n in per_layer.most_common():
        print(f"     {n:4}  {k}")
    #: il rovescio, obbligatorio: gli stessi layer sui FALSI FERMATI. Un layer
    #: che compare SOLO sui veri persi e' un candidato cura; uno che compare su
    #: entrambi sta facendo il suo lavoro e ha un costo.
    per_layer_falsi = Counter(s for e in falsi_fermati for s in (e.get("layer") or []) or ["(nessun layer)"])
    print(f"  e gli stessi layer sui {len(falsi_fermati)} FALSI fermati — il rovescio:")
    for k, n in per_layer_falsi.most_common():
        quota = per_layer.get(k, 0)
        print(f"     {n:4}  {k}   (sui veri persi: {quota})")

    corpo = {"popolazione": f_nome, "saltati": a.salta,
             "criterio_cieco_pct": round(cieco, 1),
             "lunghezza_mediana_per_esito": lunghezze,
             "veri_persi_per_decisore": dict(per_chi),
             "veri_persi_per_layer": dict(per_layer),
             "falsi_fermati_per_layer": dict(per_layer_falsi),
             "claim": len(esiti),
             "falsi_ammessi": len(falsi_ammessi), "falsi_totali": len(falsi),
             "veri_persi": len(veri_persi), "veri_totali": len(veri),
             "falsi_fra_i_serviti": len(falsi_serviti), "serviti": len(serviti),
             "commit": sha, "store": "temporaneo (HIPPO_DATA_DIR)"}
    out = RADICE / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpo, indent=2), encoding="utf-8")
    print(f"\n  REGIME  commit {sha} · store temporaneo · popolazione PUBBLICA mai scritta da noi")
    print(f"  scritto {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
