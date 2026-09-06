"""`--db` vale sulle porte che si digitano, non solo su `console` e `stats`.

T16, e il ticket lo sottostima. Non e' che `--db` manchi dalla riga di comando:
ESISTE gia' su due comandi e non sulle tre porte che l'utente usa davvero.
Misurato eseguendo l'`--help`, non contando le occorrenze del nome:

    verimem recall   --help | grep -- --db   ->   NESSUN --db
    verimem remember --help | grep -- --db   ->   NESSUN --db
    verimem facts    --help | grep -- --db   ->   NESSUN --db
    cli.py:1023  @app.command("console")  --db "Path to your memory store"
    cli.py:1972  @app.command("stats")    --db "Store file"

e `console` STAMPA GIA' `store: {mem.semantic.db_path}` (cli.py:1048). La forma
che serve e' dentro il prodotto, su due comandi secondari, e non ha fatto lo
sweep: la classe «manca lo SWEEP», non un pezzo da inventare.

PERCHE' E' UN P0 E NON UN'ASIMMETRIA ESTETICA. Il Quickstart insegnava
`Memory("memory.db")`, che e' relativo alla cartella corrente e che SOLO l'SDK
puo' ricevere. Chi poi prova la riga di comando dalla stessa cartella non
riceve un errore: riceve `no facts found` con EXIT=0. Il silenzio e' il danno —
l'utente conclude che la memoria e' vuota, non che sta guardando un altro file.
Per questo qui non basta che `--db` esista: la risposta deve DIRE quale store
ha aperto. Un percorso stampato trasforma un mistero in un refuso.

⚠️ NASCE ROSSO, ED E' VOLUTO: oggi le celle 2, 3, 4 e 5 cadono perche' l'opzione
non esiste (typer risponde "No such option" con exit 2). Diventano verdi quando
`_open_memory()` e `_facts_sm()` — le DUE superfici uniche che aprono lo store
per tutte le porte, sette chiamanti la prima — accettano il percorso.

Niente giudice e niente orologio: le scritture passano da `sm.store()` diretto.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app
from verimem.client import Memory
from verimem.semantic import Fact

_BASE = 1_700_000_000.0
_TESTO = "Il canone di locazione del capannone e' 2900 euro."
_QUERY = "quanto e' il canone di locazione"


def _punta_env(monkeypatch, dove: Path) -> None:
    """Sposta le tre variabili che la riga di comando rilegge a ogni giro.

    Sono TRE e vanno spostate tutte: e' misurato che la CLI rilegge la data dir
    dall'ambiente (fatto `ddbe62018c9a`), quindi una sola lasciata indietro
    farebbe aprire la cartella di prima e la cella misurerebbe un altro store.
    """
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(dove))


@pytest.fixture()
def due_cartelle(tmp_path, monkeypatch):
    """A contiene un fatto, B e' vuota — e l'ambiente punta a B DA SUBITO.

    E' la situazione dell'utente del ticket: lo store vero sta da una parte, la
    cartella da cui digita e' un'altra. Senza `--db` non ha ALCUN modo di dire
    alla riga di comando dove guardare.

    ⚠️ IN A SI SCRIVE CON `SemanticMemory(db_path=…)` DIRETTO, E L'ORDINE E' LA
    CURA. La prima versione puntava l'ambiente ad A, apriva `Memory()`, poi
    spostava l'ambiente su B: e il fatto di A usciva lo stesso da una porta
    puntata a B. Non era il prodotto — misurato separando l'unica variabile che
    contava, il PROCESSO:

        processo nuovo puntato ad A -> trova 2900: True     (controllo)
        processo nuovo puntato a B  -> trova 2900: False    (isola)

    cioe' l'ambiente isola benissimo, ed era il `CliRunner` — che gira NELLO
    STESSO processo — a riusare lo store gia' aperto dalla fixture. Aprendo A
    solo da `SemanticMemory` diretto, il percorso che la porta risolve dall'
    ambiente non viene mai popolato con A e la cella torna a misurare la porta.
    """
    from verimem.semantic import SemanticMemory

    a = tmp_path / "A"
    b = tmp_path / "B"
    a.mkdir()
    b.mkdir()

    _punta_env(monkeypatch, b)      #: la porta apre B, sempre
    db_a = a / "semantic" / "semantic.db"
    db_a.parent.mkdir(parents=True, exist_ok=True)
    sm = SemanticMemory(db_path=db_a)
    sm.store(Fact(id="F1", proposition=_TESTO, topic="t",
                  asserted_at=_BASE), embed="sync")
    return db_a, a, b


def _cli(*argomenti: str):
    return CliRunner().invoke(app, list(argomenti))


def test_controllo_positivo_dalla_cartella_giusta_il_fatto_si_trova(
        tmp_path, monkeypatch) -> None:
    """Se questa cade, tutto il resto del file non misura niente.

    Prova che il fatto e' scritto, che la query lo pesca e che la porta
    risponde: cosi' un rosso nelle celle sotto e' l'opzione mancante e non un
    banco che non ha mai avuto niente da trovare.
    """
    dati = tmp_path / "solo_una"
    dati.mkdir()
    _punta_env(monkeypatch, dati)
    m = Memory()
    #: ⚠️ UNA CIFRA DIVERSA DA QUELLA DI `due_cartelle`, di proposito. Le celle
    #: girano nello stesso processo: se una cella vedesse per sbaglio lo store
    #: di un'altra, con lo stesso numero il banco resterebbe verde e non lo
    #: saprei. Cifre diverse rendono la contaminazione VISIBILE.
    m.semantic.store(Fact(id="F1", proposition="Il canone del capannone e' "
                                               "1700 euro.",
                          topic="t", asserted_at=_BASE), embed="sync")

    esito = _cli("recall", _QUERY, "--k", "5")
    assert esito.exit_code == 0, f"uscita {esito.exit_code}"
    assert "1700" in esito.stdout, (
        "dalla cartella GIUSTA il fatto non si trova: il banco e' cieco, "
        "e nessuna delle celle sotto significa niente")


def test_dalla_cartella_sbagliata_oggi_il_silenzio(due_cartelle) -> None:
    """Il danno del ticket, messo per iscritto: nessun errore, EXIT=0.

    Questa cella NON chiede una cura: fotografa il comportamento che rende il
    difetto insidioso, e resta verde anche dopo. Se un domani la porta
    imparasse a dire «lo store che ho aperto e' vuoto», si aggiorna qui.
    """
    _, _, _ = due_cartelle
    esito = _cli("recall", _QUERY, "--k", "5")
    assert esito.exit_code == 0, (
        "oggi la porta esce con 0 anche quando non ha trovato niente")
    assert "2900" not in esito.stdout, (
        "la cartella B e' vuota: se il fatto compare, le due cartelle non "
        "sono separate e il banco misura un solo store")


def test_recall_accetta_lo_store_che_indichi(due_cartelle) -> None:
    """⚠️ RED: `--db` non esiste su `recall`."""
    db_a, _, _ = due_cartelle
    esito = _cli("recall", _QUERY, "--k", "5", "--db", str(db_a))
    assert esito.exit_code == 0, (
        f"`recall --db` esce con {esito.exit_code}: l'opzione non esiste, "
        f"mentre `console` e `stats` ce l'hanno gia'. Uscita: "
        f"{esito.stdout[:200]!r}")
    assert "2900" in esito.stdout, (
        "indicato lo store, il fatto deve uscire: e' l'unico modo che ha chi "
        "sta in un'altra cartella di leggere la propria memoria")


def test_remember_scrive_nello_store_che_indichi(due_cartelle) -> None:
    """⚠️ RED: `--db` non esiste su `remember`.

    Non basta guardarne l'uscita: il fatto va RILETTO dallo store A, altrimenti
    la cella starebbe verde anche se la scrittura fosse finita in B.
    """
    db_a, a, _ = due_cartelle
    esito = _cli("remember", "Il deposito cauzionale e' 5800 euro.",
                 "--topic", "t", "--db", str(db_a))
    assert esito.exit_code == 0, (
        f"`remember --db` esce con {esito.exit_code}: {esito.stdout[:200]!r}")

    riletto = Memory(str(db_a)).search("quanto e' il deposito cauzionale", k=5)
    assert any("5800" in str(r) for r in riletto), (
        "scritto con --db, il fatto non e' nello store indicato: l'opzione "
        "e' accettata e ignorata, che e' peggio del non averla")


def test_facts_list_legge_lo_store_che_indichi(due_cartelle) -> None:
    """⚠️ RED: `--db` non esiste sulla famiglia `facts`.

    `facts` apre lo store da `_facts_sm()`, che e' una superficie DIVERSA da
    `_open_memory()`: due innesti, non uno, o meta' delle porte resta indietro.
    """
    db_a, _, _ = due_cartelle
    esito = _cli("facts", "list", "--db", str(db_a))
    assert esito.exit_code == 0, (
        f"`facts list --db` esce con {esito.exit_code}: {esito.stdout[:200]!r}")
    assert "2900" in esito.stdout, "lo store indicato contiene quel fatto"


def test_la_porta_dice_quale_store_ha_aperto(due_cartelle) -> None:
    """⚠️ RED, ed e' la meta' che rende il difetto NON RIPETIBILE.

    `--db` da solo cura chi gia' SA di avere due store. Chi non lo sa — cioe'
    l'utente del ticket — continua a leggere `no facts found` e a concludere
    che la memoria e' vuota. Il percorso stampato e' cio' che trasforma un
    mistero in un refuso, e `console` lo fa gia' (cli.py:1048).
    """
    db_a, _, _ = due_cartelle
    esito = _cli("recall", _QUERY, "--k", "5", "--db", str(db_a))
    assert esito.exit_code == 0
    #: il confronto e' sul NOME DEL FILE, non sul percorso intero: su Windows
    #: il percorso lungo va a capo nella resa a colonne e un `in` sul path
    #: pieno fallirebbe per l'a capo, non per il difetto.
    assert Path(db_a).name in esito.stdout, (
        "la risposta non dice quale store ha aperto: chi ha sbagliato "
        "cartella non ha modo di accorgersene, ed e' esattamente il P0")
