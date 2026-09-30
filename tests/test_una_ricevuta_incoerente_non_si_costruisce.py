"""Una ricevuta incoerente non deve poter esistere, nemmeno per un istante.

Gli invarianti stanno nel costruttore di `verimem/core/ricevuta.py` e sollevano
`ValueError`. Finche' nessuno li ESEGUE, pero', sono commenti con la sintassi di
un controllo: la fetta 1 e' arrivata alla lettura con sette invarianti e zero
test, e il rilievo l'ha fatto un pari. Questo file e' quel controllo.

DUE REGOLE CHE QUESTO FILE SI DA', perche' un negativo fatto male passa sempre:

1. `pytest.raises(ValueError)` da solo e' un righello LARGO: accetterebbe un
   errore sollevato da un campo che non c'entra, e il test resterebbe verde per
   la ragione sbagliata. Ogni negativo qui verifica anche il MESSAGGIO.

2. Un negativo e' CIECO se la stessa costruzione senza il difetto non passa: il
   raise potrebbe venire da qualunque altra cosa. Per ogni difetto si costruisce
   prima la variante SANA e si pretende che viva. Se un giorno la base diventasse
   invalida, questi test fallirebbero invece di mentire in verde.
"""
from __future__ import annotations

import json

import pytest

from verimem.core import (
    ALIAS_NON_ATTRIBUIBILE,
    CHIAVI,
    DECISO_DAL_DEFAULT,
    ESITI,
    NON_MISURATO_REMOTA,
    STATI_LIVELLO,
    Livello,
    Ricevuta,
    Ritiro,
)

#: Il minimo che una ricevuta deve portare: l'esito, dove si e' scritto, e chi
#: l'ha deciso. Tutto il resto e' facoltativo per costruzione.
BASE = dict(esito="ammesso", store="/prova/semantic.db",
            store_decided_by=DECISO_DAL_DEFAULT)


def _sana(**cambi):
    """La base con qualche campo cambiato. Se questa alza, il banco e' rotto."""
    return Ricevuta(**{**BASE, **cambi})


# ---------------------------------------------------------------- positivi

def test_la_ricevuta_minima_si_costruisce():
    r = _sana()
    assert r.esito == "ammesso"
    assert r.fermato_da is None
    assert r.livelli == () and r.ritirati == ()


def test_rende_esattamente_le_chiavi_dichiarate_e_nello_stesso_ordine():
    """CHIAVI e `come_dizionario()` non devono divergere: e' l'elenco che la
    proprieta' delle tre porte confronta, e se vive in due posti diverge."""
    assert tuple(_sana().come_dizionario()) == CHIAVI


def test_i_campi_dello_store_ci_sono_sempre_anche_quando_non_dicono_nulla():
    """Un campo ASSENTE direbbe due cose opposte a seconda della porta: «l'ha
    deciso il disco» e «questa porta lo butta». Presenti sempre."""
    d = _sana().come_dizionario()
    for chiave in ("store", "store_decided_by", "store_env_ignored"):
        assert chiave in d


def test_la_corsia_remota_porta_la_ragione_e_non_il_silenzio():
    r = _sana(store=NON_MISURATO_REMOTA, store_decided_by=NON_MISURATO_REMOTA)
    assert r.store == NON_MISURATO_REMOTA


def test_l_alias_non_attribuibile_e_un_valore_ammesso():
    assert _sana(store_decided_by=ALIAS_NON_ATTRIBUIBILE).store_decided_by


def test_il_margine_lo_calcola_la_ricevuta_non_il_chiamante():
    r = _sana(punteggio=99.5, soglia=40.0, scala="ce-locale-0-100",
              modello="local_gate_ce_v2")
    assert r.margine == pytest.approx(59.5)
    assert r.come_dizionario()["margine"] == pytest.approx(59.5)


def test_senza_punteggio_il_margine_non_si_inventa():
    assert _sana().margine is None


@pytest.mark.parametrize("esito", ESITI)
def test_tutti_e_quattro_gli_esiti_dichiarati_sono_costruibili(esito):
    """Il quarto valore, `degradato`, e' stato concesso dopo una discussione:
    se un giorno sparisse dall'elenco, questo test lo dice."""
    serve_un_nome = esito in ("fermato", "rifiutato")
    r = _sana(esito=esito, fermato_da="L4" if serve_un_nome else None)
    assert r.esito == esito


