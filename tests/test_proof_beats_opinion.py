"""TDD — la prova meccanica batte l'opinione del modello.

Il caso che ha forzato questa regola, trovato col dogfooding sul corpus reale.
L'organismo OEIS verifica relazioni fra sequenze con un controllo intero ESATTO
e le scrive con l'evidenza corrispondente (qa:exact_integer_check_..._PASS). Di
9 relazioni verificate ne sopravvivevano 2: le altre 7 venivano RITIRATE, a
coppie, dal supersede same-source.

    R1  +A000032(n) -3*A000045(n+1) +A000045(n+2) = 0
    R2  +A000032(n)   +A000045(n)   -2*A000045(n+1) = 0

Sono due proprieta' DISTINTE delle stesse sequenze, entrambe vere, entrambe
provate. Misurato: su questa coppia NESSUN rilevatore deterministico spara
(numeric/version/date/negation tutti None) — il verdetto di contraddizione viene
solo dal giudice NLI.

La regola: se ENTRAMBI i fatti portano evidenza machine-checkable — la stessa che
il gate riconosce gia' in L1.15 per non quarantenarli — l'opinione di un
cross-encoder non e' evidenza sufficiente per ritirarne uno. Ritirare e'
irreversibile, tenere entrambi non lo e'.

Cosa questa regola NON fa, deliberatamente: non promuove nessuno status a
'verified' e non rende nulla intoccabile. Un conflitto DETERMINISTICO continua a
ritirare il vecchio, e chi forgiasse un verified_by falso otterrebbe solo la
coesistenza, non l'immunita'. Il commento in client.py:165 e
provenance_validator.py:163 vietano esplicitamente di fabbricare
status='verified' bypassando il moat: questa regola non lo fa.
"""
from __future__ import annotations

from verimem.proof_evidence import both_machine_checked

QA = ["qa:exact_integer_check_201pts_window_n200_residual0_PASS"]
PYTEST = ["pytest:test_recall_PASS"]
CI = ["ci:12345:green"]
WEAK = ["source: ho controllato a mano"]


def test_two_machine_checked_facts_are_both_proven():
    assert both_machine_checked(QA, QA)
    assert both_machine_checked(PYTEST, CI)


def test_one_sided_evidence_does_not_trigger_the_rule():
    """Se solo uno dei due porta la prova, la regola non si applica: non c'e'
    simmetria da rispettare e il gate decide come prima."""
    assert not both_machine_checked(QA, WEAK)
    assert not both_machine_checked(WEAK, QA)
    assert not both_machine_checked(QA, None)
    assert not both_machine_checked(None, None)


def test_a_bare_prefix_is_not_evidence():
    """Riusa il riconoscitore del gate: un prefisso nudo senza esito non conta,
    altrimenti la regola si comprerebbe con una stringa qualsiasi."""
    assert not both_machine_checked(["pytest:something"], ["pytest:other"])
    assert not both_machine_checked(["test:greenfield"], ["test:greenfield"])


def test_the_real_oeis_pair_is_protected():
    """La coppia vera: nessun rilevatore deterministico spara, entrambe provate."""
    from verimem.quantity_match import (
        date_conflict,
        negation_conflict,
        numeric_conflict,
        version_conflict,
    )
    r1 = ("OEIS verified relation: +A000032(n) -3*A000045(n+1) +A000045(n+2) = 0 | "
          "evidence: holds exactly at 201 common points (window n<=200)")
    r2 = ("OEIS verified relation: +A000032(n) +A000045(n) -2*A000045(n+1) = 0 | "
          "evidence: holds exactly at 201 common points (window n<=200)")
    assert numeric_conflict(r1, r2) is None
    assert version_conflict(r1, r2) is None
    assert date_conflict(r1, r2) is None
    assert negation_conflict(r1, r2) is None
    assert both_machine_checked(QA, QA), "entrambe portano la prova esatta"


