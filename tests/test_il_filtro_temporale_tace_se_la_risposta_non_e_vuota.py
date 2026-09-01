"""La dichiarazione sulla lettura al passato esce solo sul VUOTO, e il caso vero
non è vuoto.

`test_la_porta_leggeva_al_passato_senza_dirlo` ha introdotto `letto_al_passato`:
quando la porta **deduce** una data dalla domanda e a quell'istante non c'era
nulla, lo dichiara. Giusto, e questo test non lo tocca.

⚠️ **Ma la sua condizione è `not out`**: la dichiarazione esce solo se il
risultato è **completamente vuoto**. Misurato sul corpus vero il 2026-09-02
(documento `70`), sui tre casi che il `67` aveva misurato come spenti dal
routing temporale::

    758425daf047   n=10   fatto giusto PERSO   dichiarazione NESSUNA
    0ebe9e824198   n= 2   fatto giusto PERSO   dichiarazione NESSUNA
    3e74902dc247   n=10   fatto giusto PERSO   dichiarazione NESSUNA

**Zero su tre.** E sull'intera popolazione dei 16 fatti retrospettivi non esiste
**una sola** risposta vuota: la dichiarazione non ha mai occasione di uscire.

🔑 **Il caso non-vuoto è PEGGIO del vuoto.** Il vuoto è onesto — «non ho trovato
niente». Dieci fatti da cui il filtro ha tolto proprio quello che rispondeva
sono una risposta **plausibile e sbagliata**, e chi legge non ha nessun segnale.

LA CONDIZIONE UTILE non è «`out` è vuoto» ma **«il filtro temporale ha scartato
qualcosa»** — e quel conteggio oggi si perde dentro `recall_as_of`, che filtra e
restituisce solo i sopravvissuti. **Il vuoto è un caso particolare dello
scarto.**

📌 La forma della cura è già nel codice, sul filtro accanto: per il pavimento
`_n_prima` e `_best_prima` **si conservano prima del taglio**, apposta perché
l'avviso a valle possa dire quanti ne ha tolti. E il canale è lo stesso già
usato per il degrado — un contatore sull'oggetto `semantic`, letto dal chiamante
prima e dopo (`_recall_degraded_count`).
"""
from __future__ import annotations

import time

import pytest

from verimem.client import Memory

# ancora nel 2019: i fatti "vecchi" sopravvivono, i "nuovi" vengono scartati
DOMANDA = "cosa risultava sul magazzino K-77 al 3 marzo 2019"
VECCHIO = time.mktime((2018, 6, 1, 12, 0, 0, 0, 0, -1))


@pytest.fixture()
def misto(tmp_path):
    """Uno store in cui il filtro temporale scarta MA NON SVUOTA.

    Tre fatti asseriti nel 2018 (sopravvivono all'ancora del 2019) e tre
    asseriti adesso (scartati). È la situazione del corpus vero, dove la
    risposta torna piena e il fatto giusto è stato tolto.
    """
    m = Memory(str(tmp_path / "reg.db"))
    for i in range(3):
        m.add(f"Il magazzino K-77 di Rovigo aveva {4000 + i * 10} metri "
              f"quadrati nel deposito storico.", topic="az/vecchi",
              asserted_at=VECCHIO)
    for i in range(3):
        m.add(f"Il magazzino K-77 di Rovigo ha {5000 + i * 10} metri "
              f"quadrati dopo l ampliamento.", topic="az/nuovi")
    return m


def test_il_PRESUPPOSTO_il_filtro_scarta_senza_svuotare(misto):
    """Verificato invece che assunto: se un giorno la risposta tornasse vuota
    (o piena di tutto), il test sotto passerebbe per la ragione sbagliata."""
    con_ancora = misto.recall(DOMANDA, k=10)
    senza = misto.recall(DOMANDA, k=10, as_of=None)
    assert len(con_ancora) > 0, "il filtro ha svuotato: non è questo il caso"
    assert len(con_ancora) < len(senza), (
        "il filtro non ha scartato niente: non è questo il caso "
        f"({len(con_ancora)} con ancora, {len(senza)} senza)"
    )


def test_quando_il_filtro_SCARTA_la_porta_lo_dice_anche_se_non_ha_svuotato(misto):
    """IL CUORE: risposta piena, ma qualcosa è stato tolto dal tempo ⇒ si
    dichiara. È il caso che sul corpus vero vale 3 su 3 e oggi tace."""
    r = misto.recall(DOMANDA, k=10)
    avviso = getattr(r, "letto_al_passato", None)
    assert avviso, (
        "il filtro temporale ha scartato dei risultati e la porta non lo dice: "
        f"{len(r)} risultati serviti"
    )
    assert avviso.get("scartati"), avviso


def test_il_vuoto_resta_dichiarato_come_prima(tmp_path):
    """IL PRESIDIO sul comportamento che esisteva: se il filtro toglie TUTTO,
    la dichiarazione continua a uscire. Questo test resta verde anche senza la
    cura — è il suo mestiere."""
    m = Memory(str(tmp_path / "solo_nuovi.db"))
    for i in range(3):
        m.add(f"Il magazzino K-7{i} di Rovigo ha {5000 + i * 10} metri "
              f"quadrati.", topic="az/nuovi")
    r = m.recall(DOMANDA, k=10)
    assert len(r) == 0
    assert getattr(r, "letto_al_passato", None)


def test_senza_scarti_non_si_dichiara_niente(misto):
    """L'ALTRO PRESIDIO — rumore al posto del silenzio sarebbe il difetto
    opposto. Un'ancora nel futuro non scarta nulla: nessuna dichiarazione."""
    r = misto.recall("cosa risultava sul magazzino K-77 al 31 dicembre 2099",
                     k=10)
    assert len(r) > 0
    assert getattr(r, "letto_al_passato", None) is None


def test_un_as_of_esplicito_continua_a_non_dichiarare(misto):
    """⚖️ Chi passa `as_of` a mano SA di aver chiesto il passato: la
    dichiarazione serve a chi non l'ha chiesto. Comportamento preesistente,
    tenuto fermo."""
    r = misto.recall("quanti metri quadrati ha il magazzino K-77", k=10,
                     as_of=time.mktime((2019, 3, 3, 23, 59, 59, 0, 0, -1)))
    assert getattr(r, "letto_al_passato", None) is None
