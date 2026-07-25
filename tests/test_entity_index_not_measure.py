"""TDD — un numero che IDENTIFICA non e' un numero che MISURA.

Il rilevatore di conflitti numerici trattava ogni "parola + numero" come una
misura, quindi "issue 42" e "issue 43" erano lo stesso soggetto con un valore
diverso = conflitto, e il supersede ritirava il primo. La cura precedente
(scartare le preposizioni come unita') copriva i sintomi in italiano ma non la
causa: restavano casi come

    "il fatto 3 ha 500 righe di codice"  vs  "il fatto 5 ha 200 righe di codice"

dove l'unita' condivisa e' 'righe' e le parole distintive coincidono, quindi il
giudice li legge come lo stesso soggetto — mentre gli indici 3 e 5 dicono che
sono due soggetti distinti.

La distinzione strutturale: un numero e' una MISURA (45 ms, 8004 test: un valore
diverso e' un'evoluzione) o un IDENTIFICATORE (issue 42, task 7, porta 8080: un
valore diverso e' un'altra cosa). Il primitivo event_indices esisteva gia' per
'day 4' / 'week 2' ma (a) non conosceva i nomi di entita' e (b) non era collegato
al path numerico. Ora entrambe le cose.
"""
from __future__ import annotations

from verimem.quantity_match import (
    distinct_event_indices,
    event_indices,
    numeric_conflict,
)


def test_entity_names_are_recognised_as_indices():
    for text, want in (
        ("issue 42 nel tracker", ("issue", 42)),
        ("issue #43 nel tracker", ("issue", 43)),
        ("il fatto 3 della catena", ("fatto", 3)),
        ("la riga 12 della funzione", ("riga", 12)),
        ("il servizio ascolta sulla porta 8080", ("porta", 8080)),
        ("the service listens on port 9090", ("port", 9090)),
        ("ticket #517 assegnato", ("ticket", 517)),
        ("il progetto 7 e' approvato", ("progetto", 7)),
    ):
        assert want in event_indices(text), f"{text!r} -> {event_indices(text)}"


def test_different_entity_indices_are_different_subjects():
    assert distinct_event_indices("issue 42 nel tracker e' aperta",
                                  "issue 43 nel tracker e' aperta")
    assert distinct_event_indices("il fatto 3 ha 500 righe di codice",
                                  "il fatto 5 ha 200 righe di codice")


def test_the_case_that_survived_the_previous_fix():
    """Il caso concreto che la cura precedente non prendeva: unita' condivisa
    ('righe') + parole distintive uguali, ma indici di entita' diversi."""
    assert numeric_conflict("il fatto 3 ha 500 righe di codice",
                            "il fatto 5 ha 200 righe di codice") is None
    assert numeric_conflict("la issue 42 ha 3 commenti",
                            "la issue 43 ha 9 commenti") is None
    assert numeric_conflict("il servizio sulla porta 8080 gestisce 200 richieste",
                            "il servizio sulla porta 9090 gestisce 500 richieste") is None


def test_same_entity_index_still_conflicts():
    """Controllo nullo: STESSO identificatore e misura diversa e' una vera
    evoluzione, e deve continuare a essere rilevata. Senza questo la guardia
    spegnerebbe il rilevatore invece di correggerlo."""
    assert numeric_conflict("il fatto 3 ha 500 righe di codice",
                            "il fatto 3 ha 200 righe di codice") is not None
    assert numeric_conflict("la issue 42 ha 3 commenti",
                            "la issue 42 ha 9 commenti") is not None


def test_measures_without_any_index_still_conflict():
    """Nessun identificatore in gioco: il rilevatore lavora come prima."""
    assert numeric_conflict("la full suite conta 7883 test passati",
                            "la full suite conta 8004 test passati") is not None
    assert numeric_conflict("il recall risponde in 45 ms",
                            "il recall risponde in 120 ms") is not None
    assert numeric_conflict("the cache holds 1024 entries",
                            "the cache holds 4096 entries") is not None


