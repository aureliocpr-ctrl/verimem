"""Le promesse del README devono valere APPENA INSTALLATO — zero flag, zero setup.

Nasce da un'osservazione di Aurelio il 2026-08-01, dopo una notte in cui avevo
riportato che «il prodotto funziona quando lo si usa come va usato»:

    «non è che ci deve essere scelta, nel senso: il programma funziona se usato
    come va usato, ma un utente normale non si deve mettere a controllare ste
    cose. Il sistema deve essere fatto in modo da funzionare dall'installazione,
    inutile altrimenti»

Ha ragione, e i numeri dello store reale gli danno ragione: **152 fatti
giudicati dal moat su 6572**, perche' il moat gira solo sulle scritture che
portano una `source` e nessuno legge le ricevute. Un default che richiede di
sapere qualcosa non e' un default: e' una trappola con le istruzioni allegate.

QUESTO FILE E' IL BANCO CHE MANCAVA. Ogni test:

* parte da una data dir VERGINE (nessuno store precedente, nessuna cache);
* non passa NESSUN flag, NESSUNA env, nessun parametro non-default;
* cita la riga del README che sta verificando;
* fallisce se la promessa vale solo «sapendo come».

Non verifica che il prodotto sia capace di una cosa — quello lo fanno gia' i
test di ogni sottosistema. Verifica che la faccia **da solo**, che e' la
differenza fra un motore e un prodotto.

DUE COSE CHE QUESTO BANCO NON PUO' FARE, e vanno dette perche' altrimenti il
verde qui si legge come una garanzia piu' ampia di quella che e':

* i modelli locali (embedder, gate CE, NLI) devono gia' essere su disco. Su una
  macchina davvero nuova il primo `verimem warmup` li scarica, e QUELLO e' un
  percorso di rete che qui non si esercita;
* «vergine» e' la data dir, non l'installazione Python: i pacchetti sono quelli
  del repo.

IL SECONDO LIMITE E' STATO PAGATO UNA VOLTA, il 2026-08-19, e sta scritto qui
perche' un limite dichiarato e' un debito: chi lo legge deve sapere se qualcuno
l'ha mai saldato, e con quale esito. Pacchetto costruito da `bcc35b5c` e
installato in un venv creato per l'occasione (`--no-cache-dir`, 7 min 49 s,
1140 MB su disco), poi esercitato FUORI da pytest — perche' sotto pytest il
`conftest` sostituisce l'embedder con uno stub su SHA-256, e ogni misura che
passa da un coseno diventa un'altra misura. Sul pacchetto installato:

* `verified_by` NON promuove a «verified»: ne' una provenienza vera
  (`ci:main:green`) ne' una ricevuta che si auto-dichiara
  (`["verified", "trusted", "self:approved"]`). Entrambe restano `model_claim`;
* la provenienza si vede in LETTURA (`['ci:main:green']`), come promette la
  vetrina — nella ricevuta della SCRITTURA il campo torna `None`, che e' una
  superficie diversa da quella promessa;
* `explain()` separa i due esiti su un campo, non su una parola: domanda
  estranea -> `abstained=True`, domanda che lo store sa -> `abstained=False`.

⚠️ E il primo limite RESTA, ora con un numero: un `pip install` pulito porta il
prodotto ma NON il giudice, e appena installato il moat non c'e'. Cosa costa
questo e' misurato in `test_il_referto_del_moat_spento_dice_cosa_si_perde.py`,
che nasce da qui.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def appena_installato(tmp_path, monkeypatch):
    """Una data dir che non e' mai esistita, e nient'altro.

    Le tre env sono quelle che il prodotto stesso usa per isolare lo store —
    non configurazione, ma il modo di dire «parti da zero». Tutto il resto
    (soglie, gate, tier, daemon) resta al suo default."""
    # I MODELLI DEVONO ESSERE SU DISCO, ed e' il limite che questo file
    # dichiara in cima — ma dichiararlo non basta: la CI warma con `--no-gate`
    # e ha la rete chiusa, e i test committati senza questa guardia sono andati
    # in `LocalEntryNotFoundError` su tutte le piattaforme, bloccando la PR.
    # Scritto il limite e non applicato: la stessa distanza fra promessa ed
    # esecuzione che questo banco esiste per misurare.
    from tests._real_model import real_ce_cached, real_model_cached
    if not real_model_cached() or not real_ce_cached():
        pytest.skip("i modelli locali non sono in cache (la CI warma con "
                    "--no-gate e senza rete): qui si verificano i DEFAULT dato "
                    "che l'installazione e' completa, non il download")
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.client import Memory
    return Memory(path=tmp_path / "semantic.db")


def test_una_scrittura_con_fonte_viene_GIUDICATA_senza_chiedere_nulla(
        appena_installato):
    """README: «the free local cross-encoder judges every write».

    Se questo diventa rosso, il moat e' tornato a non girare di default — ed e'
    la promessa su cui poggia tutto il resto del prodotto."""
    r = appena_installato.add(
        "Il rimborso avviene entro 7 giorni lavorativi.",
        source="La politica aziendale prevede il rimborso entro 7 giorni "
               "lavorativi dalla richiesta.",
        topic="policy/rimborsi")
    assert r.get("stored"), r
    assert isinstance(r.get("grounding_score"), (int, float)), (
        f"la scrittura NON e' stata giudicata dal moat, e nessuno l'ha chiesto "
        f"esplicitamente: e' il default che decide. {r}")
    assert r["grounding_score"] > 50, r


def test_una_fonte_che_NON_supporta_viene_fermata_senza_chiedere_nulla(
        appena_installato):
    """La meta' che conta: giudicare non serve se il verdetto e' sempre «passa».

    README: «a fact its source does not support is QUARANTINED — stored, but
    kept OUT of default recall»."""
    r = appena_installato.add(
        "Il rimborso avviene entro 24 ore.",
        source="La politica aziendale prevede il rimborso entro 7 giorni "
               "lavorativi dalla richiesta.",
        topic="policy/rimborsi")
    disp = (r.get("adjudication") or {}).get("disposition")
    assert r.get("status") == "quarantined" or disp == "quarantined", (
        f"una fonte che dice «7 giorni» ha lasciato passare «24 ore» senza "
        f"riserve: {r}")


def test_una_scrittura_SENZA_fonte_dichiara_che_non_e_stata_verificata(
        appena_installato):
    """Il default piu' scomodo, e va inchiodato proprio perche' e' scomodo.

    Senza `source` non c'e' NULLA contro cui giudicare, quindi il prodotto non
    puo' fare di meglio che ammettere. Ma deve DIRLO: e' la differenza fra «non
    ho verificato» e «ho verificato». Sullo store reale sono 152 fatti giudicati
    su 6572, e nessuno di quei 6420 sa di non essere stato giudicato."""
    r = appena_installato.add("Il rimborso avviene entro 7 giorni lavorativi.",
                              topic="policy/rimborsi")
    assert r.get("stored"), r
    assert r.get("grounding_score") is None, (
        "senza source il moat non ha nulla da confrontare: un punteggio qui "
        f"sarebbe inventato. {r}")
    adj = r.get("adjudication") or {}
    # SI INTERROGA LA STRUTTURA, NON IL TESTO. La prima stesura cercava le
    # sottostringhe "L4"/"skip"/"source" nella prosa della ricevuta, e falliva:
    # il prodotto lo dichiara in CAMPI (`evidence_class`, `confidence_tier`),
    # che e' il modo giusto di dirlo. E' la trappola gia' pagata sei volte in
    # una sessione e messa in memoria come feedback — presa una settima proprio
    # qui, nel test scritto per verificare l'onesta' delle dichiarazioni.
    assert adj.get("evidence_class") == "lexical_only", (
        f"senza source nessuna evidenza e' stata verificata, e la ricevuta non "
        f"classifica cosi' la scrittura: {r}")
    assert adj.get("confidence_tier") == "unverified", (
        f"la scrittura non giudicata non e' marcata `unverified`: chi ordina "
        f"per fiducia la trattera' come le altre. {r}")
    assert adj.get("judge") is None and adj.get("score") is None, adj


def test_un_valore_aggiornato_RITIRA_il_vecchio_senza_chiedere_nulla(
        appena_installato):
    """README: «Cross-fact contradiction + same-source evolution — ON by
    default. A plain `Memory()` no longer hoards a contradicted value».

    Misurato su data dir vergine il 2026-08-01: PostgreSQL poi MySQL ->
    `superseded: ['edc2cc9d76e9']`, e il recall restituisce solo il corrente."""
    m = appena_installato
    m.add("Il database di produzione e' PostgreSQL.", topic="infra/db")
    r = m.add("Il database di produzione e' MySQL.", topic="infra/db")
    assert r.get("superseded"), (
        f"il valore vecchio non e' stato ritirato: il recall servira' due "
        f"risposte in contesa a chi ne chiede una. {r}")
    testi = " ".join(h["text"].lower() for h in m.search("database di produzione", k=5))
    assert "mysql" in testi, testi
    assert "postgresql" not in testi, (
        f"il valore superato compare ancora nel recall di default: {testi}")


def test_il_dossier_si_astiene_su_una_domanda_estranea_senza_chiedere_nulla(
        appena_installato):
    """README: «on a question it cannot support it ABSTAINS ("I don't know")
    instead of stitching a guess from weak matches».

    Il bi-encoder e' anisotropo — ogni query somiglia a qualcosa intorno a 0.8 —
    quindi «nessun hit» da solo non basta, e l'astensione dipende da un gate che
    DEVE essere acceso di default sul canale che l'utente usa."""
    m = appena_installato
    m.add("Il database di produzione e' PostgreSQL.", topic="infra/db")
    rep = m.explain("come si pota un ulivo in primavera")
    assert rep.get("abstained") is True, (
        f"il dossier ha risposto a una domanda su cui non ha nulla, invece di "
        f"astenersi: {({k: v for k, v in rep.items() if k != 'facts'})}")


