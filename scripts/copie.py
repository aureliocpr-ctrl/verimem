#!/usr/bin/env python3
"""Il cricchetto delle copie (regola R3: una superficie per primitiva).

Conta, con `ast`, quante volte la stessa primitiva è stata riscritta invece di
essere importata da un posto solo. Ogni contatore ha un TETTO: il numero di
oggi. Il tetto non deve salire. Se sale, questo script esce 1 e la PR non entra.

    python scripts/copie.py              # verdetto, uscita 0/1
    python scripts/copie.py --dettaglio  # anche il file e la riga di ogni copia
    python scripts/copie.py --autotest   # prova che il cricchetto morde

PERCHÉ AST E NON GREP — misurato il 09/09/2026 sugli stessi tre file:
`grep '^\\s*def '` dava 167 definizioni, `ast` ne dava 176. Nessuno dei due
sbagliava: `^\\s*def ` non è un contatore di definizioni, è un filtro di righe
che *cominciano con* `def`, e non vede né `async def` né `class`. Qui si conta
con `ast`, e ogni totale porta accanto il criterio che lo compone.

PERCHÉ IL TETTO PORTA IL CRITERIO — i numeri di partenza proposti nel piano
(18/20/5/4/3) reggono su due contatori su cinque, perché gli altri tre erano
misurati con un criterio diverso da questo. I tetti qui sotto sono i numeri di
QUESTO script, eseguito il 09/09/2026 sul tip `20257636`; il criterio di
ciascuno è scritto accanto e vale quanto il numero. Cambiare il criterio senza
cambiare il tetto rende il cricchetto muto.

COME SI ALZA UN TETTO: a mano, in questo file, nello stesso commit che aggiunge
la copia, con il motivo nel messaggio. Non esiste un `--aggiorna`: un cricchetto
che si ripara da solo non morde (misurato il 06/09 su quattro versioni dello
stesso numero: un numero che ti dà ragione non fa attrito, quindi nessuno lo urta).

COME SI PROVA CHE MORDE: `--autotest` aggiunge una copia finta e pretende
l'uscita 1. Un cricchetto che non è mai diventato rosso è un sensore
scollegato, non un presidio: `tests/test_copie_cricchetto.py` lo tiene onesto.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import pathlib
import sys
from collections import defaultdict

RADICE = pathlib.Path(__file__).resolve().parent.parent
PACCHETTO = RADICE / "verimem"

# --- i tetti: numero + criterio. Misurati il 09/09/2026 sul tip 20257636 ------
TETTI = {
    "def__jaccard": 18,
    "def__tokens": 20,
    "def__signature": 5,
    "corpi__signature": 4,
    "liste_di_parole_vuote": 16,
    "elenchi_di_status": 22,
}
# ⛔ QUI C'ERA UN «DEBITO» DI 13 ELENCHI CON `quarantined` E SENZA `user_belief`,
# attribuito al ticket T49. RITIRATO da me il 10/09/2026, dopo aver letto tutti e
# tredici i posti uno per uno sul main appena mergiato (`32273665`):
#
#   cli.py:4255            l'enum canonico per la PRESENTAZIONE
#   cli.py:4683            la validazione dello status dopo il gate
#   client.py:1207 · flow_events.py:353 · mcp_server.py:14263
#                          il calcolo di `withheld_despite_judge` su UN fatto
#   gateway.py:1746 · trust_ledger.py:30
#                          le AZIONI del gate — `admitted` e `abstained` non sono
#                          nemmeno status: falsi positivi puri del criterio
#   entity_populate.py:111 · provenance_signing.py:142 · tier2_judge.py:296 ·
#   semantic.py:3460 · 3488 · 3516
#                          esclusioni VOLUTE e corrette («Quarantined/orphaned
#                          facts are excluded»)
#
# Zero su tredici erano «una porta che serve i quarantenati come veri», che è la
# cosa che il nome prometteva e che T49 ha davvero curato con una superficie sola.
# Il numero non è sceso col merge di T49 perché non misurava T49.
#
# E c'è di peggio di un numero inutile: quel contatore pretendeva di SCENDERE,
# cioè chiedeva di togliere sei esclusioni corrette. Un righello che spinge nella
# direzione sbagliata è peggio di nessun righello — chi lo prende sul serio rompe
# il prodotto per far scendere una cifra.
#
# La lezione, contro di me: **contare le OCCORRENZE di una forma non misura una
# funzione**. Chi vuole misurare T49 conta i chiamanti di recupero che non
# nascondono gli status bassi, e quel test ce l'ha Giano.

# Le parole vuote note servono solo a RICONOSCERE una stoplist, non a esserlo.
_VUOTE_EN = {"the", "and", "for", "with", "that", "this", "from", "are", "was", "not", "you"}
_VUOTE_IT = {"il", "lo", "la", "di", "che", "per", "con", "una", "del", "non", "sono", "come"}
_SOGLIA_PAROLE_VUOTE = 4

_STATUS = {
    "quarantined", "orphaned", "user_belief", "provisional",
    "model_claim", "verified", "legacy_unverified", "rejected", "admitted",
}
_SOGLIA_STATUS = 2


def _stringhe_del_contenitore(nodo: ast.AST) -> list[str] | None:
    """Le stringhe letterali di `[...]`, `{...}`, `(...)` e di `set(...)`/`frozenset(...)`.

    Serve la forma con la chiamata: `frozenset({"a", "b"})` è la stessa copia di
    `{"a", "b"}`, e un criterio che vedesse solo la seconda conterebbe meno del vero.
    """
    elementi = None
    if isinstance(nodo, (ast.Set, ast.List, ast.Tuple)):
        elementi = nodo.elts
    elif (
        isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Name)
        and nodo.func.id in {"set", "frozenset", "tuple", "list"}
        and len(nodo.args) == 1
        and isinstance(nodo.args[0], (ast.Set, ast.List, ast.Tuple))
    ):
        elementi = nodo.args[0].elts
    if elementi is None:
        return None
    return [e.value for e in elementi if isinstance(e, ast.Constant) and isinstance(e.value, str)]


def conta(pacchetto: pathlib.Path, copia_finta: str | None = None) -> dict:
    """Le sei misure. `copia_finta` aggiunge una definizione inventata: serve all'autotest."""
    definizioni: dict[str, list[tuple[str, int]]] = defaultdict(list)
    corpi_signature: dict[str, list[str]] = defaultdict(list)
    stoplist: list[tuple[str, int, int, int]] = []
    status: list[tuple[str, int, tuple[str, ...]]] = []
    non_letti: list[tuple[str, str]] = []

    for percorso in sorted(pacchetto.rglob("*.py")):
        try:
            rel = percorso.relative_to(RADICE).as_posix()
        except ValueError:
            # un albero fuori dal repo (un worktree, una copia, il banco del test):
            # si misura lo stesso, col percorso relativo al pacchetto che gli è stato dato
            rel = percorso.relative_to(pacchetto.parent).as_posix()
        testo = percorso.read_text(encoding="utf-8", errors="replace")
        try:
            albero = ast.parse(testo, filename=str(percorso))
        except SyntaxError as errore:  # un file che non si legge NON è un file senza copie
            non_letti.append((rel, str(errore)))
            continue
        for nodo in ast.walk(albero):
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definizioni[nodo.name].append((rel, nodo.lineno))
                if nodo.name == "_signature":
                    corpo = ast.dump(ast.Module(body=nodo.body, type_ignores=[]))
                    impronta = hashlib.sha256(corpo.encode()).hexdigest()[:8]
                    corpi_signature[impronta].append(f"{rel}:{nodo.lineno}")
                continue
            stringhe = _stringhe_del_contenitore(nodo)
            if not stringhe:
                continue
            insieme = set(stringhe)
            n_en = len(insieme & _VUOTE_EN)
            n_it = len(insieme & _VUOTE_IT)
            if n_en + n_it >= _SOGLIA_PAROLE_VUOTE:
                stoplist.append((rel, getattr(nodo, "lineno", 0), n_en, n_it))
            dentro = insieme & _STATUS
            if len(dentro) >= _SOGLIA_STATUS:
                status.append((rel, getattr(nodo, "lineno", 0), tuple(sorted(dentro))))

    if copia_finta:
        definizioni[copia_finta].append(("verimem/COPIA_FINTA.py", 1))

    stoplist = sorted(set(stoplist))
    status = sorted(set(status))
    senza_user_belief = [s for s in status if "quarantined" in s[2] and "user_belief" not in s[2]]

    return {
        "misure": {
            "def__jaccard": len(definizioni.get("_jaccard", [])),
            "def__tokens": len(definizioni.get("_tokens", [])),
            "def__signature": len(definizioni.get("_signature", [])),
            "corpi__signature": len(corpi_signature),
            "liste_di_parole_vuote": len(stoplist),
            "elenchi_di_status": len(status),
        },
        "debito_status_senza_user_belief": len(senza_user_belief),
        "dove": {
            "_jaccard": definizioni.get("_jaccard", []),
            "_tokens": definizioni.get("_tokens", []),
            "_signature": definizioni.get("_signature", []),
        },
        "corpi_signature": corpi_signature,
        "stoplist": stoplist,
        "status": status,
        "status_senza_user_belief": senza_user_belief,
        "non_letti": non_letti,
        "pacchetto": str(pacchetto.resolve()),
        "file_letti": len(list(pacchetto.rglob("*.py"))) - len(non_letti),
    }


