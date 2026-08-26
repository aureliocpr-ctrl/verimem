"""Ripetere due volte la stessa frase che smentisce il claim lo fa ENTRARE.

Nessun contenuto nuovo, nessuna zavorra, nessuna riformulazione: la stessa
identica frase, due volte. Misurato il 2026-08-26 alle 22:56, `191f65d3`, fuori
da pytest, `validate="full"`, CE locale, **store nuovo per ogni cella**:

    fonte  «Verbale: il direttore ha rassegnato le dimissioni il 4 maggio.»
    claim  «Il direttore e' ancora in carica il 4 maggio.»       (falso)
        x1  ->  TRATT  0.9
        x2  ->  passa 97.2
    tre giri indipendenti: 0.9/97.2 · 0.9/97.2 · 0.9/97.2

La fonte raddoppiata e' logicamente identica a se stessa. Non e' il significato:
e' il giudizio.

QUATTRO DOMINI — 3 su 4 ribaltano con UNA ripetizione, il quarto sale in scala:

    dimissioni  TRATT  0.9   passa 97.2
    lotto       TRATT  1.8   passa 94.3
    deceduto    TRATT 61.4   passa 98.6
    demolito    TRATT  0.8   TRATT 40.4   TRATT 94.9   TRATT 98.3   (x1..x4)

⚠️ IL TASSO, misurato il 26/08 alle 23:17 su una popolazione NON SCELTA DA ME —
la batteria di dieci casi di ws3, IT ed EN appaiati:

    ribaltamenti per ripetizione   italiano 1/10   inglese 1/10

I quattro casi qui sopra erano SELEZIONATI: li avevo trovati proprio perche'
ribaltavano, quindi il «3 su 4» descrive la mia selezione e non il prodotto. Il
numero onesto e' 1/10 per lingua. Il fenomeno resta, e resta in DUE lingue —
non e' un difetto italiano — ma non e' la regola: e' la coda.

E in altri due casi il punteggio ESPLODE senza ribaltare, perche' un layer
lessicale tiene il fatto mentre il giudice ha gia' ceduto:

    IT «dimissioni»  TRATT 1.8 -> TRATT 99.3
    EN «fallimento»  TRATT 0.4 -> TRATT 79.1

⇒ Contare i soli ribaltamenti SOTTOSTIMA il fenomeno: il giudizio si muove di
90 punti anche dove l'esito non cambia.

DUE SPIEGAZIONI GIA' FALSIFICATE, e stanno qui perche' nessuno le riprovi:

  · «e' il MAX su finestre»: g(A+B)=99.9 con max(g(A),g(B))=1.6. Il punteggio
    del tutto non e' derivabile dalle parti — nessuna delle due frasi, da sola,
    sostiene il claim (0.9 e 1.6); insieme lo sostengono a 99.9.
  · «e' la LUNGHEZZA»: allungare con riempimento senza senso («xxxx yyyy zzzz»,
    83 char) lascia 0.7, e «Nota interna numero 4.» (85 char) lascia 1.2.
    Serve testo linguisticamente pieno, non lunghezza.

Non c'e' una spiegazione in questo file, e non e' una dimenticanza: il fenomeno
e' deterministico e riproducibile, il meccanismo non lo so.

PERCHE' NON E' DA LABORATORIO: i documenti veri ripetono. Un log ripete la riga,
un verbale l'intestazione, un referto il nome del paziente, l'output di pytest il
nodeid. Nel caso d'uso reale la ripetizione e' la norma — e la garanzia in
vetrina «a claim the source contradicts does not come back as truth» e' misurata
su fonti di UNA frase (batteria di ws3,
`docs/stato-reale/banchi/ws3-la-contraddizione-implicita.py`).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

#: (nome, fonte che smentisce il claim, claim falso)
CASI = [
    ("dimissioni",
     "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio.",
     "Il direttore e ancora in carica il 4 maggio."),
    ("lotto",
     "Due pezzi del lotto B12 risultano difformi.",
     "Il lotto B12 e conforme alle specifiche."),
    ("deceduto",
     "Referto: il paziente e' deceduto il 30 luglio in terapia intensiva.",
     "Il paziente ha lasciato il reparto il 30 luglio sulle proprie gambe."),
]
#: il caso che non ribalta a x2 ma sale monotono: 0.8 -> 40.4 -> 94.9 -> 98.3
MONOTONO = ("Perizia: il capannone e' stato demolito nel 2024.",
            "Il capannone ospita ancora la linea di produzione.")


def _esito(claim: str, fonte: str) -> tuple[str, float | None]:
    """Store NUOVO a ogni chiamata: nessuna contaminazione fra scritture."""
    mem = Memory(str(Path(tempfile.mkdtemp()) / "rip.db"))
    ric = mem.add(claim, topic="t/ripetuta", source=fonte, validate="full")
    return str(ric.get("status")), ric.get("grounding_score")


@pytest.mark.parametrize("nome,fonte,claim", CASI)
def test_CONTROLLO_con_la_fonte_scritta_una_volta_la_falsita_e_fermata(nome, fonte, claim):
    """Il righello. Se cade lui, l'xfail sotto non misura la ripetizione."""
    stato, punteggio = _esito(claim, fonte)
    assert stato == "quarantined", (
        f"[{nome}] la falsita' entra gia' con la fonte scritta una volta "
        f"({stato}, g={punteggio}): il banco non misura piu' l'effetto della "
        "ripetizione, rimisurare"
    )


@pytest.mark.xfail(
    strict=True,
    reason="ripetere la stessa frase due volte ribalta il verdetto: 0.9 -> 97.2, "
    "deterministico su tre giri con store nuovo (26/08)",
)
@pytest.mark.parametrize("nome,fonte,claim", CASI)
def test_ripetere_la_fonte_non_dovrebbe_cambiare_il_verdetto(nome, fonte, claim):
    stato, punteggio = _esito(claim, f"{fonte} {fonte}")
    assert stato == "quarantined", f"[{nome}] ammessa con g={punteggio} ripetendo la fonte"


def test_IL_PUNTEGGIO_CRESCE_COL_NUMERO_DI_COPIE():
    """La forma piu' nuda del fenomeno: nessun ribaltamento, solo la scala.

    Il caso «demolito» resta trattenuto fino a x4, ma il grounding sale
    monotono — 0.8, 40.4, 94.9, 98.3 — su una fonte che ripete sempre la stessa
    frase. Se un giorno smette di salire, il difetto e' curato: rimisurare tutto
    il banco, e' una buona notizia.
    """
    fonte, claim = MONOTONO
    punteggi = [_esito(claim, " ".join([fonte] * n))[1] for n in (1, 2, 4)]
    assert all(isinstance(p, (int, float)) for p in punteggi), (
        f"un punteggio manca: {punteggi} — senza numeri il confronto non si fa"
    )
    assert punteggi[0] < punteggi[1] < punteggi[2], (
        f"il punteggio non cresce piu' con le copie ({punteggi}): se si e' "
        "stabilizzato, il difetto e' curato e il banco va rimisurato"
    )
    assert punteggi[2] > 90, (
        f"a quattro copie il grounding e' {punteggi[2]} e non piu' >90: "
        "il fenomeno si e' attenuato, rimisurare"
    )
