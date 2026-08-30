"""Un chiamante puo' sapere che il moat NON ha girato, leggendo un CAMPO?

LA DOMANDA. Il gate ammette un write anche quando il giudice non e' disponibile
— e' dichiarato in quattro posti, e la ricevuta lo scrive in prosa
(`L4-skipped — entailment NOT verified for THIS write`). Ma un agente non legge
la prosa: legge **campi**. Se la distinzione fra «giudicato e passato» e «non
giudicato affatto» vivesse solo in una frase, ogni chiamante automatico
tratterebbe i due casi allo stesso modo.

E LA RISPOSTA E' GIA' SCRITTA — nelle istruzioni che il server MCP consegna
agli agenti, verbatim::

    That separation is NOT readable in `status`, which stays `model_claim`
    either way: it is `grounding_score` that carries it — a number means a
    source was judged, `null` means never judged.

⇒ Il prodotto **dichiara** sia il campo che porta l'informazione, sia il campo
che NON la porta. Resta da verificare che dica il vero, e in ENTRAMBI i versi:
non basta che un giudicato abbia il numero — serve che un NON giudicato non ce
l'abbia, altrimenti il campo non discrimina.

LA PREDIZIONE, scritta prima di eseguire: **la promessa regge 3 su 3**. Il
prodotto e' stato preciso ogni volta che ha dichiarato un proprio limite (il
fail-open, l'eccezione `meta_narrative`, il costo del primo write), e una frase
che nomina il campo *sbagliato* accanto a quello giusto non e' una frase di
marketing.

CONDIZIONE DI FALSIFICAZIONE: se un write NON giudicato porta un
`grounding_score` numerico — poniamo `0` — il campo non discrimina, ogni
chiamante che filtra su `grounding_score < soglia` tratterebbe «non giudicato»
come «giudicato male», e la frase delle istruzioni sarebbe falsa nel punto in
cui e' piu' utile.

CONTROLLO CHE DEVE POTER FALLIRE: il regime «giudice presente» deve produrre un
numero **e** una quarantena (la fonte NEGA il claim). Se non giudicasse nemmeno
li', non misurerei la distinzione: misurerei un moat spento.

REGIME: tre processi separati, store TEMPORANEO ciascuno, `Memory()` **senza
path esplicito** (un path esplicito mette i fatti fuori dalla vista di
`doctor`/`status`, misurato il 30/08). Il giudice si rende assente puntando
`ENGRAM_LOCAL_GATE_MODEL` a una cartella vuota: **nessun download, nessuna
disinstallazione**. Lo store di Aurelio non e' toccato.

🟢 ESITO: **LA PROMESSA REGGE 3/3, e c'e' un campo IN PIU' di quanto prometta.**

    regime                     judge      status        grounding_score  layer
    giudice PRESENTE + fonte   delegated  quarantined   0.56             L4.1,L4-grounding
    giudice ASSENTE  + fonte   absent     model_claim   null             L4-skipped
    giudice PRESENTE, no fonte warming    model_claim   null             (vuoto)

    giudicato -> numero .............................. SI
    non giudicato (giudice assente) -> null .......... SI
    mai giudicato (nessuna fonte)   -> null .......... SI
    `status` distingue? .............................. NO  {model_claim, quarantined}

🔑 **DUE campi, e insieme separano tutti e tre gli stati**:
  · `grounding_score` — numero contro `null`: **giudicato** contro **no**
  · il **layer** `L4-skipped` — presente contro assente: **c'era una fonte e non
    e' stata giudicata** contro **non c'era fonte da giudicare**

⇒ Un chiamante che legge **solo campi** distingue i tre casi. La seconda
distinzione non e' promessa dalle istruzioni: **il prodotto ne offre una in piu'
di quante ne dichiari**, ed e' il verso giusto in cui sbagliare una promessa.

⚠️ E la parte che il prodotto dichiara di NON avere e' vera: **`status` non
distingue**, `model_claim` copre sia «non giudicato» sia «mai giudicato». Chi
filtrasse su `status` tratterebbe i due casi allo stesso modo — ed e'
esattamente cio' che la frase delle istruzioni avverte di non fare.

⚠️ LIMITI: un claim, una fonte, italiano, porta SDK. La ricevuta MCP espone gli
stessi campi con nomi in parte diversi (misurato altrove); qui si verifica la
PROMESSA, non l'equivalenza fra le due porte.

    python docs/stato-reale/banchi/ws3-il-campo-che-distingue-non-giudicato-da-giudicato.py
"""

from __future__ import annotations

import json
import subprocess
import sys

CLAIM = "La penale e' di 500 euro al giorno."
FONTE = "Il contratto fissa la penale in 120 euro al giorno."

