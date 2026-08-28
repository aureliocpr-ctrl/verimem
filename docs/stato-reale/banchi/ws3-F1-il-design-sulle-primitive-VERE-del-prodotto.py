# -*- coding: utf-8 -*-
"""F1 · Il design regge sulle primitive VERE del prodotto, o solo sulle mie?

@ws5, nella sua review (banco `d9b39135`), ha eseguito i cinque passi **coi
pezzi veri del prodotto** — `extract_quantities`, `query_intent._STOP` — e ha
trovato due cose che la mia simulazione non poteva vedere, perche' la mia
simulazione usava **le mie regex e la mia stoplist**, entrambe piu' favorevoli.

⇒ e' la lezione di casa che tocca a me stavolta: **il livello a cui misuri
  decide il verdetto**, e la porta del prodotto batte il mio banco.

Questo banco rifa' la mia regola (compreso il **passo 2-bis** delle ancore
discriminanti, che @ws5 non poteva conoscere: e' arrivato a `b81966a0`, quattro
minuti prima del suo messaggio) **sulle primitive VERE**, e misura QUANTI dei
miei 22 casi sono ancora **esprimibili**.

CIO' CHE HO GIA' SONDATO A MANO, e che il banco ri-verifica:
    «La penale ... pari al 2% ...»              -> {('', 2.0)}
    «Art. 4 - La penale ... al 5% ...»          -> {('', 4.0), ('', 5.0)}
    «Il termine ... fissato al 12 marzo 2027»   -> set()
  ⇒ ① le PERCENTUALI escono SENZA unita' (@ws5 ③)
    ② il NUMERO DELL'ARTICOLO finisce nello stesso secchio delle percentuali
    ③ le DATE non escono affatto

LA PREDIZIONE, scritta prima di eseguire:
  · i 2 scambi su DATE diventano INESPRIMIBILI (nessun valore estratto)
  · i 2 scambi su PERCENTUALI restano esprimibili ma il passo 4 confronta
    valori con unita' '' — cioe' mescola percentuali e numeri d'articolo
  · i 6 scambi su mg / euro reggono
  · con `query_intent._STOP` come stoplist, almeno un caso cambia esito
    (@ws5 lo ha misurato sul suo: «il» come ancora)

CONDIZIONE DI FALSIFICAZIONE: se tutti e 22 i casi restano esprimibili e con lo
stesso esito, allora le primitive non sono un ostacolo e la mia simulazione
precedente era rappresentativa.

⚠️ NON E' LA CURA: nessun file di `verimem/` viene toccato. Legge tre funzioni
   del prodotto in sola lettura per misurarne il comportamento.

    python docs/stato-reale/banchi/ws3-F1-il-design-sulle-primitive-VERE-del-prodotto.py
"""

from __future__ import annotations

import re
import sys
import unicodedata

_FRASE = re.compile(r"(?<=[.;!?])\s+")

# la MIA stoplist della simulazione precedente, per il confronto a due regimi
_MIA_STOP = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da",
    "in", "con", "su", "per", "tra", "fra", "del", "dello", "della", "dei",
    "degli", "delle", "al", "allo", "alla", "ai", "agli", "alle", "dal",
    "dalla", "nel", "nella", "sul", "sulla", "e", "ed", "o", "che", "non",
    "e'", "essere", "sono", "art", "pari", "ogni", "come", "piu", "presente",
}


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# ⚠️ Difetto del MIO banco, trovato alla prima esecuzione (28/08 ~20:30) e
# corretto qui: passando all'estrattore del prodotto avevo smesso di togliere il
# token dell'UNITA' dalle ancore, cosi' «mg» finiva fra i soggetti e il caso
# VERO-p5 tornava OK invece di ASTIENITI. Non e' una colpa del design: e' mia, e
# la separo prima di attribuire alcunche'. Le unita' non sono soggetti.
_UNITA_TOK = {"mg", "ml", "kg", "euro", "eur", "gr", "grammi", "giorni",
              "mesi", "anni", "percento", "cento"}


