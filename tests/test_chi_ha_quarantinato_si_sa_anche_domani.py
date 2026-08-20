"""Chi guarda un fatto quarantinato il giorno dopo non sapeva chi l'avesse deciso.

IL DIFETTO, trovato indagando il caso irrisolto di ws5 (un fatto quarantinato in
produzione con grounding 99.96 che riscrivendolo non si riproduce)::

    colonne di stato in `facts`   [created_at, status, grounding_score]
    audit_mutations               ZERO righe per quei fatti
    facts_undo_log                ZERO righe per quei fatti

Il campo ``quarantined_by`` — che dice QUALE layer ha deciso — l'ho aggiunto io
ieri, e esce **solo nella ricevuta**: la vede chi scrive, nell'istante in cui
scrive. Un minuto dopo l'informazione non esiste più da nessuna parte.

🔑 E NON È UN DETTAGLIO DI COMODITÀ: è il motivo per cui un caso aperto resta
aperto. I due fatti di ws5 sono lì, quarantinati, con il punteggio più alto del
corpus — e non possono dire da soli chi li ha fermati. Sei tentativi di
riproduzione (testo, fonte, topic, dimensione del corpus, canale SDK/CLI,
``validate`` full/fast) non hanno chiuso la domanda che una colonna avrebbe
risposto in un secondo.

📌 PERCHÉ NON IN ``audit_mutations``, che pure esiste ed è chiamata così: quella
tabella è **action-only per scelta deliberata e motivata** — *«storing WHAT was
deleted, even as a hash, inside an immutable chain makes GDPR Art.17 erasure a
logical contradiction»* — ed è per le operazioni DISTRUTTIVE (delete / purge /
forget / supersede / reset). Una quarantena al write non distrugge niente: è una
decisione di ammissione. Metterla lì sarebbe piegare una superficie al caso
sbagliato.

📌 E PERCHÉ FUORI DALLA SCALA VERSIONATA: accanto alla tabella dell'audit c'è
scritto il prezzo già pagato — *«deliberately outside the versioned ladder (v15
history: two forgotten target-bumps broke production writes)»*. Una colonna
nullable aggiunta in modo idempotente non ha bisogno di un numero di versione, e
non può rompere una scrittura per un bump dimenticato.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory

#: Frasi che L1 ferma per quello che sono: auto-attestazioni senza prova.
VANTI = [
    "Ho verificato che la funzione ora funziona correttamente.",
    "Il modulo e' stato testato ed e' pronto per la produzione.",
]


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def _colonna(mem, fact_id: str, nome: str):
    c = sqlite3.connect(str(mem.semantic.db_path))
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(facts)")]
        if nome not in cols:
            return "COLONNA ASSENTE"
        return c.execute(f"SELECT {nome} FROM facts WHERE id=?",
                         (fact_id,)).fetchone()[0]
    finally:
        c.close()


@pytest.mark.parametrize("vanto", VANTI)
def test_la_causa_della_quarantena_sopravvive_alla_ricevuta(mem, vanto):
    """IL CUORE: il fatto è nel database, quarantinato. Chi lo rilegge domani
    deve poter sapere CHI l'ha fermato senza avere sotto mano la ricevuta di
    quel momento."""
    r = mem.add(vanto, topic="az/q")
    assert r.get("status") == "quarantined", r
    assert r.get("id"), r
    persistito = _colonna(mem, r["id"], "quarantined_by")
    assert persistito, (
        f"la causa non è nel DB (valore: {persistito!r}) — l'informazione "
        f"esiste solo nella ricevuta, che nessuno rilegge")
    assert persistito == r.get("quarantined_by"), (
        f"il DB dice {persistito!r}, la ricevuta {r.get('quarantined_by')!r}: "
        f"due viste della stessa cosa che già divergono")


def test_CONTROLLO_POSITIVO_un_fatto_AMMESSO_non_porta_una_causa(mem):
    """⚠️ IL PRESIDIO: la colonna deve restare vuota per i fatti ammessi. Se
    fosse valorizzata sempre non distinguerebbe niente, ed è lo stesso motivo
    per cui `nascosti` deve essere zero su un documento pulito."""
    r = mem.add("Il magazzino di Prato contiene 300 pallet.", topic="az/ok",
                source="Inventario: il magazzino di Prato contiene 300 pallet.")
    assert r.get("status") != "quarantined", r
    assert not _colonna(mem, r["id"], "quarantined_by")


def test_il_DB_e_la_RICEVUTA_dicono_la_stessa_cosa(mem):
    """La proprietà che conta più del campo: due superfici della stessa
    informazione non devono divergere. È la classe che questa casa ha pagato
    tre volte (`_fact_view` copiata in `search`, poi in `history`), qui
    prevenuta prima che nasca la seconda copia."""
    r = mem.add(VANTI[0], topic="az/z")
    assert _colonna(mem, r["id"], "quarantined_by") == r.get("quarantined_by")


def test_uno_store_GIA_ESISTENTE_prende_la_colonna_senza_rompersi(tmp_path):
    """⚠️ IL PRESIDIO CHE PROTEGGE IL CORPUS DI PRODUZIONE: la colonna si
    aggiunge a un database già popolato, e i fatti che c'erano prima restano
    leggibili con la causa a `NULL` — «non registrata», che è la verità per
    tutto ciò che è stato scritto prima di oggi."""
    p = tmp_path / "vecchio.db"
    m1 = Memory(str(p))
    vecchio = m1.add("Il contratto vale 4500 euro.", topic="az/v",
                     source="Listino: il contratto vale 4500 euro.")
    del m1
    m2 = Memory(str(p))                      # riapertura: la migrazione rigira
    assert m2.get(vecchio["id"]) is not None, "il fatto vecchio non si rilegge"
    nuovo = m2.add(VANTI[0], topic="az/n")
    assert _colonna(m2, nuovo["id"], "quarantined_by")


def _prima_riga(db_path, colonne="id, status, grounding_score, quarantined_by"):
    c = sqlite3.connect(str(db_path))
    try:
        return c.execute(f"SELECT {colonne} FROM facts").fetchone()
    finally:
        c.close()


def test_ANCHE_LA_PORTA_facts_add_scrive_la_causa(tmp_path, monkeypatch):
    """⚠️ LA SECONDA PORTA, e il difetto non è nel gate: è nella GIUNTURA.

    `quarantined_by` si scrive in UN SOLO punto — `client.py` — e `facts add`
    non ci passa: quarantina per conto suo (``final_status = "quarantined" if
    gate.action == "downgrade"``) e chiama ``sm.store`` senza toccare la
    colonna. Il verdetto NUMERICO invece lo persiste, e il commento accanto
    dice perché: *«Il verdetto va PERSISTITO, non solo calcolato»*. L'autore no.

    🔬 MISURATO con un A/B a un solo fattore — stesso claim, stessa source::

        save      (client.py)   quarantined  92.16   quarantined_by 'gate'
        facts add (cli.py)      quarantined  92.16   quarantined_by None

    ⇒ Non è arretrato storico: è vivo. E spiega la parte recente dei 1958
    quarantinati senza autore su 2329 (84,1% del corpus al 20/08).
    """
    for v in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(v, str(tmp_path))
    from typer.testing import CliRunner

    from verimem.cli import app

    res = CliRunner().invoke(app, ["facts", "add", "-p", VANTI[0], "-t", "az/q"])
    assert res.exit_code == 0, res.output

    riga = _prima_riga(tmp_path / "semantic" / "semantic.db")
    assert riga is not None, f"nessun fatto scritto: {res.output}"
    _id, status, _gs, causa = riga
    assert status == "quarantined", (
        f"il banco non misura più ciò per cui esiste: atteso quarantined, "
        f"ottenuto {status!r}. Output: {res.output}")
    assert causa, (
        "`facts add` scrive il fatto e il punteggio ma NON chi l'ha fermato: "
        "chi rilegge domani trova una quarantena senza autore. La stessa "
        "scrittura fatta da `save` porta 'gate'.")


def test_LE_DUE_PORTE_DICONO_LA_STESSA_COSA(tmp_path, monkeypatch):
    """La proprietà che conta più del campo: due superfici della stessa
    decisione non devono divergere. Se un giorno cambia la regola (`moat` /
    `L1` / `gate`), questo test cade su ENTRAMBE o su nessuna — è ciò che
    impedisce alla seconda copia di nascere di nuovo."""
    for v in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(v, str(tmp_path))
    from typer.testing import CliRunner

    from verimem.cli import app

    res = CliRunner().invoke(app, ["facts", "add", "-p", VANTI[1], "-t", "az/q"])
    assert res.exit_code == 0, res.output
    _id, _st, _gs, causa_cli = _prima_riga(tmp_path / "semantic" / "semantic.db")

    mem = Memory(str(tmp_path / "altra.db"))
    r = mem.add(VANTI[1], topic="az/q")
    causa_client = r.get("quarantined_by")

    assert causa_cli == causa_client, (
        f"stessa frase, due porte, due risposte: `facts add` dice "
        f"{causa_cli!r} e `save` dice {causa_client!r}")


def test_ANCHE_IL_FLIP_DOPO_LA_SCRITTURA_dice_chi_ha_deciso(mem):
    """⚠️ LA TERZA PORTA, e non è al write: è DOPO.

    `SemanticMemory.quarantine_fact` ribalta un fatto già scritto — la usano il
    triage Tier-2 (`tier2_judge`), il composer e la demozione retroattiva
    quando la fiducia di una fonte crolla. Prende un ``reason``, lo manda al
    canale eventi… e la RIGA non diceva niente.

    🔑 È esattamente il difetto per cui `quarantined_by` è nata, su una
    superficie diversa: il canale eventi non è provenienza, perché **ruota**
    (misurato: 41.518 righe su due file, e il 75,7% delle scritture del
    giornale non esiste nemmeno nel corpus — sono banchi). Chi rilegge la riga
    domani non ha il giornale sotto mano, e spesso non ce l'ha più nessuno.

    ⛔ E il ``reason`` non può andare nella colonna: è testo libero e può
    portare PII, che la catena immutabile non deve fissare (`semantic.py`,
    `trust_ledger.py`). Per questo la colonna porta un CODICE a vocabolario
    chiuso, non la frase.
    """
    r = mem.add("Il magazzino di Prato contiene 300 pallet.", topic="az/ok",
                source="Inventario: il magazzino di Prato contiene 300 pallet.")
    assert r.get("status") != "quarantined", r
    fid = r["id"]

    assert mem.semantic.quarantine_fact(fid, reason="tier2:declass") is True
    assert _colonna(mem, fid, "quarantined_by"), (
        "un fatto ribaltato DOPO la scrittura resta senza autore: la riga dice "
        "solo 'quarantined', e il motivo vive solo in un giornale che ruota")


def test_IL_FLIP_DICE_QUALE_DELLE_TRE_CAUSE(mem):
    """⚖️ Non basta che la colonna sia piena: deve DISTINGUERE. I tre
    chiamanti hanno tre ragioni diverse — il triage Tier-2, il composer, la
    demozione retroattiva per fiducia della fonte — e leggerle tutte come una
    sola sarebbe la stessa cecità di prima con un valore dentro."""
    viste = set()
    for i, codice in enumerate(("tier2", "composer", "source-trust")):
        r = mem.add(f"Il deposito {i} contiene 300 pallet.", topic="az/ok",
                    source=f"Inventario: il deposito {i} contiene 300 pallet.")
        assert r.get("status") != "quarantined", r
        mem.semantic.quarantine_fact(r["id"], reason="x", deciso_da=codice)
        viste.add(_colonna(mem, r["id"], "quarantined_by"))
    assert viste == {"tier2", "composer", "source-trust"}, (
        f"le tre cause non si distinguono: la colonna dice {viste}")


#: Il vocabolario CHIUSO della colonna. Sei valori, tre per il write e tre per
#: il ribalto successivo. Non e' una lista di comodo: e' il motivo per cui la
#: colonna porta un codice invece del `reason`, che e' testo libero e puo'
#: portare PII dentro una catena immutabile.
VOCABOLARIO = {"moat", "L1", "gate", "store-screen",
               "tier2", "composer", "source-trust", "triage"}


def test_IL_VOCABOLARIO_E_CHIUSO_e_lo_screen_dello_store_ha_la_PRECEDENZA():
    """⚠️ LA PRECEDENZA E' IL PUNTO, non la lista.

    Quando il gate AMMETTE e uno screen dentro ``store()`` ribalta il fatto,
    rispondere «gate» non e' un'etichetta imprecisa: e' **falsa**, perche'
    attribuisce la decisione a chi aveva detto di ammettere. Sul giornale sono
    34 scritture quarantinate su 1268 (2,7%).

    📌 E il caso opposto va tenuto: se il gate HA declassato, l'autore e' suo
    (moat o L1 o gate), e lo screen dello store non c'entra.
    """
    from verimem.client import chi_ha_quarantinato as chi

    # lo store ribalta cio' che il gate aveva ammesso
    assert chi("passed", [], agito=["store-screen"]) == "store-screen"
    # ...anche se ci fossero avvisi L1 di natura ADVISORY: ha agito lo store
    assert chi("passed", [{"layer": "L1.13"}],
               agito=["store-screen"]) == "store-screen"
    # il gate ha declassato: l'autore e' del gate, non dello store
    assert chi("failed", [], agito=[]) == "moat"
    assert chi("passed", [{"layer": "L1.15"}], agito=[]) == "L1"
    assert chi("passed", [{"layer": "L3"}], agito=[]) == "gate"
    # e ogni risposta sta nel vocabolario dichiarato
    for m, w, a in [("failed", [], []), ("passed", [{"layer": "L1"}], []),
                    ("passed", [], []), ("passed", [], ["store-screen"])]:
        assert chi(m, w, agito=a) in VOCABOLARIO


def test_IL_MOAT_SI_DERIVA_dai_layer_e_non_si_reinventa():
    """L'altra meta' della superficie unica: `esito_del_moat` legge cio' che il
    gate ha gia' detto. I quattro esiti distinti sono la ragione per cui la
    funzione esiste — se un giorno cambiano i nomi dei layer, questo cade."""
    from verimem.client import esito_del_moat

    class _G:
        def __init__(self, gs): self.grounding_score = gs

    assert esito_del_moat(_G(90), [], source=None) == "not_run:no_source"
    assert esito_del_moat(_G(90), [{"layer": "L4-skipped"}],
                          source="x") == "not_run:no_judge"
    assert esito_del_moat(_G(None), [], source="x") == "not_run:unknown"
    assert esito_del_moat(_G(2), [{"layer": "L4-grounding"}],
                          source="x") == "failed"
    assert esito_del_moat(_G(99), [], source="x") == "passed"
