"""T17 — la MISURA prima della cura: quanti avvisi L4.2 toglie ciascuna regola, sulla popolazione intera.

Le quattro giunture lette in verimem/vicinato_del_valore.py (cella RED
tests/test_l42_avvisa_falsamente_sugli_output_di_programma.py, 46ed1a8f) danno
quattro regole candidate, e ognuna si misura DA SOLA e poi insieme:
  A  INCROCIO dei lati: le parole non grammaticali accanto al numero nel claim
     (prima e dopo) contro quelle nella fonte (prima e dopo): se una coincide,
     e' la stessa grandezza. Oggi si confrontano solo lati omologhi.
  B  STESSA RIGA: la fonte e' output di programma, ETICHETTA: valore; il
     vicinato si prende sulla riga del numero (tutte le parole non
     grammaticali della riga), non sull'ultima parola prima e la prima dopo,
     che oltrepassano il fine riga («…: 249 ⏎ primi 3»).
  C  COMPOSTO INTERO: se il numero del claim sta in un composto (03:27,
     2026-09-06, 2.14.0, 3/40) e quel composto compare tale e quale nella
     fonte, e' la stessa grandezza: tace.
  D  PUNTO FINALE: «esce 2.» — il numero seguito dal punto e poi fine/spazio
     va trovato nel claim (oggi il lookahead lo esclude e il criterio scatta
     a vuoto, con «(nessuna parola accanto)»).
Il modulo NON viene toccato: le regole sono reimplementate qui, sopra
`_intorno`/`extract_quantities` importati dal prodotto, e si applicano SOLO ai
casi in cui L4.2 oggi avvisa (una regola puo' solo TOGLIERE avvisi: se l'avviso
era vero, e' un vero perso della cura, e i presidi lo misurano).

Popolazione: i fatti vivi con `grounding_span` (la fonte intera non e'
conservata, M6: e' la stessa approssimazione del banco di casa
quali-parole-la-ricevuta-mostra-come-grandezza.py). Presidi: i riusi VERI dei
test (14 valvole/14 operai · 7 corsie/7 tecnici · EN line 3 / 22 days) devono
ancora scattare; le riformulazioni e «2 s»/«elapsed 2 s» devono tacere.

PREDIZIONI depositate in questo commit PRIMA di eseguire:
  P-T1  L4.2 oggi avvisa su almeno il 40% dei fatti con span (W7-80 diceva
        49,8%; Iris e Nadia «quasi ogni fatto»). Sotto il 25% l'allarme era
        locale alle fonti di stanotte.
  P-T2  la regola C da sola (composti) toglie almeno il 25% degli avvisi:
        orari, date e versioni sono la forma piu' comune delle nostre fonti.
  P-T3  A+B+C+D insieme tolgono almeno il 60% degli avvisi, e i presidi
        restano tutti (3 scattano, 2 tacciono). Se restano sopra il 60% degli
        avvisi, la classe «output di programma» non e' la maggioranza e la
        cura va ripensata; se cade un presidio, la regola che lo spegne non
        entra.
Store in sola lettura (mode=ro). Nessun modello. Secondi.
"""
from __future__ import annotations

import re
import sqlite3
import sys

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
_PAROLA = re.compile(r"[^\W\d_]+", re.UNICODE)
_COMPOSTO = re.compile(r"\d[\d:./-]*\d")

PRESIDI_SCATTANO = [
    ("Ci sono 14 valvole.", "Relazione: sono stati assunti 14 operai nel trimestre."),
    ("Il magazzino ha 7 corsie.", "Relazione: sono stati formati 7 tecnici."),
    ("Line 3 processed 22 orders.", "Report: the plant produced 850 frames. Line 3 ran for 22 days."),
]
PRESIDI_TACCIONO = [
    ("Sono stati assunti 14 operai.", "Relazione: sono stati assunti 14 operai nel trimestre."),
    ("Il comando ha richiesto 2 s.", "elapsed 2 s"),
]
FALSI_T17 = [
    ("Il comando esce 2 stampando Usage.", "EXIT=2\nUsage: verimem [OPTIONS]"),
    ("Il comando esce 2.", "EXIT=2"),
    ("The command exits 2.", "EXIT=2"),
    ("Il commit ebc2bf74 risulta delle 03:27 del 2026-09-06.",
     "ebc2bf74 2026-09-06 03:27 test della promozione: la cella diventa un presidio"),
    ("La funzione _list_tools_unfiltered restituisce 249 strumenti.",
     "STRUMENTI ESPOSTI A RUNTIME: 249\nprimi 3: ['sandbox_exec', 'hippo_run_task']"),
]


def _occorrenze(testo: str, valore: float, punto_finale: bool) -> list[re.Match]:
    intero = int(valore) if float(valore).is_integer() else valore
    coda = r"(?![\d,]|\.(?=\d))" if punto_finale else r"(?![\d.,])"
    return list(re.finditer(rf"(?<![\d.,]){re.escape(str(intero))}{coda}", testo))


