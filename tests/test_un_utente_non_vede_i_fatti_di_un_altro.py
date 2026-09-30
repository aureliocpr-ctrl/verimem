"""Un utente non vede i fatti di un altro, anche quando chi legge salta il prefisso.

ATLAS (29/09). Lo scope B-1 vive nel topic — ``user:<u>/agent:<a>/run:<r>/<base>``
— e fino a questa cura il restringimento lo faceva CHI LEGGE: la riga di comando
(`facts search`, `facts recall`) e il server MCP calcolano il prefisso e filtrano
i risultati per conto loro, ognuno con la sua copia. Lo store non sapeva niente
dell'utente. Un consumatore della libreria — un'applicazione che serve piu'
utenti con `Memory` o con lo store — non passa da quel codice: salta il prefisso
e vede i fatti di tutti.

LA PROMESSA. Un handle legato a un utente (`Memory(path, user_id=...)`, o lo
store stesso legato con `nell_ambito`) non restituisce MAI il fatto di un altro
utente, qualunque metodo chiami e qualunque argomento gli passi; e quello che
scrive finisce nel suo ambito. Il restringimento sta nello STORE, che e' l'unico
punto da cui passano tutti: non si puo' dimenticarlo in una chiamata.

⚖️ I CONTROLLI, e senza di loro questo file direbbe il falso. Un handle SENZA
ambito vede tutto — e' l'amministratore, il comportamento di oggi, che non deve
cambiare. E l'handle di un utente vede i SUOI fatti: «non vede quelli di Bob» e'
vero anche per un handle che non vede niente, e quello sarebbe un altro difetto.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.scope import scoped_topic
from verimem.semantic import Fact, SemanticMemory

ALICE = "Alice rinnova il piano annuale ogni gennaio."
BOB = "Bob rinnova il piano mensile ogni primo del mese."
BOB_2 = "Bob paga il piano con un bonifico bancario."
#: un fatto CONDIVISO (topic senza scope): per B-1 si vede solo su richiesta,
#: con `include_shared` — mai i fatti di un altro utente.
COMUNE = "Il piano annuale si rinnova a gennaio per tutti i clienti."
DOMANDA = "quando si rinnova il piano"


@pytest.fixture()
def negozio(tmp_path):
    """Lo store di un'applicazione con due utenti, scritto come lo scrivono
    le porte che conoscono lo scope: il topic porta il prefisso dell'utente."""
    db = tmp_path / "negozio" / "semantic.db"
    sm = SemanticMemory(db_path=db)
    ids: dict[str, str] = {}
    #: Bob ha DUE fatti e Alice uno: un conteggio che confondesse i due utenti
    #: darebbe un numero diverso, invece dello stesso 1 per tutti e due.
    for chi, testo, topic in (
            ("alice", ALICE, scoped_topic("abbonamenti", user_id="alice")),
            ("bob", BOB, scoped_topic("abbonamenti", user_id="bob")),
            ("bob2", BOB_2, scoped_topic("pagamenti", user_id="bob")),
            ("comune", COMUNE, "abbonamenti")):
        fatto = Fact(proposition=testo, topic=topic)
        sm.store(fatto, embed="sync")
        ids[chi] = fatto.id
    return db, ids


def _testi(risultati) -> set[str]:
    return {r.get("text") or getattr(r, "proposition", "") for r in risultati}


def test_CONTROLLO_senza_ambito_si_vede_tutto(negozio):
    """L'amministratore: il comportamento di oggi, e la prova che la domanda
    TROVA il fatto di Bob. Senza questa cella, «Alice non vede Bob» sarebbe
    vero anche su uno store in cui la ricerca non trova niente."""
    db, _ = negozio
    visti = _testi(Memory(path=str(db)).search(DOMANDA, k=10))
    assert {ALICE, BOB, COMUNE} <= visti, (
        f"senza ambito la ricerca non rende i tre fatti: {sorted(visti)}")


