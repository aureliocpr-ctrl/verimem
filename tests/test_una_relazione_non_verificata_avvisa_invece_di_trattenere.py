"""Un riformulato vero veniva trattenuto da un criterio che vale una volta su tre.

`unverified_relation` (relation_claim.py) risponde quando il claim annuncia una
relazione — una causa, uno stato completato, una certezza — che la fonte non
enuncia. Il gate la usava per QUARANTINARE anche quando il giudice era certo::

    fonte  «Verbale: … la consegna e' stata effettuata il 12 marzo con 45 colli.»
    claim  «Sono stati spediti 45 colli.»
    esito  grounding 99.98 · layers ['L4-review'] · status quarantined
           withheld_despite_judge=True

Il criterio è lessicale: `_completed_action_absent_from` chiede che il PARTICIPIO
del claim compaia LETTERALMENTE nella fonte. `spediti` non è in una fonte che
dice `effettuata`, quindi scatta — e la riformulazione è il caso NORMALE, perché
nessuno ricopia la fonte.

**Le due popolazioni, misurate il 19/08 prima di decidere:**

    riformulati VERI con participio     2 trattenuti su 3
    confabulazioni da prendere          3 prese su 3
    …ma i loro grounding sono 2.81 · 5.50 · 93.95 ⇒ DUE su tre le ferma già il
    moat da solo. Il veto aggiunge qualcosa UNA volta e sbaglia DUE.

⇒ Decisione (registro `decisioni/prese`, 19/08): un criterio che sbaglia il
doppio di quanto serve non può essere un veto. Sopra la banda diventa un AVVISO
— `L4-relazione` — che è la stessa forma già scelta per L4.2 nello stesso file.

⚠️ **IL COSTO È DICHIARATO E PRESIDIATO QUI SOTTO, non nascosto**: la
confabulazione che il moat non ferma da solo ora ENTRA, con l'avviso addosso.
Era la scelta alternativa a perdere due riformulati veri su tre.

⛔ Ciò che questa decisione NON fa, e un test lo vieta: non tocca il criterio,
non tocca la banda, non spegne niente. Sotto `tau_hi` si trattiene come prima.
"""
from __future__ import annotations

import pathlib

import pytest

from verimem.client import Memory

FONTE = ("Verbale: il deposito di Prato ospita 300 bancali. La consegna e' "
         "stata effettuata il 12 marzo con 45 colli.")


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    for _e in ("VERIMEM_DATA_DIR", "ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        monkeypatch.setenv(_e, str(tmp_path / "d"))
    return Memory(str(pathlib.Path(tmp_path) / "s.db"))


def _layers(r):
    return [w.get("layer") for w in (r.get("warnings") or [])]


def test_un_riformulato_vero_non_e_piu_trattenuto(mem):
    """Il caso: la fonte dice «consegna effettuata con 45 colli», il claim dice
    «spediti». Stesso numero, stesso oggetto, participio diverso."""
    r = mem.add("Sono stati spediti 45 colli.", topic="rel/vero", source=FONTE)
    assert r.get("status") != "quarantined", (
        f"riformulato vero trattenuto con g={r.get('grounding_score')} "
        f"e layers={_layers(r)}")


def test_e_l_avviso_resta_visibile_a_chi_legge(mem):
    """⚠️ Ammettere NON vuol dire tacere. Se l'avviso sparisse, questa decisione
    diventerebbe «abbiamo spento un controllo» invece di «lo abbiamo declassato
    dichiarando»."""
    r = mem.add("Sono stati spediti 45 colli.", topic="rel/avv", source=FONTE)
    assert "L4-relazione" in _layers(r), (
        f"il fatto entra SENZA l'avviso: {_layers(r)}")


def test_IL_COSTO_la_confabulazione_che_il_moat_non_ferma_ORA_ENTRA(mem):
    """⚠️⚠️ IL PREZZO DELLA DECISIONE, scritto e presidiato invece che nascosto.

    «Il pagamento è stato effettuato» su una fonte che dice «in lavorazione» è
    una confabulazione, il CE le dà ~94 e il moat non la ferma. Prima la
    tratteneva il veto; ora entra con l'avviso.

    Questo test NON difende il comportamento: lo RENDE VISIBILE. Il giorno in
    cui qualcuno saprà fermarla senza perdere due riformulati veri su tre,
    questo test cadrà — ed è il segnale che la decisione è stata superata."""
    r = mem.add("Il pagamento e stato effettuato.", topic="rel/costo",
                source="Il pagamento e in lavorazione presso la banca.")
    assert r.get("status") != "quarantined"
    assert "L4-relazione" in _layers(r), (
        "entra SENZA avviso: allora sarebbe davvero un controllo spento")


def test_la_confabulazione_che_il_moat_ferma_resta_ferma(mem):
    """⚠️ POPOLAZIONE OPPOSTA. La decisione tocca solo il caso in cui il CE è
    SICURO. Dove il moat fa il suo lavoro, nulla cambia."""
    r = mem.add("Il contratto e stato firmato dal cliente.", topic="rel/opp",
                source="Il contratto e stato inviato per la firma al cliente.")
    assert r.get("status") == "quarantined", (
        f"una confabulazione che il moat bocciava ora passa: g="
        f"{r.get('grounding_score')}")


def test_la_banda_NON_e_stata_toccata(mem):
    """⚠️⚠️ IL VINCOLO PIÙ STRETTO: il modo più facile di far passare i test
    sopra è ammettere tutto sopra soglia. Un grounding basso deve restare
    trattenuto esattamente come prima."""
    r = mem.add("Il deposito di Prato ospita 500 bancali.", topic="rel/banda",
                source=FONTE)
    assert r.get("status") == "quarantined", (
        f"un numero cambiato non e' piu' fermato: g={r.get('grounding_score')}")
