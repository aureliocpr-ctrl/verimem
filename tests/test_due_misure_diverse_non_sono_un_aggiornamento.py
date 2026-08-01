"""Dieci fatti veri e scorrelati, e il prodotto ne ritira sei.

MISURATO su data dir VERGINE, canale SDK `Memory.add`, ZERO flag — il metro di
questa settimana: cio' che succede a chi installa e usa il prodotto com'e'::

    RITIRATO 5a81c0d99f93 da f52df5f49e3c: Il grafo delle entita contiene 8625 nodi.
    RITIRATO f52df5f49e3c da 7b24aac970b7: La quarantena trattiene 528 fatti.
    RITIRATO 7b24aac970b7 da 807817b6c1c7: Il repository ha 113 commit fuori da main.
    RITIRATO b34a4f9a7ddd da 807817b6c1c7: La CLI espone 24 comandi.
    RITIRATO 807817b6c1c7 da 87347f1993d9: Il corpus contiene 6682 fatti.
    RITIRATO 87347f1993d9 da c52de6eefee1: La prima fetta della suite ha riportato 2698 passed.
    fatti ritirati in totale: 6 (store con 10 fatti)

Una CATENA: ogni fatto che porta un numero mangia il precedente. Chi scrive
dieci misure ne ritrova quattro, in silenzio — il recall non restituisce piu' i
ritirati e `Memory.get()` non espone nemmeno `superseded_by`.

IL PERCORSO, tracciato e non dedotto: il warning porta `other_fact_id`, quindi
e' il ramo **NLI** (`:1326`), non quello lessicale (`:1146`). Sulle stesse
coppie `validate_claim` risponde `unknown` con `evidence_facts=[]` — la prima
diagnosi, che dava la colpa al percorso lessicale, era SBAGLIATA. I due rami
emettono lo stesso identico warning, e curarne uno solo non basta.

LA CLASSE E' GIA' NOTA IN QUESTO FILE, per un caso particolare. La guardia
`both_machine_checked` nacque da nove relazioni OEIS e la descrive cosi': «two
DISTINCT true properties of the same sequences read as "same subject, different
numbers"». E' esattamente questo difetto — ma protegge solo chi ha un
`verified_by` deterministico, cioe' nessuno degli utenti che scrivono dall'SDK.

LA TERZA GUARDIA generalizza le due che ci sono: due fatti che non condividono
NESSUNA parola di contenuto non sono l'uno l'evoluzione dell'altro. Non tocca
soglie, non spegne il knob, non promuove nessuno stato — restringe cosa puo'
CHIAMARSI evoluzione. Misurato prima di scriverla, su dodici coppie::

    sei finte (quelle ritirate davvero) -> 0 parole condivise, tutte e sei
    sei evoluzioni legittime            -> da 3 a 5 parole condivise, tutte e sei

e il commento accanto alla seconda guardia gia' dichiara la posta: «an NLI
opinion silently deleting a true fact is the error this store exists to avoid».
"""
from __future__ import annotations

import pytest

from verimem import Memory

#: Le sei coppie (ritirato, ritirante) osservate nel DB dell'esperimento.
COPPIE_FINTE = [
    ("Il grafo delle entita contiene 8625 nodi.",
     "La quarantena trattiene 528 fatti."),
    ("La quarantena trattiene 528 fatti.",
     "Il repository ha 113 commit fuori da main."),
    ("Il repository ha 113 commit fuori da main.",
     "Il corpus contiene 6682 fatti."),
    ("La CLI espone 24 comandi.",
     "Il corpus contiene 6682 fatti."),
    ("Il corpus contiene 6682 fatti.",
     "La prima fetta della suite ha riportato 2698 passed."),
    ("La prima fetta della suite ha riportato 2698 passed.",
     "Il commit ea0b494b ha aggiunto 181 inserzioni."),
]

#: Evoluzioni vere: stessa grandezza, valore nuovo. Se la cura le bloccasse,
#: spegnerebbe la promessa centrale del prodotto invece di un difetto.
COPPIE_VERE = [
    ("Il prezzo del piano annuale e 100 euro.",
     "Il prezzo del piano annuale e 200 euro."),
    ("Il corpus contiene 6682 fatti.",
     "Il corpus contiene 6690 fatti."),
    ("Il database di produzione gira su PostgreSQL 14.",
     "Il database di produzione gira su PostgreSQL 16."),
    ("Il rimborso avviene entro 7 giorni lavorativi.",
     "Il rimborso avviene entro 14 giorni lavorativi."),
]


@pytest.mark.parametrize("vecchio,nuovo", COPPIE_FINTE)
def test_due_misure_di_cose_diverse_non_sono_un_aggiornamento(vecchio, nuovo):
    from verimem.anti_confab_gate import _puo_essere_una_evoluzione
    assert _puo_essere_una_evoluzione(nuovo, vecchio) is False, (
        "queste due frasi non condividono NESSUNA parola di contenuto e il "
        "prodotto trattava la seconda come un aggiornamento della prima")


@pytest.mark.parametrize("vecchio,nuovo", COPPIE_VERE)
def test_una_evoluzione_VERA_resta_una_evoluzione(vecchio, nuovo):
    """Senza questa meta' la cura non sarebbe una cura: sarebbe lo spegnimento
    della memoria che evolve, che e' la ragione per cui il knob e' default ON."""
    from verimem.anti_confab_gate import _puo_essere_una_evoluzione
    assert _puo_essere_una_evoluzione(nuovo, vecchio) is True, (
        "un aggiornamento legittimo dello stesso valore non e' piu' "
        "riconosciuto: il prodotto terrebbe due valori in contesa invece di "
        "ritirare quello vecchio")


