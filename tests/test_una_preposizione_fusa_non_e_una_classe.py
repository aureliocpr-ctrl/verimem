"""«Il server è nel datacenter» non dice CHE COSA è il server.

`_copula_parse` protegge gia' dal locativo: distingue l'articolo dalla
preposizione per lingua, perche' «a» e' articolo in inglese («is a labrador»)
e preposizione in italiano («è a Roma»). La protezione pero' conosce solo le
preposizioni NUDE, e italiano e francese fondono preposizione e articolo in
UNA parola sola — che in italiano e' la forma piu' comune delle due.

Misurato (2026-08-01), 7 locativi su 10 accettati come se fossero classi:

    Il server è nel datacenter di Milano. -> ('il server', 'nel datacenter di milano')
    Il server è al lavoro.                -> ('il server', 'al lavoro')
    Il file è sul disco.                  -> ('il file', 'sul disco')
    Le bureau est au centre.              -> ('le bureau', 'au centre')     (au = à+le)
    Le serveur est aux Pays-Bas.          -> ('le serveur', 'aux pays-bas') (aux = à+les)
    Il documento è nell'archivio.         -> ('il documento', "nell'archivio")
    El coche es al lado.                  -> ('el coche', 'al lado')        (al = a+el)

mentre «Il gatto è a Roma.» veniva respinto correttamente: la guardia c'era e
smetteva di esistere sulla forma articolata.

E in francese anche l'ACCENTO: «est a Paris» respinto, «est à Paris»
accettato. La preposizione francese e' `à`; `a` senza accento e' il verbo
avere, cioe' proprio quella che NON serviva.

IL DANNO NON E' PERDERE UN'ANALISI, E' FABBRICARE UNA CONTESA.
`_copula_parse` e `subject_key` alimentano cinque moduli — composer, guardian
(le contraddizioni), active_probe (la contro-evidenza), source_trust,
ignorance_map. Con il locativo preso per una classe, «Il server è nel
datacenter di Milano» e «Il server è un nodo di produzione» diventano due
CLASSI RIVALI dello stesso soggetto: due fatti veri e compatibili messi in
contesa, che e' l'errore che il commento del modulo dichiara di voler evitare.

L'inglese non e' toccato: li' nessun difetto e' stato misurato, e non fonde le
preposizioni con gli articoli.
"""
from __future__ import annotations

import pytest

from verimem.composer import _copula_parse

# --- il difetto: preposizione + articolo in una parola sola ---------------

LOCATIVI_FUSI = [
    # italiano — tutte e cinque le preposizioni che si articolano
    ("Il server è nel datacenter di Milano.", "in + il"),
    ("Il server è al lavoro.", "a + il"),
    ("Il file è sul disco.", "su + il"),
    ("Il backup è dalla parte giusta.", "da + la"),
    ("La chiave è negli archivi.", "in + gli"),
    ("Il valore è del cliente.", "di + il"),
    ("Il dato è coi backup.", "con + i"),
    # italiano — la forma ELISA, che lo split() lascia attaccata al nome
    ("Il documento è nell'archivio.", "in + l'"),
    ("Il record è dall'inizio.", "da + l'"),
    # francese — le due contrazioni, e l'accento
    ("Le bureau est au centre.", "à + le"),
    ("Le serveur est aux Pays-Bas.", "à + les"),
    ("Le chat est à Paris.", "à accentata: la lista aveva solo 'a'"),
    ("Le chat est à l'hôtel.", "à + articolo eliso"),
    # spagnolo — la contrazione che mancava accanto a `del`, che c'era
    ("El coche es al lado.", "a + el"),
]


@pytest.mark.parametrize("frase,forma", LOCATIVI_FUSI,
                         ids=[f for f, _ in LOCATIVI_FUSI])
def test_un_locativo_fuso_non_e_una_classe(frase, forma):
    assert _copula_parse(frase) is None, (
        f"{forma}: locativo accettato come classe -> {_copula_parse(frase)}")


# --- e la guardia non deve diventare cieca: cio' che passava, passa -------

CLASSI_VERE = [
    "Rex is a labrador.",
    "Il gatto è un labrador.",
    "Le chat est un labrador.",
    "El gato es un labrador.",
    "Il gatto è l'animale preferito.",
    "Le chat est l'animal favori.",
]


@pytest.mark.parametrize("frase", CLASSI_VERE)
def test_una_classe_vera_continua_a_passare(frase):
    """Il rischio opposto: una lista troppo larga rende muto il confronto.
    Perdere una classe legittima costa un fatto in meno nei confronti — ma su
    CINQUE moduli, e senza che nessuno lo dichiari."""
    assert _copula_parse(frase) is not None, f"classe vera respinta: {frase}"


def test_i_locativi_nudi_restano_respinti():
    """La guardia che gia' c'era non si tocca."""
    for frase in ("Il gatto è a Roma.", "Rex e' a Roma.",
                  "The server is at the office.", "El servidor es del centro.",
                  "Le chat est a Paris."):
        assert _copula_parse(frase) is None, frase


def test_una_parola_che_INIZIA_come_una_preposizione_non_lo_e():
    """`nel` e' una preposizione, `nelson` no: il confronto e' sulla PAROLA.

    E' il rischio che l'elencazione porta con se' — la stessa forma di difetto
    gia' pagata su questo repo, dove un nome veniva trovato dentro un'altra
    parola. Qui il confronto e' su token interi, e questo test lo inchioda.
    """
    for frase in ("Il cantante è Nelson Mandela.",
                  "Il colore è alabastro.",
                  "Il pesce è sulmone."):
        assert _copula_parse(frase) is not None, (
            f"parola respinta perche' INIZIA come una preposizione: {frase}")
