"""`ask` in modo EXCLUDE serviva fatti che il gate aveva quarantinato.

La riga di apertura del prodotto: «a fact its source does not support is
QUARANTINED — stored, but kept OUT of default recall, so you never get it back
as truth». Il ramo EXCLUDE di `ask` la rompeva.

Trovato usando il prodotto. Store di cinque note, una delle quali il gate
quarantina; poi `ask("tutto tranne moat")`::

    stato dei fatti scritti:
       model_claim  Il gate lessicale gira sempre.
       model_claim  La quarantena tiene fuori dal recall di default.
       model_claim  Moat e gate sono due nomi della stessa cosa.
       model_claim  Senza source il moat non gira.
       quarantined  Il moat giudica la fonte contro il fatto.

    BASE    (list_facts)  : 5 fatti     <- include i quarantinati
    ESCLUSI (search_facts): 2 fatti     <- non li include

    'tutto tranne moat' -> 3 risultati, e fra questi:
       Il moat giudica la fonte contro il fatto.   (quarantined)

Due difetti in uno, e il secondo è peggiore del primo:

① Il fatto quarantinato ESCE da una superficie di lettura. Non è un problema
   di esclusione: è la quarantena che perde.
② Non si può nemmeno togliere. La base e l'insieme escludente guardano viste
   DIVERSE, quindi ciò che sta solo nella base è inescludibile per costruzione
   — nessuna formulazione della domanda lo fa sparire.

E sopra ci si sovrapponeva il difetto delle parole funzionali: «tutto tranne IL
moat» lasciava dentro 2 fatti invece di 1, perché l'articolo restringe l'insieme
escluso (stessa famiglia di `aa62e68b` su `count`).

Le due cose si curano insieme perché sono lo stesso errore: la base e gli
esclusi devono essere lo stesso insieme, chiesto allo stesso modo.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from verimem import Memory

#: La prima frase è una claim senza fonte: il gate la quarantina. Non è una
#: coincidenza da tenere fragile — il test verifica che sia successo davvero
#: prima di misurare, così se un domani il gate cambia idea il test lo dice
#: invece di passare a vuoto.
CORPUS = [
    "Il moat giudica la fonte contro il fatto.",
    "Senza source il moat non gira.",
    "Moat e gate sono due nomi della stessa cosa.",
    "La quarantena tiene fuori dal recall di default.",
    "Il gate lessicale gira sempre.",
]


@pytest.fixture()
def store():
    """RIPARATO il 2026-08-07, e la ragione conta più della riparazione.

    Il banco contava sul fatto che il gate quarantinasse la PRIMA frase da
    solo. Non lo fa più, e non per un guasto: sul ramo sono entrate quattro
    cure di L1 — fra cui `a6b7fd30` «una parola non è un claim: il
    detector L1 chiedeva un commit a un sismologo» — che l'hanno reso
    meno impulsivo di proposito. Misurato: tutte e cinque tornano
    `model_claim`, `layers=[]`.

    La canarino `test_il_banco_regge` ha fatto esattamente il suo mestiere:
    ha detto «questo banco non prova più niente» invece di lasciare
    passare a vuoto gli altri test.

    ⛔ Quello che NON si fa è ripristinare l'assert sul vecchio
    comportamento: sarebbe un test verde che tiene in vita ciò che qualcuno
    ha cambiato apposta — la classe che questo stesso ramo ha curato
    stamattina su `last_verified_at`.

    Quindi la quarantena qui diventa ESPLICITA. Il banco misura il ramo
    EXCLUDE, non i gusti lessicali del gate: dipenderne era una fragilità,
    e ora la premessa è costruita invece che sperata.
    """
    m = Memory(path=str(pathlib.Path(tempfile.mkdtemp()) / "s.db"))
    ids = [m.add(t, topic="note")["id"] for t in CORPUS]
    m.semantic.quarantine_fact(ids[0], reason="banco: premessa esplicita")
    return m


def _quarantinati(m) -> list[str]:
    return [f.proposition for f in m.semantic.list_facts(limit=100)
            if f.status == "quarantined"]


def test_il_banco_regge(store):
    """La premessa esiste ancora: se questo cade, gli altri test qui sotto
    non stanno misurando niente.

    Prima verificava che fosse il GATE a quarantinare, ed è caduto il
    2026-08-07 quando una cura di L1 l'ha reso meno impulsivo — facendo
    esattamente il suo mestiere. Ora la premessa è costruita a mano
    (vedi la fixture), quindi il canarino sorveglia che la costruzione
    regga, non i gusti del gate."""
    assert _quarantinati(store), (
        "nessun fatto quarantinato: il banco non prova più nulla")


def test_un_quarantinato_non_esce_dall_esclusione(store):
    quarantinati = set(_quarantinati(store))
    usciti = [r["text"] for r in store.ask("tutto tranne gate")["results"]
              if r["text"] in quarantinati]
    assert not usciti, (
        "il ramo EXCLUDE ha servito fatti che il gate aveva quarantinato — "
        "«kept OUT of default recall» non regge qui:\n  " + "\n  ".join(usciti))


def test_un_articolo_non_cambia_cosa_viene_escluso(store):
    """«tranne il moat» deve escludere esattamente quello che esclude
    «tranne moat»: l'articolo non fa parte del soggetto."""
    senza = {r["id"] for r in store.ask("tutto tranne moat")["results"]}
    con = {r["id"] for r in store.ask("tutto tranne il moat")["results"]}
    assert senza == con, (
        f"l'articolo cambia il risultato: {len(senza)} vs {len(con)} fatti")


def test_l_esclusione_esclude_davvero(store):
    """Il contratto minimo: dopo «tutto tranne X» non deve restare nessun
    fatto che nomina X."""
    rimasti = [r["text"] for r in store.ask("tutto tranne moat")["results"]
               if "moat" in r["text"].lower()]
    assert not rimasti, (
        "fatti che nominano il termine escluso sono rimasti:\n  "
        + "\n  ".join(rimasti))


def test_ma_il_resto_resta(store):
    """Controprova: l'esclusione non deve svuotare la risposta."""
    res = store.ask("tutto tranne moat")["results"]
    assert res, "l'esclusione ha svuotato tutto"
    assert any("quarantena" in r["text"].lower() for r in res)


def test_il_ramo_FIND_non_si_muove(store):
    """Perimetro: la cura tocca EXCLUDE, non la ricerca normale — che i
    quarantinati già li filtrava."""
    quarantinati = set(_quarantinati(store))
    got = store.ask("cosa fa il gate")
    assert got["intent"] != "exclude"
    assert not [r for r in (got.get("results") or [])
                if r.get("text") in quarantinati]