def test_una_parola_generica_in_comune_NON_basta_piu():
    """Il limite che questo file dichiarava, e che e' stato superato.

    La prima stesura della guardia chiedeva UNA parola di contenuto condivisa,
    e due misure di cose diverse passavano lo stesso::

        "Il corpus contiene 6682 fatti."      -> {corpus, contiene, fatti}
        "La quarantena trattiene 528 fatti."  -> {quarantena, trattiene, fatti}
                                                                    ^^^^^^

    «fatti» e' generica in un prodotto che parla di fatti. Ora le condizioni
    sono due in OR — stessa testa nominale, oppure almeno DUE parole — e
    nessuna delle due regge da sola: misurato su 18 coppie, la sola parola
    sbaglia 1, la sola testa ne sbaglia 3 (sulle evoluzioni VERE), le due
    insieme zero.
    """
    from verimem.anti_confab_gate import _puo_essere_una_evoluzione
    assert _puo_essere_una_evoluzione(
        "Il corpus contiene 6682 fatti.",
        "La quarantena trattiene 528 fatti.") is False, (
        "due misure di soggetti diversi passano ancora per una sola parola "
        "generica in comune")


@pytest.mark.parametrize("vecchio,nuovo", [
    ("Nel piano annuale il prezzo e 100 euro.",
     "Il prezzo del piano annuale e 200 euro."),
    ("Secondo la misura di ieri la suite impiega 18 minuti.",
     "La suite impiega 20 minuti."),
    ("A gennaio il corpus conteneva 6000 fatti.",
     "Il corpus contiene 6682 fatti."),
])
def test_una_evoluzione_scritta_al_contrario_resta_una_evoluzione(vecchio, nuovo):
    """Perche' la testa nominale NON puo' essere l'unica condizione.

    Queste tre aggiornano davvero lo stesso valore, ma aprono con un
    complemento, quindi la loro «prima parola di contenuto» e' «piano»,
    «secondo», «gennaio». Con la sola testa il prodotto terrebbe due valori in
    contesa invece di ritirare il vecchio — tre casi su dieci nella misura.
    A salvarle e' l'altra condizione: le parole condivise sono molte.
    """
    from verimem.anti_confab_gate import _puo_essere_una_evoluzione
    assert _puo_essere_una_evoluzione(nuovo, vecchio) is True


def test_IL_LIMITE_due_misure_diverse_dello_STESSO_soggetto():
    """Il caso duro, capitato addosso a me mentre scrivevo questa cura.

    Due fatti veri, stessa fonte, scritti a due secondi di distanza — uno un
    CONTEGGIO, l'altro delle MEDIANE — e il secondo ha ritirato il primo::

        superseded 6f5552d31efe — no longer served by default recall

    Hanno la stessa testa («coppie») e molte parole in comune, quindi
    passano entrambe le condizioni. Non e' un difetto di questa guardia: e' il
    punto in cui un criterio LESSICALE finisce. Per separarle serve sapere
    QUALE grandezza si misura — un conteggio non aggiorna una mediana — e
    nessuna parola della frase lo dice.

    Sta in un test perche' il giorno in cui qualcuno ci arriva questo FALLISCE,
    ed e' il momento giusto per riscriverlo.
    """
    from verimem.anti_confab_gate import _puo_essere_una_evoluzione
    assert _puo_essere_una_evoluzione(
        "Le coppie riconosciute come evoluzione hanno mediana 2498 char e "
        "quelle giudicate ritiri sbagliati mediana 165 char.",
        "Fra le coppie ritirato-ritirante con entrambi i testi sotto 200 "
        "char, i ritiri sbagliati sono 32 su 257.") is True, (
        "la guardia distingue due MISURE diverse dello stesso soggetto: "
        "rimisura la cascata sul corpus e aggiorna il limite dichiarato qui")


def test_un_fatto_vuoto_non_blocca_nulla():
    """Il caso limite: senza testo da confrontare la guardia non deve avere
    un'opinione — decidono gli strati che c'erano gia'."""
    from verimem.anti_confab_gate import _puo_essere_una_evoluzione
    assert _puo_essere_una_evoluzione("Il prezzo e 200 euro.", "") is True
    assert _puo_essere_una_evoluzione("", "Il prezzo e 100 euro.") is True


#: LA PROVA DAL VIVO NON STA QUI, e il perche' e' un reperto suo.
#:
#: La prima stesura la teneva in questo file e PASSAVA anche con la guardia
#: disattivata: non riproduceva niente. Il conftest impone `HIPPO_OFFLINE=1`,
#: `HF_HUB_OFFLINE=1` e `TRANSFORMERS_OFFLINE=1` a tutta la suite, quindi il
#: tier NLI — che e' il ramo dove la cascata nasce — nei test non gira MAI.
#: Il difetto e' strutturalmente invisibile al presidio che dovrebbe prenderlo,
#: come lo era il rosso di CI finche' `pytest-xdist` non era installato qui.
#:
#: Sta quindi in `test_le_promesse_valgono_appena_installato.py`, che e' il
#: posto giusto due volte: li' la fixture salta se i modelli non sono in cache
#: (invece di fingere di misurare) e li' il metro e' esattamente questo —
#: cosa succede a chi installa il prodotto e lo usa com'e'.
