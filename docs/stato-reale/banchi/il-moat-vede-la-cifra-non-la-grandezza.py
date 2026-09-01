"""Il moat vede la CIFRA e non la GRANDEZZA; L1 ferma i veri per una parola.

Nasce da un caso vero, non da un'ipotesi: il README dichiara "~7% escape in
Spanish" mentre il 7.1% della sua fonte e' il totale di QUATTRO lingue (W7-111).
Cioe' la cifra giusta con la grandezza sbagliata. Domanda: il nostro prodotto,
alla sua porta, fermerebbe il numero della nostra vetrina?

Fonte unica per tutti i casi, in prosa:

    "The suite finished in 42 seconds on the build machine."

MISURATO IL 02/09/2026 fra le 01:50 e le 02:00, quattro processi, store isolato
ogni volta (HIPPO_DATA_DIR + ENGRAM_DATA_DIR + VERIMEM_DATA_DIR su una tempdir),
gate CE reale, nessun giudice llm:

  claim                                        vero?  status       by    moat    grounding  L4.2
  "The suite finished in 42 seconds."           si    quarantined  L1    passed    94.95    spento
  "The suite completed in 42 seconds."          si    quarantined  L1    passed    92.49    spento
  "The suite finished on the build machine."    si    quarantined  L1    passed    95.69    spento
  "It took the suite 42 seconds to finish."     si    model_claim  -     passed    96.13    spento
  "The suite needs 42 seconds on the machine."  si    model_claim  -     passed    92.60    spento
  "The suite ran 42 test files."                NO    model_claim  -     passed    98.06    ACCESO
  "The suite used 42 megabytes of memory."      NO    model_claim  -     passed    95.73    ACCESO
  "The suite found 42 errors."                  NO    model_claim  -     passed    88.04    ACCESO
  "The suite finished in 4200 seconds."         NO    quarantined  moat  FAILED     0.72    spento

DUE LETTURE, ognuna col suo controllo:

1. L1 ferma la FORMA VERBALE, non la falsita'. Cadono i tre claim VERI che
   portano un completamento in forma finita (finished, completed); passano i due
   VERI che lo evitano (to finish, needs). P1 e P2 hanno grounding 92.49 e 92.60
   - undici centesimi di differenza - e uno cade e l'altro no: la decisione non
   la prende il moat, la prende una parola.

2. Il moat guarda la CIFRA e non l'UNITA'. Cambiare 42 in 4200 lo fa crollare da
   ~95 a 0.72 (controllo positivo: si accende). Cambiare "seconds" in "test
   files", "megabytes" o "errors" lo lascia a 88-98. Le tre falsita' passano.
   L4.2 le vede tutte e tre - ed e' l'unico che le vede - ma e' un AVVISO e non
   blocca: i tre claim falsi sono model_claim, cioe' ammessi.

=> Sui numeri spostati di grandezza la difesa che DECIDE non vede il difetto, e
   quella che lo VEDE non decide. Il numero della nostra vetrina e' di quella
   forma esatta.

NOTA SULLA FORMA DELLA FONTE, misurata prima e necessaria per leggere il resto:
su una fonte TABELLARE (la tabella per lingua di EVIDENCE-stress) L4.2 si accende
anche su un claim che la ricopia alla lettera - 4 casi su 4. In prosa distingue
(spento sui veri, acceso sui tre spostamenti). Le nostre EVIDENCE sono tabelle:
li' l'avviso non porta informazione.

LIMITI: nove claim, una sola fonte, una sola lingua. Il pattern di L1 e' inferito
da 3 cadute contro 2 passaggi, non letto nel codice. Non dice quanto siano
frequenti queste forme nel corpus.

Run:  python -c "exec(open(r'docs/stato-reale/banchi/il-moat-vede-la-cifra-non-la-grandezza.py').read())"
      dalla RADICE del worktree (con python <percorso> importerebbe un altro verimem).
"""
import json
import os
import sys
import tempfile


def apri_store():
    d = tempfile.mkdtemp(prefix="banco_grandezza_")
    for k in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        os.environ[k] = d
    os.environ["VERIMEM_HOSTED"] = "1"
    for m in [k for k in list(sys.modules) if k.startswith("verimem")]:
        del sys.modules[m]
    from verimem.client import Memory
    return Memory(), d


SRC = "The suite finished in 42 seconds on the build machine."

CASI = [
    ("finished in 42 seconds", True, "The suite finished in 42 seconds."),
    ("completed in 42 seconds", True, "The suite completed in 42 seconds."),
    ("finished on the machine", True, "The suite finished on the build machine."),
    ("took 42 seconds to finish", True, "It took the suite 42 seconds to finish."),
    ("needs 42 seconds", True, "The suite needs 42 seconds on the build machine."),
    ("ran 42 test files", False, "The suite ran 42 test files."),
    ("used 42 megabytes", False, "The suite used 42 megabytes of memory."),
    ("found 42 errors", False, "The suite found 42 errors."),
    ("finished in 4200 seconds", False, "The suite finished in 4200 seconds."),
]


def main():
    mem, d = apri_store()
    print(f"  store isolato: {d}\n")
    print(f"  {'claim':28s} {'vero':5s} {'status':12s} {'by':6s} {'moat':8s} {'grounding':>9s}  L4.2")
    ids, righe = set(), []
    for nome, vero, claim in CASI:
        r = mem.add(claim, source=SRC, topic="banco/grandezza")
        fid = r.get("id") or r.get("fact_id")
        ids.add(fid)
        g = r.get("grounding_score")
        l42 = "L4.2" in json.dumps(r, default=str)
        righe.append((nome, vero, r.get("status"), l42))
        print(f"  {nome:28s} {'si' if vero else 'NO':5s} {str(r.get('status')):12s} "
              f"{str(r.get('quarantined_by') or '-'):6s} {str(r.get('moat')):8s} "
              f"{'-' if g is None else round(g, 2):>9}  {'ACCESO' if l42 else 'spento'}")
    if len(ids) != len(CASI):
        print("\n  NON RIUSCITO: id ripetuti, lo store non separa i casi")
        return 1
    veri_fermati = [n for n, v, s, _ in righe if v and s == "quarantined"]
    falsi_passati = [n for n, v, s, _ in righe if not v and s != "quarantined"]
    visti_solo_da_l42 = [n for n, v, s, l in righe if not v and s != "quarantined" and l]
    print(f"\n  VERI fermati:   {len(veri_fermati)}/5  {veri_fermati}")
    print(f"  FALSI passati:  {len(falsi_passati)}/4  {falsi_passati}")
    print(f"  di cui visti dal solo avviso L4.2: {len(visti_solo_da_l42)}")
    if len(veri_fermati) == 0 and len(falsi_passati) == 0:
        print("  ESITO: il gate separa vero e falso su questa fonte - il reperto e' superato")
        return 0
    print("  ESITO: la porta non separa vero da falso su questa fonte")
    return 0


sys.exit(main())
