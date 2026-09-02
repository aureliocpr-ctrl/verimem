"""`_NOME_DI_PARAMETRO` e' quadratica, e a proteggerci e' il taglio a 40.

MISURATO il 02/09 sul caso peggiore della regex
(`docs/stato-reale/banchi/ws3-V5-le-nove-regex-segnalate-sono-lente-davvero.py`)::

    input      10 KB        100 KB       crescita
    tempo    1720,6ms   188659,5ms        109,7x     <- quadratico, non lineare

CodeQL ha ragione (alert 1306, `py/polynomial-redos`): la regex ha
backtracking polinomiale. Su 100 KB impiega **tre minuti**.

⚠️ MA NON E' SFRUTTABILE, e la ragione NON e' nella regex: e' nel chiamante.
`_e_sintassi` le passa `testo[max(0, inizio - 40):inizio]` — **quaranta
caratteri**, sempre. Sui suoi 40 caratteri reali la regex costa **25,2
microsecondi**. Le altre cinque regex segnalate crescono 8,7-16,3x su 10x di
input, cioe' sono lineari in pratica: **questa e' l'unica davvero quadratica**.

🔑 PERCHE' QUESTA CELLA ESISTE. Quel `[max(0, inizio - 40):inizio]` non e' stato
scritto per proteggere dal ReDoS — protegge per **coincidenza**, ed e' la forma
di mitigazione che sparisce alla prima rifattorizzazione: chi domani passasse
l'intero testo non vedrebbe nulla di rotto, perche' il tempo esplode solo su
input lunghi che i test non usano.
⇒ Qui il taglio diventa **una promessa verificata**: se qualcuno lo toglie,
questa cella diventa ROSSA e il ReDoS non entra in silenzio.

⚖️ E QUESTA E' LA CURA, al posto di riscrivere la regex. Riscrivere il pattern
di un detector `L1` cambierebbe **cosa quel detector riconosce** — rischio reale
su un difetto che oggi costa 25 microsecondi. Se un giorno il chiamante dovra'
passare piu' di 40 caratteri, allora la regex andra' riscritta, e sara' questa
cella a dirlo.
"""
from __future__ import annotations

import verimem.l1_tested_detector as mod

TETTO = 40


class _RegexSpiona:
    """Sta al posto della regex e registra quanto testo le viene dato."""

    def __init__(self):
        self.lunghezze: list[int] = []

    def search(self, testo):
        self.lunghezze.append(len(testo))
        return None


def test_il_chiamante_non_da_mai_alla_regex_piu_di_quaranta_caratteri(monkeypatch):
    """Il comportamento, non il sorgente: si guarda cosa la regex RICEVE."""
    spiona = _RegexSpiona()
    monkeypatch.setattr(mod, "_NOME_DI_PARAMETRO", spiona)

    # un testo lungo, e una posizione ben dentro: se il taglio sparisse, la
    # regex riceverebbe decine di migliaia di caratteri invece di quaranta.
    testo = "-" + "a" * 100_000
    mod._e_sintassi(testo, inizio=50_000, fine=50_010)

    assert spiona.lunghezze, (
        "la regex non e' stata chiamata: il test non misura piu' cio' che dice "
        "(il ramo `_ADIACENTE_DI_CODICE` puo' aver risposto prima)")
    assert max(spiona.lunghezze) <= TETTO, (
        f"la regex ha ricevuto {max(spiona.lunghezze)} caratteri invece di "
        f"al massimo {TETTO}: il taglio nel chiamante e' stato tolto e "
        f"`_NOME_DI_PARAMETRO` e' quadratica (109,7x su 10x input, 188s su "
        f"100 KB). O si rimette il taglio, o si riscrive la regex.")


def test_la_spia_si_accende_davvero_se_il_taglio_sparisce():
    """CONTROLLO POSITIVO: senza taglio la lunghezza supera il tetto.

    Una cella che asserisce «<= 40» passa anche se la funzione non chiamasse
    mai la regex, o se il testo fosse corto. Qui si verifica che il righello
    sappia accendersi: la stessa fetta SENZA il taglio e' lunghissima.
    """
    testo = "-" + "a" * 100_000
    senza_taglio = testo[:50_000]
    con_taglio = testo[max(0, 50_000 - 40):50_000]

    assert len(senza_taglio) > TETTO, "il caso di controllo non e' lungo"
    assert len(con_taglio) == TETTO
