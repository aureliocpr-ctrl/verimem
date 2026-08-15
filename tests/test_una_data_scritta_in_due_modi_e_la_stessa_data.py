"""Una data che la fonte contiene non è un «valore non nella fonte».

`valore_non_nella_fonte` è il controllo deterministico che ha chiuso il buco più
serio del gate: un LLM non inventa il fornitore, inventa **la durata, l'importo,
il numero di pezzi**, e quei dettagli entravano con i punteggi più alti del
sistema (5 su 5 ammessi, g 97,1–99,5). Il modulo li ferma confrontando i numeri
del claim con quelli della fonte. Funziona, e questo banco comincia col
proteggerlo.

⚠️ Ma un numero può non essere una quantità. Il modulo lo sa e lo scrive fra i
propri limiti — «un ANNO nudo non è una quantità… **e il percorso delle date è
un altro**» — e l'esclusione copre l'anno. Non il giorno, non il mese.

Misurato il 15/08 con la fonte `misurato 2026-08-15 13:24 — job in coda 19`::

    claim «Il 2026-08-15 …»       0 valori assenti      ✅
    claim «Il 15/08/2026 …»       0                     ✅
    claim «Il 15 agosto …»        0                     ✅
    claim «Alle 13:24 …»          0                     ✅
    claim «Il 15/08 …»            2   ['08', '15']      ← la stessa data

⇒ **Un caso solo**, e va detta l'ampiezza: giorno/mese senza anno contro una
fonte che scrive la data in forma estesa. Ma è la combinazione che capita di
più in casa nostra, perché le fonti sono output di comandi — che stampano
`2026-08-15T13:31:02` — mentre chi scrive il fatto data la propria misura in
italiano, `il 15/08`. Ed è esattamente ciò che il nostro metodo chiede di fare:
dire **quando** si è misurato.

═══ IL PEZZO ESISTE E NON È COLLEGATO — ma collegarlo non basta ═══

`temporal_context.date_menzionate()` riconosce già tre formati e li normalizza::

    'il 2026-08-15'      -> [(2026, 8, 15)]
    'il 15/08/2026'      -> [(2026, 8, 15)]
    'il 15 agosto 2026'  -> [(2026, 8, 15)]
    'il 15/08'           -> []          ← e qui si ferma

Misurato: sul caso che fallisce, la fonte produce `[(2026, 8, 15)]` e il claim
`[]`. ⇒ Collegare i due moduli — la cura ovvia — **non curerebbe questo caso**.
Servono due pezzi, e il secondo ha un prezzo reale: `15/08` è ambiguo rispetto
alla convenzione mese/giorno, quindi la sua assenza è una scelta difficile e non
una dimenticanza. Per questo il banco **registra** il difetto e non impone la
cura: chi la scriverà dovrà decidere quell'ambiguità, e la decisione non è di
chi passa di qui a misurare.
"""
from __future__ import annotations

import pytest

from verimem.temporal_context import date_menzionate
from verimem.valore_non_nella_fonte import valori_non_nella_fonte

_FONTE = "misurato 2026-08-15 13:24 — job in coda 19"
_FONTE_ORDINE = "ordine 77 del fornitore Bianchi, stato: consegnato"


@pytest.mark.parametrize("claim,atteso", [
    ("L'ordine 77 conteneva 40 pezzi.", "40"),
    ("L'ordine 77 vale 1200 euro.", "1200"),
])
def test_IL_RILEVATORE_PRENDE_ANCORA_I_DETTAGLI_INVENTATI(claim, atteso):
    """⚠️ PRIMA DI TUTTO: la cura sbagliata è più facile di quella giusta.

    Il modo comodo di far tacere il falso positivo sotto è smettere di guardare
    i numeri corti, o quelli separati da `/`. Sarebbe **peggio del difetto**:
    questi tre claim sono la classe che il modulo esiste per fermare, e
    passavano con 97-99 di grounding. Se questo test diventa rosso, la cura ha
    spento il rilevatore invece di raffinarlo.
    """
    trovati = [v.come_scritto() for v in
               valori_non_nella_fonte(claim, _FONTE_ORDINE)]
    assert atteso in trovati, (
        f"«{claim}» inventa un dettaglio che la fonte non contiene e il "
        f"rilevatore non lo vede più (trovati: {trovati}): una cura ha spento "
        f"il controllo invece di raffinarlo")


