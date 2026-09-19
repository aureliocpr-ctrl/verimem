"""T161 — «same-source evolution» su due fatti che la stessa fonte non ce l'hanno.

Misurato sullo store vivo, su una copia in sola lettura:

    coppie same-source evolution                     : 533
      con source_signature DIVERSA                   : 159
      con ENTRAMBI i lati senza verified_by          : 533 su 533
      restano evoluzioni con la regola nuova         : 374

Dieci delle 159 lette una per una: dieci su dieci sono oggetti diversi. Fra
queste i due bracci di uno stesso A/B — «explain con file assente 81013
millisecondi» ritirato da «explain con file scritto 2264 millisecondi» — e due
misure diverse dello stesso comando, «doctor riporta 65.1%» ritirato da «doctor
esce con EXIT=1». Il braccio lento è stato archiviato dal braccio veloce.

PERCHÉ SUCCEDE, e perché non è una soglia da tarare: `canonical_source_of`
mette nel secchio `"user"` chiunque non dichiari un `verified_by`, e 533 coppie
su 533 sono in quel caso. Due fatti anonimi risultano quindi SEMPRE «stessa
fonte», qualunque cosa dicano le loro fonti.

⚠️ LA CURA CHE LEGGEVA LA FIRMA FU SCRITTA E RITIRATA IL 2026-08-04 perché
«rompeva il presidio»: con la firma, anche l'aggiornamento legittimo smetteva di
ritirare. La diagnosi di allora fu fatta sulla funzione, e la funzione era
innocente: il candidato che il gate le passa (`anti_confab_gate.py`,
`SimpleNamespace`) porta cinque campi — `verified_by`, `created_at`,
`asserted_at`, `writer_principal`, `proposition` — e `source_signature` non è
fra questi. Chi leggeva la firma vedeva `None` su un lato SEMPRE, quindi ogni
aggiornamento diventava un conflitto.

E la firma non manca: al punto di chiamata la variabile `source` c'è, e viene
ridotta a `cand_ha_source=bool(source and ...)`. Il valore arriva fin lì e si
ferma una chiamata prima — la stessa cosa che era già successa con
`writer_principal`, documentata dieci righe sopra nello stesso file.
"""
from __future__ import annotations

import types

import pytest

from verimem.supersession_policy import (
    canonical_source_of,
    is_same_source,
    source_signature_of,
)


def _fatto(*, verified_by=None, source_signature=None, proposition="x"):
    """Un fatto come lo vede la policy: solo i campi che legge."""
    return types.SimpleNamespace(
        verified_by=verified_by,
        source_signature=source_signature,
        proposition=proposition,
    )


# ------------------------------------------------------------------ cella 1 --
def test_due_anonimi_con_fonti_diverse_non_sono_la_stessa_fonte() -> None:
    """Il caso delle 159: nessuno dei due dichiara un autore, le fonti differiscono.

    Oggi entrambi finiscono nel secchio `"user"` e uno ritira l'altro. È il
    caso di «explain con file assente» contro «explain con file scritto»: due
    bracci di un A/B, e il secondo cancella il primo.
    """
    a = _fatto(source_signature=source_signature_of("la fonte A"))
    b = _fatto(source_signature=source_signature_of("una fonte del tutto altra"))
    assert a.source_signature != b.source_signature, "il banco parte da firme diverse"

    assert not is_same_source(a, b), (
        f"due fatti anonimi con fonti DIVERSE risultano la stessa fonte: "
        f"canonical_source_of dà {canonical_source_of(a)!r} e "
        f"{canonical_source_of(b)!r}. Uno può ritirare l'altro come evoluzione")


# ------------------------------------------------------------------ cella 2 --
def test_la_stessa_fonte_ripresentata_resta_la_stessa_fonte() -> None:
    """L'aggiornamento legittimo: stessa fonte, valore nuovo. DEVE restare evoluzione.

    È la riga che il 04/08 fece ritirare la cura. Se questa cella cade, la cura
    ha ripreso il difetto di allora e non va consegnata.
    """
    firma = source_signature_of("il documento di riferimento, immutato")
    a = _fatto(source_signature=firma, proposition="il valore è 100")
    b = _fatto(source_signature=firma, proposition="il valore è 200")

    assert is_same_source(a, b), (
        "due scritture con la STESSA fonte non risultano la stessa fonte: "
        "l'aggiornamento legittimo smetterebbe di ritirare, che è la "
        "regressione per cui la cura del 2026-08-04 fu ritirata")


