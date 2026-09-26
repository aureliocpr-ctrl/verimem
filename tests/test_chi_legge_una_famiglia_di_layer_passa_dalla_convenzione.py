"""T129 — chi confronta un layer per FAMIGLIA deve passare dalla superficie unica.

IL DIFETTO CHE CHIUDE, misurato tre volte in un giorno:
  · `run_validation_gate` contava i layer per prefisso e DECIDEVA: un avviso
    marcato «si vede e non decide» faceva quarantenare una scrittura ammessa;
  · la porta MCP li prende per prefisso e NOMINA: elencherebbe un avviso
    ritirato fra i responsabili di una quarantena (T128);
  · il 2026-09-03 la stessa forma era gia' stata curata in una terza giuntura.
La convenzione (`_is_advisory_layer`) esiste dal 03/09. Il difetto non e' che
manchi: e' che **nessuno obbliga a passarci**.

PERCHE' SOLO IL PREFISSO DI FAMIGLIA. `== "L4-review"` o `in ("L4-grounding",
"L4.1")` nominano un livello PRECISO e non possono pescare un marcatore per
sbaglio. `.startswith("L1")` prende un'intera famiglia — e i marcatori nascono
dentro la famiglia, con un suffisso. Il difetto vive li' e solo li'.

DUE CELLE, perche' un presidio con una sola meta' non e' un controllo:
  · chi confronta per famiglia senza il filtro accende il rosso (sotto);
  · chi solo REGISTRA non e' obbligato a filtrare — se lo obbligassi, il banco
    misurerebbe la mia pazienza e non il pacchetto (controllo negativo).

SI LEGGE CON `ast`, NON CON UN GREP: un commento che cita `.startswith("L1")`
non e' codice, e i numeri di riga si spostano sotto i piedi. La chiave
dell'elenco e' `file::funzione`, che sopravvive a uno spostamento.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACCHETTO = Path(__file__).resolve().parents[1] / "verimem"

#: Deroghe DICHIARATE: chiave `<file>::<funzione>` -> (QUANTE, la ragione con
#: la DATA DI USCITA). Un elenco senza data diventa un cimitero — questo
#: progetto ne ha gia' visti.
#:
#: ⚠️ IL NUMERO NON E' UN DETTAGLIO, ED E' UN CRICCHETTO A SCENDERE. La prima
#: versione di questo banco derogava per FUNZIONE, e una funzione lunga ne
#: nascondeva dentro quattro: il contatore che ha fatto quarantenare una
#: scrittura ammessa spariva nella deroga scritta per un ALTRO confronto della
#: stessa funzione. Una deroga che copre cio' che non hai guardato non e' una
#: deroga: e' un tappeto.
DEROGHE: dict[str, tuple[int, str]] = {
    "anti_confab_gate.py::advisory_eligible": (1, (
        "La lista che il confronto scorre e' gia' filtrata dalla convenzione "
        "DUE RIGHE SOPRA (`ws = [... not _is_advisory_layer(...)]`): il "
        "confronto e' conforme nella sostanza, e a non vederlo e' questo "
        "banco, che guarda una sola espressione per volta. Derogato invece "
        "che curato perche' la cura sarebbe nel BANCO, non nel prodotto, e "
        "un presidio che insegue i propri falsi positivi smette di essere "
        "leggibile. USCITA: quando il filtro e il confronto staranno nella "
        "stessa espressione, se qualcuno tocchera' quella funzione."
    )),
    "anti_confab_gate.py::run_validation_gate": (4, (
        "Erano cinque e sono quattro: il quinto — il contatore che DECIDE se "
        "trattenere, il difetto vero — e' uscito con la fusione che marca gli "
        "avvisi ritirati, e il numero e' sceso qui come era scritto.\n"
        "  · `has_l1`, che alimenta i due marcatori di osservabilita' e deve "
        "    restare INTERO di proposito (lo dice il commento del modulo): "
        "    ESCE quando l'osservabilita' legge i marcatori invece dei layer;\n"
        "  · una guardia che decide se EMETTERE un testo: un avviso ritirato "
        "    glielo farebbe emettere. USCITA: con 1b.3, insieme a T128;\n"
        "  · due che aggiungono una nota all'`advice` di un avviso: decorano, "
        "    non decidono e non nominano — restano, e il negativo di questo "
        "    banco esiste perche' non vengano trascinate dentro."
    )),
    "mcp_server.py::_call_tool_impl": (1, (
        "T128: `_altri` NOMINA i responsabili di una quarantena e prenderebbe "
        "anche un avviso ritirato. Cura nota (`and not _is_advisory_layer`), "
        "rimandata a 1b.3 perche' quel testo la ricevuta unica lo riscrive. "
        "USCITA: con 1b.3."
    )),
}

#: I prefissi che nominano una FAMIGLIA. `L3-semantic` o `L4-review` no: quelli
#: sono livelli precisi, e un confronto esatto non puo' sbagliare bersaglio.
_FAMIGLIE = ("L1", "L2", "L3", "L4")


def _e_confronto_di_famiglia(nodo: ast.Call) -> bool:
    f = nodo.func
    if not (isinstance(f, ast.Attribute) and f.attr == "startswith"):
        return False
    if not nodo.args or not isinstance(nodo.args[0], ast.Constant):
        return False
    valore = nodo.args[0].value
    return isinstance(valore, str) and valore in _FAMIGLIE


def _usa_la_convenzione(nodo: ast.AST) -> bool:
    """`_is_africa...` no: si cerca una CHIAMATA alla convenzione nell'albero."""
    for n in ast.walk(nodo):
        if isinstance(n, ast.Call):
            f = n.func
            nome = f.id if isinstance(f, ast.Name) else (
                f.attr if isinstance(f, ast.Attribute) else "")
            if nome == "_is_advisory_layer":
                return True
    return False


