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


# --- progressione vs identita': due cesti diversi --------------------------

def test_progression_kinds_do_not_make_two_subjects():
    """Controesempio di glm-5.2 (2026-07-25), confermato eseguendo. 'version',
    'build', 'fase', 'ciclo' indicano la PROGRESSIONE della stessa entita', non
    entita' distinte: un numero diverso li' e' un'evoluzione, non un altro
    soggetto. Trattandoli come identificatori si perdeva il ritiro legittimo:

        "issue 42, fase 1: bug aperto"   vs  "issue 42, fase 2: bug chiuso"
        "version 1: latenza 45 ms"       vs  "version 2: latenza 200 ms"

    La prima coppia e' la STESSA issue che evolve; la seconda e' lo stesso modulo
    che peggiora. Entrambe devono restare rilevabili."""
    a = "issue 42, fase 1: bug aperto, priorita alta"
    b = "issue 42, fase 2: bug chiuso, priorita bassa"
    assert not distinct_event_indices(a, b), (
        "la fase e' stata letta come un soggetto diverso")

    c = "version 1 del modulo: latenza 45 ms"
    d = "version 2 del modulo: latenza 200 ms"
    assert numeric_conflict(c, d) is not None, (
        "la version e' stata letta come un soggetto diverso")


def test_identity_kinds_still_separate_subjects():
    """Controllo nullo del fix precedente: i kind di IDENTITA' continuano a
    distinguere i soggetti."""
    assert distinct_event_indices("issue 42 e' aperta", "issue 43 e' aperta")
    assert distinct_event_indices("la riga 12 va cambiata", "la riga 30 va cambiata")
    assert distinct_event_indices("porta 8080 in ascolto", "porta 9090 in ascolto")


def test_a_progression_kind_alone_leaves_the_conflict_visible():
    """Se l'UNICO indice condiviso e' di progressione, non c'e' nulla che
    distingua i soggetti e il conflitto resta."""
    assert not distinct_event_indices("al ciclo 3 la suite conta 100 test",
                                      "al ciclo 4 la suite conta 200 test")


# --- il discriminante POSIZIONALE: una lista di kind non basta -------------

def test_any_noun_followed_by_a_bare_number_is_an_index():
    """Una lista chiusa di kind non copre il vocabolario, e un test della suite
    l'ha dimostrato: di 9 fatti distinti — "The email module sends message 0/1/2",
    "The user module stores profile 0/1/2", "The tax module computes rate 0/1/2" —
    ne venivano RITIRATI 7, perche' message/profile/rate non erano in lista.

    Il discriminante generale e' POSIZIONALE, non lessicale:
      <parola> <numero>  senza unita' dopo  -> INDICE   ("message 0", "issue 42")
      <numero> <unita'>                     -> MISURA   ("7883 test", "45 ms")
    """
    assert ("message", 0) in event_indices("The email module sends message 0.")
    assert ("profile", 2) in event_indices("The user module stores profile 2.")
    assert ("rate", 1) in event_indices("The tax module computes rate 1.")


def test_a_measure_is_not_read_as_an_index():
    """Controllo nullo, ed e' il vincolo che rende sicura la regola: se il numero
    e' seguito da un'unita' e' una misura, e due valori diversi restano un
    conflitto vero."""
    assert not any(k == "conta" for (k, _n)
                   in event_indices("la full suite conta 7883 test passati"))
    assert numeric_conflict("la full suite conta 7883 test passati",
                            "la full suite conta 8004 test passati") is not None
    assert numeric_conflict("il recall risponde in 45 ms",
                            "il recall risponde in 120 ms") is not None


def test_the_nine_distinct_facts_stay_distinct():
    """Il caso della suite, end-to-end sui primitivi."""
    for word in ("message", "profile", "rate"):
        a = f"The module handles {word} 0."
        b = f"The module handles {word} 1."
        assert distinct_event_indices(a, b), f"{word} 0 e {word} 1 confusi"


def test_different_kinds_are_also_different_subjects():
    """Il buco piu' grosso, trovato strumentando: _indices_disjoint cercava un
    kind CONDIVISO, quindi con kind diversi il ciclo non iterava e la guardia
    rispondeva "non sono soggetti diversi" — l'opposto della verita'. Effetto
    misurato: un fatto su "email/message 0" ritirava TRE fatti su "tax/rate
    0/1/2". Il criterio e' il confronto degli INSIEMI di indici, non la ricerca
    di un kind in comune."""
    assert distinct_event_indices("The email module sends message 0.",
                                  "The tax module computes rate 0.")
    assert distinct_event_indices("issue 42 e' aperta", "la riga 42 va cambiata")
    assert numeric_conflict("The email module sends message 0.",
                            "The tax module computes rate 0.") is None


def test_same_index_set_still_conflicts():
    """Controllo nullo: insiemi di indici UGUALI = stesso soggetto = il conflitto
    vero resta."""
    assert not distinct_event_indices("il fatto 3 ha 500 righe di codice",
                                      "il fatto 3 ha 200 righe di codice")
    assert numeric_conflict("il fatto 3 ha 500 righe di codice",
                            "il fatto 3 ha 200 righe di codice") is not None
    # nessun indice da nessuna parte: il rilevatore lavora come sempre
    assert not distinct_event_indices("la full suite conta 7883 test",
                                      "la full suite conta 8004 test")
