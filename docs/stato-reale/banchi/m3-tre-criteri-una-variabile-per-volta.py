"""M3 anello ③ — i tre criteri del gate sul supersede, una variabile per volta.

    python docs/stato-reale/banchi/m3-tre-criteri-una-variabile-per-volta.py

POPOLAZIONE, dichiarata: le coppie `(ritirato -> sostituto)` con
`superseded_reason LIKE 'same-source%%'` e con entrambi gli embedding presenti.
NON sono i «213 casi già classificati» del mandato: quell'insieme non esiste —
143 viene da un censimento per tipo di scrittura (`49e67921d177`) e 70 dalla
popolazione di un altro motivo di ritiro (`29b35cf2386b`), e i `numeric_clash`
oggi sono 147.

⚠️ IL PROBLEMA DELL'ETICHETTA, e lo dichiaro invece di nasconderlo.
La verità dell'anello ① — «sbagliata = il ritirato aveva grounding >= 90» — dà
463 positivi su 466: con quel rapporto precision e recall sono DEGENERI, perché
un criterio che blocca tutto avrebbe precision 99,4%. Non misurerebbe niente.

Quindi l'etichetta di questo banco è un'ALTRA, ed è un PROXY dichiarato:

    SBAGLIATA  = il ritirato e il sostituto portano insiemi di numeri DIVERSI
                 (il nuovo dice ALTRO, non riformula il vecchio)
    LEGITTIMA  = stessi numeri (il nuovo riformula)

È il criterio di `W2-369`. Non è la verità: è una proxy, e il banco ne LEGGE un
campione in fondo perché il lettore possa giudicarla.

I TRE CRITERI, uno per volta e nessuno combinato:
    (a) coseno fra gli embedding sopra soglia
    (b) stessa testa del soggetto (`subject_head`) fra ritirato e sostituto
    (c) il giudice del prodotto dice che il sostituto NON è implicato dal
        ritirato — l'NLI di contraddizione, su un campione perché costa

Per ognuno si stampano ENTRAMBE le popolazioni: quante SBAGLIATE ferma e
quante LEGITTIME blocca. Un criterio che ferma il 99% delle sbagliate ma anche
il 99% delle legittime non è utilizzabile, e con la sola precision non si vede.

Sola lettura sullo store; il criterio (c) gira su store temporaneo.
"""
from __future__ import annotations

import os
import re
import struct
import sys

DB = os.path.join(os.environ["USERPROFILE"], ".engram", "semantic", "semantic.db")
NUM = re.compile(r"\d+[.,]?\d*")
CAMPIONE_NLI = 40


def coppie() -> list[tuple[str, str, str, bytes, bytes]]:
    import sqlite3
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    righe = con.execute(
        "SELECT v.id, v.proposition, n.proposition, v.embedding, n.embedding "
        "FROM facts v JOIN facts n ON v.superseded_by = n.id "
        "WHERE v.superseded_reason LIKE 'same-source%' "
        "AND v.embedding IS NOT NULL AND n.embedding IS NOT NULL").fetchall()
    con.close()
    return righe


def coseno(a: bytes, b: bytes) -> float:
    n = len(a) // 4
    va = struct.unpack(f"{n}f", a)
    vb = struct.unpack(f"{n}f", b)
    num = sum(x * y for x, y in zip(va, vb, strict=True))
    na = sum(x * x for x in va) ** 0.5
    nb = sum(y * y for y in vb) ** 0.5
    return num / (na * nb) if na and nb else 0.0


def due_popolazioni(nome: str, etichette: list[bool], ferma: list[bool]) -> None:
    """Stampa quante SBAGLIATE ferma e quante LEGITTIME blocca."""
    sb = [f for e, f in zip(etichette, ferma, strict=True) if e]
    lg = [f for e, f in zip(etichette, ferma, strict=True) if not e]
    fs, fl = sum(sb), sum(lg)
    prec = 100.0 * fs / (fs + fl) if (fs + fl) else 0.0
    rec = 100.0 * fs / len(sb) if sb else 0.0
    print(f"  {nome}")
    print(f"     SBAGLIATE fermate {fs:4d}/{len(sb):4d} = recall    {rec:5.1f}%")
    print(f"     LEGITTIME bloccate{fl:4d}/{len(lg):4d} = falsi     "
          f"{100.0 * fl / len(lg) if lg else 0.0:5.1f}%")
    print(f"     precision {prec:5.1f}%   (fermate in tutto {fs + fl})")


