"""LIVELLO: solo regex e `subject_of` — nessun gate, nessun modello, nessuna scrittura.

MURO 1, fase 2: le SUBORDINATE. Quanta superficie hanno nel corpus vivo, e che
cosa succede ai pezzi se lo splitter le spezza.

    python docs/stato-reale/banchi/ws3-muro1-fase2-le-subordinate.py

⚡ COSTO ZERO. Store di Aurelio in SOLA LETTURA. Sotto i 60 s.

━━ DA DOVE VIENE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il residuo dichiarato dal lead (a05dd7a6d6fa2458): il caso P3 «Dopo che il
tecnico ha collaudato l'impianto, la funzionalita' e' verificata» non si spezza
sulle coordinate, e la self-claim in coda passa. La letteratura (docs/ricerca/
2026-09-04 e 2026-09-05) non tratta le subordinate come classe: la risposta
implicita e' decontestualizzare, cioe' dare a ogni pezzo un soggetto.

Due domande, in ordine:
  ① SUPERFICIE: quanti fatti del corpus hanno una subordinata temporale/causale/
     condizionale? E quanti di questi hanno un completamento in coda (la forma
     del difetto)? Senza il denominatore, «le subordinate sono un residuo» e'
     un'opinione.
  ② FORMA DEI PEZZI: se si spezza ANCHE sulle subordinate, i pezzi che escono
     hanno un soggetto oppure no? E' la condizione perche' quello split non
     peggiori il danno collaterale misurato ieri.

━━ PREDIZIONE, depositata sul canale PRIMA (fc8b697a4d90ce14, 20:55) ━━━━━━━━━━
    T4 spezzare sulle subordinate produce pezzi SENZA soggetto piu' spesso che
       spezzare sulle coordinate: la frazione e' >= 2x. 🔴 muore se e' uguale o
       minore: allora le subordinate non sono peggio delle coordinate e il
       residuo del lead si cura con lo stesso splitter.
Il perche' della predizione: la subordinata italiana porta spesso il soggetto
nel verbo («Dopo che ha collaudato…»), e il pezzo che resta e' un verbo nudo.

━━ CIO' CHE NON DECIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se la superficie ① e' piccola, il residuo e' reale ma raro, e la cura puo'
aspettare. Se e' grande, la cura dello splitter non basta e serve un
decompositore che capisca la sintassi (parser o LLM), come dice la letteratura.
"""
from __future__ import annotations

import pathlib
import re
import sqlite3
import sys

ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")
sys.path.insert(0, str(ALBERO))

from verimem.subject_extract import subject_of  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"

_COORD = re.compile(r"\s*(?:,\s*ed?\s+|\s+ed?\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
# subordinate temporali, causali, condizionali, concessive — italiano e inglese
_SUB = re.compile(
    r"\s*(?:,\s*)?\b(?:dopo che|prima che|quando|mentre|perche'|perché|poiche'|poiché|"
    r"siccome|sebbene|benche'|benché|anche se|se|finche'|finché|"
    r"after|before|when|while|because|since|although|though|if|until)\b\s+", re.I)
# un completamento in coda: participio di chiusura nell'ultimo pezzo
_COMPLETAMENTO = re.compile(
    r"\b(verificat[oaie]|completat[oaie]|finit[oaie]|concluso|conclus[aie]|terminat[oaie]|"
    r"collaudat[oaie]|testat[oaie]|chius[oaie]|risolt[oaie]|verified|completed|done|"
    r"finished|tested|fixed|resolved|closed)\b", re.I)


def pezzi(testo: str, coord: re.Pattern[str]) -> list[str]:
    return [p.strip(" .,") for p in coord.split(testo) if p and len(p.split()) >= 3]


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL "
            "AND proposition IS NOT NULL") if r[0]]
    finally:
        con.close()
    tot = len(righe)

    con_sub = [t for t in righe if _SUB.search(t)]
    coda = [t for t in con_sub if _COMPLETAMENTO.search(pezzi(t, _SUB)[-1] if pezzi(t, _SUB) else t)]
    print(f"① SUPERFICIE delle subordinate nel corpus vivo ({tot} fatti)")
    print(f"   con almeno una subordinata           : {len(con_sub)}  ({100 * len(con_sub) / tot:.1f}%)")
    print(f"   di questi, con un completamento in coda: {len(coda)}  ({100 * len(coda) / tot:.1f}% del corpus)")
    print("   esempi con completamento in coda:")
    for t in coda[:5]:
        print(f"     · «{t[:100].replace(chr(10), ' ')}…»")

    def frazione_nudi(testi: list[str], coord: re.Pattern[str]) -> tuple[int, int]:
        nudi = totali = 0
        for t in testi:
            ps = pezzi(t, coord)
            if len(ps) < 2:
                continue
            # il PRIMO pezzo tiene il soggetto per costruzione: si guardano gli altri
            for p in ps[1:]:
                totali += 1
                nudi += not subject_of(p)
        return nudi, totali

    n_c, t_c = frazione_nudi(righe, _COORD)
    n_s, t_s = frazione_nudi(con_sub, _SUB)
    f_c = n_c / max(1, t_c)
    f_s = n_s / max(1, t_s)
    print("\n② FORMA DEI PEZZI dopo lo split (pezzi successivi al primo)")
    print(f"   split sulle COORDINATE  : pezzi {t_c:5d}  senza soggetto {n_c:5d}  = {100 * f_c:.1f}%")
    print(f"   split sulle SUBORDINATE : pezzi {t_s:5d}  senza soggetto {n_s:5d}  = {100 * f_s:.1f}%")
    rapporto = f_s / max(1e-9, f_c)
    print(f"   rapporto subordinate/coordinate: {rapporto:.2f}x")
    print(f"   ⇒ T4 (>= 2x) {'REGGE' if rapporto >= 2.0 else '🔴 FALSIFICATA'}")
    print("\n   esempi di pezzi nudi da subordinata:")
    k = 0
    for t in con_sub:
        for p in pezzi(t, _SUB)[1:]:
            if not subject_of(p) and k < 6:
                print(f"     · «{p[:70]}»   ← «{t[:45].replace(chr(10), ' ')}…»")
                k += 1


if __name__ == "__main__":
    main()