# --- codici alfanumerici: A000030, CVE2024, ABC123 -------------------------

def test_alphanumeric_codes_are_indices_too():
    """Ultimo residuo del caso reale: l'organismo OEIS scrive relazioni fra
    sequenze identificate da codici come A000030 / A000045. Non sono "parola +
    numero", quindi event_indices non li vedeva, e due relazioni fra sequenze
    DIVERSE risultavano lo stesso soggetto: la seconda ritirava la prima e delle
    9 relazioni verificate ne sopravviveva 1."""
    assert ("a", 30) in event_indices("relation: a(n) = A000030(n) - A000045(n)")
    assert ("cve", 2024) in event_indices("la CVE2024 e' stata pubblicata")


def test_a_commit_sha_is_not_an_index():
    """Un SHA non e' un codice-con-prefisso: 'a64d252' non deve produrre indici,
    altrimenti ogni fatto che cita un commit diventerebbe un soggetto a se'."""
    assert event_indices("il commit a64d252 ha rotto il test") == set() or all(
        k != "a" for (k, _n) in event_indices("il commit a64d252"))


def test_different_oeis_sequences_do_not_conflict():
    a = ("OEIS verified relation: a(n) = A000030(n) - A000045(n) | "
         "REL=[[1,\"A000030\",0]] | evidence: holds exactly at 34 common points")
    b = ("OEIS verified relation: a(n) = A000032(n) - A000045(n) | "
         "REL=[[1,\"A000032\",0]] | evidence: holds exactly at 34 common points")
    assert distinct_event_indices(a, b), "A000030 e A000032 sono sequenze diverse"
    assert numeric_conflict(a, b) is None


# --- specifico vs generico: non sono lo stesso soggetto --------------------

def test_indexed_and_unindexed_statements_are_not_comparable():
    """Il caso peggiore trovato dal dogfooding: la nota di servizio

        "a stray note that is not a relation"

    ha SUPERSEDUTO una relazione matematica verificata

        "OEIS verified relation: +2*A000217(n) -A002378(n) = 0 | REL=..."

    Il giudice NLI legge la negazione ("is NOT a relation" contro "verified
    relation") e dichiara contraddizione; essendo stessa fonte e tempo
    posteriore, il gate ritira la relazione. Ma la relazione parla di due
    sequenze IDENTIFICATE e la nota non nomina niente: uno enunciato specifico e
    uno generico non hanno un soggetto in comune da contraddire.

    Nota di scopo: questa e' una guardia di PRECISIONE sul verdetto di un
    modello, non sul giudizio deterministico — la stessa scelta fatta per la
    reference guard dopo la review avversariale."""
    from verimem.quantity_match import indexed_vs_unindexed

    rel = ("OEIS verified relation: +2*A000217(n) -A002378(n) = 0 | "
           "REL=[[2, \"A000217\", 0], [-1, \"A002378\", 0]]")
    note = "a stray note that is not a relation"
    assert indexed_vs_unindexed(rel, note)
    assert indexed_vs_unindexed(note, rel)          # simmetrica


def test_two_generic_statements_stay_comparable():
    """Controllo nullo: se nessuno dei due ha indici, la guardia non interviene e
    le contraddizioni vere restano rilevabili."""
    from verimem.quantity_match import indexed_vs_unindexed

    assert not indexed_vs_unindexed("la full suite conta 7883 test passati",
                                    "la full suite conta 8004 test passati")
    assert not indexed_vs_unindexed("il gate quarantena il 75% del corpus",
                                    "il gate quarantena il 40% del corpus")


def test_two_indexed_statements_stay_comparable():
    """E se entrambi hanno indici, decide il criterio degli indici (stesso
    indice = stesso soggetto = conflitto vero), non questa guardia."""
    from verimem.quantity_match import indexed_vs_unindexed

    assert not indexed_vs_unindexed("il fatto 3 ha 500 righe",
                                    "il fatto 3 ha 200 righe")