CRITERI = {
    "def__jaccard": "definizioni `def _jaccard` (ast, a qualunque indentazione)",
    "def__tokens": "definizioni `def _tokens` (ast, a qualunque indentazione)",
    "def__signature": "definizioni `def _signature` (ast)",
    "corpi__signature": "corpi DISTINTI fra quelle `_signature` (sha256 del corpo ast)",
    "liste_di_parole_vuote": f"liste letterali con >= {_SOGLIA_PAROLE_VUOTE} parole vuote note (it+en)",
    "elenchi_di_status": f"liste letterali con >= {_SOGLIA_STATUS} status di fatto noti",
}


def stampa(risultato: dict, dettaglio: bool) -> int:
    misure = risultato["misure"]
    # il percorso ASSOLUTO, non «verimem/»: questo script si ancora a __file__, quindi
    # lanciato da un altro albero misura QUELL'albero e stampa un verde che non vale
    # (trovato in revisione da ws1 il 09/09: una copia dello script nella scratchpad
    # dava VERDE con EXIT=0 perché lì `verimem/` non esiste).
    print(f"copie.py — {risultato['file_letti']} file letti sotto {risultato['pacchetto']} (ast)")
    if risultato["file_letti"] == 0:
        print("VERDETTO: ROSSO — zero file letti: questo non è l'albero del prodotto. "
              "Un cricchetto che misura la cartella sbagliata stampa sempre verde.")
        return 1
    if risultato["non_letti"]:
        print(f"  ATTENZIONE: {len(risultato['non_letti'])} file NON letti (SyntaxError): "
              "il conteggio è un minimo, non un totale")
        for rel, errore in risultato["non_letti"]:
            print(f"    {rel}: {errore[:70]}")
    print()
    saliti = []
    for chiave, tetto in TETTI.items():
        valore = misure[chiave]
        segno = "OK " if valore <= tetto else "SALE"
        if valore > tetto:
            saliti.append((chiave, valore, tetto))
        print(f"  [{segno}] {chiave:24s} {valore:3d} / tetto {tetto:3d}   {CRITERI[chiave]}")

    # Il «debito» degli elenchi senza `user_belief` è stato RITIRATO: vedi la nota
    # in testa al file. Il numero resta consultabile con --dettaglio, senza tetto e
    # senza pretendere di misurare una funzione.

    if dettaglio:
        print("\n--- dove stanno ---")
        for nome in ("_jaccard", "_tokens", "_signature"):
            print(f"  def {nome}:")
            for rel, riga in sorted(risultato["dove"][nome]):
                print(f"      {rel}:{riga}")
        print("  corpi distinti di _signature:")
        for impronta, dove in sorted(risultato["corpi_signature"].items(), key=lambda kv: -len(kv[1])):
            print(f"      {impronta} x{len(dove)}  {', '.join(dove)}")
        print("  liste di parole vuote:")
        for rel, riga, n_en, n_it in risultato["stoplist"]:
            print(f"      {rel}:{riga}  (en={n_en} it={n_it})")
        print("  elenchi di status:")
        for rel, riga, dentro in risultato["status"]:
            manca = "   <-- senza user_belief" if "quarantined" in dentro and "user_belief" not in dentro else ""
            print(f"      {rel}:{riga}  {list(dentro)}{manca}")

    print()
    if saliti:
        print("VERDETTO: ROSSO — una primitiva è stata riscritta invece di essere importata.")
        for chiave, valore, tetto in saliti:
            print(f"  {chiave}: {valore} > {tetto}")
        print("  Cura: importa quella che esiste. Se la copia è voluta, alza il tetto in "
              "scripts/copie.py nello stesso commit, col motivo nel messaggio.")
        return 1
    print("VERDETTO: VERDE — nessuna primitiva sorvegliata è stata riscritta.")
    return 0