# ---------------------------------------------------------------- negativi

def test_un_esito_fuori_elenco_non_passa():
    _sana()                          # la base vive: il negativo non e' cieco
    with pytest.raises(ValueError, match="non ammesso"):
        _sana(esito="ammesso_forse")


def test_ammesso_con_un_bloccante_e_una_contraddizione():
    _sana(esito="ammesso")
    with pytest.raises(ValueError, match="incoerente"):
        _sana(esito="ammesso", fermato_da="L4")


@pytest.mark.parametrize("esito", ["fermato", "rifiutato"])
def test_chi_ferma_ha_un_nome(esito):
    _sana(esito=esito, fermato_da="L4")
    with pytest.raises(ValueError, match="senza fermato_da"):
        _sana(esito=esito)


@pytest.mark.parametrize("cambi", [
    dict(punteggio=99.5, soglia=40.0, modello="m"),                 # manca scala
    dict(punteggio=99.5, soglia=40.0, scala="ce-locale-0-100"),     # manca modello
])
def test_un_punteggio_senza_la_sua_scala_non_e_una_misura(cambi):
    """Il 13/09 un margine di 0,31 e' stato letto ~60 confrontando due scale."""
    _sana(punteggio=99.5, soglia=40.0, scala="ce-locale-0-100", modello="m")
    with pytest.raises(ValueError, match="senza scala o senza modello"):
        _sana(**cambi)


def test_un_punteggio_senza_soglia_non_ha_un_margine():
    _sana(punteggio=99.5, soglia=40.0, scala="s", modello="m")
    with pytest.raises(ValueError, match="senza soglia"):
        _sana(punteggio=99.5, scala="s", modello="m")


def test_lo_store_non_puo_essere_vuoto():
    _sana(store="/x")
    with pytest.raises(ValueError, match="store vuoto"):
        _sana(store="")


def test_chi_ha_scelto_lo_store_non_puo_essere_vuoto():
    _sana(store_decided_by="HIPPO_DATA_DIR")
    with pytest.raises(ValueError, match="store_decided_by vuoto"):
        _sana(store_decided_by="")


@pytest.mark.parametrize("campo", ["store", "store_decided_by"])
def test_i_due_campi_dello_store_sono_obbligatori(campo):
    """Senza default: il TIPO dice quello che il costruttore pretende. Stavano
    come `str | None = None` mentre il docstring vietava quel None."""
    senza = {k: v for k, v in BASE.items() if k != campo}
    with pytest.raises(TypeError, match="required"):
        Ricevuta(**senza)


# ------------------------------------------------------- negativi sul livello

@pytest.mark.parametrize("stato", STATI_LIVELLO)
def test_i_quattro_stati_di_un_livello_sono_costruibili(stato):
    serve = stato != "eseguito"
    liv = Livello(nome="L4", stato=stato,
                  ragione="R2 judge-unavailable" if serve else None)
    assert liv.stato == stato


def test_uno_stato_di_livello_fuori_elenco_non_passa():
    Livello(nome="L4", stato="eseguito")
    with pytest.raises(ValueError, match="non ammesso"):
        Livello(nome="L4", stato="quasi_eseguito")


def test_un_livello_che_non_ha_deciso_deve_dire_perche():
    """Uno stato diverso da «eseguito» senza ragione dice MENO di un campo
    assente, perche' sembra una risposta."""
    Livello(nome="L4", stato="saltato", ragione="R2 judge-unavailable")
    with pytest.raises(ValueError, match="senza ragione"):
        Livello(nome="L4", stato="saltato")


def test_anche_il_livello_porta_la_scala_del_suo_punteggio():
    """Due livelli punteggiano su scale diverse: il moat 99.5 su 0-100 e il
    giudice delle relazioni 0.87 su 0-1. Il difetto lo trovo' un pari."""
    Livello(nome="L4", stato="eseguito", punteggio=0.87, scala="0-1", modello="m")
    with pytest.raises(ValueError, match="senza scala o senza"):
        Livello(nome="L4", stato="eseguito", punteggio=0.87)


