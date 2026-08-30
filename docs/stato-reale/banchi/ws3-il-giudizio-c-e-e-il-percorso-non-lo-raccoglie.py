"""Il giudizio C'E' — 0.56 dal daemon — e il percorso di `add()` non lo raccoglie.

IL FENOMENO, gia' riportato in `ws3-le-due-porte-separano-gli-stessi-tre-stati`
blocco [B] e qui ISOLATO. Regime: **modello locale assente** (cartella vuota in
`ENGRAM_LOCAL_GATE_MODEL`), **daemon di encoding VIVO**,
`HIPPO_ENCODE_DELEGATE_ONLY=1`::

    porta  status        gs      cosa succede al claim
    sdk    model_claim   null    AMMESSO — e la sua fonte lo NEGA
    mcp    quarantined   0.56    fermato

⚠️ Il fail-open dell'SDK senza modello locale **e' dichiarato** (`README:64`).
Questo banco non contesta quello: contesta che sia **inevitabile**, perche' nello
stesso identico regime **il giudizio e' ottenibile** e qualcuno lo ottiene.

═══════════════════════════════════════════════════════════════════════════════
🔑 IL FATTO CHE DECIDE — isolamento in un processo fresco, stesso regime::

    try_local_score(fonte, claim)          ->  0.56      ← la delega FUNZIONA
    Memory().add(claim, source=fonte)      ->  gs=None   ← il percorso la perde

**Il giudice non c'e' in locale, ma il daemon risponde 0.56.** La via esiste,
e la porta piu' usata non la percorre.
═══════════════════════════════════════════════════════════════════════════════

QUATTRO CAUSE ESCLUSE, ognuna con la sua misura — le elenco perche' **il valore
di questo banco e' tanto in cio' che ha escluso quanto in cio' che ha trovato**:

    ① l'ORDINE delle due porte      invertito A/B: MCP giudica sia per primo
                                    sia per secondo, l'SDK MAI ⇒ non e' l'ordine
    ② `_load_failed`                resta **False** prima e dopo, in entrambi i
                                    percorsi ⇒ non e' la condizione
                                    `not judge._load_failed` a spegnere la delega
    ③ il ramo del backend           `_resolve_backend()` -> `claude` e il ramo
                                    che chiama `try_local_score` e' **True** in
                                    ENTRAMBI i regimi (modello presente e
                                    assente) ⇒ la funzione VIENE chiamata
    ④ il `focus_budget`             `try_local_score` da' **0.56** con e senza
                                    `focus_budget=1500` ⇒ non e' l'argomento in
                                    piu' che il gate passa

🔑 **LOCALIZZATA — 30/08 16:26.** Il valore tracciato in TRE punti dello stesso
processo, stesso regime::

    try_local_score(fonte, claim)          0.56
    fact_grounding_score_ex(None, f, c)    [0.56, 'local']   <- IL GATE RACCOGLIE
    Memory().add(...)                      gs=None           <- si perde QUI

*(la prima chiamata alla porta pubblica era fallita per **firma** — `llm` e' il
PRIMO posizionale, non un keyword: letta la firma invece di indovinarla.)*

⇒ La perdita e' **fra il gate e la ricevuta**, e sta in una riga sola:
`anti_confab_gate.py:2336-2338`::

    _have_judge = (grounding_llm is not None
                   or _resolve_backend() == "local"
                   or local_ce_available())
    ...
    if source and _ground_on and _have_judge:
        gscore, _judge_used = fact_grounding_score_ex(...)

Nel regime misurato: `grounding_llm` e' `None` · `_resolve_backend()` da'
`claude` (non `local`) · **`local_ce_available()` da' `False`** perche' il
modello non e' su disco. ⇒ **`_have_judge` e' falso e il gate non viene MAI
chiamato** — mentre il gate, chiamato, risponde **0.56**.

🔑 **`local_ce_available()` risponde a «il modello e' su disco?» e viene usata
per rispondere a «c'e' un giudice?».** Sono domande diverse: **il daemon e' un
giudice senza modello su disco.** Il commento accanto elenca le vie —
«*an llm was injected, the backend is explicitly 'local', OR no llm but the
multilingual local CE is on disk*» — e **il daemon non e' nell'elenco**.
⇒ E' la stessa classe che ho pagato oggi sul mio `come_fonte`: *un elenco che
non conosce il caso aggiunto dopo*. Li' erano «le due potature» e ne avevo messa
una terza fuori; qui sono tre vie al giudizio e la quarta non e' nominata.

📌 **PROPOSTA, e non l'applico**: la guardia decide **prima di provare**, su un
proxy (il modello su disco) che non copre tutte le vie. La cura naturale e'
**provare e decidere sul risultato** — il gate sa gia' dire di non poter
giudicare (`NoGroundingJudge`), e `try_local_score` torna `None`.
⚠️ **Non e' banale e va detto**: `judge_state()` da' `absent` col modello assente
e diventa `delegated` **solo dopo** una delega riuscita — quindi **la
disponibilita' del daemon non e' nota prima di provarci**, ed e' proprio per
questo che un pre-check non puo' saperla.
⛔ `anti_confab_gate.py` e' il cuore del prodotto e quella condizione tocca OGNI
scrittura: **misuro, localizzo, propongo. La decisione e' di chi mantiene il
layer.**

⚠️ COSA QUESTO BANCO NON DICE:
  · **non dice che sia un difetto**: potrebbe esserci una ragione deliberata per
    cui la scrittura non usa la delega quando il modello locale manca, e non
    l'ho trovata scritta da nessuna parte — *ma «non l'ho trovata» non e' «non
    esiste»*.
  · **QUANTO E' LARGO — misurato il 30/08 16:25, e la risposta e' precisa.**
    `_have_judge` non guarda il claim, quindi la predizione era «totale». Tre
    cause diverse nello stesso regime::

        fonte che NEGA        model_claim   gs=None   L4-skipped
        irrilevante           model_claim   gs=None   L4-skipped
        self-claim con fonte  quarantined   gs=None   L1.10,L1.15,L1.20,L4-skipped

    ⇒ **Il MOAT non gira mai: 3/3 con `gs=None` e `L4-skipped`.** Ma la famiglia
    **`L1` continua a girare** e ferma cio' che sa fermare lessicalmente. 🔑 La
    formulazione giusta non e' «il buco e' totale», e': **in quel regime resta
    solo la difesa lessicale, e passa cio' che SOLO il moat poteva fermare** —
    una fonte che nega, un irrilevante. *La difesa in profondita' regge la parte
    che le compete.*
  · **IL REGIME E' ARTIFICIALE NEL MODO IN CUI L'HO COSTRUITO, e va detto.**
    `ENGRAM_LOCAL_GATE_MODEL` cambia la vista del **processo**; il daemon ha il
    **suo** modello ed e' per questo che risponde 0.56. Un utente che non ha mai
    installato il modello non avrebbe nemmeno il daemon caldo. ⇒ **Il buco e'
    reale nel codice**, e i regimi che lo raggiungono sono di **configurazione**:
    env puntata al posto sbagliato · modello spostato o cancellato con il daemon
    ancora vivo · due percorsi d'installazione (default contro legacy).
    🟢 **E `doctor` lo diagnostica**: sul modello assente risponde `status='fail'`
    col path e con entrambe le conseguenze (misurato nello stesso giro). **La
    mitigazione esiste ed e' quella giusta.**
  · **dipende da un daemon VIVO**: senza, non c'e' niente da raccogliere e
    l'asimmetria sparisce. **E' una proprieta' della macchina, non del codice.**
  · **il caso quarantinato normale NON e' toccato**: con il modello presente le
    due porte coincidono 3/3, sotto-strati compresi (blocco [C] dell'altro
    banco). L'asimmetria e' **stretta e localizzata a questo regime**.

REGIME: un processo per cella, store TEMPORANEO, `Memory()` senza path
esplicito, giudice locale reso assente puntando `ENGRAM_LOCAL_GATE_MODEL` a una
cartella vuota — **nessun download**, ⛔ nessun `warmup`. Store di Aurelio
intatto.

    python docs/stato-reale/banchi/ws3-il-giudizio-c-e-e-il-percorso-non-lo-raccoglie.py
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
os.environ["HIPPO_ENCODE_DELEGATE_ONLY"] = "1"
if sys.argv[1] == "assente":
    os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()   # cartella VUOTA
claim, fonte, come = sys.argv[2], sys.argv[3], sys.argv[4]
from verimem.local_grounding import get_local_judge
j = get_local_judge()
out = {"load_failed_prima": bool(getattr(j, "_load_failed", False))}
if come == "diretta":
    from verimem.local_grounding import try_local_score
    r = try_local_score(fonte, claim)
    out["valore"] = None if r is None else round(float(r[0]), 2)
else:
    from verimem.client import Memory
    rec = Memory().add(claim, topic="giunt/x", source=fonte, validate="full")
    gs = rec.get("grounding_score")
    out["valore"] = None if gs is None else round(float(gs), 2)
    out["status"] = rec.get("status")
out["load_failed_dopo"] = bool(getattr(get_local_judge(), "_load_failed", False))
print(json.dumps(out, default=str))
'''


def _cella(giudice: str, come: str) -> dict:
    p = subprocess.run([sys.executable, "-c", FIGLIO, giudice, CLAIM, FONTE, come],
                       capture_output=True, text=True, timeout=1800)
    if p.returncode != 0:
        raise RuntimeError(f"processo morto exit={p.returncode}: "
                           f"{p.stderr.strip()[-120:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def main() -> int:
    print("  REGIME: modello locale ASSENTE · daemon VIVO · DELEGATE_ONLY=1\n")

    print("  [1] CONTROLLO — col modello PRESENTE `add()` deve giudicare")
    ctrl = _cella("presente", "via-add")
    print(f"      add() con modello presente: valore={ctrl['valore']} "
          f"status={ctrl.get('status')}")
    if ctrl["valore"] is None:
        print("      CONTROLLO CADUTO: `add()` non giudica nemmeno col modello")
        print("      presente ⇒ misuro un moat spento, non la giuntura.")
        print("      NESSUN VERDETTO.")
        return 1

    print("\n  [2] L'ISOLAMENTO — modello ASSENTE, due vie allo stesso giudizio")
    diretta = _cella("assente", "diretta")
    via_add = _cella("assente", "via-add")
    print(f"      try_local_score(fonte, claim) ....... {diretta['valore']}")
    print(f"      Memory().add(claim, source=fonte) ... {via_add['valore']}  "
          f"(status={via_add.get('status')})")
    print(f"      `_load_failed` diretta: {diretta['load_failed_prima']} -> "
          f"{diretta['load_failed_dopo']}   ·   via add: "
          f"{via_add['load_failed_prima']} -> {via_add['load_failed_dopo']}")

    print("\n  ══ VERDETTO ══")
    if diretta["valore"] is not None and via_add["valore"] is None:
        print("     🔴 IL GIUDIZIO C'E' E IL PERCORSO NON LO RACCOGLIE.")
        print(f"     Il daemon risponde {diretta['valore']} senza modello locale, e la")
        print("     scrittura ammette il claim come non giudicato — un claim che")
        print("     la sua fonte NEGA. Il fail-open e' dichiarato; che sia")
        print("     INEVITABILE in questo regime, no.")
        print("     ⚠️ Quattro cause escluse (ordine · `_load_failed` · ramo del")
        print("     backend · `focus_budget`), e la causa NON e' localizzata:")
        print("     e' scritto nel docstring invece che indovinato.")
    elif diretta["valore"] is None:
        print("     La delega non funziona nemmeno diretta ⇒ il fenomeno e' un")
        print("     altro, e la lettura del blocco [B] va rivista.")
    else:
        print("     🟢 `add()` raccoglie il giudizio: la giuntura non c'e' (piu').")
        print("     Se questo banco diventa verde, la cura e' arrivata: va")
        print("     verificato QUANDO e da chi, non solo festeggiato.")

    print("\n  ⚠️ LIMITI: un claim, una fonte, italiano. Dipende da un daemon")
    print("     VIVO — senza, non c'e' niente da raccogliere. Col modello")
    print("     PRESENTE le due porte coincidono 3/3: l'asimmetria e' stretta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
