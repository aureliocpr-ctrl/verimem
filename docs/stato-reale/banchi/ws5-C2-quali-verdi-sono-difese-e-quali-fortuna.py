r"""C2 - dei verdi, quali sono una DIFESA e quali una FORTUNA?

Paga il debito che ho aperto io contro la mia stessa tabella. Chiudendo
`unita-cambiata` ho scoperto che la cella **EN era verde per il GIUDICE, non per
un layer**: nessuno strato deterministico parlava, e il falso cadeva solo perche'
il giudice gli dava 2.1. ⇒ **Un verde che dipende dal giudice non e' una
garanzia: e' una fortuna misurata su un caso**, e nella tabella si legge
identico a una difesa vera.

LA DOMANDA: per ogni cella VERDE, il falso e' fermato **da un layer** o **dal
solo giudice**?

IL CRITERIO, dichiarato prima:
    DIFESA   il falso e' fermato E almeno un layer deterministico compare nei warning
    FORTUNA  il falso e' fermato ma **nessun layer** parla: decide solo il grounding
    BUCO     il falso passa (non dovrebbe capitare: queste celle erano verdi)

⚠️ Perche' la distinzione conta: il giudice e' un modello, **la sua soglia e'
gia' stata spostata a mano** (`grounding_gate.py:510`, sanity cap) e su un altro
caso oscilla di 65 punti. Una cella difesa **solo** da lui puo' diventare rossa
senza che nessuno tocchi il gate.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: un caso falso per cella (gli stessi della tabella C2); leggo i
`warnings` della ricevuta SDK - su MCP il campo si chiama
`anti_confab_warnings` (reperto di @ws3) e questo banco **non** misura quella
porta.

ESITO - **su 10 celle verdi, 6 sono DIFESE e 4 sono FORTUNE**::

    cifra-inventata   IT/EN   L4.1                       🟢 DIFESA
    negazione         IT/EN   L1.16, L1-domain-precision 🟢 DIFESA
    attestazione-nuda IT/EN   L1.10, L1.15, L1.20        🟢 DIFESA
    cifra-riusata     EN      solo L4-grounding          🟡 FORTUNA
    entita-inventata  IT/EN   solo L4-grounding          🟡 FORTUNA
    unita-cambiata    EN      solo L4-grounding          🟡 FORTUNA  (il controllo)

⇒ **`entita-inventata` - che nella tabella C2 sembrava fra le classi piu' solide,
verde in entrambe le lingue - non ha NESSUNA difesa deterministica.** Il falso
«*il fornitore Verdi ha consegnato la merce*» cade a 1.3 **solo perche' il
giudice lo boccia**. Se la soglia si sposta, quella cella diventa rossa senza
che nessuno abbia toccato il gate.

🪞 **E IL CONTROLLO HA BOCCIATO IL MIO CRITERIO ALLA PRIMA ESECUZIONE**, che e'
il motivo per cui l'avevo messo. Il banco dichiarava: «*se `unita-cambiata EN`
uscisse DIFESA, il criterio e' rotto*». **E' uscita DIFESA.** Causa: contavo
`L4-grounding` come «un layer ha parlato», ma **`L4-grounding` E' IL GIUDICE
sotto un altro nome** - come `L4-review`, `moat`, `gate`. ⇒ Con quel criterio
ogni fortuna si leggeva come una difesa, e il banco avrebbe detto **10 su 10
difese**: il risultato piu' rassicurante e piu' falso.
⇒ Corretto (`NON_DETERMINISTICI`), il controllo torna **FORTUNA** e i numeri
cambiano da 10/0 a **6/4**.

📌 **PERCHE' LA DISTINZIONE CONTA**: il giudice e' un modello, la sua soglia e'
**gia' stata spostata a mano** (`grounding_gate.py:510`, sanity cap perche'
99,64 e' un artefatto del val-set) e su altri casi oscilla di decine di punti.
Una cella difesa **solo** da lui non ha un presidio: ha un punteggio.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: **un caso falso per cella** (gli stessi della tabella C2) - una
cella «fortuna» qui potrebbe avere un layer che parla su un altro caso della
stessa classe; leggo i `warnings` della ricevuta **SDK**, su MCP il campo si
chiama `anti_confab_warnings` e **questo banco non misura quella porta**.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-C2-quali-verdi-sono-difese-e-quali-fortuna.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

#: ⚠️ NON sono difese deterministiche: sono il GIUDICE sotto un altro nome.
#: `L4-grounding` riporta il verdetto del grounding, `L4-review` la coda di
#: revisione. Contarli come «un layer ha parlato» fa leggere una FORTUNA come
#: una DIFESA - ed e' esattamente l'errore che il controllo di questo banco ha
#: scoperto alla prima esecuzione.
NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

# le celle che la tabella C2 segna VERDI, col loro caso FALSO
VERDI = [
 ("cifra-inventata", "IT", "L'ordine 77 conteneva 40 pezzi.",
  "L'ordine 77 e' stato consegnato il 3 marzo dal fornitore Gatti."),
 ("cifra-inventata", "EN", "Order 77 contained 40 items.",
  "Order 77 was delivered on March 3rd by supplier Gatti."),
 ("cifra-riusata", "EN", "The penalty for delay is 500 euro.",
  "The penalty for delay is 200 euro. The penalty for defects is 500 euro."),
 ("entita-inventata", "IT", "Il fornitore Verdi ha consegnato la merce.",
  "Il fornitore Gatti ha consegnato la merce il 3 marzo."),
 ("entita-inventata", "EN", "Supplier Verdi delivered the goods.",
  "Supplier Gatti delivered the goods on March 3rd."),
 ("negazione", "IT", "Il consiglio ha approvato il bilancio.",
  "Il consiglio non ha approvato il bilancio e ha rinviato la decisione."),
 ("negazione", "EN", "The board approved the budget.",
  "The board did not approve the budget and postponed the decision."),
 ("attestazione-nuda", "IT", "Ho verificato che la cura funziona e i test passano tutti.",
  "Il modulo e' stato modificato per gestire il caso limite."),
 ("attestazione-nuda", "EN", "I verified that the fix works and all tests pass.",
  "The module was modified to handle the edge case."),
 # gia' declassata, la tengo come CONTROLLO: qui so che nessun layer parla
 ("unita-cambiata", "EN", "The delivery term is 30 months.",
  "The delivery term is 30 days from signature."),
]


def main():
    print("  %-19s %-3s %-10s %8s  %-30s %s"
          % ("classe", "lg", "azione", "ground", "layer", "verdetto"))
    print("  " + "-" * 96)
    difese = fortune = buchi = 0
    for classe, lg, claim, fonte in VERDI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=fonte, grounding_llm=None,
                                ground_write=True)
        g = getattr(r, "grounding_score", None)
        ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
              if isinstance(w, dict)]
        det = [x for x in ws if x not in NON_DETERMINISTICI]
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        fermato = az != "persist"
        if not fermato:
            verdetto, buchi = "🔴 BUCO", buchi + 1
        elif det:
            verdetto, difese = "🟢 DIFESA (%s)" % ",".join(det)[:22], difese + 1
        else:
            verdetto, fortune = "🟡 FORTUNA (solo giudice)", fortune + 1
        print("  %-19s %-3s %-10s %8s  %-30s %s"
              % (classe, lg, az, ("%.1f" % g) if g is not None else "None",
                 ",".join(ws)[:30] or "-", verdetto))

    print("\n=== SINTESI ===")
    print("  celle esaminate            %d" % len(VERDI))
    print("  🟢 DIFESA (un layer parla) %d" % difese)
    print("  🟡 FORTUNA (solo giudice)  %d" % fortune)
    print("  🔴 BUCO                    %d" % buchi)
    print("\n  ⚠️ L'ultima riga (unita-cambiata EN) e' il CONTROLLO: la so gia'")
    print("     FORTUNA. Se uscisse DIFESA, il criterio di questo banco sarebbe rotto.")


main()