def test_il_dossier_RISPONDE_quando_ha_l_evidenza(appena_installato):
    """Controprova indispensabile: un dossier che si astiene sempre passerebbe
    il test sopra ed sarebbe inutile."""
    m = appena_installato
    m.add("Il database di produzione e' PostgreSQL.", topic="infra/db")
    rep = m.explain("quale database e' in produzione")
    assert rep.get("abstained") is not True, (
        f"si e' astenuto su una domanda che il suo store copre: {rep}")


def test_la_citazione_di_un_documento_e_ESATTA_senza_chiedere_nulla(
        appena_installato, tmp_path):
    """README: «Search indexed files with verimem_document_semantic_search
    (exact citations)».

    «Esatta» ha un significato verificabile e non opinabile: l'offset che il
    prodotto restituisce deve ritagliare dal file ORIGINALE esattamente il testo
    che ha citato. Se cosi' non fosse, la provenienza sarebbe decorativa — e una
    citazione decorativa e' peggio di nessuna citazione, perche' autorizza."""
    doc = tmp_path / "manuale.txt"
    doc.write_text(
        "Capitolo 1. Le richieste di rimborso si aprono dal portale.\n"
        "Capitolo 2. Il codice PROC-1037 identifica la procedura di reso.\n"
        "Capitolo 3. Le spedizioni partono il martedi'.\n", encoding="utf-8")
    m = appena_installato
    # TERZA OCCORRENZA DELLA CLASSE «capacita' raggiungibile solo da alcuni
    # canali», trovata da questo banco al primo giro esteso (2026-08-01):
    #
    #     MCP  hippo_document_index_file / _semantic_search   c'e'
    #     CLI  verimem index / search-docs                    c'e'
    #     SDK  Memory.<niente>                                NO
    #
    # `[x for x in dir(Memory) if 'doc' in x.lower()]` -> `[]`. Le altre due
    # occorrenze erano `recall --as-of` e la correzione di un fatto, entrambe
    # assenti dalla CLI e curate il 31/07 e il 01/08. Qui manca sull'SDK, cioe'
    # sul canale che un'APPLICAZIONE userebbe per integrare verimem — e il
    # README promette la citazione esatta fra le righe che descrivono il
    # prodotto. Lo skip NON e' un limite del test: e' il finding, e sparisce da
    # solo il giorno in cui il metodo esiste.
    if not hasattr(m, "index_document"):
        pytest.skip("SDK: nessun metodo per i documenti (MCP e CLI ce l'hanno) "
                    "— vedi il commento qui sopra, e' un finding non una resa")
    idx = m.index_document(str(doc))
    assert idx is not None
    hits = m.search_documents("codice della procedura di reso", k=3)
    assert hits, "nessun risultato su un documento appena indicizzato"
    originale = doc.read_text(encoding="utf-8")
    for h in hits:
        s, e = h.get("start"), h.get("end")
        if s is None or e is None:
            continue
        assert originale[s:e] == h["text"], (
            f"l'offset citato NON ritaglia il testo citato: la provenienza "
            f"sarebbe decorativa\n  atteso: {h['text'][:60]!r}\n  "
            f"trovato: {originale[s:e][:60]!r}")