# --- i numeri dell'EVIDENZA non sono il claim ------------------------------

def test_numbers_after_an_evidence_marker_are_not_the_claim():
    """La causa radice del caso OEIS, isolata: il testo del fatto portava anche
    i metadati della verifica, e il rilevatore li leggeva come contenuto.

        "... = 0 | evidence: holds exactly at 199 common points (window n<=200)"
        "... = 0 | evidence: holds exactly at 200 common points (window n<=200)"

    Due relazioni DIVERSE verificate su un numero diverso di punti diventavano
    "stessa unita' 'common', valore 199 vs 200" = conflitto, e il supersede
    ritirava la prima. Misurato: togliendo la porzione dopo 'evidence:' il
    conflitto spariva.

    Cio' che segue un marcatore di evidenza e' PROVENIENZA, non asserzione: da
    quanti campioni, quale run, quale commit. Chiunque scriva "verificato su 200
    campioni" nel testo si fabbricava conflitti con se stesso."""
    from verimem.quantity_match import extract_quantities, numeric_conflict

    r1 = ("OEIS verified relation: +A000032(n) -3*A000045(n+1) = 0 | "
          "evidence: holds exactly at 199 common points (window n<=200)")
    r2 = ("OEIS verified relation: +A000032(n) +A000045(n) = 0 | "
          "evidence: holds exactly at 200 common points (window n<=200)")
    assert numeric_conflict(r1, r2) is None
    # i numeri della provenienza non entrano affatto fra le quantita'
    assert not {v for (_u, v) in extract_quantities(r1) if v in (199.0, 200.0)}


def test_the_claim_before_the_marker_is_still_measured():
    """Controllo nullo: il claim PRIMA del marcatore conta come sempre, e due
    valori diversi restano un conflitto vero."""
    from verimem.quantity_match import numeric_conflict

    a = "la full suite conta 7883 test passati | evidence: pytest run 12345"
    b = "la full suite conta 8004 test passati | evidence: pytest run 99999"
    assert numeric_conflict(a, b) is not None


def test_other_evidence_markers_are_recognised():
    from verimem.quantity_match import extract_quantities

    for marker in ("evidence:", "verified_by:", "source:", "ref:", "prova:",
                   "fonte:"):
        text = f"il gate blocca il claim | {marker} misurato su 512 campioni"
        vals = {v for (_u, v) in extract_quantities(text)}
        assert 512.0 not in vals, f"{marker} non riconosciuto: {vals}"


def test_an_inline_marker_does_not_swallow_the_claim():
    """MISURATO sul corpus vivo appena scritta la prima versione: tagliava 140
    fatti su 6293 scartando in mediana il 67% del testo, perche' scattava su
    marcatori usati INLINE dentro un blocco di metadati —

        "RESEARCH FINDING [provisional, source: arxiv.org/... ] ProvSEEK (2025) ..."

    dove il claim vero viene DOPO la parentesi. Quella versione teneva
    l'intestazione e buttava il contenuto, rendendo invisibile il 97% del testo di
    quei fatti a tutti i rilevatori. Un marcatore chiude il claim solo se
    introduce una CODA."""
    from verimem.quantity_match import claim_span

    inline = ("RESEARCH FINDING [provisional, source: arxiv.org/abs/2512.16962 "
              "ar5iv full read 2026-05-16] MemoryGraft raggiunge 87 punti su 100")
    assert claim_span(inline) == inline, "il claim dopo la parentesi e' stato perso"

    tail = ("OEIS verified relation: +A000032(n) -3*A000045(n+1) = 0 | "
            "evidence: holds exactly at 199 common points")
    assert claim_span(tail).startswith("OEIS verified relation")
    assert "199" not in claim_span(tail)


def test_a_marker_that_leaves_only_crumbs_is_ignored():
    """Se dopo il taglio resta meno di meta' testo, il marcatore era parte della
    frase: meglio misurare un numero in piu' che perdere il claim."""
    from verimem.quantity_match import claim_span

    t = "fonte: il documento interno dichiara 45 ms di latenza sul path caldo"
    assert claim_span(t) == t


