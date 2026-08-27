# -*- coding: utf-8 -*-
"""Q2 — QUALI LAME PARLANO QUANDO LA FONTE E' UN DOCUMENTO INTERO.

Il ruolo assegnato a ws4 il 27/08 alle 20:25 e' il MECCANISMO: non quanto, ma
quale layer parla e quale tace. La domanda di @ws3 e @ws5 e' se il gate regga
sul REGIME VERO — tutte le nostre misure sono su fonti di UNA FRASE, e un
contratto e' quaranta pagine.

LA PREDIZIONE DI @ws3, da falsificare
-------------------------------------
    «sul lungo, L4.1 dovrebbe comportarsi COME SUL CORTO (e' lessicale sulla
     cifra, non dipende dalla lunghezza), mentre L4-grounding e il giudice
     dovrebbero degradare. Se invece anche L4.1 cede sul lungo, la mia lettura
     e' sbagliata.»

LA MIA, che il banco puo' smentire
-----------------------------------
Il giudice ha una finestra (`_rerank_max_doc_chars()` vale 2000 char ≈ 512
token, e presidia il rerank, non il write). ⇒ su una fonte da 220 KB il giudizio
si forma su un TRONCAMENTO che la ricevuta non dichiara: un claim VERO sostenuto
dall'ultima pagina dovrebbe risultare non sostenuto. Se invece il claim di coda
regge sull'intero, la finestra non morde qui e devo dirlo.

LA FONTE E' REALE, non costruita da me: `docs/archive/2026-05-13_FORGIA.md`,
un documento del repo. I due claim veri citano cifre che stanno DAVVERO una a
riga 10 e una nelle ultime righe. Il claim falso cita una cifra che nel
documento non c'e'.

I CONTROLLI CHE DEVONO POTER FALLIRE
-------------------------------------
① il claim di CODA sulla fonte «solo le ultime righe» deve essere ammesso: e'
   la prova che quel claim e' vero e riconoscibile, senza la quale un suo crollo
   sull'intero non significherebbe niente;
② il claim FALSO deve essere fermato sul regime corto: e' la cella di cui
   conosco gia' l'esito, e se cambia sto misurando un banco diverso.

Fuori da pytest (sotto pytest l'embedder e' uno stub su SHA-256).

    python docs/stato-reale/banchi/quali-lame-parlano-sul-regime-lungo.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

DOC = Path("docs/archive/2026-05-13_FORGIA.md")

CLAIM = {
    "A testa   (1143 LOC, riga 10)": "Il file wake.py conta 1143 LOC.",
    "B coda    (75 tool, in fondo)": "HippoAgent v2.0 ha 75 tool MCP.",
    "C falso   (cifra assente)": "Il file wake.py conta 9999 LOC.",
}


def _lame(ric: dict) -> str:
    """Quale lama ha parlato. Le chiavi le chiedo, non le presumo."""
    fuori = []
    for chiave in ("moat", "adjudication", "warnings", "advice"):
        v = ric.get(chiave)
        if not v:
            continue
        testo = json.dumps(v, ensure_ascii=False, default=str)
        for nome in (
            "L1", "L3", "L4.1", "L4.2", "L4-grounding", "L4-negazione",
            "L4-relazione", "L4-review", "L4-skipped", "SOURCE_TRUST",
        ):
            if f'"{nome}"' in testo or f"'{nome}'" in testo or f" {nome} " in testo:
                if nome not in fuori:
                    fuori.append(nome)
    return ",".join(fuori) if fuori else "-"


def main() -> int:
    if not DOC.exists():
        print(f"NON RIUSCITO: {DOC} non c'e' — eseguire dalla radice del repo")
        return 1
    testo = DOC.read_text(encoding="utf-8", errors="replace")
    print(f"  fonte REALE: {DOC}  ({len(testo)} caratteri)")

    # I due claim veri devono davvero stare dove dico: se no, non misuro niente.
    if "1143" not in testo[:3000]:
        print("NON RIUSCITO: «1143» non e' nei primi 3000 caratteri")
        return 1
    if "75" not in testo[-3000:]:
        print("NON RIUSCITO: «75» non e' negli ultimi 3000 caratteri")
        return 1
    print("  verificato: «1143» sta nei primi 3000 char, «75» negli ultimi 3000\n")

    REGIMI = {
        "testa 2k": testo[:2000],
        "testa 20k": testo[:20000],
        "INTERO 220k": testo,
        "coda 2k": testo[-2000:],
    }

    from verimem import client as _client  # noqa: PLC0415
    from verimem.client import Memory  # noqa: PLC0415

    print(f"  codice sotto misura: {_client.__file__}\n")
    mem = Memory(str(Path(tempfile.mkdtemp()) / "lungo.db"))

    print(f"  {'regime':<12} {'claim':<32} {'esito':<13} {'ground':>7}  {'ms':>6}  lame")
    print("  " + "-" * 96)
    esiti: dict[tuple[str, str], tuple[str, float | None, str]] = {}
    chiavi = None
    for reg, fonte in REGIMI.items():
        for nome, prop in CLAIM.items():
            t0 = time.monotonic()
            ric = mem.add(prop, topic=f"lungo/{reg}", source=fonte, validate="full")
            ms = (time.monotonic() - t0) * 1000
            if chiavi is None:
                chiavi = sorted(ric.keys())
            st = str(ric.get("status"))
            g = ric.get("grounding_score")
            lame = _lame(ric)
            esiti[(reg, nome)] = (st, g, lame)
            gs = "None" if g is None else f"{float(g):.1f}"
            print(f"  {reg:<12} {nome:<32} {st:<13} {gs:>7}  {ms:6.0f}  {lame}")
        print()

    print(f"  chiavi della ricevuta: {chiavi}")

    # ── CONTROLLO ①: il claim di coda e' vero e riconoscibile.
    st_coda = esiti[("coda 2k", "B coda    (75 tool, in fondo)")][0]
    print("\nCONTROLLO (1) il claim di CODA sulla fonte di coda e' ammesso:")
    if st_coda == "quarantined":
        print(f"   CADUTO — e' {st_coda} anche sulle sole ultime righe.")
        print("   ⇒ un suo crollo sull'intero non proverebbe niente sulla finestra.")
        return 1
    print(f"   retto — {st_coda}")

    # ── CONTROLLO ②: il falso e' fermato sul corto.
    st_falso = esiti[("testa 2k", "C falso   (cifra assente)")][0]
    print("CONTROLLO (2) il claim FALSO e' fermato sul regime corto:")
    if st_falso != "quarantined":
        print(f"   CADUTO — e' {st_falso}: sto misurando un banco diverso da quello che credo")
        return 1
    print(f"   retto — {st_falso}, lame {esiti[('testa 2k', 'C falso   (cifra assente)')][2]}")

    # ── LA PREDIZIONE DI ws3: L4.1 non dipende dalla lunghezza.
    print("\nLA PREDIZIONE DI ws3 — L4.1 sul lungo si comporta come sul corto:")
    for nome in CLAIM:
        riga = {reg: esiti[(reg, nome)][2] for reg in REGIMI}
        l41 = {reg: ("L4.1" in v) for reg, v in riga.items()}
        stabile = len(set(l41.values())) == 1
        print(f"   {nome:<32} L4.1 {'STABILE' if stabile else 'CAMBIA'}: {l41}")

    # ── LA MIA: il claim vero di coda crolla sull'intero?
    st_int, g_int, lame_int = esiti[("INTERO 220k", "B coda    (75 tool, in fondo)")]
    _s_coda, g_coda, _l = esiti[("coda 2k", "B coda    (75 tool, in fondo)")]
    print("\nLA MIA — il claim VERO di coda, sulla fonte INTERA:")
    print(f"   sulla coda sola: {g_coda if g_coda is None else round(float(g_coda), 1)}")
    print(f"   sull'intero:     {g_int if g_int is None else round(float(g_int), 1)}  ({st_int}, lame {lame_int})")
    if st_int == "quarantined" and _s_coda != "quarantined":
        print("   ⇒ CONFERMATA: lo stesso claim vero passa sulla coda e cade sull'intero.")
        print("      Il documento contiene la prova e il giudizio non la raggiunge.")
    else:
        print("   ⇒ NON confermata su questa cella: la finestra non morde qui, e va detto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