def autotest() -> int:
    """Il controllo positivo: il cricchetto DEVE diventare rosso su una copia in più."""
    print("=== autotest: (a) il repo com'è ===")
    a = conta(PACCHETTO)
    uscita_a = stampa(a, dettaglio=False)
    print("\n=== autotest: (b) con UNA copia finta di _jaccard in più ===")
    b = conta(PACCHETTO, copia_finta="_jaccard")
    uscita_b = stampa(b, dettaglio=False)
    print()
    if uscita_a == 0 and uscita_b == 1:
        print("AUTOTEST VERDE: (a) esce 0 e (b) esce 1 — il cricchetto morde.")
        return 0
    print(f"AUTOTEST ROSSO: (a) esce {uscita_a} (atteso 0), (b) esce {uscita_b} (atteso 1).")
    if uscita_a != 0:
        print("  (a) != 0 significa che un tetto è già superato: leggi il verdetto sopra.")
    if uscita_b != 1:
        print("  (b) != 1 significa che questo script è un sensore scollegato: NON usarlo in CI.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dettaglio", action="store_true", help="stampa file e riga di ogni copia")
    parser.add_argument("--autotest", action="store_true",
                        help="prova che il cricchetto diventa rosso su una copia in più")
    argomenti = parser.parse_args(argv)
    if argomenti.autotest:
        return autotest()
    return stampa(conta(PACCHETTO), dettaglio=argomenti.dettaglio)


if __name__ == "__main__":
    sys.exit(main())
