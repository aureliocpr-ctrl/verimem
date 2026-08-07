"""«40 Stück» non aveva unità, e «40 Stueck» sì. La differenza era l'umlaut.

IL DIFETTO, misurato da ws4 (gradino 4 della sua mappa) e riprodotto::

    40 unità    -> unità VUOTA      40 Stueck   -> 'stueck'  ✓
    40 Stück    -> VUOTA            40 minuti   -> 'minuto'  ✓
    40 años     -> VUOTA            40 metri    -> 'metro'   ✓
    40 unités   -> VUOTA

``_QUANT_RE`` cattura l'unità con ``([A-Za-z]+)`` — la classe ASCII — quindi
ogni unità che porta un accento, un umlaut o una tilde **non viene vista**. E
``norm_unit`` non recupera a valle: ``unità`` e ``unita`` restano due unità
diverse, ``Stück`` e ``Stuck`` pure.

🔑 PERCHÉ È PEGGIO DI QUANTO SEMBRI: colpisce le parole più comuni del dominio.
``Stück`` è il tedesco per «pezzi», l'unità di magazzino per eccellenza;
``unità`` è la stessa cosa in italiano; ``años`` conta gli anni in spagnolo.
⇒ E SPIEGA PERCHÉ IL TEDESCO SEMBRAVA FUNZIONARE: nei banchi di oggi abbiamo
  usato tutti «Minuten», «Paletten», «Stunden» — parole **senza umlaut**. Il
  sottoinsieme che si scrive in ASCII passava, e nessuno aveva provato l'altro.

📌 È LA CLASSE ②, LA CURA C'ERA E MANCAVA LO SWEEP, ed è documentata a
quindici righe di distanza in questo stesso modulo. Il 2026-08-04 qualcuno
scrisse per ``content_tokens``::

    «Le lettere di QUALUNQUE alfabeto, non solo ASCII. [a-zA-Z]{4,} è la classe
     ASCII […] accenti italiani: la parola TRONCATA sull'accento — «città» ->
     citt, «però» -> per (3 char, via).»

La diagnosi era giusta, la cura fu applicata a una funzione sola, e ``_QUANT_RE``
— nello stesso file, con lo stesso identico difetto — non fu toccata. La domanda
che mancava è quella che questa casa si è scritta: *chi ALTRO fa la stessa cosa?*

⚠️ E LA CURA CHIUDE ANCHE IL GRADINO 2 DELLA MAPPA DI ws4: cirillico, greco e
arabo avevano «numero sì, unità vuota» per la stessa ragione — ``[A-Za-z]`` non
li contiene. Non è un effetto collaterale: è lo stesso difetto visto su alfabeti
diversi.

⛔ NON tocca il gradino 3 (cinese, giapponese, thai), dove il numero non viene
proprio catturato perché i lookaround ``(?<![\\w.])``/``(?![\\w])`` falliscono in
assenza di spazi. È un difetto diverso, con una cura diversa, e ws4 avverte che
allargarlo cambierebbe la cattura in TUTTE le lingue.
"""
from __future__ import annotations

import pytest

from verimem.quantity_match import extract_quantities, norm_unit

#: Unità che portano un segno diacritico: devono essere viste come le altre.
CON_DIACRITICI = [
    ("IT", "il magazzino contiene 40 unità", "unita"),
    ("DE", "das Lager hat 40 Stück", "stuck"),
    ("ES", "el almacen tiene 40 años", "ano"),
    ("FR", "la reunion dure 40 unités", "unite"),
    ("DE", "die Halle misst 40 Fläche", "flache"),
    ("PT", "o armazem tem 40 caixões", "caixoe"),
]

#: ⚠️ IL GRADINO 2 di ws4, chiuso dalla stessa cura: alfabeti non latini con
#: gli spazi fra le parole. Nulla li distingue dal latino se non il blocco
#: Unicode — e nulla giustifica che l'unità sparisca.
ALFABETI_NON_LATINI = [
    ("RU", "на складе 40 паллет", "паллет"),
    ("EL", "η αποθήκη έχει 40 παλέτες", "παλετες"),
    ("AR", "المستودع به 40 منصة", "منصة"),
]

