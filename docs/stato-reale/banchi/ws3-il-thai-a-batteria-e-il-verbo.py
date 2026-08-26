# -*- coding: utf-8 -*-
"""Il thai a 99.87 e' l'ultimo mio numero a n=1. E l'ipotesi superstite era «il verbo».

Storia, perche' serve a leggere il disegno:
  25/08  misurato UN caso thai di negazione AMMESSO con grounding 99.87 — la
         fonte dice «il contratto NON e' stato rinnovato», il claim dice che lo
         e' stato, e il gate lo ammette con quasi-certezza.
  25/08  due mie diagnosi cadute: «e' il negatore che non vede» (falso: altri
         tre casi thai di negazione sono FERMATI) e «e' la fonte multi-frase»
         (falso: con e senza contorno, quarantined g=4.9 e g=4.4).
  26/08  l'unica differenza superstite fra il caso ammesso e uno fermato di
         struttura IDENTICA era il VERBO: ต่ออายุ (rinnovare) contro อนุมัติ
         (approvare). Con due casi non era una tesi.
  26/08  e la batteria sui dettagli ha mostrato che un caso per cella produce
         aneddoti: avevo pescato l'unico tipo che l'inglese fermasse e ci avevo
         letto «EN regge».

⇒ Questo banco fa DUE cose insieme:
   ① da' il TASSO della negazione in thai su dieci casi, che oggi non esiste
     (il thai circola come «controesempio noto» avendo n=1);
   ② TESTA l'ipotesi del verbo tenendo la struttura FISSA e variando solo
     quello: «X ไม่ได้รับการ<VERBO>» -> «X ได้รับการ<VERBO>แล้ว».
     Se cade sempre lo stesso verbo, l'ipotesi lessicale ha una gamba; se i
     fallimenti sono sparsi, cade anche quella e resta il tasso.

⚖️ Ogni caso porta il suo VERO, e qui il controllo e' piu' importante del solito:
le rese thai sono mie e la struttura e' ripetitiva, quindi un mio errore
sistematico si propagherebbe a tutti e dieci. Il VERO lo intercetta — se il
vero e' ammesso, la frase e' comprensibile al giudice.
🔑 EN appaiato sulla stessa struttura: se anche l'inglese cede sugli stessi
casi, non e' il thai.
⛔ Nessun caso numerico: L4.1 ferma i numeri 8 lingue su 8 e misurerebbe se
stesso, non il giudice.

MISURATO 26/08 — IL TASSO ESISTE, E IL THAI NON ERA UN ANEDDOTO::

    falsita' AMMESSE   TH  6/10   EN  0/10
    VERI rifiutati     TH  0/10   EN  0/10
    verbi che passano in TH: rinnovare, firmare, consegnare, verificare,
                             riparare, completare
    verbi che passano in EN: nessuno

① IL TASSO: 6 su 10, contro 0 su 10 in inglese a struttura identica. La classe
NEGAZIONE — quella che in IT/EN e' 0/10 su dieci casi ciascuna — in thai cede
su piu' della meta'. Il caso singolo a 99.87 del 25/08 non era una frase
sfortunata: era la punta di un tasso.
② L'IPOTESI DEL VERBO aveva la direzione giusta e la taglia sbagliata.
«rinnovare» (ต่ออายุ) E' fra quelli che passano, coerente col caso originale.
Ma passano anche firmare, consegnare, verificare, riparare, completare: sei
verbi, non uno. ⇒ Non e' «quel verbo». E' che il verbo CONTA — quattro su dieci
reggono — senza che una regola lessicale su un verbo spieghi niente.
③ I VERI THAI SONO AMMESSI 10/10, ed e' il controllo che rende il numero
utilizzabile: le rese sono mie, ma il giudice le capisce. Non e' che non
comprenda il thai; e' che in sei casi su dieci non vede la negazione.
④ EN 0/10 NELLA STESSA STRUTTURA: non e' il disegno del banco, non e' la
struttura ripetitiva, non e' la mia forma. E' la lingua.

═══ COSA CAMBIA NEL QUADRO, ed e' la parte che tocca il README ═══
    classe                IT      EN      TH
    negazione            0/10    0/10    6/10
    entita' sostituita   1/10    2/10    (n=1, non misurata)
    dettaglio aggiunto   8/10    9/10    (n=1, non misurata)

La tesi «il gate prende cio' che la fonte CONTRADDICE e manca cio' che TACE»
regge su IT/EN. In thai cede anche la contraddizione. ⇒ **La garanzia sulle
contraddizioni — l'unica dichiarabile — e' IT/EN-only, e adesso ha un
controesempio misurato invece che un aneddoto.**

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

os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp(prefix="ws3_thbatt_")
os.environ["ENGRAM_DATA_DIR"] = os.environ["HIPPO_DATA_DIR"]
os.environ["HIPPO_RERANK_PRELOAD"] = "0"

from verimem.cli import main  # noqa: E402

#: (verbo, soggetto_TH, verbo_TH, soggetto_EN, verbo_EN_passato, verbo_EN_part)
#: struttura TH:  «บันทึก: <sogg>ไม่ได้รับการ<verbo>»  ->  «<sogg>ได้รับการ<verbo>แล้ว»
#: struttura EN:  «Note: <subj> was not <part>.»        ->  «<subj> was <part>.»
VERBI = [
    ("rinnovare",  "สัญญาเช่าคลังสินค้าทางเหนือ", "ต่ออายุ",
     "the north warehouse lease", "renewed"),
    ("approvare",  "คำขอเบิกจ่ายของแผนกขาย", "อนุมัติ",
     "the sales department refund request", "approved"),
    ("firmare",    "สัญญาจัดซื้อฉบับใหม่", "ลงนาม",
     "the new procurement contract", "signed"),
    ("consegnare", "อุปกรณ์สำหรับสายการผลิตที่สาม", "ส่งมอบ",
     "the equipment for the third production line", "delivered"),
    ("verificare", "รายงานการเงินประจำไตรมาส", "ตรวจสอบ",
     "the quarterly financial report", "audited"),
    ("pubblicare", "ผลการประเมินของคณะกรรมการ", "เผยแพร่",
     "the committee assessment results", "published"),
    ("riparare",   "ระบบทำความเย็นของอาคารกลาง", "ซ่อมแซม",
     "the central building cooling system", "repaired"),
    ("registrare", "คำร้องขอเข้าถึงเอกสาร", "บันทึก",
     "the document access request", "recorded"),
    ("accettare",  "ข้อเสนอของผู้จัดจำหน่ายรายที่สอง", "ยอมรับ",
     "the second supplier proposal", "accepted"),
    ("completare", "การย้ายข้อมูลไปยังระบบใหม่", "ดำเนินการจนเสร็จ",
     "the migration to the new system", "completed"),
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
    print("%-12s %-3s %-6s %-12s %7s  %s"
          % ("verbo", "lg", "caso", "esito", "g", "layer"))
    passa = {"TH": [], "EN": []}
    veri_rif = {"TH": [], "EN": []}
    for (nome, sog_th, v_th, sog_en, v_en) in VERBI:
        src_th = "บันทึก: %sไม่ได้รับการ%s" % (sog_th, v_th)
        vero_th = "%sไม่ได้รับการ%s" % (sog_th, v_th)
        falso_th = "%sได้รับการ%sแล้ว" % (sog_th, v_th)
        src_en = "Note: %s was not %s." % (sog_en, v_en)
        vero_en = "%s was not %s." % (sog_en.capitalize(), v_en)
        falso_en = "%s was %s." % (sog_en.capitalize(), v_en)
        for lg, src, vero, falso in (("TH", src_th, vero_th, falso_th),
                                     ("EN", src_en, vero_en, falso_en)):
            e_v, g_v, l_v = esegui(vero, src)
            if e_v != "admitted":
                veri_rif[lg].append(nome)
            e_f, g_f, l_f = esegui(falso, src)
            if e_f != "quarantined":
                passa[lg].append(nome)
            print("%-12s %-3s %-6s %-12s %7s  %-22s %s"
                  % (nome, lg, "VERO", e_v,
                     ("%.1f" % g_v) if g_v is not None else "-", l_v,
                     "" if e_v == "admitted" else "<<< VERO RIFIUTATO"))
            print("%-12s %-3s %-6s %-12s %7s  %-22s %s"
                  % ("", lg, "falso", e_f,
                     ("%.1f" % g_f) if g_f is not None else "-", l_f,
                     "" if e_f == "quarantined" else "<<< FALSITA' AMMESSA"))
        print()
    n = len(VERBI)
    print("=" * 84)
    print("  falsita' AMMESSE   TH %2d/%d   EN %2d/%d"
          % (len(passa["TH"]), n, len(passa["EN"]), n))
    print("  VERI rifiutati     TH %2d/%d   EN %2d/%d"
          % (len(veri_rif["TH"]), n, len(veri_rif["EN"]), n))
    print()
    print("  verbi che passano in TH: %s" % (", ".join(passa["TH"]) or "nessuno"))
    print("  verbi che passano in EN: %s" % (", ".join(passa["EN"]) or "nessuno"))
    print("  VERI rifiutati in TH:    %s" % (", ".join(veri_rif["TH"]) or "nessuno"))
    print()
    print("  Se «rinnovare» e' fra i verbi che passano e gli altri no,")
    print("  l'ipotesi lessicale ha una gamba. Se i fallimenti sono sparsi,")
    print("  cade anche quella e resta il TASSO, che e' cio' che mancava.")


if __name__ == "__main__":
    main_banco()
