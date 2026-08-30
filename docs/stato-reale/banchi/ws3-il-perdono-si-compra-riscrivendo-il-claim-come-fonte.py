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

LA DOMANDA: quanto e' larga questa via?

LA PREDIZIONE, scritta prima di eseguire: **la via si apre su ogni claim di
completamento**, perche' la condizione del perdono e' testuale e la fonte-eco la
soddisfa sempre. Cio' che restera' fermato lo dovra' a un **altro** detector,
non a questo.

CONDIZIONE DI FALSIFICAZIONE: se qualche claim resta fermato **da `L1.13`**
nonostante l'eco, il perdono non e' incondizionato e la via e' piu' stretta.

CONTROLLO CHE DEVE POTER FALLIRE: **senza fonte tutti devono essere fermati**.
Se anche uno passasse gia' senza fonte, non misurerei l'eco: misurerei un
detector che non prende quel claim, e ogni cella sarebbe illeggibile.

🔴 RETTIFICA DELLA PRIMA STESURA (30/08 13:55, commit 584df914 → questo).
La prima versione concludeva **3 su 5** e attribuiva la resistenza al **DOMINIO**
(«si apre sui verbali, resta chiusa su software/deploy»). **Era falso, e il
difetto stava nel banco**: due dei cinque claim — e solo quei due — contenevano
«and **verified**» / «e **verificato**», che sveglia `L1.15` (*tested/verified
claim*), un detector **diverso** che non c'entra col completamento.

    SOFTWARE con «verified»      senza fonte FERMATO L1.13,L1.15   eco FERMATO L1.15
    SOFTWARE SENZA «verified»    senza fonte FERMATO L1.13         eco passa

🔑 **Un banco che varia due cose insieme non puo' attribuire l'effetto a una.**
La popolazione ora e' **appaiata** — nessun claim porta parole da collaudo — e le
due coppie del confondente sono stampate invece che rimosse, perche' sono il
reperto piu' utile del banco.

🔴 ESITO, con la popolazione corretta: **`L1.13` perdona 5 su 5.**

    claim          senza fonte      fonte = eco del claim
    LEGALE  EN     FERMATO L1.13    passa
    VERBALE IT     FERMATO L1.13    passa
    AUDIT   EN     FERMATO L1.13    passa
    SOFTWARE       FERMATO L1.13    passa
    DEPLOY  IT     FERMATO L1.13    passa

⇒ **Il perdono e' incondizionato rispetto al contenuto**: basta ripassare la
frase come fonte. Cio' che salva un claim reale e' che porti *per caso* anche
un'altra parola sorvegliata — «verified», «fixed», «shipped» — e allora lo ferma
un altro strato, per un'altra ragione.
🔑 Si compone col banco di @Paragone `a83d9605` («il perimetro di `L1.13` e' sei
radici»): li' il layer si aggira **cambiando parola**, senza fonte; qui si aggira
**passando il claim come fonte**, senza cambiare parola. **Due vie indipendenti
sullo stesso strato**, e cio' che resta e' la copertura di detector che guardano
il gergo di collaudo. Un verbale d'ufficio non ne ha nessuno.
🔑 Ed e' il banco `ef234ae0` di lead-audit da un lato nuovo: la' il fail-closed
anti-auto-sorgente si aggirava **per riformulazione**; qui basta la **copia
identica**.

⚠️ COSA QUESTO BANCO NON DICE: cinque claim scritti da me, due lingue, un solo
sotto-strato. **5/5 non e' un tasso sul corpus**: e' la misura che la condizione
del perdono e' soddisfatta per costruzione dalla fonte-eco. Non dice quanti
chiamanti reali la percorrerebbero, e non dice se sia un difetto o il modello di
fiducia del prodotto — il gate non puo' sapere se il chiamante mente sulla
fonte, e stabilire se debba provare a saperlo e' design, non misura.

