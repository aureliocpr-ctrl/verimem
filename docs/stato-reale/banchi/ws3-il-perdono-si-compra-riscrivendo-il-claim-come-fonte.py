"""Il perdono di `L1.13` si compra riscrivendo il claim come fonte.

CONTESTO. La cura `e3ecd7f1` (28/08, Agent: Paragone, assegnata da lead-audit)
ha risolto un difetto vero: `detect_unsupported_completion_claim` non riceveva
la fonte, e su un verbale d'ufficio («la pratica e' stata chiusa») fermava fatti
VERI con la fonte al 99,9. La cura passa `source` al detector e **non segnala
quando il `matched_text` compare verbatim nella fonte**. Il commit dichiara il
proprio limite con precisione::

    si perdona solo cio' che la fonte scrive. Una self-claim senza fonte non ha
    nulla da perdonare e resta fermata.

⚠️ QUELLA FRASE E' VERA ALLA LETTERA, e questo banco la conferma: **senza fonte
il claim resta fermato 5/5**. Cio' che la frase non nomina e' che **chi scrive
la fonte e' chi scrive il claim**. Se il chiamante passa come `source` la stessa
identica frase, il `matched_text` compare verbatim **per costruzione**, e il
perdono diventa una scelta del chiamante invece che una proprieta' della fonte.

LA DOMANDA: quanto e' larga questa via? Un caso non e' una classe, e un buco che
si apre su ogni claim e' un'altra cosa da un buco che si apre su tre domini.

LA PREDIZIONE, scritta prima di eseguire: **la via si apre sui domini che la
cura voleva servire** (verbali, pratiche, adempimenti) e **resta chiusa su
software/deploy**, perche' li' un SECONDO strato prende il claim comunque — il
commit stesso dichiarava che «La consegna e' stata effettuata» resta fermata da
`L1.20`, non da `L1.13`.

CONDIZIONE DI FALSIFICAZIONE: se **tutti e cinque** scappano con l'eco, la via
non e' legata al dominio ma alla guardia, ed e' molto piu' larga di come la
racconto. Se **nessuno** scappa, la cura non introduce alcuna via e il reperto
non esiste.

CONTROLLO CHE DEVE POTER FALLIRE: **senza fonte tutti e cinque devono essere
fermati**. Se anche uno passasse gia' senza fonte, non misurerei l'eco:
misurerei un detector che non prende quel claim, e ogni cella sarebbe illeggibile.

⚠️ REGIME DICHIARATO: `ENGRAM_L1_DOMAIN_PRECISION=0`, cioe' il carve-out di
dominio DISATTIVATO — lo stesso regime che il fixture di
`test_quarantine_restore_public.py` chiede. Col default (ON, dal 22/07) il claim
legale passa comunque per via del carve-out, e la misura direbbe un'altra cosa.
**La leva morde**: verificato con la cella `PREC=1` contro `PREC=0` a fonte
assente. Store TEMPORANEO, mai quello di Aurelio.

🔴 ESITO: PREDIZIONE RETTA — **3 su 5 scappano**, e sono i tre non-software.

    claim          senza fonte      fonte = eco del claim
    LEGALE  EN     FERMATO L1       passa      <-- scappa
    VERBALE IT     FERMATO L1       passa      <-- scappa
    AUDIT   EN     FERMATO L1       passa      <-- scappa
    SOFTWARE       FERMATO L1       FERMATO L1
    DEPLOY  IT     FERMATO L1       FERMATO L1

    controllo (fermati senza fonte): 5/5     scappano con l'eco: 3/5

⇒ La via di fuga **esiste e non e' universale**. Chi resta fermato lo deve a un
SECONDO strato, non alla guardia curata: togliere quel secondo strato
allargherebbe la via senza che nulla diventi rosso.
🔑 E' il banco D di lead-audit (`ef234ae0`, «il fail-closed anti-auto-sorgente si
aggira per riformulazione 3/3») **da un lato nuovo**: qui non serve nemmeno
riformulare — basta la copia identica — e il bersaglio e' `L1.13` DOPO la cura.

⚠️ COSA QUESTO BANCO NON DICE: cinque casi scritti da me, due lingue, un solo
sotto-strato. **3/5 non e' un tasso**: dice che la via esiste e che non e'
universale. Non dice quanti claim reali la percorrerebbero, e non dice se sia un
difetto o il modello di fiducia del prodotto — il gate non puo' sapere se il
chiamante mente sulla fonte, e stabilire se debba provare a saperlo e' una
decisione di design, non una misura.

    python docs/stato-reale/banchi/ws3-il-perdono-si-compra-riscrivendo-il-claim-come-fonte.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

#: ogni claim gira in un processo suo: la variabile d'ambiente si legge una
#: volta e un processo unico misurerebbe il primo regime per tutti.
FIGLIO = r'''
import json, os, sys, tempfile
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
from verimem.client import Memory
mem = Memory(os.environ["HIPPO_DATA_DIR"] + "/eco.db")
claim = sys.argv[1]
kw = {"source": claim} if sys.argv[2] == "eco" else {}
r = mem.add(claim, topic="legal/deal", verified_by=["source-doc:dd:1"], **kw)
print(json.dumps({"status": r.get("status"), "qb": r.get("quarantined_by")},
                 default=str, ensure_ascii=False))
'''

CASI: list[tuple[str, str]] = [
    ("LEGALE  EN",
     "The due-diligence review was completed before the acquisition closed."),
    ("VERBALE IT",
     "La pratica e' stata chiusa prima della scadenza."),
    ("AUDIT   EN",
     "The compliance audit was completed by the external firm."),
    ("SOFTWARE  ",
     "The database migration was completed and verified in production."),
    ("DEPLOY  IT",
     "Il deploy in produzione e' stato completato e verificato."),
]


def _scrivi(claim: str, modo: str, env: dict) -> str:
    p = subprocess.run([sys.executable, "-c", FIGLIO, claim, modo],
                       env=env, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        return f"MORTO exit={p.returncode}"
    d = json.loads(p.stdout.strip().splitlines()[-1])
    if d["status"] != "quarantined":
        return "passa"
    return f"FERMATO {d['qb']}"


def main() -> int:
    env = dict(os.environ)
    env["ENGRAM_L1_DOMAIN_PRECISION"] = "0"
    print("  REGIME: ENGRAM_L1_DOMAIN_PRECISION=0 (il carve-out di dominio OFF,")
    print("          lo stesso che chiede il fixture di quarantine_restore)")
    print("          store TEMPORANEO per ogni scrittura; quello di Aurelio mai toccato\n")

    print(f"  {'claim':<12} {'senza fonte':<18} {'fonte = eco del claim':<22}")
    print("  " + "-" * 56)
    fermati_senza = 0
    scappati = 0
    for etichetta, claim in CASI:
        senza = _scrivi(claim, "no", env)
        eco = _scrivi(claim, "eco", env)
        fuga = senza.startswith("FERMATO") and eco == "passa"
        fermati_senza += senza.startswith("FERMATO")
        scappati += fuga
        print(f"  {etichetta:<12} {senza:<18} {eco:<22}"
              f"{'  <-- scappa' if fuga else ''}")

    tot = len(CASI)
    print(f"\n  [1] CONTROLLO — fermati SENZA fonte: {fermati_senza}/{tot}")
    if fermati_senza < tot:
        print("      CONTROLLO CADUTO: un claim passa gia' senza fonte ⇒ non sto")
        print("      misurando l'eco, sto misurando un detector che non prende")
        print("      quel claim. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     scappano con la fonte-eco: {scappati}/{tot}")
    if scappati == tot:
        print("     PREDIZIONE FALSIFICATA: scappano TUTTI ⇒ la via non e' legata")
        print("     al dominio ma alla guardia, ed e' piu' larga di come la")
        print("     raccontavo. Il reperto va riscritto al rialzo.")
    elif scappati == 0:
        print("     PREDIZIONE FALSIFICATA: non scappa nessuno ⇒ la cura non")
        print("     introduce alcuna via, e il reperto non esiste.")
    else:
        print("     PREDIZIONE RETTA: la via esiste e NON e' universale. Chi resta")
        print("     fermato lo deve a un SECONDO strato, non alla guardia curata —")
        print("     e togliere quel secondo strato allargherebbe la via senza che")
        print("     nulla diventi rosso.")

    print(f"\n  ⚠️ LIMITI: {tot} casi scritti da me, 2 lingue, un solo sotto-strato.")
    print("     Non e' un tasso. E non dice se sia un difetto o il modello di")
    print("     fiducia del prodotto: che il gate DEBBA sospettare del chiamante")
    print("     e' una decisione di design, non una misura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
