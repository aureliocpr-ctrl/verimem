"""Due fatti tedeschi scorrelati si ritiravano a vicenda.

Il criterio dell'evoluzione riconosce i nomi propri dalla MAIUSCOLA. In
tedesco TUTTI i sostantivi sono maiuscoli, quindi finiscono tutti fra i nomi e
`_parole_di_contenuto` li toglie. Quello che resta e' la grammatica:

    Der Server ist ein Produktionsknoten.    -> ['ein', 'ist']   testa 'ist'
    Die Datenbank ist ein Postgres Cluster.  -> ['ein', 'ist']   testa 'ist'

Le uniche parole di contenuto sono l'articolo e il verbo essere, e il criterio
scatta per DUE vie insieme — stessa testa nominale, e due parole condivise.
Verdetto misurato: `_puo_essere_una_evoluzione` -> True. Il secondo fatto
RITIRA il primo. Chi scrive dieci misure in tedesco ne ritrova una.

E NON E' UN PROBLEMA DI LISTA INCOMPLETA. Aggiungere `der`/`die`/`das`/`ist`
alle parole vuote curerebbe il tedesco e lascerebbe identici il polacco, il
turco, il russo, l'indonesiano e le altre settemila. Il prodotto ha liste per
quattro lingue e utenti in tutto il mondo: la strada delle liste non arriva in
fondo, per costruzione.

LA CURA E' CHE IL CRITERIO SI ACCORGA DI NON SAPER LEGGERE. Il segnale e'
strutturale e non nomina nessuna lingua: se in una frase quasi ogni parola e'
capitalizzata, il riconoscimento dei nomi propri PER MAIUSCOLA non e'
applicabile li' — e cio' che resta come «contenuto» non e' contenuto, e' lo
scarto. In quel caso il criterio non decide, e non decidere significa NON
dichiarare l'evoluzione: restano due fatti vivi in contesa, che e' il verso di
errore che questo modulo dichiara di preferire.

Copre anche il Title Case («The Server Is A Production Node»), dove il segnale
e' lo stesso e la conclusione pure.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import _puo_essere_una_evoluzione

DE_SCORRELATI = [
    ("Der Server ist ein Produktionsknoten.",
     "Die Datenbank ist ein Postgres Cluster."),
    ("Der Graph hat 8625 Knoten.",
     "Die Quarantaene haelt 528 Fakten zurueck."),
    ("Das Repository hat 113 Commits.",
     "Der Korpus enthaelt 6682 Fakten."),
]


@pytest.mark.parametrize("vecchio,nuovo", DE_SCORRELATI,
                         ids=[a[:34] for a, _ in DE_SCORRELATI])
def test_due_fatti_tedeschi_scorrelati_non_si_ritirano(vecchio, nuovo):
    assert _puo_essere_una_evoluzione(nuovo, vecchio) is False, (
        "due fatti scorrelati dichiarati l'uno l'aggiornamento dell'altro: "
        "in tedesco i sostantivi sono maiuscoli e spariscono dal contenuto, "
        "quindi restano solo articolo e copula")


def test_anche_il_title_case_inglese_e_illeggibile():
    """Stesso segnale, stessa conclusione — e non serve sapere che lingua e'."""
    assert _puo_essere_una_evoluzione(
        "The Database Is A Postgres Cluster.",
        "The Server Is A Production Node.") is False


def test_le_lingue_coperte_non_si_muovono():
    """Il vincolo vero: italiano e inglese in minuscolo continuano a decidere
    come prima, perche' e' su quel comportamento che gira tutto il corpus."""
    assert _puo_essere_una_evoluzione(
        "Il piano annuale costa 200 euro.",
        "Il piano annuale costa 100 euro.") is True
    assert _puo_essere_una_evoluzione(
        "The annual plan costs 200 euros.",
        "The annual plan costs 100 euros.") is True


def test_un_nome_proprio_in_una_frase_normale_non_la_rende_illeggibile():
    """La guardia deve scattare sulla DENSITA', non sulla presenza: una frase
    italiana con due nomi propri e' perfettamente leggibile."""
    assert _puo_essere_una_evoluzione(
        "Il server di Roma ospita il cluster Postgres da marzo.",
        "Il server di Roma ospita il cluster Postgres da gennaio.") is True


def test_una_frase_di_una_parola_non_manda_in_crisi_la_guardia():
    for a, b in (("Rust.", "Python."), ("", "qualcosa"), ("qualcosa", "")):
        assert isinstance(_puo_essere_una_evoluzione(b, a), bool)
