# -*- coding: utf-8 -*-
"""La vetrina fa DUE promesse. Del degrado per scrittura ho misurato solo la PRIMA.

Il README dichiara due garanzie separate: (1) una contraddizione della fonte
viene fermata, (2) un dettaglio che la fonte NON contiene viene fermato. E
dichiara che «beyond IT/EN the first guarantee degrades with the script»,
portando il gradiente misurato sull'ENTITA' SOSTITUITA.

Su quella riga ho gia' misurato due classi fuori da IT/EN (entita' sostituita e
contraddizione implicita). La SECONDA garanzia, no: il dettaglio aggiunto e'
misurato in IT (8/10), EN (9/10) e TH (10/10) e basta. Cinque scritture
scoperte su una riga che il lettore usa per decidere se fidarsi.

⚠️ E c'e' una ragione per cui la risposta non e' ovvia: le due garanzie NON
passano dallo stesso meccanismo. Il dettaglio NUMERICO lo ferma `L4.1`, che
cerca la cifra dentro la fonte — un criterio LESSICALE, che non ha ragione di
dipendere dalla lingua. Il dettaglio NON numerico non ha una lama dedicata e
resta al giudice, cioe' allo stesso componente che degrada con la scrittura.
Da qui la predizione che questo banco mette alla prova, PRIMA di eseguirlo:

    A (numerico)     -> regge uniformemente in tutte le scritture
    B (non numerico) -> degrada, come degradano le altre classi del giudice

Se A e B degradassero insieme, la mia attribuzione «e' L4.1 che tiene su la
seconda garanzia» sarebbe falsa. Se reggessero entrambi, la seconda garanzia
sarebbe solida ovunque e la vetrina — che qualifica il degrado alla PRIMA —
sarebbe esatta per la ragione giusta.

═══════════════════════════════════════════════════════════════════════════
ESITO — meta' predizione confermata, meta' FALSIFICATA, e la meta' sbagliata
vale piu' di quella giusta::

    lg    A numerico    B non numerico    VERI rifiutati
    EN       0/3            3/3               0/1
    ZH       0/3            2/3               0/1
    JA       0/3            3/3               0/1
    KO       0/3            2/3               0/1
    AR       0/3            3/3               0/1
    HI       0/3            3/3               0/1

① A CONFERMATA, e in modo netto: 18 casi su 18 fermati, in tutte e sei le
scritture, e SEMPRE dallo stesso layer — `L4.1`. Un criterio lessicale sulla
cifra non ha una lingua, e infatti non ne mostra una.

🔑 ② B FALSIFICATA, e NON nella direzione che temevo: non «degrada con la
scrittura». **Non degrada affatto: e' gia' a terra in INGLESE** (3/3 sfuggiti,
la peggiore insieme a JA/AR/HI). Le uniche due che ne fermano uno sono ZH e KO
— scritture NON latine. ⇒ Su questa garanzia non esiste il gradiente per
scrittura che governa l'altra: **l'asse non e' la lingua, e' la presenza di una
CIFRA**. Zero su 18 quando c'e', sedici su 18 quando non c'e'.

🔑 ③ COSA NE SEGUE PER LA VETRINA, e non e' una smentita. `README.md:707` non
promette affatto di fermare il non sostenuto: dichiara il contrario, col
numero — «unsupported ones are admitted: 8/10 IT, 9/10 EN». La riga e' VERA.
Ma quel tasso aggrega due popolazioni dal comportamento OPPOSTO, e chi lo legge
come un tasso unico conclude «ne ferma 2 su 10». Il dato vero e': **ne ferma
praticamente tutti se portano una cifra, e quasi nessuno se non la portano.**
E' la forma della lezione «misura entrambe le popolazioni, consegna la
SEPARAZIONE», applicata a una riga che gia' consegna il numero onesto.
📌 Conferma indipendente del commento a `anti_confab_gate.py:2377`, dove avevo
scritto che i tre esempi storici del «B dettaglio → 5/5 ammessi» erano TUTTI
numerici e che la classe restava aperta sul non numerico: aperta lo era, e il
numero della classe aperta e' 16 su 18 su sei scritture.

④ I due che si fermano lo fanno con lame DIVERSE — ZH `guasto` da `L1.20`, KO
`trasporto` da `L4-grounding` con g=18.5 — cioe' due colpi isolati, non una
soglia che tiene. E i VERI di controllo passano 6 su 6: il banco non e'
degenere, e il prezzo su questa classe non si paga sull'altra popolazione.

⚠️ LIMITI, dichiarati: n=3 per sottoclasse per lingua, e n=1 sul VERO — la
tabella regge il CONTRASTO A vs B, non fissa un tasso per lingua. Restano non
misurate: il numero scritto in caratteri locali, e il dettaglio aggiunto in
italiano su questa stessa terna (misurato altrove, su casi diversi).
═══════════════════════════════════════════════════════════════════════════

📐 REGIME, e una scelta di disegno che va dichiarata: i numeri sono in CIFRE
ARABE (340, 12, 27) in TUTTE e sei le lingue. Scriverli in caratteri locali
(三百四十, ٣٤٠) avrebbe cambiato DUE cose insieme — la scrittura del testo e la
forma del numero — e i due fattori sarebbero stati confusi per costruzione.
Con le cifre fisse, l'unica variabile e' la scrittura del testo intorno. ⇒ La
cella «numero scritto in caratteri locali» resta NON misurata, e non pretendo
di averla coperta.

Fonte e claim condividono lo stesso fatto: cio' che cambia e' SOLO il dettaglio
aggiunto, che la fonte non contiene. Ogni lingua porta un VERO di controllo —
una riformulazione fedele della stessa fonte — che deve essere AMMESSO: senza,
un gate che rifiutasse tutto sembrerebbe perfetto.

Regime: porta pubblica `verimem remember --source`, store temporaneo, FUORI
pytest, n=3 per sottoclasse e per lingua (dichiarato: serve al contrasto A/B
dentro la stessa lingua, non a fissare un tasso).
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_dett_xl_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

_L = re.compile(r"L\d+(?:\.\d+)?(?:-[a-z-]+)?|store-screen|L4-[a-z-]+")

#: {lingua: [(sottoclasse, nome, fonte, claim_falso), ...]} + il VERO in coda
CASI = {
    "EN": [
        ("A", "colli", "Logistics note: the shipment was delivered to the Bari depot.",
         "The shipment of 340 crates was delivered to the Bari depot."),
        ("A", "voti", "Minutes: the board approved the budget.",
         "The board approved the budget with 12 votes in favour."),
        ("A", "assunti", "Report: the Verona branch hired new staff.",
         "The Verona branch hired 27 people."),
        ("B", "notaio", "Note: the contract was signed at the head office.",
         "The contract was signed at the head office in the presence of notary Ferri."),
        ("B", "guasto", "Log: line 3 stopped because of a fault.",
         "Line 3 stopped because of a fault in the hydraulic system."),
        ("B", "trasporto", "Record: the sample was moved to the laboratory.",
         "The sample was moved to the Padua laboratory in a refrigerated van."),
        ("V", "VERO", "Logistics note: the shipment was delivered to the Bari depot.",
         "The Bari depot received the shipment."),
    ],
    "ZH": [
        ("A", "colli", "物流记录：货物已送达巴里仓库。", "340箱货物已送达巴里仓库。"),
        ("A", "voti", "会议记录：董事会批准了预算。", "董事会以12票赞成批准了预算。"),
        ("A", "assunti", "报告：维罗纳分公司招聘了新员工。", "维罗纳分公司招聘了27人。"),
        ("B", "notaio", "备注：合同在总部签署。", "合同在总部由公证人费里在场签署。"),
        ("B", "guasto", "日志：三号生产线因故障停机。", "三号生产线因液压系统故障停机。"),
        ("B", "trasporto", "记录：样品已转移到实验室。", "样品已用冷藏车转移到帕多瓦实验室。"),
        ("V", "VERO", "物流记录：货物已送达巴里仓库。", "巴里仓库已收到货物。"),
    ],
    "JA": [
        ("A", "colli", "物流記録：荷物はバーリ倉庫に配達されました。",
         "340箱の荷物はバーリ倉庫に配達されました。"),
        ("A", "voti", "議事録：取締役会は予算を承認しました。",
         "取締役会は賛成12票で予算を承認しました。"),
        ("A", "assunti", "報告：ヴェローナ支店は新しい従業員を採用しました。",
         "ヴェローナ支店は27人を採用しました。"),
        ("B", "notaio", "備考：契約は本社で署名されました。",
         "契約は本社で公証人フェッリの立ち会いのもとで署名されました。"),
        ("B", "guasto", "ログ：三号ラインは故障のため停止しました。",
         "三号ラインは油圧系統の故障のため停止しました。"),
        ("B", "trasporto", "記録：試料は研究所に移されました。",
         "試料は冷蔵車でパドヴァの研究所に移されました。"),
        ("V", "VERO", "物流記録：荷物はバーリ倉庫に配達されました。",
         "バーリ倉庫は荷物を受け取りました。"),
    ],
    "KO": [
        ("A", "colli", "물류 기록: 화물이 바리 창고로 배송되었습니다.",
         "340상자의 화물이 바리 창고로 배송되었습니다."),
        ("A", "voti", "회의록: 이사회가 예산을 승인했습니다.",
         "이사회가 찬성 12표로 예산을 승인했습니다."),
        ("A", "assunti", "보고서: 베로나 지점이 신입 직원을 채용했습니다.",
         "베로나 지점이 27명을 채용했습니다."),
        ("B", "notaio", "비고: 계약서는 본사에서 서명되었습니다.",
         "계약서는 본사에서 공증인 페리가 입회한 가운데 서명되었습니다."),
        ("B", "guasto", "로그: 3호 라인이 고장으로 정지했습니다.",
         "3호 라인이 유압 시스템 고장으로 정지했습니다."),
        ("B", "trasporto", "기록: 시료가 연구소로 옮겨졌습니다.",
         "시료가 냉장 차량으로 파도바 연구소로 옮겨졌습니다."),
        ("V", "VERO", "물류 기록: 화물이 바리 창고로 배송되었습니다.",
         "바리 창고가 화물을 받았습니다."),
    ],
    "AR": [
        ("A", "colli", "سجل الشحن: تم تسليم الشحنة إلى مستودع باري.",
         "تم تسليم شحنة من 340 صندوقًا إلى مستودع باري."),
        ("A", "voti", "محضر الاجتماع: وافق مجلس الإدارة على الميزانية.",
         "وافق مجلس الإدارة على الميزانية بـ 12 صوتًا مؤيدًا."),
        ("A", "assunti", "تقرير: وظّف فرع فيرونا موظفين جددًا.",
         "وظّف فرع فيرونا 27 شخصًا."),
        ("B", "notaio", "ملاحظة: تم توقيع العقد في المقر الرئيسي.",
         "تم توقيع العقد في المقر الرئيسي بحضور الموثّق فيري."),
        ("B", "guasto", "سجل: توقف الخط الثالث بسبب عطل.",
         "توقف الخط الثالث بسبب عطل في النظام الهيدروليكي."),
        ("B", "trasporto", "سجل: تم نقل العينة إلى المختبر.",
         "تم نقل العينة إلى مختبر بادوفا في شاحنة مبردة."),
        ("V", "VERO", "سجل الشحن: تم تسليم الشحنة إلى مستودع باري.",
         "استلم مستودع باري الشحنة."),
    ],
    "HI": [
        ("A", "colli", "लदान रिकॉर्ड: माल बारी गोदाम पहुँचा दिया गया।",
         "340 पेटियों का माल बारी गोदाम पहुँचा दिया गया।"),
        ("A", "voti", "कार्यवृत्त: निदेशक मंडल ने बजट स्वीकृत किया।",
         "निदेशक मंडल ने 12 मतों से बजट स्वीकृत किया।"),
        ("A", "assunti", "रिपोर्ट: वेरोना शाखा ने नए कर्मचारी नियुक्त किए।",
         "वेरोना शाखा ने 27 लोगों को नियुक्त किया।"),
        ("B", "notaio", "टिप्पणी: अनुबंध मुख्यालय में हस्ताक्षरित हुआ।",
         "अनुबंध मुख्यालय में नोटरी फ़ेरी की उपस्थिति में हस्ताक्षरित हुआ।"),
        ("B", "guasto", "लॉग: तीसरी लाइन खराबी के कारण रुक गई।",
         "तीसरी लाइन हाइड्रोलिक प्रणाली की खराबी के कारण रुक गई।"),
        ("B", "trasporto", "अभिलेख: नमूना प्रयोगशाला भेजा गया।",
         "नमूना प्रशीतित वैन से पादोवा प्रयोगशाला भेजा गया।"),
        ("V", "VERO", "लदान रिकॉर्ड: माल बारी गोदाम पहुँचा दिया गया।",
         "बारी गोदाम को माल मिल गया।"),
    ],
}


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
    print("%-3s %-2s %-11s %-12s %7s  %s"
          % ("lg", "cl", "caso", "esito", "g", "layer"))
    print("-" * 74)
    tot = {}
    for lg, casi in CASI.items():
        passa = {"A": 0, "B": 0}
        vero_ko = 0
        for cl, nome, src, claim in casi:
            esito, g, lay = esegui(claim, src)
            if cl == "V":
                atteso_ko = esito != "admitted"
                vero_ko += 1 if atteso_ko else 0
                marca = "  <<< VERO RIFIUTATO" if atteso_ko else ""
            else:
                sfugge = esito != "quarantined"
                passa[cl] += 1 if sfugge else 0
                marca = "  <<< SFUGGE" if sfugge else ""
            print("%-3s %-2s %-11s %-12s %7s  %s%s"
                  % (lg, cl, nome, esito, "-" if g is None else g, lay, marca))
        tot[lg] = (passa["A"], passa["B"], vero_ko)
        print("-" * 74)

    print("\n=== SFUGGITI su 3 per sottoclasse (piu' basso = meglio) ===")
    print("%-3s  %-14s %-14s %s" % ("lg", "A numerico", "B non numerico",
                                    "VERI rifiutati"))
    for lg, (a, b, v) in tot.items():
        print("%-3s  %-14s %-14s %s" % (lg, "%d/3" % a, "%d/3" % b, "%d/1" % v))
    print("\nLa predizione dichiarata prima di eseguire: A uniforme (lo ferma")
    print("L4.1, criterio lessicale sulla cifra), B degrada con la scrittura")
    print("(resta al giudice). La tabella qui sopra la conferma o la falsifica.")


if __name__ == "__main__":
    main_banco()
