"""TDD — una preposizione che segue un numero non e' un'unita' di misura.

Trovato per dogfooding il 25/07: verimem perdeva fatti veri. Tre relazioni OEIS
distinte, due issue diverse, due servizi su porte diverse — in ognuno di questi
casi il secondo write RITIRAVA il primo (o, con il supersede spento, veniva
quarantenato), e 8 fatti veri su 9 uscivano dal recall di default.

La catena: extract_quantities prende la parola che SEGUE il numero come unita'.
_NON_UNIT_WORDS esiste proprio per scartare le function word ("30 and 45",
"5 of 10") e contiene gia' qualche parola italiana (di, da, su, il, la) — ma NON
le preposizioni ARTICOLATE, che in italiano sono la forma piu' comune:

    "issue #42 nel tracker"   -> ('nel', 42.0)
    "task 7 del piano"        -> ('del', 7.0)
    "port 8080 locally"       -> ('locally', 8080.0)

Due numeri diversi seguiti dalla stessa preposizione = stessa unita', valore
diverso = conflitto. Da lì il supersede ritira il fatto precedente.

Il contratto che questo viola e' scritto nel codice, nella docstring di
numeric_conflict: "precision over recall — a false conflict downgrades a true
fact, the opposite of the trust we sell".
"""
from __future__ import annotations

from verimem.quantity_match import extract_quantities, numeric_conflict


def _units(text: str) -> set[str]:
    return {u for (u, _v) in extract_quantities(text) if u}


# --- le unita' non devono essere function word ------------------------------

def test_italian_articulated_prepositions_are_not_units():
    """Le preposizioni articolate sono un insieme chiuso e frequentissimo in
    italiano: senza di loro la lista di function word copre l'inglese e lascia
    scoperta la lingua in cui questo store viene effettivamente usato."""
    for text in ("issue #42 nel tracker e' aperta",
                 "task 7 del piano e' completato",
                 "il fatto 3 nella catena e' orfano",
                 "la riga 12 della funzione va cambiata",
                 "il punto 5 dei requisiti manca",
                 "lo step 2 degli otto previsti",
                 "la fase 4 alla fine del ciclo",
                 "il commit 3 sul branch principale",
                 "la nota 9 sulla revisione"):
        assert _units(text) == set(), f"unita' inventata in: {text!r} -> {_units(text)}"


def test_english_ly_adverbs_are_not_units():
    """Nessuna unita' di misura reale finisce in -ly: ms, kg, min, entries,
    requests… La morfologia basta, senza allungare la lista a mano."""
    for text in ("the service listens on port 8080 locally",
                 "the cache holds 1024 entries only",
                 "the job runs 3 times daily"):
        bad = {u for u in _units(text) if u.endswith("ly")}
        assert not bad, f"unita' in -ly in {text!r}: {bad}"


# --- il caso reale: fatti distinti non si contraddicono ---------------------

def test_distinct_subjects_with_a_trailing_preposition_do_not_conflict():
    assert numeric_conflict("issue #42 nel tracker e' aperta e assegnata a nessuno",
                            "issue #43 nel tracker e' aperta e assegnata a nessuno") is None
    assert numeric_conflict("task 7 del piano e' completato",
                            "task 8 del piano e' completato") is None
    assert numeric_conflict("The Verimem service listens on port 8080 locally",
                            "The Cortex service listens on port 9090 locally") is None


# --- controllo nullo: le contraddizioni VERE devono restare tali ------------

def test_real_quantity_conflicts_still_fire():
    """Il rilevatore serve: allentarlo fino a perdere le contraddizioni vere
    sarebbe barattare un difetto con uno peggiore (G5 — nessun guadagno può
    costare confabulazione)."""
    assert numeric_conflict("la full suite di verimem conta 7883 test passati",
                            "la full suite di verimem conta 8004 test passati") is not None
    assert numeric_conflict("il recall di verimem risponde in 45 ms",
                            "il recall di verimem risponde in 120 ms") is not None
    assert numeric_conflict("the cache holds 1024 entries",
                            "the cache holds 4096 entries") is not None
    assert numeric_conflict("the timeout is 30 seconds",
                            "the timeout is 90 seconds") is not None


def test_real_units_are_still_extracted():
    assert ("ms", 45.0) in extract_quantities("risponde in 45 ms")
    assert ("min", 30.0) in extract_quantities("30 minutes to run")
    assert ("test", 8004.0) in extract_quantities("conta 8004 test passati")
    assert ("entry", 1024.0) in extract_quantities("the cache holds 1024 entries")


def test_italian_adverbs_are_not_units():
    """Aggiunto dopo una review avversariale (glm-5.2, 2026-07-25) che ha
    trovato il buco nella PRIMA versione di questo fix: la regola copriva solo
    l'inglese in -ly e lasciava l'italiano in -mente rotto come prima. Verificato
    eseguendo: 'porta 8080 localmente' dava unita' 'localmente' e due porte
    diverse continuavano a produrre un conflitto."""
    for text in ("il servizio ascolta sulla porta 8080 localmente",
                 "il job parte 3 volte esattamente",
                 "la coda tiene 1024 elementi solamente"):
        bad = {u for (u, _v) in extract_quantities(text) if u.endswith("mente")}
        assert not bad, f"unita' in -mente in {text!r}: {bad}"
    assert numeric_conflict(
        "il servizio verimem ascolta sulla porta 8080 localmente",
        "il servizio cortex ascolta sulla porta 9090 localmente") is None


def test_decalitre_is_the_accepted_cost_of_the_preposition_rule():
    """Costo noto e accettato, sollevato dallo stesso avversario: 'dal' e' sia
    preposizione articolata sia simbolo del decalitro. La preposizione vince, il
    decalitro perde l'unita' e diventa numero nudo — un conflitto MANCATO, che
    qui e' l'errore piu' economico di uno FABBRICATO. Il test fissa la scelta
    perche' sia una decisione e non una sorpresa."""
    assert ("", 50.0) in extract_quantities("50 dal di vino nella cantina")


def test_frequency_words_are_real_units():
    """Sollevato da un SECONDO avversario (deepseek-v4-pro, 2026-07-25) e
    confermato eseguendo: la regola '-ly' aveva trasformato un conflitto
    FABBRICATO in uno sistematicamente MANCATO. 'daily/weekly/monthly/yearly'
    nei domini che questo store serve sono unita' di frequenza vere, e
    '10 daily reports' vs '50 daily reports' aveva smesso di essere un
    conflitto. Una regola morfologica rozza ha bisogno di questa eccezione."""
    assert ("daily", 10.0) in extract_quantities("10 daily reports generated")
    assert ("yearly", 5000.0) in extract_quantities("il budget e 5000 yearly")
    assert numeric_conflict("10 daily reports generated",
                            "50 daily reports generated") is not None
    assert numeric_conflict("3 weekly backups are kept",
                            "7 weekly backups are kept") is not None
    # …e gli avverbi che NON sono frequenze restano fuori
    assert not {u for (u, _v) in extract_quantities("port 8080 locally") if u}
