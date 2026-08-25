# -*- coding: utf-8 -*-
"""«Magazzino nord» -> «magazzino sud» passa in thai. Passa anche in inglese?

Trovato ieri sera misurando altro: in thai il gate AMMETTE un claim che
sostituisce l'entita' — fonte «il magazzino NORD misura 1800 mq», claim «il
magazzino SUD misura 1800 mq». E' la classe che un moat dovrebbe prendere
sempre: il numero e' identico, cambia solo di cosa si parla.

⇒ LA DOMANDA CHE DECIDE LA TAGLIA DEL DIFETTO, e per questo il banco esiste:
   se passa SOLO in thai, e' una voce della matrice delle scritture;
   se passa anche in EN e IT, non e' multilingue affatto — e' un buco del moat
   che riguarda ogni utente, e la classe non era mai stata isolata.
Per questo EN e IT sono nel banco: non come contorno, come IPOTESI CONCORRENTE.

DUE FORME della stessa classe, perche' potrebbero comportarsi diversamente:
  ATTRIBUTO   nord -> sud      (l'entita' e' distinta da un aggettivo)
  NOME PROPRIO Somchai -> Somsak (l'entita' e' distinta da un nome)
Il ramo `_proper` di `_entita_diverse` (59fb0862, mio) tratta i nomi propri in
modo speciale, quindi le due forme non sono intercambiabili a priori.

⚖️ Ogni fonte porta il suo VERO: senza l'altra popolazione un gate che
rifiutasse tutto sembrerebbe perfetto su questa tabella.
⚠️ Rese non latine mie, non riviste da parlanti — il VERO ammesso e' il presidio
   contro «la frase e' sgrammaticata».

═══ MISURATO 25/08 — l'ipotesi concorrente CADE, e il quadro peggiora ═══

    VERI ammessi ................... 16/16   (nessun falso allarme)
    falso ATTRIBUTO passa in ....... AR, TH, HI
    falso NOME PROPRIO passa in .... TH, HI

⇒ EN e IT NON compaiono: EN IT ZH JA KO fermano entrambe le forme. **Non e' un
buco generale del moat** — l'ipotesi che avevo messo come concorrente e' falsa,
e per il prodotto e' la notizia buona della serata.
⇒ MA non e' piu' «passa solo il thai», come avevo scritto ieri: sulla classe
ENTITA' SOSTITUITA cadono TRE scritture, e due di esse — AR e HI — REGGEVANO
sulla negazione nel banco precedente (falsi semantici fermati a g=1.4 e 2.5).

🔑 LA CONSEGUENZA CHE CAMBIA LA PROPOSTA PER IL README: la matrice non e' una
lista di lingue, e' una tabella LINGUA x CLASSE DI FALSITA'. Sulle stesse
scritture il gate tiene su una classe e cede su un'altra::

                 numeri   negazione   entita' sostituita
    EN IT ZH JA KO  si        si             si
    AR              si        si             NO
    HI              si        si             NO
    TH              si        NO*            NO
    (*TH negazione: 1 caso ammesso a 99.87, 3 fermati — vedi
      ws3-il-thai-e-la-negazione-o-e-quella-frase.py)

⇒ «Misurato su ZH/JA/KO/AR/HI» sarebbe una riga di vetrina VERA E INGANNEVOLE:
vera sulla classe che ho misurato prima, falsa su questa.

═══ IL CONTROLLO CHE RENDE LEGGIBILE IL RESTO ═══
Nel banco a store unico comparivano `L3-supersession` e `L3-coexistence`: i casi
si vedevano fra loro. L3 AGGIUNGE quarantene, quindi le ammissioni dovrebbero
reggere a maggior ragione — ma «dovrebbe» non e' una misura. Rifatti i cinque
casi che passano, ciascuno in un PROCESSO e uno store VUOTO suoi::

    AR attributo   -> admitted     layer=L4-review
    TH attributo   -> admitted     layer=-
    HI attributo   -> admitted     layer=-
    TH nome        -> admitted     layer=-
    HI nome        -> admitted     layer=L4-review
    EN attributo   -> quarantined  layer=L4-grounding   <- controllo, stessa esecuzione

Tutti e cinque reggono, e il controllo EN si ferma. 📌 Su AR e HI il gate emette
`L4-review`: non e' silenzio totale, e' un segnale che non diventa veto.

Regime: porta pubblica `verimem remember --source`, store temporaneo vuoto,
FUORI pytest. PYTHONUTF8=1 per la STAMPA, non per il gate.
⚠️ Il banco qui sotto condivide UN solo store fra i casi: e' cosi' che e' stata
fatta la prima misura, e la ri-verifica a store separati e' quella riportata
sopra. Chi lo rifa' e vuole i layer puliti, lo lanci un caso per processo.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_entita_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (lingua, fonte, vero, falso ATTRIBUTO, fonte-nome, vero-nome, falso NOME)
CASI = [
    ("EN", "Report: the north warehouse measures 1800 square metres.",
     "The north warehouse measures 1800 square metres.",
     "The south warehouse measures 1800 square metres.",
     "Deed: the north warehouse was sold to Mr Anderson in March.",
     "The north warehouse was sold to Mr Anderson.",
     "The north warehouse was sold to Mr Baxter."),
    ("IT", "Rapporto: il magazzino nord misura 1800 metri quadrati.",
     "Il magazzino nord misura 1800 metri quadrati.",
     "Il magazzino sud misura 1800 metri quadrati.",
     "Atto: il magazzino nord e' stato venduto al signor Anselmi a marzo.",
     "Il magazzino nord e' stato venduto al signor Anselmi.",
     "Il magazzino nord e' stato venduto al signor Boveri."),
    ("ZH", "报告：北仓库面积为 1800 平方米。",
     "北仓库面积为 1800 平方米。", "南仓库面积为 1800 平方米。",
     "契约：北仓库于三月出售给了安德森先生。",
     "北仓库出售给了安德森先生。", "北仓库出售给了巴克斯特先生。"),
    ("JA", "報告：北倉庫の面積は 1800 平方メートルです。",
     "北倉庫の面積は 1800 平方メートルです。", "南倉庫の面積は 1800 平方メートルです。",
     "契約書：北倉庫は三月にアンダーソン氏に売却されました。",
     "北倉庫はアンダーソン氏に売却されました。", "北倉庫はバクスター氏に売却されました。"),
    ("KO", "보고서: 북쪽 창고의 면적은 1800 제곱미터입니다.",
     "북쪽 창고의 면적은 1800 제곱미터입니다.", "남쪽 창고의 면적은 1800 제곱미터입니다.",
     "계약서: 북쪽 창고는 삼월에 앤더슨 씨에게 매각되었습니다.",
     "북쪽 창고는 앤더슨 씨에게 매각되었습니다.", "북쪽 창고는 백스터 씨에게 매각되었습니다."),
    ("AR", "تقرير: مساحة المستودع الشمالي 1800 متر مربع.",
     "مساحة المستودع الشمالي 1800 متر مربع.", "مساحة المستودع الجنوبي 1800 متر مربع.",
     "عقد: تم بيع المستودع الشمالي إلى السيد أندرسون في مارس.",
     "تم بيع المستودع الشمالي إلى السيد أندرسون.",
     "تم بيع المستودع الشمالي إلى السيد باكستر."),
    ("TH", "รายงาน: คลังสินค้าทางเหนือมีพื้นที่ 1800 ตารางเมตร",
     "คลังสินค้าทางเหนือมีพื้นที่ 1800 ตารางเมตร",
     "คลังสินค้าทางใต้มีพื้นที่ 1800 ตารางเมตร",
     "สัญญา: คลังสินค้าทางเหนือถูกขายให้กับคุณสมชายเมื่อเดือนมีนาคม",
     "คลังสินค้าทางเหนือถูกขายให้กับคุณสมชาย",
     "คลังสินค้าทางเหนือถูกขายให้กับคุณสมศักดิ์"),
    ("HI", "रिपोर्ट: उत्तरी गोदाम का क्षेत्रफल 1800 वर्ग मीटर है।",
     "उत्तरी गोदाम का क्षेत्रफल 1800 वर्ग मीटर है।",
     "दक्षिणी गोदाम का क्षेत्रफल 1800 वर्ग मीटर है।",
     "अनुबंध: उत्तरी गोदाम मार्च में श्री एंडरसन को बेचा गया।",
     "उत्तरी गोदाम श्री एंडरसन को बेचा गया।",
     "उत्तरी गोदाम श्री बैक्स्टर को बेचा गया।"),
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
    return esito, (float(m.group(1)) if m else None), ("+".join(sorted(set(_L.findall(o)))) or "-")


def main_banco() -> None:
    print("%-4s %-16s %-12s %-12s %7s  %s"
          % ("lg", "caso", "atteso", "esito", "g", "layer"))
    passa_attr, passa_nome, veri = [], [], 0
    for lg, s1, v1, f_attr, s2, v2, f_nome in CASI:
        for nome, claim, src, atteso in (
                ("VERO attributo", v1, s1, "admitted"),
                ("falso ATTRIBUTO", f_attr, s1, "quarantined"),
                ("VERO nome", v2, s2, "admitted"),
                ("falso NOME", f_nome, s2, "quarantined")):
            e, g, layer = esegui(claim, src)
            giusto = (e == atteso)
            if nome.startswith("VERO") and giusto:
                veri += 1
            if nome == "falso ATTRIBUTO" and not giusto:
                passa_attr.append(lg)
            if nome == "falso NOME" and not giusto:
                passa_nome.append(lg)
            print("%-4s %-16s %-12s %-12s %7s  %-24s %s"
                  % (lg, nome, atteso, e, ("%.1f" % g) if g is not None else "-",
                     layer, "" if giusto else "<<< AMMESSA UNA FALSITA'"
                     if not nome.startswith("VERO") else "<<< VERO RIFIUTATO"))
        print()
    print("=" * 80)
    print("  VERI ammessi ................... %d/%d" % (veri, 2 * len(CASI)))
    print("  falso ATTRIBUTO passa in ....... %s" % (", ".join(passa_attr) or "nessuna"))
    print("  falso NOME PROPRIO passa in .... %s" % (", ".join(passa_nome) or "nessuna"))
    print()
    print("  Se EN o IT compaiono in una delle due righe, NON e' un difetto")
    print("  multilingue: e' un buco del moat che riguarda ogni utente.")


if __name__ == "__main__":
    main_banco()
