"""Una frase estranea nella fonte fa entrare la contraddizione IMPLICITA.

Misurato il 2026-08-26 alle 22:44, `93f57edc`, fuori da pytest, store isolato,
`validate="full"`, CE locale. Continua il banco di ws3
(`docs/stato-reale/banchi/ws3-la-contraddizione-implicita.py`), che aveva
misurato: implicita IT 3/10 ammesse, esplicita 0/10 — e concluso «non e' la
fonte, non e' il dominio, NON E' LA LUNGHEZZA». Le sue dieci fonti erano pero'
tutte di UNA frase: la lunghezza non era una variabile di quel banco.

    esplicite (i suoi 10 casi)   fonte corta 0/10   + una frase estranea 0/10
    implicite riformulate        fonte corta 0/12   + una frase estranea 4/12

⇒ La contraddizione ESPLICITA regge anche col contorno, e il punteggio scende
in 8 casi su 10 (3.5→2.3, 6.1→4.4, 4.7→2.5). Quella IMPLICITA no.

IL CASO PEGGIORE, riprodotto 3 giri su 3:

    fonte  «Verbale: il direttore ha rassegnato le dimissioni il 4 maggio.»
           + «La mensa aziendale resta chiusa il primo maggio.»
    claim  «Il direttore e' ancora in carica il 4 maggio.»
    esito  ammesso, grounding 99.9   (senza la frase sulla mensa: TRATT 0.9)

E sul claim originale di ws3 («e' stato CONFERMATO nell'incarico») il contorno
porta il moat da 1.8 a 99.9 — il giudice passa da «contraddetto» a «sostenuto» —
eppure il fatto resta trattenuto, `quarantined_by='L1'`, layer `L1.10`.
⇒ Su quel caso la garanzia non e' tenuta dal giudice: e' tenuta per caso da un
filtro lessicale, perche' il claim contiene una parola che L1.10 conosce.
Togliendo quella parola, tre riformulazioni su tre entrano.

⚠️ Limiti: le riformulazioni le ha scritte chi conosceva il difetto, quindi
questo NON e' un tasso di prodotto — e' la prova che esistono riformulazioni che
passano, su 2 domini su 4. Una sola frase di zavorra, sempre la stessa. Mai
misurato col giudice llm (`Memory(llm=...)`): il banco per quello e'
`docs/stato-reale/banchi/l_llm_chiude_davvero_le_due_lacune.py`.

Vicini: `test_una_frase_estranea_puo_ribaltare_il_moat.py` (stesso meccanismo su
una fonte inventata) · `test_il_gate_cerca_la_contraddizione_non_il_sostegno.py`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

ZAVORRA = "La mensa aziendale resta chiusa il primo maggio."
FONTE_DIMISSIONI = "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio."
FONTE_DECEDUTO = "Referto: il paziente e' deceduto il 30 luglio in terapia intensiva."

#: falsita' implicite riformulate — nessuna contiene un negatore
FALSITA = [
    (FONTE_DIMISSIONI, "Il direttore e ancora in carica il 4 maggio."),
    (FONTE_DIMISSIONI, "Il direttore resta alla guida della societa dal 4 maggio."),
    (FONTE_DECEDUTO, "Il paziente ha lasciato il reparto il 30 luglio sulle proprie gambe."),
]
#: la contraddizione ESPLICITA sulla stessa fonte: regge, ed e' il confronto
ESPLICITE = [
    (FONTE_DIMISSIONI, "Il direttore non ha rassegnato le dimissioni il 4 maggio."),
    (FONTE_DECEDUTO, "Il paziente non e' deceduto il 30 luglio."),
]


def _esito(claim: str, fonte: str) -> tuple[str, float | None, str]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "ci.db"))
    ric = mem.add(claim, topic="t/implicita", source=fonte, validate="full")
    return str(ric.get("status")), ric.get("grounding_score"), str(ric.get("quarantined_by"))


@pytest.mark.parametrize("fonte,claim", FALSITA)
def test_CONTROLLO_con_la_fonte_corta_la_falsita_e_trattenuta(fonte, claim):
    """Il righello: senza questo, l'xfail sotto non misura l'effetto del contorno."""
    stato, punteggio, _ = _esito(claim, fonte)
    assert stato == "quarantined", (
        f"gia' con la fonte corta {claim!r} entra ({stato}, g={punteggio}): il banco "
        "non misura piu' cio' che la zavorra aggiunge, rimisurare"
    )


@pytest.mark.parametrize("fonte,claim", ESPLICITE)
def test_LA_CONTRADDIZIONE_ESPLICITA_regge_anche_col_contorno(fonte, claim):
    """La meta' che tiene, e sta qui perche' il banco non deve esagerare.

    Sui dieci casi espliciti di ws3 le falsita' ammesse sono 0/10 con la fonte
    corta e 0/10 con una frase estranea. Il contorno non le aiuta a passare.
    """
    stato, punteggio, _ = _esito(claim, f"{fonte} {ZAVORRA}")
    assert stato == "quarantined", (
        f"una contraddizione ESPLICITA entra col contorno ({punteggio}): il difetto "
        "e' piu' esteso di quanto questo banco dichiari, allargare la misura"
    )


@pytest.mark.xfail(
    strict=True,
    reason="una frase estranea fa entrare la contraddizione implicita riformulata: "
    "0/12 con la fonte corta, 4/12 col contorno (26/08)",
)
@pytest.mark.parametrize("fonte,claim", FALSITA)
def test_la_falsita_implicita_non_dovrebbe_entrare_col_contorno(fonte, claim):
    stato, punteggio, _ = _esito(claim, f"{fonte} {ZAVORRA}")
    assert stato == "quarantined", f"ammessa con g={punteggio} grazie a una frase sulla mensa"


def test_A_TRATTENERE_il_claim_di_ws3_e_L1_non_il_moat():
    """Lo stato attuale: se diventa rosso perche' il moat lo giudica, e' un bene.

    Col contorno il grounding del claim originale di ws3 sale da 1.8 a 99.9 — il
    giudice lo dichiara sostenuto — e il fatto resta trattenuto solo perche'
    contiene una parola che L1.10 conosce.
    """
    stato, punteggio, chi = _esito(
        "Il direttore e' stato confermato nell'incarico il 4 maggio.",
        f"{FONTE_DIMISSIONI} {ZAVORRA}",
    )
    assert stato == "quarantined", f"ora entra ({punteggio}): il caso di ws3 e' peggiorato"
    assert chi == "L1", (
        f"a trattenerlo ora e' {chi!r} e non 'L1' (g={punteggio}): se e' il moat, "
        "ha imparato a vedere la contraddizione implicita — buona notizia, rimisurare"
    )
