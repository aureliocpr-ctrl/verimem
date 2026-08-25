# -*- coding: utf-8 -*-
"""Su scrittura NON latina non esisteva NESSUNA misura del giudice. Questa e' la prima.

Perche' serviva. Il giudice del moat e' `cross-encoder/nli-deberta-v3-base`
(gate_config.json), vocab_size 128100 — un DeBERTa-v3 inglese. In casa la sua
separazione e' misurata solo su alfabeto latino: `grounding_gate.py:522-531`
(18/07) dice 97-99 sugli entailment e ~0.6 sui confab «in EN/IT/FR/ES alike».
I layer LESSICALI invece sono noti ciechi fuori di li' (`_has_negator` False su
KO/TH/HI/TR). ⇒ Il buco non era «funziona male»: era che nessuno avesse guardato.

═══ IL DISEGNO, a DUE ASSI — ed e' la parte che conta ═══
Ogni fonte porta DUE falsita' di natura diversa, e la differenza fra le due
colonne e' l'informazione:

  falsita' NUMERICA   1800 -> 2500. Le cifre restano cifre in ogni scrittura,
                      quindi L4.1 (deterministico) dovrebbe prenderla OVUNQUE.
                      ⇒ E' il CONTROLLO CHE IL BANCO FUNZIONI: se cade anche
                      questa, il caso non e' arrivato al gate e il resto del
                      numero non significa niente.
  falsita' SEMANTICA  afferma il contrario della fonte senza toccare i numeri.
                      Nessun layer lessicale la vede fuori da EN/IT.
                      ⇒ Solo il CE puo' prenderla: E' LA MISURA VERA.

Piu' un VERO per lingua (citazione della fonte): senza l'altra popolazione un
gate che rifiuta tutto sembrerebbe perfetto.

⚠️ IL LIMITE, dichiarato prima dei numeri e non dopo: le rese non latine sono
mie e non sono state riviste da un parlante. Un esito «il gate sbaglia» potrebbe
essere «la mia frase e' sgrammaticata». ⇒ Per questo EN gira NELLA STESSA
esecuzione: se EN funziona e le altre no, la differenza e' attribuibile alla
scrittura; se sbaglia anche EN, il difetto e' nel banco. E per questo le frasi
sono elementari e ancorate a cifre e nomi propri, che sopravvivono a una resa
mediocre.

⛔ QUESTO BANCO NON DICE se il prodotto «regge» in coreano. Dice se il giudice
distingue vero da falso su frasi elementari in quelle scritture — che e' il
minimo, e finora era ignoto.

═══ MISURATO 25/08, e ribalta la preoccupazione da cui ero partita ═══

    VERI ammessi ................ 7/7
    falsi NUMERICI fermati ...... 7/7    <- il controllo: i casi ARRIVANO al gate
    falsi SEMANTICI fermati ..... 6/7    <- passa SOLO il thai

Il CE regge su ZH, JA, KO, AR, HI: cinque scritture non latine, falsi semantici
fermati con g fra 0.9 e 2.5. ⇒ «il giudice va sostituito perche' e' inglese» e'
FALSO come l'avevo formulata, e questo indebolisce la mia stessa proposta.

⇒ MA IL THAI NON E' UN BUCO CIECO: E' UN ERRORE CONFIDENTE. La ricevuta piena::

    grounding_score=99.86940002441406  judged=True  layers=[]  status=model_claim

Il claim afferma il CONTRARIO della fonte (il contratto d'affitto «e' stato
rinnovato» contro «non e' stato rinnovato») e il CE gli da' 99.87 — non un
punteggio basso, la quasi certezza che la fonte lo sostenga.
🔑 E' molto peggio di un punteggio basso: un g basso produce una quarantena,
cioe' un falso allarme recuperabile. 99.87 produce un'AMMISSIONE — una falsita'
che torna come verita', l'unica cosa che il prodotto promette di non fare.

🔑 IL MECCANISMO, e il doppio asse lo isola: sulla STESSA fonte thai il falso
NUMERICO prende g=0.2, il piu' basso di tutto il banco. Lo stesso giudice, la
stessa frase, due esiti opposti ⇒ non e' che «non capisce il thai»: non vede il
NEGATORE. In thai non ci sono spazi fra le parole e «ไม่ได้» finisce dentro una
sequenza che un vocabolario inglese frammenta (ipotesi sul perche', NON
misurata: il fatto misurato e' l'esito).
🔗 E chiude un cerchio: F-NEG — la negazione falsa — e' la classe che in IT e EN
risulta chiusa 0/8 in due regimi (banco ws3-quale-famiglia-chiude-la-classe).
In thai la stessa classe e' APERTA, e non di poco.

⛔ n=1 LINGUA SU 6, e non generalizzo: non dico «il CE cade sulle scritture
senza spazi», che sarebbe una tesi con un solo caso. Dico che ESISTE una
scrittura in cui ammette una falsita' a 99.87. Per una promessa della forma
«un fatto che la fonte non sostiene non ti torna come verita'», una prova di
esistenza basta a renderla falsa fuori dalle lingue misurate.
📌 APERTO: il thai era gia' un mio aperto congelato dal 13/08, per un'altra via.
Ci arriva un secondo metodo dodici giorni dopo, ed e' la sola voce che regge.

Regime: porta pubblica `verimem remember --source`, store temporaneo vuoto,
FUORI pytest (sotto pytest l'embedder e' uno stub SHA-256). PYTHONUTF8=1 per
la STAMPA delle scritture, non per il gate.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_nonlatino_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (lingua, fonte, vero, falso NUMERICO, falso SEMANTICO)
CASI = [
    ("EN-rif",
     "Site report: the north warehouse measures 1800 square metres. The lease was not renewed.",
     "The north warehouse measures 1800 square metres.",
     "The north warehouse measures 2500 square metres.",
     "The lease for the north warehouse was renewed."),
    ("ZH",
     "现场报告：北仓库面积为 1800 平方米。租约没有续签。",
     "北仓库面积为 1800 平方米。",
     "北仓库面积为 2500 平方米。",
     "北仓库的租约已经续签。"),
    ("JA",
     "現地報告：北倉庫の面積は 1800 平方メートルです。賃貸契約は更新されませんでした。",
     "北倉庫の面積は 1800 平方メートルです。",
     "北倉庫の面積は 2500 平方メートルです。",
     "北倉庫の賃貸契約は更新されました。"),
    ("KO",
     "현장 보고서: 북쪽 창고의 면적은 1800 제곱미터입니다. 임대 계약은 갱신되지 않았습니다.",
     "북쪽 창고의 면적은 1800 제곱미터입니다.",
     "북쪽 창고의 면적은 2500 제곱미터입니다.",
     "북쪽 창고의 임대 계약이 갱신되었습니다."),
    ("AR",
     "تقرير الموقع: مساحة المستودع الشمالي 1800 متر مربع. لم يتم تجديد عقد الإيجار.",
     "مساحة المستودع الشمالي 1800 متر مربع.",
     "مساحة المستودع الشمالي 2500 متر مربع.",
     "تم تجديد عقد إيجار المستودع الشمالي."),
    ("TH",
     "รายงานพื้นที่: คลังสินค้าทางเหนือมีพื้นที่ 1800 ตารางเมตร สัญญาเช่าไม่ได้รับการต่ออายุ",
     "คลังสินค้าทางเหนือมีพื้นที่ 1800 ตารางเมตร",
     "คลังสินค้าทางเหนือมีพื้นที่ 2500 ตารางเมตร",
     "สัญญาเช่าคลังสินค้าทางเหนือได้รับการต่ออายุแล้ว"),
    ("HI",
     "स्थल रिपोर्ट: उत्तरी गोदाम का क्षेत्रफल 1800 वर्ग मीटर है। पट्टे का नवीनीकरण नहीं किया गया।",
     "उत्तरी गोदाम का क्षेत्रफल 1800 वर्ग मीटर है।",
     "उत्तरी गोदाम का क्षेत्रफल 2500 वर्ग मीटर है।",
     "उत्तरी गोदाम के पट्टे का नवीनीकरण कर दिया गया।"),
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
    print("%-8s %-10s %-6s %-12s %7s  %s"
          % ("lingua", "caso", "atteso", "esito", "g", "layer"))
    ok_num = ok_sem = ok_vero = 0
    for lang, src, vero, f_num, f_sem in CASI:
        for nome, claim, atteso in (("VERO", vero, "admitted"),
                                    ("falso NUM", f_num, "quarantined"),
                                    ("falso SEM", f_sem, "quarantined")):
            esito, g, layer = esegui(claim, src)
            giusto = (esito == atteso)
            if giusto:
                if nome == "VERO":
                    ok_vero += 1
                elif nome == "falso NUM":
                    ok_num += 1
                else:
                    ok_sem += 1
            print("%-8s %-10s %-6s %-12s %7s  %-28s %s"
                  % (lang, nome, "amm" if atteso == "admitted" else "quar", esito,
                     ("%.1f" % g) if g is not None else "-", layer,
                     "" if giusto else "<<< SBAGLIATO"))
        print()
    n = len(CASI)
    print("=" * 74)
    print("  VERI ammessi ................. %d/%d" % (ok_vero, n))
    print("  falsi NUMERICI fermati ....... %d/%d   <- controllo: il caso arriva al gate?"
          % (ok_num, n))
    print("  falsi SEMANTICI fermati ...... %d/%d   <- LA MISURA: solo il CE puo' prenderli"
          % (ok_sem, n))
    print("  (EN-rif e' nella stessa esecuzione: se sbaglia lui, e' il banco)")


if __name__ == "__main__":
    main_banco()