def test_a_marker_mid_sentence_is_not_a_section_break():
    """Terzo controesempio di glm-5.2, confermato eseguendo:

        "Riferendosi alla fonte: il record 42 ha valore 100"

    lasciava "Riferendosi alla " — 17 caratteri, oltre la soglia — e buttava via
    IL CLAIM, compreso l'identificatore 'record 42' e il valore. Se contraddiceva
    "record 42 ha valore 200", il conflitto spariva.

    'fonte:' e 'prova:' sono parole italiane comuni e 'ref:' compare nelle note
    tecniche: contare i caratteri non basta. Un marcatore chiude il claim solo se
    APRE UNA SEZIONE — preceduto da un delimitatore (|, newline, punto, ;, —) o
    dall'inizio del testo, eventualmente con un'etichetta in maiuscolo davanti
    ("EMPIRICAL EVIDENCE:", "STEP-BY-STEP EVIDENCE:")."""
    from verimem.quantity_match import claim_span, numeric_conflict

    t = "Riferendosi alla fonte: il record 42 conta 100 righe"
    assert claim_span(t) == t, f"claim mangiato: {claim_span(t)!r}"
    # l'unita' deve SEGUIRE il numero perche' il parser la veda ("100 righe"):
    # una prima versione di questo test chiedeva un conflitto su "valore 100",
    # dove l'unita' precede, e falliva per un limite del parser che non ha nulla
    # a che vedere con claim_span — il test era mal posto, non il fix.
    assert numeric_conflict(t, "il record 42 conta 300 righe") is not None

    # …e "Vera fonte: X" e' un claim, non una citazione
    v = "FASE 0 fix IDENTITA VERIFICATO. Vera fonte: SYN_IDENTITY in singularity.py"
    assert claim_span(v) == v


def test_section_markers_still_end_the_claim():
    """Controllo nullo: i separatori di sezione veri continuano a tagliare —
    dopo una barra, e dopo un newline anche con etichetta maiuscola davanti."""
    from verimem.quantity_match import claim_span

    bar = ("OEIS verified relation: +A000032(n) -3*A000045(n+1) = 0 | "
           "evidence: holds exactly at 199 common points")
    assert "199" not in claim_span(bar)

    nl = ("LOC GENERATI: ~1500 (lab scripts + tests)\n"
          "EMPIRICAL EVIDENCE: 8 ipotesi testate, 1 singolarita' confermata")
    assert "8 ipotesi" not in claim_span(nl)


def test_ordinary_vocabulary_markers_do_not_eat_the_claim():
    """I tre controesempi del critic (counterexample worker, voto FAIL su
    70f2a76d, 2026-07-25). 'sources', 'verified', 'prove' sono vocabolario
    ORDINARIO del claim, e con >=12 caratteri davanti la prima versione di
    claim_span mangiava il claim e faceva sparire un conflitto numerico VERO:

        "The document lists these sources: 12 papers" vs "... 30 papers"
        "The API latency verified: 45 ms"            vs "... 90 ms"
        "le prove: 3 superate"                       vs "... 8 superate"

    Erano gia' chiusi dal criterio del section-break (nessun delimitatore prima
    del marcatore), introdotto in parallelo su segnalazione di glm-5.2 sulla
    stessa classe. Restano qui come regressione: se qualcuno allenta il criterio,
    questi tre cadono."""
    from verimem.quantity_match import numeric_conflict

    assert numeric_conflict("The document lists these sources: 12 papers",
                            "The document lists these sources: 30 papers") is not None
    assert numeric_conflict("The API latency verified: 45 ms",
                            "The API latency verified: 90 ms") is not None
    assert numeric_conflict("le prove: 3 superate",
                            "le prove: 8 superate") is not None