# ------------------------------------------------------------------ cella 3 --
def test_chi_dichiara_un_autore_non_viene_giudicato_dalla_fonte() -> None:
    """`verified_by` vince sulla firma: è la dichiarazione più forte.

    La cascata ha un ordine e va tenuto fermo: chi si firma è giudicato dalla
    firma dell'autore, non dal documento che cita.
    """
    a = _fatto(verified_by=["commit abc123"], source_signature="sha256:AAAA")
    b = _fatto(verified_by=["commit abc123"], source_signature="sha256:BBBB")

    assert is_same_source(a, b), (
        "due fatti con lo STESSO verified_by non risultano la stessa fonte: "
        "la firma della fonte ha scavalcato la dichiarazione dell'autore")


# ------------------------------------------------------------------ cella 4 --
def test_senza_fonte_e_senza_autore_si_resta_nel_secchio_comune() -> None:
    """La compatibilità: chi non dichiara niente continua a comportarsi come prima.

    ⚠️ È la cella che vieta la cura più larga del male. Sul corpus vivo la
    maggior parte dei fatti non porta né autore né fonte; se questa cadesse,
    ogni ritiro legittimo fra scritture anonime sparirebbe di colpo.
    """
    a = _fatto()
    b = _fatto()

    assert canonical_source_of(a) == canonical_source_of(b) == "user"
    assert is_same_source(a, b), "due fatti senza nulla non sono più la stessa fonte"


# --------------------------------------------------------- controllo positivo --
def test_il_banco_distingue_davvero_due_firme() -> None:
    """Se le celle sopra diventassero verdi, questa dice che non è perché
    `source_signature_of` ha smesso di distinguere."""
    assert source_signature_of("alfa") != source_signature_of("beta")
    assert source_signature_of("alfa") == source_signature_of("alfa")


@pytest.mark.parametrize("testo", ["", None])
def test_una_fonte_vuota_non_produce_una_firma(testo) -> None:
    """Una stringa vuota non è una fonte: se producesse una firma, tutti i
    fatti «senza fonte» ne avrebbero una identica e risulterebbero la stessa
    fonte per la ragione sbagliata."""
    assert source_signature_of(testo) is None


# ------------------------------------------------------------------ cella 5 --
def test_il_candidato_del_gate_porta_la_firma_della_fonte() -> None:
    """LA CELLA CHE IL 2026-08-04 NON C'ERA, ed è la ragione per cui la cura
    di allora fu ritirata credendola sbagliata.

    Le quattro celle sopra misurano la FUNZIONE, e la funzione era corretta
    anche allora. Il difetto stava nel candidato che il gate le passa: cinque
    campi, e `source_signature` non fra questi — quindi un lato era sempre
    `None` e ogni aggiornamento diventava un conflitto.

    Qui si guarda il codice del gate, non la funzione: se il candidato smette
    di portare la firma, la cascata torna inerte sul percorso vero e nessuna
    delle celle sopra se ne accorgerebbe.
    """
    import ast as _ast
    import pathlib as _pathlib

    from verimem import anti_confab_gate

    sorgente = _pathlib.Path(anti_confab_gate.__file__).read_text(encoding="utf-8")
    albero = _ast.parse(sorgente)

    candidati = [
        n for n in _ast.walk(albero)
        if isinstance(n, _ast.Call)
        and isinstance(n.func, _ast.Attribute)
        and n.func.attr == "SimpleNamespace"
        and {k.arg for k in n.keywords} >= {"verified_by", "proposition"}
    ]
    assert candidati, (
        "nessun candidato costruito con SimpleNamespace trovato nel gate: il "
        "righello guarda un codice che non c'è più, non un difetto assente")

    for nodo in candidati:
        campi = {k.arg for k in nodo.keywords}
        assert "source_signature" in campi, (
            f"il candidato costruito a riga {nodo.lineno} porta {sorted(campi)} "
            f"e NON la firma della fonte: chi lo giudica vedrà sempre None su "
            f"questo lato, e la cascata sarà inerte sul percorso vero")