def test_IL_NUMERO_INVENTATO_RESTA_PRESO_anche_con_questa_fonte():
    """La stessa protezione sulla fonte del caso che fallisce.

    Serve separata: se la cura fosse «ignora i numeri quando la fonte contiene
    una data», i dettagli inventati passerebbero **proprio nei fatti datati**,
    che sono i nostri.
    """
    trovati = [v.come_scritto() for v in
               valori_non_nella_fonte("I job in coda erano 47.", _FONTE)]
    assert "47" in trovati, (
        f"un numero che la fonte non contiene deve restare un valore assente "
        f"anche quando la fonte porta una data (trovati: {trovati})")


@pytest.mark.parametrize("claim", [
    "Il 2026-08-15 i job in coda erano 19.",
    "Il 15/08/2026 i job in coda erano 19.",
    "Il 15 agosto i job in coda erano 19.",
    "Alle 13:24 i job in coda erano 19.",
])
def test_i_formati_di_data_che_oggi_passano_continuino_a_passare(claim):
    """Il verso opposto: quattro forme su cinque funzionano già.

    Blindarle serve perché la cura del quinto caso passa da lì: chi tocca il
    riconoscimento delle date rischia di rompere ciò che oggi è sano, ed è il
    modo in cui una cura sensata diventa una regressione.
    """
    assert not valori_non_nella_fonte(claim, _FONTE), (
        f"«{claim}» dichiara una data che la fonte contiene, e il gate la "
        f"segnala come valore assente: era sano e ha smesso di esserlo")


def test_COLLEGARE_IL_PEZZO_ESISTENTE_NON_BASTA():
    """Perché la cura ovvia non è la cura — misurato, non dedotto.

    `date_menzionate` esiste, normalizza tre formati, e la tentazione è
    innestarla dentro `valori_non_nella_fonte`. Ma sul caso che fallisce il
    claim non produce alcuna data: il confronto sarebbe fra un insieme pieno e
    uno vuoto, e i due numeri resterebbero quantità.

    ⚠️ Se un giorno questo test fallisce è una **buona** notizia — vuol dire
    che `date_menzionate` ha imparato `gg/mm` — e allora l'innesto diventa la
    cura giusta e questo test va tolto.
    """
    assert date_menzionate(_FONTE) == {(2026, 8, 15)}, "la fonte porta la data"
    assert date_menzionate("Il 15/08 i job in coda erano 19.") == set(), (
        "date_menzionate ora riconosce gg/mm senza anno: collegarlo a "
        "valori_non_nella_fonte è diventata la cura giusta — togli questo test "
        "e l'xfail sotto")


@pytest.mark.xfail(strict=True, reason=(
    "il gate confronta i numeri, non le date: «15/08» produce i valori 08 e 15, "
    "che la fonte non contiene in cifre pur contenendo la stessa data come "
    "2026-08-15. `date_menzionate` non copre gg/mm senza anno, quindi la cura "
    "richiede sia l'innesto sia l'estensione del riconoscitore"))
def test_una_data_scritta_in_due_modi_resta_la_stessa_data():
    """Il cuore: la fonte porta la data, il claim la scrive in italiano."""
    claim = "Il 15/08 i job in coda erano 19."
    assenti = [v.come_scritto() for v in valori_non_nella_fonte(claim, _FONTE)]
    assert not assenti, (
        f"«{claim}» viene giudicato con {assenti} valori non nella fonte, ma la "
        f"fonte contiene la stessa data scritta 2026-08-15: chi data la propria "
        f"misura in italiano si vede quarantinare un fatto sostenuto, e la "
        f"ricevuta gli dice «08, 15» senza fargli capire che parla della data")
