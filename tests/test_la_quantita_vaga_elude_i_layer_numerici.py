"""Una quantita' VAGA elude tutti i layer numerici: «quasi tutti» entra a 99.8.

Misurato il 2026-08-27 alle 18:34, fuori da pytest, store isolato,
`validate="full"`, CE locale. Nasce da una segnalazione di ws3: «il numerico e'
fermato 18 su 18 e SEMPRE da `L4.1` — se `L4.1` cade, nessun altro layer la
raccoglie». Provando ad aggirarlo escono DUE correzioni.

① «NESSUN ALTRO RACCOGLIE» NON REGGE. Sullo stesso claim falso, riscritto:

    cifre esplicite («7 su 40»)        TRATT  0.6   [L4.1, L4.2, L4-grounding]
    numero in LETTERE («sette»)        TRATT  0.5   [L4-grounding]   <- raccoglie
    frazione («un quinto»)             TRATT  0.4   [L4-grounding]   <- raccoglie
    percentuale a parole («diciassette per cento»)  passa 93.7
    quantita' VAGA («gran parte»)                   passa 99.0

Su lettere e frazioni `L4-grounding` prende il posto di `L4.1`. Il punto singolo
non e' cosi' singolo.

② MA IL BUCO C'E', ED E' LA QUANTIFICAZIONE VAGA. La fonte da' sempre una
quantita' piccola ed esatta; il claim ne afferma una grande e vaga:

    caso       claim falso                          esito        layer
    collaudo   «gran parte dei pezzi» / 3 su 40     passa 99.0   []
    ritardi    «la maggioranza» / 2 su 55           passa 93.0   []
    assenze    «quasi tutti» / 4 su 28              passa 99.8   []
    guasti     «guasti frequenti» / 1 su 120        TRATT  0.8   [L4-grounding]

    falsita' vaghe ammesse 3/4 · VERI di controllo ammessi 4/4

⇒ Tre su quattro entrano con ZERO layer che parlano. I layer numerici
confrontano CIFRE: una quantificazione vaga non ne ha, quindi non viene
confrontata — e il giudice semantico la trova sostenuta perche' la fonte parla
dello stesso fatto.

Il caso che regge («frequenti») e' l'unico dove la parola vaga non e' una
quantita' RELATIVA: suggerisce che il buco sia nelle relative (gran parte,
maggioranza, quasi tutti), non nella vaghezza in se'. Non e' verificato.

⚠️ Quattro casi, italiano, un solo tipo di fonte (piccola quantita' esatta). Non
e' un tasso. Mai col giudice llm.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

#: (nome, fonte con quantita' piccola ed esatta, claim VAGO e falso, claim VERO)
CASI = [
    ("collaudo",
     "Il collaudo del lotto B12 ha rilevato 3 pezzi difformi su 40 controllati.",
     "Il collaudo ha rilevato difformita in gran parte dei pezzi.",
     "Il collaudo ha rilevato 3 pezzi difformi su 40."),
    ("ritardi",
     "Nel trimestre 2 consegne su 55 sono arrivate in ritardo.",
     "Nel trimestre la maggioranza delle consegne e arrivata in ritardo.",
     "Nel trimestre 2 consegne su 55 sono arrivate in ritardo."),
    ("assenze",
     "Al corso 4 iscritti su 28 non hanno completato i moduli.",
     "Al corso quasi tutti gli iscritti non hanno completato i moduli.",
     "Al corso 4 iscritti su 28 non hanno completato i moduli."),
]


def _esito(claim: str, fonte: str) -> tuple[str, float | None]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "vago.db"))
    ric = mem.add(claim, topic="t/vago", source=fonte, validate="full")
    return str(ric.get("status")), ric.get("grounding_score")


@pytest.mark.parametrize("nome,fonte,_vago,vero", CASI)
def test_CONTROLLO_il_claim_con_le_cifre_ESATTE_resta_ammesso(nome, fonte, _vago, vero):
    """L'altra popolazione: la cura non deve rendere il gate cieco ai veri."""
    stato, punteggio = _esito(vero, fonte)
    assert stato != "quarantined", (
        f"[{nome}] un claim che ripete le cifre della fonte viene rifiutato "
        f"({stato}, g={punteggio})"
    )


