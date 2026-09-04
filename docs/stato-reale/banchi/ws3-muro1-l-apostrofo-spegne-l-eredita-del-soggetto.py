"""LIVELLO: la porta vera `Memory.add(ground=False)` per il verdetto, la regex nuda
per la diagnosi. Nessun modello, nessuno slot.

MURO 1: perche' la decomposizione ferma un fatto vero — e se curare una `\\b`
basta a non fermarlo piu'.

    python docs/stato-reale/banchi/ws3-muro1-l-apostrofo-spegne-l-eredita-del-soggetto.py

⚡ COSTO ZERO (~2 min di scritture su store temporaneo). Store di Aurelio: SOLA LETTURA.

━━ COME CI SONO ARRIVATO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Con la regex corretta dal lead (`ed?`, msg ce8c16cef134e99a) il caso R4 finalmente
si spezza, e il danno sulle 15 passa da 2/10 a 3/10 — come avevo predetto. Ma il
pezzo che cade esce cosi':

    «Il comando warmup e' iniziato alle 14:50:24 ed e' finito alle 14:53:19.»
      -> «Il comando warmup e' iniziato alle 14:50:24.»   passa
      -> «E' finito alle 14:53:19.»                        FERMATO  [L1.13]

**senza il soggetto**, che invece lo splitter dovrebbe ereditare (e' la cura che
il lead ha preso da FActScore: i fatti atomici sono auto-contenuti). Non e' che
l'eredita' abbia sbagliato soggetto: non e' proprio scattata.

━━ LA CAUSA, misurata e non dedotta ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
La guardia e' `^(ha|è|e'|sono|...)\\b`. Dopo `e'` quel `\\b` **non puo' accendersi
mai**: l'apostrofo non e' un carattere di parola e lo spazio che segue nemmeno,
quindi li' non c'e' nessun confine. Con `(?=\\s|$)` al posto di `\\b` si accende.

    pezzo                              con \\b (oggi)   con (?=\\s|$)
    e' finito alle 14:53:19                 no            MATCH   <- diverge
    è finito alle 14:53:19                MATCH           MATCH
    e' stato depositato alle 14:30          no            MATCH   <- diverge
    ha firmato il verbale                 MATCH           MATCH

⇒ e' un difetto che colpisce **solo l'italiano scritto in ASCII** — cioe' la
  forma che usiamo in tutto il corpus, dove «è» si scrive «e'». I pezzi che
  cominciano con «e' …» restano completamenti nudi, ed e' esattamente la forma
  che L1.13 ferma.

━━ PREDIZIONE, scritta prima di eseguire ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Q4 con la guardia corretta il danno torna da 3/10 a 2/10, perche' il pezzo
       diventa «Il comando warmup e' finito alle 14:53:19», che ha la stessa
       forma della frase intera che oggi passa.
    🔴 muore se resta 3/10: allora L1.13 ferma quel claim anche col soggetto, la
    cura di una `\\b` non basta, e il problema non e' la decomposizione ma cosa
    L1.13 considera evidenza. Sarebbe il risultato piu' utile dei due.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import tempfile

ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")
sys.path.insert(0, str(ALBERO))

import verimem  # noqa: E402
from verimem.client import Memory  # noqa: E402

QUINDICI = ALBERO / "docs/stato-reale/banchi/ws7-le-quindici-liberate-tornano-fermate.json"
COORD = re.compile(r"\s*(?:,\s*ed?\s+|\s+ed?\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
VERBI = r"(ha|è|e'|sono|hanno|era|fu|has|is|are|was|signed|tested|were)"
CON_B = re.compile(rf"^{VERBI}\b", re.I)          # oggi
CURATA = re.compile(rf"^{VERBI}(?=\s|$)", re.I)   # la proposta


def claim_atomici(testo: str, guardia: re.Pattern[str]) -> list[str]:
    """Lo splitter del lead: cambia SOLO la guardia del verbo iniziale."""
    try:
        from verimem.subject_extract import subject_of
    except Exception:  # noqa: BLE001
        subject_of = None
    pezzi = [p.strip(" .") for p in COORD.split(testo) if p and len(p.split()) >= 3]
    out: list[str] = []
    soggetto = ""
    for p in pezzi:
        if guardia.match(p) and soggetto:
            p = f"{soggetto} {p[0].lower() + p[1:]}"
        else:
            s = subject_of(p) if subject_of else ""
            if not s:
                m_ = re.match(rf"^(.*?)\s+{VERBI}\b", p, re.I)
                s = m_.group(1) if m_ else ""
            soggetto = s.strip() or soggetto
        out.append(p[0].upper() + p[1:] + ".")
    return out or [testo]


def main() -> None:
    print("IMPORT DA", verimem.__file__, "\n")
    print("① LA DIAGNOSI, sulla regex nuda:")
    for c in ("e' finito alle 14:53:19", "è finito alle 14:53:19",
              "ha firmato il verbale", "e' stato depositato alle 14:30"):
        a = "MATCH" if CON_B.match(c) else "no"
        b = "MATCH" if CURATA.match(c) else "no"
        print(f"   {c:34s} con \\b: {a:5s}   con (?=\\s|$): {b:5s}"
              f"{'   🔴 DIVERGE' if a != b else ''}")

    d = json.loads(QUINDICI.read_text(encoding="utf-8"))
    m = Memory(pathlib.Path(tempfile.mkdtemp()) / "apostrofo.db")

    def fermato(t: str) -> bool:
        return m.add(t, ground=False).get("status") == "quarantined"

    print("\n② IL VERDETTO ALLA PORTA, sui 10 che DEVONO restare ammessi:")
    esiti = {}
    for et, guardia in (("con \\b (oggi)", CON_B), ("curata", CURATA)):
        k = sum(any(fermato(p) for p in claim_atomici(t, guardia))
                for t in d["elenco_restano"])
        esiti[et] = k
        print(f"   guardia {et:14s} -> fermati {k}/10")

    print("\n③ IL CASO R4, pezzo per pezzo:")
    r4 = [t for t in d["elenco_restano"] if "warmup" in t.lower()]
    if r4:
        for et, guardia in (("con \\b (oggi)", CON_B), ("curata", CURATA)):
            print(f"   guardia {et}:")
            for p in claim_atomici(r4[0], guardia):
                print(f"     · «{p[:62]:62s}» -> {'FERMATO' if fermato(p) else 'passa'}")

    print("\n④ CONTROLLO: i 5 che devono essere FERMATI restano fermati?")
    for et, guardia in (("con \\b (oggi)", CON_B), ("curata", CURATA)):
        k = sum(any(fermato(p) for p in claim_atomici(t, guardia))
                for t in d["elenco_tornate"])
        print(f"   guardia {et:14s} -> fermati {k}/5"
              f"{'  ok' if k == 5 else '  ⚠️ la cura ha rotto il lato buono'}")

    dopo = esiti["curata"]
    verdetto = "REGGE" if dopo == 2 else f"🔴 FALSIFICATA: ne restano {dopo}/10"
    print(f"\n⇒ Q4 (il danno torna da 3 a 2): {verdetto}")


if __name__ == "__main__":
    main()
