"""«45 minuti» e «1 minuto» erano due unità diverse, e nessuno l'aveva scelto.

IL DIFETTO, censito da ws4 sul mandato lingue di Aurelio: ``norm_unit`` fa
lookup su ``_UNIT_SYN`` — inglese puro — più due regole di plurale **inglesi**.
Misurato::

    EN  minute -> min      minutes -> min       ok
    FR  minute -> min      minutes -> min       ok  ← per caso: parole uguali all'EN
    ES  minuto -> minuto   minutos -> minuto    ok  ← per caso: il plurale è in -s
    IT  minuto -> minuto   minuti  -> minuti    🔴 DUE UNITÀ DIVERSE
    DE  Minute -> min      Minuten -> minuten   🔴
    DE  Tag    -> tag      Tage    -> tage      🔴

🔑 **Le tre lingue che funzionano, funzionano per caso**: francese e inglese
scrivono «minute» allo stesso modo, e spagnolo e portoghese fanno il plurale in
``-s`` come l'inglese. Italiano e tedesco no, e **non è una scelta di nessuno**:
è il bordo di una regola scritta per una lingua sola.

⚠️ COSA COSTA. Due fatti che parlano della stessa grandezza non condividono
l'unità, quindi:
  * un CONFLITTO vero fra «la riunione dura 30 minuti» e «…45 minuti» può
    sfuggire al rilevamento (unità diverse ⇒ grandezze diverse);
  * ``L4.2`` — il criterio del vicinato — sta a valle e ne eredita il bordo:
    l'intorno di un numero non coincide se singolare e plurale restano parole
    diverse. Il caso che lo distingue è di ws4: **«45 Minuten» contro «30
    Minuten»**.

LA CURA NON È UNA LISTA DI PAROLE, ed è la richiesta che ho fatto io stesso al
canale («non consegnatemi *aggiungi la lingua X alla lista*»): i plurali si
formano con **suffissi**, e sono una manciata::

    -s      EN · FR · ES · PT        (già presente)
    -i -e   IT
    -en -er DE

È morfologia, non lessico: una regola che non cresce con le parole del mondo.

⚠️ E IL RISCHIO VA MISURATO, non dichiarato: togliere ``-i`` o ``-e`` accorcia
anche parole che plurali non sono, e due unità distinte potrebbero collassare
sulla stessa radice. I presidi qui sotto misurano proprio quella popolazione.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import norm_unit

#: singolare e plurale della STESSA unità: devono normalizzare uguale.
STESSA_UNITA = [
    ("EN", "minute", "minutes"), ("EN", "day", "days"), ("EN", "hour", "hours"),
    ("IT", "minuto", "minuti"), ("IT", "giorno", "giorni"),
    ("IT", "pezzo", "pezzi"),
    ("IT", "metro", "metri"), ("IT", "litro", "litri"),
    ("DE", "Minute", "Minuten"), ("DE", "Stunde", "Stunden"),
    ("FR", "minute", "minutes"), ("ES", "minuto", "minutos"),
]

#: ⚠️ Unità DIVERSE che una regola di stemming troppo avida farebbe collassare.
#: È la popolazione opposta, e senza di lei il test sopra è soddisfatto anche
#: da una funzione che restituisce sempre la stessa stringa.
UNITA_DISTINTE = [
    ("ora", "oro"), ("mese", "mesi"),
    # ⚠️ TRE MIEI ERRORI CORRETTI DAL BANCO, e vale la pena scriverli: «case/casa»,
    # «metro/metri» e «litro/litri» li avevo messi qui come unita' DISTINTE, e
    # sono singolare e plurale della stessa parola. Il test pretendeva che la
    # cura sbagliasse. Quarta volta oggi che il banco misura se' stesso.
    ("euro", "ero"), ("tonne", "tonno"),
]


@pytest.mark.parametrize("lingua,singolare,plurale", STESSA_UNITA)
def test_singolare_e_plurale_sono_LA_STESSA_unita(lingua, singolare, plurale):
    """IL CUORE: due fatti che parlano di minuti devono condividere l'unità,
    che chi scrive abbia usato il singolare o il plurale."""
    a, b = norm_unit(singolare), norm_unit(plurale)
    assert a == b, f"{lingua}: «{singolare}»->{a} ≠ «{plurale}»->{b}"


@pytest.mark.parametrize("una,altra", UNITA_DISTINTE)
def test_CONTROLLO_POSITIVO_due_unita_DIVERSE_restano_diverse(una, altra):
    """⚠️ IL PRESIDIO CHE RENDE CONSEGNABILE LA CURA. «ora» e «oro» finiscono
    entrambe con una vocale che in italiano segna un plurale: se lo stemming le
    collassasse, due grandezze diverse diventerebbero la stessa e il gate
    vedrebbe conflitti che non esistono. Peggio del difetto curato."""
    assert norm_unit(una) != norm_unit(altra), (
        f"«{una}» e «{altra}» collassano su {norm_unit(una)!r}")


def test_LIMITE_DICHIARATO_il_plurale_tedesco_in_e_resta_scoperto():
    """⚠️ IL LIMITE, misurato e scritto invece che nascosto.

    «Tag»/«Tage» NON si uniscono, e non e' una dimenticanza: il plurale tedesco
    in ``-e`` **collide con quello italiano**, dove ``-e`` segna il plurale di
    un femminile in ``-a`` («cassa»→«casse»). Senza sapere in che lingua e'
    scritto il testo le due regole si contraddicono, e far vincere il tedesco
    romperebbe l'italiano — che e' la lingua in cui questo store e' scritto.

    Coperto in tedesco resta il plurale in ``-en``, che e' il piu' frequente e
    non ha collisioni. Chiudere anche ``-e`` richiede il rilevamento della
    lingua, che e' un'altra cura e non un'altra riga.
    """
    assert norm_unit("tage") != norm_unit("tag")
    # e il costo dall'altra parte: il plurale femminile italiano resta scoperto
    assert norm_unit("casse") != norm_unit("cassa")
    # ma il SINGOLARE tedesco non viene rotto, che era il danno peggiore
    assert norm_unit("stunde") == "stunde"


def test_l_INGLESE_non_cambia():
    """La popolazione che già funzionava: le sinonimie inglesi restano quelle,
    e nessuna cura sulle altre lingue deve spostarle."""
    assert norm_unit("hours") == norm_unit("hour") == "h"
    assert norm_unit("minutes") == "min"
    assert norm_unit("days") == "day"


def test_una_parola_che_non_e_una_unita_resta_se_stessa():
    """Il perimetro: ``norm_unit`` normalizza, non inventa. Una parola che non
    è un'unità deve tornare indietro riconoscibile — se la accorciasse, il
    vicinato di L4.2 confronterebbe monconi."""
    for w in ("", "x"):
        assert norm_unit(w) == w
