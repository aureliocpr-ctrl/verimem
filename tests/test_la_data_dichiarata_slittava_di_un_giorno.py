"""L'avviso che spiega un fraintendimento di date ne introduceva uno.

`test_la_porta_leggeva_al_passato_senza_dirlo` ha curato il silenzio: quando la
porta deduce una data dalla domanda e a quell'istante non c'è nulla, ora lo
dichiara, e la dichiara **leggibile** invece che come epoch. Giusto, e questo
test non lo tocca.

⚠️ **Ma la data dichiarata non è quella chiesta.** Misurato sul corpus vero il
2026-09-01, fuso «ora legale Europa occidentale»::

    domanda «il 18 luglio 2026 quanti fatti»   -> l'avviso dice  19/07/2026
    domanda «cosa sapevamo al 5 agosto 2026»   -> l'avviso dice  06/08/2026
    domanda «al 2026-01-31 quanti fatti»       -> l'avviso dice  01/02/2026

Tre su tre **il giorno dopo**, e l'ultimo cambia anche **mese**.

LA GIUNTURA, che è il posto dove questa casa trova i suoi difetti: `extract_as_of`
costruisce l'ancora a **fine giornata UTC** (``datetime(y, mo, d, 23, 59, 59,
tzinfo=timezone.utc)``), la formattazione la rilegge con
``datetime.fromtimestamp(as_of)`` — **senza fuso**, quindi in ora locale. A est
di Greenwich le 23:59:59 UTC sono già il giorno dopo. Nessuno dei due pezzi è
sbagliato da solo: sbagliata è la giuntura.

🔑 E il danno è mirato male: questo avviso esiste **per far vedere a chi legge
che la sua data è stata interpretata**, e gli mostra una data che lui non ha
scritto — cioè rende più difficile riconoscere il proprio caso.

⚠️ LIMITE DICHIARATO DI QUESTI TEST: discriminano solo dove il fuso è a **est**
di UTC (in Europa continentale sì, su una macchina in UTC no — lì la data era
già giusta). Su `TZ=UTC` restano verdi anche senza la cura: non sono un sensore
scollegato, ma non sono nemmeno una rete che scatta ovunque, e chi legge il
verde su un CI in UTC non ha imparato niente.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.temporal_context import extract_as_of


@pytest.fixture()
def memoria(tmp_path):
    """Fatti scritti ADESSO: qualunque ancora nel passato li esclude tutti."""
    m = Memory(str(tmp_path / "reg.db"))
    for i in range(1, 6):
        m.add(f"Il magazzino K-{70 + i} di Rovigo ha {4000 + i * 100} "
              f"metri quadrati.", topic="az/mag")
    return m


def test_la_data_dichiarata_e_QUELLA_CHE_L_UTENTE_HA_SCRITTO(memoria):
    """IL CUORE: chi chiede «il 18 luglio 2026» deve leggere 18/07/2026."""
    r = memoria.recall("il 18 luglio 2026 quanti magazzini risultavano", k=5)
    avviso = getattr(r, "letto_al_passato", None)
    assert avviso, "il presupposto è caduto: la porta non dichiara più nulla"
    assert avviso["quando_leggibile"] == "18/07/2026", (
        "la porta dichiara una data diversa da quella nella domanda: "
        f"{avviso['quando_leggibile']}"
    )


def test_anche_quando_slitta_il_MESE(memoria):
    """Il caso peggiore: l'ultimo giorno del mese scivola in quello dopo, e
    chi legge non riconosce più nemmeno il periodo."""
    r = memoria.recall("al 2026-01-31 quanti magazzini risultavano", k=5)
    avviso = getattr(r, "letto_al_passato", None)
    assert avviso
    assert avviso["quando_leggibile"] == "31/01/2026", avviso


def test_la_data_leggibile_e_COERENTE_con_l_epoch_che_l_accompagna(memoria):
    """L'invariante interno, indipendente da come è scritta la domanda: i due
    campi dello stesso avviso devono raccontare lo stesso istante, e l'ancora
    è costruita in UTC."""
    import datetime as dt

    r = memoria.recall("il 3 marzo 2019 quanti magazzini risultavano", k=5)
    avviso = getattr(r, "letto_al_passato", None)
    assert avviso
    atteso = dt.datetime.fromtimestamp(
        float(avviso["quando"]), dt.timezone.utc).strftime("%d/%m/%Y")
    assert avviso["quando_leggibile"] == atteso, avviso


def test_il_PRESUPPOSTO_l_ancora_e_a_fine_giornata_UTC():
    """Perché lo slittamento esiste, verificato invece che assunto: se un
    giorno l'ancora smettesse di essere a fine giornata UTC, questi test
    passerebbero per la ragione sbagliata."""
    import datetime as dt

    v = extract_as_of("al 18 luglio 2026")
    assert v is not None
    in_utc = dt.datetime.fromtimestamp(float(v), dt.timezone.utc)
    assert (in_utc.hour, in_utc.minute) == (23, 59), in_utc
