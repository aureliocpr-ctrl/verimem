"""La stessa scrittura lascia la stessa traccia da qualunque porta entri.

Il 25/09, su `0d0e6aac`, contando nel codice che cosa fa ciascuna porta dopo
il giudizio, commenti esclusi:

    emit_write (l'evento di scrittura)   SDK 4 | MCP remember 2 | MCP key_facts 0 | CLI facts add 0
    applica_verdetto (i ritiri)          SDK 1 | MCP remember 2 | MCP key_facts 0 | CLI facts add 2
    persisti_chi_ha_quarantinato         SDK 1 | MCP remember 1 | MCP key_facts 0 | CLI facts add 2
    _content_hash_id (id dal testo)      SDK 0 | MCP 1                            | CLI facts add 0

La stessa frase ha quattro destini secondo la porta. E ognuna delle quattro
copie del motore e' incompleta in un punto diverso: `key_facts` non lascia
l'evento, l'SDK fa un fatto nuovo a ogni ripetizione, MCP rende 3 chiavi del
nucleo su 14. La cura e' una sola, `Memory.add()` per tutte, e queste celle
la misurano ALLA PORTA, come la chiama chi la usa: la risposta racconta, la
tabella e il bus degli eventi testimoniano.

📌 L'id (D-0013 c, decisa il 20/09): `sha256(json.dumps([testo, topic,
firma della fonte]))[:12]`, con la firma a `None` senza fonte. La stessa frase
ripetuta e' UN fatto su ogni porta (T162: oggi lo e' solo su MCP), e due fonti
diverse che la sostengono sono DUE fatti, ciascuno con la sua provenienza:
oggi su MCP la seconda sovrascrive la prima in silenzio (misurato il 20/09:
99.92 sovrascritto da 98.56).
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest

TOPIC = "prova/porta-unica"
FRASE = "Il magazzino di Verona chiude alle 18 il sabato."
FONTE_1 = "Orari: il magazzino di Verona chiude alle 18 il sabato e alle 20 in settimana."
FONTE_2 = "Comunicazione del 3 marzo: il sabato il magazzino di Verona chiude alle 18."


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    return deposito


def _mcp(nome: str, argomenti: dict) -> dict:
    from verimem.mcp_server import call_tool

    risposta = asyncio.run(call_tool(nome, argomenti))
    return json.loads(risposta[0].text) if risposta else {}


def _sdk(store: Path):
    from verimem.client import Memory

    return Memory(str(store / "sdk.db"))


def _righe(db: Path | str, testo: str) -> list[tuple]:
    """(id, source_signature, superseded_by, status) delle righe con quel testo."""
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        return conn.execute(
            "SELECT id, source_signature, superseded_by, status FROM facts "
            "WHERE proposition = ? ORDER BY rowid", (testo,)).fetchall()


def _db_mcp() -> str:
    from verimem.mcp_server import _ag

    return str(_ag().semantic.db_path)


def _scrivi(porta: str, store: Path, fonte: str | None, testo: str = FRASE):
    """Una scrittura dalla porta nominata: (id reso, percorso del db)."""
    if porta == "sdk":
        mem = _sdk(store)
        r = mem.add(testo, topic=TOPIC, source=fonte)
        return r.get("id"), str(mem.semantic.db_path)
    argomenti = {"proposition": testo, "topic": TOPIC}
    if fonte is not None:
        argomenti["source"] = fonte
    r = _mcp("hippo_remember", argomenti)
    return r.get("id") or r.get("fact_id"), _db_mcp()


def test_la_memoria_del_server_e_LO_STESSO_store_dell_agente(store) -> None:
    """La prima cella, prima di ogni comportamento. La `Memory` con cui il
    server scrive deve essere costruita sull'OGGETTO store dell'agente, non sul
    suo percorso: col percorso si apre una seconda connessione allo stesso
    file e, con un percorso sbagliato, un secondo store vuoto che non fallisce
    (misurato il 20/09: `facts list --db` su un file che non c'e' esce 0 e lo
    crea). Identita', non uguaglianza: ogni verde successivo e' preso su UNO
    store."""
    from verimem import mcp_server

    assert mcp_server._memoria().semantic is mcp_server._ag().semantic


@pytest.mark.parametrize("porta", ["sdk", "mcp"])
def test_la_stessa_scrittura_due_volte_e_UN_fatto(store, porta) -> None:
    id_1, db = _scrivi(porta, store, FONTE_1)
    id_2, _ = _scrivi(porta, store, FONTE_1)
    righe = _righe(db, FRASE)
    assert id_1 and id_1 == id_2, f"{porta}: due id per la stessa scrittura: {id_1} {id_2}"
    assert len(righe) == 1, f"{porta}: la ripetizione ha fatto {len(righe)} righe: {righe}"


@pytest.mark.parametrize("porta", ["sdk", "mcp"])
def test_due_fonti_diverse_sono_DUE_fatti_ciascuno_con_la_sua_fonte(store, porta) -> None:
    id_1, db = _scrivi(porta, store, FONTE_1)
    id_2, _ = _scrivi(porta, store, FONTE_2)
    righe = _righe(db, FRASE)
    assert id_1 != id_2, f"{porta}: la seconda fonte ha riusato l'id della prima: {id_1}"
    assert len(righe) == 2, f"{porta}: {len(righe)} righe invece di due: {righe}"
    firme = {r[1] for r in righe}
    assert len(firme) == 2 and None not in firme, (
        f"{porta}: le due righe non portano ciascuna la sua fonte: {righe}")


@pytest.mark.parametrize("porta", ["sdk", "mcp"])
def test_senza_fonte_la_ripetizione_e_idempotente(store, porta) -> None:
    """Il negativo della cella sopra: senza, «l'id include la fonte» non si
    distinguerebbe da «l'id e' casuale quando la fonte manca»."""
    id_1, db = _scrivi(porta, store, None)
    id_2, _ = _scrivi(porta, store, None)
    assert id_1 and id_1 == id_2, f"{porta}: senza fonte due id: {id_1} {id_2}"
    assert len(_righe(db, FRASE)) == 1


def test_la_stessa_scrittura_ha_LO_STESSO_id_su_SDK_e_su_MCP(store) -> None:
    """L'id e' del contenuto, non della porta: se due porte lo derivassero in
    due modi, la stessa frase scritta da un agente e dal suo operatore
    sarebbero due fatti nello stesso store."""
    id_sdk, _ = _scrivi("sdk", store, FONTE_1)
    id_mcp, _ = _scrivi("mcp", store, FONTE_1)
    assert id_sdk == id_mcp, f"sdk {id_sdk} contro mcp {id_mcp}"


def _eventi_di(fid: str) -> int:
    from verimem.observability import BUS

    return sum(1 for e in BUS.history("flow.write", limit=100000)
               if (e.payload or {}).get("fact_id") == fid)


def _id_atteso(fonte: str | None) -> str:
    from verimem.client import id_dal_contenuto
    from verimem.supersession_policy import source_signature_of
    return id_dal_contenuto(FRASE, TOPIC, source_signature_of(fonte) if fonte else None)


@pytest.mark.parametrize("porta", ["sdk", "mcp"])
def test_una_scrittura_lascia_UN_evento(store, porta) -> None:
    """Si conta la DIFFERENZA: il bus degli eventi e' del processo, e con
    l'id derivato dal contenuto la stessa frase ha lo stesso id in ogni test
    che la scrive — contare il totale sommerebbe i test precedenti."""
    atteso = _id_atteso(FONTE_1)
    prima = _eventi_di(atteso)
    fid, _ = _scrivi(porta, store, FONTE_1)
    assert fid == atteso, f"{porta}: id {fid} invece di {atteso}"
    assert _eventi_di(fid) - prima == 1, (
        f"{porta}: {_eventi_di(fid) - prima} eventi flow.write per una scrittura")


def test_un_key_fact_e_una_scrittura_come_le_altre(store) -> None:
    """`key_facts` oggi: nessun evento, nessun ritiro, nessuna ricevuta."""
    prima = _eventi_di(_id_atteso(None))
    r = _mcp("hippo_record_episode", {
        "task_text": "Controllo degli orari del magazzino",
        "final_answer": "Orari confermati.",
        "key_facts": [{"proposition": FRASE, "topic": TOPIC}],
    })
    esiti = r.get("key_facts_outcome") or []
    assert len(esiti) == 1, f"risposta senza l'esito del key fact: {r}"
    fid = esiti[0].get("id")
    assert fid, f"il key fact non e' stato scritto: {esiti[0]}"
    assert fid == _id_atteso(None)
    assert _eventi_di(fid) - prima == 1, (
        f"{_eventi_di(fid) - prima} eventi flow.write per il key fact")
    for chiave in ("esito", "livelli", "punteggio", "soglia", "scala"):
        assert chiave in esiti[0], f"l'esito del key fact non porta '{chiave}': {esiti[0]}"
    righe = _righe(_db_mcp(), FRASE)
    assert len(righe) == 1


@pytest.mark.parametrize("fonte", [FONTE_1, None], ids=["con_fonte", "senza_fonte"])
def test_la_ricevuta_MCP_porta_le_chiavi_del_nucleo(store, fonte) -> None:
    """Le chiavi si prendono dalla ricevuta dell'SDK sulla stessa scrittura,
    non da un elenco scritto qui: se il nucleo ne aggiunge una, la cella la
    chiede anche a MCP senza che nessuno debba ricordarselo."""
    from verimem.adattatore_ricevuta import ricevuta_dal_cancello

    mem = _sdk(store)
    grezzo = mem.add(FRASE + " (sdk)", topic=TOPIC, source=fonte)
    nucleo = set(ricevuta_dal_cancello(grezzo).come_dizionario())
    argomenti = {"proposition": FRASE, "topic": TOPIC}
    if fonte is not None:
        argomenti["source"] = fonte
    r = _mcp("hippo_remember", argomenti)
    mancano = sorted(nucleo - set(r))
    assert not mancano, f"la ricevuta MCP non porta {len(mancano)} chiavi del nucleo: {mancano}"


def test_la_firma_della_fonte_non_la_dichiara_il_client(store) -> None:
    """Oggi MCP accetta `source_signature` come argomento: un client dichiara
    una fonte che non ha dato, e la coesistenza fra fonti distinte la prende
    per vera. La firma la calcola solo il motore, dalla fonte; l'argomento si
    ignora e la risposta lo dice nella chiave che il prodotto ha gia' per gli
    argomenti di fiducia che il server non onora, `gate_knobs_denied`.

    ⚠️ Non basta cercare la parola nella risposta: la risposta di oggi porta
    GIA' una chiave `source_signature` (il valore scritto), e quella ricerca
    sarebbe verde anche sul difetto. Si chiede l'elenco preciso."""
    r = _mcp("hippo_remember", {"proposition": FRASE, "topic": TOPIC,
                                "source_signature": "sha256:0123456789abcdef"})
    righe = _righe(_db_mcp(), FRASE)
    assert len(righe) == 1, f"la scrittura non c'e': {r}"
    assert righe[0][1] is None, f"la firma del client e' entrata nel fatto: {righe[0]}"
    assert "source_signature" in (r.get("gate_knobs_denied") or []), (
        f"l'argomento e' stato ignorato senza dirlo: {r.get('gate_knobs_denied')}")
