"""Il perimetro del pacchetto: cio' che nessuna porta raggiunge non viaggia nel wheel.

Misurato il 2026-09-17 aprendo il wheel di quel giorno
(`verimem-0.7.7-py3-none-any.whl`, 2 301 566 byte, 424 moduli `.py`): conteneva
**62 moduli su 62** che nessuna delle tre porte (SDK, CLI, MCP) raggiunge —
9 908 righe non vuote installate su ogni macchina senza servire a niente. La
prova fu eseguita spegnendo quei moduli con un `sys.meta_path` e usando il
prodotto dalle tre porte su sei operazioni: zero tentativi di importarli.

QUESTO test e' il cancello VELOCE del repo: non costruisce il wheel, controlla
l'invariante che lo rende vero — un modulo archiviato in `attic/` non deve
esistere anche in `verimem/`. Il cancello LENTO, che apre il wheel costruito,
vive nel passo di CI della release.

PERCHE' `attic/` E NON UN ELENCO IN `pyproject.toml`: `packages.find` elenca
PACCHETTI, non moduli. Con `verimem` incluso, tutti i suoi `.py` entrano nel
wheel: 61 dei 62 sono file dentro `verimem/`, quindi nessun elenco di pacchetti
li togliera' mai. Il perimetro si impone spostando i file fuori dal pacchetto.
`attic/` sta al livello della radice — non sotto `verimem/`, che verrebbe
ripreso da `include = ["verimem*"]` — e' versionata, non e' installata, e non
si cancella: il codice resta leggibile a chi lo cerca.

PERCHE' L'ELENCO NON E' SCRITTO QUI: la fonte e' `attic/` stessa. Un elenco
copiato in un test e' una seconda verita' che divergera' dalla prima.
"""
from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ATTIC = RADICE / "attic"
PACCHETTO = RADICE / "verimem"


def _moduli_in_attic() -> list[str]:
    """I nomi di modulo archiviati, letti da `attic/` (unica fonte)."""
    if not ATTIC.is_dir():
        return []
    return sorted(
        p.stem for p in ATTIC.rglob("*.py")
        if "__pycache__" not in p.parts and p.stem != "__init__"
    )


def _anche_nel_pacchetto(nomi: list[str]) -> list[str]:
    """Quali di questi nomi esistono ANCHE dentro `verimem/`.

    E' la funzione che decide, e i tre test la usano tutti e tre: quello del
    perimetro, quello che verifica di non essere vacuo, e il CONTROLLO che le
    passa un nome vivo per vederla accendere.
    """
    dentro = []
    for nome in nomi:
        if (PACCHETTO / f"{nome}.py").is_file():
            dentro.append(nome)
            continue
        if any(p.stem == nome for p in PACCHETTO.rglob("*.py")
               if "__pycache__" not in p.parts):
            dentro.append(nome)
    return dentro


def test_l_archivio_esiste_e_non_e_vuoto() -> None:
    """Un perimetro senza archivio non e' un perimetro: e' un insieme vuoto.

    Senza questo, il test del perimetro passerebbe su un repo dove `attic/` non
    esiste — verde per assenza di misura, che e' il modo piu' facile di
    consegnare un cancello che non guarda niente.
    """
    nomi = _moduli_in_attic()
    assert ATTIC.is_dir(), (
        f"{ATTIC} non esiste: il perimetro del wheel non e' imposto. "
        "I moduli che nessuna porta raggiunge stanno ancora dentro il pacchetto "
        "e vengono installati da `pip install`."
    )
    assert nomi, (
        f"{ATTIC} esiste ma non contiene moduli: il cancello del perimetro "
        "girerebbe su un insieme vuoto e sarebbe verde senza misurare nulla."
    )


def test_il_pacchetto_non_contiene_i_moduli_archiviati() -> None:
    """Il perimetro: un modulo archiviato non sta anche nel pacchetto.

    Se ci sta, il wheel se lo porta comunque e l'archiviazione e' apparente:
    il file in `attic/` diventa una copia morta e quello in `verimem/` continua
    a viaggiare.
    """
    nomi = _moduli_in_attic()
    doppioni = _anche_nel_pacchetto(nomi)
    assert not doppioni, (
        f"{len(doppioni)} moduli stanno in attic/ E in verimem/, quindi "
        f"viaggiano ancora nel wheel: {doppioni}"
    )


def test_CONTROLLO_il_cancello_si_accende_su_un_modulo_vivo() -> None:
    """Il controllo NEGATIVO, chiesto dal metodo: la logica deve saper dire NO.

    `quantity_match` e' nel pacchetto e ci resta (lo carica il gate su ogni
    scrittura). Passato all'elenco dei proibiti, `_anche_nel_pacchetto` DEVE
    trovarlo: se non lo trova, non sta leggendo l'albero e il verde del test
    del perimetro non vale niente.
    """
    assert _anche_nel_pacchetto(["quantity_match"]) == ["quantity_match"], (
        "il cancello non trova `quantity_match` dentro verimem/: non sta "
        "guardando l'albero, e allora nemmeno i moduli archiviati li vedrebbe"
    )
    assert _anche_nel_pacchetto(["modulo_che_non_esiste_affatto"]) == [], (
        "il cancello trova un nome inventato: sta rispondendo di si' a tutto"
    )
