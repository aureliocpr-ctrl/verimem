"""«45.000 pallet» contro «32.000 pallet»: NESSUN CONFLITTO RILEVATO.

⚠️ QUESTO FILE È UN GUARDIANO, NON UNA CURA. La cura non c'è ancora, e il file
esiste perché la classe che descrive non ha oggi **nessun** presidio: sei file
presidiano il rilevamento dei conflitti — ``test_facts_conflict`` nelle sue tre
forme, ``test_due_fatti_che_si_contraddicono_non_si_confermano``,
``test_contro_e_vs_non_sono_unita_di_misura``,
``test_due_opposti_non_possono_vivere_insieme`` — e valgono **75 test tutti
verdi**. Se uno solo coprisse il caso qui sotto sarebbe rosso. 🔑 **Il loro verde
non dice che il rilevatore è sano: dice che nessuno guarda da questa parte.**

═══ COSA SUCCEDE, misurato e non dedotto ═══

    45.000 vs 32.000   estratto A []                estratto B []
                       numeric_conflict -> None
    45000  vs 32000    estratto A [('pallet',45000.0)]  B [('pallet',32000.0)]
                       numeric_conflict -> ('pallet', 45000.0, 32000.0)

Il rilevatore è SANO: sugli stessi due numeri senza separatore vede il conflitto
e lo riporta. Ciò che manca è a monte — ``extract_quantities`` non produce più
alcun valore su un numero scritto all'europea, per la cura ``_PUNTO_AMBIGUO``
che ha chiuso un difetto peggiore: ``float("45.000")`` dava ``45.0``, e il gate
**certificava come vero** un fatto che la fonte contraddice di mille volte.

⚖️ **La cura era giusta e il costo è questo**, dichiarato invece che scoperto
dopo: tacere sul valore chiude la certificazione falsa e apre il conflitto non
visto. Il write lo dice già a chi scrive (avviso ``L4.1-ambiguo``, file
``test_il_gate_certificava_un_numero_falso_di_mille_volte``); **il confronto fra
due fatti no**, ed è quello che manca.

═══ 🔑 IL CUORE: ``None`` SIGNIFICA DUE COSE OPPOSTE ═══

    45.000 contro 45000    lo STESSO numero    -> None   ✅ giusto
    45.000 contro 32000    numeri DIVERSI      -> None   ❌ sbagliato

Stesso valore di ritorno per le due domande che devono avere risposta opposta.
Chi legge ``None`` non può sapere se significa «ho guardato e sono uguali» o «non
ho potuto guardare» — ed è la ragione per cui la cura non è aggiungere una
notazione al parser, ma far **dichiarare** al rilevatore quando non è in grado
di confrontare. ⚠️ Quella cura tocca la supersessione, cioè cosa muore in
memoria: non si fa di fretta, e questo guardiano serve proprio perché il difetto
resti visibile finché non si fa.

📌 PERCHÉ È IL CASO CHE CONTA E NON UN CASO DI SCUOLA: i numeri grandi scritti
all'europea sono le giacenze, i byte, i fatturati, le popolazioni. Nel corpus di
casa la classe è **100 proposizioni su 9365** (misura di ws8 su ``semantic.db``
in sola lettura), e le righe sono nostre: «102.913 LOC», «16.300 test».
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities, numeric_conflict

# Stesso soggetto in entrambi i testi («magazzino», «Verona»): la guardia
# same-subject del rilevatore è soddisfatta, quindi ciò che si misura qui è solo
# la lettura del numero. Senza questa accortezza il test misurerebbe la guardia
# e passerebbe per la ragione sbagliata.
EUROPEO_45 = "Il magazzino di Verona contiene 45.000 pallet."
EUROPEO_32 = "Il magazzino di Verona contiene 32.000 pallet."
NUDO_45 = "Il magazzino di Verona contiene 45000 pallet."
NUDO_32 = "Il magazzino di Verona contiene 32000 pallet."


@pytest.mark.xfail(strict=True, reason=(
    "LA CURA NON C'E' ANCORA: numeric_conflict restituisce None perche' "
    "extract_quantities tace sui numeri ambigui, e il rilevatore non distingue "
    "«sono uguali» da «non ho potuto guardare»"))
def test_ALLARME_due_giacenze_diverse_scritte_all_europea_sono_in_conflitto():
    """⚠️ ALLARME CHE SCATTA ALLA GUARIGIONE, non difetto nascosto.

    ``strict=True`` è la parte che conta: quando la cura arriverà questo test
    **passerà**, e uno xfail che passa è ROSSO. Chi cura non deve accorgersene
    da solo — lo scopre dalla suite, e la riga da togliere è il marcatore.
    Senza ``strict`` sarebbe un sensore scollegato: muto in entrambe le
    direzioni, cioè peggio di non averlo.
    """
    assert numeric_conflict(EUROPEO_45, EUROPEO_32) is not None


@pytest.mark.xfail(strict=True, reason=(
    "LA CURA NON C'E' ANCORA: stessa causa, sulla classe a piu' gruppi"))
def test_ALLARME_anche_i_numeri_a_piu_gruppi_sono_in_conflitto():
    """La classe dei byte e dei fatturati — «1.250.000» contro «1.150.000».

    Va tenuta separata dalla precedente perché a monte prende una strada
    diversa: con due o più gruppi il pattern non trova affatto il numero,
    mentre con un gruppo solo lo trova e la cura lo scarta. Due cause, un
    sintomo — e una cura che le chiudesse a metà passerebbe metà file.
    """
    assert numeric_conflict("Il file di Verona pesa 1.250.000 byte.",
                            "Il file di Verona pesa 1.150.000 byte.") is not None


@pytest.mark.xfail(strict=True, reason=(
    "LA CURA NON C'E' ANCORA: entrambe le domande rispondono None"))
def test_ALLARME_due_domande_opposte_non_possono_avere_la_stessa_risposta():
    """🔑 IL TEST CHE DESCRIVE IL DIFETTO MEGLIO DEGLI ALTRI DUE.

    Non chiede che un conflitto venga visto: chiede che **due situazioni
    opposte si distinguano**. Confrontare «45.000» con «45000» (lo stesso
    numero) e con «32000» (un numero diverso) deve dare due risposte diverse —
    oggi ne dà una sola, e per la prima è quella giusta per la ragione
    sbagliata.

    ⚠️ Ed è il test che una cura frettolosa non riesce a ingannare: chi facesse
    dichiarare l'incapacità di confrontare SEMPRE, anche dove i numeri sono
    uguali, passerebbe i due allarmi qui sopra e cadrebbe su questo.
    """
    stesso_numero = numeric_conflict(EUROPEO_45, NUDO_45)
    numero_diverso = numeric_conflict(EUROPEO_45, NUDO_32)
    assert stesso_numero != numero_diverso


def test_CONTROLLO_NEGATIVO_senza_separatori_il_rilevatore_VEDE_il_conflitto():
    """⚠️ SENZA QUESTO, i tre allarmi si leggerebbero come «il rilevatore dei
    conflitti è rotto» — e non lo è.

    Gli stessi due valori, scritti senza separatore, producono il conflitto con
    unità e valori. Il difetto sta in cosa arriva al rilevatore, non in cosa il
    rilevatore ne fa: è la differenza fra riparare il parser e riparare il
    confronto, e senza questa riga la prossima persona ripara la cosa
    sbagliata.
    """
    assert numeric_conflict(NUDO_45, NUDO_32) == ("pallet", 45000.0, 32000.0)


@pytest.mark.parametrize("a,b,atteso", [
    ("La tolleranza di Verona e' 0.250 mm.",
     "La tolleranza di Verona e' 0.125 mm.", ("mm", 0.25, 0.125)),
    ("Il magazzino di Verona contiene 480 pallet.",
     "Il magazzino di Verona contiene 320 pallet.", ("pallet", 480.0, 320.0)),
])
def test_CONTROLLO_POSITIVO_decimali_certi_e_interi_restano_confrontabili(
        a, b, atteso):
    """LA POPOLAZIONE OPPOSTA, che dice quanto è ampio il buco.

    I decimali con lo zero davanti («zero mila» non esiste) e gli interi nudi
    non sono mai stati ambigui e continuano a produrre conflitti. Il buco è la
    sola classe descritta in cima — non «i numeri», e non «i conflitti».
    """
    assert numeric_conflict(a, b) == atteso


def test_LA_CAUSA_HA_UN_INDIRIZZO_e_sta_a_monte_del_rilevatore():
    """Dove guardare per curare: il valore non arriva, non viene scartato dopo.

    Ancorare la causa in un test la rende falsificabile insieme al resto: se un
    giorno ``extract_quantities`` tornasse a produrre un valore qui, questa
    riga diventerebbe rossa e direbbe che la diagnosi in cima è invecchiata.
    """
    assert extract_quantities(EUROPEO_45) == set()
    assert extract_quantities(NUDO_45) == {("pallet", 45000.0)}