def _legge_un_layer(nodo: ast.Call, sorgente: str) -> bool:
    """Il confronto deve insistere su un LAYER, non su una stringa qualunque."""
    pezzo = ast.get_source_segment(sorgente, nodo) or ""
    return "layer" in pezzo.lower()


def _raccogli(percorso: Path) -> list[tuple[str, int, str]]:
    sorgente = percorso.read_text(encoding="utf-8", errors="replace")
    try:
        albero = ast.parse(sorgente)
    except SyntaxError:  # pragma: no cover — il pacchetto deve compilare
        pytest.fail(f"{percorso.name} non si parsa")

    #: funzione che contiene ogni nodo, per la chiave stabile
    dentro: dict[int, str] = {}
    for f in ast.walk(albero):
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(f):
                dentro.setdefault(id(n), f.name)

    #: ESPRESSIONE che contiene ogni nodo. ⚠️ DUE VERSIONI SBAGLIATE PRIMA DI
    #: QUESTA, e la seconda è costata quattro ore di tronco rosso il 19/09.
    #: ① una finestra di RIGHE: con il filtro tolto restava verde, perché nel
    #:   testo intorno la convenzione era citata **in un commento**;
    #: ② l'ISTRUZIONE contenitrice, cercata con `setdefault` in BFS — ma
    #:   `ast.FunctionDef` **è una `ast.stmt`**, e in BFS vince lei: l'albero
    #:   guardato diventava la funzione INTERA, e una sola chiamata alla
    #:   convenzione in un punto qualunque assolveva tutti i confronti di
    #:   quella funzione. A spegnere il sensore è stata una cura VERA entrata
    #:   in `run_validation_gate`: i 5 confronti derogati sono diventati 0
    #:   visti, e senza il cricchetto sarebbe passato per un miglioramento.
    #: Qui si guarda l'espressione FIGLIA dell'istruzione che contiene il
    #: confronto: il test di un `if`, il valore di un assegnamento. Il corpo
    #: dell'`if` non c'entra — quello che conta è se la convenzione partecipa
    #: alla DECISIONE, non se compare da qualche parte lì vicino.
    radice: dict[int, ast.expr] = {}
    for s in ast.walk(albero):
        if not isinstance(s, ast.stmt):
            continue
        for e in ast.iter_child_nodes(s):
            if isinstance(e, ast.expr):
                for n in ast.walk(e):
                    radice[id(n)] = e  # BFS: l'istruzione più interna vince

    trovati = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Call) or not _e_confronto_di_famiglia(nodo):
            continue
        if not _legge_un_layer(nodo, sorgente):
            continue
        st = radice.get(id(nodo))
        if st is not None and _usa_la_convenzione(st):
            continue
        trovati.append((percorso.name, nodo.lineno,
                        dentro.get(id(nodo), "<modulo>")))
    return trovati


def _violazioni() -> list[tuple[str, int, str]]:
    fuori = []
    for percorso in sorted(PACCHETTO.glob("*.py")):
        fuori.extend(_raccogli(percorso))
    return fuori


def _per_chiave() -> dict[str, list[tuple[str, int, str]]]:
    fuori: dict[str, list[tuple[str, int, str]]] = {}
    for f, r, fn in _violazioni():
        fuori.setdefault(f"{f}::{fn}", []).append((f, r, fn))
    return fuori