def vicinato(testo: str, valore: float, *, stessa_riga: bool, punto_finale: bool,
             grammatica: frozenset[str]) -> tuple[set[str], set[str]]:
    """Come `_intorno`, con le due varianti B e D accendibili."""
    dopo: set[str] = set()
    prima: set[str] = set()
    for m in _occorrenze(testo, valore, punto_finale):
        if stessa_riga:
            inizio = testo.rfind("\n", 0, m.start()) + 1
            fine = testo.find("\n", m.end())
            fine = len(testo) if fine < 0 else fine
            dopo |= {t.casefold() for t in _PAROLA.findall(testo[m.end():fine]) if t.casefold() not in grammatica}
            prima |= {t.casefold() for t in _PAROLA.findall(testo[inizio:m.start()]) if t.casefold() not in grammatica}
        else:
            d = _PAROLA.findall(testo[m.end():m.end() + 40])
            if d:
                dopo.add(d[0].casefold())
            p = _PAROLA.findall(testo[max(0, m.start() - 40):m.start()])
            if p:
                prima.add(p[-1].casefold())
    return dopo, prima


def composti(testo: str) -> set[str]:
    return {c for c in _COMPOSTO.findall(testo) if not c.isdigit()}


def avvisa(claim: str, fonte: str, regole: str, grammatica: frozenset[str], extract) -> bool:
    """True se, con le regole accese, L4.2 avviserebbe su almeno un valore."""
    if not claim or not fonte:
        return False
    comp_fonte = composti(fonte) if "C" in regole else set()
    for _u, valore in extract(claim):
        if "C" in regole:
            intero = str(int(valore)) if float(valore).is_integer() else str(valore)
            if any(re.search(rf"(?<!\d){re.escape(intero)}(?!\d)", c) for c in comp_fonte
                   if c in claim):
                continue
        cd, cp = vicinato(claim, valore, stessa_riga="B" in regole, punto_finale="D" in regole, grammatica=grammatica)
        fd, fp = vicinato(fonte, valore, stessa_riga="B" in regole, punto_finale="D" in regole, grammatica=grammatica)
        if not fd and not fp:
            continue
        if cd & fd or cp & fp:
            continue
        if "A" in regole and (cd | cp) & (fd | fp):
            continue
        return True
    return False


def main() -> int:
    sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
    from verimem.quantity_match import extract_quantities
    from verimem.vicinato_del_valore import _GRAMMATICA, valori_riusati_da_altro_contesto

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT proposition, grounding_span FROM facts WHERE superseded_by IS NULL "
        "AND grounding_span IS NOT NULL AND grounding_span <> ''").fetchall()
    print(f"fatti vivi con span: {len(righe)}")

    # [0] il righello riproduce il prodotto quando tutte le regole sono spente
    oggi_prodotto = [bool(valori_riusati_da_altro_contesto(p or "", s or "")) for p, s in righe]
    oggi_mio = [avvisa(p or "", s or "", "", _GRAMMATICA, extract_quantities) for p, s in righe]
    disaccordi = sum(1 for a, b in zip(oggi_prodotto, oggi_mio) if a != b)
    n_avvisi = sum(oggi_prodotto)
    print(f"[0] riproduzione a regole spente: {disaccordi} disaccordi su {len(righe)} "
          f"({'REGGE' if disaccordi <= len(righe) * 0.01 else '🔴 il righello non riproduce il prodotto: NESSUN VERDETTO'})")
    if disaccordi > len(righe) * 0.01:
        return 1
    quota = n_avvisi / len(righe)
    print(f"P-T1 L4.2 oggi avvisa su {n_avvisi}/{len(righe)} = {quota:.1%}  "
          f"{'REGGE (>= 40%)' if quota >= 0.40 else ('🔴 FALSIFICATA (< 25%)' if quota < 0.25 else 'indeciso')}")

    print("\nregola     avvisi rimasti   tolti   presidi (3 scattano / 2 tacciono)   i 5 falsi di T17 taciuti")
    esiti = {}
    for regole in ("A", "B", "C", "D", "AB", "ABC", "ABCD"):
        rimasti = sum(1 for (p, s), o in zip(righe, oggi_prodotto) if o and avvisa(p or "", s or "", regole, _GRAMMATICA, extract_quantities))
        sc = sum(1 for c, f in PRESIDI_SCATTANO if avvisa(c, f, regole, _GRAMMATICA, extract_quantities))
        ta = sum(1 for c, f in PRESIDI_TACCIONO if not avvisa(c, f, regole, _GRAMMATICA, extract_quantities))
        falsi = sum(1 for c, f in FALSI_T17 if not avvisa(c, f, regole, _GRAMMATICA, extract_quantities))
        esiti[regole] = (rimasti, sc, ta, falsi)
        print(f"{regole:8s} {rimasti:8d}/{n_avvisi:<6d} {1 - rimasti / n_avvisi:6.1%}        {sc}/3 · {ta}/2                          {falsi}/5")
    tolti_c = 1 - esiti["C"][0] / n_avvisi
    print(f"\nP-T2 la sola C toglie {tolti_c:.1%}  {'REGGE (>= 25%)' if tolti_c >= 0.25 else '🔴 FALSIFICATA'}")
    r, sc, ta, falsi = esiti["ABCD"]
    tolti = 1 - r / n_avvisi
    presidi_ok = sc == 3 and ta == 2
    print(f"P-T3 A+B+C+D toglie {tolti:.1%}, presidi {sc}/3 scattano e {ta}/2 tacciono, falsi T17 taciuti {falsi}/5  "
          f"{'REGGE' if tolti >= 0.60 and presidi_ok else ('🔴 FALSIFICATA' if (tolti < 0.40 or not presidi_ok) else 'indeciso')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
