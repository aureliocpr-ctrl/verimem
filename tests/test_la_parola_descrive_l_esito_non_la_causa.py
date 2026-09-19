"""T158 — «unsupported claims» attribuisce una causa che vale per il 60%.

Misurato il 19/09 sul registro delle azioni, sola lettura::

    scritture quarantinate nel ledger  : 1316
      SENZA L4-grounding fra i layer   :  524      <- il 39,8%
      con SOLO L4-grounding            :  494

Quelle 524 sono state fermate da un numero che la fonte non contiene, da
un'unità riferita ad altro, da una negazione, da una coesistenza, da
un'auto-affermazione o da una banda incerta — e `L4-review` dichiara di sé
«held for review, **not admitted**», che è trattenuto, non insostenuto.

Il prodotto **sa già** chi ha fermato cosa: lo stampa tre righe dopo, sotto
«by layer», e la pagina HTML ha la sua card «Gate layers that fired». La riga
generalizza una causa mentre la verità è nello stesso schermo.

⚠️ LA COPIA: la stessa parola vive su DUE superfici che l'utente vede — la
riga della CLI e la card della pagina — più il docstring del modulo che
registra le azioni, da cui è partita. Curarne una sola le farebbe divergere:
è la classe ① (copia invece di superficie unica), e per questo il testo sta
in UNA funzione che entrambe chiamano, e questo banco prova ENTRAMBE.

⚠️ NESSUN MODELLO: la riga dipende da un numero, la card da una stringa. Un
banco che ci facesse passare uno store vero misurerebbe il corpus.
"""
from __future__ import annotations

from verimem.cli import riga_dei_quarantinati
from verimem.gateway import _DASHBOARD_HTML

#: La parola che attribuisce una causa, nelle due forme in cui è scritta.
BUGIE = ("unsupported claims stored hidden", "unsupported claims quarantined")


def test_la_riga_della_CLI_non_attribuisce_una_causa():
    """Il RED, superficie ①."""
    riga = riga_dei_quarantinati(1316)
    assert "unsupported" not in riga.lower(), (
        f"la riga dice «unsupported» di tutte le scritture trattenute, e 524 "
        f"su 1316 non hanno mai avuto un verdetto del giudice. Dice: {riga!r}"
    )


def test_la_card_della_PAGINA_non_attribuisce_una_causa():
    """Il RED, superficie ② — la copia che un censimento a mano può mancare."""
    assert "unsupported" not in _DASHBOARD_HTML.lower(), (
        "la pagina HTML porta ancora la parola: le due superfici direbbero "
        "cose diverse appena una delle due viene curata"
    )


def test_le_due_superfici_dicono_LA_STESSA_COSA():
    """Il cuore di T158: una parola sola, non due che si somigliano.

    Non basta che nessuna delle due menta — devono coincidere, altrimenti fra
    sei mesi divergono di nuovo e il banco non se ne accorge.
    """
    from verimem.trust_ledger import etichetta_dei_quarantinati
    parola = etichetta_dei_quarantinati()
    assert parola in riga_dei_quarantinati(7), "la CLI non usa la funzione unica"
    assert parola in _DASHBOARD_HTML, "la pagina non usa la funzione unica"


def test_CONTROLLO_il_conteggio_resta_quello_che_era():
    """La metà che non deve cambiare: la cura tocca la PAROLA, non il numero."""
    for n in (0, 7, 1316):
        assert f"quarantined: {n}" in riga_dei_quarantinati(n), (
            f"il conteggio non compare più nella riga per n={n}"
        )


def test_CONTROLLO_il_dettaglio_per_layer_resta_su_ENTRAMBE():
    """⚠️ IL CONTROLLO CHE PROTEGGE LA CURA DA SE STESSA.

    La riga rimanda al dettaglio per layer: se quel dettaglio sparisse, il
    rimando diventerebbe una promessa falsa — cioè lo stesso difetto curato,
    con il segno invertito. Questa cella passa PRIMA della cura e deve passare
    anche dopo.
    """
    import verimem.cli as _cli
    sorgente = _cli.__file__
    with open(sorgente, encoding="utf-8") as fh:
        testo_cli = fh.read()
    assert "by layer:" in testo_cli, (
        "la CLI non stampa più il dettaglio per layer: il rimando della riga "
        "punterebbe a qualcosa che non c'è"
    )
    assert "Gate layers that fired" in _DASHBOARD_HTML, (
        "la pagina non mostra più i layer che si sono accesi"
    )