def test_l_handle_di_alice_non_vede_i_fatti_di_bob(negozio):
    """IL CUORE: un consumatore della libreria legato ad Alice chiama `search`
    senza passare nessun prefisso — e' esattamente il passo che salta."""
    db, _ = negozio
    visti = _testi(Memory(path=str(db), user_id="alice").search(DOMANDA, k=10))
    assert not {BOB, BOB_2} & visti, (
        "l'handle di Alice vede il fatto di Bob: il restringimento sta in chi "
        "legge, e un consumatore della libreria che non lo rifa' vede tutto")
    assert ALICE in visti, (
        f"l'handle di Alice non vede nemmeno il suo fatto: {sorted(visti)}")
    assert COMUNE not in visti, (
        "il fatto condiviso si vede solo su richiesta (include_shared)")


def test_un_argomento_non_allarga_l_ambito(negozio):
    """Un topic o un prefisso che nomina un altro utente viene riportato
    nell'ambito di chi legge, come fa `scoped_topic`: un argomento non apre la
    porta di Bob. `search` non prende un topic; lo prendono l'elenco e il
    conteggio, ed e' li' che un argomento potrebbe allargare."""
    db, _ = negozio
    alice = Memory(path=str(db), user_id="alice")
    elenco = _testi(alice.get_all(topic="user:bob/abbonamenti", limit=100))
    assert BOB not in elenco, (
        "passando il topic di Bob, l'handle di Alice elenca i fatti di Bob")
    # Il prefisso di Bob viene riportato in quello di Alice (`scoped_topic`: le
    # dimensioni dell'handle vincono), quindi conta i SUOI fatti: 1, non i 2 di
    # Bob.
    n = alice.count(topic_prefix="user:bob/")
    assert n == alice.count() == 1, (
        f"passando il prefisso di Bob l'handle di Alice conta {n}: Bob ha due "
        "fatti e Alice uno, e il prefisso va riportato nell'ambito di Alice")


def test_un_id_non_attraversa_l_ambito(negozio):
    """Chi conosce l'id di un fatto altrui non lo legge per id."""
    db, ids = negozio
    alice = Memory(path=str(db), user_id="alice")
    assert alice.get(ids["bob"]) is None, (
        "l'handle di Alice legge per id il fatto di Bob")
    assert alice.get(ids["alice"]) is not None, (
        "l'handle di Alice non legge per id nemmeno il suo fatto")


def test_elenco_e_conteggio_restano_nell_ambito(negozio):
    db, _ = negozio
    alice = Memory(path=str(db), user_id="alice")
    elenco = _testi(alice.get_all(limit=100))
    assert elenco == {ALICE}, f"get_all dell'handle di Alice: {sorted(elenco)}"
    assert alice.count() == 1, (
        f"l'handle di Alice conta {alice.count()} fatti invece del suo")


def test_include_shared_apre_i_condivisi_e_mai_gli_altri_utenti(negozio):
    db, _ = negozio
    alice = Memory(path=str(db), user_id="alice", include_shared=True)
    visti = _testi(alice.search(DOMANDA, k=10))
    assert {ALICE, COMUNE} <= visti, f"con include_shared: {sorted(visti)}"
    assert not {BOB, BOB_2} & visti, "include_shared ha aperto anche i fatti di Bob"


def test_quello_che_scrive_alice_finisce_nel_suo_ambito(negozio):
    """La scrittura: l'handle di Alice scrive con il SUO prefisso anche quando
    il topic non lo nomina, e Bob non lo vede."""
    db, _ = negozio
    nuovo = "Alice ha chiesto la fattura elettronica per il rinnovo."
    r = Memory(path=str(db), user_id="alice").add(nuovo, topic="fatture")
    assert r.get("stored") is True, f"la scrittura non e' andata: {r}"
    riletto = SemanticMemory(db_path=db).get(r["id"])
    assert riletto is not None and riletto.topic == "user:alice/fatture", (
        f"il fatto scritto da Alice ha topic {getattr(riletto, 'topic', None)!r}")
    bob = _testi(Memory(path=str(db), user_id="bob").search(
        "fattura elettronica", k=10))
    assert nuovo not in bob, "Bob vede il fatto appena scritto da Alice"