FIGLIO = r'''
import json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
if sys.argv[1] == "assente":
    # cartella VUOTA: il giudice risulta assente senza toccare l'installazione
    os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()
from verimem.client import Memory
from verimem.local_grounding import judge_state
mem = Memory()          # senza path esplicito: i fatti restano visibili al prodotto
claim, fonte = sys.argv[2], sys.argv[3]
kw = {"source": fonte} if fonte else {}
r = mem.add(claim, topic="campo/1", validate="full", **kw)
lay = [str(w.get("layer")) for w in (r.get("warnings") or []) if isinstance(w, dict)]
print(json.dumps({"judge": judge_state(), "status": r.get("status"),
                  "gs": r.get("grounding_score"), "lay": lay},
                 default=str, ensure_ascii=False))
'''

REGIMI: list[tuple[str, str, str]] = [
    ("giudice PRESENTE + fonte", "presente", FONTE),
    ("giudice ASSENTE  + fonte", "assente", FONTE),
    ("giudice PRESENTE, no fonte", "presente", ""),
]


def main() -> int:
    print("  PROMESSA (istruzioni del server MCP, verbatim):")
    print("    «it is `grounding_score` that carries it — a number means a")
    print("     source was judged, `null` means never judged»")
    print("\n  POPOLAZIONE APPAIATA: stesso claim, stessa fonte, tre regimi.\n")
    print(f"  {'regime':<28} {'judge':<11} {'status':<13} "
          f"{'grounding_score':<17} layer")
    print("  " + "-" * 88)

    letto: dict[str, dict] = {}
    for etichetta, modo, fonte in REGIMI:
        p = subprocess.run([sys.executable, "-c", FIGLIO, modo, CLAIM, fonte],
                           capture_output=True, text=True, timeout=1800)
        if p.returncode != 0:
            print(f"  {etichetta:<28} PROCESSO-MORTO exit={p.returncode} "
                  f"{p.stderr.strip()[-80:]!r}")
            continue
        d = json.loads(p.stdout.strip().splitlines()[-1])
        letto[etichetta] = d
        gs = d["gs"]
        print(f"  {etichetta:<28} {d['judge']:<11} {str(d['status']):<13} "
              f"{('null' if gs is None else f'{float(gs):.2f}'):<17} "
              f"{','.join(d['lay']) or '(vuoto)'}")

    if len(letto) < len(REGIMI):
        print("\n  CELLE MANCANTI: un processo e' morto. NESSUN VERDETTO.")
        return 1

    a = letto["giudice PRESENTE + fonte"]
    b = letto["giudice ASSENTE  + fonte"]
    c = letto["giudice PRESENTE, no fonte"]

    print("\n  [1] CONTROLLO — a giudice presente la fonte che NEGA quarantina: "
          f"{'SI' if a['status'] == 'quarantined' else 'NO'}")
    if a["status"] != "quarantined":
        print("      CONTROLLO CADUTO: il moat non ferma nemmeno una fonte che")
        print("      nega ⇒ misuro un moat spento, non la distinzione dei campi.")
        print("      NESSUN VERDETTO.")
        return 1

    reg = [a["gs"] is not None, b["gs"] is None, c["gs"] is None]
    print("\n  ══ VERDETTO ══")
    print(f"     giudicato -> un NUMERO ....................... {'SI' if reg[0] else 'NO'}")
    print(f"     non giudicato (giudice assente) -> null ...... {'SI' if reg[1] else 'NO'}")
    print(f"     mai giudicato (nessuna fonte)   -> null ...... {'SI' if reg[2] else 'NO'}")
    stati = sorted({str(x["status"]) for x in (a, b, c)})
    print(f"     `status` distingue i tre casi? ............... "
          f"{'SI' if len(stati) == 3 else 'NO'}  {stati}")

    l4b = any("L4-skipped" in x for x in b["lay"])
    l4c = any("L4-skipped" in x for x in c["lay"])
    if all(reg):
        print("\n     🟢 LA PROMESSA REGGE 3/3. E c'e' un campo IN PIU' di quanto")
        print("     prometta: il layer `L4-skipped` compare quando una fonte")
        print(f"     c'era e non e' stata giudicata ({l4b}) e NON quando fonte")
        print(f"     non ce n'era ({l4c}) ⇒ i tre stati si separano leggendo")
        print("     SOLO campi, senza toccare la prosa.")
        print("     ⚠️ E la parte che il prodotto dichiara di NON avere e' vera:")
        print("     `status` non distingue. Chi filtrasse su quello tratterebbe")
        print("     «non giudicato» come «giudicato e passato».")
    else:
        print("\n     🔴 LA PROMESSA CADE: `grounding_score` non discrimina come")
        print("     dichiarato. Ogni chiamante che filtra su quel campo tratta")
        print("     «non giudicato» come «giudicato male», e la frase delle")
        print("     istruzioni e' falsa nel punto in cui e' piu' utile.")

    print("\n  ⚠️ LIMITI: un claim, una fonte, italiano, porta SDK. La ricevuta")
    print("     MCP espone gli stessi campi con nomi in parte diversi: qui si")
    print("     verifica la PROMESSA, non l'equivalenza fra le due porte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
