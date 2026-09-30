"""T118 — `text=True` senza `encoding=` legge con la codifica di SISTEMA.

Su Windows quella codifica è cp1252, e il thread che legge la pipe del figlio
MUORE sul primo byte che cp1252 non sa decodificare. Il processo esce 0 e il
canale torna `None`: il guasto non somiglia a un guasto.

MISURATO, meccanismo deterministico (457 byte + 0x8d, un braccio per volta)::

    preferredencoding: cp1252
    SENZA encoding (come il chiamante):   exit=0  stdout=NoneType/None
    CON encoding=utf-8, errors=replace:   exit=0  stdout=str/458
    UnicodeDecodeError: 'charmap' codec can't decode byte 0x8d in position 457

E in CI è già costato: nel job `test (windows-latest / py3.12)` della richiesta
#73 l'avviso compare **6 volte** (`PytestUnhandledThreadExceptionWarning`) su
tre celle, con lo stesso traceback (`subprocess.py:_readerthread` ->
`encodings/cp1252.py`).

🔑 PERCHÉ UNA CELLA E NON OTTO RIGHE E BASTA. La regola è scritta nel repo dal
**3 settembre** (`.github/workflows/ci.yml`, col suo RED a `PYTHONUTF8=0`) e un
sito di prodotto la applica già (`verimem/band_escalation.py`). Non ha
contagiato gli altri perché **nessuno conta**: una riga che manca non emette
segnale. Questa cella è il contatore, e scende soltanto.

⚠️ NON si cura mettendo `encoding=` in `quiet_popen_kwargs()`, che pure è la
superficie condivisa: delle 14 chiamate che lo spargono, **5 leggono BYTE** e
decodificano a mano (`code.py`, `ide.py`, `interactive_judge.py`,
`provenance_validator.py` ×2). `encoding=` lì dentro cambierebbe loro il TIPO
in silenzio, e nessun banco lo chiede. Quelle cinque non sono difettose: usano
l'altro idioma, che è corretto.

Ticket T118. Registro: riga nuova, classe «manca lo sweep».
Decisione: nessuna, non cambia il comportamento del prodotto.
"""
from __future__ import annotations

import pathlib
import re

#: Una chiamata a subprocess, parentesi annidate di UN livello — basta per le
#: chiamate vere di questo repo e non tira dentro mezzo file.
CHIAMATA = re.compile(
    r"subprocess\.(?:run|Popen|check_output)\((?:[^()]|\([^()]*\))*\)", re.S)

RADICE = pathlib.Path(__file__).resolve().parents[1] / "verimem"


def _in_modo_testo_senza_codifica(sorgente: str) -> list[int]:
    """Le RIGHE (1-based) delle chiamate che leggono testo senza dichiararla."""
    fuori: list[int] = []
    for m in CHIAMATA.finditer(sorgente):
        blocco = m.group(0)
        if "encoding=" in blocco:
            continue
        if "text=True" in blocco or "universal_newlines=True" in blocco:
            fuori.append(sorgente[:m.start()].count("\n") + 1)
    return fuori


def test_CONTROLLO_il_rilevatore_SI_ACCENDE():
    """Il controllo positivo: senza, una regex che non trova niente è verde.

    Tre esemplari — il difetto, la forma già curata, e il modo BYTE che NON va
    toccato: se il rilevatore ne segnalasse uno degli ultimi due, la cura
    cambierebbe il tipo a chi legge byte.
    """
    difetto = 'subprocess.run(cmd, capture_output=True, text=True, timeout=5)'
    curato = ('subprocess.run(cmd, capture_output=True, text=True,\n'
              '               encoding="utf-8", errors="replace")')
    byte = 'subprocess.run(cmd, capture_output=True, timeout=5)'

    assert _in_modo_testo_senza_codifica(difetto) == [1], (
        "il rilevatore NON vede il difetto: questa cella non può fallire, "
        "quindi il suo verde non vuol dire niente.")
    assert _in_modo_testo_senza_codifica(curato) == [], (
        "il rilevatore segnala una chiamata GIÀ curata: darebbe lavoro finto.")
    assert _in_modo_testo_senza_codifica(byte) == [], (
        "il rilevatore segnala una chiamata in modo BYTE: curarla le "
        "cambierebbe il tipo del risultato, che è il difetto peggiore dei due.")


def test_nessuna_lettura_di_un_figlio_usa_la_codifica_di_sistema():
    """IL CRICCHETTO: oggi zero, e da qui può solo restare zero."""
    scoperte: list[str] = []
    for p in sorted(RADICE.rglob("*.py")):
        try:
            sorgente = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):  # pragma: no cover
            continue
        for riga in _in_modo_testo_senza_codifica(sorgente):
            scoperte.append(f"{p.relative_to(RADICE.parent).as_posix()}:{riga}")

    assert not scoperte, (
        "queste chiamate leggono l'output di un figlio con la codifica di "
        "SISTEMA (cp1252 su Windows): il thread lettore muore sul primo byte "
        "che non sa decodificare, il processo esce 0 e il canale torna None.\n"
        "  " + "\n  ".join(scoperte) + "\n"
        "Cura, la stessa già usata in verimem/band_escalation.py e dichiarata "
        "in .github/workflows/ci.yml: aggiungi "
        '`encoding="utf-8", errors="replace"`.')
