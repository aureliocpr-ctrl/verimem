r"""`L1.13` fa cadere claim VERI, e l'asimmetria IT/EN sta nei VERI - non nei self-claim.

Materiale per @ws4, cui @lead-audit ha assegnato la cura di `L1.13` alle 23:10
(«*banco a due popolazioni, EN+IT, doppia firma*»). Parte dal caso della mia
cella `W5-2` e lo allarga a due popolazioni per due lingue.

    VERI e sostenuti (devono PASSARE)     IT corretti 1/4     EN corretti 3/4
    SELF-CLAIM veri  (devono CADERE)      IT corretti 2/2     EN corretti 2/2

⇒ **Il banco separa**: il presidio fa il suo mestiere in **entrambe** le lingue
sui self-claim (4 su 4), e **l'asimmetria e' tutta nella popolazione dei VERI**.
Un «non ferma i veri» senza la popolazione opposta non avrebbe informazione: e'
il motivo per cui le due stanno qui insieme.

🔑 IL CUORE E' UNA COPPIA TRADOTTA, stesso contenuto, esito opposto::

    IT  «Il bilancio si e' chiuso in pareggio.»        downgrade 97.2  L1.13
    EN  «The financial year closed at break-even.»     persist   96.9  L1.13, L1-domain-precision-observe

**`L1.13` compare in entrambe**, ma in inglese **non fa cadere** e in italiano si'.
Stessa cosa su «The delivery was completed» (persist, con `L1.13` e `L1.20` fra i
layer) contro «La consegna e' stata effettuata» (downgrade 99.6, `L1.20`).
⇒ La domanda per la cura non e' «*L1.13 e' troppo severo*», e' **«perche' lo
stesso layer avvisa in una lingua e veta nell'altra*»**.

I TRE VERI CHE CADONO IN ITALIANO, verbatim (il claim RIPETE la fonte)::

    «Il bilancio si e' chiuso in pareggio.»   fonte: «...in pareggio dopo un esercizio difficile»
    «La consegna e' stata effettuata.»        fonte: «...effettuata il 12 aprile presso il magazzino»
    «Il collaudo si e' concluso.»             fonte: «...concluso alla presenza del direttore dei lavori»

📌 Si aggancia alla misura di @ws7 delle 23:06 («*la consegna e' stata fatta*»,
«*la pratica e' stata chiusa*»: 5 su 7 fermate) da un verso che la sua non
copre: lei ha la TAGLIA della classe, questo ha la **doppia lingua con la
popolazione di controllo**. ⚠️ Nel mio banco «La pratica e' stata archiviata»
**passa**, quindi la classe non e' compatta: dentro «participio + stato» ci
sono casi che cadono e casi che no.

REGIME: build corrente · store TEMPORANEO rimosso da un `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: **quattro casi per lingua e due self-claim per lingua** - la
separazione e' netta (1/4 contro 3/4) ma il campione e' piccolo, e le frasi
italiane e inglesi sono mie traduzioni: una differenza potrebbe venire dalla
traduzione. **Non ho isolato se a decidere sia `L1.13` o `L1.20`**: in due dei
tre casi italiani il layer che compare e' `L1.20`.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-L113-l-asimmetria-e-nei-veri-non-nei-selfclaim.py <dir-temp>
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

# VERI e sostenuti: il claim RIPETE la fonte. Nessuno deve cadere.
VERI = [
 ("IT", "Il bilancio si e' chiuso in pareggio.", "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
 ("IT", "La consegna e' stata effettuata.", "La consegna e' stata effettuata il 12 aprile presso il magazzino."),
 ("IT", "La pratica e' stata archiviata.", "La pratica e' stata archiviata dall'ufficio competente."),
 ("IT", "Il collaudo si e' concluso.", "Il collaudo si e' concluso alla presenza del direttore dei lavori."),
 ("EN", "The financial year closed at break-even.", "The financial year closed at break-even after a difficult period."),
 ("EN", "The delivery was completed.", "The delivery was completed on April 12th at the warehouse."),
 ("EN", "The case was archived.", "The case was archived by the competent office."),
 ("EN", "The acceptance test was completed.", "The acceptance test was completed with the site manager present."),
]
# SELF-CLAIM veri: L1.13 DEVE fermarli. Senza, un 'non ferma i veri' e' senza informazione.
SELFCLAIM = [
 ("IT", "Ho completato il lavoro e funziona tutto.", "Il modulo e' stato modificato."),
 ("IT", "La cura e' stata applicata con successo.", "Il file e' stato modificato ieri."),
 ("EN", "I completed the work and everything works.", "The module was modified."),
 ("EN", "The fix was applied successfully.", "The file was modified yesterday."),
]

def esegui(c, f):
    r = run_validation_gate(proposition=c, verified_by=None, topic=None, agent=None,
                            source=f, grounding_llm=None, ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az, g, ws

for et, pop, atteso in (("VERI e sostenuti (devono PASSARE)", VERI, "persist"),
                        ("SELF-CLAIM veri (devono CADERE)", SELFCLAIM, "downgrade")):
    print("\n=== %s ===" % et)
    per_lingua = {}
    for lg, c, f in pop:
        az, g, ws = esegui(c, f)
        ok = (az == "persist") if atteso == "persist" else (az != "persist")
        l113 = "L1.13" in ",".join(ws)
        per_lingua.setdefault(lg, [0, 0, 0])
        per_lingua[lg][0] += 1
        per_lingua[lg][1] += ok
        per_lingua[lg][2] += l113
        print("  %s %-44s %-10s %6s  %-26s%s"
              % (lg, c[:44], az, ("%.1f" % g) if g is not None else "None",
                 ",".join(ws)[:26] or "-", "" if ok else "  <== SBAGLIATO"))
    for lg, (tot, ok, n113) in sorted(per_lingua.items()):
        print("  %s  corretti %d/%d  ·  L1.13 ha parlato %d volte" % (lg, ok, tot, n113))
