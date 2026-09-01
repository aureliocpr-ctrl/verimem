"""Chi ha già misurato questo? — indice inverso del registro, per ARGOMENTO.

Esiste perché stanotte @ws2 ha scoperto di aver duplicato due celle di @ws4
(`W7-30`/`W7-31` alle 23:05, `W2-31`/`W2-42` un'ora dopo, stesso oggetto) e l'ha
scoperto **dopo aver misurato**, cercando celle da controfirmare. Sue parole:
«e' la QUINTA volta stanotte che dichiaro nuovo qualcosa di gia' registrato».

Il registro ha ~170 celle e le sigle sono per AUTRICE (`W2-n`, `LANT-n`, `W7-n`):
chi sta per misurare `L4.2` non ha modo di sapere chi l'ha gia' guardato senza
leggere tutto. **Non manca disciplina: manca un indice per argomento** — e la
regola che abbiamo pagato piu' volte dice di curare lo strumento, non le persone.

    python scripts/chi_ha_gia_misurato.py L4.2
    python scripts/chi_ha_gia_misurato.py supersession
    python scripts/chi_ha_gia_misurato.py            # indice completo dei layer
    python scripts/chi_ha_gia_misurato.py --ultima LANT   # l'ultima cella scritta,
                                                          # termini estratti da soli

PERCHE' `--ultima` esiste (30/08, ws7). La forma con un termine **richiede
ancora disciplina**: devi ricordarti che lo strumento esiste E scegliere la
parola giusta. Ho scritto questo script per non duplicare, e il 30/08 ho
duplicato lo stesso — `LANT-75` ripeteva un reperto gia' misurato SETTE volte
da @ws4 e @ws2, e me ne sono accorta dopo aver consegnato. **Avevo lo
strumento, la regola (`O1`) e il precedente.** ⇒ La lezione che paghiamo da
settimane — *l'adozione misura l'ATTRITO, non la disciplina: se una cura non e'
usata, cura lo strumento* — **vale anche per lo strumento nato da quella
lezione**. `--ultima` toglie i due passi che restavano: prende l'ultima cella
scritta da quella sigla ed **estrae i termini da sola**.

Cerca nel testo INTERO della cella (non solo nella domanda), stampa id, autrice e
la domanda troncata. Il confronto e' case-insensitive; un punto nel termine e'
trattato alla lettera, cosi' `L4.1` non pesca `L4-11`.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

REGISTRO = Path(__file__).resolve().parent.parent / "docs" / "stato-reale" / "00-ESAME.md"
#: ⚠️ era `^\| [\w-]+ \|`, che accetta QUALSIASI parola fra barre: nel file
#: vivono ALTRE TABELLE (liste numerate di cancelli, comandi, verifiche) e le
#: loro righe finivano nel conteggio — 61 su 675, misurato il 01/09 (`LANT-144`).
#: Quarto posto in cui lo stesso pattern era stato COPIATO.
RIGA_CELLA = re.compile(r"^\| (?:LANT|W\d)-\d+[a-z]? \|")
#: i nomi di layer che il prodotto usa: e' l'asse su cui le celle si duplicano.
LAYER = re.compile(r"\bL\d(?:\.\d+)?\b|\bL\d-[a-z]+\b|\bmoat\b|\bgate\b", re.IGNORECASE)


def celle() -> list[str]:
    testo = REGISTRO.read_text(encoding="utf-8")
    return [r for r in testo.splitlines() if RIGA_CELLA.match(r) and r.count("|") >= 9]


def _campi(riga: str) -> tuple[str, str, str]:
    parti = riga.split("|")
    ident = RIGA_CELLA.match(riga).group(0).strip("| ")
    # la colonna autrice porta spesso una parentesi («ws7 (collega)», «ws1 (riporta ws2)»):
    # per l'indice serve la SIGLA, non la nota, altrimenti la stessa persona compare due volte.
    autrice = parti[7].strip().split("(")[0].strip() or "?"
    return ident, autrice[:10], parti[2].strip()[:64]


def cerca(termine: str) -> int:
    pat = re.compile(re.escape(termine), re.IGNORECASE)
    trovate = [r for r in celle() if pat.search(r)]
    if not trovate:
        print(f"  «{termine}»: nessuna cella. Sei la prima — scrivilo nella cella.")
        return 0
    print(f"  «{termine}» compare in {len(trovate)} celle:\n")
    per_autrice = Counter()
    for riga in trovate:
        ident, autrice, domanda = _campi(riga)
        per_autrice[autrice] += 1
        print(f"    {ident:9} ({autrice:12}) {domanda}")
    if len(per_autrice) > 1:
        conto = " · ".join(f"{a} {n}" for a, n in per_autrice.most_common())
        print(f"\n  ⚠️  {len(per_autrice)} autrici diverse su questo tema: {conto}")
        print("     Prima di misurare, leggi le loro: potresti avere gia' la risposta,")
        print("     o poter firmare la loro invece di rifare la stessa cosa.")
    return 0


def indice() -> int:
    conto: Counter[str] = Counter()
    autrici: dict[str, set[str]] = {}
    for riga in celle():
        _ident, autrice, _dom = _campi(riga)
        for nome in {m.group(0).upper() for m in LAYER.finditer(riga)}:
            conto[nome] += 1
            autrici.setdefault(nome, set()).add(autrice)
    print(f"  indice per argomento — {len(celle())} celle, {len(conto)} temi\n")
    print(f"  {'tema':<16} {'celle':>5}  {'autrici':>7}   chi")
    print("  " + "-" * 62)
    for nome, n in conto.most_common():
        chi = sorted(autrici[nome])
        segno = "  ⚠️ duplicabile" if len(chi) > 2 and n > 3 else ""
        print(f"  {nome:<16} {n:>5}  {len(chi):>7}   {' '.join(chi)[:28]}{segno}")
    return 0


#: i termini che vale la pena cercare in una cella: sigle di layer, nomi di file
#: e parole tecniche lunghe. Le parole comuni non discriminano e sporcherebbero
#: il risultato con celle che non c'entrano.
TERMINE_UTILE = re.compile(
    r"\b(?:L\d[.\-]?\d*(?:[.\-]\w+)?|[a-z_]{6,}\.py|[a-z_]{8,})\b")
COMUNI = {"misurata", "registro", "grounding", "popolazione", "controllo",
          "verificato", "dichiarato", "conferma", "riferimento", "precedente",
          "eseguito", "temporaneo", "risultato", "misurato", "verifica",
          "elemento", "sostiene", "contiene", "compare", "misurare", "misurano"}


def ultima(sigla: str) -> int:
    """L'ultima cella scritta da *sigla*: quali suoi temi erano gia' misurati?"""
    mie = [r for r in celle() if r.lstrip("| ").startswith(sigla)]
    if not mie:
        print(f"  nessuna cella con sigla «{sigla}».")
        return 1
    riga = mie[-1]
    ident, autrice, domanda = _campi(riga)
    print(f"  ultima cella di «{sigla}»: {ident} ({autrice})")
    print(f"    {domanda}")
    print()

    #: i termini della cella, i piu' lunghi per primi (i piu' specifici)
    grezzi = {m.group(0).lower() for m in TERMINE_UTILE.finditer(riga)} - COMUNI
    termini = sorted(grezzi, key=len, reverse=True)[:8]
    print(f"  cerco i suoi {len(termini)} termini piu' specifici: {' '.join(termini)}")
    print()

    tutte = celle()
    trovato = False
    for termine in termini:
        pat = re.compile(re.escape(termine), re.IGNORECASE)
        altre = [r for r in celle()
                 if pat.search(r) and not r.startswith(f"| {ident} |")]
        if len(altre) < 2:            # una cella sola non e' un tema condiviso
            continue
        #: e un termine che compare OVUNQUE non discrimina: «indipendente» sta
        #: in 21 celle di 6 autrici e non dice niente su cosa hai misurato.
        #: Un tetto sulla frequenza batte una lista di parole comuni — la lista
        #: e' monolingue, va manutenuta, e dimentica sempre un caso.
        if len(altre) > len(tutte) // 8:
            continue
        autrici = {_campi(r)[1] for r in altre} - {autrice}
        if not autrici:               # gia' tuo: non e' un duplicato fra istanze
            continue
        trovato = True
        print(f"  ⚠️  «{termine}» — {len(altre)} altre celle, "
              f"{len(autrici)} altre autrici: {' '.join(sorted(autrici))}")
        for r in altre[:4]:
            i2, a2, d2 = _campi(r)
            print(f"        {i2:9} ({a2:12}) {d2[:56]}")
    if not trovato:
        print("  ✅ nessun tema di questa cella e' gia' misurato da un'altra: e' nuova.")
    else:
        print()
        print("  ⇒ LEGGI quelle celle prima di dichiarare il reperto NUOVO.")
        print("     Puoi comunque avere un pezzo che loro non hanno: dillo cosi'.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--ultima":
        sys.exit(ultima(sys.argv[2]))
    sys.exit(cerca(" ".join(sys.argv[1:])) if len(sys.argv) > 1 else indice())