def test_lo_store_stesso_applica_l_ambito(negozio):
    """Il consumatore piu' in basso: lo store. Legato ad Alice, `recall`,
    `search_facts`, `get` e `all` restano nel suo ambito senza che il chiamante
    passi `topic_prefix` — che e' il passo che il consumatore salta."""
    db, ids = negozio
    sm = SemanticMemory(db_path=db).nell_ambito(user_id="alice")
    richiamati = {f.proposition for f, *_ in sm.recall(DOMANDA, k=10)}
    assert BOB not in richiamati and ALICE in richiamati, (
        f"recall dello store legato ad Alice: {sorted(richiamati)}")
    cercati = {f.proposition for f in sm.search_facts("piano", limit=10)}
    assert BOB not in cercati and ALICE in cercati, (
        f"search_facts dello store legato ad Alice: {sorted(cercati)}")
    assert sm.get(ids["bob"]) is None
    assert {f.proposition for f in sm.all()} == {ALICE}


def test_il_costruttore_unico_non_ignora_l_ambito_col_server(monkeypatch, tmp_path):
    """`open_memory` e' il costruttore che i consumatori devono usare. Con un
    server remoto restituiva il client remoto IGNORANDO `user_id`: un handle
    senza ambito a chi aveva chiesto quello di Alice. Ora rifiuta, finche' il
    client remoto non sa legarsi a un utente."""
    import verimem.client as motore
    costruiti: list[dict] = []

    class _Remoto:
        def __init__(self, *args, **kwargs):
            costruiti.append(kwargs)

        def health(self) -> bool:
            return True

    monkeypatch.setenv("VERIMEM_SERVER_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(motore, "_remote_cls", lambda: _Remoto)
    with pytest.raises(PermissionError):
        motore.open_memory(str(tmp_path / "s.db"), user_id="alice")
    assert not costruiti, "il client remoto e' stato costruito lo stesso"
    # CONTROLLO: senza ambito il cammino verso il server e' quello di prima.
    assert isinstance(motore.open_memory(str(tmp_path / "s.db")), _Remoto)


def test_CRICCHETTO_ogni_metodo_ammesso_applica_l_ambito():
    """Un metodo fra gli ammessi che lo store legato NON sovrascrive deve
    applicare la clausola dell'ambito nella base: altrimenti e' ammesso senza
    essere ristretto, cioe' aperto. Un metodo nuovo che entra nell'elenco senza
    l'una o l'altra cosa accende questo test il giorno in cui entra."""
    import inspect

    from verimem import semantic as s
    scoperti = [
        nome for nome in sorted(s._CONSAPEVOLI_DELL_AMBITO)
        if nome not in vars(s._StoreNellAmbito) and nome != "nell_ambito"
        and "_clausola_dell_ambito" not in inspect.getsource(
            getattr(s.SemanticMemory, nome))]
    assert not scoperti, f"ammessi e non ristretti: {scoperti}"


def test_un_metodo_non_ammesso_rifiuta_e_non_tocca_niente(negozio):
    """Il «nasce chiuso», misurato: `delete` non sa ancora applicare l'ambito,
    quindi sullo store legato rifiuta — e il fatto di Bob e' ancora li'."""
    db, ids = negozio
    legato = SemanticMemory(db_path=db).nell_ambito(user_id="alice")
    with pytest.raises(PermissionError):
        legato.delete(ids["bob"])
    assert SemanticMemory(db_path=db).get(ids["bob"]) is not None, (
        "lo store legato ad Alice ha cancellato il fatto di Bob")


def test_il_motore_legato_chiude_i_metodi_che_non_sanno_l_ambito(negozio):
    db, ids = negozio
    alice = Memory(path=str(db), user_id="alice")
    with pytest.raises(PermissionError):
        alice.delete(ids["bob"])
    with pytest.raises(PermissionError):
        _ = alice.documents
    assert SemanticMemory(db_path=db).get(ids["bob"]) is not None
    # CONTROLLO: il motore senza ambito non e' stato chiuso.
    assert callable(Memory(path=str(db)).delete)
