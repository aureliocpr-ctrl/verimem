# -*- coding: utf-8 -*-
"""Estende il banco cifra-vs-lettere: decimali, forme miste, AR/HI/KO.

Limite dichiarato nel banco precedente: sei casi, interi tondi (340, 27, 12),
niente decimali a parole, niente forme miste, niente AR/HI/KO. Un limite
dichiarato e' un debito: qui lo pago.
⚠️ Cella di controllo obbligatoria in ogni riga: la forma CIFRA deve bloccare.
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
