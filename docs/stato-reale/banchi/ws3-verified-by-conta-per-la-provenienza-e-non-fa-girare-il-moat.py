"""`verified_by` conta per la PROVENIENZA e NON fa girare il moat: regge 4/4.

LA PROMESSA, dalle istruzioni che il server MCP consegna agli agenti::

    `verified_by` records WHO vouches for a fact and **does not run this
    check**; pass the source text to get it.

⚠️ PERCHE' CONTA: un chiamante che passa `verified_by` puo' **credersi
protetto**. Se il giudice non c'e', il write e' ammesso non giudicato — e se
`verified_by` alzasse lo status o il punteggio, **un fatto sembrerebbe verificato
senza che nulla lo abbia verificato**. E' il difetto piu' grave che questo
prodotto possa avere, perche' e' esattamente cio' che promette di non fare.

LA PREDIZIONE, scritta prima di eseguire: **la promessa regge**. Il prodotto e'
stato preciso su ogni limite dichiarato che ho misurato oggi (dieci su dieci), e
questa frase nomina **il campo che NON fa la cosa**, che non e' una forma da
brochure.

CONDIZIONE DI FALSIFICAZIONE: se con `verified_by` lo `status` sale o compare un
`grounding_score` che senza non c'era, la promessa cade **nel punto in cui e'
piu' utile**.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE, ed e' il pezzo che rende leggibile tutto
il resto: **`verified_by` deve cambiare l'esito DA QUALCHE PARTE.** Se non lo
cambiasse mai, un «regge 4/4» misurerebbe **un campo ignorato**, non una
promessa mantenuta — e sarebbe indistinguibile da un successo.
═══════════════════════════════════════════════════════════════════════════════

🟢 ESITO: **LA PROMESSA REGGE 4/4, E IL CONTROLLO E' RETTO.**

    [1] la promessa — stesso claim, stessa fonte, quattro celle

        giudice    verified_by  status        gs      strati
        presente   no           quarantined   0.56    L4.1,L4-grounding
        presente   si           quarantined   0.56    L4.1,L4-grounding
        assente    no           model_claim   None    L4-skipped
        assente    si           model_claim   None    L4-skipped

    ⇒ `verified_by` non muove **ne' lo status ne' il punteggio**, in nessuno dei
      due regimi. Chi lo passa **non guadagna una protezione che non ha.**

    [2] il controllo — self-claim NUDO, senza fonte

        verified_by  status        qb    strati
        no           quarantined   L1    L1.10,L1.15,L1.20
        si           model_claim   -     (nessuno)

    ⇒ Il campo **conta eccome**: sposta la provenienza (`classify_provenance`
      lo legge, `anti_confab_gate:1954`) e `L1` non si applica piu'.

⇒ Le due misure insieme dicono la cosa esatta: **`verified_by` decide CHI
sta parlando, non SE il fatto sia vero.** E' la separazione giusta, ed e' quella
che la frase delle istruzioni dichiara.

⚠️ E IL COSTO DEL BYPASS, che non e' un difetto ma va detto: `verified_by` e'
**dichiarato dal chiamante e non verificato**. Un agente che scrive
`verified_by=["pytest:PASS"]` senza aver eseguito pytest ottiene il passaggio.
🔑 **Il prodotto lo sa e lo ha gia' scritto altrove**, nel commit della guardia
anti-eco: «*`writer_role` e' una dichiarazione di chi chiama. La guardia alza il
costo da «riformula una frase» a «dichiara il falso su un campo»*». **La stessa
soglia vale qui**, ed e' una soglia deliberata: il gate nomina persino il formato
che si aspetta (`pytest:_PASS` / `ci:` / `test_coverage:`) nel proprio avviso.
⇒ **Non e' una falla nascosta: e' il modello di fiducia, dichiarato.** Che il
gate DEBBA sospettare del chiamante e' una decisione di design, non una misura.

⚠️ LIMITI: un claim per popolazione, italiano, porta SDK, `ENGRAM_L1_DOMAIN_
PRECISION=0` nel controllo (il regime legacy, per far parlare `L1`). Il giudice
si rende assente puntando `ENGRAM_LOCAL_GATE_MODEL` a una cartella vuota —
nessun download, ⛔ nessun `warmup`. Store TEMPORANEO; quello di Aurelio intatto.

    python docs/stato-reale/banchi/ws3-verified-by-conta-per-la-provenienza-e-non-fa-girare-il-moat.py
"""

from __future__ import annotations

import json
import subprocess
import sys

CLAIM = "La penale e' di 500 euro al giorno."
FONTE = "Il contratto fissa la penale in 120 euro al giorno."
#: self-claim NUDO: quello che `L1` esiste per fermare
AUTOCLAIM = "Il fix funziona ed e' verificato."

