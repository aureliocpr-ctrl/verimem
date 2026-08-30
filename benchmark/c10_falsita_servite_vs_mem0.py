r"""C10 — CHE TASSO DI FALSITA' SERVIAMO NOI, E QUALE NE SERVE UN CONCORRENTE.

La domanda e' di Aurelio, verbatim: **«che tasso di figure di merda fanno loro
e quale noi»**. Questo banco produce quel numero su una popolazione PUBBLICA e
su ENTRAMBE le facce.

POPOLAZIONE — `benchmark/data/external/halueval_qa_heldout.jsonl`
  HaluEval QA (RUCAIBox, licenza MIT, sha256 della fonte in
  `benchmark/data/external/README.md`). 200 item, ognuno con:
      knowledge            <- la FONTE
      right_answer         <- il claim VERO
      hallucinated_answer  <- il claim FALSO, costruito dagli autori
  ⇒ **400 claim etichettati, 200 veri e 200 falsi, ciascuno con la sua fonte.**
  Non l'abbiamo scritto noi: e' esattamente il punto di `TRUST_CORE.md` —
  «i numeri di fiducia smettono di correggere i nostri compiti».

  ⚠️ DISCIPLINA DEL README, rispettata: `heldout` si ESEGUE e non si legge. Lo
  sviluppo di questo banco e' avvenuto guardando UN item del `dev`.

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


def carica(nome: str, n: int | None) -> tuple[list[tuple[str, str, str]], str]:
    """Restituisce [(etichetta, claim, fonte)] — forma unica per le due popolazioni."""
    f_nome, forma = POPOLAZIONI[nome]
    with open(ESTERNI / f_nome, encoding="utf-8") as f:
        righe = [json.loads(r) for r in f if r.strip()]
    fuori: list[tuple[str, str, str]] = []
    if forma == "qa":
        for it in (righe[:n] if n else righe):
            fuori.append(("vero", it["right_answer"], it["knowledge"]))
            fuori.append(("falso", it["hallucinated_answer"], it["knowledge"]))
    else:
        for it in (righe[: 2 * n] if n else righe):
            fuori.append(("vero" if it["label"] == 1 else "falso", it["claim"], it["source"]))
    return fuori, f_nome


def criterio_cieco(casi: list[tuple[str, str, str]]) -> float:
    """Il righello che dice se la POPOLAZIONE e' viziata, prima di eseguire.

    Un criterio che guarda SOLO la lunghezza — cieco alla verita' — quanto ci
    prende? **50% e' il caso; molto di piu' significa che la forma predice la
    classe**, e allora il confronto misurera' la forma.

    Misurato 30/08: halueval **98%** (il falso e' 6x piu' lungo in 98 item su
    100) · truthfulqa **50,0%**. Due righe che mi hanno risparmiato un numero
    falso nel documento che conta le nostre figure di merda.
    """
    import statistics as st
    lun = [len(c.split()) for _, c, _ in casi]
    soglia = st.median(lun)
    giusti = sum(1 for (et, c, _) in casi if ((len(c.split()) > soglia) == (et == "falso")))
    return 100 * giusti / max(1, len(casi))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=None,
                    help="quanti ITEM (ognuno da' 2 claim: 1 vero + 1 falso)")
    ap.add_argument("--popolazione", choices=sorted(POPOLAZIONI), default="truthfulqa")
    ap.add_argument("--out", default="benchmark/results/c10_lato_verimem.json")
    a = ap.parse_args()

    os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws7_c10_")
    from verimem.client import Memory  # noqa: E402 — dopo HIPPO_DATA_DIR
    #: la porta che usa `verimem save` (cli.py:975 e :1762), non una scorciatoia:
    #: se misurassi da una porta diversa misurerei un altro prodotto.

    casi, f_nome = carica(a.popolazione, a.n)
    cieco = criterio_cieco(casi)
    print(f"  popolazione {a.popolazione} ({f_nome}) — {len(casi)} claim")
    print(f"  criterio CIECO alla verita' (solo lunghezza): {cieco:.1f}%  "
          f"{'⚠️ ARTEFATTO DI FORMA' if cieco > 60 else '✅ la forma non predice la classe'}")
    if cieco > 60:
        print("  ⇒ su questa popolazione il confronto misurerebbe la FORMA. "
              "Procedo solo perche' e' stato chiesto esplicitamente.")

    mem = Memory()
    esiti: list[dict] = []
    for i, (etichetta, claim, fonte) in enumerate(casi):
        try:
            r = mem.add(claim, source=fonte, topic=f"c10/{a.popolazione}")
            stato = getattr(r, "status", None) or (r.get("status") if isinstance(r, dict) else None)
            punteggio = (getattr(r, "grounding_score", None)
                         or (r.get("grounding_score") if isinstance(r, dict) else None))
        except Exception as e:  # il banco non deve morire su un caso
            stato, punteggio = f"ERRORE:{type(e).__name__}", None
        esiti.append({"i": i, "etichetta": etichetta, "stato": stato,
                      "grounding": punteggio, "claim": claim[:120]})
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

    print(f"\n  === VERIMEM su HaluEval QA heldout — {len(item)} item, {len(esiti)} claim ===")
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
    corpo = {"popolazione": f_nome, "criterio_cieco_pct": round(cieco, 1),
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
