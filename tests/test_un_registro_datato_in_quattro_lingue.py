"""Un registro di consegne in tedesco perde due fatti su tre; in francese, a metà.

IL BUCO DICHIARATO nella cura `fb8f0780` (le date distinguono due eventi), qui
misurato invece che lasciato aperto::

    DE  «12. Marz 2026» / «20. April 2026»      date viste: []  e  []
    ES  «12 de marzo de 2026» / «20 de abril»   date viste: []  e  []
    FR  «12 mars 2026» / «20 avril 2026»        date viste: [(2026,3,12)] e []

⚠️ IL CASO FRANCESE È PEGGIO DEGLI ALTRI DUE, e nessuno se ne sarebbe accorto:
``mars`` viene riconosciuto **per collisione** — ``_MONTHS`` tronca a tre lettere
e ``mars[:3] == march[:3] == "mar"`` — mentre ``avril[:3] = "avr"`` non c'è. Una
data vista e l'altra no ⇒ ``da and db`` è falso ⇒ il discriminante tace, e tace
**in modo imprevedibile**: dipende da quali mesi capitano nelle due frasi.

📌 IL FORMATO ISO FUNZIONA GIÀ IN OGNI LINGUA (misurato: una frase tedesca con
«2026-03-12» distingue correttamente). Il buco riguarda solo i mesi scritti a
parole, ed è esattamente come li scrive un essere umano in un verbale.

⚠️ E LO SPAGNOLO HA UNA FORMA CHE NESSUNA DELLE ALTRE TRE HA: «12 **de** marzo
**de** 2026». Il pattern `<giorno> <mese> <anno>` non la vede — non per la lista
dei mesi, per le particelle in mezzo. Aggiungere solo le parole non basta.

🔑 PERCHÉ QUESTA LISTA NON È «LA STESSA MALATTIA CON PIÙ RIGHE» — la riserva che
mi ero scritto io consegnando la cura precedente. Tre condizioni, tutte
verificate qui sotto: il buco è **misurato** su casi reali, non ipotizzato; il
rischio di falso positivo è **misurato** («non l'ho mai visto» non produce
nessuna data, perché il pattern esige giorno+mese+anno); e c'è un presidio per
lingua, così la prossima lingua che manca sarà un test che manca, non un
comportamento che nessuno ha guardato.
"""
from __future__ import annotations

import pytest

from verimem.temporal_context import date_menzionate


@pytest.mark.parametrize("lingua,a,b", [
    ("DE", "Die Lieferung erfolgte am 12. Marz 2026.",
           "Die Lieferung erfolgte am 20. April 2026."),
    ("DE-umlaut", "Die Lieferung erfolgte am 12. März 2026.",
                  "Die Lieferung erfolgte am 30. Mai 2026."),
    ("FR", "La livraison a eu lieu le 12 mars 2026.",
           "La livraison a eu lieu le 20 avril 2026."),
    ("ES", "La entrega se realizo el 12 de marzo de 2026.",
           "La entrega se realizo el 20 de abril de 2026."),
])
def test_due_date_in_una_lingua_europea_sono_DISTINTE(lingua, a, b):
    """IL CUORE: senza questo, un registro di eventi datati in quelle lingue
    viene mangiato dalla supersessione, che è il nodo più costoso che abbiamo."""
    da, db = date_menzionate(a), date_menzionate(b)
    assert da, f"{lingua}: nessuna data vista in «{a}»"
    assert db, f"{lingua}: nessuna data vista in «{b}»"
    assert not (da & db), f"{lingua}: le due date risultano la stessa"


@pytest.mark.parametrize("a,b", [
    ("Die Lieferung erfolgte am 2026-03-12.", "Die Lieferung erfolgte am 2026-04-20."),
    ("La entrega se realizo el 2026-03-12.", "La entrega se realizo el 2026-04-20."),
])
def test_CONTROLLO_POSITIVO_l_ISO_funzionava_gia_e_continua(a, b):
    """La copertura universale che esisteva prima della lista: se cadesse,
    avrei rotto la sola strada che non dipende dalla lingua."""
    assert date_menzionate(a) != date_menzionate(b)
    assert date_menzionate(a) and date_menzionate(b)


def test_la_STESSA_data_in_quattro_lingue_e_UNA_data():
    """⚠️ IL PRESIDIO CHE GIUSTIFICA LA NORMALIZZAZIONE. Senza, due scritture
    della stessa giornata risulterebbero due eventi diversi solo perché in
    lingue diverse — e la cura, invece di salvare i registri, ne creerebbe
    duplicati."""
    atteso = {(2026, 3, 12)}
    for t in ["il 12 marzo 2026", "on 12 March 2026", "am 12. Marz 2026",
              "le 12 mars 2026", "el 12 de marzo de 2026", "2026-03-12",
              "12/03/2026", "March 12, 2026"]:
        assert date_menzionate(t) == atteso, t


@pytest.mark.parametrize("testo", [
    "non l'ho mai visto",
    "mai piu' una cosa del genere",
    "ha aspettato 8 mesi",
    "il documento cita 3 casi",
    "sono stati consegnati 12 pezzi",
])
def test_una_frase_SENZA_data_non_produce_date(testo):
    """⚠️ IL PRESIDIO CONTRO LA LISTA CHE CRESCE. «mai» è maggio in francese e
    «never» in italiano: è la collisione più pericolosa fra le lingue coperte, e
    il pattern la neutralizza perché esige giorno **e** mese **e** anno.

    Se questo test cadesse, ogni «non l'ho mai fatto» del corpus italiano
    porterebbe una data fantasma — e le date decidono la supersessione."""
    assert not date_menzionate(testo), testo