def test_un_livello_senza_nome_non_e_leggibile():
    with pytest.raises(ValueError, match="senza nome"):
        Livello(nome="", stato="eseguito")


def test_i_livelli_finiscono_nel_dizionario_con_i_loro_campi():
    r = _sana(livelli=(Livello(nome="L4", stato="saltato", ragione="R2"),))
    (liv,) = r.come_dizionario()["livelli"]
    assert liv["nome"] == "L4"
    assert liv["stato"] == "saltato"
    assert liv["ragione"] == "R2"


# --------------------------------------------- gli elementi delle due tuple

def test_la_ricevuta_si_serializza_davvero():
    """`come_dizionario()` esiste per essere serializzato, e finche' nessuno
    chiama json.dumps «serializzabile» e' una promessa, non una misura. Era la
    promessa che mancava: un Livello finito in `ritirati` la rompeva in
    silenzio fino al primo che provava a scriverla su un canale."""
    r = _sana(punteggio=99.5, soglia=40.0, scala="s", modello="m",
              livelli=(Livello(nome="L4", stato="saltato", ragione="R2"),),
              ritirati=(Ritiro(id="abc123", ragione="superseded da def456"),))
    tornata = json.loads(json.dumps(r.come_dizionario()))
    assert tornata["ritirati"][0]["id"] == "abc123"
    assert tornata["ritirati"][0]["ragione"] == "superseded da def456"
    assert tornata["livelli"][0]["nome"] == "L4"


def test_un_ritiro_senza_ragione_non_e_un_ritiro():
    """`ritirati` era l'unico campo che nessun caso riempiva: il pari ha
    predetto il difetto PRIMA di guardare, proprio perche' non era esercitato.
    Un identificatore da solo non puo' dire PERCHE' e' stato ritirato.

    E un `Livello` non va bene nemmeno lui: un avviso ritirato da una guardia
    E' un livello del cancello, un fatto ritirato dalla supersessione NO. Una
    classe per due oggetti e' la forma che in questo progetto costa di piu'."""
    _sana(ritirati=(Ritiro(id="abc123", ragione="superseded da def456"),))
    with pytest.raises(ValueError, match="ritirati porta"):
        _sana(ritirati=("abc123",))


def test_un_nome_dentro_livelli_non_passa():
    _sana(livelli=(Livello(nome="L4", stato="eseguito"),))
    with pytest.raises(ValueError, match="livelli porta"):
        _sana(livelli=("L4",))


def test_un_ritiro_e_serializzabile_con_la_sua_ragione():
    """La cella che il pari ha chiesto: una ricevuta con un livello RITIRATO,
    serializzata davvero. Prima `ritirati` usciva grezzo e json.dumps moriva."""
    r = _sana(ritirati=(Ritiro(id="abc123", ragione="superseded da def456"),))
    tornata = json.loads(json.dumps(r.come_dizionario()))
    assert tornata["ritirati"][0]["ragione"] == "superseded da def456"


def test_la_regola_della_scala_e_UNA_SOLA_per_la_ricevuta_e_per_il_livello():
    """Era scritta due volte con due messaggi. Due copie divergono: questo
    pretende che i due punti diano lo STESSO messaggio."""
    with pytest.raises(ValueError, match="senza scala o senza modello") as alto:
        _sana(punteggio=99.5, soglia=40.0, modello="m")
    with pytest.raises(ValueError, match="senza scala o senza modello") as basso:
        Livello(nome="L4", stato="eseguito", punteggio=0.87, modello="m")
    coda = "punteggio senza scala o senza modello"
    assert coda in str(alto.value) and coda in str(basso.value)


def test_un_ritiro_pretende_id_E_ragione():
    Ritiro(id="abc123", ragione="superseded da def456")
    for manca in (dict(id="", ragione="r"), dict(id="abc", ragione="")):
        with pytest.raises(ValueError, match="identificatore E la ragione"):
            Ritiro(**manca)


def test_un_livello_dentro_ritirati_non_passa():
    """Il tipo giusto e' `Ritiro`: `Livello` ci e' stato per un giro, ed era
    una parola per due oggetti."""
    _sana(ritirati=(Ritiro(id="a", ragione="r"),))
    with pytest.raises(ValueError, match="ritirati porta"):
        _sana(ritirati=(Livello(nome="L4", stato="eseguito"),))