FIGLIO = r'''
import json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["HIPPO_ENCODE_DELEGATE_ONLY"] = "0"
os.environ["ENGRAM_L1_DOMAIN_PRECISION"] = "0"
if sys.argv[1] == "assente":
    os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
from verimem.client import Memory
claim, fonte = sys.argv[3], sys.argv[4]
kw = {"source": fonte} if fonte else {}
if sys.argv[2] == "vb":
    kw["verified_by"] = ["pytest:PASS", "ci:green"]
r = Memory().add(claim, topic="vb/x", validate="full", **kw)
lay = [str(w.get("layer")) for w in (r.get("warnings") or []) if isinstance(w, dict)]
gs = r.get("grounding_score")
print(json.dumps({"status": r.get("status"),
                  "gs": None if gs is None else round(float(gs), 2),
                  "qb": str(r.get("quarantined_by") or "-"), "lay": lay},
                 default=str, ensure_ascii=False))
'''


def _cella(giudice: str, vb: str, claim: str, fonte: str) -> dict:
    p = subprocess.run([sys.executable, "-c", FIGLIO, giudice, vb, claim, fonte],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        raise RuntimeError(f"processo morto exit={p.returncode}: "
                           f"{p.stderr.strip()[-120:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def main() -> int:
    print("  PROMESSA (istruzioni MCP): «`verified_by` records WHO vouches for a")
    print("  fact and DOES NOT RUN THIS CHECK; pass the source text to get it».\n")

    print("  [1] LA PROMESSA — stesso claim, stessa fonte, quattro celle")
    print(f"      {'giudice':<10} {'verified_by':<12} {'status':<13} {'gs':<7} strati")
    print("      " + "-" * 62)
    p1: dict[tuple[str, str], dict] = {}
    for g in ("presente", "assente"):
        for vb in ("no", "vb"):
            d = _cella(g, vb, CLAIM, FONTE)
            p1[(g, vb)] = d
            print(f"      {g:<10} {('si' if vb == 'vb' else 'no'):<12} "
                  f"{str(d['status']):<13} {str(d['gs']):<7} "
                  f"{','.join(d['lay']) or '-'}")

    print("\n  [2] IL CONTROLLO — self-claim NUDO, senza fonte")
    print(f"      {'verified_by':<12} {'status':<13} {'qb':<6} strati")
    print("      " + "-" * 52)
    p2 = {vb: _cella("presente", vb, AUTOCLAIM, "") for vb in ("no", "vb")}
    for vb in ("no", "vb"):
        d = p2[vb]
        print(f"      {('si' if vb == 'vb' else 'no'):<12} {str(d['status']):<13} "
              f"{d['qb']:<6} {','.join(d['lay']) or '(nessuno)'}")

    cambia = (p2["no"]["status"] != p2["vb"]["status"]
              or p2["no"]["lay"] != p2["vb"]["lay"])
    print(f"\n      CONTROLLO — `verified_by` cambia l'esito qui: "
          f"{'SI' if cambia else 'NO'}")
    if not cambia:
        print("      CONTROLLO CADUTO: il campo non cambia niente nemmeno dove")
        print("      dovrebbe ⇒ non posso dire che la promessa «regge»: misurerei")
        print("      un campo INERTE, indistinguibile da un successo.")
        print("      NESSUN VERDETTO.")
        return 1

    invariato = all(p1[(g, "no")]["status"] == p1[(g, "vb")]["status"]
                    and p1[(g, "no")]["gs"] == p1[(g, "vb")]["gs"]
                    for g in ("presente", "assente"))
    print("\n  ══ VERDETTO ══")
    if invariato:
        print("     🟢 LA PROMESSA REGGE 4/4: `verified_by` non muove ne' lo status")
        print("     ne' il punteggio, in nessuno dei due regimi. Chi lo passa NON")
        print("     guadagna una protezione che non ha.")
        print("     ⇒ Con il controllo: **`verified_by` decide CHI sta parlando,")
        print("     non SE il fatto sia vero** — la separazione che le istruzioni")
        print("     dichiarano.")
    else:
        print("     🔴 LA PROMESSA CADE: `verified_by` muove l'esito o il punteggio")
        print("     ⇒ un fatto puo' SEMBRARE verificato senza che nulla lo abbia")
        print("     verificato, ed e' il difetto piu' grave possibile qui.")

    print("\n  ⚠️ COSTO DEL BYPASS, dichiarato: `verified_by` e' scritto dal")
    print("     chiamante e non verificato. La soglia e' «dichiarare il falso su")
    print("     un campo» — la stessa gia' scritta per `writer_role` nella guardia")
    print("     anti-eco. Non e' una falla nascosta: e' il modello di fiducia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
