"""`L4.3` — i casi PRE-REGISTRATI, prima che il layer esistesse.

I casi non sono scelti dopo: vengono dal banco pre-registrato
`docs/stato-reale/banchi/ws3-F1-baseline-rossa-popolazione-A.py` (28/08), dalla
validazione **cieca** di ws5 (`a75ced2f`, 32 casi mai visti dall'autore) e dai
suoi tre falsi positivi. La regola è stata **corretta** dai suoi rilievi, quindi
i casi che l'hanno rotta stanno qui come presidio: se qualcuno riporta la
regola indietro, questi diventano rossi.

⚠️ Onestà sul processo: l'implementazione è stata scritta **prima** di questo
file, contro la regola di casa (TDD). La falsificazione è stata fatta lo stesso
e in modo verificabile — togliendo `verimem/soggetto_valore.py` il file va in
errore di raccolta, rimettendolo passa.
"""

from __future__ import annotations

import pytest

from verimem.soggetto_valore import avviso_soggetto_valore

CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)
REFERTO = (
    "Terapia in atto. Il paziente assume metformina 850 mg due volte al giorno. "
    "Il ramipril e' prescritto a 5 mg al mattino. "
    "L'acido acetilsalicilico e' prescritto a 100 mg alla sera."
)


def _parla(claim: str, fonte: str) -> bool:
    return avviso_soggetto_valore(claim, fonte) is not None


# ── ciò che il layer DEVE prendere: lo scambio di attribuzione ───────────
@pytest.mark.parametrize("claim", [
    "La cauzione definitiva e' pari a 148000 euro.",
    "L'importo contrattuale e' di 22000 euro.",
])
def test_scambio_su_importi_e_segnalato(claim: str) -> None:
    a = avviso_soggetto_valore(claim, CONTRATTO)
    assert a is not None, "lo scambio di attribuzione deve essere segnalato"
    assert a["layer"] == "L4.3"
    assert "attached to something else" in a["reason"]


@pytest.mark.parametrize("claim", [
    "Il ramipril e' prescritto a 850 mg al mattino.",
    "Il paziente assume metformina 5 mg due volte al giorno.",
    "L'acido acetilsalicilico e' prescritto a 850 mg alla sera.",
    "Il paziente assume metformina 100 mg due volte al giorno.",
    "L'acido acetilsalicilico e' prescritto a 5 mg alla sera.",
    "Il ramipril e' prescritto a 100 mg al mattino.",
])
def test_scambio_su_dosaggi_e_segnalato(claim: str) -> None:
    """Il caso difficile: il sostantivo di testa è condiviso («prescritto»).

    Senza le ancore DISCRIMINANTI questi vengono assolti: misurato, 6 su 12.
    """
    assert _parla(claim, REFERTO), "lo scambio fra farmaci deve essere segnalato"


# ── ciò che il layer NON deve toccare ───────────────────────────────────
@pytest.mark.parametrize("claim", [
    "Il ramipril e' prescritto a 5 mg al mattino.",
    "Il paziente assume metformina 850 mg due volte al giorno.",
])
def test_i_claim_veri_non_sono_segnalati(claim: str) -> None:
    assert not _parla(claim, REFERTO)


def test_il_vero_con_percentuale_non_e_segnalato() -> None:
    """G1 — senza unità non si accoppia.

    `extract_quantities` dà `('', 2.0)` a «2%» e `('', 3.0)` al «3» di «Art. 3»:
    accoppiarli segnalava questo claim VERO. Misurato il 28/08.
    """
    assert not _parla(
        "La penale per il ritardo e' pari al 2% dell'importo contrattuale.",
        CONTRATTO)


def test_finestra_ambigua_si_astiene() -> None:
    """R1 di ws5: cadere al passo successivo trova l'altro valore della STESSA
    frase e segnala un VERO. L'esito sicuro è l'astensione."""
    assert not _parla(
        "Il deposito e' di 2400 euro.",
        "Il canone e' di 1200 euro e il deposito e' di 2400 euro.")


def test_identificativi_non_sono_quantita() -> None:
    """R2 di ws5: un identificativo SEGUE il suo sostantivo, una quantità lo
    PRECEDE (`vicinato_del_valore.py:36-37`)."""
    assert not _parla(
        "L'ordine 77 e' stato evaso.",
        "L'ordine 77 risulta evaso. L'ordine 88 e' in attesa.")


def test_il_claim_che_cita_entrambi_i_valori_non_e_uno_scambio() -> None:
    """G2 — 27,6% dei falsi allarmi sul corpus reale (ws5)."""
    assert not _parla(
        "I quarantinati con un motivo registrato sono 623 euro su 2378 euro.",
        "I quarantinati sono 2378 euro, di cui 623 euro con un motivo.")


def test_stesso_numero_a_precisione_diversa_non_e_uno_scambio() -> None:
    """G3 — 2,5% dei falsi allarmi (ws5)."""
    assert not _parla(
        "La copertura e' di 97.6 giorni.",
        "La copertura misurata e' di 97.5968 giorni.")


def test_la_fonte_che_TACE_non_produce_avvisi() -> None:
    """Il cuore del perimetro: il layer scatta sulla CONTRADDIZIONE, mai sul
    SILENZIO. Qui la fonte non lega la metformina ad alcun dosaggio."""
    assert not _parla(
        "Il paziente assume metformina 850 mg.",
        "Il paziente assume metformina. Il dosaggio e' 850 mg.")


@pytest.mark.parametrize("claim", [
    "Il consiglio ha disposto l'affidamento al fornitore Bertani.",
    "Le spese di trasferta sono rimborsate al personale.",
    "Il contratto di servizio e' stato prorogato.",
])
def test_sull_omissione_il_layer_parla_ZERO_volte(claim: str) -> None:
    """R-ws4-2: «invariato» non è misurabile su una baseline che varia da sola
    (3/3 · 3/3 · 3/3 · 2/3). «Il layer parla zero volte» lo è, e non dipende
    dalla baseline."""
    fonte = ("L'affidamento al fornitore Bertani e' subordinato all'approvazione "
             "preventiva del collegio dei revisori. Il rimborso delle spese di "
             "trasferta e' ammesso solo entro il limite mensile fissato dal "
             "regolamento interno. La proroga del contratto di servizio decorre "
             "dalla scadenza originaria.")
    assert not _parla(claim, fonte)


def test_valore_assente_dalla_fonte_resta_a_L4_1() -> None:
    """Disgiunzione dichiarata: se il valore non è nella fonte, `L4.3` tace e
    parla `L4.1`. Nessun doppio referto sulla stessa ricevuta."""
    assert not _parla("Il ramipril e' prescritto a 73 mg al mattino.", REFERTO)


def test_la_fonte_lunga_non_indebolisce_il_layer() -> None:
    """La protezione del giudice si sgretola con la lunghezza (7/12 → 10/12
    ammessi); quella deterministica no. Qui la stessa fonte con 900 caratteri
    di clausole di stile SENZA cifre."""
    zavorra = (
        " Le parti danno atto di aver preso visione integrale del presente "
        "accordo e di accettarne ogni clausola senza riserva alcuna. Il foro "
        "competente in via esclusiva e' quello del luogo in cui ha sede la "
        "stazione appaltante. Ogni comunicazione fra le parti si intende "
        "validamente effettuata se trasmessa agli indirizzi in epigrafe. Le "
        "modifiche al presente atto sono valide soltanto se risultanti da atto "
        "scritto sottoscritto da entrambe le parti."
    )
    assert _parla("La cauzione definitiva e' pari a 148000 euro.",
                  CONTRATTO + zavorra)
