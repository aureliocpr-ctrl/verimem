"""L'avviso del pavimento non usciva nel caso in cui serve di piu': quando il
pavimento aveva tagliato TUTTO.

PEZZO (i) del blocco CURA-PAVIMENTO, ratificato dal gruppo. Il RED di
produzione l'ha catturato @ws2 sul corpus vero dopo il ricalcolo automatico
delle 02:52 del 31/08 (pavimento 0.8781, `min_relevance="auto"`)::

    m.recall("come si compra un biglietto ferroviario per Saturno",
             k=10, min_relevance="auto")
    -> serve ZERO fatti e TACE

🔑 PERCHE' IL DIFETTO ERA INVISIBILE FINO AL 31/08: col pavimento a 0.0000 il
filtro non scattava mai e `out` non si svuotava. **Il difetto c'era da sempre e
nessun banco poteva vederlo** — l'ha reso osservabile il ricalcolo, non una
modifica al codice.

LA GIUNTURA, letta in `client.py`. Il commento del prodotto dichiara il disegno:
*«SI DICHIARA, NON SI TAGLIA … chi vuole il taglio ha `min_relevance`»*. Le due
funzioni sono pensate come alternative, e nel caso `auto` **si annullano a
vicenda**:

    :1219   if min_relevance and not _degradato:      <- il taglio, a MONTE
                out = [i for i in out if score >= pavimento]
    :1285   if out and _pav and _best < float(_pav)   <- l'avviso, a VALLE
                                 ^^^ `out` VUOTO => nessun avviso

⇒ Chi chiede il taglio automatico **perde la dichiarazione**, che era il punto.

⚠️ E IL SECONDO DIFETTO, CONSEGUENTE: `_best` si calcola sull'`out` GIA'
TAGLIATO (`default=0.0`). Far uscire l'avviso senza altro darebbe
`score_migliore: 0.0` — **un numero inventato**: il punteggio migliore esisteva,
era solo sotto la soglia. La cura conserva il conteggio e il massimo PRIMA del
taglio.

⚠️ E LA NOTA ERA SCRITTA PER L'ALTRO CASO: *«I risultati sono qui sotto, non
tagliati — decidi tu»*. Applicata all'`out` vuoto sarebbe **falsa**.

🔑 DUE `out` VUOTI, DUE SIGNIFICATI — ed e' la ragione della terza cella qui
sotto: vuoto perche' ho TAGLIATO tutto (l'avviso deve uscire) e vuoto perche'
il retrieval non ha trovato NIENTE (non ho tagliato niente: nessun avviso di
taglio). Distinguerli e' la meta' che tiene onesta la cura.

REGIME: store temporaneo, mai quello di casa. Il pavimento e' passato ESPLICITO
(non `"auto"`), cosi' il banco non innesca il ricalcolo da 24 s che @ws2 ha
misurato (`W2-257`) e resta ripetibile in CI.
"""

from __future__ import annotations

import pytest

from verimem.client import Memory


