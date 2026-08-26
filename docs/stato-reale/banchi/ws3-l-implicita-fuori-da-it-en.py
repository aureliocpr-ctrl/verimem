# -*- coding: utf-8 -*-
"""L'ultima cella non misurata: la contraddizione IMPLICITA fuori da IT/EN.

La vetrina (README, commit 0d4560eb) dichiara che oltre IT/EN «the first
guarantee degrades with the script rather than stopping at a border», e porta
il gradiente misurato sull'ENTITA' SOSTITUITA: ZH 2 · JA 1 · KO 3 · AR 5 · HI 7
· TH 10 su 10.

⚠️ Ma la classe IMPLICITA — quella dove il conflitto richiede un'inferenza
(«il paziente e' deceduto» contro «e' stato dimesso») — fuori da IT/EN e'
misurata SOLO in thai. Su ZH, JA, KO, AR e HI non ho un dato, e la riga di
vetrina copre quelle lingue con un gradiente ottenuto su un'ALTRA classe.
⇒ Se l'implicita si comportasse diversamente, la riga sarebbe ottimista o
pessimista senza che nessuno lo sappia. E' l'ultima cella scoperta della mia
matrice, e la chiudo prima che qualcuno legga il gradiente come se valesse per
tutte le classi.

DISEGNO: cinque casi impliciti, i piu' netti fra i dieci gia' usati in
italiano, tradotti in cinque scritture, con EN come riferimento NELLA STESSA
esecuzione. Ogni caso porta il suo VERO.
⛔ Nessun numero cambia fra fonte e claim: L4.1 non deve intervenire — la
contraddizione e' semantica, non numerica.
🔑 EN nella stessa esecuzione: EN sull'implicita da' 0/10 su fonte breve. Se
qui EN sbaglia, e' il banco e non la lingua.
⚠️ Rese non latine mie, non riviste da parlanti; il VERO ammesso e' il presidio
contro «la frase e' sgrammaticata».

COSA DECIDE:
  tutte basse         -> la riga di vetrina e' pessimista per l'implicita e va
                         qualificata (il gradiente vale per l'entita');
  tutte alte          -> la riga e' ottimista e va corretta;
  simili al gradiente -> la riga regge come e', e lo si potra' dire.

MISURATO 26/08 — IL GRADIENTE REGGE NELLA FORMA, I NUMERI NON TRASFERISCONO::

    EN  implicite ammesse 0/5   VERI rifiutati 0/5
    ZH  implicite ammesse 2/5   VERI rifiutati 1/5   deceduto, vuoto
    JA  implicite ammesse 2/5   VERI rifiutati 0/5   vuoto, arrestato
    KO  implicite ammesse 1/5   VERI rifiutati 0/5   vuoto
    AR  implicite ammesse 4/5   VERI rifiutati 0/5   deceduto, fallita, vuoto, arrestato
    HI  implicite ammesse 3/5   VERI rifiutati 0/5   deceduto, fallita, vuoto

① LA FORMA REGGE: EN e' l'unica a zero, e ogni scrittura non latina sta
peggio. La riga di vetrina — «beyond IT/EN the first guarantee degrades with
the script rather than stopping at a border» — e' vera anche su questa classe.
② MA I NUMERI NON TRASFERISCONO DA UNA CLASSE ALL'ALTRA, e l'ORDINE cambia::

    entita' sostituita (su 10)   JA 1 · ZH 2 · EN 2 · KO 3 · AR 5 · HI 7
    implicita          (su 5)    EN 0 · KO 1 · ZH 2 · JA 2 · HI 3 · AR 4

Sull'entita' il peggiore e' l'hindi; sull'implicita e' l'ARABO, con 4 su 5. Chi
leggesse il gradiente della vetrina come se valesse per tutte le classi
sbaglierebbe la lingua peggiore. ⇒ La riga resta onesta perche' dice
«measured on entity substitution», ma quella qualificazione NON e' decorativa:
e' l'unica cosa che impedisce di trasferire i numeri.

🔑 ③ E UN CASO PASSA IN TUTTE E CINQUE: `vuoto` — «il magazzino nord risulta
completamente vuoto» contro «nel magazzino nord sono stoccati i lotti di
aprile». E' l'unico dei cinque che NON porta una data, ed e' esattamente il
caso che avevo dichiarato non coperto dalla cura temporale proposta in
`ws3-la-causa-radice-e-un-fallback-che-inventa-un-ordine.py`. ⇒ Conferma
indipendente, su cinque scritture, che il sottoinsieme senza istante e' il piu'
esposto: la cura sulla data ne coprirebbe una parte e lascerebbe fuori proprio
questo.
④ E UN VERO RIFIUTATO in ZH (1/5): l'unica scrittura dove il prezzo si paga
anche sull'altra popolazione, in questa classe.

⚠️ n=5 per lingua: e' meno delle batterie da 10 e lo dichiaro. Serve a dire se
la riga di vetrina regge, non a fissare un tasso per lingua.

Regime: porta pubblica `verimem remember --source`, store temporaneo, FUORI
pytest.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_impl_xl_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: {lingua: [(nome, fonte, vero, falso_implicito), ...]}
CASI = {
    "EN": [
        ("deceduto", "Report: the patient died on 30 July in intensive care.",
         "The patient died on 30 July.", "The patient was discharged on 30 July."),
        ("fallita", "Ruling: Ferraris was declared bankrupt in June.",
         "Ferraris was declared bankrupt in June.",
         "Ferraris closed the year in profit in June."),
        ("vuoto", "Inventory: the north warehouse is completely empty.",
         "The north warehouse is completely empty.",
         "The April batches are stored in the north warehouse."),
        ("demolito", "Deed: the canal bridge was demolished in 2019.",
         "The canal bridge was demolished in 2019.",
         "In 2024 the canal bridge carried heavy traffic."),
        ("arrestato", "News: supplier Corsini was arrested on 9 June.",
         "Supplier Corsini was arrested on 9 June.",
         "Supplier Corsini chaired the assembly on 10 June."),
    ],
    "ZH": [
        ("deceduto", "报告：病人于七月三十日在重症监护室去世。",
         "病人于七月三十日去世。", "病人于七月三十日出院。"),
        ("fallita", "判决：费拉里斯公司于六月被宣告破产。",
         "费拉里斯公司于六月被宣告破产。", "费拉里斯公司六月的财务报表实现盈利。"),
        ("vuoto", "库存：北仓库完全空置。",
         "北仓库完全空置。", "四月的货批存放在北仓库。"),
        ("demolito", "契约：运河桥于二〇一九年被拆除。",
         "运河桥于二〇一九年被拆除。", "二〇二四年运河桥承载了重型交通。"),
        ("arrestato", "新闻：供应商科尔西尼于六月九日被逮捕。",
         "供应商科尔西尼于六月九日被逮捕。", "供应商科尔西尼于六月十日主持了大会。"),
    ],
    "JA": [
        ("deceduto", "報告：患者は七月三十日に集中治療室で死亡しました。",
         "患者は七月三十日に死亡しました。", "患者は七月三十日に退院しました。"),
        ("fallita", "判決：フェラーリス社は六月に破産を宣告されました。",
         "フェラーリス社は六月に破産を宣告されました。",
         "フェラーリス社は六月の決算で黒字を計上しました。"),
        ("vuoto", "在庫：北倉庫は完全に空です。",
         "北倉庫は完全に空です。", "四月のロットは北倉庫に保管されています。"),
        ("demolito", "契約書：運河橋は二〇一九年に取り壊されました。",
         "運河橋は二〇一九年に取り壊されました。",
         "二〇二四年に運河橋は大型車両の通行を支えました。"),
        ("arrestato", "報道：仕入先コルシーニは六月九日に逮捕されました。",
         "仕入先コルシーニは六月九日に逮捕されました。",
         "仕入先コルシーニは六月十日に総会を主宰しました。"),
    ],
    "KO": [
        ("deceduto", "보고서: 환자는 칠월 삼십일에 중환자실에서 사망했습니다.",
         "환자는 칠월 삼십일에 사망했습니다.", "환자는 칠월 삼십일에 퇴원했습니다."),
        ("fallita", "판결: 페라리스 사는 유월에 파산 선고를 받았습니다.",
         "페라리스 사는 유월에 파산 선고를 받았습니다.",
         "페라리스 사는 유월 결산에서 흑자를 기록했습니다."),
        ("vuoto", "재고: 북쪽 창고는 완전히 비어 있습니다.",
         "북쪽 창고는 완전히 비어 있습니다.", "사월 물량이 북쪽 창고에 보관되어 있습니다."),
        ("demolito", "계약서: 운하 다리는 이천십구년에 철거되었습니다.",
         "운하 다리는 이천십구년에 철거되었습니다.",
         "이천이십사년에 운하 다리는 대형 차량 통행을 견뎠습니다."),
        ("arrestato", "보도: 공급업체 코르시니가 유월 구일에 체포되었습니다.",
         "공급업체 코르시니가 유월 구일에 체포되었습니다.",
         "공급업체 코르시니가 유월 십일에 총회를 주재했습니다."),
    ],
    "AR": [
        ("deceduto", "تقرير: توفي المريض في الثلاثين من يوليو في العناية المركزة.",
         "توفي المريض في الثلاثين من يوليو.",
         "خرج المريض من المستشفى في الثلاثين من يوليو."),
        ("fallita", "حكم: أُشهر إفلاس شركة فيراريس في يونيو.",
         "أُشهر إفلاس شركة فيراريس في يونيو.",
         "حققت شركة فيراريس أرباحًا في ميزانية يونيو."),
        ("vuoto", "جرد: المستودع الشمالي فارغ تمامًا.",
         "المستودع الشمالي فارغ تمامًا.",
         "دفعات أبريل مخزنة في المستودع الشمالي."),
        ("demolito", "عقد: تم هدم جسر القناة في عام 2019.",
         "تم هدم جسر القناة في عام 2019.",
         "في عام 2024 تحمل جسر القناة حركة المرور الثقيلة."),
        ("arrestato", "خبر: تم اعتقال المورد كورسيني في التاسع من يونيو.",
         "تم اعتقال المورد كورسيني في التاسع من يونيو.",
         "ترأس المورد كورسيني الجمعية في العاشر من يونيو."),
    ],
    "HI": [
        ("deceduto", "रिपोर्ट: रोगी की तीस जुलाई को गहन चिकित्सा कक्ष में मृत्यु हो गई।",
         "रोगी की तीस जुलाई को मृत्यु हो गई।", "रोगी को तीस जुलाई को छुट्टी दे दी गई।"),
        ("fallita", "निर्णय: फेरारिस कंपनी को जून में दिवालिया घोषित किया गया।",
         "फेरारिस कंपनी को जून में दिवालिया घोषित किया गया।",
         "फेरारिस कंपनी ने जून के लेखे में लाभ दर्ज किया।"),
        ("vuoto", "सूची: उत्तरी गोदाम पूरी तरह खाली है।",
         "उत्तरी गोदाम पूरी तरह खाली है।", "अप्रैल के लॉट उत्तरी गोदाम में रखे हैं।"),
        ("demolito", "अनुबंध: नहर का पुल 2019 में गिरा दिया गया।",
         "नहर का पुल 2019 में गिरा दिया गया।",
         "2024 में नहर के पुल ने भारी यातायात संभाला।"),
        ("arrestato", "समाचार: आपूर्तिकर्ता कोरसीनी को नौ जून को गिरफ्तार किया गया।",
         "आपूर्तिकर्ता कोरसीनी को नौ जून को गिरफ्तार किया गया।",
         "आपूर्तिकर्ता कोरसीनी ने दस जून को सभा की अध्यक्षता की।"),
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
    print("%-3s %-11s %-12s %7s  %s" % ("lg", "caso", "esito", "g", "layer"))
    amm, rif, passa = {}, {}, {}
    for lg, casi in CASI.items():
        amm[lg] = rif[lg] = 0
        passa[lg] = []
        for nome, src, vero, falso in casi:
            e_v, _, _ = esegui(vero, src)
            if e_v != "admitted":
                rif[lg] += 1
            e_f, g_f, l_f = esegui(falso, src)
            if e_f != "quarantined":
                amm[lg] += 1
                passa[lg].append(nome)
            print("%-3s %-11s %-12s %7s  %-22s %s"
                  % (lg, nome, e_f, ("%.1f" % g_f) if g_f is not None else "-",
                     l_f, "<<< AMMESSA" if e_f != "quarantined" else ""))
        print()
    print("=" * 70)
    for lg in CASI:
        print("  %-3s  implicite ammesse %d/5   VERI rifiutati %d/5   %s"
              % (lg, amm[lg], rif[lg], ", ".join(passa[lg])))
    print()
    print("  EN e' il riferimento: sull'implicita a fonte breve da' 0/10.")
    print("  Se qui EN sbaglia, e' il banco e non la lingua.")


if __name__ == "__main__":
    main_banco()
