# -*- coding: utf-8 -*-
r"""Dove finisce la vista di `L4.1`: la frontiera e' TIPOGRAFICA, non linguistica.

    AR interi    CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1
    HI interi    CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1
    KO interi    CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1
    IT decimale  CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1      «tre virgola cinque»
    EN decimale  CIFRA=bloc      ALTRA=AMMESSO  senzaL4.1      «three point five»
    IT mista     CIFRA=bloc      ALTRA=bloc                    «340 mila»
    EN mista     CIFRA=bloc      ALTRA=bloc                    «340 thousand»

    CIFRA  ammessi 0/7   L4.1 ha parlato su 7/7
    ALTRA  ammessi 5/7   L4.1 ha parlato su 2/7

Paga il limite dichiarato in `ws5-la-cifra-si-aggira-scrivendola-a-parole.py`
(«sei casi, interi tondi, niente decimali ne' AR/HI/KO»).

🔑 LE DUE RIGHE CHE VALGONO SONO QUELLE BLOCCATE. «340 mila» ha lo stesso valore,
la stessa lingua e la stessa struttura di «trecentoquarantamila», e viene fermato
CON `L4.1`. L'unica differenza e' che contiene il glifo `340`.
⇒ `L4.1` vede il numero **se e solo se compare almeno un carattere 0-9**. Non e' la
lingua, non e' l'alfabeto, non e' il significato: e' la presenza di un glifo
decimale ASCII. La forma mista e' la prova per contrasto — isola la variabile senza
cambiare nient'altro.

⚖️ E RIBALTA LA LETTURA DEL BANCO PRECEDENTE, che diceva «ideogrammi compresi» e
suonava come «le scritture non latine sono scoperte». FALSO: il cinese con `340箱`
e' bloccato esattamente come l'inglese, e l'inglese con «three hundred forty» passa
esattamente come il cinese con `三百四十`. **La lingua non c'entra: c'entra come
scrivi il numero.** Fermandosi alle quattro scritture si consegnava una diagnosi
che dava la colpa alla lingua sbagliata.

IN QUALE REGIME VALGONO QUESTI NUMERI. La macchina ha dieci variabili che la CI non
ha (`ENGRAM_ADMISSION_GATE=1`, `HIPPO_ENCODE_DELEGATE_ONLY=1`, `PYTHONUTF8=1`,
`ENGRAM_DECAY_ENABLED=1`, `ENGRAM_BRIEFING_*`, `ENGRAM_TELEMETRY_PREFIXES`,
`*_DATA_DIR`, `HIPPO_EXPOSE_TOOLS`). ✅ NESSUNA e' letta da `anti_confab_gate.py`,
che e' la porta chiamata qui — verificato guardando da quale file ognuna e' letta,
non a intuito (`admission_gate.py`, `embedding.py`, `daemon_runner.py`,
`briefing.py`). ✅ E questa e' la porta VERA: `verimem/cli.py:1867`,
`client.py:529` e `mcp_server.py` chiamano tutti `run_validation_gate`.
⇒ Il controllo utile non e' «togli la variabile e rimisura», e' **«da quale file e'
letta, e quel file sta sulla strada del prodotto?»**: due grep, e rispondono al
regime E al livello.

⚠️ LIMITE RESIDUO: dodici casi in tutto fra i due banchi, un valore per forma. Non
provate le frazioni («un terzo»), i numeri romani, ne' le forme parlate («un paio
di centinaia»). ⛔ NESSUNA CURA: riconoscere i numeri a parole in N lingue non e'
una regex, e una cura che non so misurare non si consegna.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-dove-finisce-la-vista-di-L41.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA: scrive in HIPPO_DATA_DIR, mai lo store principale.
"""
import os, sys
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]
from verimem.anti_confab_gate import run_validation_gate

#: (etichetta, fonte, claim-CIFRA, claim-ALTRA-FORMA)
CASI = [
 ("AR interi",   "سجل الشحن: تم تسليم البضاعة إلى مستودع باري.",
                 "تم تسليم 340 طردا إلى مستودع باري.",
                 "تم تسليم ثلاثمائة وأربعين طردا إلى مستودع باري."),
 ("HI interi",   "लॉजिस्टिक्स नोट: माल बारी गोदाम में पहुँचा दिया गया।",
                 "340 पैकेट बारी गोदाम में पहुँचाए गए।",
                 "तीन सौ चालीस पैकेट बारी गोदाम में पहुँचाए गए।"),
 ("KO interi",   "물류 기록: 화물이 바리 창고에 배송되었습니다.",
                 "340개의 화물이 바리 창고에 배송되었습니다.",
                 "삼백사십 개의 화물이 바리 창고에 배송되었습니다."),
 ("IT decimale", "Referto: la temperatura del reattore e' stata registrata.",
                 "La temperatura del reattore era 3.5 gradi.",
                 "La temperatura del reattore era tre virgola cinque gradi."),
 ("EN decimale", "Report: the reactor temperature was recorded.",
                 "The reactor temperature was 3.5 degrees.",
                 "The reactor temperature was three point five degrees."),
 ("IT mista",    "Nota: il magazzino di Ancona ha ricevuto merce.",
                 "Il magazzino di Ancona ha ricevuto 340000 colli.",
                 "Il magazzino di Ancona ha ricevuto 340 mila colli."),
 ("EN mista",    "Note: the Ancona depot received goods.",
                 "The Ancona depot received 340000 parcels.",
                 "The Ancona depot received 340 thousand parcels."),
]

def prova(claim, src):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=src, grounding_llm=None, ground_write=True)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    return (getattr(r, "action", "?") == "persist",
            any(str(w).startswith("L4.1") for w in ws))

amm = {"CIFRA": 0, "ALTRA": 0}; l41 = {"CIFRA": 0, "ALTRA": 0}
print("")
for eti, src, c_cifra, c_altra in CASI:
    out = []
    for k, claim in (("CIFRA", c_cifra), ("ALTRA", c_altra)):
        ok, ha41 = prova(claim, src)
        amm[k] += int(ok); l41[k] += int(ha41)
        out.append("%s=%-8s%s" % (k, "AMMESSO" if ok else "bloc", "" if ha41 else " senzaL4.1"))
    print("   %-12s %s" % (eti, "  ".join(out)))
print("")
n = len(CASI)
for k in ("CIFRA", "ALTRA"):
    print("   %-6s ammessi %d/%d   L4.1 ha parlato su %d/%d" % (k, amm[k], n, l41[k], n))
