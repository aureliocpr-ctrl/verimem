# -*- coding: utf-8 -*-
"""F1 · REGOLA v2 — le risposte alle R di @ws5, misurate contro la v1.

@ws5 ha fatto la validazione CIECA (32 casi mai visti da me, banco `a75ced2f`):
**15 scambi su 16 colti** — e tutti col **termine di testa condiviso**, il caso
difficile — ma **3 falsi positivi su 16 veri**, poi ristretti a **2** col
regime di segmentazione B. Il mio criterio pre-registrato («>1 ⇒ RESPINTO»)
SCATTA. Qui rispondo alle sue R e misuro se le risposte funzionano.

────────────────────────────────────────────────────────────────────────────
LE RISPOSTE, e la prima e' un'accettazione senza discussione

R1 · «la cura del passo 3 produce falsi positivi» — ACCETTATA INTEGRALMENTE.
     Avevo scritto che una finestra ambigua «cade ai passi 4/5, fallendo in
     sicurezza». E' FALSO e la sua diagnosi e' esatta: **il passo 4 e' proprio
     quello che trova l'altro valore della stessa frase**, quindi su un claim
     VERO cadere li' significa fallire VERSO il falso positivo. «Cade ai passi
     4/5» nasconde DUE esiti opposti, uno sicuro e uno no.
     ⇒ v2: finestra ambigua ⇒ **ASTIENITI**, senza passare dal passo 4.

R2 · «identificativi» — ACCETTATA, e la cura e' GIA' IN CASA: la distinzione e'
     **posizionale, non lessicale** — `vicinato_del_valore.py:36-37`: «un
     identificativo SEGUE il suo sostantivo ('ordine 77'), una quantita' lo
     PRECEDE ('3 anni')», dichiarata su IT/EN/DE/FR/ES. E' la nostra classe
     ricorrente «esiste gia' e non e' collegato?».
     ⇒ v2: se il valore SEGUE il suo sostantivo in claim e fonte, non e' una
       quantita': **ASTIENITI**.

R3 · «elenco puntato, forse colpa della mia segmentazione» — MISURATA DA LEI:
     A/B sul corpus vero, split anche su NEWLINE e «;» ⇒ falsi allarmi
     65,7% -> 31,2% **e gli scambi colti restano 15/16**. Curare la
     segmentazione **non costa sensibilita'**. ⇒ v2 adotta il regime B.

LE TRE GUARDIE del suo banco corpus-vero (`3f961371`, 3030 giudicabili):
  G1 valore SENZA unita' ⇒ il passo 4 non accoppia          -61,8%
  G2 il claim cita ANCHE l'altro valore ⇒ non e' uno scambio -27,6%
  G3 stesso numero a precisione diversa (97.6 vs 97.5968)    -2,5%
  ⇒ 65,7% -> 5,3%.
  📌 G1 cura ANCHE il mio falso positivo di `8157a777` (il VERO «penale = 2%»
     segnalato): le percentuali escono `('', 2.0)` e i numeri d'articolo
     `('', 3.0)`, nello stesso secchio. ⇒ **finche' `extract_quantities` non
     da' un'unita' alle percentuali, L4.3 semplicemente NON le tratta.**

IL VINCOLO PAVIMENTO di @ws6, e non e' piu' cautelativo: la coda di revisione
e' a **1057 contro soglia 500**, ed entra **cinque volte** piu' veloce di
quanto esce. ⇒ **L4.3 nasce AVVISO, non veto**: un nuovo veto alimenta una coda
che nessuno drena, e «held for review» diventa «silently dropped» (lo dice il
prodotto stesso, `review_queue.py:190`).

CIO' CHE MI ASPETTO, scritto prima di eseguire:
  · i 2 falsi positivi di @ws5 (canone/deposito · ordine 77) -> spariscono
  · gli scambi colti -> INVARIATI
  · il mio VERO «penale = 2%» -> non piu' segnalato (guardia G1)
  · le percentuali -> diventano intrattabili (G1): e' un COSTO, non un bug

CONDIZIONE DI FALSIFICAZIONE: se in v2 anche un solo scambio smette di essere
segnalato, le risposte costano sensibilita' e vanno ridiscusse.

⚠️ Simulazione FUORI dal prodotto: nessun file di `verimem/` toccato.

    python docs/stato-reale/banchi/ws3-F1-regola-v2-le-risposte-alle-R-misurate.py
"""

from __future__ import annotations

import re
import sys
import unicodedata

_FRASE_A = re.compile(r"(?<=[.;!?])\s+")               # v1: la mia
_FRASE_B = re.compile(r"(?<=[.;!?])\s+|\n+|(?<=;)\s*")  # v2: regime B di @ws5
_UNITA_TOK = {"mg", "ml", "kg", "euro", "eur", "gr", "grammi", "giorni",
              "mesi", "anni", "percento", "cento"}