def test_nessun_confronto_di_famiglia_senza_la_convenzione():
    """Il cuore. Il numero da portare a ZERO."""
    trovate = _per_chiave()
    non_dichiarate = {k: v for k, v in trovate.items() if k not in DEROGHE}
    assert not non_dichiarate, (
        "un layer confrontato per FAMIGLIA senza `_is_advisory_layer`: un "
        "marcatore «si vede e non decide» entrerebbe qui come se decidesse.\n"
        + "\n".join(f"  {f}:{r}  in {fn}()"
                    for v in non_dichiarate.values() for f, r, fn in v)
        + "\n  Cura: `and not _is_advisory_layer(...)`. Se la deroga e' "
          "voluta, va in DEROGHE con la ragione E la data di uscita."
    )


def test_il_cricchetto_delle_deroghe_scende_e_non_sale():
    """Quante ne copre ogni deroga. Se ne compare una in piu' nella stessa
    funzione, la deroga scritta per un'altra riga la nasconderebbe: e' successo,
    ed e' il motivo per cui questo numero esiste. Se ne spariscono, il numero
    va abbassato nello stesso commit che le toglie."""
    trovate = _per_chiave()
    errori = []
    for chiave, (quante, _ragione) in DEROGHE.items():
        viste = len(trovate.get(chiave, []))
        if viste > quante:
            errori.append(
                f"{chiave}: {viste} confronti, la deroga ne copre {quante} — "
                "una e' NUOVA e nessuno l'ha guardata")
        elif viste < quante:
            errori.append(
                f"{chiave}: {viste} confronti, la deroga ne dichiara {quante} — "
                "il cricchetto e' sceso: abbassa il numero qui")
    assert not errori, "\n".join(errori)


def test_CONTROLLO_POSITIVO_il_banco_vede_davvero_i_confronti():
    """Senza questa cella, un bug nel parser renderebbe il test verde sempre.
    Deve TROVARE i confronti di famiglia, derogati o no."""
    tutti = _violazioni()
    derogati = [x for x in tutti if f"{x[0]}::{x[2]}" in DEROGHE]
    assert derogati, (
        "il banco non trova nemmeno le deroghe note: sta misurando il vuoto "
        f"(confronti visti: {len(tutti)})")


def test_CONTROLLO_POSITIVO_il_banco_vede_IL_FILE_DOVE_IL_DIFETTO_VIVE():
    """La cella che mancava, e per volerne una in meno il tronco e' stato rosso.

    Il controllo qui sopra si accontenta di UN confronto in tutto il pacchetto,
    e quell'uno stava in un altro file: intanto in `anti_confab_gate.py` — dove
    questa forma e' nata tre volte — il presidio non ne vedeva piu' nemmeno
    uno. Un controllo positivo che non nomina il posto dove il difetto vive non
    e' un controllo: e' un'altra misura che puo' spegnersi da sola.

    ⚠️ Confronta CIO' CHE C'E' NEL FILE con CIO' CHE IL BANCO RIPORTA: non un
    numero atteso, che invecchia, ma le due letture della stessa cosa.
    """
    percorso = PACCHETTO / "anti_confab_gate.py"
    sorgente = percorso.read_text(encoding="utf-8", errors="replace")
    nel_file = [n for n in ast.walk(ast.parse(sorgente))
                if isinstance(n, ast.Call) and _e_confronto_di_famiglia(n)
                and _legge_un_layer(n, sorgente)]
    assert nel_file, (
        "il file non confronta piu' nessuna famiglia di layer: o il prodotto e' "
        "stato curato del tutto, e allora questo banco va rimisurato, o il "
        "lettore si e' rotto")
    visti = [v for v in _violazioni() if v[0] == percorso.name]
    assert visti, (
        f"{len(nel_file)} confronti di famiglia nel file e il presidio ne "
        "riporta ZERO. Non e' una cura: e' il sensore scollegato — e la volta "
        "scorsa a spegnerlo e' bastata UNA chiamata alla convenzione, in un "
        "punto qualunque della stessa funzione")


def test_CONTROLLO_NEGATIVO_chi_solo_REGISTRA_non_e_obbligato():
    """L'altra meta'. `[w.get("layer") for w in warnings]` che costruisce una
    riga di log NON confronta una famiglia e non deve comparire: se comparisse,
    il presidio obbligherebbe a filtrare anche chi scrive un diario."""
    sorgente = 'righe = [w.get("layer") for w in warnings if w.get("layer")]\n'
    albero = ast.parse(sorgente)
    confronti = [n for n in ast.walk(albero)
                 if isinstance(n, ast.Call) and _e_confronto_di_famiglia(n)]
    assert not confronti, "un lettore che solo registra non deve essere preso"


def test_una_deroga_senza_data_di_uscita_non_e_una_deroga():
    """Un elenco di eccezioni senza scadenza diventa un cimitero: qui la
    scadenza e' obbligatoria nel testo della ragione."""
    senza = [k for k, v in DEROGHE.items()
             if "USCITA" not in v[1].upper() and "esce quando" not in v[1].lower()]
    assert not senza, f"deroghe senza data/condizione di uscita: {senza}"