#: ⚠️ LA POPOLAZIONE OPPOSTA: ciò che già funzionava non deve muoversi. Senza,
#: la cura è soddisfatta anche da un regex che cattura qualunque cosa.
NON_DEVONO_MUOVERSI = [
    ("la riunione e' durata 45 minuti", "minuto"),
    ("il magazzino contiene 300 pallet", "pallet"),
    ("the warehouse holds 300 pallets", "pallet"),
    ("il file pesa 72 MB", "mb"),
    ("40 Stueck ohne Umlaut", "stueck"),
]


@pytest.mark.parametrize("lingua,frase,attesa", CON_DIACRITICI)
def test_una_unita_con_accento_viene_vista(lingua, frase, attesa):
    """IL CUORE: «Stück» è l'unità di magazzino più comune in tedesco. Non
    vederla significa che ogni inventario scritto correttamente nella propria
    lingua perde la grandezza che misura."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert attesa in unita, f"{lingua}: «{frase}» -> {unita}"


@pytest.mark.parametrize("lingua,frase,attesa", ALFABETI_NON_LATINI)
def test_il_GRADINO_2_alfabeti_non_latini_con_spazi(lingua, frase, attesa):
    """Il gradino 2 della mappa di ws4: russo, greco e arabo hanno gli spazi
    fra le parole come il latino, e avevano «numero sì, unità vuota» per la
    stessa ragione — la classe ASCII. Stesso difetto, alfabeto diverso."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert attesa in unita, f"{lingua}: «{frase}» -> {unita}"


@pytest.mark.parametrize("frase,attesa", NON_DEVONO_MUOVERSI)
def test_CONTROLLO_POSITIVO_cio_che_funzionava_non_si_muove(frase, attesa):
    """⚠️ IL PRESIDIO. Allargare una classe di caratteri è la cura che più
    facilmente cattura troppo: qui si misura che le unità già lette restino
    identiche, compreso «Stueck» scritto senza umlaut."""
    unita = {u for u, _v in extract_quantities(frase) if u}
    assert attesa in unita, f"«{frase}» -> {unita}"


def test_una_unita_accentata_e_la_sua_forma_ASCII_sono_LA_STESSA():
    """L'altra metà del difetto, a valle: chi scrive «unità» e chi scrive
    «unita» misurano la stessa grandezza. Se restano due unità diverse, due
    fatti sullo stesso magazzino non si confrontano — e il conflitto sfugge."""
    assert norm_unit("unità") == norm_unit("unita")
    assert norm_unit("Stück") == norm_unit("Stuck")
    # ⚠️ LIMITE: «Stueck» e' una TRASLITTERAZIONE, non un accento caduto, e
    # resta a parte. Unirla richiederebbe la regola inversa `ue -> u`, che
    # romperebbe ogni parola in cui `ue` sta per se stesso. Il codice lo dichiara.
    assert norm_unit("Stueck") != norm_unit("Stück")
    assert norm_unit("años") == norm_unit("anos")
    assert norm_unit("unités") == norm_unit("unites")


def test_il_gradino_3_ERA_aperto_e_ora_e_chiuso():
    """⚠️ QUESTO TEST DICEVA IL CONTRARIO UN'ORA FA, e l'aggiornamento è il
    dato: dichiarava che in cinese il numero non veniva catturato e che questa
    cura non lo toccava. Era vero, ed è stato chiuso subito dopo da una cura
    diversa — il lookbehind ``(?<![\\w.])`` ristretto alle lettere LATINE
    (``test_un_numero_attaccato_a_una_lettera_cinese``).

    Lo lascio qui, riscritto invece che cancellato, perché è la prova che i due
    gradini erano difetti separati con cure separate: la classe di caratteri
    dell'UNITÀ (curata qui) e il lookbehind del NUMERO (curato lì). Chi ne
    cura una sola e misura sull'altra lingua conclude che non funziona — ed è
    esattamente l'avvertimento che ws4 aveva scritto proponendo la mappa.

    ⚠️ IL LIMITE CHE RESTA: l'unità cinese cattura ``个托盘`` tutto insieme —
    il classificatore più il sostantivo — perché senza spazi non c'è un confine
    di parola da rispettare. È leggibile e confrontabile con sé stessa, quindi
    il conflitto numerico funziona; non è però la stessa unità che scriverebbe
    un umano. Segmentare il cinese è un'altra cura e non una regex.
    """
    assert extract_quantities("罗维戈仓库500个托盘") == {("个托盘", 500.0)}
