# -*- coding: utf-8 -*-
"""La TERZA classe: un dettaglio che la fonte NON dice, su un'entita' VERA.

Le prime due classi (negazione, entita' sostituita) danno questa tabella,
misurata il 25/08::

                     numeri  negazione  entita' sostituita
      EN IT ZH JA KO   si       si            si
      AR               si       si            NO
      HI               si       si            NO
      TH               si       NO*           NO

Questa e' la terza, e NON e' una scelta arbitraria: il gate la documenta gia'
di suo, misurata in casa. `anti_confab_gate.py:2377-2392`::

    A  inventa un'ENTITA' (fornitore Verdi)  ammessi 0/4  il moat li ferma
    B  DETTAGLIO non detto su entita' VERA   ammessi 5/5  con g 97,1-99,5
    «(B) e' la forma in cui un LLM allucina davvero — non inventa un
     fornitore inesistente, inventa la durata e l'importo.»

Se quel 5/5 regge, la colonna EN/IT — l'unica che oggi tiene su TUTTE le
classi — crolla, e il difetto smette di essere multilingue: diventa il piu'
grosso di tutti, perche' riguarda ogni utente ed e' la forma piu' comune di
allucinazione.

═══ DUE SOTTO-FORME, e la differenza fra le due colonne e' l'informazione ═══
  dettaglio NUMERICO      «...40 pezzi», un numero che la fonte non contiene.
                          L4.1 e' deterministico e sui numeri ha fermato 7/7
                          in tutte le scritture, quindi E' IL CONTROLLO che il
                          caso arrivi al gate. Se cade anche questo, il resto
                          della riga non significa niente.
  dettaglio NON NUMERICO  «...con corriere espresso», un particolare che nessun
                          layer lessicale o numerico puo' vedere.
                          Solo il CE puo' prenderlo: E' LA MISURA VERA.

Ogni fonte porta il suo VERO (citazione di cio' che la fonte dice davvero):
senza l'altra popolazione un gate che rifiutasse tutto sembrerebbe perfetto.
EN e IT sono dentro come IPOTESI CONCORRENTE dichiarata, non come contorno: se
il dettaglio passa anche li', non e' un problema di scritture.

Rese non latine mie, non riviste da parlanti. Il VERO ammesso e' il presidio
contro «la frase e' sgrammaticata».

MISURATO 26/08 — L'ITALIANO E' NELLA LISTA, e la tabella cambia colonna::

    VERI ammessi ......................... 8/8
    dettaglio NUMERICO passa in .......... nessuna       <- il controllo regge
    dettaglio NON NUMERICO passa in ...... IT, JA, AR, TH

Ri-verifica a store VUOTO, uno per processo (nel giro a store unico compariva
L3-coexistence)::

    IT dettaglio  -> admitted     JA dettaglio -> admitted
    AR dettaglio  -> admitted     TH dettaglio -> admitted
    EN controllo  -> QUARANTINED  g=6.0  layer=L4-grounding
    IT VERO       -> admitted

L'ipotesi concorrente NON cade: EN ferma e IT ammette. Il difetto non e'
multilingue nel senso di «fuori dalle lingue occidentali» — e' su una delle
DUE lingue che devono essere impeccabili.

    La tabella completa dopo tre classi:
                       numeri  negazione  entita'   dettaglio aggiunto
      EN                 si       si        si            si
      IT                 si       si        si            NO
      ZH KO              si       si        si            si
      JA                 si       si        si            NO
      AR                 si       si        NO            NO
      HI                 si       si        NO            si
      TH                 si       NO        NO            NO

E IL COMMENTO DEL GATE VA LETTO DI NUOVO. `anti_confab_gate.py:2377-2392`
dichiara «B DETTAGLIO non detto su entita' VERA -> ammessi 5/5 con g 97,1-99,5»
e porta tre esempi: «40 pezzi», «45 minuti», «1200 euro». Sono TUTTI E TRE
NUMERICI. Oggi il dettaglio numerico e' fermato in 8 lingue su 8 — L4.1 e' nato
il 05/08 (4fe67afd) proprio per quello. Quindi quel 5/5 descrive uno stato
SUPERATO per i numeri; il buco che resta e' il dettaglio NON numerico, dove un
layer deterministico non puo' arrivare per costruzione, e li' non e' mai stato
misurato. La cura ha chiuso la meta' che sapeva contare.

Regime: porta pubblica `verimem remember --source`, store temporaneo, FUORI
pytest. PYTHONUTF8=1 per la STAMPA, non per il gate.
Un solo store fra i casi, quindi L3 puo' farli vedere fra loro. Come per il
banco dell'entita' sostituita, i casi che PASSANO vanno ri-verificati uno per
processo con store vuoto: L3 aggiunge quarantene, quindi un'ammissione regge a
maggior ragione, ma «regge» va misurato, non dedotto.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_dettaglio_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (lingua, fonte, vero, dettaglio NUMERICO aggiunto, dettaglio NON numerico)
CASI = [
    ("EN", "Shipping log: order 77 was dispatched on 3 March from the Rovigo depot.",
     "Order 77 was dispatched on 3 March.",
     "Order 77 was dispatched on 3 March and contained 40 items.",
     "Order 77 was dispatched on 3 March by express courier."),
    ("IT", "Registro spedizioni: l'ordine 77 e' partito il 3 marzo dal deposito di Rovigo.",
     "L'ordine 77 e' partito il 3 marzo.",
     "L'ordine 77 e' partito il 3 marzo e conteneva 40 pezzi.",
     "L'ordine 77 e' partito il 3 marzo con corriere espresso."),
    ("ZH", "发货记录：77 号订单于三月三日从罗维戈仓库发出。",
     "77 号订单于三月三日发出。",
     "77 号订单于三月三日发出，共 40 件。",
     "77 号订单于三月三日通过特快专递发出。"),
    ("JA", "発送記録：注文 77 は三月三日にロヴィーゴ倉庫から発送されました。",
     "注文 77 は三月三日に発送されました。",
     "注文 77 は三月三日に発送され、40 点が含まれていました。",
     "注文 77 は三月三日に速達便で発送されました。"),
    ("KO", "배송 기록: 주문 77은 삼월 삼일에 로비고 창고에서 발송되었습니다.",
     "주문 77은 삼월 삼일에 발송되었습니다.",
     "주문 77은 삼월 삼일에 발송되었으며 40 개가 포함되어 있었습니다.",
     "주문 77은 삼월 삼일에 특급 택배로 발송되었습니다."),
    ("AR", "سجل الشحن: تم إرسال الطلب 77 في الثالث من مارس من مستودع روفيغو.",
     "تم إرسال الطلب 77 في الثالث من مارس.",
     "تم إرسال الطلب 77 في الثالث من مارس وكان يحتوي على 40 قطعة.",
     "تم إرسال الطلب 77 في الثالث من مارس بالبريد السريع."),
    ("TH", "บันทึกการจัดส่ง: คำสั่งซื้อ 77 ถูกส่งออกเมื่อวันที่ 3 มีนาคม จากคลังโรวีโก",
     "คำสั่งซื้อ 77 ถูกส่งออกเมื่อวันที่ 3 มีนาคม",
     "คำสั่งซื้อ 77 ถูกส่งออกเมื่อวันที่ 3 มีนาคม และมีสินค้า 40 ชิ้น",
     "คำสั่งซื้อ 77 ถูกส่งออกเมื่อวันที่ 3 มีนาคม โดยบริการจัดส่งด่วน"),
    ("HI", "शिपिंग रिकॉर्ड: ऑर्डर 77 तीन मार्च को रोविगो गोदाम से भेजा गया।",
     "ऑर्डर 77 तीन मार्च को भेजा गया।",
     "ऑर्डर 77 तीन मार्च को भेजा गया और उसमें 40 वस्तुएँ थीं।",
     "ऑर्डर 77 तीन मार्च को एक्सप्रेस कूरियर से भेजा गया।"),
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
    m = re.search(r"grounding ([\d.]+)", o)
    return esito, (float(m.group(1)) if m else None), (
        "+".join(sorted(set(_L.findall(o)))) or "-")


def main_banco() -> None:
    print("%-4s %-22s %-12s %-12s %7s  %s"
          % ("lg", "caso", "atteso", "esito", "g", "layer"))
    veri, passa_num, passa_txt = 0, [], []
    for lg, src, vero, d_num, d_txt in CASI:
        for nome, claim, atteso in (
                ("VERO", vero, "admitted"),
                ("dettaglio NUMERICO", d_num, "quarantined"),
                ("dettaglio NON numerico", d_txt, "quarantined")):
            e, g, layer = esegui(claim, src)
            giusto = (e == atteso)
            if nome == "VERO" and giusto:
                veri += 1
            if nome == "dettaglio NUMERICO" and not giusto:
                passa_num.append(lg)
            if nome == "dettaglio NON numerico" and not giusto:
                passa_txt.append(lg)
            print("%-4s %-22s %-12s %-12s %7s  %-24s %s"
                  % (lg, nome, atteso, e, ("%.1f" % g) if g is not None else "-",
                     layer, "" if giusto else "<<<"))
        print()
    print("=" * 84)
    print("  VERI ammessi ......................... %d/%d" % (veri, len(CASI)))
    print("  dettaglio NUMERICO passa in .......... %s   <- controllo"
          % (", ".join(passa_num) or "nessuna"))
    print("  dettaglio NON NUMERICO passa in ...... %s   <- LA MISURA"
          % (", ".join(passa_txt) or "nessuna"))
    print()
    print("  Se EN o IT compaiono nell'ultima riga, il difetto NON e'")
    print("  multilingue: e' la forma piu' comune di allucinazione, e")
    print("  riguarda ogni utente.")


if __name__ == "__main__":
    main_banco()
