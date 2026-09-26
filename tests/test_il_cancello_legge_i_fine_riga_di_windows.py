"""T201 — il cancello cancellava una dichiarazione vera scritta su Windows.

🔴 MISURATO IL 23/09/2026 su #126. Il commento della Definition of Done portava
le due righe, `Registro:` e `Decisione:`, e il cancello rispondeva lo stesso:

    BOCCIATO  il corpo della richiesta
      - il commento della Definition of Done non porta «Registro: riga <n>», «Decisione: <n>»

Il commento era stato caricato con `gh api -F body=@file` da un file scritto su
Windows, quindi con i fine riga `\\r\\n`. Riprodotto il cancello in locale
esattamente come lo lancia il workflow, e dato il commento al filtro che lo
script applica prima di cercare i due campi:

    CRLF nel body: 53 | LF soli: 0
    prima  del filtro: 5306 caratteri | Registro dentro? True
    dopo   il filtro :  154 caratteri | Registro dentro? False
    stesso commento con i CRLF normalizzati -> 4645 caratteri | Registro dentro? True

`_senza_recinti` riconosce la CHIUSURA di un recinto con `[ \\t]*$`: una riga
`` ```\\r `` non chiude, il recinto resta aperto fino alla fine del commento, e
tutto cio' che segue sparisce — le due righe comprese. Il messaggio diceva «non
porta Registro» quando il Registro c'era: un righello che sbaglia SENZA DIRLO.

⚠️ ED E' LA SECONDA GAMBA DELLA CURA DEL 19/09, rotta da un'altra parte.
`test_il_cancello_distingue_un_esempio_da_una_dichiarazione.py` ha insegnato al
cancello a togliere i recinti, perche' un MODELLO incollato dentro un blocco
veniva letto come una dichiarazione. Il suo docstring avverte: «una cura che
bocciasse anche la dichiarazione vera costerebbe piu' del difetto». In CRLF e'
esattamente cio' che succedeva, e il suo controllo positivo non lo vedeva perche'
le sue stringhe sono in LF.

Lo stesso script normalizza gia' `\\r\\n` in un altro punto (per i commenti HTML):
la cura non inventa niente, porta quella normalizzazione dove mancava.

⚠️ E LA CURA NON DEVE RIAPRIRE IL BUCO CHE CHIUDEVA. La terza cella rifa' le
sei forme del 19/09 IN CRLF: un modello mostrato — in un recinto, rientrato,
citato, in un commento HTML — deve continuare a non valere come dichiarazione.
"""
from __future__ import annotations

import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "scripts"))
sys.path.insert(0, str(RADICE / "tests"))

import messaggio_pulito as mp  # noqa: E402
from test_il_cancello_distingue_un_esempio_da_una_dichiarazione import (  # noqa: E402
    LE_SEI_FORME,
)

CORPO = "Una riga sola di prosa.\n"

#: La dichiarazione vera si PRENDE dallo script, non si ricopia: scritta qui come
#: stringa letterale, questo file diventerebbe esso stesso un esempio che il
#: cancello legge (e' la ragione scritta nel presidio del 19/09).
DICHIARAZIONE_VERA = mp.DOD_IN_COMMENTO[0]


def _con_un_blocco_di_codice_prima_dei_due_campi(dod: str) -> str:
    """La forma di un DoD reale: un blocco con l'output, POI i due campi.

    E' la forma che ha rotto #126 — la misura sta in un recinto, e i due campi
    vengono dopo. Senza un recinto prima dei campi il difetto non si vede,
    perche' non c'e' nessun recinto da non chiudere.
    """
    i = dod.index("Registro:")
    blocco = "```\n3 failed, 1 passed in 44.47s\n4 passed in 37.72s\n```\n\n"
    return dod[:i] + blocco + dod[i:]


def _in_crlf(testo: str) -> str:
    """Lo stesso testo con i fine riga di Windows, come arriva da un file."""
    return testo.replace("\r\n", "\n").replace("\n", "\r\n")


def test_una_dichiarazione_vera_scritta_su_WINDOWS_passa():
    """La cella che era rossa: stesso contenuto, fine riga di Windows."""
    dod = _in_crlf(_con_un_blocco_di_codice_prima_dei_due_campi(DICHIARAZIONE_VERA))
    assert "\r\n" in dod, "il banco non sta misurando niente: nessun CRLF nel testo"

    problemi = mp.controlla_corpo(CORPO, commenti=[dod])

    assert not problemi, (
        "una dichiarazione vera con fine riga CRLF viene bocciata: il filtro dei "
        f"recinti non chiude `` ```\\r `` e cancella i due campi. Problemi: {problemi}")


def test_IL_CONTROLLO_POSITIVO_la_stessa_dichiarazione_in_LF_passa():
    """Senza questa, la cella sopra potrebbe essere rossa per un'altra ragione.

    Se il DoD costruito qui non passasse nemmeno in LF, il rosso della cella in
    CRLF non direbbe niente sui fine riga: direbbe che il banco e' sbagliato.
    """
    dod = _con_un_blocco_di_codice_prima_dei_due_campi(DICHIARAZIONE_VERA)
    assert "\r" not in dod

    assert not mp.controlla_corpo(CORPO, commenti=[dod])


def test_LE_SEI_FORME_in_CRLF_restano_bocciate():
    """La gamba che la cura non deve rompere: il presidio del 19/09, su Windows.

    Normalizzare i fine riga fa chiudere i recinti che prima restavano aperti.
    Se la cura fosse sbagliata — per esempio se togliesse i recinti DOPO aver
    deciso cosa e' dichiarato, o se trattasse `\\r` come testo — un modello
    incollato tornerebbe a valere come dichiarazione. Qui si controlla che non
    succeda in nessuna delle sei forme.
    """
    for nome, forma in LE_SEI_FORME:
        mostrato = _in_crlf(forma(DICHIARAZIONE_VERA))
        assert "\r\n" in mostrato, f"{nome}: nessun CRLF, la cella non misura niente"
        problemi = mp.controlla_corpo(CORPO, commenti=[mostrato])
        assert problemi, (
            f"{nome} in CRLF: il modello e' passato come se qualcuno avesse "
            "dichiarato — la cura dei fine riga ha riaperto il buco del 19/09")
