# -*- coding: utf-8 -*-
"""Le due classi thai che restavano a n=1. Completa la matrice.

Dopo le batterie del 26/08 la matrice era::

    classe                IT      EN      TH
    negazione            0/10    0/10    6/10
    entita' sostituita   1/10    2/10    (n=1)
    dettaglio aggiunto   8/10    9/10    (n=1)

Le due celle a n=1 non sono citabili — e' la stessa lezione che stamattina mi
ha fatto ritirare «la terza classe cade in italiano». Questo banco le chiude.

🔑 IL PRESIDIO SULLE MIE RESE, che qui e' piu' forte del solito: le dieci frasi
thai NON sono nuove. Sono le stesse del banco dei verbi
(`ws3-il-thai-a-batteria-e-il-verbo.py`), dove i VERI sono stati ammessi 10/10 —
cioe' il giudice le capisce, misurato. Cambia solo la falsita' che ci si
costruisce sopra. Un mio errore di resa avrebbe gia' dovuto manifestarsi li'.

La fonte qui e' la forma POSITIVA della stessa frase, perche' entrambe le classi
hanno bisogno di un fatto affermato::

    fonte     «บันทึก: <sogg>ได้รับการ<verbo>แล้ว»       (X e' stato <verbo>)
    vero      «<sogg>ได้รับการ<verbo>แล้ว»
    ENTITA'   «<ALTRO sogg>ได้รับการ<verbo>แล้ว»          il fatto attribuito ad altri
    DETTAGLIO «<sogg>ได้รับการ<verbo>แล้ว <complemento>»  un particolare non detto

⚖️ EN appaiato sulla stessa struttura: se cede anche l'inglese non e' il thai.
⛔ Nessun caso numerico: L4.1 ferma i numeri 8/8 e misurerebbe se stesso.

COSA DECIDE: se il thai cede su TUTTE E TRE le classi, il limite da dichiarare
non e' «il thai sbaglia sulle negazioni» ma «fuori da IT/EN non abbiamo una
garanzia», che e' una frase piu' semplice e piu' onesta.

MISURATO 26/08 — IN THAI PASSANO TUTTE E VENTI::

    falsita' ammesse  TH  entita     10/10      EN  entita      2/10
    falsita' ammesse  TH  dettaglio  10/10      EN  dettaglio   8/10
    VERI rifiutati    TH 0/10                   EN 2/10

① IL THAI NON HA NESSUNA GARANZIA: entita' sostituita e dettaglio aggiunto
passano entrambe 10 volte su 10, su tutti e dieci i verbi. Con la negazione a
6/10, il limite da dichiarare non e' «il thai sbaglia sulle negazioni»: e'
**fuori da IT/EN non c'e' garanzia**, che e' una frase piu' semplice e piu'
onesta di una matrice per lingua.
② E I VERI THAI SONO AMMESSI 10/10 — di nuovo. Il giudice capisce le frasi e
non trattiene nulla: non e' prudenza eccessiva, e' assenza di difesa.

🔑 ③ UN CONTROLLO DI RIPRODUCIBILITA' CHE NON AVEVO CERCATO, e vale piu' del
resto: la colonna EN di questo banco replica le batterie precedenti su fonti
COMPLETAMENTE DIVERSE — entita' 2/10 qui contro 2/10 nel banco dell'entita',
dettaglio 8/10 qui contro 9/10 nella batteria italiana. Due popolazioni
indipendenti, stessi numeri. ⇒ I numeri IT/EN non sono un artefatto delle mie
dieci fonti.
⚠️ ④ NOVITA' DA GUARDARE: in EN due VERI sono rifiutati (0 nelle batterie
precedenti). Sono sulla forma positiva «X was <participio>», che nelle altre
batterie non compariva. Non l'ho classificato e non lo accuso: lo lascio
scritto.

═══ LA MATRICE COMPLETA ═══
    classe                IT      EN      TH
    negazione            0/10    0/10    6/10
    entita' sostituita   1/10    2/10   10/10
    dettaglio aggiunto   8/10    9/10   10/10

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

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_th2_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (nome, sogg_TH, verbo_TH, ALTRO sogg_TH, complemento_TH,
#:         sogg_EN, part_EN, ALTRO sogg_EN, complemento_EN)
CASI = [
    ("rinnovare", "สัญญาเช่าคลังสินค้าทางเหนือ", "ต่ออายุ",
     "สัญญาเช่าคลังสินค้าทางใต้", "โดยฝ่ายกฎหมาย",
     "the north warehouse lease", "renewed",
     "the south warehouse lease", "by the legal department"),
    ("approvare", "คำขอเบิกจ่ายของแผนกขาย", "อนุมัติ",
     "คำขอเบิกจ่ายของแผนกจัดซื้อ", "ในที่ประชุมใหญ่",
     "the sales department refund request", "approved",
     "the purchasing department refund request", "at the general meeting"),
    ("firmare", "สัญญาจัดซื้อฉบับใหม่", "ลงนาม",
     "สัญญาจัดซื้อฉบับเดิม", "ต่อหน้าพยานสองคน",
     "the new procurement contract", "signed",
     "the previous procurement contract", "in front of two witnesses"),
    ("consegnare", "อุปกรณ์สำหรับสายการผลิตที่สาม", "ส่งมอบ",
     "อุปกรณ์สำหรับสายการผลิตที่ห้า", "โดยบริการจัดส่งด่วน",
     "the equipment for the third production line", "delivered",
     "the equipment for the fifth production line", "by express courier"),
    ("verificare", "รายงานการเงินประจำไตรมาส", "ตรวจสอบ",
     "รายงานการเงินประจำปี", "โดยผู้ตรวจสอบภายนอก",
     "the quarterly financial report", "audited",
     "the annual financial report", "by an external auditor"),
    ("pubblicare", "ผลการประเมินของคณะกรรมการ", "เผยแพร่",
     "ผลการประเมินของคณะทำงาน", "บนเว็บไซต์ทางการ",
     "the committee assessment results", "published",
     "the working group assessment results", "on the official website"),
    ("riparare", "ระบบทำความเย็นของอาคารกลาง", "ซ่อมแซม",
     "ระบบทำความเย็นของอาคารตะวันตก", "ในช่วงกลางคืน",
     "the central building cooling system", "repaired",
     "the west building cooling system", "during the night"),
    ("registrare", "คำร้องขอเข้าถึงเอกสาร", "บันทึก",
     "คำร้องขอสำเนาเอกสาร", "ผ่านไปรษณีย์รับรอง",
     "the document access request", "recorded",
     "the document copy request", "by certified post"),
    ("accettare", "ข้อเสนอของผู้จัดจำหน่ายรายที่สอง", "ยอมรับ",
     "ข้อเสนอของผู้จัดจำหน่ายรายที่สี่", "อย่างเป็นเอกฉันท์",
     "the second supplier proposal", "accepted",
     "the fourth supplier proposal", "unanimously"),
    ("completare", "การย้ายข้อมูลไปยังระบบใหม่", "ดำเนินการจนเสร็จ",
     "การย้ายข้อมูลไปยังระบบสำรอง", "ก่อนกำหนดการ",
     "the migration to the new system", "completed",
     "the migration to the backup system", "ahead of schedule"),
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
    print("%-12s %-3s %-10s %-12s %7s  %s"
          % ("caso", "lg", "classe", "esito", "g", "layer"))
    amm = {("TH", "entita"): [], ("TH", "dettaglio"): [],
           ("EN", "entita"): [], ("EN", "dettaglio"): []}
    veri_rif = {"TH": [], "EN": []}
    for (nome, s_th, v_th, alt_th, comp_th,
         s_en, p_en, alt_en, comp_en) in CASI:
        src_th = "บันทึก: %sได้รับการ%sแล้ว" % (s_th, v_th)
        src_en = "Note: %s was %s." % (s_en, p_en)
        prove = (
            ("TH", src_th,
             "%sได้รับการ%sแล้ว" % (s_th, v_th),
             "%sได้รับการ%sแล้ว" % (alt_th, v_th),
             "%sได้รับการ%sแล้ว %s" % (s_th, v_th, comp_th)),
            ("EN", src_en,
             "%s was %s." % (s_en.capitalize(), p_en),
             "%s was %s." % (alt_en.capitalize(), p_en),
             "%s was %s %s." % (s_en.capitalize(), p_en, comp_en)),
        )
        for lg, src, vero, f_ent, f_det in prove:
            e_v, g_v, l_v = esegui(vero, src)
            if e_v != "admitted":
                veri_rif[lg].append(nome)
            print("%-12s %-3s %-10s %-12s %7s  %-20s %s"
                  % (nome, lg, "VERO", e_v,
                     ("%.1f" % g_v) if g_v is not None else "-", l_v,
                     "" if e_v == "admitted" else "<<< VERO RIFIUTATO"))
            for classe, falso in (("entita", f_ent), ("dettaglio", f_det)):
                e_f, g_f, l_f = esegui(falso, src)
                if e_f != "quarantined":
                    amm[(lg, classe)].append(nome)
                print("%-12s %-3s %-10s %-12s %7s  %-20s %s"
                      % ("", lg, classe, e_f,
                         ("%.1f" % g_f) if g_f is not None else "-", l_f,
                         "" if e_f == "quarantined" else "<<< AMMESSA"))
        print()
    n = len(CASI)
    print("=" * 84)
    for lg in ("TH", "EN"):
        for classe in ("entita", "dettaglio"):
            print("  falsita' ammesse  %s  %-10s %2d/%d"
                  % (lg, classe, len(amm[(lg, classe)]), n))
    print("  VERI rifiutati    TH %d/%d   EN %d/%d"
          % (len(veri_rif["TH"]), n, len(veri_rif["EN"]), n))
    print()
    print("  entita' che passano in TH:    %s"
          % (", ".join(amm[("TH", "entita")]) or "nessuno"))
    print("  dettagli che passano in TH:   %s"
          % (", ".join(amm[("TH", "dettaglio")]) or "nessuno"))


if __name__ == "__main__":
    main_banco()
