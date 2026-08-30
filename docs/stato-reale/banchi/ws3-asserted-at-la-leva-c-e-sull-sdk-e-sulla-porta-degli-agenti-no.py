"""`asserted_at`: la leva regge sull'SDK e sulla porta degli agenti NON ARRIVA.

DA DOVE VIENE. Alle 19:03 @ws2 «Varco» ha misurato che `asserted_at` **funziona**
sul caso clinico: senza il campo la correzione *«DECEDUTO» -> «DIMESSO»*
**sostituisce in silenzio**; con un istante esplicito i due fatti restano e la
contraddizione puo' andare al giudice. Conclusione consegnata al report:

    «Il difetto e' INTERAMENTE di adozione e documentazione ⇒ la cura e' la
     riga di help, non un cambio di comportamento.»

E alle 18:51, la premessa su cui poggia:

    «Si puo' passare da tutte e tre le porte: CLI --asserted-at · SDK parametro
     di add() · MCP nello schema (:1695) ⇒ anche gli agenti.»

⚠️ **La seconda meta' e' nel mio perimetro (la superficie MCP) e non regge: lo
schema `:1695` NON e' quello di `hippo_remember`.** Letto prima di misurare:

    :1669  name="hippo_ingest_conversation"   <- lo schema :1695 e' SUO
    :2422  name="hippo_remember"              <- la porta con cui un agente
                                                 scrive un fatto ordinario
           proprieta' dichiarate: proposition · topic · user_id · agent_id ·
           run_id · confidence · verified_by · status · valid_until ·
           source_signature · validate · gate_mode · force_persist ·
           writer_role · meta_narrative · source · derives_from
           ⇒ **`asserted_at` NON c'e'**

E le due righe che rendono la cosa peggiore di una semplice omissione:

    :351  `_CHIAVI_DI_SCRITTURA` — l'insieme delle chiavi che una scrittura
          «puo' portare», usato per dire QUALE chiave e' stata ignorata —
          **contiene `asserted_at`** ⇒ chi lo passa non viene avvisato.
    :7585 l'unico punto di `hippo_remember` che inoltra `asserted_at` sta nel
          ramo **REMOTE** (`_rm.add`). Nel percorso **locale** (:12808-13600)
          la stringa `asserted_at` **non compare affatto**.

LA PREDIZIONE, scritta prima di eseguire: **su MCP locale il campo viene
scartato in silenzio e la sostituzione avviene lo stesso.**

CONDIZIONE DI FALSIFICAZIONE: se su MCP con `asserted_at` i due fatti restano
entrambi, allora il campo arriva per una via che non ho letto e la premessa di
@ws2 regge com'e' scritta.

═══════════════════════════════════════════════════════════════════════════════
🔑 I DUE CONTROLLI CHE DEVONO POTER FALLIRE, senza i quali il reperto non si
legge:
  ① **su MCP SENZA il campo la sostituzione deve avvenire** — se non avvenisse,
    starei misurando uno store in cui la supersessione non scatta mai, e il
    «con il campo non avviene» non significherebbe niente.
  ② **su SDK CON il campo la sostituzione NON deve avvenire** — e' la misura di
    @ws2 riprodotta: se non la riproduco, il confronto fra le due porte
    misurerebbe il mio banco, non le porte.
═══════════════════════════════════════════════════════════════════════════════

🔴 IL PRIMO GIRO E' CADUTO SUL CONTROLLO ①, e la ragione va scritta qui
perche' e' la famiglia dominante dei miei difetti di oggi: **la popolazione
non conteneva cio' che credevo di misurare**. Avevo dato UNA fonte sola alle
due scritture, cosi' che almeno una non fosse sostenuta ⇒ **tutti e quattro
i regimi hanno prodotto due fatti `quarantined`**, e un quarantinato non
entra nel percorso della supersessione. Quattro celle identiche, zero
sostituzioni, NESSUN VERDETTO — il controllo ha fermato un banco che
altrimenti avrebbe detto «la leva funziona ovunque», che e' il **verso
opposto** alla mia predizione ed e' cio' che rende utile un controllo.
⇒ Cura: **due fonti, ognuna che SOSTIENE il proprio claim** — come nel caso
di @ws2, che scriveva «stessa memoria, due fonti» e che avevo letto male.

REGIME: quattro processi separati, store TEMPORANEO ciascuno
(`HIPPO_DATA_DIR=mkdtemp()`), stesso TOPIC e stesso soggetto, **due fonti che
sostengono** (i due fatti devono essere AMMESSI, o non arrivano al ramo che
voglio osservare), `asserted_at` UGUALE nelle celle che lo passano — il caso
ambiguo, non l'evoluzione vera. Lo store di Aurelio non e' toccato. Il
verdetto si legge dal DB del prodotto (`CONFIG.semantic_db`), non dalla
ricevuta.

    python docs/stato-reale/banchi/ws3-asserted-at-la-leva-c-e-sull-sdk-e-sulla-porta-degli-agenti-no.py
"""

from __future__ import annotations

import json
import subprocess
import sys

A = "Il paziente Rossi e' DECEDUTO."
FONTE_A = "Referto del 12 marzo: il paziente Rossi risulta deceduto."
B = "Il paziente Rossi e' stato DIMESSO."
FONTE_B = "Referto del 12 marzo: il paziente Rossi e' stato dimesso."