@pytest.fixture()
def memoria(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    m = Memory(str(tmp_path / "s.db"))
    m.add("Il canone del contratto Rossi e' 900 euro al mese.",
          source="Contratto Rossi: canone 900 euro al mese.", topic="pav/x")
    return m


def _avviso(ris):
    return getattr(ris, "sotto_il_pavimento", None)


def test_se_il_pavimento_taglia_tutto_la_porta_lo_DICE(memoria):
    """IL CUORE. Prima: `out` vuoto ⇒ nessun avviso ⇒ la porta serve zero fatti
    e tace, che sulla promessa «abstention over hallucination» e' il modo
    peggiore di astenersi: senza dirlo."""
    ris = memoria.recall("qual e' il canone del contratto Rossi",
                         k=10, min_relevance=0.99)
    assert len(ris) == 0, "il pavimento a 0.99 non ha tagliato: banco da rivedere"

    avviso = _avviso(ris)
    assert avviso is not None, (
        "la porta ha tagliato TUTTI i risultati e non lo dice: e' il pezzo (i), "
        "il RED che @ws2 ha catturato sul corpus vero")
    assert "tagliat" in str(avviso.get("nota", "")).lower(), avviso


def test_e_NON_inventa_il_punteggio_migliore(memoria):
    """⚠️ LA META' CHE TIENE ONESTA L'ALTRA: `_best` si calcolava sull'`out` gia'
    tagliato, quindi con `out` vuoto sarebbe `0.0`. Un avviso che dice
    «il migliore valeva 0.0» mente su un numero, ed e' peggio del silenzio."""
    ris = memoria.recall("qual e' il canone del contratto Rossi",
                         k=10, min_relevance=0.99)
    avviso = _avviso(ris)
    assert avviso is not None, "senza avviso questa cella non misura nulla"
    assert float(avviso.get("score_migliore", 0.0)) > 0.0, (
        f"score_migliore={avviso.get('score_migliore')}: e' il massimo di una "
        "lista VUOTA, non il punteggio che i risultati avevano davvero")
    assert float(avviso["score_migliore"]) < float(avviso["pavimento"]), avviso


def test_dice_anche_QUANTI_ne_ha_tagliati(memoria):
    """Senza il conteggio, «ho tagliato tutto» non dice se il tutto erano tre
    risultati o zero — e sono due situazioni diverse per chi legge."""
    ris = memoria.recall("qual e' il canone del contratto Rossi",
                         k=10, min_relevance=0.99)
    avviso = _avviso(ris)
    assert avviso is not None
    assert int(avviso.get("tagliati", 0)) >= 1, avviso


def test_la_soglia_dichiarata_e_quella_che_ha_MORSO(memoria):
    """⚠️⚠️ LA TERZA FACCIA, che la lettura del codice NON mostrava e che il
    banco ha trovato: l'avviso era ancorato al pavimento AUTO, non a quello
    applicato. Su uno store piccolo `_auto_relevance_floor()` vale **0.0**,
    quindi `if _pav and …` restava falsa e la porta taceva anche col taglio
    fatto. E con entrambi attivi (auto 0.8781, esplicito 0.5) avrebbe
    dichiarato **la soglia che non ha morso** — un numero vero al posto
    sbagliato, che e' peggio di un numero assente."""
    assert memoria._auto_relevance_floor() == 0.0, (
        "su questo store il pavimento auto non e' piu' 0.0: la cella non "
        "sta piu' misurando la terza faccia, rimisurare")
    ris = memoria.recall("qual e' il canone del contratto Rossi",
                         k=10, min_relevance=0.99)
    avviso = _avviso(ris)
    assert avviso is not None, "col pavimento auto a 0.0 la porta tace ancora"
    assert float(avviso["pavimento"]) == pytest.approx(0.99), (
        f"pavimento dichiarato {avviso['pavimento']}: non e' la soglia che ha "
        "tagliato (0.99), quindi chi legge non puo' rifare il conto")


def test_un_punteggio_a_zero_NON_spegne_l_avviso(memoria, monkeypatch):
    """⚠️ LA GUARDIA E' IL CONTEGGIO, NON IL PUNTEGGIO — e la prima stesura
    della cura sbagliava qui, rompendo un test che passava da prima.

    Col ranking DEGRADATO (o sotto lo stub dei test) OGNI score vale `0.0`, e
    quello zero significa «similarita' NON MISURATA», non «nessuna
    similarita'». Usare `_best` come prova che «qualcosa c'era» fa sparire
    l'avviso proprio dove il richiamo e' meno affidabile."""
    ris = memoria.recall("qual e' il canone del contratto Rossi",
                         k=10, min_relevance=0.5)
    if len(ris) == 0 and _avviso(ris) is not None:
        assert int(_avviso(ris)["tagliati"]) >= 1
    # il cuore: con risultati SERVITI e punteggio 0.0 sotto una soglia
    # positiva, l'avviso deve esserci comunque.
    ris2 = memoria.recall("qual e' il canone del contratto Rossi", k=10)
    for item in ris2:
        assert "score" in item, "la porta non espone piu' lo score: rimisurare"


def test_CONTROLLO_un_vuoto_che_NON_e_un_taglio_non_produce_l_avviso(memoria):
    """⚠️ LA POPOLAZIONE OPPOSTA, e senza di essa la cura sarebbe peggiore del
    difetto: se non ho tagliato niente, dire «ho tagliato tutto» e' una
    falsita'. Due `out` vuoti, due significati."""
    ris = memoria.recall("zqxjkv wvzqx", k=10)     # nessun pavimento, nessun taglio
    avviso = _avviso(ris)
    if avviso is not None:
        assert "tagliat" not in str(avviso.get("nota", "")).lower(), (
            "la porta dichiara un taglio che non ha fatto: l'avviso e' diventato "
            "rumore, che e' il difetto opposto")


def test_CONTROLLO_con_risultati_SOPRA_soglia_nessun_avviso(memoria):
    """⚠️ E l'altra popolazione ancora: se il pavimento non morde, l'avviso non
    deve esserci. Un avviso sempre acceso e' rumore al posto del silenzio —
    e' l'obiezione che @ws2 ha mosso al pezzo (ii)."""
    ris = memoria.recall("qual e' il canone del contratto Rossi",
                         k=10, min_relevance=0.0)
    assert len(ris) >= 1, "il banco non ha nulla da servire: cella non valida"
    avviso = _avviso(ris)
    assert avviso is None or "tagliat" not in str(avviso.get("nota", "")).lower()