def _ancore(t: str, stop: set[str]) -> set[str]:
    tok = re.findall(r"[a-zA-Zà-ùÀ-Ù']{2,}", t)
    return {_norm(x) for x in tok
            if _norm(x) not in stop and _norm(x) not in _UNITA_TOK}


def l43(claim: str, fonte: str, valori, stop: set[str]) -> tuple[str, str]:
    v_claim = valori(claim)
    if not v_claim:
        return "INESPRIMIBILE", "l'estrattore del prodotto non vede valori nel claim"
    v_fonte = valori(fonte)
    frasi = [f for f in _FRASE.split(fonte) if f.strip()]
    A = _ancore(claim, stop) & _ancore(fonte, stop)

    for uni, num in sorted(v_claim, key=lambda x: (x[0], x[1])):
        if (uni, num) not in v_fonte:
            return "L4.1", f"«{num} {uni or '(senza unita)'}» non e' nella fonte"
        if not A:
            return "ASTIENITI", "nessuna ancora del claim esiste nella fonte"
        cand = [f for f in frasi if any(u == uni for u, _n in valori(f))]
        occ: dict[str, int] = {}
        for f in cand:
            for a in _ancore(f, stop):
                occ[a] = occ.get(a, 0) + 1
        A_disc = {a for a in A if occ.get(a, 0) == 1}
        if not A_disc:
            return ("ASTIENITI", f"nessuna ancora discriminante: {sorted(A)[:5]} "
                                 f"compaiono in piu' frasi candidate")
        for f in frasi:
            if (uni, num) in valori(f) and A_disc & _ancore(f, stop):
                stessa = {n for u, n in valori(f) if u == uni}
                if len(stessa) >= 2:
                    break
                return "OK", f"ancora discriminante {sorted(A_disc & _ancore(f, stop))}"
        for f in frasi:
            if A_disc & _ancore(f, stop):
                altri = [(u, n) for u, n in valori(f) if u == uni and n != num]
                if altri:
                    return ("SEGNALA",
                            f"la fonte lega {sorted(A_disc & _ancore(f, stop))} a "
                            f"«{altri[0][1]} {uni or '(senza unita)'}»")
        return "ASTIENITI", f"la fonte tace sul valore in «{uni or '(senza unita)'}»"
    return "ASTIENITI", "nessun valore"


CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027. "
    "Art. 6 - Il termine per la contestazione dei vizi e' fissato al 30 aprile 2027. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