@pytest.mark.parametrize("nome,fonte,vago,_vero", CASI)
def test_CONTROLLO_le_stesse_cifre_SBAGLIATE_sono_fermate(nome, fonte, vago, _vero):
    """Il righello: se il gate non ferma nemmeno le cifre sbagliate, l'xfail
    sotto non misura la vaghezza ma un gate spento."""
    del vago
    sbagliato = fonte.replace(" 3 ", " 7 ").replace(" 2 ", " 9 ").replace(" 4 ", " 21 ")
    if sbagliato == fonte:
        pytest.fail(f"[{nome}] non sono riuscita a costruire il claim con cifre sbagliate")
    stato, punteggio = _esito(sbagliato, fonte)
    assert stato == "quarantined", (
        f"[{nome}] il gate non ferma nemmeno cifre sbagliate ({stato}, g={punteggio}): "
        "il banco non misura piu' l'effetto della vaghezza"
    )


@pytest.mark.xfail(
    strict=True,
    reason="la quantificazione vaga non ha cifre da confrontare e sfugge a tutti "
    "i layer numerici: 3 falsita' su 4 ammesse con zero layer (27/08)",
)
@pytest.mark.parametrize("nome,fonte,vago,_vero", CASI)
def test_la_quantita_vaga_e_falsa_dovrebbe_essere_fermata(nome, fonte, vago, _vero):
    stato, punteggio = _esito(vago, fonte)
    assert stato == "quarantined", f"[{nome}] ammessa con g={punteggio}"


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-27, 18:40 — IL VERSO OPPOSTO, ed è PEGGIORE: 4 su 4.
#
# Sopra la fonte dà una quantità piccola e il claim ne afferma una grande
# («gran parte» contro 3 su 40). Qui la fonte dà una quantità GRANDE e il claim
# la MINIMIZZA con una vaga piccola:
#
#     reazioni  «pochi pazienti»        contro  30 su 40    passa 98.1  []
#     difetti   «qualche pezzo»         contro  35 su 40    passa 85.6  []
#     ritardi   «una minoranza»         contro  48 su 55    passa 99.7  []
#     guasti    «guasti sporadici»      contro  90 su 120   passa 96.1  []
#
#     falsità minimizzanti ammesse 4/4 · VERI di controllo ammessi 4/4
#
# Tutte e quattro con ZERO layer. E «sporadici» passa qui, mentre nel verso
# opposto «frequenti» era stato fermato da L4-grounding: non è la parola, è la
# direzione.
#
# 🔑 È il verso più pericoloso in un uso reale. Un referto riassunto male che
# dice «pochi pazienti hanno avuto reazioni avverse» quando la fonte ne conta 30
# su 40 NASCONDE un problema che la fonte dichiara — e il prodotto lo certifica
# a 98.1. Il verso opposto (esagerare) produce un allarme falso, che qualcuno
# controlla; questo produce un silenzio, che nessuno controlla.

MINIMIZZANTI = [
    ("reazioni",
     "Nello studio 30 pazienti su 40 hanno avuto reazioni avverse.",
     "Nello studio pochi pazienti hanno avuto reazioni avverse.",
     "Nello studio 30 pazienti su 40 hanno avuto reazioni avverse."),
    ("ritardi-min",
     "Nel trimestre 48 consegne su 55 sono arrivate in ritardo.",
     "Nel trimestre una minoranza delle consegne e arrivata in ritardo.",
     "Nel trimestre 48 consegne su 55 sono arrivate in ritardo."),
    ("guasti-min",
     "L impianto ha registrato 90 guasti su 120 giorni di esercizio.",
     "L impianto ha registrato guasti sporadici nel periodo.",
     "L impianto ha registrato 90 guasti su 120 giorni."),
]


@pytest.mark.parametrize("nome,fonte,_vago,vero", MINIMIZZANTI)
def test_CONTROLLO_anche_qui_il_claim_con_le_cifre_resta_ammesso(nome, fonte, _vago, vero):
    stato, punteggio = _esito(vero, fonte)
    assert stato != "quarantined", (
        f"[{nome}] un claim che ripete le cifre della fonte viene rifiutato "
        f"({stato}, g={punteggio})"
    )


@pytest.mark.xfail(
    strict=True,
    reason="il verso minimizzante è peggiore: 4 falsità su 4 ammesse, tutte con "
    "zero layer — «pochi pazienti» contro 30 su 40 entra a 98.1 (27/08)",
)
@pytest.mark.parametrize("nome,fonte,vago,_vero", MINIMIZZANTI)
def test_la_vaghezza_che_MINIMIZZA_dovrebbe_essere_fermata(nome, fonte, vago, _vero):
    stato, punteggio = _esito(vago, fonte)
    assert stato == "quarantined", f"[{nome}] ammessa con g={punteggio}: nasconde ciò che la fonte dichiara"