🟢 CHIUSO IL 30/08 ALLE 17:34 — LA GUARDIA ANTI-ECO E' IN SERVIZIO.
Il reperto (5/5) e' stato votato 3/3 alle 14:27 e **curato da un'altra istanza**
in `l1_completion_detector.py`, il cui commento cita questo banco::

    ⛔ GUARDIA ANTI-ECO (30/08, votata 3/3 sul registro dell'esame) … non
    nominava che **chi scrive la fonte puo' essere chi scrive il claim** … un
    banco indipendente l'ha misurato **5 su 5**. Quando parla l'agente, la sua
    `source` non e' una testimonianza: e' un'eco.

**Ri-eseguito come test di accettazione: 5/5 scappavano, 0/5 adesso**, controllo
5/5 retto.
⚠️ E per tre ore il ramo «zero scappati» di questo file diceva «*il reperto non
esiste*» — **falso**: il reperto esisteva ed e' stato **curato**. *La prosa era
rimasta ferma dove il codice si era mosso, dentro il banco che quella classe
l'aveva documentata.* Corretto sotto.

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
lay = [str(w.get("layer")) for w in (r.get("warnings") or []) if isinstance(w, dict)]
print(json.dumps({"status": r.get("status"), "layers": lay},
                 default=str, ensure_ascii=False))
'''

#: ⚠️ POPOLAZIONE APPAIATA: nessuno di questi claim porta parole da collaudo.
#: La prima stesura ne aveva due con «verified» e tre senza, e quella differenza
#: — non il dominio — produceva la resistenza che avevo scambiato per un
#: meccanismo.
CASI: list[tuple[str, str]] = [
    ("LEGALE  EN",
     "The due-diligence review was completed before the acquisition closed."),
    ("VERBALE IT",
     "La pratica e' stata chiusa prima della scadenza."),
    ("AUDIT   EN",
     "The compliance audit was completed by the external firm."),
    ("SOFTWARE  ",
     "The database migration was completed in production."),
    ("DEPLOY  IT",
     "Il deploy in produzione e' stato completato."),
]

#: le due coppie che ESPONGONO il confondente: identiche alle ultime due di
#: `CASI` piu' la parola che sveglia `L1.15`.
COPPIE_CONFONDENTE: list[tuple[str, str]] = [
    ("SOFTWARE + «verified»",
     "The database migration was completed and verified in production."),
    ("DEPLOY + «verificato»",
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
    return f"FERMATO {','.join(d['layers']) or '?'}"


def main() -> int:
    env = dict(os.environ)
    env["ENGRAM_L1_DOMAIN_PRECISION"] = "0"
    print("  REGIME: ENGRAM_L1_DOMAIN_PRECISION=0 (il carve-out di dominio OFF,")
    print("          lo stesso che chiede il fixture di quarantine_restore)")
    print("          store TEMPORANEO per ogni scrittura; quello di Aurelio mai toccato")

    print("\n  [0] IL CONFONDENTE, esposto invece che rimosso")
    print(f"      {'claim':<24} {'senza fonte':<22} {'fonte = eco':<16}")
    for etichetta, claim in COPPIE_CONFONDENTE:
        senza = _scrivi(claim, "no", env)
        eco = _scrivi(claim, "eco", env)
        print(f"      {etichetta:<24} {senza:<22} {eco:<16}")
    print("      ⇒ la stessa frase con una parola in piu' resta fermata, e NON")
    print("        dal detector del completamento: da `L1.15`. E' cio' che aveva")
    print("        falsato la prima stesura di questo banco.")

    print(f"\n  [1] LA POPOLAZIONE APPAIATA — {len(CASI)} claim, nessuna parola da collaudo")
    print(f"      {'claim':<14} {'senza fonte':<22} {'fonte = eco':<16}")
    print("      " + "-" * 54)
    fermati_senza = 0
    scappati = 0
    for etichetta, claim in CASI:
        senza = _scrivi(claim, "no", env)
        eco = _scrivi(claim, "eco", env)
        fuga = senza.startswith("FERMATO") and eco == "passa"
        fermati_senza += senza.startswith("FERMATO")
        scappati += fuga
        print(f"      {etichetta:<14} {senza:<22} {eco:<16}"
              f"{'  <-- scappa' if fuga else ''}")

    tot = len(CASI)
    print(f"\n  [2] CONTROLLO — fermati SENZA fonte: {fermati_senza}/{tot}")
    if fermati_senza < tot:
        print("      CONTROLLO CADUTO: un claim passa gia' senza fonte, quindi non")
        print("      sto misurando l'eco ma un detector che non prende quel claim.")
        print("      NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    print(f"     scappano con la fonte-eco: {scappati}/{tot}")
    if scappati == tot:
        print("     PREDIZIONE RETTA: il perdono e' INCONDIZIONATO rispetto al")
        print("     contenuto — la fonte-eco soddisfa la condizione testuale per")
        print("     costruzione. Cio' che salva un claim reale e' che porti per")
        print("     caso un'ALTRA parola sorvegliata, e allora lo ferma un altro")
        print("     strato per un'altra ragione.")
    elif scappati == 0:
        print("     🟢 LA CURA E' ARRIVATA: non scappa piu' nessuno.")
        print("     ⚠️ NON significa «il reperto non esisteva»: significa che la")
        print("     GUARDIA ANTI-ECO e' in servizio (l1_completion_detector.py,")
        print("     30/08, votata 3/3; il suo commento cita QUESTO banco).")
        print("     Verificato alle 17:34: 5/5 scappavano alle 14:00, 0/5 adesso.")
        print("     ⇒ Chi rilegge verifichi QUANDO e DA CHI, non festeggi soltanto.")
    else:
        print("     PREDIZIONE FALSIFICATA: qualcuno resta fermato nonostante")
        print("     l'eco ⇒ il perdono NON e' incondizionato. Leggere QUALE layer")
        print("     lo ferma prima di raccontare un meccanismo: e' l'errore che")
        print("     questa stessa pagina ha gia' fatto una volta.")

    print(f"\n  ⚠️ LIMITI: {tot} claim scritti da me, 2 lingue, un solo sotto-strato.")
    print("     Non e' un tasso sul corpus. E non dice se sia un difetto o il")
    print("     modello di fiducia del prodotto: che il gate DEBBA sospettare del")
    print("     chiamante e' una decisione di design, non una misura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
