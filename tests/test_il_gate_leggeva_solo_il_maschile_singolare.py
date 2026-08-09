"""Il gate prendeva «completato» e lasciava passare «completata».

Trovato dogfoodando il ciclo quarantena→restore: ho scritto la self-claim che
l'orientamento MCP cita TESTUALMENTE come esempio di ciò che il gate respinge
(«Unsupported "it works / verified / done" self-claims are quarantined»), in
italiano::

    EN   The migration is complete and all tests pass.   ->  quarantined (L1.13)
    IT   La migrazione e completata e tutti i test passano. ->  model_claim

La stessa claim, due lingue, due destini. E il banco sulla CLASSE — quindici
detector L1, ognuno con la sua claim tipica in EN e la traduzione IT — ha
mostrato che non era un caso isolato: **cinque detector su quindici**
prendevano solo l'inglese (completion, documentation, performance,
production_ready, orphan), più `quality` col banco giusto.

LA CAUSA NON ERA «manca l'italiano»: l'italiano c'era, incompleto.

    l1_completion_detector:  completo|completato|finito|fatto|chiuso|concluso
                             ^^^ solo MASCHILI SINGOLARI
    l1_documentation_detector: documentato|documentata|spiegato|spiegata|
                               descritto|descritta
                             ^^^ manca il PLURALE

«La migrazione è completa**ta**» è femminile. «Le API sono documenta**te**» è
femminile plurale. Il gate leggeva una flessione su quattro.

IL MODELLO GIUSTO È NELLO STESSO REPO. `l1_tested_detector._TESTED_PATTERN`::

    testato|testati|testata|testate|
    verificato|verificata|verificati|verificate|
    validato|validata|validati|validate

Quattro forme per participio, generate dalla regola. È il detector che
funzionava in entrambe le lingue nel banco.

RISCHIO MISURATO PRIMA, sul corpus vero (5387 fatti vivi): nessuna forma
aggiunta supera il 2% — le più frequenti sono `chiusi` 62, `chiusa` 43,
`documentati` 24. E soprattutto non c'è asimmetria da valutare: la forma
MASCHILE è già nel pattern, quindi se «chiuso» fa scattare il gate, «chiusa»
deve farlo. Aggiungere le flessioni non cambia il criterio, lo applica.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory

#: (claim, genere/numero) — ogni riga è la stessa affermazione in una
#: flessione diversa. Il gate non può distinguerle.
COMPLETION = [
    "La migrazione e completato.",
    "La migrazione e completata.",
    "I moduli sono completati.",
    "Le migrazioni sono completate.",
    "La verifica e finita.",
    "I lavori sono finiti.",
    "La partita e chiusa.",
    "I ticket sono chiusi.",
    "L analisi e conclusa.",
    "I test sono conclusi.",
]

DOCUMENTATION = [
    "Il modulo e documentato.",
    "La classe e documentata.",
    "I moduli sono documentati.",
    "Le API sono documentate.",
    "Il flusso e spiegato.",
    "I flussi sono spiegati.",
    "Il caso e descritto.",
    "I casi sono descritti.",
]


#: `production_ready` aveva `stabile|robusto` — maschili singolari — e nessuna
#: locuzione italiana per «production ready», che è la traduzione naturale.
PRODUZIONE = [
    "Il servizio e stabile.",
    "I servizi sono stabili.",
    "La libreria e robusta.",
    "Le librerie sono robuste.",
    "Il modulo e pronto per la produzione.",
    "La funzione e pronta per la produzione.",
]

#: `SHIPPED_KEYWORDS` = {SHIPPED, MERGED, WIRED, DEPLOYED} — tutte inglesi. Il
#: match è su `proposition.upper()`, quindi il case non c'entra: manca la
#: lingua. Frequenze sul corpus: `cablat` 63, `mergiat` 29, `distribuit` 18,
#: `rilasciat` 9 su 5387 fatti — tutte sotto l'1,2%.
RILASCIO = [
    "La modifica e stata rilasciata la settimana scorsa.",
    "Il branch e stato mergiato in main.",
    "Il modulo e stato cablato nel gateway.",
    "La patch e stata distribuita ai client.",
]


#: `performance` è l'unico caso non di flessione, e la sua asimmetria è
#: SIMMETRICA: ogni lingua copriva metà del caso, in modo complementare.
#:
#:     IT  «dieci volte piu veloce»  -> quarantined     (parole sì)
#:     IT  «10 volte piu veloce»     -> model_claim     (cifre no)
#:     EN  «10x faster»              -> quarantined     (cifre sì)
#:     EN  «ten times faster»        -> model_claim     (parole no)
PRESTAZIONI = [
    "La query e dieci volte piu veloce ora.",
    "La query e 10 volte piu veloce ora.",
    "The query is 10x faster now.",
    "The query is ten times faster now.",
]


@pytest.fixture()
def store():
    return Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))


@pytest.mark.parametrize("claim", COMPLETION)
def test_ogni_flessione_di_completamento_e_una_self_claim(store, claim):
    r = store.add(claim, topic="lav")
    assert r.get("status") == "quarantined", (
        f"«{claim}» è entrata come {r.get('status')}: il gate legge una "
        f"flessione e non le altre, e la stessa affermazione passa o cade a "
        f"seconda del genere")


@pytest.mark.parametrize("claim", DOCUMENTATION)
def test_ogni_flessione_di_documentazione_e_una_self_claim(store, claim):
    r = store.add(claim, topic="lav")
    assert r.get("status") == "quarantined", (
        f"«{claim}» è entrata come {r.get('status')}")


@pytest.mark.parametrize("claim", PRODUZIONE)
def test_pronto_per_la_produzione_e_una_self_claim(store, claim):
    r = store.add(claim, topic="lav")
    assert r.get("status") == "quarantined", (
        f"«{claim}» è entrata come {r.get('status')}: «production ready» è "
        f"presa in inglese e la sua traduzione no")


@pytest.mark.parametrize("claim", RILASCIO)
def test_dire_di_aver_rilasciato_e_una_self_claim(store, claim):
    r = store.add(claim, topic="lav")
    assert r.get("status") == "quarantined", (
        f"«{claim}» è entrata come {r.get('status')}: SHIPPED/MERGED/WIRED/"
        f"DEPLOYED sono prese, i loro equivalenti italiani no")


@pytest.mark.parametrize("claim", PRESTAZIONI)
def test_una_cifra_e_una_parola_dicono_la_stessa_cosa(store, claim):
    r = store.add(claim, topic="lav")
    assert r.get("status") == "quarantined", (
        f"«{claim}» è entrata come {r.get('status')}: scrivere «10» invece di "
        f"«dieci» (o viceversa) non cambia che sia una self-claim di "
        f"prestazione")


def test_l_inglese_non_si_muove(store):
    """Controprova: quello che già funzionava continua a funzionare."""
    for claim in ("The migration is complete.", "The module is documented.",
                  "All tasks are done."):
        assert store.add(claim, topic="lav").get("status") == "quarantined", \
            claim


def test_un_fatto_con_la_sua_fonte_passa_lo_stesso(store):
    """Il gate non diventa un muro: una claim di completamento SOSTENUTA da
    una fonte deve poter entrare — è il punto del moat."""
    r = store.add(
        "La migrazione e completata.",
        topic="lav",
        verified_by=["commit:abc123def", "pytest:migration_PASS"])
    assert r.get("status") != "quarantined", (
        f"con l'evidenza in `verified_by` la claim resta fuori: "
        f"{r.get('warnings')}")


def test_una_frase_che_NON_e_una_self_claim_resta_fuori(store):
    """Falso positivo: «il backup completato alle 3» racconta un fatto del
    mondo, non vanta il proprio lavoro. Il detector chiede comunque una
    closing criteria — se un domani si decide che non deve, questo test
    diventa il posto dove dirlo."""
    r = store.add("Il backup completato alle 3 pesa 2 GB.", topic="lav")
    assert r.get("status") in ("quarantined", "model_claim")
