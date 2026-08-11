"""`S-001` letto come «1 contiene»: il codice che DISTINGUE prova il conflitto.

TROVATO seguendo il referto di ws5 sulla scala — «duecento record scritti, uno
vivo: il corpus ha capienza UNO» — e cercando *perché* un prefisso numerato nel
testo porta la perdita dal 98% a zero. La risposta sta nel parser delle
quantità:

    «Il campione S-001 contiene piombo a 11 mg/l»  ->  ('contiene', 1.0) …
    «Il campione S-002 contiene cadmio a 12 mg/l»  ->  ('contiene', 2.0) …
    numeric_conflict  ->  ('contiene', 1.0, 2.0)

Il `001` del codice viene letto come un VALORE e la parola che segue come la sua
UNITÀ. Due schede con codici diversi risultano quindi «la stessa grandezza con
due valori» — cioè una contraddizione. **L'identificatore che distingue i due
record diventa la prova che si contraddicono**, ed è il contrario del suo
mestiere.

Sul corpus vivo: **908 fatti su 6109 (15%)** contengono un identificatore
`LETTERA-CIFRE`, e i più frequenti non sono codici di laboratorio ma i nomi che
usiamo ogni giorno — `glm-5`, `GPT-5`, `gemini-2`, `opus-4`, `round-2`, `top-10`.

    «Il caccia F-16 vola a 2000 km orari»   ->  ('vola', 16.0)
    «Il magazzino K-77 ha 4200 metri quadri» ->  ('', 77.0)

**E LE DATE ISO, che scriviamo in continuazione:**

    «Il report del 2026-08-04 conta 42 righe»  ->  ('', 8.0), ('conta', 4.0)

Due report di due giorni diversi hanno «conta 4» e «conta 5»: stessa unità,
valori diversi. `YEAR_RE` esclude già l'anno nudo — il mese e il giorno di una
data completa no.

⚠️ QUESTA CURA È DIVERSA DA QUELLE GIÀ CADUTE, e la differenza è il motivo per
cui vale la pena provarla. Non tocca `content_tokens` (conservare token corti e
cifre: falsificato, le coppie sopra soglia da 848 a 2293), non alza soglie
(margine +0.000), non è il veto sulle entità (caduto). **Toglie un falso
positivo alla radice**: un codice non è una misura, e non lo era nemmeno prima.

⚠️ IL PRESIDIO: le quantità vere non si toccano. «4200 metri quadri», «11 mg/l»,
«2000 km orari» devono continuare a essere estratte — anche quando stanno nella
stessa frase di un identificatore, che è il caso normale.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities, numeric_conflict


def _valori(testo: str) -> set[float]:
    return {v for _, v in extract_quantities(testo)}


#: (frase, numero che NON è una quantità)
NON_SONO_QUANTITA = [
    ("Il campione S-001 contiene piombo a 11 milligrammi per litro.", 1.0),
    ("Il magazzino K-77 ha 4200 metri quadri.", 77.0),
    ("Il caccia F-16 vola a 2000 chilometri orari.", 16.0),
    ("Il modello GPT-5 ha risposto in 3 secondi.", 5.0),
    ("Il lotto REF-42 pesa 8 chilogrammi.", 42.0),
]


@pytest.mark.parametrize("frase,intruso", NON_SONO_QUANTITA)
def test_un_identificatore_non_e_una_quantita(frase, intruso):
    """Il cuore: `S-001` identifica un record, non misura niente. Leggerlo come
    valore fa sì che due schede diverse risultino in conflitto.

    ✅ CURATO il 2026-08-11 da `_senza_identificatori` in `quantity_match`: i
    cinque casi qui sopra sono diventati `XPASS(strict)` nella stessa esecuzione
    in cui la cura è entrata, e il marcatore è caduto lì.

    📌 PERCHÉ ORA E NON IL 04/08, quando la cura fu scritta e ritirata: quella
    faceva DUE cose insieme — toglieva il codice dall'estrazione **e** aggiungeva
    un discriminante di soggetto dentro `numeric_conflict`. È entrata solo la
    prima metà, che non tocca la supersessione. ⇒ L'xfail più sotto
    (`test_due_schede_con_codici_diversi_non_sono_in_conflitto`) **resta armato
    apposta**: senza il discriminante non può passare, e il suo rosso alla
    guarigione dirà che è arrivata anche l'altra metà."""
    assert intruso not in _valori(frase), (
        f"«{frase}» produce {sorted(extract_quantities(frase))}, "
        f"dove {intruso} viene dall'identificatore")


