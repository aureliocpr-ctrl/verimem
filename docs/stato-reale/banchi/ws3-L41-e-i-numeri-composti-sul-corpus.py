"""L4.1 e i numeri COMPOSTI, misurato sul corpus (store in SOLA LETTURA, nessun
giudice): quanti fatti con fonte hanno un valore che L4.1 dice assente, e in
quanti di questi l'assenza e' FALSA perche' il claim scrive un PREFISSO di un
numero composto della fonte («10:29:36» contro «10:29:36.847243800», «15:38»
letto come 15 e 38, «0.484» contro «0.48470836877822876», «98.86» contro
«98.86549377441406»): parsing asimmetrico o troncamento, non un numero inventato.

Versioni del righello, dichiarate: (1) 14:38, «assente contenuto in un composto»
per sottostringa: 71/484 — sovracontava («20» dentro «2026-08-10»). (2) 14:39,
prefisso al confine: 27/484 — sovracontava ancora: «0 righe» contro la versione
«0.7.0», «returncode 1» contro «1.26.0», «20 passed» contro l'ora «20:04:48»: un
intero nudo non e' la stessa grandezza di un pezzo di versione o di orario.
(3) questa: un assente e' spiegato solo se (a) e' un pezzo di un COMPOSTO scritto
nel claim (con separatore) che e' prefisso di un composto della fonte, oppure
(b) e' esso stesso un DECIMALE che e' prefisso di un decimale piu' lungo della
fonte. Gli interi nudi non si spiegano mai (stima contro la cura).

PREDIZIONI (depositate prima di eseguire, 06/09 14:43):
  P-C2'' fra i 484 fatti che L4.1 fermerebbe, le false assenze sono fra 12 e 24;
  P-C3'' la forma piu' frequente e' l'orario (hh:mm[:ss] con frazione o parsing
         asimmetrico), poi il decimale troncato.
Argomento 1: il worktree da cui importare verimem.
"""
import pathlib
import re
import sqlite3
import sys
from collections import Counter

QUI = pathlib.Path(__file__).resolve().parent
WT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else QUI.parents[2]
sys.path.insert(0, str(WT))
import verimem  # noqa: E402

print("IMPORT DA", verimem.__file__)
from verimem.valore_non_nella_fonte import valori_non_nella_fonte  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
righe = con.execute(
    "SELECT id, proposition, grounding_span FROM facts WHERE superseded_by IS NULL "
    "AND proposition IS NOT NULL AND grounding_span IS NOT NULL AND grounding_span <> ''"
).fetchall()
con.close()
print(f"fatti con fonte (span) nello store: {len(righe)}")

_COMPOSTO = re.compile(r"\d+(?:[:/.,-]\d+)+")
_DECIMALE = re.compile(r"\d+[.,]\d+")


def forma(comp: str) -> str:
    if ":" in comp:
        return "orario"
    if comp.count(".") >= 2 or comp.count("-") >= 2 or "/" in comp:
        return "versione-o-data"
    return "decimale"


def prefisso_di(corto: str, lungo: str) -> bool:
    """«corto» e' un prefisso di «lungo» al confine giusto: dopo di lui viene un
    separatore (10:29:36 | .847) oppure altre cifre di un decimale (0.484 | 70…)."""
    if corto == lungo or not lungo.startswith(corto):
        return False
    resto = lungo[len(corto):]
    return resto[0] in ":./,-" or (resto[0].isdigit() and ("." in corto or "," in corto))


def spiegazioni(prop: str, span: str, assenti) -> list[str | None]:
    comp_fonte = [m.group() for m in _COMPOSTO.finditer(span)] + [m.group() for m in _DECIMALE.finditer(span)]
    comp_claim = [m.group() for m in _COMPOSTO.finditer(prop)]
    spiegati: dict[str, str] = {}
    for cc in comp_claim:  # (a) un composto del claim, prefisso di uno della fonte
        for sc in comp_fonte:
            if cc == sc or prefisso_di(cc, sc):
                for pezzo in re.split(r"[:/.,-]", cc):
                    spiegati[pezzo] = sc
                spiegati[cc] = sc
    out = []
    for a in assenti:
        t = (a.testo or "").strip()
        if t in spiegati:
            out.append(spiegati[t])
        elif ("." in t or "," in t) and any(prefisso_di(t, sc) for sc in comp_fonte):  # (b)
            out.append(next(sc for sc in comp_fonte if prefisso_di(t, sc)))
        else:
            out.append(None)
    return out


con_assenti = tutti = almeno = 0
forme = Counter()
esempi = []
for fid, prop, span in righe:
    try:
        assenti = valori_non_nella_fonte(prop, span)
    except Exception as e:  # noqa: BLE001 — il banco conta, non cura
        print("errore su", fid, type(e).__name__)
        continue
    if not assenti:
        continue
    con_assenti += 1
    sp = spiegazioni(prop, span, assenti)
    n_sp = sum(s is not None for s in sp)
    if n_sp:
        almeno += 1
        for s in sp:
            if s:
                forme[forma(s)] += 1
    if n_sp == len(assenti):
        tutti += 1
        if len(esempi) < 30:
            esempi.append((fid[:12], [a.testo for a in assenti], sorted({s for s in sp if s}), prop[:78]))

n = len(righe)
print(f"\nfatti con almeno un valore assente (L4.1 scatterebbe): {con_assenti}/{n} = {100 * con_assenti / n:.1f}%")
if con_assenti:
    print(f"  FALSA ASSENZA (tutti gli assenti spiegati da un composto o decimale troncato): {tutti}/{con_assenti} = "
          f"{100 * tutti / con_assenti:.1f}% = {100 * tutti / n:.2f}% dei fatti con fonte  P-C2'' 12-24: "
          f"{'REGGE' if 12 <= tutti <= 24 else 'FALSIFICATA'}")
    print(f"  con almeno un assente spiegato: {almeno}/{con_assenti}")
print(f"  forme: {forme.most_common()}  P-C3'': {'REGGE' if forme and forme.most_common(1)[0][0] == 'orario' else 'FALSIFICATA'}")
print("\nTUTTE le false assenze (da leggere una per una):")
for e in esempi:
    print(f"  {e[0]} assenti={e[1]} fonte={e[2]} «{e[3]}»")
