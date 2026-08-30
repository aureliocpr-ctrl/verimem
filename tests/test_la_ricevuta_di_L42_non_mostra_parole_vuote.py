"""La ricevuta di `L4.2` non mostra una parola vuota come se fosse una grandezza.

MISURATO PRIMA DI CURARE (`W7-80`, 30/08, popolazione **intera** — 6176 fatti
vivi con fonte, funzione pura):

    fatti su cui `L4.2` parla   3077 (49,8%)   ·   riusi 5166 (1,7 per fatto)
    lato «nella_fonte»   VUOTA 15,5%  mista 18,0%  piena 66,6%
    lato «nel_claim»     VUOTA 34,6%  mista  3,6%  piena 61,9%

Il caso che ha aperto il filone e' una ricevuta mia delle 14:02::

    26 qui e' «fatti», nella fonte «di fonti il la non su»

**Il verdetto era giusto** — `L4.2` e' un AVVISO e non quarantina nulla —
**ma il messaggio non insegna niente a chi lo legge**, e la ricevuta e' l'unica
cosa che l'utente vede.

⚠️ **QUESTA CURA TOCCA UNA REGOLA SCRITTA DA UN ALTRO, e lo dichiaro.**
`_da_mostrare` ha un presidio esplicito (`test_la_ricevuta_di_L42_mostrava_meta_
di_cio_che_decideva.py`): *«il lato precedente non sostituisce quello seguente:
lo INTEGRA quando l'altro non c'e'»*. La cura **estende** quella regola da
«quando l'altro non c'e'» a «quando l'altro **non dice niente**» — e il test
originale continua a passare, perche' li' il lato seguente e' **pieno**.

⚖️ **Cosa NON cambia**: il **criterio** con cui `L4.2` decide. Solo il
**testo** della ricevuta. Se toccasse il criterio, una riformulazione legittima
verrebbe segnalata — ed e' il vincolo che il test gemello gia' presidia.
"""

from __future__ import annotations

from verimem.vicinato_del_valore import _da_mostrare


def test_una_parola_vuota_non_viene_mostrata_come_grandezza() -> None:
    """Il cuore: se il lato che segue e' solo grammatica, non e' un contesto."""
    assert "di" not in _da_mostrare({"di"}, {"pallet"})
    assert _da_mostrare({"di"}, {"pallet"}) == "prima del numero: pallet"


def test_le_vuote_si_tolgono_anche_da_un_insieme_misto() -> None:
    """«di fonti» → «fonti»: la parola piena resta, la grammatica cade."""
    assert _da_mostrare({"di", "fonti"}, set()) == "fonti"


def test_quando_entrambi_i_lati_sono_grammatica_lo_DICE() -> None:
    """Il caso della mia ricevuta delle 14:02. Stampare «di fonti il la non su»
    e' peggio che ammettere di non avere un contesto: chi legge crede che
    quella SIA la grandezza."""
    reso = _da_mostrare({"su"}, {"di", "il"})
    assert "su" not in reso.split() and "il" not in reso.split(), reso
    assert "grammatical" in reso or "nessuna" in reso, reso


# ── I TRE PRESIDI ESISTENTI, che la cura NON deve rompere. Se cadono, la cura
#    va RIFIUTATA: sto cambiando una regola invece di estenderla.

def test_presidio_il_precedente_INTEGRA_e_non_sostituisce() -> None:
    """Quando il lato che segue e' PIENO, resta quello. E' la regola originale
    e la cura non la tocca."""
    assert _da_mostrare({"pallet"}, {"riga"}) == "pallet"


def test_presidio_il_lato_precedente_si_annuncia() -> None:
    assert _da_mostrare(set(), {"riga"}) == "prima del numero: riga"


def test_presidio_senza_parole_accanto_lo_dice() -> None:
    reso = _da_mostrare(set(), set())
    assert reso != "?" and "nessuna parola" in reso, reso