REFERTO = (
    "Terapia in atto. Il paziente assume metformina 850 mg due volte al giorno. "
    "Il ramipril e' prescritto a 5 mg al mattino. "
    "L'acido acetilsalicilico e' prescritto a 100 mg alla sera. "
    "Controllo previsto a tre mesi."
)
CASI = [
    ("SCAMBIO %",  CONTRATTO, "La penale per il ritardo e' pari al 5% dell'importo contrattuale.", "SEGNALA"),
    ("SCAMBIO %",  CONTRATTO, "La penale per difformita' qualitativa e' pari al 2% dell'importo contrattuale.", "SEGNALA"),
    ("SCAMBIO data", CONTRATTO, "Il termine di consegna e' fissato al 30 aprile 2027.", "SEGNALA"),
    ("SCAMBIO data", CONTRATTO, "Il termine per la contestazione dei vizi e' fissato al 12 marzo 2027.", "SEGNALA"),
    ("SCAMBIO eur", CONTRATTO, "La cauzione definitiva e' pari a 148000 euro.", "SEGNALA"),
    ("SCAMBIO eur", CONTRATTO, "L'importo contrattuale e' di 22000 euro.", "SEGNALA"),
    ("SCAMBIO mg",  REFERTO, "Il ramipril e' prescritto a 850 mg al mattino.", "SEGNALA"),
    ("SCAMBIO mg",  REFERTO, "Il paziente assume metformina 5 mg due volte al giorno.", "SEGNALA"),
    ("SCAMBIO mg",  REFERTO, "L'acido acetilsalicilico e' prescritto a 850 mg alla sera.", "SEGNALA"),
    ("SCAMBIO mg",  REFERTO, "Il paziente assume metformina 100 mg due volte al giorno.", "SEGNALA"),
    ("SCAMBIO mg",  REFERTO, "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.", "SEGNALA"),
    ("SCAMBIO mg",  REFERTO, "Il ramipril e' prescritto a 100 mg al mattino.", "SEGNALA"),
    ("CIFRA",      CONTRATTO, "L'importo contrattuale e' di 391000 euro.", "L4.1"),
    ("CIFRA",      REFERTO, "Il ramipril e' prescritto a 73 mg al mattino.", "L4.1"),
    ("VERO",       CONTRATTO, "La penale per il ritardo e' pari al 2% dell'importo contrattuale.", "OK"),
    ("VERO",       REFERTO, "Il ramipril e' prescritto a 5 mg al mattino.", "OK"),
    ("VERO",       CONTRATTO, "L'importo contrattuale e' di 148000 euro.", "OK"),
    ("VERO-p5",    "Il paziente assume metformina. Il dosaggio e' 850 mg.",
                   "Il paziente assume metformina 850 mg.", "ASTIENITI"),
]


def main() -> int:
    from verimem.quantity_match import extract_quantities  # noqa: PLC0415
    from verimem.query_intent import _STOP  # noqa: PLC0415

    def prod(t: str) -> set[tuple[str, float]]:
        return extract_quantities(t, come_fonte=True)

    print("  ⚠️ Nessun file di verimem/ toccato: leggo tre funzioni del prodotto.")
    print(f"  primitive del prodotto: extract_quantities · query_intent._STOP "
          f"({len(_STOP)} parole)")
    print("\n  [0] COSA VEDE L'ESTRATTORE DEL PRODOTTO (sonda)")
    for t in ["La penale per il ritardo e' pari al 2% dell'importo contrattuale.",
              "Art. 4 - La penale per difformita' qualitativa e' pari al 5%.",
              "Il termine di consegna e' fissato al 12 marzo 2027.",
              "Il ramipril e' prescritto a 5 mg al mattino."]:
        print(f"      {str(sorted(prod(t))):<34} <- {t[:52]}")

    regimi = [("MIA stoplist", _MIA_STOP), ("_STOP del prodotto", set(_STOP))]
    print(f"\n  {'famiglia':<14} {'atteso':<14} " +
          " ".join(f"{n:<22}" for n, _s in regimi))
    print("  " + "-" * 78)
    conta = {n: {"ok": 0, "inespr": 0} for n, _s in regimi}
    for fam, fonte, claim, atteso in CASI:
        col = []
        for nome, stop in regimi:
            e, _m = l43(claim, fonte, prod, stop)
            col.append(e)
            if e == atteso:
                conta[nome]["ok"] += 1
            if e == "INESPRIMIBILE":
                conta[nome]["inespr"] += 1
        print(f"  {fam:<14} {atteso:<14} " +
              " ".join(f"{c:<22}" for c in col) + f"  {claim[:34]}")

    print("\n  ══ RIEPILOGO ══")
    for nome, _s in regimi:
        c = conta[nome]
        print(f"     {nome:<20} torna su {c['ok']}/{len(CASI)}"
              f"   ·   INESPRIMIBILI: {c['inespr']}")

    print("\n  ⚠️ LIMITI: e' una simulazione fuori dal prodotto — il gate vero ha")
    print("     clausole, span troncati e un ordine dei layer che qui non ci sono.")
    print("     La segmentazione in frasi resta la mia regex, non del prodotto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
