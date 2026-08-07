"""«monta la versione 2.1» non conteneva nessuna versione. Solo in italiano.

IL DIFETTO, e l'ironia e' il dato: ``_VERSION2_KW_RE`` elenca le parole chiave
in inglese — ``version|versions|release|releases|build|builds|v`` — e le altre
lingue maggiori si salvano **per somiglianza**, non per copertura::

    EN  runs version 2.1          -> {'2.1'}   ok
    DE  laeuft Version 2.1        -> {'2.1'}   ok  ← «Version» si scrive uguale
    FR  execute la version 2.1    -> {'2.1'}   ok  ← idem
    ES  ejecuta la version 2.1    -> {'2.1'}   ok  ← idem (senza accento)
    IT  monta la versione 2.1     -> set()     🔴  ← la «e» finale lo rompe

🔑 **L'UNICA LINGUA CHE CADE E' QUELLA IN CUI IL PRODOTTO E' SCRITTO**, e non e'
una coincidenza: tedesco, francese e spagnolo passano perche' scrivono
«version» come l'inglese. L'italiano declina, e basta una vocale in fondo. E'
la stessa forma del difetto che ws5 ha misurato su ``ask`` («sbaglia solo in
IT») e di quello che ws4 ha misurato su ``norm_unit`` («minuti»/«minuto»).

⚠️ COSA COSTA. ``version_conflict`` e' uno dei detector che decidono la
SUPERSESSIONE: se le versioni non vengono estratte, due fatti italiani sulla
stessa cosa a due versioni diverse **non sono mai in conflitto**, e il vecchio
resta vivo accanto al nuovo. E' il ramo gemello di cio' che ws2 ha misurato sul
numerico: due verita' contemporanee sullo stesso dato.

LA CURA NON E' UNA LISTA DI LINGUE — e' la RADICE. Tutte le lingue romanze e
germaniche prendono la parola dal latino *versio*::

    version · versions · versione · versioni · versionen · versión ·
    versiones · versão · versões · versioning

Una radice con il suffisso libero le copre tutte, comprese quelle che nessuno
di noi parla, e non cresce con l'elenco delle lingue supportate.

⛔ NON ho esteso ``release`` e ``build``: sono prestiti che ogni lingua tecnica
usa in inglese, e allargarli sarebbe rumore senza un caso che lo chieda. La
parola che ogni lingua traduce DAVVERO e' *version*.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_versions, version_conflict

#: La stessa frase in sei lingue: la versione dev'essere vista in tutte.
LINGUE = [
    ("EN", "the machine runs version 2.1"),
    ("IT", "la macchina monta la versione 2.1"),
    ("IT", "il server esegue le versioni 2.1"),
    ("DE", "die Maschine laeuft Version 2.1"),
    ("DE", "die Maschinen laufen Versionen 2.1"),
    ("FR", "la machine execute la version 2.1"),
    ("ES", "la maquina ejecuta la version 2.1"),
    ("ES", "las maquinas ejecutan las versiones 2.1"),
    ("PT", "a maquina executa a versao 2.1"),
]

#: ⚠️ LA POPOLAZIONE OPPOSTA. Un numero a due componenti conta come versione
#: SOLO vicino a una parola chiave: altrove e' un decimale e appartiene al
#: percorso numerico. Se la radice fosse troppo larga, un decimale qualsiasi
#: diventerebbe una versione e i conflitti numerici si sposterebbero di ramo.
NON_SONO_VERSIONI = [
    "la temperatura e' 2.3 degrees",
    "il margine e' 2.3 punti",
    "il bench ha fatto 120 versus 2.3",     # «versus» inizia per «vers»
    "si sposta verso 2.3",                  # «verso» inizia per «vers»
    "il verso 2.3 della poesia",
    # ⚠️ L'OMOGRAFO CHE HA DECISO LA FORMA DELLA RADICE: in italiano «versi»
    # sono le righe di una poesia. Una radice `versi\w*` — che sarebbe la piu'
    # corta a coprire tutte le lingue — li catturerebbe. Per questo la radice
    # e' `version` e le forme portoghesi sono elencate a parte: e' piu' lunga
    # da scrivere ed e' l'unica che non inventa versioni dove non ce ne sono.
    "i versi 2.3 sono i piu' belli",
    "ha versato 2.3 euro",
]


@pytest.mark.parametrize("lingua,frase", LINGUE)
def test_la_versione_si_riconosce_in_ogni_lingua(lingua, frase):
    """IL CUORE: «versione», «Versionen», «versiones», «versão» sono la stessa
    parola in lingue diverse. Vederne una sola significa che la supersessione
    per versione funziona solo per chi scrive in inglese."""
    assert extract_versions(frase) == {"2.1"}, f"{lingua}: «{frase}»"


@pytest.mark.parametrize("frase", NON_SONO_VERSIONI)
def test_CONTROLLO_POSITIVO_un_decimale_non_diventa_una_versione(frase):
    """⚠️ IL PRESIDIO CHE RENDE CONSEGNABILE LA CURA. «versus» e «verso»
    cominciano per «vers»: una radice troppo corta li catturerebbe, e un
    decimale qualsiasi diventerebbe una versione — spostando di ramo conflitti
    che il percorso numerico gestisce gia'."""
    assert not extract_versions(frase), frase


def test_due_versioni_italiane_diverse_ora_confliggono():
    """L'effetto che conta: senza questa cura due fatti italiani sulla stessa
    macchina a due versioni diverse non erano MAI in conflitto, e il vecchio
    restava vivo accanto al nuovo."""
    assert version_conflict(
        "Il gateway Helios monta la versione 2.1.",
        "Il gateway Helios monta la versione 3.4.") == ("2.1", "3.4")


def test_CONTROLLO_POSITIVO_l_inglese_non_si_muove():
    """La popolazione che gia' funzionava: nessuna cura sulle altre lingue deve
    spostare cio' che l'inglese faceva."""
    assert extract_versions("upgrade to version 2.1") == {"2.1"}
    assert extract_versions("release 3.4.0 is out") == {"3.4.0"}
    assert extract_versions("running v2.1") == {"2.1"}
    assert extract_versions("build 7.0.1") == {"7.0.1"}
