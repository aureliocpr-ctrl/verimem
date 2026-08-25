# -*- coding: utf-8 -*-
"""Il thai ammette una falsita' a 99.87. E' LA NEGAZIONE, il THAI, o QUELLA FRASE?

Il banco precedente (ws3-il-giudice-fuori-dall-alfabeto-latino) ha misurato UN
caso: fonte thai «il contratto NON e' stato rinnovato», claim «e' stato
rinnovato», esito `admitted` con grounding_score=99.86940002441406. Con n=1 non
si sa quale delle tre cose sia, e la spiegazione che mi ero data — «in thai non
ci sono spazi fra le parole, il tokenizer inglese frammenta il negatore» — ha
gia' un CONTROESEMPIO IN CASA: **il giapponese non separa le parole con spazi e
regge** (falso semantico fermato a g=1.0 nello stesso banco). ⇒ La mia ipotesi
e' gia' incrinata prima di questo file, e va falsificata sul serio.

═══ I QUATTRO ASSI, ciascuno tiene fermo tutto tranne una cosa ═══
  TH-neg-2   seconda fonte thai, stessa STRUTTURA (negazione ribaltata),
             contenuto diverso  -> se passa anche questa, non e' «quella frase»
  TH-neg-inv fonte thai POSITIVA, claim che NEGA -> se passa, il guasto e'
             simmetrico; se cade, il gate vede la negazione in un verso solo
  TH-nonneg  falsita' thai che NON e' una negazione (entita' sostituita:
             magazzino nord -> magazzino sud) -> se la ferma, il difetto e'
             SPECIFICO della negazione; se passa, e' il thai in generale
  JA-neg-2   la STESSA struttura di TH-neg-2 in giapponese -> controllo: il
             giapponese deve continuare a reggere, altrimenti il banco e' rotto

⚖️ Ogni fonte porta anche il suo VERO. Senza l'altra popolazione, un gate che
rifiutasse tutto sembrerebbe perfetto su questa tabella.

⚠️ LIMITE, dichiarato prima dei numeri: le rese thai e giapponesi sono mie e non
riviste da parlanti. Il VERO di ciascuna fonte e' il presidio contro «la frase e'
sgrammaticata»: se il vero e' ammesso, la frase e' comprensibile al giudice.

═══ MISURATO — DUE MIE DIAGNOSI CADUTE IN VENTI MINUTI ═══

    asse                  caso            atteso        esito         g     layer
    TH-neg-2              falso NEG       quarantined   quarantined   4.90  L4-grounding
    TH-neg-inv            falso NEG-inv   quarantined   quarantined   1.50  L4-grounding+L4-negazione
    TH-nonneg             falso ENTITA    quarantined   ADMITTED         -  -          <<<
    JA-neg-2 (controllo)  falso NEG       quarantined   quarantined   0.80  L4-grounding
    (i VERI delle quattro fonti: ammessi 4/4 — le frasi arrivano al giudice)

① «E' IL NEGATORE CHE NON VEDE» — FALSA, ed e' il ROVESCIO del vero. La
   negazione thai viene PRESA: due casi su due, e su `TH-neg-inv` scatta perfino
   il layer `L4-negazione`. Quello che passa e' la SOSTITUZIONE DI ENTITA':
   คลังสินค้าทางเหนือ (magazzino nord) -> ทางใต้ (sud), stesso numero, ammesso.

② «E' LA FONTE MULTI-FRASE: il CE si ancora alla porzione identica» — l'avevo
   formulata perche' il caso originale a 99.87 aveva una fonte di DUE frasi
   mentre TH-neg-2 ne ha una. Test diretto, tre esecuzioni::

     A  fonte una frase                        quarantined  g=4.9
     B  STESSA fonte + una frase di contorno   quarantined  g=4.4   <- predetto: passa
     C  controllo, claim = il contorno stesso  admitted             <- il banco funziona

   Il contorno sposta g di mezzo punto e NON ribalta il verdetto. Falsa anche questa.

═══ QUELLO CHE RESTA, ed e' meno elegante e piu' onesto ═══
DUE fatti misurati e riproducibili, e NESSUNA spiegazione che regga:
  · esiste un caso thai con negazione ammesso a grounding 99.87
    (banco ws3-il-giudice-fuori-dall-alfabeto-latino);
  · esiste un caso thai con entita' sostituita ammesso (questo banco);
  · e altri tre casi thai con negazione, di struttura IDENTICA al primo, FERMATI.
Il primo e TH-neg-2 hanno la stessa forma («X ไม่ได้รับการ<verbo>» -> «X ได้รับการ
<verbo>แล้ว») e cambiano solo il verbo: ต่ออายุ (rinnovare) contro อนุมัติ
(approvare). ⇒ L'unica differenza superstite e' LESSICALE, ma con due casi non e'
una tesi: e' l'ultima cosa rimasta in piedi dopo che ne sono cadute due.

🔑 Lo consegno cosi' perche' una diagnosi elegante e sbagliata avrebbe mandato
qualcuno a curare il negatore — che funziona. Il fatto che serve alla decisione
e' il primo: il gate ammette una falsita' con 99.87 in una scrittura, e non
sappiamo dire quando. Una promessa non si limita a «tranne il thai»: si limita
alle scritture MISURATE.

⛔ NON MISURATO, e non lo indovino: se il discrimine sia il verbo, il vocabolario
del tokenizer, o altro. Serve una batteria di coppie thai che varino UNA parola
per volta, ed e' un fronte, non una riga.

Regime: porta pubblica `verimem remember --source`, store temporaneo vuoto,
FUORI pytest. PYTHONUTF8=1 per la STAMPA, non per il gate.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_thaineg_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (asse, fonte, [(nome_caso, claim, atteso)])
CASI = [
    ("TH-neg-2",
     "บันทึกการประชุม: คำขอเบิกจ่ายของแผนกขายไม่ได้รับการอนุมัติ",
     [("VERO", "คำขอเบิกจ่ายของแผนกขายไม่ได้รับการอนุมัติ", "admitted"),
      ("falso NEG", "คำขอเบิกจ่ายของแผนกขายได้รับการอนุมัติแล้ว", "quarantined")]),

    ("TH-neg-inv",
     "บันทึก: คลังสินค้าทางเหนือถูกขายให้กับคุณสมชายเมื่อเดือนมีนาคม",
     [("VERO", "คลังสินค้าทางเหนือถูกขายให้กับคุณสมชาย", "admitted"),
      ("falso NEG-inv", "คลังสินค้าทางเหนือไม่ได้ถูกขายให้กับคุณสมชาย", "quarantined")]),

    ("TH-nonneg",
     "รายงาน: คลังสินค้าทางเหนือมีพื้นที่ 1800 ตารางเมตร",
     [("VERO", "คลังสินค้าทางเหนือมีพื้นที่ 1800 ตารางเมตร", "admitted"),
      ("falso ENTITA", "คลังสินค้าทางใต้มีพื้นที่ 1800 ตารางเมตร", "quarantined")]),

    ("JA-neg-2 (controllo)",
     "議事録：営業部の支出申請は承認されませんでした。",
     [("VERO", "営業部の支出申請は承認されませんでした。", "admitted"),
      ("falso NEG", "営業部の支出申請は承認されました。", "quarantined")]),
]

_L = re.compile(r"\b(L1(?:\.\d+)?|L3[\w-]*|L4(?:\.\d+)?[\w-]*|store-screen)\b")


def esegui(claim: str, source: str):
    buf = io.StringIO()
    sys.argv = ["verimem", "remember", claim, "--source", source]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            main()
    except SystemExit:
        pass
    except Exception as e:                                    # noqa: BLE001
        return "ECCEZIONE", None, type(e).__name__
    o = buf.getvalue()
    esito = ("admitted" if re.search(r"\badmitted\b", o)
             else "quarantined" if re.search(r"\bquarantined\b", o) else "?")
    m = re.search(r"grounding[_ ]score=([\d.]+)", o) or re.search(r"grounding ([\d.]+)", o)
    return esito, (float(m.group(1)) if m else None), ("+".join(sorted(set(_L.findall(o)))) or "-")


def main_banco() -> None:
    print("%-22s %-14s %-12s %-12s %8s  %s"
          % ("asse", "caso", "atteso", "esito", "g", "layer"))
    esiti = {}
    for asse, src, casi in CASI:
        for nome, claim, atteso in casi:
            e, g, layer = esegui(claim, src)
            giusto = (e == atteso)
            if nome != "VERO":
                esiti[asse] = giusto
            print("%-22s %-14s %-12s %-12s %8s  %-22s %s"
                  % (asse, nome, atteso, e, ("%.2f" % g) if g is not None else "-",
                     layer, "" if giusto else "<<< SBAGLIATO"))
        print()
    print("=" * 84)
    for asse, ok in esiti.items():
        print("  %-24s falsita' FERMATA: %s" % (asse, "si" if ok else "NO"))
    print()
    print("  Come si legge:")
    print("   TH-neg-2 NO   -> non e' «quella frase»: la negazione thai cade anche altrove")
    print("   TH-nonneg si  -> il difetto e' SPECIFICO della negazione, non del thai")
    print("   TH-nonneg NO  -> e' il thai in generale, e la mia diagnosi era troppo stretta")
    print("   JA-neg-2 NO   -> il banco e' rotto o il giapponese non regge come credevo")


if __name__ == "__main__":
    main_banco()
