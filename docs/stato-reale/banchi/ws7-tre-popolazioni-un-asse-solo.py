# -*- coding: utf-8 -*-
"""TRE POPOLAZIONI SULLO STESSO ASSE: quante frasi VERE il gate ferma?

PERCHE' ESISTE. Alle 19:24 @ws1 ha ristretto il suo reperto piu' citato («70% contro
0,6%») mostrando che i due numeri **confrontavano unita' diverse** — frasi contro
coppie. A unita' unica il suo verso si ribalta: prosa umana **11,9%**, nostro corpus
**55,5%**, sue frasi da contratto **70%**.

⇒ Io citavo quel reperto in due punti del registro come CONFERMA del mio contrasto
(«verbali d'ufficio fermati 8/10, nostri referti 0/6»). **La citazione cade**: il suo
asse e' l'ESPOSIZIONE a `event_index`, il mio sono i FATTI FERMATI dal gate. Due assi
diversi che sembravano rimare. Ho aperto una tensione e questo banco la chiude, dalla
mia parte: **le tre popolazioni sul MIO asse, misurate insieme.**

LE TRE POPOLAZIONI, e la regola che le rende confrontabili:
ogni frase e' **VERA rispetto alla propria fonte**, perche' e' **presa alla lettera**
dal documento che le fa da source. ⇒ Una frase letterale con la sua fonte accanto
**non ha alcuna ragione di essere fermata**: ogni stop e' un falso positivo puro.

  A. PROSA UMANA REALE   frasi estratte AUTOMATICAMENTE da README/CONTRIBUTING/
                         SECURITY (le stesse fonti di @ws1), blocchi di codice
                         esclusi. **Nessuna selezione mia**: prende le prime N che
                         passano il filtro, in ordine di file.
  B. NOSTRI REFERTI      frasi dall'uscita di un mio banco, con quell'uscita come fonte.
  C. VERBALI D'UFFICIO   le frasi di `LANT-32`, col verbale come fonte.

CONTROLLO CHE DEVE POTER FALLIRE: per ogni popolazione, una variante con **una cifra
alterata** deve essere FERMATA. Se passasse, il gate sarebbe spento su quella
popolazione e il conto dei falsi positivi non direbbe nulla.

    python docs/stato-reale/banchi/ws7-tre-popolazioni-un-asse-solo.py

Store TEMPORANEO, modello vero, FUORI da pytest.
⚠️ LIMITE noto e comune a tutti i miei banchi: la coda di revisione e' a ZERO, quindi
`REVIEW_BACKPRESSURE` non puo' scattare — sul corpus vero scatta (`LANT-40`).
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent.parent.parent
DOCS = ["README.md", "CONTRIBUTING.md", "SECURITY.md"]

#: una frase «utilizzabile»: abbastanza lunga da avere contenuto, non un titolo, non
#: una riga di lista/tabella, e con almeno una CIFRA (senza numeri L4.1 non ha nulla
#: da dire e il confronto misurerebbe solo gli L1).
def _frasi_dai_documenti(quante: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for nome in DOCS:
        f = RADICE / nome
        if not f.exists():
            continue
        testo = f.read_text(encoding="utf-8", errors="replace")
        # via i blocchi di codice: sono la parte che @ws1 esclude, e a ragione
        testo = re.sub(r"```.*?```", " ", testo, flags=re.S)
        testo = re.sub(r"`[^`]*`", " ", testo)
        for riga in testo.splitlines():
            r = riga.strip()
            if not r or r.startswith(("#", "|", ">", "-", "*", "+")) or len(r) < 60:
                continue
            for frase in re.split(r"(?<=[.!?])\s+", r):
                frase = frase.strip()
                if 60 <= len(frase) <= 220 and re.search(r"\d", frase):
                    out.append((frase, testo))
                    break
            if len(out) >= quante:
                return out
    return out


FONTE_REFERTO = """  === i miei referti, passati al gate (store temporaneo) ===
  OK  99.98 model_claim  Su cinque righe del log dei bloccati P1 nomina lo schermo 5 su 5.
  OK  99.47 model_claim  Lo span tenuto e' 314 caratteri su 5250 della fonte.
  OK  99.47 model_claim  Lo span non e' contiguo nella fonte.
  CONTROLLO (900 invece di 314): quarantined  retto
  => miei referti ammessi: 5/5"""

FONTE_VERBALE = (
    "Verbale della seduta del 14 marzo. La pratica numero 2214 e' stata verificata "
    "dall'ufficio tecnico. Il preventivo e' stato approvato dal consiglio con nove voti "
    "favorevoli. Il documento e' stato firmato dal presidente in data 14 marzo. Il guasto "
    "segnalato a gennaio e' stato risolto dalla ditta incaricata. La sede si trova a Verona. "
    "Il compenso pattuito e' di 3200 euro.")

REFERTI = [
    ("Lo span tenuto e' 314 caratteri su 5250 della fonte.", FONTE_REFERTO),
    ("Lo span non e' contiguo nella fonte.", FONTE_REFERTO),
    ("Su cinque righe del log dei bloccati P1 nomina lo schermo 5 su 5.", FONTE_REFERTO),
]
VERBALI = [
    ("La pratica numero 2214 e' stata verificata dall'ufficio tecnico.", FONTE_VERBALE),
    ("Il preventivo e' stato approvato dal consiglio con nove voti favorevoli.", FONTE_VERBALE),
    ("Il documento e' stato firmato dal presidente in data 14 marzo.", FONTE_VERBALE),
]


def _giro(Memory, radice: Path, nome: str, coppie: list[tuple[str, str]]) -> tuple[int, int, list]:
    mem = Memory(str(radice / f"{nome}.db"))
    fermate, dettagli = 0, []
    for i, (claim, fonte) in enumerate(coppie):
        ric = mem.add(claim, topic=f"{nome}/{i}", source=fonte, validate="full")
        st = str(ric.get("status"))
        if st == "quarantined":
            fermate += 1
            dettagli.append((float(ric.get("grounding_score") or -1),
                             list(ric.get("layers") or []), claim[:76]))
    # CONTROLLO: la stessa frase con una cifra alterata DEVE essere fermata
    claim0, fonte0 = coppie[0]
    alterato = re.sub(r"\d+", lambda m: str(int(m.group(0)) + 4321), claim0, count=1)
    ric = mem.add(alterato, topic=f"{nome}/controllo", source=fonte0, validate="full")
    ctrl_ok = str(ric.get("status")) == "quarantined"
    return fermate, len(coppie), [ctrl_ok, dettagli]


def main() -> int:
    umane = _frasi_dai_documenti(8)
    if len(umane) < 5:
        print(f"  NIENTE DA MISURARE: solo {len(umane)} frasi umane estratte, servono almeno 5")
        return 1
    print(f"  estratte {len(umane)} frasi umane da {DOCS} (blocchi di codice esclusi,")
    print("  nessuna selezione mia: le prime che passano il filtro, in ordine di file)\n")

    from verimem.client import Memory  # noqa: PLC0415
    radice = Path(tempfile.mkdtemp())

    risultati = {}
    for nome, coppie in (("umane", umane), ("referti", REFERTI), ("verbali", VERBALI)):
        f, n, (ctrl, det) = _giro(Memory, radice, nome, coppie)
        risultati[nome] = (f, n, ctrl)
        print(f"  == {nome.upper()}: fermate {f}/{n}   controllo (cifra alterata fermata): "
              f"{'retto' if ctrl else 'CADUTO'}")
        for g, layers, c in det:
            print(f"     🔴 {g:6.2f} {str(layers):26} {c}")

    print("\n  " + "=" * 76)
    print("  TRE POPOLAZIONI, UN ASSE SOLO — frasi VERE fermate dal gate")
    for nome, (f, n, ctrl) in risultati.items():
        stato = "" if ctrl else "   ⚠️ CONTROLLO CADUTO: qui il numero non significa nulla"
        print(f"    {nome:9} {f}/{n}  = {100*f/n:5.1f}%{stato}")
    print("  " + "=" * 76)
    if not all(c for _f, _n, c in risultati.values()):
        print("  ⚠️ Almeno un controllo e' caduto: il confronto NON e' leggibile.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