_MIA_STOP = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da",
    "in", "con", "su", "per", "tra", "fra", "del", "dello", "della", "dei",
    "degli", "delle", "al", "allo", "alla", "ai", "agli", "alle", "dal",
    "dalla", "nel", "nella", "sul", "sulla", "e", "ed", "o", "che", "non",
    "e'", "essere", "sono", "art", "pari", "ogni", "come", "piu", "presente",
    "risulta", "stato",
}


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _ancore(t: str) -> set[str]:
    tok = re.findall(r"[a-zA-Zà-ùÀ-Ù']{2,}", t)
    return {_norm(x) for x in tok
            if _norm(x) not in _MIA_STOP and _norm(x) not in _UNITA_TOK}


def _identificativo(testo: str, valore: float) -> bool:
    """R2 — regola POSIZIONALE del prodotto (vicinato_del_valore.py:36-37):
    un identificativo SEGUE il suo sostantivo, una quantita' lo PRECEDE."""
    for m in re.finditer(r"(?<![\d.,])%s(?![\d.,])" % re.escape(
            str(int(valore)) if valore == int(valore) else str(valore)), testo):
        prima = testo[max(0, m.start() - 40):m.start()].strip().split()
        dopo = testo[m.end():m.end() + 40].strip().split()
        p = _norm(prima[-1]) if prima else ""
        d = _norm(dopo[0]) if dopo else ""
        # quantita': il sostantivo/unita' SEGUE il numero  («3 anni», «5 mg»)
        if d and d not in _MIA_STOP:
            return False
        # identificativo: il sostantivo PRECEDE il numero  («ordine 77»)
        if p and p not in _MIA_STOP:
            return True
    return False


def regola(claim: str, fonte: str, valori, *, v2: bool) -> tuple[str, str]:
    v_claim = valori(claim)
    if not v_claim:
        return "INESPRIMIBILE", "l'estrattore non vede valori nel claim"
    v_fonte = valori(fonte)
    frasi = [f.strip() for f in (_FRASE_B if v2 else _FRASE_A).split(fonte) if f and f.strip()]
    A = _ancore(claim) & _ancore(fonte)

    for uni, num in sorted(v_claim, key=lambda x: (x[0], x[1])):
        if (uni, num) not in v_fonte:
            return "L4.1", f"«{num} {uni or '(nuda)'}» non e' nella fonte"
        if v2 and not uni:
            return "ASTIENITI", f"G1: «{num}» non porta unita' — non accoppiabile"
        if v2 and _identificativo(claim, num) and _identificativo(fonte, num):
            return "ASTIENITI", f"R2: «{num}» SEGUE il suo sostantivo: identificativo"
        if not A:
            return "ASTIENITI", "nessuna ancora del claim esiste nella fonte"
        cand = [f for f in frasi if any(u == uni for u, _n in valori(f))]
        occ: dict[str, int] = {}
        for f in cand:
            for a in _ancore(f):
                occ[a] = occ.get(a, 0) + 1
        A_disc = {a for a in A if occ.get(a, 0) == 1}
        if not A_disc:
            return "ASTIENITI", f"nessuna ancora discriminante fra {sorted(A)[:4]}"
        for f in frasi:
            if (uni, num) in valori(f) and A_disc & _ancore(f):
                stessa = {n for u, n in valori(f) if u == uni}
                if len(stessa) >= 2:
                    if v2:
                        # R1: la finestra ambigua ASTIENE. Cadere al passo 4
                        # significherebbe trovare l'altro valore DELLA STESSA
                        # FRASE e segnalare un VERO. Diagnosi di @ws5, accettata.
                        return "ASTIENITI", ("R1: finestra ambigua (due valori "
                                             "stessa unita'): non passo al passo 4")
                    break
                return "OK", f"ancora discriminante {sorted(A_disc & _ancore(f))}"
        for f in frasi:
            if A_disc & _ancore(f):
                altri = [(u, n) for u, n in valori(f) if u == uni and n != num]
                if not altri:
                    continue
                if v2 and any((u2, n2) in v_claim for u2, n2 in altri):
                    return "ASTIENITI", "G2: il claim cita ANCHE l'altro valore"
                if v2 and any(abs(n2 - num) / max(abs(num), 1e-9) < 0.01
                              for _u2, n2 in altri):
                    return "ASTIENITI", "G3: stesso numero a precisione diversa"
                return "SEGNALA", (f"la fonte lega {sorted(A_disc & _ancore(f))} a "
                                   f"«{altri[0][1]} {uni or '(nuda)'}»")
        return "ASTIENITI", f"la fonte tace sul valore in «{uni or '(nuda)'}»"
    return "ASTIENITI", "nessun valore"


CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
REFERTO = (
    "Terapia in atto. Il paziente assume metformina 850 mg due volte al giorno. "
    "Il ramipril e' prescritto a 5 mg al mattino. "
    "L'acido acetilsalicilico e' prescritto a 100 mg alla sera."
)
CASI = [
    # (famiglia, fonte, claim, atteso in v2)
    ("SCAMBIO", CONTRATTO, "La cauzione definitiva e' pari a 148000 euro.", "SEGNALA"),
    ("SCAMBIO", CONTRATTO, "L'importo contrattuale e' di 22000 euro.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "Il ramipril e' prescritto a 850 mg al mattino.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "Il paziente assume metformina 5 mg due volte al giorno.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "L'acido acetilsalicilico e' prescritto a 850 mg alla sera.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "Il paziente assume metformina 100 mg due volte al giorno.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.", "SEGNALA"),
    ("SCAMBIO", REFERTO, "Il ramipril e' prescritto a 100 mg al mattino.", "SEGNALA"),
    ("CIFRA",   CONTRATTO, "L'importo contrattuale e' di 391000 euro.", "L4.1"),
    ("CIFRA",   REFERTO, "Il ramipril e' prescritto a 73 mg al mattino.", "L4.1"),
    ("VERO",    REFERTO, "Il ramipril e' prescritto a 5 mg al mattino.", "OK"),
    ("VERO",    CONTRATTO, "L'importo contrattuale e' di 148000 euro.", "OK"),
    # 🔴 il MIO falso positivo di 8157a777 (percentuale + numero d'articolo)
    ("VERO-mio", CONTRATTO,
     "La penale per il ritardo e' pari al 2% dell'importo contrattuale.", "ASTIENITI"),
    # 🔴 i DUE falsi positivi di @ws5 (validazione cieca a75ced2f)
    ("VERO-ws5-1", "Il canone e' di 1200 euro e il deposito e' di 2400 euro.",
     "Il deposito e' di 2400 euro.", "ASTIENITI"),
    ("VERO-ws5-2", "L'ordine 77 risulta evaso. L'ordine 88 e' in attesa.",
     "L'ordine 77 e' stato evaso.", "ASTIENITI"),
    # il test del passo 5
    ("VERO-p5", "Il paziente assume metformina. Il dosaggio e' 850 mg.",
     "Il paziente assume metformina 850 mg.", "ASTIENITI"),
]


def main() -> int:
    from verimem.quantity_match import extract_quantities  # noqa: PLC0415

    def prod(t: str) -> set[tuple[str, float]]:
        return extract_quantities(t, come_fonte=True)

    print("  ⚠️ Simulazione FUORI dal prodotto: nessun file di verimem/ toccato.")
    print("     Primitive vere: extract_quantities. Segmentazione: mia (v1) /")
    print("     regime B di @ws5, newline e ';' (v2).\n")
    print(f"  {'famiglia':<12} {'atteso v2':<12} {'v1':<14} {'v2':<14} claim")
    print("  " + "-" * 92)
    ok1 = ok2 = 0
    seg1 = seg2 = 0
    fp1 = fp2 = 0
    for fam, fonte, claim, atteso in CASI:
        e1, _m1 = regola(claim, fonte, prod, v2=False)
        e2, m2 = regola(claim, fonte, prod, v2=True)
        ok1 += (e1 == atteso)
        ok2 += (e2 == atteso)
        if fam == "SCAMBIO":
            seg1 += (e1 == "SEGNALA")
            seg2 += (e2 == "SEGNALA")
        if fam.startswith("VERO"):
            fp1 += (e1 == "SEGNALA")
            fp2 += (e2 == "SEGNALA")
        print(f"  {fam:<12} {atteso:<12} {e1:<14} {e2:<14} {claim[:34]}")
        if fam.startswith("VERO") and e1 == "SEGNALA" and e2 != "SEGNALA":
            print(f"  {'':<40} └─ v2: {m2[:60]}")

    n_sc = sum(1 for f, _s, _c, _a in CASI if f == "SCAMBIO")
    n_ve = sum(1 for f, _s, _c, _a in CASI if f.startswith("VERO"))
    print(f"\n  ══ v1 CONTRO v2 ══")
    print(f"     scambi SEGNALATI     v1 {seg1}/{n_sc}      v2 {seg2}/{n_sc}")
    print(f"     FALSI POSITIVI       v1 {fp1}/{n_ve}       v2 {fp2}/{n_ve}")
    print(f"     esiti attesi         v1 {ok1}/{len(CASI)}     v2 {ok2}/{len(CASI)}")

    print("\n  ══ VERDETTO ══")
    if seg2 < seg1:
        print("     FALSIFICATA: v2 perde sensibilita' sugli scambi ⇒ le risposte")
        print("     alle R costano, e vanno ridiscusse prima della firma.")
    elif fp2 == 0 and seg2 == seg1:
        print("     RETTA: v2 azzera i falsi positivi SENZA perdere un solo scambio.")
        print("     Le tre R e le tre guardie fanno cio' che dicono, sui casi noti.")
    else:
        print(f"     PARZIALE: falsi positivi {fp1} -> {fp2}, scambi {seg1} -> {seg2}.")

    print("\n  ⚠️ LIMITI: sono i casi GIA' NOTI (miei + i due FP di @ws5). Una v2")
    print("     tarata sui casi che l'hanno rotta NON e' validata: serve una")
    print("     SECONDA cieca su casi nuovi. E le percentuali sono ora")
    print("     INTRATTABILI per costruzione (G1): e' un COSTO dichiarato, non un")
    print("     bug — sparisce solo curando extract_quantities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
