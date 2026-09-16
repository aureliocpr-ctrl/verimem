"""README:535-536 — «Write receipts carry the handles too (`superseded_undo_ops`
on `add()`)».

IL CLAIM, testuale dal README pubblicato:

    Write receipts carry the handles too (`superseded_undo_ops` on `add()`),
    every retirement emits a `flow.supersession` event, and the Engine Room
    (`/ui/engine`) shows the pairs with one-click undo/restore.

PERCHE' QUESTA RIGA PRIMA DELLE ALTRE, e non e' per la riga in se'.

**Su quella maniglia poggia la gravita' di un ALTRO ticket.** T51 (ws3 Galileo)
dice che `update` ritira il fatto vecchio anche quando il gate boccia il nuovo,
ed e' classificato **P1** con questa motivazione: *«l'undo ripara, la maniglia e'
nella ricevuta»*. Se la maniglia non arriva, o arriva e non funziona, **T51 non
e' P1: e' P0** — perche' allora il fatto vecchio e' perso e basta.

Un presidio che tiene ferma questa riga tiene ferma anche la classificazione di
T51. Per questo l'ho presa prima del resto della sezione.

LO STATO, verificato il 10/09 leggendo:
  · `superseded_undo_ops` e' prodotto a `client.py:1213`;
  · **un solo file di test lo nomina** (`test_flow_isolamento_tenant.py`), e li'
    e' di passaggio: prova l'isolamento fra tenant, non la maniglia;
  · l'altra meta' della riga — «every retirement emits a `flow.supersession`
    event» — e' presidiata da cinque file, e il prodotto dichiara il perimetro
    da se' (`auto_dream_worker.py:428`: «le singole supersessioni un evento ce
    l'hanno; la passata no», con la cura accanto). **Quella meta' non la
    ritocco: e' coperta.**

⚠️ IL CONTROLLO POSITIVO QUI E' OBBLIGATORIO, piu' del solito. Un test che
chiede «la ricevuta porta la maniglia» e' verde anche quando **nessun ritiro e'
avvenuto** — e in un test con l'embedder stub la supersessione potrebbe non
scattare affatto. Percio' il primo asserto e' che il ritiro **c'e' stato**; solo
dopo si guarda la ricevuta.

ws7 «Iris», 10/09/2026. Misurato con:
`python -m pytest tests/test_la_ricevuta_porta_la_maniglia_per_disfare_il_ritiro.py -q -p no:randomly`
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

CAMPO = "superseded_undo_ops"


@pytest.fixture()
def store(tmp_path):
    return Memory(tmp_path / "store.db")


def _il_ritiro_e_avvenuto(ricevuta: dict) -> bool:
    """Il ritiro è avvenuto? Letto da `replaced`, che è un campo DIVERSO.

    ⚠️ Questa funzione esiste per due errori miei di fila, e li scrivo perché
    la forma è più istruttiva della riga.

    ① La prima versione chiedeva `replaced` **or** `superseded_undo_ops` — cioè
      guardava anche il campo che il test sotto deve verificare. Rompendo quel
      campo nel prodotto per falsificare, è caduto il CONTROLLO e il test della
      promessa è stato SKIPPATO: il presidio non si è acceso dove doveva.
      **Un controllo positivo accoppiato al proprio oggetto non è un controllo**:
      dice «c'è» quando c'è e tace quando manca, cioè quando servirebbe.

    ② La seconda versione cercava il fatto vecchio in
      `list_facts(limit=10000)` e ne guardava lo `status`: **cade sul prodotto
      SANO**, perché quella lista non me lo rende in quella forma. Un segnale
      «indipendente» scelto senza verificarlo è solo un secondo modo di
      sbagliare.

    ③ La terza — `replaced` da solo — **cade anche lei sul prodotto sano**: in
      questo scenario la ricevuta di `add()` non porta `replaced`. La prima
      versione passava proprio grazie al fallback che ho tolto.

    ⚠️ **MI FERMO AL TERZO E DICHIARO IL LIMITE invece di continuare a
    tentoni.** Il fatto misurato è questo: **la ricevuta di `add()` segnala il
    ritiro con UN CAMPO SOLO**, `superseded_undo_ops`. Non esiste, per questa
    via, un secondo segnale con cui confermare la supersessione — quindi il
    controllo positivo qui **è accoppiato al suo oggetto e non può non esserlo**.

    Che cosa vuol dire per chi legge: se un giorno il campo sparisce, questo
    file **non si accende** — va in `1 failed, 1 skipped` sul controllo, non sul
    test della promessa. È il rosso giusto per la ragione sbagliata, e ora è
    scritto. Il presidio forte va costruito sullo STORE (il fatto vecchio
    risulta ritirato?), e serve la via giusta per interrogarlo: `list_facts` non
    me lo rende in quella forma. **Aperto, e dichiarato.**
    """
    return bool(ricevuta.get("replaced") or ricevuta.get(CAMPO))


def _scrivi_e_poi_correggi(mem: Memory) -> tuple[dict, dict]:
    """Due misure dello stesso dato: la seconda dovrebbe ritirare la prima."""
    prima = mem.add("il capannone 12 misura 400 metri quadri.",
                    topic="perizie/capannone-12",
                    source="Perizia 2026-03-04: il capannone 12 misura 400 mq.")
    dopo = mem.add("il capannone 12 misura 450 metri quadri.",
                   topic="perizie/capannone-12",
                   source="Perizia 2026-09-01: il capannone 12 misura 450 mq.")
    return prima, dopo


# ── IL CONTROLLO POSITIVO PER PRIMO, E QUI CONTA PIU' DEL RESTO ─────────────


def test_CONTROLLO_un_ritiro_e_davvero_avvenuto(store):
    """Senza un ritiro, «la ricevuta porta la maniglia» e' verde a vuoto.

    Questo test non presidia il README: presidia gli ALTRI test di questo file.
    Se cade, non vuol dire che il prodotto e' rotto — vuol dire che lo scenario
    non ha prodotto la supersessione e che gli asserti sotto non stanno
    guardando niente.
    """
    prima, dopo = _scrivi_e_poi_correggi(store)
    assert prima.get("id"), f"la prima scrittura non ha reso un id: {prima!r}"
    assert dopo.get("id"), f"la seconda scrittura non ha reso un id: {dopo!r}"

    assert _il_ritiro_e_avvenuto(dopo), (
        "la seconda scrittura non ha ritirato la prima: nessuna supersessione è "
        "avvenuta in questo scenario.\n"
        "Gli altri test di questo file non possono dire niente finché questo "
        "non passa — non è un difetto del prodotto, è lo scenario che non "
        "esercita la strada."
    )


# ── LA PROMESSA ─────────────────────────────────────────────────────────────


def test_la_ricevuta_di_add_porta_la_maniglia_del_ritiro(store):
    """README:535 — «Write receipts carry the handles (`superseded_undo_ops`)».

    ⚠️ Non è una riga cosmetica: **su questa maniglia poggia la gravità P1 di
    T51**. Senza, un ritiro sbagliato non è riparabile e quel ticket sale a P0.
    """
    prima, dopo = _scrivi_e_poi_correggi(store)
    if not _il_ritiro_e_avvenuto(dopo):
        pytest.skip("nessun ritiro in questo scenario: lo dice il controllo sopra")

    assert CAMPO in dopo, (
        f"README:535 promette che la ricevuta di `add()` porti `{CAMPO}`, e "
        f"questa non ce l'ha. Chiavi: {sorted(dopo)}.\n"
        "Per l'utente: un fatto è stato ritirato e non ha in mano la maniglia "
        "per disfarlo. E per noi: la gravità P1 di T51 è motivata proprio da "
        "«l'undo ripara, la maniglia è nella ricevuta» — se la maniglia non "
        "arriva, quel ticket va riclassificato P0."
    )
    maniglie = dopo[CAMPO]
    assert maniglie, f"`{CAMPO}` c'è ma è vuoto: {maniglie!r}"
    assert isinstance(maniglie, dict), (
        f"`{CAMPO}` non è una mappa fact_id→op_id ma {type(maniglie).__name__}: "
        f"{maniglie!r}. Il docstring di `client.py:3990` la documenta come "
        "`{'130697c37e61': 'fcc15331752c4d33'}`."
    )
    for fatto, maniglia in maniglie.items():
        assert fatto and maniglia, (
            f"maniglia inutilizzabile: {fatto!r} -> {maniglia!r}. Un campo che "
            "c'è ma non porta un id è peggio di un campo assente: sembra una "
            "difesa e non lo è."
        )