FIGLIO = r'''
import asyncio, json, os, sqlite3, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
porta, con_campo, a_txt, fa_txt, b_txt, fb_txt = sys.argv[1:7]
AAT = 1756000000.0            # stesso istante per entrambe: il caso AMBIGUO

def scrivi_sdk(prop, fonte):
    from verimem.client import Memory
    kw = {"asserted_at": AAT} if con_campo == "si" else {}
    return Memory().add(prop, topic="clin/x", source=fonte, validate="full", **kw)

def scrivi_mcp(prop, fonte):
    from verimem import mcp_server
    args = {"proposition": prop, "topic": "clin/x", "source": fonte,
            "validate": "full"}
    if con_campo == "si":
        args["asserted_at"] = AAT
    out = asyncio.run(mcp_server._call_tool_impl("hippo_remember", args))
    return out

for _p, _f in ((a_txt, fa_txt), (b_txt, fb_txt)):
    (scrivi_sdk if porta == "sdk" else scrivi_mcp)(_p, _f)

from verimem.config import CONFIG
db = str(CONFIG.semantic_db)
righe = []
with sqlite3.connect(db) as c:
    c.row_factory = sqlite3.Row
    for r in c.execute("SELECT proposition, status, superseded_by FROM facts"):
        righe.append({"p": r["proposition"][:34], "status": r["status"],
                      "sup": r["superseded_by"]})
print(json.dumps({"db": db, "righe": righe}, ensure_ascii=False))
'''

CELLE: list[tuple[str, str, str]] = [
    ("MCP  senza asserted_at", "mcp", "no"),
    ("MCP  CON   asserted_at", "mcp", "si"),
    ("SDK  senza asserted_at", "sdk", "no"),
    ("SDK  CON   asserted_at", "sdk", "si"),
]


def _cella(porta: str, con: str) -> dict:
    p = subprocess.run([sys.executable, "-c", FIGLIO, porta, con,
                        A, FONTE_A, B, FONTE_B],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        raise RuntimeError(f"exit={p.returncode}: {p.stderr.strip()[-200:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def _sostituito(d: dict) -> bool:
    """Vero se una delle due scritture ha superseduto l'altra."""
    return any(r["sup"] for r in d["righe"])


def main() -> int:
    print("  PREMESSA DI @ws2 (18:51): «MCP nello schema (:1695) ⇒ anche gli")
    print("  agenti». LETTO PRIMA DI MISURARE: :1695 e' lo schema di")
    print("  `hippo_ingest_conversation`; `hippo_remember` (:2422) NON dichiara")
    print("  `asserted_at`, e il percorso locale non lo legge mai.\n")

    print(f"  {'cella':<26} {'fatti':<7} {'supersessione':<15} righe")
    print("  " + "-" * 86)
    letto: dict[str, dict] = {}
    for nome, porta, con in CELLE:
        try:
            d = _cella(porta, con)
        except RuntimeError as exc:
            print(f"  {nome:<26} PROCESSO MORTO {exc}")
            return 1
        letto[nome] = d
        stato = "SI (silenziosa)" if _sostituito(d) else "no"
        det = " | ".join(f"{r['p']}[{r['status']}]" for r in d["righe"])
        print(f"  {nome:<26} {len(d['righe']):<7} {stato:<15} {det[:60]}")

    mcp_no = letto["MCP  senza asserted_at"]
    mcp_si = letto["MCP  CON   asserted_at"]
    sdk_si = letto["SDK  CON   asserted_at"]

    print("\n  [1] CONTROLLO ① — su MCP SENZA il campo la sostituzione avviene: "
          f"{'SI' if _sostituito(mcp_no) else 'NO'}")
    if not _sostituito(mcp_no):
        print("      CONTROLLO CADUTO: in questo store la supersessione non")
        print("      scatta mai ⇒ un «con il campo non avviene» non significa")
        print("      niente. NESSUN VERDETTO.")
        return 1

    print("  [2] CONTROLLO ② — su SDK CON il campo la sostituzione NON avviene: "
          f"{'SI' if not _sostituito(sdk_si) else 'NO'}")
    if _sostituito(sdk_si):
        print("      CONTROLLO CADUTO: non riproduco la misura di @ws2 ⇒ il")
        print("      confronto fra le porte misurerebbe il mio banco, non le")
        print("      porte. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if _sostituito(mcp_si):
        print("     🔴 SULLA PORTA DEGLI AGENTI LA LEVA NON ARRIVA: con")
        print("     `asserted_at` passato a `hippo_remember` la sostituzione")
        print("     avviene lo stesso, mentre sull'SDK non avviene.")
        print("     ⇒ La premessa «esposto da tre porte su tre» non regge per")
        print("     la porta con cui un agente scrive un fatto ordinario, e la")
        print("     cura «una riga di help» NON basta su MCP: li' non c'e' un")
        print("     parametro da documentare.")
        print("     ⚠️ E il campo e' in `_CHIAVI_DI_SCRITTURA` (:351) ⇒ il")
        print("     meccanismo che esiste per dire «questa chiave l'ho")
        print("     ignorata» NON lo segnala.")
    else:
        print("     🟢 LA LEVA ARRIVA ANCHE SU MCP: la premessa di @ws2 regge")
        print("     com'e' scritta, e la mia lettura del sorgente era")
        print("     incompleta — il campo passa per una via che non ho letto.")

    print("\n  ⚠️ LIMITI: un caso, due scritture, italiano, `asserted_at` UGUALE")
    print("     (il caso ambiguo). Si misura SE il campo arriva alla porta, non")
    print("     quanto spesso servirebbe sul traffico reale.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
