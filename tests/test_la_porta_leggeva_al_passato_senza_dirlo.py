"""La porta interpretava la domanda come «al giorno X» e, se a quel giorno non
c'era nulla, restituiva zero risultati senza dire che aveva viaggiato nel tempo.

DA DOVE VIENE — non e' un reperto mio. E' il TERZO CASO che il pezzo (i) non
copriva, consegnato dal banco «letture che non trovano» (doc 67, `8db090b2`),
con un A/B a quattro bracci nella STESSA esecuzione::

    domanda: «il 18 luglio 2026 quanti fatti scritti e quanti mai giudicati»

    1. as_of="auto"                          n=0
    2. as_of=None                            n=6   best=0.8790
    3. as_of=None + min_relevance=0.0001     n=6   best=0.8790   <- identico
    4. as_of="auto" + min_relevance=0.0001   n=0

⇒ 🔑 **IL PAVIMENTO NON C'ENTRA**: il best senza routing e' `0.8790`, SOPRA il
pavimento `0.8781`. Senza il routing sarebbe una lettura buona, e nemmeno
l'avviso del pavimento sarebbe dovuto.

IL TRIGGER, letto nel codice da chi l'ha misurato: la regex di `extract_as_of`
accetta l'articolo «il», e il commento sopra di essa lo dichiara gia' — *«da
soli sono gli articoli piu' comuni della lingua»*. Cosi' «cosa e' successo **il**
18 luglio», dove la data e' il SOGGETTO, viene letta come «cosa sapevamo **al**
18 luglio». ⚠️ **Il discrimine non e' la preposizione, e' il VERBO** (*sapevamo*
contro *e' successo*), e in inglese «on» fa lo stesso.

⚖️ COSA QUESTO FILE FA E NON FA. **NON tocca la regex**: distinguere «il» da
«al» e' il filone di chi ha misurato il trigger, e cambiarla sposta cosa la
porta CAPISCE. Qui si cura cosa la porta **DICE**: se ha viaggiato nel tempo per
una sua deduzione e non ha trovato nulla, deve dichiararlo, cosi' chi legge vede
il fraintendimento invece di un vuoto muto.

🔑 UN CAMPO NUOVO E NON `sotto_il_pavimento`: sono DUE cause diverse dello
stesso vuoto — la soglia che taglia e il tempo che non contiene nulla. Metterle
nello stesso campo sarebbe l'errore che questo modulo passa il tempo a curare:
un solo segnale per due significati.
"""

from __future__ import annotations

import pytest

from verimem.client import Memory


@pytest.fixture()
def memoria(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    m = Memory(str(tmp_path / "s.db"))
    m.add("Il canone del contratto Rossi e' 900 euro al mese.",
          source="Contratto Rossi: canone 900 euro al mese.", topic="tmp/x")
    return m


DOMANDA = "il 18 luglio 2019 quanto era il canone del contratto Rossi"


# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ A QUALE LIVELLO QUESTO BANCO MISURA, E PERCHE' NON PIU' IN ALTO.
#
# La prima stesura provava l'esito END-TO-END: «senza `as_of` la domanda trova,
# con `as_of="auto"` no». Sotto pytest l'embedder e' uno STUB SHA-256, quindi la
# similarita' e' arbitraria: misurato, la domanda lunga NON trova nemmeno senza
# routing (`n=0` in entrambi i bracci), mentre la query breve trova (`n=1`).
# ⇒ In questo ambiente **il vuoto del routing e quello del miss non sono
# distinguibili**, e il mio stesso CONTROLLO l'ha detto cadendo.
#
# 🔑 Quindi il banco scende di livello e misura il MECCANISMO, che e'
# deterministico: la data viene dedotta dalla domanda, e la dichiarazione esce
# quando la deduzione e' avvenuta e il risultato e' vuoto. **L'esito
# end-to-end col best `0.8790` sopra il pavimento `0.8781` e' misurato FUORI da
# pytest nel doc 67, ed e' citato come misura altrui, non rifatto qui.**
# ═══════════════════════════════════════════════════════════════════════════


def test_il_trigger_esiste_la_data_viene_DEDOTTA_dalla_domanda():
    """La premessa di tutto, e non dipende dal ranking: la domanda nomina la
    data come SOGGETTO e il routing la trasforma in un istante di
    interrogazione."""
    import datetime as _dt

    from verimem.temporal_context import extract_as_of
    quando = extract_as_of(DOMANDA)
    assert quando is not None, (
        "la data non viene piu' dedotta: il terzo caso del doc 67 non puo' "
        "piu' verificarsi, e questo file va rimisurato prima di toglierlo")
    assert _dt.datetime.fromtimestamp(float(quando)).year == 2019, quando


def test_la_data_nella_domanda_viene_letta_come_un_AL_e_la_porta_lo_dice(memoria):
    """IL CUORE: la domanda nomina una data come SOGGETTO, il routing la legge
    come istante di interrogazione, il filtro scarta tutto — e prima di questa
    cura il chiamante riceveva `[]` senza sapere che era successo."""
    ris = memoria.recall(DOMANDA, k=10, as_of="auto")
    assert len(ris) == 0, (
        "il routing temporale non ha svuotato il risultato: la premessa del "
        "banco non regge, rimisurare prima di fidarsi")
    avviso = getattr(ris, "letto_al_passato", None)
    assert avviso is not None, (
        "la porta ha interpretato la domanda come «al 18 luglio 2019», non ha "
        "trovato nulla e NON lo dice: e' il terzo caso del doc 67")
    assert "quando" in avviso, avviso


def test_la_data_interpretata_e_LEGGIBILE_non_un_timestamp(memoria):
    """⚠️ Un epoch non aiuta nessuno a vedere il fraintendimento: chi legge deve
    riconoscere la data che ha scritto nella domanda."""
    ris = memoria.recall(DOMANDA, k=10, as_of="auto")
    avviso = getattr(ris, "letto_al_passato", None)
    assert avviso is not None
    assert "2019" in str(avviso.get("quando_leggibile", "")), avviso


def test_CONTROLLO_se_il_passato_CONTIENE_qualcosa_nessun_avviso(memoria):
    """⚠️ LA POPOLAZIONE OPPOSTA: un `as_of` che trova risultati non deve
    produrre l'avviso. Un avviso sempre acceso e' rumore al posto del
    silenzio."""
    import time
    ris = memoria.recall("quanto e' il canone del contratto Rossi", k=10,
                         as_of=time.time() + 86400)
    if len(ris) >= 1:
        assert getattr(ris, "letto_al_passato", None) is None


def test_CONTROLLO_un_as_of_ESPLICITO_non_produce_la_dichiarazione(memoria):
    """⚖️ Chi passa `as_of` a mano SA di aver chiesto il passato: la
    dichiarazione serve a chi non sa che il routing e' scattato. Dirlo anche a
    lui non e' falso, ma e' rumore — e la distinzione tiene l'avviso raro."""
    ris = memoria.recall(DOMANDA, k=10, as_of=1.0)   # 1970: nulla esisteva
    assert len(ris) == 0
    assert getattr(ris, "letto_al_passato", None) is None
