#!/usr/bin/env python3
"""Un `|` in un pattern di `grep` senza `-E` è un ZERO che sembra misurato.

    python scripts/grep_nelle_mappe.py                    # sui documenti della mappa
    python scripts/grep_nelle_mappe.py --cartella docs/   # su un'altra cartella
    python scripts/grep_nelle_mappe.py --autotest         # prova che il controllo morde

IL DIFETTO, trovato da ws4 ML il 10/09/2026 e misurato nello stesso giro:

    $ grep -c  "trust signal|trusted|hallucination rate" README.md
    0        EXIT=1
    $ grep -cE "trust signal|trusted|hallucination rate" README.md
    1        EXIT=0
    $ grep -n  "trust signal" README.md
    463:# + provenance are the trust signal, not a self-asserted badge).

Senza `-E` il carattere `|` è **letterale**: `grep` cerca la stringa intera
«a|b|c», non la trova, esce 1. E una conclusione come «nessuna riga del README
nomina questa funzione» sembra misurata mentre è l'artefatto di un'opzione
mancante. Su 405 mappe, 7 dichiaravano un pattern con `|`: **2 conclusioni
"nessuna" erano smentite** (`trust_signal.md` → README:463,
`trust_calibration.md` → README:249), 5 reggevano. Due su sette, non sette su
sette — il numero è di ws4 ML, che aveva tutto da guadagnare a gonfiarlo.

È la regola di casa applicata al RIGHELLO invece che al prodotto: **il grep
serve a TROVARE, mai a CONTARE**, e qui non trovava nemmeno.

COME DISTINGUE IL `|` DEL PATTERN DALLA PIPE DELLA SHELL: con `shlex`, che
rispetta le virgolette. In `grep "foo" | head` la pipe è un token a sé e il
pattern è `foo`: nessun allarme. In `grep "a|b" file` il pattern è `a|b`:
allarme. Un controllo che cercasse `|` nella riga darebbe un rosso su metà del
repo, e nessuno lo userebbe — che è il modo più comune in cui un presidio muore.

NON VEDE (dichiarato, perché un limite taciuto si legge come assenza di limite):
  * i pattern costruiti da una variabile di shell;
  * `grep -f file_di_pattern`;
  * un `|` dentro una classe `[...]`, dove è letterale per davvero — segnalato
    lo stesso, perché scriverlo lì è quasi sempre un errore;
  * se il match trovato con `-E` sia **pertinente**: questo dice che la misura
    era sbagliata, non quale sia quella giusta.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import shlex
import sys

CARTELLA_PREDEFINITA = pathlib.Path("docs/stato-reale/mappa")
COMANDI = ("grep", "git grep", "egrep", "rg")
# `-E`/`-P` accendono le alternative; `egrep` e `rg` le hanno già accese.
OPZIONI_CHE_SALVANO = {"-E", "-P", "--extended-regexp", "--perl-regexp"}
_INIZIO = re.compile(r"(?<![\w./-])(git\s+grep|egrep|grep|rg)(?![\w-])")


def pattern_di(comando: str) -> tuple[str | None, bool]:
    """(il pattern, se le alternative sono accese). `shlex` rispetta le virgolette."""
    try:
        pezzi = shlex.split(comando)
    except ValueError:
        return None, True  # virgolette non bilanciate: non è misurabile, non è un rosso
    acceso = False
    for i, pezzo in enumerate(pezzi):
        if pezzo in ("egrep", "rg"):
            acceso = True
            continue
        if pezzo in OPZIONI_CHE_SALVANO:
            acceso = True
            continue
        if pezzo.startswith("-") and len(pezzo) > 1 and not pezzo.startswith("--"):
            # opzioni raggruppate: -cE, -nE, -rEn …
            if "E" in pezzo[1:] or "P" in pezzo[1:]:
                acceso = True
            continue
        if pezzo.startswith("-"):
            continue
        if pezzo in ("grep", "git"):
            continue
        if pezzo == "|":       # la pipe della shell: il comando finisce qui
            return None, acceso
        return pezzo, acceso   # il primo argomento non-opzione è il pattern
    return None, acceso


def _e_riga_di_tabella(riga: str) -> bool:
    """Una riga di tabella markdown: comincia con `|` e ne ha almeno due."""
    spogliata = riga.strip()
    return spogliata.startswith("|") and spogliata.count("|") >= 2


def classifica(pattern: str, riga: str) -> str | None:
    r"""SICURO / AMBIGUO / None, per un pattern che contiene un `|`.

    In BRE — cioe' `grep` SENZA `-E` — l'alternanza si scrive `\|`, ed e' CORRETTA.
    Un righello che accusasse ogni `|` sbaglierebbe contro chi lo usa: sui 403
    documenti della mappa, il 09/09, avrebbe dato 8 dove i sicuri erano 3.

    Resta un caso che nessun criterio meccanico puo' chiudere: dentro una TABELLA
    markdown il `|` va scritto `\|` per non spezzare la cella, quindi li' un
    `\|` puo' essere l'escape del documento su un comando che nel terminale
    aveva il `|` NUDO — cioe' un difetto vero travestito da BRE. Quello si marca
    AMBIGUO e lo legge una persona: dichiararlo vale piu' che sceglierne una.
    """
    nudi = re.findall(r"(?<!\\)\|", pattern)
    if nudi:
        if _rami_degeneri(pattern):
            return None      # il `|` è LETTERALE VOLUTO: vedi `_rami_degeneri`
        return "SICURO"
    if _e_riga_di_tabella(riga):
        return "AMBIGUO"
    return None          # solo `\|`: alternanza BRE valida, nessun difetto


def _rami_degeneri(pattern: str) -> bool:
    """Vero se, con `-E`, uno dei rami dell'alternanza sarebbe VUOTO.

    Allora il `|` non è un'alternanza dimenticata: è la barra LETTERALE che
    qualcuno cerca davvero — tipicamente l'inizio di una riga di tabella
    markdown, `^| \\`docs`. Aggiungere `-E` a un pattern così non lo ripara, lo
    ROMPE: un ramo vuoto matcha ogni riga. Provato il 10/09/2026 su un file di
    tre righe di cui due di tabella:

        grep -c  '^| `docs' prova.txt   -> 2   (le due righe di tabella)
        grep -cE '^| `docs' prova.txt   -> 3   (TUTTE: il ramo vuoto matcha)

    Senza questa classe il righello accusava anche `documenti.md:724` e
    suggeriva una cura che avrebbe peggiorato la misura.
    """
    rami = re.split(r"(?<!\\)\|", pattern)
    return any(ramo in ("", "^", "$") for ramo in rami)


def cerca(cartella: pathlib.Path) -> dict:
    sospetti: list[tuple[str, int, str, str]] = []
    ambigui: list[tuple[str, int, str, str]] = []
    comandi_visti = 0
    documenti = sorted(cartella.rglob("*.md"))
    for percorso in documenti:
        for numero, riga in enumerate(
            percorso.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            for trovato in _INIZIO.finditer(riga):
                comandi_visti += 1
                pattern, acceso = pattern_di(riga[trovato.start():])
                if not (pattern and "|" in pattern and not acceso):
                    continue
                verdetto = classifica(pattern, riga)
                voce = (percorso.as_posix(), numero, pattern, riga.strip()[:110])
                if verdetto == "SICURO":
                    sospetti.append(voce)
                elif verdetto == "AMBIGUO":
                    ambigui.append(voce)
    return {
        "cartella": str(cartella.resolve()),
        "documenti": len(documenti),
        "comandi_visti": comandi_visti,
        "sospetti": sospetti,
        "ambigui": ambigui,
    }


def stampa(risultato: dict) -> int:
    print(f"grep_nelle_mappe.py — {risultato['documenti']} documenti .md sotto "
          f"{risultato['cartella']}")
    print(f"  comandi di ricerca letti: {risultato['comandi_visti']}")
    print()
    sospetti = risultato["sospetti"]
    ambigui = risultato.get("ambigui", [])
    if ambigui:
        print(f"  {len(ambigui)} da LEGGERE (un `\\|` dentro una riga di tabella: puo' essere "
              "l'escape del markdown su un `|` nudo, oppure alternanza BRE valida):")
        for percorso, numero, pattern, riga in ambigui:
            print(f"    {percorso}:{numero}")
            print(f"        pattern: {pattern}")
            print(f"        riga:    {riga}")
        print()
    if not sospetti:
        print("VERDETTO: VERDE — nessun pattern con un `|` NUDO cercato senza `-E`.")
        if ambigui:
            print(f"  ({len(ambigui)} ambigui elencati sopra: li giudica chi possiede la mappa.)")
        return 0
    print(f"  {len(sospetti)} pattern con `|` cercati SENZA `-E` (il `|` è letterale, "
          "quindi lo zero non vuol dire «non c'è»):")
    for percorso, numero, pattern, riga in sospetti:
        print(f"    {percorso}:{numero}")
        print(f"        pattern: {pattern}")
        print(f"        riga:    {riga}")
    print()
    print(f"VERDETTO: ROSSO — {len(sospetti)} misure potrebbero essere zeri che sembrano misurati.")
    print("  Cura: rieseguire con `-E` e correggere la conclusione se il numero cambia.")
    return 1


def autotest() -> int:
    """Il controllo positivo, e soprattutto i casi che NON devono suonare."""
    import tempfile

    casi = [
        ("grep senza -E con alternative", '`grep -c "a|b" README.md`', 1),
        ("grep CON -E", '`grep -cE "a|b" README.md`', 0),
        ("opzioni raggruppate -cE", '`grep -cE "a|b" f`', 0),
        ("egrep", '`egrep "a|b" f`', 0),
        ("git grep senza -E", '`git grep "a|b" -- f`', 1),
        ("pipe della SHELL, non del pattern", '`grep -n "solo" f | head -3`', 0),
        ("pipe di shell dopo un pattern con -E", '`grep -nE "a|b" f | wc -l`', 0),
        ("nessun grep", "una riga qualunque con un | in mezzo", 0),
        ("virgolette non bilanciate", '`grep -c "a|b README.md`', 0),
        ("il nome di un file che finisce per grep", "`ripgrep e' un altro programma`", 0),
        # --- le tre classi trovate sui 403 documenti veri, il 10/09/2026 ---
        # senza queste il righello dava 8 dove i sicuri erano 3: sbagliava
        # CONTRO chi lo usa, che e' il modo piu' rapido di far ignorare un presidio.
        ("BRE: `\\|` e' l'alternanza CORRETTA senza -E", '`grep -c "a\\|b" f`', 0),
        ("ramo degenere: `^|` cerca la barra LETTERALE, -E lo romperebbe",
         "`grep -c '^| \\`docs' f`", 0),
        ("ramo degenere in coda: `a|`", "`grep -c 'a|' f`", 0),
        ("tre alternative vere restano un difetto", '`grep -rn "A|B|C" verimem/`', 1),
        ("`\\|` dentro una riga di TABELLA e' ambiguo, non un rosso",
         '| domanda | `grep -c "a\\|b" f` | **4** |', 0),
    ]
    esiti = []
    for nome, riga, atteso in casi:
        with tempfile.TemporaryDirectory() as cartella:
            base = pathlib.Path(cartella)
            (base / "prova.md").write_text(riga + "\n", encoding="utf-8")
            avuto = stampa(cerca(base))
            ok = avuto == atteso
            esiti.append(ok)
            print(f"=== {nome}: atteso {atteso}, avuto {avuto}  {'OK' if ok else 'ROSSO'}\n")
    if all(esiti):
        print(f"AUTOTEST VERDE: {len(esiti)} casi su {len(esiti)} — morde sul difetto e "
              "TACE sulla pipe della shell (che è la metà che decide se il presidio verrà usato).")
        return 0
    print(f"AUTOTEST ROSSO: {esiti.count(False)} casi sbagliati su {len(esiti)}.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cartella", default=str(CARTELLA_PREDEFINITA))
    parser.add_argument("--autotest", action="store_true")
    argomenti = parser.parse_args(argv)
    if argomenti.autotest:
        return autotest()
    cartella = pathlib.Path(argomenti.cartella)
    if not cartella.exists():
        print(f"grep_nelle_mappe.py — NON MISURATO: {cartella} non esiste in questo albero.")
        print("  I documenti della mappa arrivano con la fusione di lead/mappa-indice;")
        print("  fino ad allora una conclusione «nessuna riga» può essere uno zero finto.")
        return 0
    return stampa(cerca(cartella))


if __name__ == "__main__":
    sys.exit(main())