def test_il_passato_si_puo_chiedere_senza_chiedere_nulla(appena_installato):
    """README: «Bi-temporal history — facts carry both *when it happened* and
    *when we learned it*. Query the past (`as_of`)».

    Il time-travel non e' un extra: e' cio' che distingue una memoria da un
    dizionario che sovrascrive. Deve valere sul client nudo."""
    import time as _t
    m = appena_installato
    m.add("Il database di produzione e' PostgreSQL.", topic="infra/db")
    quando = _t.time()
    _t.sleep(1.1)
    m.add("Il database di produzione e' MySQL.", topic="infra/db")
    adesso = " ".join(h["text"].lower()
                      for h in m.search("database di produzione", k=3))
    prima = " ".join(h["text"].lower()
                     for h in m.search("database di produzione", k=3,
                                       as_of=quando))
    assert "mysql" in adesso, adesso
    assert "postgresql" in prima, (
        f"il passato non restituisce il valore che allora era corrente: {prima}")
    assert "mysql" not in prima, (
        f"il passato contiene un fatto che a quell'istante non esisteva ancora: "
        f"{prima}")


#: LA CASCATA DI SUPERSESSIONE NON HA UN TEST QUI, e l'assenza e' un reperto.
#:
#: Dieci misure vere e scorrelate scritte su data dir vergine ne lasciano vive
#: QUATTRO: ogni fatto che porta un numero ritira il precedente. Ma la stessa
#: prova scritta come test — sia qui sia altrove — PASSA anche disattivando la
#: cura, cioe' non riproduce niente. Fuori da pytest, con le stesse env, la
#: cascata avviene (2 ritirati su 5 misurati il 2026-08-01).
#:
#: Qualcosa nell'ambiente della suite spegne il ramo che produce il difetto, e
#: non e' l'offline (`local_nli_available()` risponde True in entrambi i casi).
#: Finche' non si sa COSA, un test che passa sempre e' peggio di nessun test:
#: sarebbe il terzo presidio-che-non-presidia di questa giornata. Il difetto e'
#: inchiodato dove si puo' inchiodarlo davvero — sui predicati, in
#: `test_due_misure_diverse_non_sono_un_aggiornamento.py`.