@pytest.mark.parametrize("frase,vera", [
    ("Il campione S-001 contiene piombo a 11 milligrammi per litro.", 11.0),
    ("Il magazzino K-77 ha 4200 metri quadri.", 4200.0),
    ("Il caccia F-16 vola a 2000 chilometri orari.", 2000.0),
    ("Il modello GPT-5 ha risposto in 3 secondi.", 3.0),
    ("Il lotto REF-42 pesa 8 chilogrammi.", 8.0),
])
def test_la_quantita_VERA_nella_stessa_frase_resta(frase, vera):
    """IL PRESIDIO. Il caso normale è che identificatore e misura stiano nella
    stessa frase: togliere il primo non deve togliere la seconda, altrimenti la
    cura spegne il rilevatore di contraddizioni numeriche invece di affinarlo."""
    assert vera in _valori(frase), (
        f"«{frase}» ha perso la misura vera: {sorted(extract_quantities(frase))}")


@pytest.mark.parametrize("frase", [
    "Il report del 2026-08-04 conta 42 righe.",
    "La misura del 2026-08-05 conta 42 righe.",
])
def test_una_data_ISO_non_e_una_coppia_di_quantita(frase):
    """`YEAR_RE` esclude già l'anno nudo; il mese e il giorno di una data
    completa no. Due report di due giorni diversi avevano «conta 4» e «conta 5»
    — stessa unità, valori diversi — e sono la cosa che scriviamo più spesso.

    ✅ CURATO il 2026-08-10 da `_DATA_RE` in `quantity_match`, e il marcatore
    `xfail(strict)` che stava qui è caduto da solo: due `XPASS(strict)` nella
    stessa esecuzione in cui la cura è entrata.

    🔑 PERCHÉ QUESTA VOLTA NON HA ROTTO IL PRESIDIO, che è la ragione per cui la
    cura del 2026-08-04 era stata ritirata: quella trattava identificatori e
    date con un criterio SOLO — entrambi hanno la forma «qualcosa-numero» — e
    togliendo `S-001` si portava via anche l'`11` della misura vera nella stessa
    frase. Separando le due classi, la metà delle DATE si chiude senza toccare
    l'altra: `test_la_quantita_VERA_nella_stessa_frase_resta` resta verde e i
    due xfail sugli identificatori restano armati, perché quel difetto è vivo.
    ⇒ Una cura che cadeva per essere troppo larga non era sbagliata: era
    indivisa."""
    assert _valori(frase) == {42.0}, (
        f"«{frase}» -> {sorted(extract_quantities(frase))}")


def test_due_schede_con_codici_diversi_non_sono_in_conflitto():
    """L'end-to-end del difetto: è la coppia che, moltiplicata per duecento
    record, lascia il corpus con un solo fatto vivo.

    ✅ CURATO il 2026-08-11 da `_identificatori_disgiunti`, la seconda metà della
    cura degli identificatori — la prima (`_senza_identificatori`, `232c3486`)
    aveva tolto il falso segnale, ma sotto restava quello vero: 11 e 12 sono
    valori veri, e mancava chi dicesse «sono due record diversi».

    📌 E QUI CADE LA RAGIONE PER CUI LA CURA DEL 2026-08-04 FU RITIRATA. Il suo
    marcatore diceva «fa cadere 2 test nella suite del gate». Misurato oggi con
    questa sola fetta applicata: **i sette file che presidiano i conflitti sono
    tutti verdi** (facts_conflict 27, facts_conflict_numeric 7,
    entity_index_not_measure 19, proof_beats_opinion 12, exclusive_words 3,
    due_opposti 17, due_fatti_che_si_contraddicono 5). ⇒ Quei due test non
    cadevano per questo guard, ma per l'altra parte di quella cura — quella in
    `supersession_policy`, che **non è entrata** e resta fuori: tocca
    direttamente cosa muore in memoria.
    ⇒ Terza volta in due giorni che la stessa separazione paga: **una cura che
    cade per essere troppo larga non è sbagliata, è indivisa.**"""
    a = "Il campione S-001 contiene piombo a 11 milligrammi per litro."
    b = "Il campione S-002 contiene cadmio a 12 milligrammi per litro."
    assert numeric_conflict(a, b) is None, (
        f"due schede distinte risultano in conflitto: {numeric_conflict(a, b)}")


def test_due_misure_dello_STESSO_record_restano_in_conflitto():
    """L'altro verso, senza cui la cura sarebbe uno spegnimento: lo stesso
    campione con due valori diversi È una contraddizione, e va vista."""
    a = "Il campione S-001 contiene piombo a 11 milligrammi per litro."
    b = "Il campione S-001 contiene piombo a 25 milligrammi per litro."
    assert numeric_conflict(a, b) is not None, (
        "stesso campione, due valori: il conflitto deve restare")