def main() -> int:
    righe = coppie()
    etich = [set(NUM.findall(v or "")) != set(NUM.findall(n or ""))
             for _i, v, n, _a, _b in righe]
    print(f"  POPOLAZIONE: {len(righe)} coppie same-source con entrambi gli embedding")
    print(f"  etichetta PROXY (numeri diversi): SBAGLIATE {sum(etich)} · "
          f"LEGITTIME {len(etich) - sum(etich)}")
    print()

    cos = [coseno(a, b) for _i, _v, _n, a, b in righe]
    for soglia in (0.80, 0.90, 0.95):
        due_popolazioni(f"(a) coseno > {soglia:.2f} FERMA la supersessione",
                        etich, [c > soglia for c in cos])
    print()

    from verimem.subject_extract import subject_head
    stessa = [subject_head(v or "") == subject_head(n or "") and subject_head(v or "") != ""
              for _i, v, n, _a, _b in righe]
    due_popolazioni("(b) stessa TESTA del soggetto -> lascia passare; diversa FERMA",
                    etich, [not s for s in stessa])
    print()

    print(f"  (c) NLI: campione di {CAMPIONE_NLI}, gira su store temporaneo")
    print("      [eseguito solo con --nli per non pagare i giudizi a ogni corsa]")
    if "--nli" in sys.argv:
        # ⚠️ CAMPIONE BILANCIATO, e la ragione e' un errore della prima corsa:
        #    prendendo le prime 40 righe il campione conteneva UNA sola
        #    legittima, e «precision 100%, falsi 0%» poggiava su quel caso.
        #    Un criterio si giudica su ENTRAMBE le popolazioni o non si giudica.
        sb = [(r, e) for r, e in zip(righe, etich, strict=True) if e][:CAMPIONE_NLI // 2]
        lg = [(r, e) for r, e in zip(righe, etich, strict=True) if not e][:CAMPIONE_NLI // 2]
        mix = sb + lg
        print(f"      campione BILANCIATO: {len(sb)} sbagliate + {len(lg)} legittime")
        nli([r for r, _e in mix], [e for _r, e in mix])
    print()

    print("  UN CAMPIONE DELL'ETICHETTA, da leggere: la proxy dice il vero?")
    mostrati = 0
    for (_i, v, n, _a, _b), e in zip(righe, etich, strict=True):
        if mostrati >= 3 or not e:
            continue
        print(f"     SBAGLIATA?  vecchio: {(v or '')[:74]}")
        print(f"                 nuovo  : {(n or '')[:74]}")
        mostrati += 1
    return 0


def nli(sub: list, etich: list) -> None:
    import tempfile
    d = tempfile.mkdtemp(prefix="m3nli_")
    os.environ["HIPPO_DATA_DIR"] = d
    os.environ.pop("ENGRAM_DATA_DIR", None)
    from verimem import mcp_server
    from verimem.anti_confab_gate import run_validation_gate
    ag = mcp_server._ag()
    assert "m3nli_" in str(ag.semantic.db_path), "non e' la dir temporanea"
    ferma = []
    for _i, v, n, _a, _b in sub:
        r = run_validation_gate(proposition=n or "", verified_by=None,
                                topic="banco/m3", agent=ag, source=v or "",
                                ground_write=True, validate="full")
        g = getattr(r, "grounding_score", None)
        ferma.append(g is not None and g < 40.0)
    due_popolazioni("(c) il giudice NON implica il sostituto dal ritirato", etich, ferma)


if __name__ == "__main__":
    raise SystemExit(main())
