"""QUANTO DEL LAVORO E' RAGGIUNGIBILE DAL REGISTRO — i banchi che nessun documento nomina.

Il **canale** e' effimero: ha un TTL, scorre, e domani nessuno lo rilegge. Il
**registro** (`00-ESAME.md`) e i dossier sono il **lascito**. ⇒ La domanda:
**quanti dei banchi che abbiamo scritto sono raggiungibili da li'?**

Non e' una domanda di forma. Un banco che nessun documento nomina esiste solo
per chi si ricorda di averlo scritto — e fra una sessione e l'altra **quel
ricordo non c'e'**. E' la stessa classe del *puntatore vuoto* che il nostro
metodo gia' conosce: *«prima di togliere una riga, grep il file puntato»*.

CRITERIO, dichiarato: un banco e' **CITATO** se il suo nome file (con o senza
`.py`) compare in un qualunque `.md` di `docs/stato-reale/`. E' un criterio
**generoso** — basta la menzione, non serve la riga «rifallo con» — quindi il
numero che esce e' un **limite superiore** della raggiungibilita'.

⚠️ **ESCLUSIONI dichiarate, e sono la correzione di un mio conteggio**: la prima
misura dava **150 orfani su 244**, ma dentro c'erano i moduli che iniziano con
`_` (`_ricevuta.py`, `_numero_solo_strutturale.py`): sono **librerie di
supporto**, non banchi, e **non devono** essere citati da nessuna cella.
Contarli come orfani gonfia il numero.

CONTROLLI CHE POSSONO FALLIRE:
 (1) se i documenti non si leggono, non dico niente invece di dire zero.
 (2) **controllo positivo**: un banco che SO essere citato (quello di `W7-54`,
     `tre-popolazioni-sulla-stessa-fonte-reale.py`) deve risultare CITATO. Se
     risulta orfano, il mio criterio non trova le citazioni che ci sono.

    python -u docs/stato-reale/banchi/quanto-del-lavoro-e-raggiungibile-dal-registro.py
"""

from __future__ import annotations

import io
import os
import sys

BASE = "docs/stato-reale"
NOTO_CITATO = "tre-popolazioni-sulla-stessa-fonte-reale.py"


def main() -> int:
    if not os.path.isdir(BASE):
        print(f"NON RIUSCITO: {BASE} non esiste (esegui dalla radice del repo)")
        return 1
    testi = {}
    for f in sorted(os.listdir(BASE)):
        if f.endswith(".md"):
            try:
                testi[f] = io.open(os.path.join(BASE, f), encoding="utf-8",
                                   errors="replace").read()
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠️ non leggo {f}: {type(e).__name__}")
    if not testi:
        print("NON RIUSCITO: nessun documento letto, non dico 'zero citati'.")
        return 1
    tutto = "\n".join(testi.values())
    registro = testi.get("00-ESAME.md", "")
    print(f"  documenti letti: {len(testi)}   registro: "
          f"{len(registro)} caratteri")

    d = os.path.join(BASE, "banchi")
    tutti = sorted(f for f in os.listdir(d) if f.endswith(".py"))
    supporto = [f for f in tutti if f.startswith("_")]
    banchi = [f for f in tutti if not f.startswith("_")]

    def citato(f: str, testo: str) -> bool:
        return f in testo or f[:-3] in testo

    print("\n  -- CONTROLLO (2): un banco che SO citato risulta citato?")
    if NOTO_CITATO not in banchi:
        print(f"     CADUTO - {NOTO_CITATO} non e' su disco: controllo inutile")
        return 1
    if not citato(NOTO_CITATO, tutto):
        print(f"     CADUTO - {NOTO_CITATO} risulta ORFANO ma so che e' citato:")
        print("     il criterio non trova le citazioni che ci sono.")
        return 1
    print(f"     retto - {NOTO_CITATO[:44]} risulta citato")

    in_reg = [f for f in banchi if citato(f, registro)]
    in_doc = [f for f in banchi if citato(f, tutto)]
    orfani = [f for f in banchi if not citato(f, tutto)]

    print(f"\n  == LA MISURA  (esclusi {len(supporto)} moduli di supporto '_*')")
    print(f"     banchi su disco:           {len(banchi)}")
    print(f"     citati nel REGISTRO:       {len(in_reg):>4}"
          f"   ({100.0 * len(in_reg) / len(banchi):.1f}%)")
    print(f"     citati in QUALSIASI doc:   {len(in_doc):>4}"
          f"   ({100.0 * len(in_doc) / len(banchi):.1f}%)")
    print(f"     ORFANI:                    {len(orfani):>4}"
          f"   ({100.0 * len(orfani) / len(banchi):.1f}%)")

    # 🪞 CORRETTO il 29/08 alle 21:56, su segnalazione di un'altra istanza.
    # La prima stesura filtrava `r.startswith("| W")` e contava **130 celle**:
    # il registro ne ha **TRE forme di ID** — `W<n>-<n>`, `LANT-<n>` e **solo
    # numero** — e quel filtro escludeva le ultime due, cioe' **138 celle**.
    # ⇒ Il numero che avevo pubblicato (46 su 130, 35,4%) era **ottimistico per
    # costruzione**: mancavano proprio le famiglie messe peggio.
    import re as _re

    def _id_cella(r: str) -> str | None:
        if not r.startswith("| ") or r.count("|") < 4:
            return None
        i = r.split("|")[1].strip()
        for pat in (r"W\d+-\d+\w*", r"LANT-\d+", r"\d+"):
            if _re.fullmatch(pat, i):
                return i
        return None

    celle = [r for r in registro.split("\n") if _id_cella(r)]
    con = [r for r in celle if "rifallo con" in r]
    print("\n  == E DALL'ALTRO LATO: le celle con la riga «rifallo con»")
    print(f"     celle: {len(celle)}   con «rifallo con»: {len(con)}"
          f"   ({100.0 * len(con) / max(1, len(celle)):.1f}%)")
    print("     per FORMA di ID, perche' non sono messe uguale:")
    for nome, pat in (("W<n>-<n>", r"W\d+-\d+\w*"), ("LANT-<n>", r"LANT-\d+"),
                      ("solo NUMERO", r"\d+")):
        sub = [r for r in celle if _re.fullmatch(pat, _id_cella(r) or "")]
        subc = [r for r in sub if "rifallo con" in r]
        print(f"       {nome:<12} {len(sub):>4} celle, {len(subc):>3} con rifallo"
              f"  ({100.0 * len(subc) / max(1, len(sub)):.1f}%)")

    print("\n  == I PRIMI ORFANI, in ordine alfabetico")
    for f in orfani[:10]:
        print(f"     {f}")

    print("\n  -- LA RIGA CHE CONTA")
    print(f"     {len(orfani)} banchi su {len(banchi)} non sono nominati da NESSUN")
    print("     documento. Esistono solo per chi si ricorda di averli scritti, e")
    print("     fra una sessione e l'altra quel ricordo non c'e'.")
    print("     ⚠️ «Orfano» qui significa **non citato in un .md**, NON inutile:")
    print("     molti sono stati annunciati sul CANALE, che pero' e' effimero.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
