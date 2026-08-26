# -*- coding: utf-8 -*-
"""Ho scritto «Outside IT/EN neither guarantee holds». Poggia su UNA lingua.

Nel README (commit c62da996) l'apertura adesso dichiara la garanzia che regge —
un claim che la fonte CONTRADDICE non torna come verita' — e chiude con
«Outside IT/EN neither guarantee holds».

Quella riga poggia sul THAI e basta, perche' e' l'unica scrittura per cui ho
misurato tutte e tre le classi a batteria (negazione 6/10, entita' 10/10,
dettaglio 10/10). Sulle altre cinque ho solo il banco del 25/08, che e' a UN
CASO PER CELLA — lo stesso disegno che il 26/08 mi ha fatto ritirare una
conclusione pubblica.

⚠️ Se ZH, JA, KO, AR e HI reggessero sulla classe «entita' sostituita», la mia
riga sarebbe PIU' SEVERA DEL VERO e starei sottovendendo il prodotto sulla
pagina di PyPI. **Una vetrina che promette meno di quello che fa e' inesatta
quanto una che promette di piu'** — solo, nessuno se ne lamenta, ed e' per
questo che nessuno la misura.

DISEGNO: classe entita' sostituita (il fatto della fonte attribuito a UN'ALTRA
entita', tutto il resto identico, numeri compresi), 10 casi, cinque scritture
piu' EN come riferimento NELLA STESSA esecuzione. Ogni caso porta il suo VERO.
⛔ Nessun numero cambia fra fonte e claim: L4.1 non deve poter intervenire.
🔑 EN nella stessa esecuzione: se cede anche lui, e' il disegno e non la lingua.

COSA DECIDE:
  tutte e cinque cedono   -> la riga regge com'e';
  qualcuna regge          -> la riga va ristretta, e la correggo io perche' e'
                             mia. La formulazione onesta diventa un elenco
                             delle scritture misurate, non un «outside IT/EN».

MISURATO 26/08 — LA RIGA E' TROPPO SEVERA, E NON C'E' UN MURO: C'E' UN
GRADIENTE::

    EN  falsita' ammesse  2/10   VERI rifiutati 1/10     <- riferimento
    ZH  falsita' ammesse  2/10   VERI rifiutati 1/10     <- pari a EN
    JA  falsita' ammesse  1/10   VERI rifiutati 0/10     <- MEGLIO di EN
    KO  falsita' ammesse  3/10   VERI rifiutati 0/10
    AR  falsita' ammesse  5/10   VERI rifiutati 0/10
    HI  falsita' ammesse  7/10   VERI rifiutati 0/10
    (TH 10/10, dal banco precedente)

① LA MIA RIGA E' FALSA per cinese e giapponese: reggono quanto o meglio
dell'inglese sulla stessa classe, nella stessa esecuzione. «Outside IT/EN
neither guarantee holds» va corretta, ed e' mia — commit c62da996.
② NON E' UN MURO, E' UN GRADIENTE: 1-2 · 1-2 · 3 · 5 · 7 · 10. La garanzia non
si spegne al confine di IT/EN: degrada con la scrittura. Una riga binaria
(«dentro vale, fuori no») e' comoda e sbagliata in entrambe le direzioni —
promette troppo poco su ZH/JA e troppo su KO/AR/HI, che con 3, 5 e 7 su 10 non
stanno «quasi bene».
🔑 ③ TERZA REPLICA INDIPENDENTE, non cercata: EN da' 2/10 qui, e 2/10 nel banco
dell'entita' su fonti diverse. Il disegno regge attraverso tre popolazioni.
④ E I VERI: 2 rifiutati in tutto (EN e ZH), zero nelle altre quattro. Il gate
non e' paranoico su nessuna di queste scritture — su HI ammette 7 falsita' su
10 senza rifiutare un solo vero, che e' il profilo di chi non sta guardando.

⚠️ QUESTO BANCO MISURA UNA CLASSE SOLA (entita' sostituita). Non autorizza a
dire «ZH e JA sono a posto»: sulle altre due classi, fuori da IT/EN, l'unico
dato e' il thai. La correzione al README deve dirlo.

Regime: porta pubblica `verimem remember --source`, store temporaneo, FUORI
pytest. PYTHONUTF8=1 per la STAMPA, non per il gate.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_vetrina_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (lingua, [(fonte, vero, falso), ...])  — 10 casi per lingua
CASI = {
    "EN": [
        ("Report: the north warehouse measures 1800 square metres.",
         "The north warehouse measures 1800 square metres.",
         "The south warehouse measures 1800 square metres."),
        ("Deed: the Rovigo warehouse was sold to Mr Anselmi.",
         "The Rovigo warehouse was sold to Mr Anselmi.",
         "The Rovigo warehouse was sold to Mr Boveri."),
        ("Minutes: the sales department request was rejected.",
         "The sales department request was rejected.",
         "The purchasing department request was rejected."),
        ("Note: supplier Baldini delivered the batch on 9 June.",
         "Supplier Baldini delivered the batch on 9 June.",
         "Supplier Corsini delivered the batch on 9 June."),
        ("Report: the Mestre site was handed over in November.",
         "The Mestre site was handed over in November.",
         "The Treviso site was handed over in November."),
        ("Note: the migration to Postgres was approved on 9 June.",
         "The migration to Postgres was approved on 9 June.",
         "The migration to MySQL was approved on 9 June."),
        ("Minutes: the report was presented by Dr Merli.",
         "The report was presented by Dr Merli.",
         "The report was presented by Dr Fabbri."),
        ("Note: the night shift completed the maintenance on line 3.",
         "The night shift completed the maintenance on line 3.",
         "The day shift completed the maintenance on line 3."),
        ("Report: the cardiology ward patient was discharged on 30 July.",
         "The cardiology ward patient was discharged on 30 July.",
         "The oncology ward patient was discharged on 30 July."),
        ("Minutes: the contract was awarded to Ferraris.",
         "The contract was awarded to Ferraris.",
         "The contract was awarded to Malaspina."),
    ],
    "ZH": [
        ("报告：北仓库面积为 1800 平方米。", "北仓库面积为 1800 平方米。", "南仓库面积为 1800 平方米。"),
        ("契约：罗维戈仓库出售给了安德森先生。", "罗维戈仓库出售给了安德森先生。", "罗维戈仓库出售给了巴克斯特先生。"),
        ("会议记录：销售部门的申请被驳回。", "销售部门的申请被驳回。", "采购部门的申请被驳回。"),
        ("通知：供应商巴尔迪尼于六月九日交付了货物。", "供应商巴尔迪尼于六月九日交付了货物。", "供应商科尔西尼于六月九日交付了货物。"),
        ("报告：梅斯特雷工地于十一月移交。", "梅斯特雷工地于十一月移交。", "特雷维索工地于十一月移交。"),
        ("记录：向 Postgres 的迁移于六月九日获得批准。", "向 Postgres 的迁移于六月九日获得批准。", "向 MySQL 的迁移于六月九日获得批准。"),
        ("会议记录：报告由梅尔利医生提交。", "报告由梅尔利医生提交。", "报告由法布里医生提交。"),
        ("记录：夜班完成了三号生产线的维护。", "夜班完成了三号生产线的维护。", "白班完成了三号生产线的维护。"),
        ("报告：心内科病人于七月三十日出院。", "心内科病人于七月三十日出院。", "肿瘤科病人于七月三十日出院。"),
        ("会议记录：合同授予了费拉里斯公司。", "合同授予了费拉里斯公司。", "合同授予了马拉斯皮纳公司。"),
    ],
    "JA": [
        ("報告：北倉庫の面積は 1800 平方メートルです。", "北倉庫の面積は 1800 平方メートルです。", "南倉庫の面積は 1800 平方メートルです。"),
        ("契約書：ロヴィーゴ倉庫はアンダーソン氏に売却されました。", "ロヴィーゴ倉庫はアンダーソン氏に売却されました。", "ロヴィーゴ倉庫はバクスター氏に売却されました。"),
        ("議事録：営業部の申請は却下されました。", "営業部の申請は却下されました。", "購買部の申請は却下されました。"),
        ("通知：仕入先バルディーニが六月九日に納品しました。", "仕入先バルディーニが六月九日に納品しました。", "仕入先コルシーニが六月九日に納品しました。"),
        ("報告：メストレ現場は十一月に引き渡されました。", "メストレ現場は十一月に引き渡されました。", "トレヴィーゾ現場は十一月に引き渡されました。"),
        ("記録：Postgres への移行は六月九日に承認されました。", "Postgres への移行は六月九日に承認されました。", "MySQL への移行は六月九日に承認されました。"),
        ("議事録：報告はメルリ医師によって提出されました。", "報告はメルリ医師によって提出されました。", "報告はファッブリ医師によって提出されました。"),
        ("記録：夜勤が三番生産ラインの保守を完了しました。", "夜勤が三番生産ラインの保守を完了しました。", "日勤が三番生産ラインの保守を完了しました。"),
        ("報告：循環器科の患者は七月三十日に退院しました。", "循環器科の患者は七月三十日に退院しました。", "腫瘍科の患者は七月三十日に退院しました。"),
        ("議事録：契約はフェラーリス社に授与されました。", "契約はフェラーリス社に授与されました。", "契約はマラスピーナ社に授与されました。"),
    ],
    "KO": [
        ("보고서: 북쪽 창고의 면적은 1800 제곱미터입니다.", "북쪽 창고의 면적은 1800 제곱미터입니다.", "남쪽 창고의 면적은 1800 제곱미터입니다."),
        ("계약서: 로비고 창고는 앤더슨 씨에게 매각되었습니다.", "로비고 창고는 앤더슨 씨에게 매각되었습니다.", "로비고 창고는 백스터 씨에게 매각되었습니다."),
        ("회의록: 영업부의 요청이 기각되었습니다.", "영업부의 요청이 기각되었습니다.", "구매부의 요청이 기각되었습니다."),
        ("통지: 공급업체 발디니가 유월 구일에 납품했습니다.", "공급업체 발디니가 유월 구일에 납품했습니다.", "공급업체 코르시니가 유월 구일에 납품했습니다."),
        ("보고서: 메스트레 현장은 십일월에 인도되었습니다.", "메스트레 현장은 십일월에 인도되었습니다.", "트레비소 현장은 십일월에 인도되었습니다."),
        ("기록: Postgres 로의 이전이 유월 구일에 승인되었습니다.", "Postgres 로의 이전이 유월 구일에 승인되었습니다.", "MySQL 로의 이전이 유월 구일에 승인되었습니다."),
        ("회의록: 보고서는 메를리 박사가 제출했습니다.", "보고서는 메를리 박사가 제출했습니다.", "보고서는 파브리 박사가 제출했습니다."),
        ("기록: 야간 근무조가 삼번 생산라인 정비를 완료했습니다.", "야간 근무조가 삼번 생산라인 정비를 완료했습니다.", "주간 근무조가 삼번 생산라인 정비를 완료했습니다."),
        ("보고서: 순환기내과 환자는 칠월 삼십일에 퇴원했습니다.", "순환기내과 환자는 칠월 삼십일에 퇴원했습니다.", "종양내과 환자는 칠월 삼십일에 퇴원했습니다."),
        ("회의록: 계약은 페라리스 사에 낙찰되었습니다.", "계약은 페라리스 사에 낙찰되었습니다.", "계약은 말라스피나 사에 낙찰되었습니다."),
    ],
    "AR": [
        ("تقرير: مساحة المستودع الشمالي 1800 متر مربع.", "مساحة المستودع الشمالي 1800 متر مربع.", "مساحة المستودع الجنوبي 1800 متر مربع."),
        ("عقد: تم بيع مستودع روفيغو إلى السيد أندرسون.", "تم بيع مستودع روفيغو إلى السيد أندرسون.", "تم بيع مستودع روفيغو إلى السيد باكستر."),
        ("محضر: تم رفض طلب قسم المبيعات.", "تم رفض طلب قسم المبيعات.", "تم رفض طلب قسم المشتريات."),
        ("إشعار: قام المورد بالديني بالتسليم في التاسع من يونيو.", "قام المورد بالديني بالتسليم في التاسع من يونيو.", "قام المورد كورسيني بالتسليم في التاسع من يونيو."),
        ("تقرير: تم تسليم موقع ميستري في نوفمبر.", "تم تسليم موقع ميستري في نوفمبر.", "تم تسليم موقع تريفيزو في نوفمبر."),
        ("سجل: تمت الموافقة على الانتقال إلى Postgres في التاسع من يونيو.", "تمت الموافقة على الانتقال إلى Postgres في التاسع من يونيو.", "تمت الموافقة على الانتقال إلى MySQL في التاسع من يونيو."),
        ("محضر: قدمت الدكتورة ميرلي التقرير.", "قدمت الدكتورة ميرلي التقرير.", "قدمت الدكتورة فابري التقرير."),
        ("سجل: أكملت الوردية الليلية صيانة الخط الثالث.", "أكملت الوردية الليلية صيانة الخط الثالث.", "أكملت الوردية النهارية صيانة الخط الثالث."),
        ("تقرير: خرج مريض قسم القلب في الثلاثين من يوليو.", "خرج مريض قسم القلب في الثلاثين من يوليو.", "خرج مريض قسم الأورام في الثلاثين من يوليو."),
        ("محضر: تم منح العقد لشركة فيراريس.", "تم منح العقد لشركة فيراريس.", "تم منح العقد لشركة مالاسبينا."),
    ],
    "HI": [
        ("रिपोर्ट: उत्तरी गोदाम का क्षेत्रफल 1800 वर्ग मीटर है।", "उत्तरी गोदाम का क्षेत्रफल 1800 वर्ग मीटर है।", "दक्षिणी गोदाम का क्षेत्रफल 1800 वर्ग मीटर है।"),
        ("अनुबंध: रोविगो गोदाम श्री एंडरसन को बेचा गया।", "रोविगो गोदाम श्री एंडरसन को बेचा गया।", "रोविगो गोदाम श्री बैक्स्टर को बेचा गया।"),
        ("कार्यवृत्त: बिक्री विभाग का अनुरोध अस्वीकृत कर दिया गया।", "बिक्री विभाग का अनुरोध अस्वीकृत कर दिया गया।", "क्रय विभाग का अनुरोध अस्वीकृत कर दिया गया।"),
        ("सूचना: आपूर्तिकर्ता बालदिनी ने नौ जून को माल पहुँचाया।", "आपूर्तिकर्ता बालदिनी ने नौ जून को माल पहुँचाया।", "आपूर्तिकर्ता कोरसीनी ने नौ जून को माल पहुँचाया।"),
        ("रिपोर्ट: मेस्त्रे साइट नवंबर में सौंपी गई।", "मेस्त्रे साइट नवंबर में सौंपी गई।", "त्रेविजो साइट नवंबर में सौंपी गई।"),
        ("अभिलेख: Postgres पर स्थानांतरण नौ जून को स्वीकृत हुआ।", "Postgres पर स्थानांतरण नौ जून को स्वीकृत हुआ।", "MySQL पर स्थानांतरण नौ जून को स्वीकृत हुआ।"),
        ("कार्यवृत्त: रिपोर्ट डॉक्टर मेरली ने प्रस्तुत की।", "रिपोर्ट डॉक्टर मेरली ने प्रस्तुत की।", "रिपोर्ट डॉक्टर फाब्री ने प्रस्तुत की।"),
        ("अभिलेख: रात्रि पाली ने तीसरी लाइन का रखरखाव पूरा किया।", "रात्रि पाली ने तीसरी लाइन का रखरखाव पूरा किया।", "दिवस पाली ने तीसरी लाइन का रखरखाव पूरा किया।"),
        ("रिपोर्ट: हृदय रोग विभाग का रोगी तीस जुलाई को छुट्टी पा गया।", "हृदय रोग विभाग का रोगी तीस जुलाई को छुट्टी पा गया।", "कैंसर रोग विभाग का रोगी तीस जुलाई को छुट्टी पा गया।"),
        ("कार्यवृत्त: अनुबंध फेरारिस कंपनी को दिया गया।", "अनुबंध फेरारिस कंपनी को दिया गया।", "अनुबंध मालास्पीना कंपनी को दिया गया।"),
    ],
}

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
    print("%-3s %-3s %-6s %-12s %7s  %s"
          % ("lg", "n", "caso", "esito", "g", "layer"))
    amm, veri_rif = {}, {}
    for lg, casi in CASI.items():
        amm[lg] = 0
        veri_rif[lg] = 0
        for i, (src, vero, falso) in enumerate(casi, 1):
            e_v, g_v, l_v = esegui(vero, src)
            if e_v != "admitted":
                veri_rif[lg] += 1
            e_f, g_f, l_f = esegui(falso, src)
            if e_f != "quarantined":
                amm[lg] += 1
            print("%-3s %-3d %-6s %-12s %7s  %-22s %s"
                  % (lg, i, "falso", e_f,
                     ("%.1f" % g_f) if g_f is not None else "-", l_f,
                     "" if e_f == "quarantined" else "<<< AMMESSA"))
        print()
    print("=" * 76)
    for lg in CASI:
        print("  %-3s  falsita' ammesse %2d/10   VERI rifiutati %2d/10"
              % (lg, amm[lg], veri_rif[lg]))
    print()
    print("  EN e' il riferimento nella stessa esecuzione: se cede lui,")
    print("  e' il disegno del banco e non la lingua.")
    print("  Se qualcuna delle cinque REGGE, la riga «Outside IT/EN neither")
    print("  guarantee holds» che ho messo nel README e' TROPPO SEVERA.")


if __name__ == "__main__":
    main_banco()
